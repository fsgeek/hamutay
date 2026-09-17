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
from hamutay.assembly.records import child_question_id, closing_event_id, closing_id_for, reduce
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


def test_derive_activations_falls_back_to_the_question_proposal_when_the_closing_lacks_one(house):
    """The spec's §2 closing schema block never documented `proposal`/`proposal_sha256` on
    the closing itself. A closing built to the documented schema alone (no `proposal`) must
    still be activated by reading the question's proposal."""
    root, led, cfg, q, bindings = house
    cid = closing_id_for(q["question_id"])
    closing = {"record_type": "closing", "closing_id": cid, "question_id": q["question_id"],
               "lineage_id": q["lineage_id"], "round": q["round"], "outcome": "assented", "governing": q["governing"],
               "provisional": True, "tally": {}, "positions": [], "testimony": [], "absent": [],
               "next_question": None, "closed_by": "cli:test", "closed_at": iso(CLOSE),
               "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in q["members"]}}
    assert "proposal" not in closing and "proposal_sha256" not in closing
    with led.locked():
        led.append_unlocked(closing)
        acts = derive_activations(led, reduce(led.read_unlocked()))
    assert len(acts) == 1 and acts[0]["status"] == "active" and acts[0]["activated_by_closing_id"] == cid
    assert reduce(led.read()).active_procedure["procedure_id"] == q["proposal"]["procedure_id"]


def test_derive_activations_rejects_on_digest_mismatch_when_the_closing_lacks_a_proposal(house):
    root, led, cfg, q, bindings = house
    cid = closing_id_for(q["question_id"])
    bad_question = dict(q); bad_question["proposal"] = dict(q["proposal"], sha256="0" * 64)
    closing = {"record_type": "closing", "closing_id": cid, "question_id": q["question_id"],
               "lineage_id": q["lineage_id"], "round": q["round"], "outcome": "assented", "governing": q["governing"],
               "provisional": True, "tally": {}, "positions": [], "testimony": [], "absent": [],
               "next_question": None, "closed_by": "cli:test", "closed_at": iso(CLOSE),
               "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in q["members"]}}
    with led.locked():
        led.append_unlocked(closing)
        view = reduce(led.read_unlocked())
        view.questions[q["question_id"]] = bad_question
        acts = derive_activations(led, view)
    assert len(acts) == 1 and acts[0]["status"] == "rejected" and acts[0]["activated_by_closing_id"] == cid


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
    # spec §7 step 5: the cap is named in trace, not only in tally["cap"]
    assert "cap:not_offered" in c["tally"]["trace"]
    assert c["tally"]["cap"] == "cap:not_offered:d"


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


def _compact_retry(store, event, run_id):
    """A window failure on `run_id`: the `failed` row plus its compact pending copy."""
    return store.append_failed_with_retry(event=event, run_id=run_id, exc=RuntimeError("cut"),
                                          reason="truncated_reply")[1]


def test_a_compact_pending_row_does_not_hide_the_failed_first_attempts_position(house):
    """§6: the first attempt recorded a position and then failed with a window failure.
    The compact retry makes the event's *latest* status `pending`, but the position's own
    run is `failed` — the cap must stand."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    pos, ctx, store = _wake_and_position(led, cfg, bindings, q, "c", "assent",
                                         at=T0 + timedelta(days=1), complete=False)
    retry = _compact_retry(store, ctx.event, ctx.run_id)
    assert retry["detail"]["compact_context"] is True and retry["detail"]["retry_of_run"] == ctx.run_id
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert c["tally"]["position_from_failed_wake"] == ["c"]
    assert c["tally"]["cap"].startswith("cap:position_from_failed_wake")
    cpos = [p for p in c["positions"] if p["record"]["member"] == "door:c"]
    assert len(cpos) == 1 and cpos[0]["eligible"] is None and cpos[0]["reason"] == "wake_failed"


def test_a_compact_retry_running_at_the_cutoff_waits_then_caps_as_running(house):
    """The compact run itself is claimed just before the deadline: it is a live run and
    holds the close open through the grace window, then caps as running_at_cutoff."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    store = EventStore(cfg.members["c"].events)
    ev, running = store.claim_next_pending(now=T0 + timedelta(days=1))
    _compact_retry(store, ev, running["run_id"])
    store.claim_next_pending(now=CLOSE - timedelta(minutes=5))       # the compact run starts
    with led.locked():
        v = reduce(led.read_unlocked())
        assert try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(minutes=30), actor="x") is None
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + GRACE + timedelta(seconds=1), actor="x")
    assert c["tally"]["running_at_cutoff"] == ["c"] and c["tally"]["cap"].startswith("cap:running_at_cutoff")


def test_a_compact_completion_without_a_position_leaves_the_failed_wake_cap(house):
    """The compact run completes but records no position. The first attempt's stance is
    still unjoinable, so its cap stands: the compact completion does not absolve it."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    pos, ctx, store = _wake_and_position(led, cfg, bindings, q, "c", "dissent",
                                         at=T0 + timedelta(days=1), complete=False)
    retry = _compact_retry(store, ctx.event, ctx.run_id)
    _, running2 = store.claim_next_pending(now=T0 + timedelta(days=1, minutes=1))
    store.append_completed(event=retry, run_id=running2["run_id"], wake_cycle=2,
                           result_record_id=uuid4(), response_text="quiet")
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert c["tally"]["position_from_failed_wake"] == ["c"]
    assert c["tally"]["cap"].startswith("cap:position_from_failed_wake")
    assert c["tally"]["objections"] == []


def test_a_compact_completion_with_a_replacement_position_replaces_the_failed_one(house):
    """The compact run records its own position and completes with the joined record. That
    position is the active one and no failed-wake cap is raised: the door spoke."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    pos, ctx, store = _wake_and_position(led, cfg, bindings, q, "c", "dissent",
                                         at=T0 + timedelta(days=1), complete=False)
    _compact_retry(store, ctx.event, ctx.run_id)
    # the compact run: claim, take a replacement position, complete with its record id
    pos2, ctx2, _ = _wake_and_position(led, cfg, bindings, q, "c", "assent",
                                       at=T0 + timedelta(days=1, minutes=1))
    assert ctx2.run_id != ctx.run_id
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert c["tally"]["position_from_failed_wake"] == []
    assert c["tally"]["active"]["c"] == pos2["position_id"]
    assert c["tally"]["assents"] == ["a", "b", "c"] and c["outcome"] == "assented"
    cfailed = [p for p in c["positions"]
               if p["record"]["member"] == "door:c" and p["record"]["position_id"] == pos["position_id"]]
    assert len(cfailed) == 1 and cfailed[0]["eligible"] is None and cfailed[0]["reason"] == "wake_failed"


def test_a_recovered_orphan_run_is_superseded_and_not_running_at_cutoff(house):
    """Boot recovery re-pends a `running` orphan. The dead run must not hold the question
    open forever: it is superseded by the pending row that names it."""
    from hamutay.heartbeat import recover_orphaned_running
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    store = EventStore(cfg.members["c"].events)
    ev, running = store.claim_next_pending(now=T0 + timedelta(days=1))   # the wake starts, the process dies
    recovered = recover_orphaned_running(store)                          # boot recovery re-pends it
    assert len(recovered) == 1 and recovered[0]["recovered_from_run_id"] == running["run_id"]
    _, running2 = store.claim_next_pending(now=T0 + timedelta(days=1, minutes=5))
    store.append_completed(event=recovered[0], run_id=running2["run_id"], wake_cycle=2,
                           result_record_id=uuid4(), response_text="ok")
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert c is not None and c["tally"]["running_at_cutoff"] == []
    assert c["outcome"] == "assented"


def test_a_failed_wake_after_an_earlier_eligible_position_still_caps(house):
    """The suppression is ordered, not merely present: a door that spoke, then spoke again
    on a wake that failed, has a later stance nobody can read — the cap stands."""
    root, led, cfg, q, bindings = house
    _wake_and_position(led, cfg, bindings, q, "a", "assent", at=T0 + timedelta(days=1))
    _wake_and_position(led, cfg, bindings, q, "b", "assent", at=T0 + timedelta(days=1))
    first, _, store = _wake_and_position(led, cfg, bindings, q, "c", "assent", at=T0 + timedelta(days=1))
    store.append(dict(q["delivery"]["c"], record_type="event_status", event_type="inbound_message",
                      status="pending", created_at=iso(T0 + timedelta(days=2))))
    pos2, ctx2, _ = _wake_and_position(led, cfg, bindings, q, "c", "dissent",
                                       at=T0 + timedelta(days=2), complete=False)
    store.append_failed(event=ctx2.event, run_id=ctx2.run_id, exc=RuntimeError("boom"))
    with led.locked():
        v = reduce(led.read_unlocked())
        c = try_close(led, v, v.questions[q["question_id"]], now=CLOSE + timedelta(seconds=1), actor="x")
    assert c["tally"]["active"]["c"] == first["position_id"]      # the older stance is the active one
    assert c["tally"]["position_from_failed_wake"] == ["c"]       # but the newer one is unread
    assert c["tally"]["cap"].startswith("cap:position_from_failed_wake")
