from datetime import datetime, timedelta, timezone
from hamutay.gpu_lease import cli, ledger, run as runmod
from hamutay.gpu_lease.actions import Ctx, REGISTRY, Lease, run as run_action
from hamutay.gpu_lease.state import locked, read_lease, read_quarantine, list_tombstones, scope_unit_for

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

def test_run_lease_replaced_between_unlocked_wait_and_locked_recheck_no_hang(p, sd, monkeypatch, capsys):
    # CRITICAL 1 regression: wait_ready succeeds UNLOCKED, then (before the LOCKED
    # re-check inside the launch block runs) the lease is invalidated. The launcher
    # must never be reached, and the wrapper must exit 3 promptly rather than hang
    # self-deadlocked on 4090.lock (the old bug: _release called from inside a
    # `with locked(...)` block already held by supervise itself).
    #
    # This has to land the invalidation strictly between the unlocked wait_ready's
    # success and the locked re-check's read, which the sleep hook can't target
    # directly (the two wait_ready calls happen back-to-back with no sleep() in
    # between on the success path). So we wrap run.wait_ready itself: the first
    # call made *without* already_locked (the unlocked one, in the wait loop) acks
    # the stop, lets wait_ready report ok, and then — after it has already decided
    # ok=True but before returning to supervise — unlinks the lease file. The next
    # call (already_locked=True, inside the launch block) then sees no lease and
    # must refuse.
    clock = Clock()
    launcher_calls = []
    def launcher(scope, cmd):
        launcher_calls.append((scope, cmd))
        return FakeProc(sd, scope, rc=0, lifetime=3)

    def sleep(s):
        clock.sleep(s)

    real_wait_ready = runmod.wait_ready
    state = {"acked": False, "pulled": False}

    def wrapped_wait_ready(ctx, lease_id, min_remaining, *, already_locked=False):
        if not state["acked"]:
            v = read_lease(p, clock.now())
            if v.kind == "live":
                _ack(p, sd, v.data["lease_id"])
                state["acked"] = True
        ok, why = real_wait_ready(ctx, lease_id, min_remaining, already_locked=already_locked)
        if ok and not already_locked and not state["pulled"]:
            # the unlocked wait_ready in the wait loop just decided ok=True;
            # invalidate the lease before returning it, so the locked re-check
            # in the launch block (the code CRITICAL 1 fixed) sees it gone
            state["pulled"] = True
            p.lease.unlink(missing_ok=True)
        return ok, why

    monkeypatch.setattr(runmod, "wait_ready", wrapped_wait_ready)

    start = clock.now()
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "true"],
                  systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)
    # bounded-clock proof of no hang: the fake clock only advances inside sleep(),
    # which a real deadlock on flock would never return from, so reaching this
    # assertion at all (under pytest's default run, no external timeout needed)
    # together with a small clock delta is the "didn't hang" evidence.
    assert clock.now() - start < timedelta(minutes=1)
    assert rc == 3
    assert launcher_calls == []
    assert "launch refused" in capsys.readouterr().err

def test_run_wait_loop_does_not_release_lease_replaced_by_another_holder(p, sd, capsys):
    # IMPORTANT 5: a wait-loop failure must not release unconditionally. Simulate
    # another holder taking the resource out from under us mid-wait (our lease
    # expires or is force-cleared and someone else leases it) by directly unlinking
    # our lease and writing a fresh one for "intruder" via the real Lease action,
    # all before our own wait_ready ever succeeds. supervise must give up (exit 3)
    # without touching the intruder's lease: no release row naming our lease_id,
    # the intruder's lease still present and live, and a "no longer ours" message.
    clock = Clock()
    our_lease_id = {"v": None}
    intruder_lease_id = {"v": None}

    def launcher(scope, cmd):
        raise AssertionError("must not launch: the lease was replaced mid-wait")

    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and our_lease_id["v"] is None:
            our_lease_id["v"] = v.data["lease_id"]
            # never ack ensure_stopped for us: wait_ready keeps failing, so the
            # wait loop keeps polling via tick() until we intervene below.
            # Simulate a clean hand-off (force-clear, then a fresh lease): drop
            # both our lease file and our tombstone so the resource is FREE.
            p.lease.unlink(missing_ok=True)
            tomb = p.tombstones / scope_unit_for(our_lease_id["v"])
            tomb.unlink(missing_ok=True)
            ctx = Ctx(p, sd, now=clock.now, by="intruder")
            with locked(p):
                act = Lease("intruder", "other work", timedelta(minutes=15), None)
                out = run_action(ctx, act, REGISTRY)
            assert out["outcome"] == "ok"
            intruder_lease_id["v"] = act.lease_id

    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--wait-timeout", "1m",
                  "--", "true"], systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)

    assert rc == 3
    assert our_lease_id["v"] is not None and intruder_lease_id["v"] is not None
    # no release row for our lease_id
    assert not any(r.get("action") == "release" and r.get("lease_id") == our_lease_id["v"]
                  for r in ledger.rows(p))
    # the intruder's lease is untouched
    view = read_lease(p, clock.now())
    assert view.kind == "live" and view.data["lease_id"] == intruder_lease_id["v"]
    assert "no longer ours" in capsys.readouterr().err

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


def test_run_expires_a_stale_lease_instead_of_refusing(p, sd):
    """A holder that died leaves an expired lease. It is not FREE until an
    `expire` action kills its scope and removes it — `lease` does that, but
    `run` did not, so every subsequent run refused with exit 2 until a human
    intervened."""
    clock = Clock()
    # a lease from a dead holder, already past its expiry by the time run starts
    with locked(p):
        dead = Lease("ghost", "died", timedelta(minutes=20), None)
        run_action(Ctx(p, sd, now=lambda: START, by="t"), dead, REGISTRY)
    clock.t = START + timedelta(hours=2)
    assert read_lease(p, clock.now()).kind == "expired"

    procs = []
    def launcher(scope, cmd):
        pr = FakeProc(sd, scope, rc=0, lifetime=3); procs.append(pr); return pr
    def sleep(s):
        clock.sleep(s)
        v = read_lease(p, clock.now())
        if v.kind == "live" and v.data["holder"] == "yupi" and not any(
                r.get("action") == "ensure_stopped" and r.get("episode_id") == v.data["lease_id"]
                for r in ledger.rows(p)):
            _ack(p, sd, v.data["lease_id"])
    rc = cli.main(["run", "--holder", "yupi", "--purpose", "t", "--ttl", "15m", "--", "true"],
                  systemd=sd, now=clock.now, launcher=launcher, sleep=sleep)
    assert rc == 0 and procs
    assert any(r.get("action") == "expire" and r.get("outcome") == "ok" for r in ledger.rows(p))
    assert read_lease(p, clock.now()).kind == "absent" and list_tombstones(p) == []
