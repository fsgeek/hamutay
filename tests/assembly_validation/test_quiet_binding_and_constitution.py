from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

import pytest

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.convene import ConveneRefused, convene
from hamutay.assembly.records import reduce
from hamutay.events import EventStore, build_inbound_event, build_quiet_declaration
from hamutay.heartbeat import build_constitution
from hamutay.taste_open import _build_messages
from hamutay.tools.schemas import ASSEMBLY_CONSTITUTION_CLAUSE

from .conftest import T0, append_jsonl, convene_question, member_document, write_members


def _store_with_quiet(path, *, until: str | None) -> EventStore:
    store = EventStore(path)
    prior = build_inbound_event(purpose="ordinary wake", sender="test", label="prior")
    append_jsonl(path, prior)
    claimed = store.claim_next_pending(now=T0)
    assert claimed is not None
    event, running = claimed
    record_id = str(uuid4())
    store.append_completed(
        event=event,
        run_id=running["run_id"],
        wake_cycle=1,
        result_record_id=record_id,
        response_text="done",
    )
    append_jsonl(
        path,
        build_quiet_declaration(
            reason="resting",
            declared_by_cycle=1,
            declared_by_record_id=record_id,
            until=until,
        ),
    )
    return store


def _assembly_event(*, expires_at: str) -> dict:
    return build_inbound_event(
        purpose="assembly question",
        sender="assembly",
        label="assembly:test",
        assembly={
            "assembly_question_id": str(uuid4()),
            "expires_at": expires_at,
        },
    )


def _records(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_timed_quiet_defers_then_releases_an_assembly_event(tmp_path):
    path = tmp_path / "deferred.events.jsonl"
    quiet_until = T0 + timedelta(hours=2)
    store = _store_with_quiet(path, until=quiet_until.isoformat())
    event = _assembly_event(expires_at=(T0 + timedelta(days=1)).isoformat())
    append_jsonl(path, event)

    assert store.claim_next_pending(now=T0 + timedelta(hours=1)) is None
    claimed = store.claim_next_pending(now=T0 + timedelta(hours=3))
    assert claimed is not None
    assert claimed[0]["event_id"] == event["event_id"]


def test_quiet_outlasting_expiry_expires_without_a_wake(tmp_path):
    path = tmp_path / "expired.events.jsonl"
    store = _store_with_quiet(path, until=(T0 + timedelta(days=2)).isoformat())
    event = _assembly_event(expires_at=(T0 + timedelta(days=1)).isoformat())
    append_jsonl(path, event)

    assert store.claim_next_pending(now=T0 + timedelta(hours=1)) is None
    statuses = [row for row in _records(path) if row.get("event_id") == event["event_id"]]
    assert [row.get("status") for row in statuses] == ["pending", "expired"]
    assert statuses[-1]["detail"]["reason"] == "skipped_by_quiet"
    assert not any(row.get("status") == "running" for row in statuses)


def test_untimed_quiet_does_not_defer_assembly(tmp_path):
    path = tmp_path / "untimed.events.jsonl"
    store = _store_with_quiet(path, until=None)
    event = _assembly_event(expires_at=(T0 + timedelta(days=1)).isoformat())
    append_jsonl(path, event)

    claimed = store.claim_next_pending(now=T0 + timedelta(minutes=1))
    assert claimed is not None
    assert claimed[0]["event_id"] == event["event_id"]


def test_timed_quiet_does_not_defer_non_assembly_events(tmp_path):
    path = tmp_path / "plain.events.jsonl"
    store = _store_with_quiet(path, until=(T0 + timedelta(days=2)).isoformat())
    event = build_inbound_event(purpose="ordinary work", sender="test", label="plain")
    append_jsonl(path, event)

    claimed = store.claim_next_pending(now=T0 + timedelta(minutes=1))
    assert claimed is not None
    assert claimed[0]["event_id"] == event["event_id"]


@pytest.mark.parametrize("change", ["added", "removed", "path"])
def test_convene_refuses_membership_or_path_changes_during_open_lineage(
    house_factory, change
):
    house = house_factory(change)
    convene_question(house)
    document = member_document()
    if change == "added":
        document["members"]["new-door"] = {
            "session": "community/new-door/session.jsonl",
            "events": "community/new-door/session.jsonl.events.jsonl",
        }
    elif change == "removed":
        del document["members"]["west"]
    else:
        document["members"]["east"]["events"] = "community/east/replacement.events.jsonl"
    write_members(house.root, document)
    changed = load_members(house.root)
    assert changed is not None

    before = list(reduce(house.ledger.read()).questions)
    with pytest.raises(ConveneRefused):
        convene(
            house.ledger,
            changed,
            convener="tony",
            text="a second lineage",
            closes_in=timedelta(days=1),
            now=T0,
            proposal_procedure={
                "rule": "consent-v0",
                "max_rounds": 3,
                "quorum": "ceil(half)",
            },
            artifact={"path": "proposal", "commit": "a" * 40, "sha256": "b" * 64},
        )
    assert list(reduce(house.ledger.read()).questions) == before


def test_bind_refuses_live_paths_that_differ_from_open_snapshot(house):
    convene_question(house)
    document = member_document(
        event_overrides={"north": "community/north/replacement.events.jsonl"}
    )
    write_members(house.root, document)
    changed = load_members(house.root)
    assert changed is not None
    north = changed.members["north"]
    snapshots = reduce(house.ledger.read()).snapshots_of_open_questions()

    binding, note = bind(
        house.root,
        north.session,
        north.events,
        open_snapshots=snapshots,
    )
    assert binding is None
    assert "path" in note.lower() or "snapshot" in note.lower()


def test_constitution_clause_exists_only_when_assembly_tools_are_offered():
    without_assembly = build_constitution(None)
    with_assembly = build_constitution(None, assembly=True)
    assert ASSEMBLY_CONSTITUTION_CLAUSE not in without_assembly
    assert ASSEMBLY_CONSTITUTION_CLAUSE in with_assembly

    messages, rendered_prefix = _build_messages(
        None,
        "hello",
        1,
        system_prefix=with_assembly,
        tools_enabled=True,
        assembly=False,
    )
    rendered = json.dumps(messages, default=str) + rendered_prefix
    assert ASSEMBLY_CONSTITUTION_CLAUSE not in rendered
