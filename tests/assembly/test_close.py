import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.close import GRACE, derive_activations, try_close
from hamutay.assembly.convene import convene
from hamutay.assembly.ledger import Ledger, iso, parse_instant
from hamutay.assembly.outbox import run_outbox
from hamutay.assembly.pass_ import run_pass
from hamutay.assembly.position import record_position
from hamutay.assembly.records import child_question_id, closing_id_for, reduce
from hamutay.events import EventStore, StoreUnavailable, WakeContext, build_quiet_declaration

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
CLOSE = T0 + timedelta(days=7)
DOORS = ("a", "b", "c", "d")


@pytest.fixture
def house(tmp_path):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    members = {d: {"session": f"community/{d}/session.jsonl", "events": f"community/{d}/session.jsonl.events.jsonl"}
               for d in DOORS}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    for d in DOORS:
        (tmp_path / "community" / d).mkdir()
    cfg = load_members(tmp_path)
    led = Ledger(cfg.ledger)
    q = convene(led, cfg, convener="custodian", text="ratify?", closes_in=timedelta(days=7), now=T0,
                proposal_procedure={"rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)"},
                artifact={"path": "p", "commit": "c", "sha256": "s"})
    with led.locked():
        run_outbox(led, reduce(led.read_unlocked()), now=T0)
    bindings = {d: bind(tmp_path, cfg.members[d].session, cfg.members[d].events)[0] for d in DOORS}
    return tmp_path, led, cfg, q, bindings


def _wake_and_position(led, cfg, bindings, q, door, stance, *, at, complete=True, reasons=None):
    """A door claims its question event, takes a position, and (optionally) completes."""
    store = EventStore(cfg.members[door].events)
    claimed, running = store.claim_next_pending(now=at)
    assert claimed["event_id"] == q["delivery"][door]["event_id"]
    ctx = WakeContext(event_id=claimed["event_id"], run_id=running["run_id"], started_at=running["started_at"], event=claimed)
    rid = uuid4()
    pos = record_position(led, binding=bindings[door], wake=ctx, cycle=1, record_id=rid,
                          question_id=q["question_id"], stance=stance, reasons=reasons, now=at)
    if complete:
        store.append_completed(event=claimed, run_id=running["run_id"], wake_cycle=1, result_record_id=rid, response_text="r")
    return pos, ctx, store


def test_assent_by_quorum_with_the_empty_chair_and_activation(house):
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "abstain", at=T0 + timedelta(days=2))
    # c: claimed and completed without a position; d: never claimed
    sc = EventStore(cfg.members["c"].events); ev, run = sc.claim_next_pending(now=T0 + timedelta(days=3))
    sc.append_completed(event=ev, run_id=run["run_id"], wake_cycle=1, result_record_id=uuid4(), response_text="r")
    with led.locked():
        c = try_close(led, reduce(led.read_unlocked()), reduce(led.read_unlocked()).questions[q["question_id"]],
                      now=CLOSE + timedelta(seconds=1), actor="cli:test")
    assert c["outcome"] == "assented" and c["closing_id"] == closing_id_for(q["question_id"])
    assert c["tally"]["active"]["a"] and c["tally"]["assents"] == ["a"] and c["tally"]["spoke"] == 2
    reasons = {a["member"]: a["reason"] for a in c["absent"]}
    assert reasons == {"door:c": "completed_without_position", "door:d": "pending_at_close"}
    assert c["provisional"] is True and c["proposal_sha256"] == q["proposal"]["sha256"]
    with led.locked():
        acts = derive_activations(led, reduce(led.read_unlocked()))
        again = derive_activations(led, reduce(led.read_unlocked()))
    assert len(acts) == 1 and acts[0]["status"] == "active" and acts[0]["activated_by_closing_id"] == c["closing_id"]
    assert again == [] and reduce(led.read()).active_procedure["procedure_id"] == q["proposal"]["procedure_id"]


def test_one_dissent_extends_as_one_record_and_the_position_stands_in_round_two(house):
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "dissent", at=T0 + timedelta(days=1), reasons="no")
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="cli:test")
    assert c["outcome"] == "extended"
    child_id = child_question_id(q["lineage_id"], 2)
    assert c["next_question"]["question_id"] == child_id and c["next_question"]["round"] == 2
    assert c["next_question"]["opened_at"] == c["closed_at"]
    assert [r["record_type"] for r in led.read()][-1] == "closing"          # one record
    v = reduce(led.read())
    assert v.questions[child_id]["derived_from_closing"] == c["closing_id"]
    # round 2: silence from a preserves the dissent; a's store must be readable for the join
    with led.locked():
        v = reduce(led.read_unlocked()); run_outbox(led, v, now=parse_instant(c["closed_at"]))
    with led.locked():
        v = reduce(led.read_unlocked())
        c2 = try_close(led, v, v.questions[child_id], now=CLOSE + timedelta(days=7, seconds=1), actor="cli:test")
    assert c2["outcome"] == "extended" and c2["tally"]["objections"] == ["a"] and c2["round"] == 2
    with led.locked():
        v = reduce(led.read_unlocked())
        c3 = try_close(led, v, v.questions[child_question_id(q["lineage_id"], 3)],
                       now=CLOSE + timedelta(days=14, seconds=1), actor="cli:test")
    assert c3["outcome"] == "unresolved" and c3["next_question"] is None


def test_running_wake_inside_the_window_waits_then_caps(house):
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    # c claims just before the deadline and is still running (its position is buffered... or not)
    _wake_and_position(led, cfg, bindings, q, "c", "dissent", at=CLOSE - timedelta(minutes=5), complete=False)
    with led.locked():
        v = reduce(led.read_unlocked())
        assert try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(minutes=30), actor="x") is None
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + GRACE + timedelta(seconds=1), actor="x")
    assert c["outcome"] == "extended" and c["tally"]["cap"].startswith("cap:running_at_cutoff:c")
    ineligible = [p for p in c["positions"] if p["eligible"] is False]
    assert ineligible and ineligible[0]["record"]["member"] == "door:c"


def test_unreadable_store_waits_then_caps_and_never_marks_ineligible(house, monkeypatch):
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "c", "dissent", at=T0 + timedelta(days=1))
    real = EventStore.try_read_records
    def flaky(self, timeout_s=2.0):
        if "/c/" in str(self.path):
            raise StoreUnavailable("busy")
        return real(self, timeout_s)
    monkeypatch.setattr(EventStore, "try_read_records", flaky)
    with led.locked():
        v = reduce(led.read_unlocked())
        assert try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(minutes=1), actor="x") is None
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + GRACE + timedelta(seconds=1), actor="x")
    assert c["outcome"] == "extended" and "unknown_at_cutoff:c" in c["tally"]["cap"]
    cpos = [p for p in c["positions"] if p["record"]["member"] == "door:c"]
    assert cpos and cpos[0]["eligible"] is None
    assert {a["member"]: a["reason"] for a in c["absent"]}["door:c"] == "store_unreadable"


def test_not_offered_member_caps_assent(house, monkeypatch):
    root, led, cfg, q, bindings = house
    # pretend d's delivery never landed: rewrite its truth by appending store_unreadable after the fact
    from hamutay.assembly.records import build_delivery
    led.append(build_delivery(for_="question", id_=q["question_id"], door="d",
                              event_id=q["delivery"]["d"]["event_id"], state="store_unreadable", detail={"error": "x"}))
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + GRACE + timedelta(seconds=1), actor="x")
    assert c["outcome"] == "extended" and "not_offered:d" in c["tally"]["cap"]


def test_skipped_by_quiet_is_named_in_the_empty_chair(house):
    root, led, cfg, q, bindings = house
    store = EventStore(cfg.members["d"].events)
    ev = {"record_type": "event_status", "event_id": q["delivery"]["d"]["event_id"], "event_type": "inbound_message",
          "status": "expired", "expired_at": iso(T0), "detail": {"reason": "skipped_by_quiet", "quiet_until": iso(CLOSE)}}
    store.append(ev)
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert {a["member"]: a["reason"] for a in c["absent"]}["door:d"] == "skipped_by_quiet"


def test_run_pass_closes_lands_activates_and_then_skips_when_quiescent(house):
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    for d in ("c", "d"):                                     # both complete without a position
        s = EventStore(cfg.members[d].events); ev, run = s.claim_next_pending(now=T0 + timedelta(days=2))
        s.append_completed(event=ev, run_id=run["run_id"], wake_cycle=1, result_record_id=uuid4(), response_text="r")
    out, memo = run_pass(bindings["a"], now=CLOSE + timedelta(seconds=1), actor="heartbeat:a")
    assert out["closed"] == [q["question_id"]] and out["activated"]
    v = reduce(led.read())
    for d in DOORS:
        assert v.delivery_truth("closing", closing_id_for(q["question_id"]), d)["state"] == "landed"
    out2, memo2 = run_pass(bindings["b"], now=CLOSE + timedelta(seconds=2), actor="heartbeat:b", memo=memo)
    assert out2["skipped"] is True
    led.append({"record_type": "testimony", "testimony_id": "t", "lineage_id": q["lineage_id"],
                "question_id": q["question_id"], "by": "tony", "text": "late"})
    out3, _ = run_pass(bindings["b"], now=CLOSE + timedelta(seconds=3), actor="heartbeat:b", memo=memo2)
    assert out3["skipped"] is False                          # the ledger changed


def test_two_passes_one_closing(house):
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    for d in ("c", "d"):
        s = EventStore(cfg.members[d].events); ev, run = s.claim_next_pending(now=T0 + timedelta(days=2))
        s.append_completed(event=ev, run_id=run["run_id"], wake_cycle=1, result_record_id=uuid4(), response_text="r")
    run_pass(bindings["a"], now=CLOSE + timedelta(seconds=1), actor="heartbeat:a")
    run_pass(bindings["b"], now=CLOSE + timedelta(seconds=1), actor="heartbeat:b")
    assert len([r for r in led.read() if r["record_type"] == "closing"]) == 1
