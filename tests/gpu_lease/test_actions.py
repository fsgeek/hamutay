from datetime import datetime, timezone
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
