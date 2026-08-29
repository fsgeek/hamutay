"""Wake budget governor — implementer's TDD tests.

Spec: docs/superpowers/specs/2026-08-29-wake-budget-governor-design.md
(including "Revisions after Codex's review"). Validating tests are authored
separately by Codex per repo norm.

A resident's UTC day is bounded in dollars and in wakes. The ledger is the
session log itself; the policy is checked before every wake; when the day
is exceeded the heartbeat rests until UTC midnight, events wait, and a wake
that runs after a rest is told so in its envelope.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from hamutay.events import EventStore, build_inbound_event
from hamutay.heartbeat import DailyLedger, HeartbeatLoop, WakeBudget


def _record(ts, cost=None, provider="openrouter", cycle=1, unreported=0):
    usage = {"input_tokens": 1000, "output_tokens": 50}
    if cost is not None:
        usage["cost_usd"] = cost
        usage["generation_ids"] = ["gen-x"]
    if unreported:
        usage["cost_turns_unreported"] = unreported
    return {
        "cycle": cycle,
        "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
        "launch": {"provider": provider, "model": "m"},
        "usage": usage,
        "state": {},
    }


def _write(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _append(path, record, newline=True):
    with open(path, "a") as f:
        f.write(json.dumps(record) + ("\n" if newline else ""))


NOW = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)


# --- ledger: the log is the ledger --------------------------------------------


def test_ledger_sums_cost_and_counts_wakes_for_the_utc_day(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [
        _record(NOW - timedelta(hours=5), cost=1.25, cycle=1),
        _record(NOW - timedelta(hours=1), cost=2.00, cycle=2),
    ])
    day = DailyLedger(str(log)).day(NOW)
    assert day["day"] == "2026-08-29"
    assert day["wakes"] == 2
    assert day["cost_usd"] == pytest.approx(3.25)
    assert day["unmeasured_wakes"] == 0
    assert day["cost_turns_unreported"] == 0


def test_ledger_day_boundary_is_utc_midnight_not_local(tmp_path):
    log = tmp_path / "s.jsonl"
    yesterday_late = datetime(2026, 8, 28, 23, 59, 59, tzinfo=timezone.utc)
    today_start = "2026-08-29T00:00:00+00:00"
    _write(log, [
        _record(yesterday_late, cost=9.00, cycle=1),
        _record(today_start, cost=0.10, cycle=2),
    ])
    day = DailyLedger(str(log)).day(NOW)
    assert day["wakes"] == 1
    assert day["cost_usd"] == pytest.approx(0.10)


def test_ledger_reads_z_suffix_and_naive_timestamps_as_utc(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [
        _record("2026-08-29T10:00:00Z", cost=0.10, cycle=1),
        _record("2026-08-29T11:00:00", cost=0.10, cycle=2),
    ])
    assert DailyLedger(str(log)).day(NOW)["wakes"] == 2


def test_ledger_naive_now_is_read_as_utc(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [_record(NOW - timedelta(hours=1), cost=0.10)])
    naive_now = datetime(2026, 8, 29, 18, 0)
    assert DailyLedger(str(log)).day(naive_now)["wakes"] == 1


def test_ledger_unmeasured_metered_wake_is_counted_never_free(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [
        _record(NOW - timedelta(hours=2), cost=None, provider="openrouter", cycle=1),
        _record(NOW - timedelta(hours=1), cost=0.50, cycle=2),
    ])
    day = DailyLedger(str(log)).day(NOW)
    assert day["wakes"] == 2
    assert day["unmeasured_wakes"] == 1
    assert day["cost_usd"] == pytest.approx(0.50)


def test_ledger_partially_reported_wake_is_unmeasured_and_a_lower_bound(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [_record(NOW - timedelta(hours=1), cost=0.30, unreported=2)])
    day = DailyLedger(str(log)).day(NOW)
    assert day["cost_usd"] == pytest.approx(0.30)
    assert day["unmeasured_wakes"] == 1
    assert day["cost_turns_unreported"] == 2


def test_ledger_anthropic_direct_cost_never_feeds_the_cost_ceiling(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [
        _record(NOW - timedelta(hours=2), cost=None, provider="anthropic", cycle=1),
        _record(NOW - timedelta(hours=1), cost=7.0, provider="anthropic", cycle=2),
    ])
    day = DailyLedger(str(log)).day(NOW)
    assert day["wakes"] == 2
    assert day["unmeasured_wakes"] == 0
    assert day["cost_usd"] == pytest.approx(0.0)


def test_ledger_bool_or_string_cost_is_not_a_number(tmp_path):
    log = tmp_path / "s.jsonl"
    rows = [_record(NOW - timedelta(hours=1), cost=0.1, cycle=1)]
    rows[0]["usage"]["cost_usd"] = True
    rows.append(_record(NOW - timedelta(hours=2), cost=0.1, cycle=2))
    rows[1]["usage"]["cost_usd"] = "0.25"
    _write(log, rows)
    day = DailyLedger(str(log)).day(NOW)
    assert day["cost_usd"] == pytest.approx(0.0)
    assert day["unmeasured_wakes"] == 2


def test_ledger_missing_log_is_an_empty_day(tmp_path):
    day = DailyLedger(str(tmp_path / "never.jsonl")).day(NOW)
    assert day == {"day": "2026-08-29", "wakes": 0, "cost_usd": 0.0,
                   "unmeasured_wakes": 0, "cost_turns_unreported": 0}


def test_ledger_sees_records_appended_after_first_read(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [_record(NOW - timedelta(hours=2), cost=1.0, cycle=1)])
    ledger = DailyLedger(str(log))
    assert ledger.day(NOW)["wakes"] == 1
    _append(log, _record(NOW - timedelta(minutes=5), cost=1.0, cycle=2))
    assert ledger.day(NOW)["wakes"] == 2


def test_ledger_torn_tail_is_not_counted_and_not_cached(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [_record(NOW - timedelta(hours=2), cost=1.0, cycle=1)])
    ledger = DailyLedger(str(log))
    # a second record, mid-write: no newline yet
    _append(log, _record(NOW - timedelta(minutes=5), cost=1.0, cycle=2), newline=False)
    assert ledger.day(NOW)["wakes"] == 1
    # the write completes with only the newline: size grows by one byte
    with open(log, "a") as f:
        f.write("\n")
    assert ledger.day(NOW)["wakes"] == 2


def test_ledger_skips_malformed_and_non_dict_lines(tmp_path):
    log = tmp_path / "s.jsonl"
    with open(log, "w") as f:
        f.write("{not json\n")
        f.write("[1, 2]\n")
        f.write(json.dumps(_record(NOW - timedelta(hours=1), cost=0.5)) + "\n")
    assert DailyLedger(str(log)).day(NOW)["wakes"] == 1


def test_ledger_rolls_to_the_new_day_without_a_write(tmp_path):
    log = tmp_path / "s.jsonl"
    _write(log, [_record(NOW - timedelta(hours=1), cost=9.0)])
    ledger = DailyLedger(str(log))
    assert ledger.day(NOW)["cost_usd"] == pytest.approx(9.0)
    tomorrow = datetime(2026, 8, 30, 0, 0, 1, tzinfo=timezone.utc)
    assert ledger.day(tomorrow) == {"day": "2026-08-30", "wakes": 0, "cost_usd": 0.0,
                                    "unmeasured_wakes": 0, "cost_turns_unreported": 0}


# --- policy -------------------------------------------------------------------


def test_budget_cost_ceiling_checked_before_wake_ceiling():
    budget = WakeBudget(daily_usd=5.0, daily_wakes=48)
    assert budget.exceeded({"cost_usd": 5.0, "wakes": 48}) == "cost"
    assert budget.exceeded({"cost_usd": 4.99, "wakes": 48}) == "wakes"
    assert budget.exceeded({"cost_usd": 4.99, "wakes": 47}) is None


def test_budget_ceilings_are_inclusive_and_zero_rests_immediately():
    budget = WakeBudget(daily_usd=5.0, daily_wakes=10)
    assert budget.exceeded({"cost_usd": 5.0, "wakes": 0}) == "cost"
    assert budget.exceeded({"cost_usd": 0.0, "wakes": 10}) == "wakes"
    assert WakeBudget(0.0, 48).exceeded({"cost_usd": 0.0, "wakes": 0}) == "cost"
    assert WakeBudget(5.0, 0).exceeded({"cost_usd": 0.0, "wakes": 0}) == "wakes"


@pytest.mark.parametrize("usd,wakes", [(-1.0, 48), (float("nan"), 48), (True, 48),
                                       (5.0, -1), (5.0, True), (5.0, 2.5)])
def test_budget_rejects_invalid_ceilings(usd, wakes):
    with pytest.raises(ValueError):
        WakeBudget(usd, wakes)


# --- daemon: resting ----------------------------------------------------------


class _StubSession:
    pass


def _loop(tmp_path, *, log_records, budget, now=NOW, summaries=None, batch_limit=10):
    """A HeartbeatLoop over a real store and a real ledger; run_pending stubbed."""
    log = tmp_path / "s.jsonl"
    _write(log, log_records)
    store = EventStore(str(tmp_path / "events.jsonl"))
    sleeps: list[float] = []
    ran: list[dict] = []
    clock = {"now": now}

    def run_pending(session, s, **kw):
        ran.append(kw)
        return {"ran": 0, "results": []}

    summary_iter = iter(summaries or [])

    def summarize(records, now=None):
        try:
            return next(summary_iter)
        except StopIteration:
            return {"pending_runnable_count": 0, "pending_waiting_count": 0}

    loop = HeartbeatLoop(
        _StubSession(),
        store,
        poll_interval=30.0,
        batch_limit=batch_limit,
        sleep=sleeps.append,
        now=lambda: clock["now"],
        run_pending=run_pending,
        summarize=summarize,
        ledger=DailyLedger(str(log)),
        budget=budget,
    )
    return loop, store, sleeps, ran, clock


def _statuses(store):
    return [
        (r["status"], r["reason"])
        for r in store.read_records()
        if r.get("record_type") == "heartbeat_status"
    ]


def _resting_records(store):
    return [
        r for r in store.read_records()
        if r.get("record_type") == "heartbeat_status" and r["status"] == "resting"
    ]


def test_step_rests_when_cost_ceiling_reached_and_runs_nothing(tmp_path):
    loop, store, sleeps, ran, _ = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=5.25)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    store.append(build_inbound_event(purpose="hello", sender="tony"))
    result = loop.step()
    assert result["state"] == "resting"
    assert ran == []
    assert store.next_pending(now=NOW) is not None  # the event waits
    resting = _resting_records(store)
    assert len(resting) == 1
    assert resting[0]["reason"] == "daily_budget_reached"
    assert resting[0]["created_at"] == NOW.isoformat()  # the loop's clock, not the wall
    detail = resting[0]["detail"]
    assert detail["exceeded"] == "cost"
    assert detail["cost_usd"] == pytest.approx(5.25)
    assert detail["cost_is_lower_bound"] is False
    assert detail["daily_usd"] == 5.0
    assert detail["wakes"] == 1
    assert detail["unmeasured_wakes"] == 0
    assert detail["day"] == "2026-08-29"
    assert detail["resumes_at"] == "2026-08-30T00:00:00+00:00"
    assert "resumed_after_restart" not in detail


def test_step_rests_when_wake_cap_reached(tmp_path):
    records = [_record(NOW - timedelta(minutes=i), cost=0.01, cycle=i) for i in range(1, 4)]
    loop, store, _, ran, _ = _loop(
        tmp_path, log_records=records, budget=WakeBudget(daily_usd=5.0, daily_wakes=3),
    )
    assert loop.step()["state"] == "resting"
    assert ran == []
    assert _statuses(store)[-1] == ("resting", "daily_budget_reached")


def test_rest_detail_labels_partial_cost_as_lower_bound(tmp_path):
    loop, store, _, _, _ = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=6.0, unreported=1)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop.step()
    detail = _resting_records(store)[0]["detail"]
    assert detail["cost_is_lower_bound"] is True
    assert detail["cost_turns_unreported"] == 1


def test_resting_sleep_runs_to_midnight_capped_by_poll(tmp_path):
    loop, _, _, _, clock = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=9.0)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    assert loop.step()["sleep_seconds"] == 30.0
    clock["now"] = datetime(2026, 8, 29, 23, 59, 50, tzinfo=timezone.utc)
    assert loop.step()["sleep_seconds"] == pytest.approx(10.0)


def test_rest_is_recorded_once_and_ingress_during_rest_stays_pending(tmp_path):
    loop, store, _, ran, clock = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=9.0)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop.step()
    clock["now"] = NOW + timedelta(minutes=1)
    store.append(build_inbound_event(purpose="knock", sender="tony"))
    loop.step()
    loop.step()
    assert ran == []
    assert _statuses(store).count(("resting", "daily_budget_reached")) == 1
    assert ("active", "runnable_pending") not in _statuses(store)
    assert store.next_pending(now=clock["now"]) is not None


def test_new_utc_day_resumes_quiet_when_nothing_is_pending(tmp_path):
    loop, store, _, ran, clock = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=9.0)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    assert loop.step()["state"] == "resting"
    clock["now"] = datetime(2026, 8, 30, 0, 0, 5, tzinfo=timezone.utc)
    assert loop.step()["state"] == "quiet"
    assert len(ran) == 1
    statuses = _statuses(store)
    assert statuses[-2] == ("resting", "daily_budget_reached")
    assert statuses[-1][0] == "quiet"


def test_new_utc_day_resumes_active_when_ingress_waited(tmp_path):
    loop, store, _, ran, clock = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=9.0)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
        summaries=[{"pending_runnable_count": 1, "pending_waiting_count": 0}],
    )
    assert loop.step()["state"] == "resting"
    store.append(build_inbound_event(purpose="knock", sender="tony"))
    clock["now"] = datetime(2026, 8, 30, 0, 0, 5, tzinfo=timezone.utc)
    assert loop.step()["state"] == "active"
    assert len(ran) == 1
    statuses = _statuses(store)
    assert statuses[-2] == ("resting", "daily_budget_reached")
    assert statuses[-1] == ("active", "runnable_pending")


def test_restart_during_a_rest_continues_the_episode(tmp_path):
    loop, store, _, _, clock = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=9.0)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop.step()
    # process weather: a new loop over the same store and log, same day
    clock2 = {"now": NOW + timedelta(hours=2)}
    loop2 = HeartbeatLoop(
        _StubSession(), store, poll_interval=30.0, sleep=lambda s: None,
        now=lambda: clock2["now"], run_pending=lambda *a, **k: {"ran": 0, "results": []},
        summarize=lambda r, now=None: {"pending_runnable_count": 0, "pending_waiting_count": 0},
        ledger=DailyLedger(str(tmp_path / "s.jsonl")),
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop2.boot()
    assert loop2.step()["state"] == "resting"
    resting = _resting_records(store)
    assert len(resting) == 2
    assert "resumed_after_restart" not in resting[0]["detail"]
    assert resting[1]["detail"]["resumed_after_restart"] is True
    assert resting[1]["detail"]["day"] == "2026-08-29"


def test_a_second_exceeded_day_starts_its_own_episode(tmp_path):
    loop, store, _, _, clock = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=9.0)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop.step()
    # tomorrow is also over budget from a wake logged just after midnight
    _append(tmp_path / "s.jsonl",
            _record(datetime(2026, 8, 30, 0, 0, 30, tzinfo=timezone.utc), cost=9.0, cycle=2))
    clock["now"] = datetime(2026, 8, 30, 0, 1, 0, tzinfo=timezone.utc)
    assert loop.step()["state"] == "resting"
    resting = _resting_records(store)
    assert [r["detail"]["day"] for r in resting] == ["2026-08-29", "2026-08-30"]
    assert "resumed_after_restart" not in resting[1]["detail"]


def test_budget_checks_before_every_wake_by_running_one_event_per_step(tmp_path):
    loop, _, _, ran, _ = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=0.5)],
        budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop.step()
    assert ran[0]["limit"] == 1


def test_no_budget_means_no_rest_and_configured_batch_limit(tmp_path):
    loop, store, _, ran, _ = _loop(
        tmp_path,
        log_records=[_record(NOW - timedelta(hours=1), cost=999.0)],
        budget=None,
        batch_limit=7,
    )
    assert loop.step()["state"] == "quiet"
    assert ran[0]["limit"] == 7
    assert ("resting", "daily_budget_reached") not in _statuses(store)


def test_step_transitions_carry_the_loop_clock(tmp_path):
    loop, store, _, _, _ = _loop(
        tmp_path, log_records=[], budget=WakeBudget(daily_usd=5.0, daily_wakes=48),
    )
    loop.boot()
    loop.step()
    stamps = [r["created_at"] for r in store.read_records()
              if r.get("record_type") == "heartbeat_status"]
    assert stamps == [NOW.isoformat(), NOW.isoformat()]


# --- envelope: the resident is told ------------------------------------------


def _status_at(store, created_at, status, reason, detail=None):
    """Append a heartbeat_status record with a chosen timestamp."""
    record = {
        "record_type": "heartbeat_status",
        "heartbeat_record_id": f"hb-{created_at}-{status}",
        "status": status,
        "reason": reason,
        "created_at": created_at,
    }
    if detail is not None:
        record["detail"] = detail
    store.append(record)
    return record


REST_DETAIL = {"exceeded": "cost", "cost_usd": 5.01, "daily_usd": 5.0, "wakes": 12,
               "unmeasured_wakes": 0, "cost_turns_unreported": 0,
               "cost_is_lower_bound": False, "daily_wakes": 48,
               "day": "2026-08-29", "resumes_at": "2026-08-30T00:00:00+00:00"}


def _notes(store, event, now):
    from hamutay.events import operational_notes_for_event
    return operational_notes_for_event(store.read_records(), event, now=now)


def test_envelope_note_for_event_pending_across_a_rest_reports_the_overlap(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="waited", sender="tony")
    event["created_at"] = "2026-08-29T17:00:00+00:00"
    store.append(event)
    _status_at(store, "2026-08-29T18:00:00+00:00", "resting", "daily_budget_reached", REST_DETAIL)
    _status_at(store, "2026-08-30T00:00:05+00:00", "active", "runnable_pending")
    notes = _notes(store, event, datetime(2026, 8, 30, 0, 0, 5, tzinfo=timezone.utc))
    assert len(notes) == 1
    note = notes[0]
    assert "rested from 2026-08-29T18:00:00+00:00 to 2026-08-30T00:00:05+00:00" in note
    assert "cost 5.01 of 5.00 USD" in note and "12 wakes" in note
    assert "waited 6h 0m" in note  # overlap, not the 7h queue age


def test_envelope_note_for_event_created_during_an_open_rest(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    detail = {**REST_DETAIL, "exceeded": "wakes", "cost_usd": 1.0, "wakes": 48,
              "unmeasured_wakes": 2}
    _status_at(store, "2026-08-29T18:00:00+00:00", "resting", "daily_budget_reached", detail)
    event = build_inbound_event(purpose="mid-rest", sender="tony")
    event["created_at"] = "2026-08-29T20:00:00+00:00"
    store.append(event)
    notes = _notes(store, event, datetime(2026, 8, 30, 0, 0, 5, tzinfo=timezone.utc))
    assert len(notes) == 1
    assert "has been resting since 2026-08-29T18:00:00+00:00" in notes[0]
    assert "has waited 4h 0m" in notes[0]
    assert "2 unmeasured" in notes[0]
    assert " to " not in notes[0]  # no invented end


def test_envelope_note_labels_lower_bound_cost(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    detail = {**REST_DETAIL, "cost_is_lower_bound": True, "cost_turns_unreported": 3}
    _status_at(store, "2026-08-29T18:00:00+00:00", "resting", "daily_budget_reached", detail)
    event = build_inbound_event(purpose="x", sender="tony")
    event["created_at"] = "2026-08-29T19:00:00+00:00"
    store.append(event)
    notes = _notes(store, event, datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc))
    assert "cost 5.01 (lower bound) of 5.00 USD" in notes[0]


def test_envelope_merges_a_restart_continuation_into_one_episode(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="waited", sender="tony")
    event["created_at"] = "2026-08-29T17:00:00+00:00"
    store.append(event)
    _status_at(store, "2026-08-29T18:00:00+00:00", "resting", "daily_budget_reached", REST_DETAIL)
    _status_at(store, "2026-08-29T20:00:00+00:00", "waking", "boot")
    _status_at(store, "2026-08-29T20:00:01+00:00", "resting", "daily_budget_reached",
               {**REST_DETAIL, "resumed_after_restart": True})
    _status_at(store, "2026-08-30T00:00:05+00:00", "quiet", "chosen_quiet")
    notes = _notes(store, event, datetime(2026, 8, 30, 0, 0, 5, tzinfo=timezone.utc))
    assert len(notes) == 1
    assert "rested from 2026-08-29T18:00:00+00:00 to 2026-08-30T00:00:05+00:00" in notes[0]


def test_envelope_reports_each_of_several_rests(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="long wait", sender="tony")
    event["created_at"] = "2026-08-28T17:00:00+00:00"
    store.append(event)
    _status_at(store, "2026-08-28T18:00:00+00:00", "resting", "daily_budget_reached",
               {**REST_DETAIL, "day": "2026-08-28"})
    _status_at(store, "2026-08-29T00:00:05+00:00", "quiet", "chosen_quiet")
    _status_at(store, "2026-08-29T09:00:00+00:00", "resting", "daily_budget_reached", REST_DETAIL)
    _status_at(store, "2026-08-30T00:00:05+00:00", "active", "runnable_pending")
    notes = _notes(store, event, datetime(2026, 8, 30, 0, 0, 5, tzinfo=timezone.utc))
    assert len(notes) == 2
    assert "2026-08-28T18:00:00+00:00" in notes[0]
    assert "2026-08-29T09:00:00+00:00" in notes[1]


def test_no_envelope_note_when_nothing_rested(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="plain", sender="tony")
    store.append(event)
    _status_at(store, NOW.isoformat(), "quiet", "chosen_quiet")
    assert _notes(store, event, NOW) == []


def test_no_envelope_note_for_a_rest_that_ended_before_the_event_existed(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _status_at(store, "2026-08-28T18:00:00+00:00", "resting", "daily_budget_reached", detail={})
    _status_at(store, "2026-08-29T00:00:05+00:00", "quiet", "chosen_quiet")
    event = build_inbound_event(purpose="later", sender="tony")
    event["created_at"] = "2026-08-29T10:00:00+00:00"
    store.append(event)
    assert _notes(store, event, NOW) == []


def test_no_envelope_note_when_event_has_no_created_at(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _status_at(store, "2026-08-29T18:00:00+00:00", "resting", "daily_budget_reached", REST_DETAIL)
    event = build_inbound_event(purpose="undated", sender="tony")
    event.pop("created_at", None)
    assert _notes(store, event, NOW + timedelta(hours=1)) == []


def test_envelope_carries_operational_notes():
    from hamutay.events import build_event_envelope

    event = build_inbound_event(purpose="p", sender="tony")
    text = build_event_envelope(
        event, [], "run-1", operational_notes=["heartbeat rested from A to B"],
    )
    assert json.loads(text)["operational_notes"] == ["heartbeat rested from A to B"]


def test_envelope_omits_operational_notes_when_none():
    from hamutay.events import build_event_envelope

    event = build_inbound_event(purpose="p", sender="tony")
    assert "operational_notes" not in json.loads(build_event_envelope(event, [], "run-1"))


# --- CLI and constitution -----------------------------------------------------


def test_parser_budget_defaults_on():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x"])
    assert args.daily_budget_usd == 5.0
    assert args.daily_wake_cap == 48
    assert args.no_daily_budget is False


def test_resolve_budget_from_args_disabled_loudly():
    from hamutay.heartbeat import build_parser, resolve_budget

    args = build_parser().parse_args(["--log-path", "x", "--no-daily-budget"])
    budget, note = resolve_budget(args)
    assert budget is None
    assert "NO DAILY BUDGET" in note


def test_resolve_budget_from_args_enabled_states_the_numbers():
    from hamutay.heartbeat import build_parser, resolve_budget

    args = build_parser().parse_args(
        ["--log-path", "x", "--daily-budget-usd", "2.5", "--daily-wake-cap", "7"]
    )
    budget, note = resolve_budget(args)
    assert budget.daily_usd == 2.5 and budget.daily_wakes == 7
    assert "2.50 USD/day" in note and "7 wakes/day" in note


def test_resolve_budget_rejects_negative_ceilings_at_launch():
    from hamutay.heartbeat import build_parser, resolve_budget

    args = build_parser().parse_args(["--log-path", "x", "--daily-budget-usd", "-1"])
    with pytest.raises(SystemExit, match="daily budget"):
        resolve_budget(args)


def test_constitution_states_the_budget_as_an_operational_fact():
    from hamutay.heartbeat import CONSTITUTION

    assert "budgeted per UTC day" in CONSTITUTION
    assert "rests until midnight UTC" in CONSTITUTION


def test_built_constitution_states_the_active_numbers():
    from hamutay.heartbeat import build_constitution

    text = build_constitution(WakeBudget(daily_usd=5.0, daily_wakes=48))
    assert "cost ceiling of 5.00 USD" in text
    assert "count ceiling of 48 wakes" in text
    assert "wake ends" in text  # the rest of the constitution is intact


def test_built_constitution_is_true_when_budget_is_disabled():
    from hamutay.heartbeat import build_constitution

    text = build_constitution(None)
    assert "not budgeted" in text
    assert "budgeted per UTC day" not in text
    assert "disabled" in text
