import json
from datetime import datetime, timezone
import pytest
from hamutay.events import EventStore, LeaseGateRequired, build_inbound_event, run_next_event, run_pending_events
from hamutay.gpu_lease.actions import Ctx, REGISTRY, Lease, run as run_action
from hamutay.gpu_lease.gate import LeaseGate
from hamutay.gpu_lease.state import paths, locked
from hamutay.gpu_lease import ledger
from datetime import timedelta

NOW = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)

class FakeSystemd:  # minimal copy of tests/gpu_lease/conftest.py's
    def __init__(self): self.units = {}; self.calls = []; self.fail_show = False
    def show(self, unit):
        return dict(self.units.get(unit, {"active_state": "inactive", "sub_state": "dead", "load_state": "not-found", "invocation_id": ""}))
    def start(self, unit): self.calls.append(("start", unit)); self.units[unit] = {"active_state": "active", "sub_state": "running", "load_state": "loaded", "invocation_id": "i1"}; return 0, ""
    def stop(self, unit): self.calls.append(("stop", unit)); self.units.setdefault(unit, {}).update(active_state="inactive", sub_state="dead", load_state="loaded"); return 0, ""
    def kill(self, unit, signal="TERM"): return 0, ""

@pytest.fixture
def bound(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    door = tmp_path / "community" / "qwen"; door.mkdir(parents=True)
    (door / "door.json").write_text(json.dumps({"gpu_lease": "4090"}))
    store = EventStore(door / "session.jsonl.events.jsonl")
    store.append(build_inbound_event(purpose="hello", sender="t"))
    return store, paths(), FakeSystemd()

def test_bound_store_refuses_unguarded_claim(bound):
    store, _, _ = bound
    assert store.lease_binding == "4090"
    with pytest.raises(LeaseGateRequired):
        store.claim_next_pending(now=NOW)
    with pytest.raises(LeaseGateRequired):
        run_next_event(None, store, now=NOW)

def test_unbound_store_unchanged(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    store.append(build_inbound_event(purpose="hello", sender="t"))
    assert store.claim_next_pending(now=NOW) is not None

def test_gate_claims_when_free_and_blocks_when_leased(bound):
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx)
    status, payload = gate.claim(NOW)
    assert status == "claimed" and payload[1]["status"] == "running"
    store.append(build_inbound_event(purpose="again", sender="t"))
    with locked(p):
        run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    status, payload = gate.claim(NOW)
    assert status == "blocked" and payload["kind"] == "lease"

def test_run_pending_events_stops_on_lease_blocked(bound):
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    batch = run_pending_events(None, store, limit=3, now=NOW, claim_gate=LeaseGate(store, ctx))
    assert batch["ran"] == 0 and batch["results"][0]["status"] == "lease_blocked"

def test_dangling_release_of_expired_lease_does_not_raise(bound):
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        outcome = run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    lease_id = outcome["lease_id"]
    # A release intent was written but never reconciled to an outcome: it is
    # dangling. resolve_dangling() will reconcile it (the scope is already
    # dead under FakeSystemd), leaving no lease at all -- claim() must not
    # let Expire()'s own NotFree escape when the lease it expected is gone.
    ledger.append(p, {"action_id": "dangling-release-1", "phase": "intent", "action": "release",
                       "by": ctx.by, "at": NOW.isoformat(), "lease_id": lease_id,
                       "generation_before": 1, "scope_unit": outcome["scope_unit"],
                       "episode_id": lease_id})
    later = NOW + timedelta(hours=2)  # past the 1h ttl: lease is expired
    ctx_later = Ctx(p, sd, now=lambda: later, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx_later)
    status, payload = gate.claim(later)  # must not raise NotFree
    assert status in ("none", "claimed")

def test_expire_not_free_race_does_not_raise(bound, monkeypatch):
    """Directly exercises the ruling: if the lease stops being expired between
    gate.claim()'s expired-check and Expire().intent()'s own re-read (a dangling
    expire/release reconciled concurrently, or the clock advancing), intent()
    raises NotFree. claim() must swallow it, not propagate it, and evaluate
    is_free() on the now-current state."""
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    later = NOW + timedelta(hours=2)
    ctx_later = Ctx(p, sd, now=lambda: later, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx_later)

    import hamutay.gpu_lease.gate as gate_module

    def _raises_not_free(self, ctx):
        raise gate_module.NotFree("lease no longer expired")

    monkeypatch.setattr(gate_module.Expire, "intent", _raises_not_free)
    status, payload = gate.claim(later)  # must not raise
    assert status in ("none", "claimed", "blocked")

def test_malformed_door_json_raises_lease_gate_required(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    door = tmp_path / "community" / "broken"; door.mkdir(parents=True)
    (door / "door.json").write_text('{"gpu_lease":')
    with pytest.raises(LeaseGateRequired):
        EventStore(door / "session.jsonl.events.jsonl")

def test_empty_gpu_lease_is_unbound(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    door = tmp_path / "community" / "empty"; door.mkdir(parents=True)
    (door / "door.json").write_text(json.dumps({"gpu_lease": ""}))
    store = EventStore(door / "session.jsonl.events.jsonl")
    assert store.lease_binding is None
