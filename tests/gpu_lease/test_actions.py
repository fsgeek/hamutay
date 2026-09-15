from datetime import datetime, timedelta, timezone
import pytest
from hamutay.gpu_lease import ledger
from hamutay.gpu_lease.actions import Action, Ctx, run, resolve_dangling
from hamutay.gpu_lease.state import locked
from conftest import StubbornSystemd

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
    """A renew whose write LANDED before the crash reconciles to ok: the
    predicate (mutation_id == this action_id) already holds, so the reconciler
    only has to read it. This is the evaluation-only path succeeding."""
    renew_action_id = "11111111-1111-4111-8111-111111111111"
    act, _ = _lease(p, sd)
    before = read_lease(p, NOW).data
    ledger.append(p, {"action_id": renew_action_id, "phase": "intent", "action": "renew", "by": "crashed",
                      "at": NOW.isoformat(), "lease_id": act.lease_id, "ttl": "1h",
                      "generation_before": before["generation"]})
    # the write landed: the lease already carries this mutation_id
    with locked(p):
        run(ctx(p, sd), Renew(act.lease_id, timedelta(hours=1)))
    landed = dict(read_lease(p, NOW).data)
    landed["mutation_id"] = renew_action_id
    from hamutay.gpu_lease.state import write_atomic
    write_atomic(p.lease, landed)
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    after = read_lease(p, NOW).data
    assert done[0]["outcome"] == "ok" and after["mutation_id"] == renew_action_id


# --- I6: lease and renew reconcile by evaluation only ---

def test_dangling_lease_reconciles_to_not_performed_and_writes_no_lease(p, sd):
    """A grant to a dead caller is never owed: the reconciler evaluates the
    predicate and records not_performed rather than handing the GPU to a
    process that is no longer there to use or release it."""
    lease_action_id = "33333333-3333-4333-8333-333333333333"
    lease_id = "44444444-4444-4444-8444-444444444444"
    ledger.append(p, {"action_id": lease_action_id, "phase": "intent", "action": "lease", "by": "crashed",
                      "at": NOW.isoformat(), "holder": "yupi", "purpose": "t", "ttl_seconds": 3600,
                      "lease_id": lease_id, "scope_unit": f"ayllu-gpu-{lease_id}.scope",
                      "generation_before": 0, "episode_id": lease_id, "expected_until": None})
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    assert done[0]["outcome"] == "not_performed" and done[0]["reconciled"] is True
    assert read_lease(p, NOW).kind == "absent"
    assert list_tombstones(p) == []
    assert is_free(ctx(p, sd))[0] is True


def test_dangling_renew_whose_write_never_landed_reconciles_to_not_performed(p, sd):
    renew_action_id = "55555555-5555-4555-8555-555555555555"
    act, _ = _lease(p, sd)
    before = read_lease(p, NOW).data
    ledger.append(p, {"action_id": renew_action_id, "phase": "intent", "action": "renew", "by": "crashed",
                      "at": NOW.isoformat(), "lease_id": act.lease_id, "ttl": "1h",
                      "generation_before": before["generation"]})
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    after = read_lease(p, NOW).data
    assert done[0]["outcome"] == "not_performed"
    # the old mutation_id and generation survive untouched
    assert after["mutation_id"] == before["mutation_id"] and after["generation"] == before["generation"]
    assert after["expires_at"] == before["expires_at"]

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
    intent = [r for r in ledger.rows(p)
              if r["phase"] == "intent" and r["action"] == "release_force"][-1]
    assert sorted(intent["originals_present"]) == ["lease", "quarantine"]
    # An unreadable lease has no id to name: episode_id is present but None.
    assert intent["episode_id"] is None and out["episode_id"] is None

def test_release_force_names_the_episode_when_the_lease_is_readable(p, sd):
    """Boot reconciliation dates a forced release's closing record from the
    ledger's episode_id, so the forced release must carry one."""
    act, _ = _lease(p, sd)
    with locked(p):
        out = run(ctx(p, sd), ReleaseForce("tony", "test"), REGISTRY)
    assert out["outcome"] == "ok"
    # perform() runs nested workload_killed actions that append their own
    # intents, so select this action's row rather than the last one.
    intent = [r for r in ledger.rows(p)
              if r["phase"] == "intent" and r["action"] == "release_force"][-1]
    assert intent["episode_id"] == act.lease_id and out["episode_id"] == act.lease_id

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

def test_dangling_workload_killed_reconciles_to_indeterminate_when_show_fails(p, sd):
    ledger.append(p, {"action_id": "22222222-2222-4222-8222-222222222222", "phase": "intent",
                      "action": "workload_killed", "by": "crashed", "at": NOW.isoformat(),
                      "scope_unit": "ayllu-gpu-z.scope"})
    sd.fail_show = True
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    assert done[0]["outcome"] == "indeterminate" and done[0]["detail"]["error"]


# --- I5: an indeterminate outcome is a dangling condition, fenced by resolve_dangling ---

def test_resolve_dangling_quarantines_an_unfenced_indeterminate(p, sd):
    """A crash between the indeterminate outcome and its quarantine_enter leaves
    the resource unfenced. resolve_dangling finds the row and fences it."""
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), ServerStart(), REGISTRY)
    assert out["outcome"] == "indeterminate"
    assert read_quarantine(p) is None          # nobody quarantined it
    sd.fail_show = False
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    q = read_quarantine(p)
    assert q is not None and q["cause_action_id"] == out["action_id"]
    assert [d["action"] for d in done] == ["quarantine_enter"]
    # a second pass appends nothing: the resource is already fenced
    rows_before = len(ledger.rows(p))
    with locked(p):
        again = resolve_dangling(ctx(p, sd), REGISTRY)
    assert again == [] and len(ledger.rows(p)) == rows_before
    assert read_quarantine(p)["quarantine_id"] == q["quarantine_id"]


def test_an_indeterminate_already_named_by_a_quarantine_is_not_refenced(p, sd):
    sd.fail_show = True
    with locked(p):
        out = run(ctx(p, sd), ServerStart(), REGISTRY)
        quarantine_if_indeterminate(ctx(p, sd), out)
    sd.fail_show = False
    q_before = read_quarantine(p)
    rows_before = len(ledger.rows(p))
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    assert done == [] and len(ledger.rows(p)) == rows_before
    assert read_quarantine(p) == q_before


def test_a_second_indeterminate_does_not_stack_a_second_quarantine(p, sd):
    """Only one quarantine file can exist; the first fence is the one that
    counts. A later unfenced indeterminate is skipped, not stacked."""
    sd.fail_show = True
    with locked(p):
        first = run(ctx(p, sd), ServerStart(), REGISTRY)
        second = run(ctx(p, sd), EnsureStopped("ep"))
    assert first["outcome"] == second["outcome"] == "indeterminate"
    sd.fail_show = False
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    assert len(done) == 1 and read_quarantine(p)["cause_action_id"] == first["action_id"]
    with locked(p):
        assert resolve_dangling(ctx(p, sd), REGISTRY) == []


# --- I8: release --force must not publish FREE over a scope that will not die ---

def test_release_force_quarantines_an_unkillable_scope_and_keeps_the_originals(p, sd):
    act, _ = _lease(p, sd)
    scope = read_lease(p, NOW).data["scope_unit"]
    stubborn = StubbornSystemd(scope)
    with locked(p):
        out = run(ctx(p, stubborn), ReleaseForce("tony", "stuck"), REGISTRY)
    assert out["outcome"] != "ok"
    assert "unkillable" in out["detail"]["error"]
    # the originals stay exactly where they were: nothing is published as FREE
    assert p.lease.exists() and read_lease(p, NOW).data["lease_id"] == act.lease_id
    assert list_tombstones(p) == [scope]
    q = read_quarantine(p)
    assert q is not None and q["reason"] == "scope_unkillable"
    assert is_free(ctx(p, stubborn))[0] is False


# --- Follow-up 1: the unfenced-indeterminate scan runs BEFORE the dangling-intent pass ---

def test_unfenced_indeterminate_is_fenced_before_a_dangling_server_start_reconciles(p, sd):
    """A dangling server_start must never start the server one sweep before an
    unfenced indeterminate gets its quarantine. resolve_dangling must fence
    first, then reconcile: the reconciled server_start's perform() then raises
    NotFree under the fresh quarantine, and the outcome must not be ok."""
    indeterminate_action_id = "66666666-6666-4666-8666-666666666666"
    ledger.append(p, {"action_id": indeterminate_action_id, "phase": "intent", "action": "server_start",
                      "by": "crashed", "at": NOW.isoformat()})
    ledger.append(p, {"action_id": indeterminate_action_id, "phase": "outcome", "action": "server_start",
                      "by": "crashed", "at": NOW.isoformat(), "outcome": "indeterminate",
                      "observed": {}, "detail": {"error": "SystemdUnavailable: fake"}})
    server_start_action_id = "77777777-7777-4777-8777-777777777777"
    ledger.append(p, {"action_id": server_start_action_id, "phase": "intent", "action": "server_start",
                      "by": "crashed", "at": NOW.isoformat()})
    sd.units["hamutay-llama-server.service"] = {"active_state": "inactive", "sub_state": "dead",
                                                 "load_state": "loaded", "invocation_id": ""}
    with locked(p):
        done = resolve_dangling(ctx(p, sd), REGISTRY)
    assert read_quarantine(p) is not None
    assert ("start", "hamutay-llama-server.service") not in sd.calls
    reconciled = [d for d in done if d["action_id"] == server_start_action_id]
    assert reconciled and reconciled[0]["outcome"] != "ok"
