from datetime import datetime, timedelta, timezone
from hamutay.gpu_lease import cli, ledger, run as runmod
from hamutay.gpu_lease.state import read_lease, read_quarantine, list_tombstones

START = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)

class Clock:
    def __init__(self): self.t = START
    def now(self): return self.t
    def sleep(self, s): self.t += timedelta(seconds=s)

class FakeProc:
    def __init__(self, sd, scope, rc=0, lifetime=60):
        self.sd, self.scope, self.rc, self.left = sd, scope, rc, lifetime
        sd.units[scope] = {"active_state": "active", "sub_state": "running", "load_state": "loaded", "invocation_id": "s"}
    def poll(self):
        self.left -= 1
        if self.left <= 0:
            self.sd.units[self.scope]["active_state"] = "inactive"; return self.rc
        return None
    def wait(self): return self.rc
    @property
    def returncode(self): return self.rc

def _ack(p, sd, lease_id):
    ledger.append(p, {"action_id": "e", "phase": "outcome", "action": "ensure_stopped", "episode_id": lease_id,
                      "outcome": "ok", "by": "heartbeat:qwen", "at": START.isoformat()})
    sd.units["hamutay-llama-server.service"] = {"active_state": "inactive", "sub_state": "dead", "load_state": "loaded", "invocation_id": ""}

def test_run_leases_waits_launches_releases(p, sd):
    clock = Clock(); procs = []
    def launcher(scope, cmd):
        pr = FakeProc(sd, scope, rc=0, lifetime=3); procs.append(pr); return pr
    # acknowledge as soon as a lease exists: simulate the heartbeat inside wait's sleep
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and not any(r.get("action") == "ensure_stopped" for r in ledger.rows(p)):
            _ack(p, sd, v.data["lease_id"])
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "true"],
                  systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)
    assert rc == 0 and procs and read_lease(p, clock.now()).kind == "absent" and list_tombstones(p) == []

def test_run_rejects_short_ttl(p, sd):
    assert cli.main(["run", "--holder", "y", "--purpose", "t", "--ttl", "5m", "--", "true"], systemd=sd) == 2

def test_run_kills_scope_when_renew_fails_before_expiry(p, sd, monkeypatch):
    clock = Clock()
    def launcher(scope, cmd): return FakeProc(sd, scope, rc=0, lifetime=10_000)
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and not any(r.get("action") == "ensure_stopped" for r in ledger.rows(p)):
            _ack(p, sd, v.data["lease_id"])
    # make renew fail after launch by deleting the lease file underneath the supervisor
    def failing_renew(ctx, lease_id, ttl):
        p.lease.unlink(missing_ok=True); return False
    monkeypatch.setattr(runmod, "renew_once", failing_renew)
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "sleep", "1"],
                  systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)
    assert rc == 5
    assert any(c[0] == "stop" and c[1].startswith("ayllu-gpu-") for c in sd.calls)
    assert clock.now() <= START + timedelta(minutes=15)   # died before expiry
    assert any(r.get("action") == "workload_killed" and r.get("outcome") == "ok" for r in ledger.rows(p))

def test_run_registration_failure_shuts_down_like_any_path(p, sd):
    clock = Clock()
    class Unregistered(FakeProc):
        def __init__(self, sd, scope): super().__init__(sd, scope); sd.units[scope]["load_state"] = "not-found"; sd.units[scope]["active_state"] = "inactive"
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and not any(r.get("action") == "ensure_stopped" for r in ledger.rows(p)):
            _ack(p, sd, v.data["lease_id"])
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "true"],
                  systemd=sd, now=clock.now, launcher=lambda scope, cmd: Unregistered(sd, scope), sleep=sleep)
    assert rc == 6 and read_lease(p, clock.now()).kind == "absent" and list_tombstones(p) == []

def test_run_lease_replaced_between_unlocked_wait_and_locked_recheck_no_hang(p, sd):
    # CRITICAL 1 regression: wait_ready succeeds unlocked, then the lease disappears
    # (or is no longer ours) before the locked re-check inside the launch block. The
    # launcher must never be reached, and the wrapper must exit 3 promptly rather than
    # hang self-deadlocked on 4090.lock (the old bug: _release called from inside a
    # `with locked(...)` block already held by supervise itself).
    clock = Clock()
    launcher_calls = []
    def launcher(scope, cmd):
        launcher_calls.append((scope, cmd))
        return FakeProc(sd, scope, rc=0, lifetime=3)
    acked = {"v": False}
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and not acked["v"]:
            _ack(p, sd, v.data["lease_id"])
            acked["v"] = True
            # right after the unlocked wait_ready would first succeed, pull the lease
            # out from under the locked re-check
            p.lease.unlink(missing_ok=True)
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "true"],
                  systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)
    assert rc == 3
    assert launcher_calls == []

def test_run_unkillable_scope_quarantines_and_leaves_lease(p, sd):
    # CRITICAL 2: a scope that never dies after `stop` must not be silently abandoned —
    # quarantine_enter(scope_unkillable) must be written, and the lease/tombstone must
    # stay in place (no release) so the next actor resolves it.
    class StubbornSystemd:
        """Like FakeSystemd, but stop/kill never change unit state: the scope can't die."""
        def __init__(self):
            self.units = {}
            self.calls = []
        def show(self, unit):
            self.calls.append(("show", unit))
            return dict(self.units.get(unit, {"active_state": "inactive", "sub_state": "dead",
                                              "load_state": "not-found", "invocation_id": ""}))
        def start(self, unit):
            self.calls.append(("start", unit))
            self.units[unit] = {"active_state": "active", "sub_state": "running",
                                "load_state": "loaded", "invocation_id": f"inv-{len(self.calls)}"}
            return 0, ""
        def stop(self, unit):
            self.calls.append(("stop", unit))
            return 0, ""   # unlike FakeSystemd.stop, state never flips to inactive
        def kill(self, unit, signal="TERM"):
            self.calls.append(("kill", unit, signal))
            return 0, ""   # no effect either
    sd2 = StubbornSystemd()
    clock = Clock()
    def launcher(scope, cmd): return FakeProc(sd2, scope, rc=0, lifetime=10_000)
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and not any(r.get("action") == "ensure_stopped" for r in ledger.rows(p)):
            _ack(p, sd2, v.data["lease_id"])
    def failing_renew(ctx, lease_id, ttl):
        return False
    import hamutay.gpu_lease.run as runmod2
    orig = runmod2.renew_once
    runmod2.renew_once = failing_renew
    try:
        rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "sleep", "1"],
                      systemd=sd2, now=clock.now, launcher=launcher, sleep=sleep)
    finally:
        runmod2.renew_once = orig
    assert rc in (5, 6)
    assert read_lease(p, clock.now()).kind == "live"
    assert list_tombstones(p) != []
    q = read_quarantine(p)
    assert q is not None and q["reason"] == "scope_unkillable"

def test_run_stops_scope_before_release_when_command_exits_but_scope_stays_active(p, sd):
    # MINOR 7: "release never precedes scope death". poll() reports the command exited
    # (returns 0) but the scope's own active_state is left "active" by the fake process
    # (it never flips it, unlike FakeProc) so the wrapper must stop it and observe it
    # dead as part of run's own exit sequence, before release — not skip straight to
    # release because poll() returned.
    class ExitedButScopeStillActive:
        def __init__(self, sd, scope):
            self.sd, self.scope = sd, scope
            sd.units[scope] = {"active_state": "active", "sub_state": "running",
                               "load_state": "loaded", "invocation_id": "s"}
        def poll(self):
            return 0   # command already exited on the very first poll
        def wait(self): return 0
        @property
        def returncode(self): return 0
    clock = Clock()
    def launcher(scope, cmd): return ExitedButScopeStillActive(sd, scope)
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and not any(r.get("action") == "ensure_stopped" for r in ledger.rows(p)):
            _ack(p, sd, v.data["lease_id"])
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "true"],
                  systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)
    # The command's own exit code (0) is not what's returned here: the scope was still
    # active when the command's process exited, so the wrapper had to force it down
    # itself, which is exit 5 by the same convention as any other supervisor-initiated
    # kill. What this test asserts is the ordering invariant: stop-and-observe-dead
    # strictly before release.
    assert rc == 5
    rows = ledger.rows(p)
    stop_idx = next(i for i, r in enumerate(rows)
                    if r.get("action") == "workload_killed" and r.get("phase") == "outcome" and r.get("outcome") == "ok")
    release_idx = next(i for i, r in enumerate(rows)
                       if r.get("action") == "release" and r.get("phase") == "outcome" and r.get("outcome") == "ok")
    assert stop_idx < release_idx
    assert any(c[0] == "stop" and c[1].startswith("ayllu-gpu-") for c in sd.calls)
