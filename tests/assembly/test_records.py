from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from hamutay.assembly.ledger import Ledger, iso
from hamutay.assembly.records import (
    STANCES, build_delivery, build_position, build_procedure, build_question,
    child_question_id, closing_event_id, closing_id_for, payload_sha256, reduce,
)

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
SNAP = {"qwen": {"session": "/p/community/qwen/session.jsonl", "events": "/p/community/qwen/session.jsonl.events.jsonl"},
        "elder": {"session": "/p/community/elder/session.jsonl", "events": "/p/community/elder/session.jsonl.events.jsonl"}}
GOV = {"procedure_id": None, "rule": "consent-v0", "max_rounds": 3, "quorum": 1}


def _question(**kw):
    base = dict(text="q?", convener="custodian", opened_at=iso(T0), closes_at=iso(T0 + timedelta(days=7)),
                governing=GOV, members_snapshot=SNAP, proposal={"kind": "text", "sha256": "0" * 64})
    base.update(kw)
    return build_question(**base)


def test_ids_are_deterministic():
    q = "5f2a9e2e-1c7b-4a1e-9f3a-2b6c8d9e0f11"
    assert closing_id_for(q) == closing_id_for(q) and UUID(closing_id_for(q))
    assert child_question_id(q, 2) != child_question_id(q, 3)
    assert closing_event_id(closing_id_for(q), "qwen") != closing_event_id(closing_id_for(q), "elder")


def test_payload_sha256_is_order_independent():
    assert payload_sha256({"a": 1, "b": 2}) == payload_sha256({"b": 2, "a": 1})


def test_question_builder_plans_one_delivery_per_member_with_fresh_event_ids():
    q = _question()
    assert set(q["delivery"]) == {"qwen", "elder"}
    ids = {d["event_id"] for d in q["delivery"].values()}
    assert len(ids) == 2 and q["round"] == 1 and q["lineage_id"] == q["question_id"]
    assert q["members"] == SNAP


def test_question_builder_refuses_naive_instants_and_bad_stance():
    with pytest.raises(ValueError):
        _question(opened_at="2026-09-20T12:00:00")
    q = _question()
    with pytest.raises(ValueError):
        build_position(question=q, member="qwen", cycle=1, record_id="r", event_id="e", run_id="u",
                       wake_started_at=iso(T0), stance="maybe", reasons=None, events_path=SNAP["qwen"]["events"])


def test_reduce_delivery_truth_and_open_questions(ledger_path):
    led = Ledger(ledger_path)
    q = led.append(_question())
    view = reduce(led.read())
    assert [x["question_id"] for x in view.open_questions()] == [q["question_id"]]
    assert view.delivery_truth("question", q["question_id"], "qwen")["state"] == "planned"
    led.append(build_delivery(for_="question", id_=q["question_id"], door="qwen",
                              event_id=q["delivery"]["qwen"]["event_id"], state="store_unreadable",
                              detail={"error": "busy"}))
    led.append(build_delivery(for_="question", id_=q["question_id"], door="qwen",
                              event_id=q["delivery"]["qwen"]["event_id"], state="landed", landed_at=iso(T0)))
    view = reduce(led.read())
    truth = view.delivery_truth("question", q["question_id"], "qwen")
    assert truth["state"] == "landed" and truth["landed_at"] == iso(T0)
    assert not view.quiescent(T0)          # elder still planned
    led.append(build_delivery(for_="question", id_=q["question_id"], door="elder",
                              event_id=q["delivery"]["elder"]["event_id"], state="landed", landed_at=iso(T0)))
    view = reduce(led.read())
    assert view.quiescent(T0) and not view.quiescent(T0 + timedelta(days=7))


def test_reduce_derives_a_child_from_a_closing_and_resolves_its_delivery_through_the_parent(ledger_path):
    led = Ledger(ledger_path)
    q = led.append(_question())
    cid = closing_id_for(q["question_id"])
    child = {"question_id": child_question_id(q["lineage_id"], 2), "round": 2,
             "opened_at": iso(T0 + timedelta(days=7)), "closes_at": iso(T0 + timedelta(days=14)),
             "text": q["text"], "proposal": q["proposal"], "governing": GOV, "members": SNAP}
    closing = {"record_type": "closing", "closing_id": cid, "question_id": q["question_id"],
               "lineage_id": q["lineage_id"], "round": 1, "outcome": "extended", "governing": GOV,
               "provisional": True, "tally": {}, "positions": [], "testimony": [], "absent": [],
               "next_question": child, "closed_by": "cli:test", "closed_at": iso(T0 + timedelta(days=7)),
               "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in SNAP}}
    led.append(closing)
    view = reduce(led.read())
    assert q["question_id"] not in [x["question_id"] for x in view.open_questions()]
    derived = view.questions[child["question_id"]]
    assert derived["derived_from_closing"] == cid and derived["parent_question_id"] == q["question_id"]
    assert view.delivery_truth("question", child["question_id"], "qwen")["state"] == "planned"
    led.append(build_delivery(for_="closing", id_=cid, door="qwen", event_id=closing_event_id(cid, "qwen"),
                              state="landed", landed_at=iso(T0 + timedelta(days=7, minutes=1))))
    view = reduce(led.read())
    t = view.delivery_truth("question", child["question_id"], "qwen")
    assert t["state"] == "landed" and t["event_id"] == closing_event_id(cid, "qwen")
    assert view.open_lineage_for("custodian")["question_id"] == child["question_id"]


def test_governing_selector_prefers_the_active_procedure(ledger_path):
    led = Ledger(ledger_path)
    view = reduce(led.read())
    assert view.governing_for_new_question()["procedure_id"] is None
    prov = led.append(build_procedure({"rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)"},
                                      {"path": "p", "commit": "c", "sha256": "s"}, status="provisional"))
    assert prov["version"] == 1
    act = dict(prov); act.pop("seq"); act.pop("created_at"); act["status"] = "active"; act["activated_by_closing_id"] = "x"
    led.append(act)
    view = reduce(led.read())
    assert view.active_procedure["procedure_id"] == prov["procedure_id"]
    assert view.governing_for_new_question()["procedure_id"] == prov["procedure_id"]
