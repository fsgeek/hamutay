import os
from datetime import timedelta

import pytest

from hamutay.gpu_lease.actions import (
    EnsureStopped,
    Expire,
    ForceStop,
    Lease,
    Release,
    ServerStart,
    WorkloadKilled,
    run,
)
from hamutay.gpu_lease.cli import main
from hamutay.gpu_lease.ledger import rows
from hamutay.gpu_lease.state import locked

from conftest import SERVER, lease_object, write_json


def _outcomes(p, action):
    return [r for r in rows(p) if r.get("phase") == "outcome" and r.get("action") == action]


def test_malformed_lease_is_quarantined_and_blocks_claim_and_start(p, ctx, sd, clock, tmp_path):
    from hamutay.events import EventStore
    from hamutay.gpu_lease.gate import LeaseGate

    p.lease.parent.mkdir(parents=True, exist_ok=True)
    bad = b'{"resource":"4090","lease_id":'
    p.lease.write_bytes(bad)
    door = tmp_path / "door"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    store = EventStore(door / "session.jsonl.events.jsonl")
    gate = LeaseGate(store, ctx)

    assert gate.claim(clock())[0] == "blocked"
    assert p.quarantine.exists()
    kind, _ = gate.observe(clock())
    assert kind == "quarantined"
    assert not any(call[0] == "start" for call in sd.calls)
    assert not _outcomes(p, "lease")


def test_unreadable_quarantine_blocks_grant_and_start(p, ctx, sd, clock, monkeypatch):
    p.quarantine.parent.mkdir(parents=True, exist_ok=True)
    p.quarantine.write_text("not-json\n")

    with locked(p):
        lease = run(ctx, Lease("holder", "purpose", timedelta(hours=1), clock() + timedelta(hours=1)))
        start = run(ctx, ServerStart())

    assert lease["outcome"] != "ok"
    assert start["outcome"] != "ok"
    assert not p.lease.exists()
    assert not any(call[0] == "start" for call in sd.calls)


@pytest.mark.parametrize("action_name", [
    "ensure_stopped", "server_stop", "force_stop", "server_start",
    "workload_killed", "release", "expire",
])
def test_systemctl_unavailable_is_indeterminate_and_quarantined(p, ctx, sd, clock, action_name):
    lease = None
    if action_name in {"release", "expire"}:
        lease = lease_object(clock, minutes=-1 if action_name == "expire" else 60)
        write_json(p.lease, lease)
        write_json(p.tombstones / lease["scope_unit"], {"scope_unit": lease["scope_unit"]})
        action = Release(lease["lease_id"]) if action_name == "release" else Expire()
    elif action_name == "workload_killed":
        scope = "ayllu-gpu-unavailable.scope"
        write_json(p.tombstones / scope, {"scope_unit": scope})
        action = WorkloadKilled(scope)
    elif action_name == "force_stop":
        action = ForceStop("episode")
    elif action_name == "server_start":
        action = ServerStart()
    else:
        action = EnsureStopped("episode")
    sd.unavailable = True

    with locked(p):
        outcome = run(ctx, action)

    assert outcome["outcome"] == "indeterminate"
    quarantine = p.quarantine.read_text()
    assert "systemctl" in quarantine or "unavailable" in quarantine or "indeterminate" in quarantine
    enters = _outcomes(p, "quarantine_enter")
    assert enters and enters[-1]["outcome"] == "ok"
    assert enters[-1].get("cause_action_id") == outcome["action_id"] or outcome["action_id"] in p.quarantine.read_text()


def test_nothing_claims_or_starts_under_quarantine(p, ctx, sd, clock, tmp_path):
    from hamutay.events import EventStore
    from hamutay.gpu_lease.gate import LeaseGate

    write_json(p.quarantine, {
        "quarantine_id": "q-validation", "reason": "unreadable",
        "source_action_id": "source-validation", "observed_digest": "", "at": clock().isoformat(),
    })
    door = tmp_path / "door"
    door.mkdir()
    write_json(door / "door.json", {"gpu_lease": "4090"})
    gate = LeaseGate(EventStore(door / "session.jsonl.events.jsonl"), ctx)

    assert gate.claim(clock())[0] == "blocked"
    assert gate.observe(clock())["state"] == "resting"
    assert not any(call[0] == "start" for call in sd.calls)


def test_release_force_clears_quarantine_and_ledgers_actor_and_reason(p, sd, clock):
    write_json(p.quarantine, {
        "quarantine_id": "q-validation", "reason": "unreadable",
        "source_action_id": "source-validation", "observed_digest": "", "at": clock().isoformat(),
    })

    code = main(["release", "--force", "--by", "tony", "--reason", "examined state"], systemd=sd, now=clock)
    outcome = _outcomes(p, "release_force")[-1]

    assert code == 0
    assert not p.quarantine.exists()
    assert outcome["outcome"] == "ok"
    assert outcome["by"] == "tony"
    assert outcome["reason"] == "examined state"
