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


def _closing(q, *, outcome, proposal=None, next_question=None):
    cid = closing_id_for(q["question_id"])
    return {"record_type": "closing", "closing_id": cid, "question_id": q["question_id"],
            "lineage_id": q["lineage_id"], "round": q["round"], "outcome": outcome, "governing": q["governing"],
            "provisional": True, "proposal": proposal or q["proposal"],
            "proposal_sha256": (proposal or q["proposal"])["sha256"], "tally": {}, "positions": [],
            "testimony": [], "absent": [], "next_question": next_question, "closed_by": "cli:test",
            "closed_at": iso(T0 + timedelta(days=7)),
            "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in q["members"]}}


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
                                      {"path": "p", "commit": "c", "sha256": "s"}, status="provisional", version=1))
    assert prov["version"] == 1
    act = dict(prov); act.pop("seq"); act.pop("created_at"); act["status"] = "active"; act["activated_by_closing_id"] = "x"
    led.append(act)
    view = reduce(led.read())
    assert view.active_procedure["procedure_id"] == prov["procedure_id"]
    assert view.governing_for_new_question()["procedure_id"] == prov["procedure_id"]


def test_missing_activations_lists_assented_procedure_closings_without_a_derivation(ledger_path):
    led = Ledger(ledger_path)
    prov = led.append(build_procedure({"rule": "consent-v0"}, {"path": "p", "commit": "c", "sha256": "s"},
                                      status="provisional", version=1))
    proposal = {"kind": "procedure", "procedure_id": prov["procedure_id"], "sha256": prov["payload_sha256"]}
    q = led.append(_question(proposal=proposal))
    c = led.append(_closing(q, outcome="assented"))
    view = reduce(led.read())
    assert [x["closing_id"] for x in view.missing_activations()] == [c["closing_id"]]
    act = build_procedure(prov["payload"], prov["artifact"], status="active", procedure_id=prov["procedure_id"],
                          version=1, activated_by_closing_id=c["closing_id"])
    led.append(act)
    assert reduce(led.read()).missing_activations() == []
    # a text proposal or a non-assented outcome never needs a derivation
    q2 = led.append(_question(convener="tony"))
    led.append(_closing(q2, outcome="unresolved"))
    assert reduce(led.read()).missing_activations() == []


def test_missing_activations_falls_back_to_the_question_proposal_when_the_closing_lacks_one(ledger_path):
    """The spec's §2 closing schema block never documented `proposal`/`proposal_sha256`
    on the closing itself (they're a convenience `try_close` happens to copy). A closing
    built to the documented schema alone must still be found."""
    led = Ledger(ledger_path)
    prov = led.append(build_procedure({"rule": "consent-v0"}, {"path": "p", "commit": "c", "sha256": "s"},
                                      status="provisional", version=1))
    proposal = {"kind": "procedure", "procedure_id": prov["procedure_id"], "sha256": prov["payload_sha256"]}
    q = led.append(_question(proposal=proposal))
    cid = closing_id_for(q["question_id"])
    closing = {"record_type": "closing", "closing_id": cid, "question_id": q["question_id"],
               "lineage_id": q["lineage_id"], "round": q["round"], "outcome": "assented", "governing": q["governing"],
               "provisional": True, "tally": {}, "positions": [], "testimony": [], "absent": [],
               "next_question": None, "closed_by": "cli:test", "closed_at": iso(T0 + timedelta(days=7)),
               "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in q["members"]}}
    assert "proposal" not in closing and "proposal_sha256" not in closing
    led.append(closing)
    view = reduce(led.read())
    assert [x["closing_id"] for x in view.missing_activations()] == [cid]


def test_build_execution_requires_an_assented_closing_and_reasons_when_declined(ledger_path):
    from hamutay.assembly.records import build_execution
    q = _question()
    ok = build_execution(closing=_closing(q, outcome="assented"), by="custodian", outcome="done", what="did it", reasons=None)
    assert ok["closing_id"] == closing_id_for(q["question_id"]) and ok["proposal_sha256"] == q["proposal"]["sha256"]
    with pytest.raises(ValueError):
        build_execution(closing=_closing(q, outcome="unresolved"), by="custodian", outcome="done", what="x", reasons=None)
    with pytest.raises(ValueError):
        build_execution(closing=_closing(q, outcome="assented"), by="tony", outcome="declined", what="x", reasons=None)
    dec = build_execution(closing=_closing(q, outcome="assented"), by="tony", outcome="declined", what="x", reasons="no")
    assert dec["outcome"] == "declined" and dec["reasons"] == "no"


def test_quorum_for_integer_and_ceil_half():
    from hamutay.assembly.records import quorum_for
    four = {d: {} for d in "abcd"}
    assert quorum_for(four, {"quorum": "ceil(half)"}) == 2
    assert quorum_for({d: {} for d in "abc"}, {"quorum": "ceil(half)"}) == 2
    assert quorum_for(four, {"quorum": 3}) == 3


def test_reduce_orders_by_seq_regardless_of_input_order(ledger_path):
    led = Ledger(ledger_path)
    q = led.append(_question())
    a = led.append(build_delivery(for_="question", id_=q["question_id"], door="qwen",
                                  event_id=q["delivery"]["qwen"]["event_id"], state="store_unreadable", detail={"error": "x"}))
    b = led.append(build_delivery(for_="question", id_=q["question_id"], door="qwen",
                                  event_id=q["delivery"]["qwen"]["event_id"], state="landed", landed_at=iso(T0)))
    shuffled = [b, a, q]
    assert reduce(shuffled).delivery_truth("question", q["question_id"], "qwen")["state"] == "landed"
