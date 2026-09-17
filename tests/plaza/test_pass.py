import json
from datetime import datetime, timedelta, timezone

import pytest

from hamutay.assembly.ledger import Ledger, LedgerUnavailable, iso
from hamutay.events import EventStore, StoreUnavailable
from hamutay.plaza.pass_ import PASS_BUDGET_S, PASS_UNITS, PlazaMemo, run_plaza_pass
from hamutay.plaza.records import reduce
from hamutay.plaza.send import send

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _wake(ev):
    return {"cycle": 1, "record_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "event_id": ev,
            "run_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "started_at": iso(T0)}


def _broken(path, event, *, timeout_s=2.0):
    raise StoreUnavailable("busy")


def _pending(cfg, n, to="elder"):
    ids = []
    for i in range(n):
        r = send(cfg, actor="door:qwen", via="tool", to=to, text=f"m{i}", now=T0 + timedelta(seconds=i),
                 wake=_wake(f"{i:08d}-1111-4111-8111-111111111111"), land=_broken)
        ids.append(r["message_id"])
    return ids


def test_pass_lands_pending_deliveries_at_most_once_and_records_them(house):
    root, cfg, binding = house
    ids = _pending(cfg, 2)
    out, memo = run_plaza_pass(binding, now=T0)
    assert out["landed"] == ids and out["units"] == 2 and not out["skipped"]
    v = reduce(Ledger(cfg.plaza).read())
    assert all(v.delivery_truth(i)["state"] == "landed" for i in ids)
    assert len(EventStore(cfg.members["elder"].events).read_records()) == 2
    out2, memo2 = run_plaza_pass(binding, now=T0, memo=memo)
    assert out2["skipped"] is True and memo2 == memo


def test_pass_records_landed_when_the_event_was_already_present(house):
    root, cfg, binding = house
    (mid,) = _pending(cfg, 1)
    m = reduce(Ledger(cfg.plaza).read()).by_id[mid]
    from hamutay.plaza.event import inbound_event_for
    EventStore(cfg.members["elder"].events).append_if_absent(inbound_event_for(m))   # crash between the two writes
    out, _ = run_plaza_pass(binding, now=T0)
    assert out["landed"] == [mid]
    assert len(EventStore(cfg.members["elder"].events).read_records()) == 1


def test_pass_is_bounded_by_units_stops_after_one_circuit_and_is_fair(house):
    root, cfg, binding = house
    ids = _pending(cfg, 6)
    out, memo = run_plaza_pass(binding, now=T0)
    assert out["units"] == PASS_UNITS and out["landed"] == ids[:4] and memo.cursor == reduce(Ledger(cfg.plaza).read()).by_id[ids[3]]["seq"]
    out, memo = run_plaza_pass(binding, now=T0, memo=memo)
    assert out["landed"] == ids[4:] and out["units"] == 2
    # one stuck message is tried once per pass, not four times
    (stuck,) = _pending(cfg, 1, to="fable")
    calls = []
    def flaky(path, event, *, timeout_s=2.0):
        calls.append(event["event_id"]); raise StoreUnavailable("still busy")
    out, memo = run_plaza_pass(binding, now=T0, memo=memo, land=flaky)
    assert out["units"] == 1 and out["unreadable"] == [stuck] and len(calls) == 1
    # a repeated identical error is not re-recorded
    n_before = len(Ledger(cfg.plaza).read())
    run_plaza_pass(binding, now=T0, memo=None, land=flaky)
    assert len(Ledger(cfg.plaza).read()) == n_before


def test_pass_budget_stops_before_a_unit_that_cannot_fit(house):
    root, cfg, binding = house
    _pending(cfg, 3)
    t = [0.0]
    def clock():
        return t[0]
    def slow(path, event, *, timeout_s=2.0):
        t[0] += 3.0; return True
    out, _ = run_plaza_pass(binding, now=T0, land=slow, clock=clock)
    assert out["units"] == 1                    # after 3 s spent, 3 s remain: less than the 4 s a unit needs
    assert PASS_BUDGET_S == 6.0


def test_pass_continues_past_per_message_failures_and_stops_on_malformed(house):
    root, cfg, binding = house
    a, b = _pending(cfg, 2)
    a_event_id = reduce(Ledger(cfg.plaza).read()).by_id[a]["delivery"]["event_id"]
    def half(path, event, *, timeout_s=2.0):
        if event["event_id"] == a_event_id:
            # store.land normalises OSError (and LeaseGateRequired) into
            # StoreUnavailable, so StoreUnavailable is the only thing the pass
            # can actually see from a real land (M6).
            raise StoreUnavailable("disk")
        return True
    out, _ = run_plaza_pass(binding, now=T0, land=half)
    assert out["unreadable"] == [a] and out["landed"] == [b]
    with cfg.plaza.open("a") as f:
        f.write(json.dumps({"record_type": "note", "seq": 99}) + "\n")
    out, _ = run_plaza_pass(binding, now=T0)
    assert "error" in out and out["units"] == 0


def test_pass_skips_when_the_lock_is_held(house):
    root, cfg, binding = house
    _pending(cfg, 1)
    with Ledger(cfg.plaza).locked():
        out, _ = run_plaza_pass(binding, now=T0)
    assert out["skipped"] == "lock"


def test_pass_keeps_the_advanced_cursor_when_the_lock_times_out_mid_pass(house):
    """I1: a lock timeout part-way through a pass must not throw away the cursor
    the completed units advanced. The LedgerMalformed path already returns the
    advanced cursor and the fresh signature; LedgerUnavailable returned the
    caller's original memo, so the next pass re-examined messages this one
    already landed and could retry a stuck head indefinitely."""
    root, cfg, binding = house
    ids = _pending(cfg, 3)
    seqs = {m: reduce(Ledger(cfg.plaza).read()).by_id[m]["seq"] for m in ids}
    stale = PlazaMemo(("stale", 0.0), 0, 3)

    calls = []
    real_try_locked = Ledger.try_locked

    def flaky_lock(self, timeout_s):
        calls.append(1)
        if len(calls) > 2:                       # the third unit cannot get the lock
            raise LedgerUnavailable("plaza busy")
        return real_try_locked(self, timeout_s)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(Ledger, "try_locked", flaky_lock)
    try:
        out, memo = run_plaza_pass(binding, now=T0, memo=stale)
    finally:
        monkey.undo()

    assert out["skipped"] == "lock" and out["landed"] == ids[:2]
    assert memo is not stale
    assert memo.cursor == seqs[ids[1]]           # the cursor the two landed units advanced
    assert memo.signature != stale.signature     # and the signature read this pass
    assert memo.undelivered >= 1                 # something is still pending
