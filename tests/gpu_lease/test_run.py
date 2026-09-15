from datetime import datetime, timedelta, timezone
from hamutay.gpu_lease import cli, ledger, run as runmod
from hamutay.gpu_lease.state import read_lease, list_tombstones

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
