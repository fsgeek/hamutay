import json
import multiprocessing
from datetime import datetime, timedelta, timezone
from pathlib import Path
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


def test_a_position_from_a_failed_wake_caps_assent_and_is_neither_eligible_nor_ignorable(house):
    """C1: a wake that records a dissent and then terminates `failed` is never re-pended
    (boot recovery re-pends `running` orphans only), so its stance cannot be counted and
    must not be silently discarded: the door enters cap:position_from_failed_wake."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    pos, ctx, store = _wake_and_position(led, cfg, bindings, q, "c", "dissent",
                                         at=T0 + timedelta(days=1), complete=False)
    store.append_failed(event=ctx.event, run_id=ctx.run_id, exc=RuntimeError("boom"))
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert c["outcome"] == "extended"
    assert c["tally"]["cap"] == "cap:position_from_failed_wake:c"
    assert c["tally"]["position_from_failed_wake"] == ["c"]
    cpos = [p for p in c["positions"] if p["record"]["member"] == "door:c"]
    assert len(cpos) == 1 and cpos[0]["eligible"] is None and cpos[0]["reason"] == "wake_failed"
    assert c["tally"]["objections"] == []            # the stance is not counted
    assert {a["member"]: a["reason"] for a in c["absent"]}["door:c"] == "failed"


def test_a_position_from_a_running_wake_is_still_ineligible_not_unknown(house):
    """The `failed` carve-out is narrow: running/pending keep eligible: False."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "c", "dissent", at=CLOSE - timedelta(minutes=5), complete=False)
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + GRACE + timedelta(seconds=1), actor="x")
    cpos = [p for p in c["positions"] if p["record"]["member"] == "door:c"]
    assert len(cpos) == 1 and cpos[0]["eligible"] is False and "reason" not in cpos[0]
    assert c["tally"]["position_from_failed_wake"] == []


def test_run_pass_bounds_the_ledger_lock_and_leaves_the_memo_unchanged(house):
    """I2: the pass reads every door's store under the ledger lock, so it can hold that
    lock for many seconds; a heartbeat waiting for it must give up, not block forever."""
    import threading
    import time as _time
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    memo_in = run_pass(bindings["a"], now=T0 + timedelta(days=1), actor="heartbeat:a")[1]
    held, release = threading.Event(), threading.Event()

    def holder():
        with led.locked():
            held.set(); release.wait(30)

    t = threading.Thread(target=holder); t.start(); held.wait(5)
    try:
        start = _time.monotonic()
        out, memo = run_pass(bindings["b"], now=CLOSE + timedelta(seconds=1), actor="heartbeat:b", memo=memo_in)
        elapsed = _time.monotonic() - start
    finally:
        release.set(); t.join()
    assert 9.5 <= elapsed <= 10.5, f"run_pass waited {elapsed:.1f}s for the ledger lock"
    assert out["skipped"] is False and "busy" in out["error"]
    assert out["closed"] == [] and out["activated"] == []
    assert memo == memo_in                                   # the memo is unchanged
    assert [r for r in led.read() if r["record_type"] == "closing"] == []


CLOSING_KEYS = {
    "record_type", "closing_id", "question_id", "lineage_id", "round", "outcome", "governing",
    "provisional", "proposal", "proposal_sha256", "tally", "positions", "testimony", "absent",
    "next_question", "closed_by", "closed_at", "delivery", "seq", "created_at",
}
TALLY_KEYS = {
    "eligible_members", "quorum", "active", "objections", "assents", "abstentions", "spoke",
    "not_offered", "running_at_cutoff", "unknown_at_cutoff", "position_from_failed_wake",
    "trace", "cap",
}


def test_closing_shape(house):
    """The closing is the assembly's only durable verdict and is read by the outbox, the
    activation derivation, the CLI and every door. Pin its key set, not only its values."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="cli:test")
    assert set(c) == CLOSING_KEYS, f"unexpected: {set(c) ^ CLOSING_KEYS}"
    assert set(c["tally"]) == TALLY_KEYS, f"unexpected: {set(c['tally']) ^ TALLY_KEYS}"
    assert set(c["delivery"]) == set(DOORS)
    assert all(set(v2) == {"event_id"} for v2 in c["delivery"].values())
    assert all(set(p) <= {"record", "eligible", "reason"} for p in c["positions"])
    assert all(set(a) == {"member", "reason", "detail"} for a in c["absent"])


def _pass_worker(barrier, root, door, when_iso):
    from hamutay.assembly.binding import bind, load_members
    from hamutay.assembly.pass_ import run_pass
    cfg = load_members(Path(root))
    b = bind(Path(root), cfg.members[door].session, cfg.members[door].events)[0]
    barrier.wait(30)
    run_pass(b, now=parse_instant(when_iso), actor=f"heartbeat:{door}")


def test_four_processes_close_once(house):
    """Four heartbeats poll the same due question at the same instant. The ledger lock and
    the deterministic closing id must yield exactly one closing and one delivery per door."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    for d in ("c", "d"):
        s = EventStore(cfg.members[d].events); ev, run = s.claim_next_pending(now=T0 + timedelta(days=2))
        s.append_completed(event=ev, run_id=run["run_id"], wake_cycle=1, result_record_id=uuid4(), response_text="r")
    ctx = multiprocessing.get_context("fork")
    barrier = ctx.Barrier(len(DOORS))
    when = iso(CLOSE + timedelta(seconds=1))
    procs = [ctx.Process(target=_pass_worker, args=(barrier, str(root), d, when)) for d in DOORS]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
    assert all(p.exitcode == 0 for p in procs), [p.exitcode for p in procs]

    records = led.read()
    cid = closing_id_for(q["question_id"])
    closings = [r for r in records if r["record_type"] == "closing"]
    assert len(closings) == 1 and closings[0]["closing_id"] == cid
    landed = [r for r in records if r["record_type"] == "delivery" and r["for"] == "closing"
              and r["id"] == cid and r["state"] == "landed"]
    assert sorted(r["door"] for r in landed) == sorted(DOORS)
    assert [r["seq"] for r in records] == list(range(1, len(records) + 1))
    for d in DOORS:
        evs = [r for r in EventStore(cfg.members[d].events).read_records() if r.get("record_type") != "event_status"]
        ids = [r["event_id"] for r in evs if r.get("event_id")]
        assert len(ids) == len(set(ids)), f"{d}: duplicate store events {ids}"
