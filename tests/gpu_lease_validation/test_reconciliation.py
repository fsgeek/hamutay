from datetime import timedelta
from uuid import uuid4

import pytest

from hamutay.gpu_lease import actions
from hamutay.gpu_lease.actions import (
    EnsureStopped,
    Expire,
    ForceStop,
    Lease,
    QuarantineEnter,
    Release,
    ReleaseForce,
    Renew,
    ServerStart,
    WorkloadKilled,
    resolve_dangling,
)
from hamutay.gpu_lease.ledger import append, rows
from hamutay.gpu_lease.state import locked, write_atomic

from .conftest import SERVER, lease_object, write_json


REGISTRY = dict(actions.REGISTRY)


def hand_write_intent(ctx, action, *, action_name=None):
    """Write the intent boundary without invoking actions.run or any side effect."""
    action_id = str(uuid4())
    row = {
        "record_type": "gpu_lease",
        "phase": "intent",
        "action_id": action_id,
        "action": action_name or action.name,
        "by": ctx.by,
        "at": ctx.now().isoformat(),
        **action.intent(ctx),
    }
    append(ctx.paths, row)
    return row


def reconcile(ctx):
    return resolve_dangling(ctx, REGISTRY)


def outcome_for(p, intent):
    return [r for r in rows(p) if r.get("phase") == "outcome" and r.get("action_id") == intent["action_id"]][-1]


def lease_from_intent(intent, clock):
    return {
        "resource": "4090",
        "lease_id": intent["lease_id"],
        "generation": intent.get("generation_before", 0) + 1,
        "mutation_id": intent["action_id"],
        "holder": intent["holder"],
        "purpose": intent["purpose"],
        "since": clock().isoformat(),
        "expires_at": (clock() + timedelta(seconds=int(intent["ttl_seconds"]))).isoformat(),
        "expected_until": intent["expected_until"],
        "scope_unit": intent["scope_unit"],
    }


def test_dangling_lease_is_evaluation_only_when_no_write_landed(p, ctx, clock):
    with locked(p):
        intent = hand_write_intent(ctx, Lease("holder", "purpose", timedelta(hours=1), clock() + timedelta(hours=1)))
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "not_performed"
    assert not p.lease.exists()
    assert not (p.tombstones / intent["scope_unit"]).exists()


def test_dangling_lease_with_only_file_is_not_completed_or_repaired(p, ctx, clock):
    with locked(p):
        intent = hand_write_intent(ctx, Lease("holder", "purpose", timedelta(hours=1), clock() + timedelta(hours=1)))
        write_json(p.lease, lease_from_intent(intent, clock))
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "not_performed"
    assert p.lease.exists()
    assert not (p.tombstones / intent["scope_unit"]).exists()


def test_dangling_lease_with_both_writes_is_completed_by_evaluation(p, ctx, clock):
    with locked(p):
        intent = hand_write_intent(ctx, Lease("holder", "purpose", timedelta(hours=1), clock() + timedelta(hours=1)))
        write_json(p.lease, lease_from_intent(intent, clock))
        write_json(p.tombstones / intent["scope_unit"], {"scope_unit": intent["scope_unit"]})
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"


@pytest.mark.parametrize("landed", [False, True])
def test_dangling_renew_is_evaluation_only(p, ctx, clock, landed):
    original = lease_object(clock)
    write_json(p.lease, original)
    before = p.lease.read_bytes()
    with locked(p):
        intent = hand_write_intent(ctx, Renew(original["lease_id"], timedelta(hours=2)))
        if landed:
            renewed = dict(original)
            renewed.update(
                mutation_id=intent["action_id"],
                generation=original["generation"] + 1,
                expires_at=(clock() + timedelta(hours=2)).isoformat(),
            )
            write_json(p.lease, renewed)
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == ("ok" if landed else "not_performed")
    if not landed:
        assert p.lease.read_bytes() == before


@pytest.mark.parametrize("boundary", ["none", "dead", "tombstone_removed", "lease_removed"])
@pytest.mark.parametrize("kind", ["release", "expire"])
def test_release_and_expire_reconcile_every_boundary(p, ctx, sd, clock, boundary, kind):
    lease = lease_object(clock, minutes=-1 if kind == "expire" else 60)
    scope = lease["scope_unit"]
    tombstone = p.tombstones / scope
    write_json(p.lease, lease)
    write_json(tombstone, {"scope_unit": scope})
    sd.units[scope] = sd.active()
    action = Release(lease["lease_id"]) if kind == "release" else Expire()
    with locked(p):
        intent = hand_write_intent(ctx, action)
        if boundary in {"dead", "tombstone_removed", "lease_removed"}:
            sd.units[scope] = sd.inactive(load_state="not-found")
        if boundary in {"tombstone_removed", "lease_removed"}:
            tombstone.unlink()
        if boundary == "lease_removed":
            p.lease.unlink()
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"
    assert not p.lease.exists()
    assert not tombstone.exists()
    assert sd.units[scope]["active_state"] in {"inactive", "failed"}


@pytest.mark.parametrize("boundary", ["none", "quarantine_escrowed", "both_escrowed", "one_deleted"])
def test_release_force_reconciles_every_file_boundary(p, ctx, clock, boundary):
    write_json(p.lease, lease_object(clock))
    write_json(p.quarantine, {
        "quarantine_id": "q", "reason": "unreadable", "source_action_id": "s",
        "observed_digest": "", "at": clock().isoformat(),
    })
    with locked(p):
        intent = hand_write_intent(ctx, ReleaseForce("operator", "validation"))
        q_escrow = p.quarantine.with_name(p.quarantine.name + ".escrow-" + intent["action_id"])
        l_escrow = p.lease.with_name(p.lease.name + ".escrow-" + intent["action_id"])
        if boundary in {"quarantine_escrowed", "both_escrowed", "one_deleted"}:
            p.quarantine.rename(q_escrow)
        if boundary in {"both_escrowed", "one_deleted"}:
            p.lease.rename(l_escrow)
        if boundary == "one_deleted":
            q_escrow.unlink()
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"
    assert not p.lease.exists() and not p.quarantine.exists()
    assert not l_escrow.exists() and not q_escrow.exists()


@pytest.mark.parametrize("landed", [False, True])
def test_quarantine_enter_reconciles_before_and_after_rename(p, ctx, clock, landed):
    with locked(p):
        intent = hand_write_intent(ctx, QuarantineEnter("malformed_lease", "digest"))
        if landed:
            write_json(p.quarantine, {
                "quarantine_id": "q", "reason": "malformed_lease",
                "source_action_id": intent["action_id"], "observed_digest": "digest",
                "at": clock().isoformat(),
            })
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"
    assert intent["action_id"] in p.quarantine.read_text()


@pytest.mark.parametrize(
    "action,action_name",
    [
        (EnsureStopped("episode"), "ensure_stopped"),
        (EnsureStopped("episode"), "server_stop"),
        (ForceStop("episode"), "force_stop"),
    ],
)
@pytest.mark.parametrize("already_done", [False, True])
def test_stop_actions_reconcile_both_systemd_boundaries(p, ctx, sd, action, action_name, already_done):
    sd.units[SERVER] = sd.inactive() if already_done else sd.active()
    with locked(p):
        intent = hand_write_intent(ctx, action, action_name=action_name)
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"
    assert sd.units[SERVER]["active_state"] in {"inactive", "failed"}


@pytest.mark.parametrize("already_started", [False, True])
def test_server_start_reconciles_before_and_after_start(p, ctx, sd, already_started):
    sd.units[SERVER] = sd.active() if already_started else sd.inactive()
    with locked(p):
        intent = hand_write_intent(ctx, ServerStart())
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"
    assert sd.units[SERVER]["active_state"] in {"active", "activating"}


@pytest.mark.parametrize("boundary", ["none", "dead", "tombstone_removed"])
def test_workload_killed_reconciles_every_boundary(p, ctx, sd, boundary):
    scope = "ayllu-gpu-reconcile.scope"
    tombstone = p.tombstones / scope
    write_json(tombstone, {"scope_unit": scope})
    sd.units[scope] = sd.active()
    with locked(p):
        intent = hand_write_intent(ctx, WorkloadKilled(scope))
        if boundary in {"dead", "tombstone_removed"}:
            sd.units[scope] = sd.inactive(load_state="not-found")
        if boundary == "tombstone_removed":
            tombstone.unlink()
        reconcile(ctx)

    assert outcome_for(p, intent)["outcome"] == "ok"
    assert not tombstone.exists()
    assert sd.units[scope]["active_state"] in {"inactive", "failed"}
