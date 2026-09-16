from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.close import try_close
from hamutay.assembly.position import PositionRefused, record_position
from hamutay.assembly.records import reduce
from hamutay.events import WakeContext

from .conftest import (
    House,
    T0,
    claim,
    complete,
    convene_question,
    land_outbox,
    member_document,
    take_and_complete,
    write_members,
)


def _close(house: House, q: dict, *, minutes_after: int = 61) -> dict | None:
    now = T0 + timedelta(days=1, minutes=minutes_after)
    with house.ledger.locked():
        view = reduce(house.ledger.read_unlocked())
        return try_close(
            house.ledger,
            view,
            view.questions[q["question_id"]],
            now=now,
            actor="heartbeat:north",
        )


def _corrupt_store(house: House, door: str) -> None:
    path = house.members.members[door].events
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write("{not-json\n")


def _two_assents(house: House, q: dict) -> None:
    take_and_complete(house, q, "north", "assent")
    take_and_complete(house, q, "east", "assent")


def test_not_offered_member_caps_an_otherwise_assented_question(house):
    q = convene_question(house)
    _corrupt_store(house, "west")
    land_outbox(house)
    _two_assents(house, q)

    closing = _close(house, q)
    assert closing is not None
    assert closing["outcome"] == "extended"
    assert "west" in closing["tally"]["not_offered"]
    assert "cap:not_offered" in closing["tally"]["trace"]


def test_running_wake_waits_through_grace_then_caps_assent(house):
    q = convene_question(house)
    land_outbox(house)
    _two_assents(house, q)
    claim(house, "west", now=T0 + timedelta(hours=1))

    assert _close(house, q, minutes_after=30) is None
    closing = _close(house, q, minutes_after=61)
    assert closing is not None
    assert closing["outcome"] == "extended"
    assert "west" in closing["tally"]["running_at_cutoff"]
    assert "cap:running_at_cutoff" in closing["tally"]["trace"]


def test_unreadable_store_caps_and_preserves_unknown_position_eligibility(house):
    q = convene_question(house)
    land_outbox(house)
    _two_assents(house, q)
    west = take_and_complete(house, q, "west", "assent")
    _corrupt_store(house, "west")

    closing = _close(house, q)
    assert closing is not None
    assert closing["outcome"] == "extended"
    assert "west" in closing["tally"]["unknown_at_cutoff"]
    carried = next(
        item for item in closing["positions"] if item["record"]["position_id"] == west["position_id"]
    )
    assert carried["eligible"] is None
    assert "cap:unknown_at_cutoff" in closing["tally"]["trace"]


def test_position_from_failed_wake_is_unknown_and_caps_assent(house):
    q = convene_question(house)
    land_outbox(house)
    _two_assents(house, q)
    event, running = claim(house, "west", now=T0 + timedelta(hours=1))
    record_id = str(uuid4())
    wake = WakeContext(
        event_id=event["event_id"],
        run_id=running["run_id"],
        started_at=running["started_at"],
        event=event,
    )
    west = record_position(
        house.ledger,
        binding=house.bindings["west"],
        wake=wake,
        cycle=1,
        record_id=record_id,
        question_id=q["question_id"],
        stance="assent",
        reasons=None,
        now=T0 + timedelta(hours=1),
    )
    house.store("west").append_failed(
        event=event,
        run_id=running["run_id"],
        exc=RuntimeError("wake failed after taking a position"),
    )

    closing = _close(house, q, minutes_after=1)
    assert closing is not None
    assert closing["outcome"] == "extended"
    assert "west" in closing["tally"]["position_from_failed_wake"]
    carried = next(
        item for item in closing["positions"] if item["record"]["position_id"] == west["position_id"]
    )
    assert carried["eligible"] is None
    assert "cap:position_from_failed_wake" in closing["tally"]["trace"]


def test_position_is_durable_on_return_and_refusals_write_no_position(house):
    q = convene_question(house)
    land_outbox(house)
    event, running = claim(house, "north")
    record_id = str(uuid4())
    wake = WakeContext(event["event_id"], running["run_id"], running["started_at"], event)

    accepted = record_position(
        house.ledger,
        binding=house.bindings["north"],
        wake=wake,
        cycle=1,
        record_id=record_id,
        question_id=q["question_id"],
        stance="assent",
        reasons="yes",
        now=T0,
    )
    assert any(
        row.get("position_id") == accepted["position_id"] for row in house.ledger.read()
    )

    before_positions = len(reduce(house.ledger.read()).positions)
    with pytest.raises(PositionRefused):
        record_position(
            house.ledger,
            binding=house.bindings["north"],
            wake=wake,
            cycle=1,
            record_id=str(uuid4()),
            question_id=str(uuid4()),
            stance="dissent",
            reasons=None,
            now=T0,
        )

    missed = WakeContext(
        event["event_id"],
        running["run_id"],
        q["closes_at"],
        event,
    )
    with pytest.raises(PositionRefused):
        record_position(
            house.ledger,
            binding=house.bindings["north"],
            wake=missed,
            cycle=1,
            record_id=str(uuid4()),
            question_id=q["question_id"],
            stance="dissent",
            reasons=None,
            now=T0 + timedelta(days=1),
        )

    document = member_document()
    document["members"]["outsider"] = {
        "session": "community/outsider/session.jsonl",
        "events": "community/outsider/session.jsonl.events.jsonl",
    }
    write_members(house.root, document)
    expanded = load_members(house.root)
    assert expanded is not None
    outsider = expanded.members["outsider"]
    outsider.session.parent.mkdir(parents=True, exist_ok=True)
    outsider_binding, note = bind(house.root, outsider.session, outsider.events)
    assert outsider_binding is not None, note
    with pytest.raises(PositionRefused):
        record_position(
            house.ledger,
            binding=outsider_binding,
            wake=wake,
            cycle=1,
            record_id=str(uuid4()),
            question_id=q["question_id"],
            stance="dissent",
            reasons=None,
            now=T0,
        )
    assert len(reduce(house.ledger.read()).positions) == before_positions

    complete(house, "north", event, running, record_id=record_id)
    take_and_complete(house, q, "east", "assent")
    closing = _close(house, q, minutes_after=1)
    assert closing is not None and closing["outcome"] == "assented"

    positions_before_closed_call = len(reduce(house.ledger.read()).positions)
    with pytest.raises(PositionRefused):
        record_position(
            house.ledger,
            binding=house.bindings["north"],
            wake=wake,
            cycle=1,
            record_id=str(uuid4()),
            question_id=q["question_id"],
            stance="dissent",
            reasons="too late",
            now=T0 + timedelta(days=1, minutes=2),
        )
    view = reduce(house.ledger.read())
    assert len(view.positions) == positions_before_closed_call
    assert view.records[-1]["record_type"] == "late_position"
    assert view.records[-1]["closing_id"] == closing["closing_id"]
