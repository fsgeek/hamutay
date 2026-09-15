import json
from datetime import datetime, timezone
import pytest
from hamutay.events import EventStore, LeaseGateRequired, build_inbound_event, run_next_event, run_pending_events
from hamutay.gpu_lease.actions import Ctx, REGISTRY, Lease, run as run_action
from hamutay.gpu_lease.gate import LeaseGate
from hamutay.gpu_lease.state import paths, locked
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
