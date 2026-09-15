import json
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from hamutay.gpu_lease.actions import EnsureStopped, Expire, Lease, ServerStart, run
from hamutay.gpu_lease.cli import main
from hamutay.gpu_lease.gate import LeaseGate
from hamutay.gpu_lease.ledger import rows
from hamutay.gpu_lease.run import supervise
from hamutay.gpu_lease.state import locked

from conftest import SERVER, append_jsonl, lease_object, read_jsonl, write_json


def _door(tmp_path, p, lease):
    from hamutay.events import EventStore

    door = tmp_path / "door"
    door.mkdir()
    event_log = door / "session.jsonl.events.jsonl"
    write_json(door / "door.json", {"gpu_lease": "4090"})
    p.door.parent.mkdir(parents=True, exist_ok=True)
    p.door.write_text(str(door) + "\n")
    write_json(p.lease, lease)
    return door, event_log, EventStore(event_log)


def test_live_tombstone_prevents_lease_grant(p, ctx, sd, clock):
    scope = "ayllu-gpu-still-running.scope"
    write_json(p.tombstones / scope, {"scope_unit": scope})
    sd.units[scope] = sd.active()

    with locked(p):
        outcome = run(ctx, Lease("new-holder", "new-work", timedelta(hours=1), clock() + timedelta(hours=1)))

    assert outcome["outcome"] != "ok"
    assert not p.lease.exists()
    assert not any(call == ("start", SERVER) for call in sd.calls)


def test_server_start_never_occurs_while_tombstone_still_exists(p, ctx, sd):
    scope = "ayllu-gpu-orphan.scope"
    tombstone = p.tombstones / scope
    write_json(tombstone, {"scope_unit": scope})
    sd.units[scope] = sd.active()
    sd.units[SERVER] = sd.inactive()

    sd.before_start = lambda unit: pytest.fail("server started before tombstone resolution") if tombstone.exists() else None
    with locked(p):
        outcome = run(ctx, ServerStart())

    assert outcome["outcome"] == "ok"
    assert not tombstone.exists()
    assert ("stop", scope) in sd.calls
    assert ("start", SERVER) in sd.calls


def test_expiry_kills_scope_before_removing_lease(p, ctx, sd, clock):
    lease = lease_object(clock, minutes=-1)
    scope = lease["scope_unit"]
    tombstone = p.tombstones / scope
    write_json(p.lease, lease)
    write_json(tombstone, {"scope_unit": scope})
    sd.units[scope] = sd.active()
    observed = []

    def before_stop(unit):
        if unit == scope:
            observed.append((p.lease.exists(), tombstone.exists()))

    sd.before_stop = before_stop
    with locked(p):
        outcome = run(ctx, Expire())

    assert observed == [(True, True)]
    assert outcome["outcome"] == "ok"
    assert not p.lease.exists()
    assert not tombstone.exists()


def test_run_refuses_launch_with_less_than_six_minutes_remaining(p, ctx, sd, clock):
    lease = lease_object(clock, minutes=5)
    write_json(p.lease, lease)
    write_json(p.tombstones / lease["scope_unit"], {"scope_unit": lease["scope_unit"]})
    sd.units[SERVER] = sd.inactive()
    launched = []
    args = SimpleNamespace(
        holder=lease["holder"], purpose=lease["purpose"], ttl=timedelta(minutes=15),
        expected_until=None, wait_timeout=0, command=["validation-workload"],
    )

    code = supervise(args, ctx, launcher=lambda *a: launched.append(a), sleep=lambda _: None)

    assert code != 0
    assert launched == []


def test_heartbeat_records_rest_before_ensure_stopped(p, sd, clock, tmp_path):
    lease = lease_object(clock)
    door, event_log, store = _door(tmp_path, p, lease)
    sd.units[SERVER] = sd.active()
    stop_observation = []

    def before_stop(unit):
        if unit == SERVER:
            records = read_jsonl(event_log)
            rests = [r for r in records if r.get("record_type") == "heartbeat_status"
                     and r.get("status") == "resting" and r.get("reason") == "substrate_lent"]
            stop_observation.append(rests[-1]["created_at"])

    sd.before_stop = before_stop
    gate = LeaseGate(store, __import__("hamutay.gpu_lease.actions", fromlist=["Ctx"]).Ctx(p, sd, clock, "heartbeat:qwen"))
    result = gate.observe(clock())
    outcome = [r for r in rows(p) if r.get("phase") == "outcome" and r.get("action") == "ensure_stopped"][-1]

    assert result["state"] == "resting"
    assert stop_observation
    assert stop_observation[0] <= outcome["at"]


def test_force_stop_records_rest_before_ledger_outcome(p, sd, clock, tmp_path):
    lease = lease_object(clock)
    door, event_log, _ = _door(tmp_path, p, lease)
    sd.units[SERVER] = sd.active()
    observations = []

    def before_stop(unit):
        if unit == SERVER:
            observations.append(read_jsonl(event_log))

    sd.before_stop = before_stop
    code = main(
        ["force-stop", "--lease-id", lease["lease_id"], "--by", "operator", "--reason", "validation"],
        systemd=sd, now=clock,
    )
    outcome = [r for r in rows(p) if r.get("phase") == "outcome" and r.get("action") == "force_stop"][-1]
    rest = [r for r in observations[0] if r.get("record_type") == "heartbeat_status"
            and r.get("reason") == "substrate_lent"][-1]

    assert code == 0
    assert rest["created_at"] <= outcome["at"]
