from datetime import datetime, timedelta, timezone
import pytest
from hamutay.gpu_lease import ledger
from hamutay.gpu_lease.actions import Action, Ctx, run, resolve_dangling
from hamutay.gpu_lease.state import locked

NOW = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)

class Touch(Action):
    """Creates a file; complete iff it exists."""
    name = "touch"
    def __init__(self, path, explode=False):
        self.path, self.explode = path, explode
    def intent(self, ctx): return {"target": str(self.path)}
    def perform(self, ctx):
        if self.explode:
            raise RuntimeError("boom")
        self.path.write_text("x")
    def predicate(self, ctx): return self.path.exists()

def ctx(p, sd):
    return Ctx(p, sd, now=lambda: NOW, by="test")

def test_run_writes_intent_then_outcome_ok(p, sd, tmp_path):
    with locked(p):
        out = run(ctx(p, sd), Touch(tmp_path / "f"))
    rows = ledger.rows(p)
    assert [r["phase"] for r in rows] == ["intent", "outcome"]
    assert rows[0]["action_id"] == rows[1]["action_id"] == out["action_id"]
    assert rows[0]["target"].endswith("/f") and out["outcome"] == "ok" and out["by"] == "test"
    assert out["target"].endswith("/f")

def test_run_records_error_outcome_when_perform_raises(p, sd, tmp_path):
    with locked(p):
        out = run(ctx(p, sd), Touch(tmp_path / "f", explode=True))
    assert out["outcome"] == "error" and "boom" in out["detail"]["error"]

def test_dangling_intent_is_reconciled_by_predicate(p, sd, tmp_path):
    target = tmp_path / "g"
    ledger.append(p, {"record_type": "gpu_lease", "action_id": "a1", "phase": "intent",
                      "action": "touch", "target": str(target), "at": NOW.isoformat(), "by": "crashed"})
    target.write_text("x")   # the crash happened after the side effect
    with locked(p):
        done = resolve_dangling(ctx(p, sd), {"touch": lambda row: Touch(tmp_path / "g")})
    assert [d["outcome"] for d in done] == ["ok"] and done[0]["reconciled"] is True
    assert ledger.dangling_intents(ledger.rows(p)) == []

def test_dangling_intent_is_completed_by_performing_owed_work(p, sd, tmp_path):
    ledger.append(p, {"record_type": "gpu_lease", "action_id": "a2", "phase": "intent",
                      "action": "touch", "target": str(tmp_path / "h"), "at": NOW.isoformat(), "by": "crashed"})
    with locked(p):
        done = resolve_dangling(ctx(p, sd), {"touch": lambda row: Touch(tmp_path / "h")})
    # the reconciler performs the owed side effect, then evaluates
    assert done[0]["outcome"] == "ok" and (tmp_path / "h").exists()

class Noop(Action):
    """Never creates the file; complete iff it exists (it never will here)."""
    name = "noop"
    def __init__(self, path):
        self.path = path
    def intent(self, ctx): return {"target": str(self.path)}
    def perform(self, ctx): pass
    def predicate(self, ctx): return self.path.exists()

def test_dangling_intent_not_performed_when_predicate_stays_false(p, sd, tmp_path):
    target = tmp_path / "i"
    ledger.append(p, {"record_type": "gpu_lease", "action_id": "a3", "phase": "intent",
                      "action": "noop", "target": str(target), "at": NOW.isoformat(), "by": "crashed"})
    with locked(p):
        done = resolve_dangling(ctx(p, sd), {"noop": lambda row: Noop(target)})
    assert done[0]["outcome"] == "not_performed" and not target.exists()

def test_run_requires_lock():
    with pytest.raises(RuntimeError):
        run(Ctx(None, None, now=lambda: NOW, by="x"), Touch(None))

class Evil(Action):
    """An action whose intent() tries to clobber the framework's own ledger keys."""
    name = "evil-real"
    def __init__(self, path):
        self.path = path
    def intent(self, ctx): return {"action": "evil", "by": "x", "at": "y"}
    def perform(self, ctx): self.path.write_text("x")
    def predicate(self, ctx): return self.path.exists()

def test_intent_fields_cannot_overwrite_framework_keys(p, sd, tmp_path):
    with locked(p):
        out = run(ctx(p, sd), Evil(tmp_path / "f"))
    rows = ledger.rows(p)
    for row in rows:
        assert row["action"] == "evil-real"
        assert row["by"] == "test"
        assert row["at"] == NOW.isoformat()
    assert out["action"] == "evil-real" and out["by"] == "test" and out["at"] == NOW.isoformat()

class CheckServer(Action):
    """predicate() itself consults systemd, so a systemd failure surfaces as indeterminate,
    not swallowed by the default observe()."""
    name = "check-server"
    def intent(self, ctx): return {}
    def perform(self, ctx): pass
    def predicate(self, ctx):
        ctx.systemd.show(ctx.server_unit)
        return True

def test_predicate_failure_yields_indeterminate_outcome(p, sd):
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), CheckServer())
    assert out["outcome"] == "indeterminate"


from hamutay.gpu_lease.actions import (
    REGISTRY, Lease, Renew, Release, Expire, QuarantineEnter, WorkloadKilled, EnsureStopped,
    ServerStart, ReleaseForce, NotFree, is_free, resolve_tombstones,
)
from hamutay.gpu_lease.state import read_lease, read_quarantine, list_tombstones


def _lease(p, sd, holder="yupi", ttl=timedelta(hours=6)):
    with locked(p):
        act = Lease(holder, "test", ttl, None)
        out = run(ctx(p, sd), act, REGISTRY)
    return act, out

def test_lease_writes_file_and_tombstone(p, sd):
    act, out = _lease(p, sd)
    view = read_lease(p, NOW)
    assert out["outcome"] == "ok" and view.kind == "live"
    assert view.data["mutation_id"] == out["action_id"] and view.data["generation"] == 1
    assert list_tombstones(p) == [view.data["scope_unit"]]

def test_lease_refuses_foreign_live_lease(p, sd):
    _lease(p, sd, holder="yupi")
    with locked(p):
        out = run(ctx(p, sd), Lease("tq", "x", timedelta(hours=1), None), REGISTRY)
    assert out["outcome"] == "error" and "NotFree" in out["detail"]["error"]

def test_same_holder_lease_renews(p, sd):
    act, _ = _lease(p, sd)
    with locked(p):
        out = run(ctx(p, sd), Lease("yupi", "again", timedelta(hours=1), None), REGISTRY)
    v = read_lease(p, NOW).data
    assert out["outcome"] == "ok" and v["lease_id"] == act.lease_id and v["generation"] == 2
    assert v["purpose"] == "test" and v["mutation_id"] == out["action_id"]

def test_renew_reconciles_by_mutation_id(p, sd):
    # action_id must be uuid4-shaped: mutation_id round-trips through validate_lease,
    # which requires it (state.py's _is_uuid), same as every real action_id from run().
    renew_action_id = "11111111-1111-4111-8111-111111111111"
    act, _ = _lease(p, sd)
    before = read_lease(p, NOW).data
    ledger.append(p, {"action_id": renew_action_id, "phase": "intent", "action": "renew", "by": "crashed",
                      "at": NOW.isoformat(), "lease_id": act.lease_id, "ttl": "1h",
                      "generation_before": before["generation"]})
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    after = read_lease(p, NOW).data
    assert done[0]["outcome"] == "ok" and after["mutation_id"] == renew_action_id and after["generation"] == 2

def test_release_kills_scope_and_removes_tombstone_and_lease(p, sd):
    act, _ = _lease(p, sd)
    scope = read_lease(p, NOW).data["scope_unit"]
    sd.units[scope] = {"active_state": "active", "sub_state": "running", "load_state": "loaded", "invocation_id": "i"}
    with locked(p):
        out = run(ctx(p, sd), Release(act.lease_id), REGISTRY)
    assert out["outcome"] == "ok" and ("stop", scope) in sd.calls
    assert read_lease(p, NOW).kind == "absent" and list_tombstones(p) == []

def test_expire_kills_before_it_frees(p, sd):
    act, _ = _lease(p, sd, ttl=timedelta(minutes=1))
    scope = read_lease(p, NOW).data["scope_unit"]
    sd.units[scope] = {"active_state": "active", "sub_state": "running", "load_state": "loaded", "invocation_id": "i"}
    later = Ctx(p, sd, now=lambda: NOW + timedelta(minutes=5), by="hb")
    with locked(p):
        out = run(later, Expire(), REGISTRY)
    stop_idx = sd.calls.index(("stop", scope))
    assert out["outcome"] == "ok" and read_lease(p, NOW).kind == "absent" and stop_idx >= 0

def test_free_requires_no_tombstone(p, sd):
    p.tombstones.mkdir(parents=True); (p.tombstones / "ayllu-gpu-z.scope").write_text("")
    assert is_free(ctx(p, sd)) == (False, "tombstone")
    with locked(p):
        outs = resolve_tombstones(ctx(p, sd))
    assert outs[0]["action"] == "workload_killed" and outs[0]["outcome"] == "ok"
    assert is_free(ctx(p, sd)) == (True, "")

def test_workload_killed_is_indeterminate_when_show_fails(p, sd):
    p.tombstones.mkdir(parents=True); (p.tombstones / "ayllu-gpu-z.scope").write_text("")
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), WorkloadKilled("ayllu-gpu-z.scope"), REGISTRY)
    assert out["outcome"] == "indeterminate"

def test_quarantine_enter_and_identity(p, sd):
    with locked(p):
        q1 = run(ctx(p, sd), QuarantineEnter("malformed_lease", "deadbeef"), REGISTRY)
    q = read_quarantine(p)
    assert q["source_action_id"] == q1["action_id"] and q["reason"] == "malformed_lease"
    assert is_free(ctx(p, sd)) == (False, "quarantine")

def test_ensure_stopped_already_inactive_is_ok_with_flag(p, sd):
    with locked(p):
        out = run(ctx(p, sd), EnsureStopped("ep"), REGISTRY)
    assert out["outcome"] == "ok" and out["detail"]["already_inactive"] is True

def test_server_start_refuses_when_not_free(p, sd):
    _lease(p, sd)
    with locked(p):
        out = run(ctx(p, sd), ServerStart(), REGISTRY)
    assert out["outcome"] == "error" and ("start", "hamutay-llama-server.service") not in sd.calls

def test_release_force_clears_unreadable_files_via_escrow(p, sd):
    p.dir.mkdir(parents=True, exist_ok=True)
    p.lease.write_bytes(b"{garbage"); p.quarantine.write_bytes(b"also garbage")
    with locked(p):
        out = run(ctx(p, sd), ReleaseForce("tony", "test"), REGISTRY)
    assert out["outcome"] == "ok" and not p.lease.exists() and not p.quarantine.exists()
    assert not list(p.dir.glob("*.escrow-*"))
    intent = [r for r in ledger.rows(p) if r["phase"] == "intent"][-1]
    assert sorted(intent["originals_present"]) == ["lease", "quarantine"]

def test_release_force_reconciles_before_any_rename(p, sd):
    p.dir.mkdir(parents=True, exist_ok=True)
    p.lease.write_bytes(b"{garbage")
    ledger.append(p, {"action_id": "f1", "phase": "intent", "action": "release_force", "by": "tony",
                      "at": NOW.isoformat(), "originals_present": ["lease"], "tombstones": [],
                      "reason": "t"})
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    assert done[0]["outcome"] == "ok" and not p.lease.exists()


# --- Round 1 review fixes: observation failures go indeterminate, framework-wide ---

from hamutay.gpu_lease.actions import quarantine_if_indeterminate


def test_release_is_indeterminate_when_show_fails(p, sd):
    act, _ = _lease(p, sd)
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), Release(act.lease_id), REGISTRY)
    assert out["outcome"] == "indeterminate"

def test_ensure_stopped_is_indeterminate_when_show_fails(p, sd):
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), EnsureStopped("ep"), REGISTRY)
    assert out["outcome"] == "indeterminate"

def test_server_start_is_indeterminate_when_show_fails(p, sd):
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), ServerStart(), REGISTRY)
    assert out["outcome"] == "indeterminate"

def test_workload_killed_is_indeterminate_when_show_fails_framework(p, sd):
    p.tombstones.mkdir(parents=True); (p.tombstones / "ayllu-gpu-z.scope").write_text("")
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), WorkloadKilled("ayllu-gpu-z.scope"), REGISTRY)
    assert out["outcome"] == "indeterminate"

def test_quarantine_if_indeterminate_writes_quarantine_with_cause(p, sd):
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), ServerStart(), REGISTRY)
        assert out["outcome"] == "indeterminate"
        q_out = quarantine_if_indeterminate(ctx(p, sd), out)
    q = read_quarantine(p)
    assert q["cause_action_id"] == out["action_id"] == q["cause_action_id"]
    assert q["source_action_id"] == q_out["action_id"]
