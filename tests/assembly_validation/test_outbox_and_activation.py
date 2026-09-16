from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

from hamutay.assembly.close import derive_activations
from hamutay.assembly.outbox import run_outbox
from hamutay.assembly.pass_ import run_pass
from hamutay.assembly.records import reduce

from .conftest import T0, convene_question, land_outbox, take_and_complete


def test_repeated_outbox_runs_create_one_pending_event_per_store(house):
    q = convene_question(house)
    with house.ledger.locked():
        run_outbox(house.ledger, reduce(house.ledger.read_unlocked()), now=T0)
        run_outbox(house.ledger, reduce(house.ledger.read_unlocked()), now=T0)
        run_outbox(house.ledger, reduce(house.ledger.read_unlocked()), now=T0)

    for door, member in house.members.members.items():
        records = [json.loads(line) for line in member.events.read_text().splitlines()]
        event_id = q["delivery"][door]["event_id"]
        assert sum(record.get("event_id") == event_id for record in records) == 1


def test_assented_procedure_activates_exactly_once_across_repeated_passes(house):
    q = convene_question(house)
    land_outbox(house)
    take_and_complete(house, q, "north", "assent")
    take_and_complete(house, q, "east", "assent")

    close_time = T0 + timedelta(days=1, seconds=1)
    first, memo = run_pass(house.bindings["north"], now=close_time, actor="heartbeat:north")
    second, memo = run_pass(
        house.bindings["east"],
        now=close_time + timedelta(seconds=1),
        actor="heartbeat:east",
        memo=memo,
    )
    third, _memo = run_pass(
        house.bindings["north"],
        now=close_time + timedelta(seconds=2),
        actor="heartbeat:north",
        memo=memo,
    )

    view = reduce(house.ledger.read())
    closing = view.closings[q["question_id"]]
    activations = [
        row
        for row in view.records
        if row["record_type"] == "procedure"
        and row.get("status") == "active"
        and row.get("activated_by_closing_id") == closing["closing_id"]
    ]
    assert closing["outcome"] == "assented"
    assert len(activations) == 1
    assert activations[0]["payload_sha256"] == q["proposal"]["sha256"]
    assert first.get("error") is None
    assert second.get("error") is None
    assert third.get("error") is None


def test_digest_mismatch_is_rejected_and_never_activated(house):
    procedure_id = str(uuid4())
    question_id = str(uuid4())
    lineage_id = str(uuid4())
    closing_id = str(uuid4())
    members = house.members.snapshot()
    delivery = {
        door: {"event_id": str(uuid4())}
        for door in house.members.members
    }
    governing = {
        "procedure_id": None,
        "rule": "consent-v0",
        "max_rounds": 3,
        "quorum": 2,
    }
    proposal_payload = {
        "rule": "consent-v0",
        "max_rounds": 3,
        "quorum": "ceil(half)",
    }
    house.ledger.append(
        {
            "record_type": "procedure",
            "procedure_id": procedure_id,
            "version": 1,
            "status": "provisional",
            "payload": proposal_payload,
            "payload_sha256": "a" * 64,
            "artifact": {"path": "proposal", "commit": "c" * 40, "sha256": "d" * 64},
            "proposed_by_question_id": question_id,
            "activated_by_closing_id": None,
        }
    )
    house.ledger.append(
        {
            "record_type": "question",
            "question_id": question_id,
            "lineage_id": lineage_id,
            "round": 1,
            "parent_question_id": None,
            "convener": "custodian",
            "text": "mismatched proposal",
            "proposal": {
                "kind": "procedure",
                "procedure_id": procedure_id,
                "sha256": "b" * 64,
            },
            "opened_at": T0.isoformat(),
            "closes_at": (T0 + timedelta(days=1)).isoformat(),
            "governing": governing,
            "members": members,
            "delivery": delivery,
        }
    )
    house.ledger.append(
        {
            "record_type": "closing",
            "closing_id": closing_id,
            "question_id": question_id,
            "lineage_id": lineage_id,
            "round": 1,
            "outcome": "assented",
            "governing": governing,
            "provisional": True,
            "tally": {},
            "positions": [],
            "testimony": [],
            "absent": [],
            "next_question": None,
            "closed_by": "heartbeat:north",
            "closed_at": (T0 + timedelta(days=1, seconds=1)).isoformat(),
            "delivery": delivery,
        }
    )

    with house.ledger.locked():
        first = derive_activations(house.ledger, reduce(house.ledger.read_unlocked()))
        second = derive_activations(house.ledger, reduce(house.ledger.read_unlocked()))

    rows = house.ledger.read()
    rejected = [
        row
        for row in rows
        if row["record_type"] == "procedure"
        and row.get("status") == "rejected"
        and row.get("activated_by_closing_id") == closing_id
    ]
    active = [
        row
        for row in rows
        if row["record_type"] == "procedure"
        and row.get("status") == "active"
        and row.get("procedure_id") == procedure_id
    ]
    assert len(first) == 1
    assert second == []
    assert len(rejected) == 1
    assert active == []
