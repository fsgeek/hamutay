"""Independent adversarial validation for the wake budget governor.

These tests are intentionally separate from the implementer's TDD suite.  They
exercise malformed/torn ledger input, UTC boundaries, repeated rests, envelope
wiring, and CLI interactions from the public feature surface.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hamutay.events import (
    EventStore,
    build_inbound_event,
    operational_notes_for_event,
    run_next_event,
)
from hamutay.heartbeat import (
    DailyLedger,
    HeartbeatLoop,
    WakeBudget,
    build_constitution,
    build_parser,
    resolve_budget,
)


UTC = timezone.utc
DAY = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
_MISSING = object()


def _cycle(
    timestamp: str,
    *,
    cost: object = _MISSING,
    cost_turns_unreported: object = _MISSING,
    provider: str = "openrouter",
    cycle: int = 1,
) -> dict:
    usage: dict = {"input_tokens": 10, "output_tokens": 2}
    if cost is not _MISSING:
        usage["cost_usd"] = cost
    if cost_turns_unreported is not _MISSING:
        usage["cost_turns_unreported"] = cost_turns_unreported
    return {
        "cycle": cycle,
        "timestamp": timestamp,
        "launch": {"provider": provider, "model": "validation-model"},
        "usage": usage,
        "state": {},
    }


def _write_jsonl(path, records) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def _heartbeat_records(store: EventStore) -> list[dict]:
    return [
        record
        for record in store.read_records()
        if record.get("record_type") == "heartbeat_status"
    ]


def _status(created_at: str, status: str, *, detail=_MISSING) -> dict:
    record = {
        "record_type": "heartbeat_status",
        "heartbeat_record_id": str(uuid4()),
        "status": status,
        "reason": (
            "daily_budget_reached" if status == "resting" else "validation"
        ),
        "created_at": created_at,
    }
    if detail is not _MISSING:
        record["detail"] = detail
    return record


# --- ledger -----------------------------------------------------------------


def test_ledger_treats_naive_and_z_timestamps_as_utc_and_includes_midnight(
    tmp_path,
):
    log = tmp_path / "session.jsonl"
    _write_jsonl(
        log,
        [
            _cycle("2026-08-28T23:59:59Z", cost=9.0, cycle=1),
            _cycle("2026-08-29T00:00:00", cost=1.0, cycle=2),
            _cycle("2026-08-29T00:00:01Z", cost=2.0, cycle=3),
        ],
    )

    day = DailyLedger(str(log)).day(DAY)

    assert day == {
        "day": "2026-08-29",
        "wakes": 2,
        "cost_usd": pytest.approx(3.0),
        "unmeasured_wakes": 0,
        "cost_turns_unreported": 0,
    }


def test_ledger_ignores_malformed_json_without_losing_valid_cycles(tmp_path):
    log = tmp_path / "session.jsonl"
    valid = json.dumps(_cycle("2026-08-29T01:00:00Z", cost=1.25))
    log.write_text("{not-json\n" + valid + "\n")

    assert DailyLedger(str(log)).day(DAY)["cost_usd"] == pytest.approx(1.25)


def test_ledger_ignores_non_object_json_records(tmp_path):
    """Only cycle-record objects can contribute to the ledger."""
    log = tmp_path / "session.jsonl"
    valid = _cycle("2026-08-29T01:00:00Z", cost=1.25)
    _write_jsonl(log, [[], "not a record", 7, None, valid])

    day = DailyLedger(str(log)).day(DAY)

    assert day["wakes"] == 1
    assert day["cost_usd"] == pytest.approx(1.25)


def test_bool_and_string_costs_are_unmeasured_not_numeric(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_jsonl(
        log,
        [
            _cycle("2026-08-29T01:00:00Z", cost=True, cycle=1),
            _cycle("2026-08-29T02:00:00Z", cost="2.50", cycle=2),
        ],
    )

    day = DailyLedger(str(log)).day(DAY)

    assert day["wakes"] == 2
    assert day["cost_usd"] == pytest.approx(0.0)
    assert day["unmeasured_wakes"] == 2


def test_ledger_discards_cached_rows_when_log_shrinks(tmp_path):
    log = tmp_path / "session.jsonl"
    old = [
        _cycle(f"2026-08-29T0{hour}:00:00Z", cost=1.0, cycle=hour)
        for hour in range(1, 6)
    ]
    _write_jsonl(log, old)
    ledger = DailyLedger(str(log))
    assert ledger.day(DAY)["wakes"] == 5
    old_size = log.stat().st_size

    _write_jsonl(log, [_cycle("2026-08-29T09:00:00Z", cost=0.25, cycle=99)])
    assert log.stat().st_size < old_size

    day = ledger.day(DAY)
    assert day["wakes"] == 1
    assert day["cost_usd"] == pytest.approx(0.25)


def test_torn_append_is_ignored_until_the_line_is_complete(tmp_path):
    log = tmp_path / "session.jsonl"
    first = _cycle("2026-08-29T01:00:00Z", cost=1.0, cycle=1)
    second_text = json.dumps(
        _cycle("2026-08-29T02:00:00Z", cost=2.0, cycle=2)
    )
    _write_jsonl(log, [first])
    ledger = DailyLedger(str(log))
    assert ledger.day(DAY)["wakes"] == 1

    split = len(second_text) // 2
    with log.open("a") as stream:
        stream.write(second_text[:split])
    assert ledger.day(DAY)["wakes"] == 1

    with log.open("a") as stream:
        stream.write(second_text[split:] + "\n")
    day = ledger.day(DAY)
    assert day["wakes"] == 2
    assert day["cost_usd"] == pytest.approx(3.0)


def test_torn_tail_is_reread_when_newline_lands_without_changing_file_size(
    tmp_path,
):
    log = tmp_path / "session.jsonl"
    record = json.dumps(_cycle("2026-08-29T02:00:00Z", cost=2.0))
    log.write_bytes(record.encode() + b"\r")
    size = log.stat().st_size
    ledger = DailyLedger(str(log))

    assert ledger.day(DAY)["wakes"] == 0

    with log.open("r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"\n")
    assert log.stat().st_size == size

    day = ledger.day(DAY)
    assert day["wakes"] == 1
    assert day["cost_usd"] == pytest.approx(2.0)


def test_numeric_anthropic_cost_never_reaches_the_cost_ceiling(tmp_path):
    """Anthropic-direct wakes count, but their cost is never metered here."""
    log = tmp_path / "session.jsonl"
    _write_jsonl(
        log,
        [_cycle("2026-08-29T01:00:00Z", cost=5.0, provider="anthropic")],
    )

    day = DailyLedger(str(log)).day(DAY)

    assert day["wakes"] == 1
    assert day["cost_usd"] == pytest.approx(0.0)
    assert day["unmeasured_wakes"] == 0
    assert WakeBudget(5.0, 48).exceeded(day) is None


def test_unpriced_anthropic_wake_is_governed_by_wake_count_only(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_jsonl(
        log,
        [_cycle("2026-08-29T01:00:00Z", provider="anthropic")],
    )

    day = DailyLedger(str(log)).day(DAY)

    assert day["cost_usd"] == pytest.approx(0.0)
    assert day["unmeasured_wakes"] == 0
    assert WakeBudget(5.0, 1).exceeded(day) == "wakes"


# --- daemon and policy -------------------------------------------------------


class _Session:
    pass


def _quiet_summary(_records, *, now=None) -> dict:
    del now
    return {"pending_runnable_count": 0, "pending_waiting_count": 0}


def test_consecutive_exceeded_utc_days_each_persist_a_rest_record(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_jsonl(log, [_cycle("2026-08-29T23:00:00Z", cost=6.0, cycle=1)])
    ledger = DailyLedger(str(log))
    store = EventStore(tmp_path / "events.jsonl")
    clock = {"now": datetime(2026, 8, 29, 23, 59, 59, tzinfo=UTC)}
    loop = HeartbeatLoop(
        _Session(),
        store,
        now=lambda: clock["now"],
        ledger=ledger,
        budget=WakeBudget(5.0, 48),
        run_pending=lambda *_args, **_kwargs: {"ran": 0, "results": []},
        summarize=_quiet_summary,
    )

    assert loop.step()["state"] == "resting"
    with log.open("a") as stream:
        stream.write(
            json.dumps(_cycle("2026-08-30T00:00:00Z", cost=7.0, cycle=2))
            + "\n"
        )
    clock["now"] = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
    assert loop.step()["state"] == "resting"

    rests = [
        record
        for record in _heartbeat_records(store)
        if record["status"] == "resting"
    ]
    assert [record["detail"]["day"] for record in rests] == [
        "2026-08-29",
        "2026-08-30",
    ]
    assert [record["created_at"] for record in rests] == [
        "2026-08-29T23:59:59+00:00",
        "2026-08-30T00:00:00+00:00",
    ]
    assert all("resumed_after_restart" not in record["detail"] for record in rests)


def test_rest_at_exact_midnight_resumes_next_midnight_and_never_sleeps_negative(
    tmp_path,
):
    class _ExceededLedger:
        def day(self, now):
            return {
                "day": now.astimezone(UTC).date().isoformat(),
                "wakes": 1,
                "cost_usd": 10.0,
                "unmeasured_wakes": 0,
            }

    store = EventStore(tmp_path / "events.jsonl")
    midnight = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
    loop = HeartbeatLoop(
        _Session(),
        store,
        now=lambda: midnight,
        poll_interval=100_000,
        ledger=_ExceededLedger(),
        budget=WakeBudget(5.0, 48),
    )

    result = loop.step()
    detail = _heartbeat_records(store)[0]["detail"]

    assert result["sleep_seconds"] == pytest.approx(86_400.0)
    assert result["sleep_seconds"] >= 0
    assert detail["resumes_at"] == "2026-08-31T00:00:00+00:00"


def test_budgeted_batch_limit_remains_one_when_configured_as_one(tmp_path):
    calls: list[dict] = []
    store = EventStore(tmp_path / "events.jsonl")

    class _UnderBudgetLedger:
        def day(self, _now):
            return {
                "day": "2026-08-29",
                "wakes": 0,
                "cost_usd": 0.0,
                "unmeasured_wakes": 0,
            }

    loop = HeartbeatLoop(
        _Session(),
        store,
        now=lambda: DAY,
        batch_limit=1,
        ledger=_UnderBudgetLedger(),
        budget=WakeBudget(5.0, 48),
        run_pending=lambda *_args, **kwargs: (
            calls.append(kwargs) or {"ran": 0, "results": []}
        ),
        summarize=_quiet_summary,
    )

    loop.step()

    assert calls[0]["limit"] == 1


def test_non_resting_step_records_active_when_ingress_lands_inside_batch(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")

    class _UnderBudgetLedger:
        def day(self, _now):
            return {
                "day": "2026-08-29",
                "wakes": 0,
                "cost_usd": 0.0,
                "unmeasured_wakes": 0,
            }

    loop = HeartbeatLoop(
        _Session(),
        store,
        now=lambda: DAY,
        ledger=_UnderBudgetLedger(),
        budget=WakeBudget(5.0, 48),
        # next_pending() above sees no event; this simulates an event claimed
        # after that check but before/during run_pending().
        run_pending=lambda *_args, **_kwargs: {"ran": 1, "results": []},
        summarize=_quiet_summary,
    )

    loop.step()

    transitions = [
        (record["status"], record["reason"])
        for record in _heartbeat_records(store)
    ]
    assert transitions == [
        ("active", "runnable_pending"),
        ("quiet", "awaiting_first_event"),
    ]


def test_zero_explicit_cost_ceiling_rests_immediately():
    args = build_parser().parse_args(
        ["--log-path", "session.jsonl", "--daily-budget-usd", "0"]
    )

    budget, _note = resolve_budget(args)

    assert budget is not None
    assert budget.exceeded({"cost_usd": 0.0, "wakes": 0}) == "cost"


@pytest.mark.parametrize("value", ["-1", "nan"])
def test_negative_or_nan_explicit_cost_ceiling_is_rejected_at_launch(value):
    args = build_parser().parse_args(
        ["--log-path", "session.jsonl", "--daily-budget-usd", value]
    )

    with pytest.raises(SystemExit, match="daily budget"):
        resolve_budget(args)


@pytest.mark.parametrize(
    ("daily_usd", "daily_wakes"),
    [(-1, 48), (float("nan"), 48), (True, 48), (5.0, -1), (5.0, True)],
)
def test_wake_budget_rejects_negative_nan_and_boolean_ceilings(
    daily_usd,
    daily_wakes,
):
    with pytest.raises(ValueError):
        WakeBudget(daily_usd, daily_wakes)


def test_no_daily_budget_wins_over_explicit_ceiling_values():
    args = build_parser().parse_args(
        [
            "--log-path",
            "session.jsonl",
            "--daily-budget-usd",
            "0.01",
            "--daily-wake-cap",
            "1",
            "--no-daily-budget",
        ]
    )

    budget, note = resolve_budget(args)

    assert budget is None
    assert "NO DAILY BUDGET" in note


# --- operational notes and wiring -------------------------------------------


def test_restart_continues_rest_episode_and_envelope_merges_it(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_jsonl(log, [_cycle("2026-08-29T17:30:00Z", cost=6.0)])
    store = EventStore(tmp_path / "events.jsonl")
    event = build_inbound_event(purpose="wait through restart", sender="tony")
    event["created_at"] = "2026-08-29T17:00:00Z"
    store.append(event)
    clock = {"now": datetime(2026, 8, 29, 18, 0, tzinfo=UTC)}
    common = {
        "now": lambda: clock["now"],
        "ledger": DailyLedger(str(log)),
        "budget": WakeBudget(5.0, 48),
        "run_pending": lambda *_args, **_kwargs: {"ran": 0, "results": []},
        "summarize": _quiet_summary,
    }

    first_loop = HeartbeatLoop(_Session(), store, **common)
    assert first_loop.step()["state"] == "resting"

    clock["now"] = datetime(2026, 8, 29, 19, 0, tzinfo=UTC)
    restarted_loop = HeartbeatLoop(_Session(), store, **common)
    restarted_loop.boot()
    clock["now"] = datetime(2026, 8, 29, 19, 5, tzinfo=UTC)
    assert restarted_loop.step()["state"] == "resting"

    store.append(_status("2026-08-30T00:00:00Z", "active"))
    session = _EnvelopeCapturingSession()
    completed = run_next_event(
        session,
        store,
        now=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
    )

    rests = [
        record
        for record in _heartbeat_records(store)
        if record["status"] == "resting"
    ]
    assert len(rests) == 2
    assert rests[0]["created_at"] == "2026-08-29T18:00:00+00:00"
    assert "resumed_after_restart" not in rests[0]["detail"]
    assert rests[1]["created_at"] == "2026-08-29T19:05:00+00:00"
    assert rests[1]["detail"]["resumed_after_restart"] is True
    assert completed["status"] == "completed"
    assert len(session.envelope["operational_notes"]) == 1
    assert "rested from 2026-08-29T18:00:00+00:00" in (
        session.envelope["operational_notes"][0]
    )


def test_partial_cost_is_lower_bound_in_rest_detail_and_envelope_note(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_jsonl(
        log,
        [
            _cycle(
                "2026-08-29T17:30:00Z",
                cost=5.01,
                cost_turns_unreported=2,
            )
        ],
    )
    store = EventStore(tmp_path / "events.jsonl")
    event = build_inbound_event(purpose="wait for measured rest", sender="tony")
    event["created_at"] = "2026-08-29T17:00:00Z"
    store.append(event)
    loop = HeartbeatLoop(
        _Session(),
        store,
        now=lambda: datetime(2026, 8, 29, 18, 0, tzinfo=UTC),
        ledger=DailyLedger(str(log)),
        budget=WakeBudget(5.0, 48),
    )

    assert loop.step()["state"] == "resting"
    rest = _heartbeat_records(store)[0]
    assert rest["detail"]["cost_usd"] == pytest.approx(5.01)
    assert rest["detail"]["cost_turns_unreported"] == 2
    assert rest["detail"]["unmeasured_wakes"] == 1
    assert rest["detail"]["cost_is_lower_bound"] is True

    store.append(_status("2026-08-30T00:00:00Z", "quiet"))
    notes = operational_notes_for_event(
        store.read_records(),
        event,
        now=datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
    )
    assert len(notes) == 1
    assert "cost 5.01 (lower bound) of 5.00 USD" in notes[0]


def test_open_rest_note_has_since_wording_and_no_invented_end():
    event = build_inbound_event(purpose="claimed during rest", sender="tony")
    event["created_at"] = "2026-08-29T19:00:00Z"
    records = [
        _status(
            "2026-08-29T18:00:00Z",
            "resting",
            detail={"day": "2026-08-29", "wakes": 48},
        )
    ]
    now = datetime(2026, 8, 29, 21, 0, tzinfo=UTC)

    notes = operational_notes_for_event(records, event, now=now)

    assert len(notes) == 1
    assert notes[0].startswith(
        "heartbeat has been resting since 2026-08-29T18:00:00+00:00"
    )
    assert "heartbeat rested from" not in notes[0]
    assert f" to {now.isoformat()}" not in notes[0]


@pytest.mark.parametrize(
    ("created_at", "waited"),
    [
        ("2026-08-29T17:00:00Z", "6h 0m"),
        ("2026-08-29T20:00:00Z", "4h 0m"),
    ],
)
def test_event_wait_is_only_its_overlap_with_rest(created_at, waited):
    event = build_inbound_event(purpose="overlap", sender="tony")
    event["created_at"] = created_at
    records = [
        _status("2026-08-29T18:00:00Z", "resting"),
        _status("2026-08-30T00:00:00Z", "quiet"),
    ]

    notes = operational_notes_for_event(
        records,
        event,
        now=datetime(2026, 8, 30, 1, 0, tzinfo=UTC),
    )

    assert len(notes) == 1
    assert f"this event waited {waited} of it" in notes[0]


def test_build_constitution_reports_the_actual_budget_configuration():
    budgeted = build_constitution(WakeBudget(1.25, 7))
    unbudgeted = build_constitution(None)

    assert "cost ceiling of 1.25 USD" in budgeted
    assert "count ceiling of 7 wakes" in budgeted
    assert "steward disabled" not in budgeted
    assert "steward disabled the daily cost and count ceilings" in unbudgeted
    assert "cost ceiling of 1.25 USD" not in unbudgeted
    assert "count ceiling of 7 wakes" not in unbudgeted


def test_operational_notes_include_multiple_rests_and_missing_detail():
    event = build_inbound_event(purpose="wait through both", sender="tony")
    event["created_at"] = "2026-08-29T17:00:00Z"
    records = [
        _status("2026-08-29T18:00:00Z", "resting"),
        _status("2026-08-30T00:00:00Z", "quiet"),
        _status(
            "2026-08-30T18:00:00Z",
            "resting",
            detail={"wakes": 48, "unmeasured_wakes": 2},
        ),
        _status("2026-08-31T00:00:00Z", "active"),
    ]

    notes = operational_notes_for_event(
        records,
        event,
        now=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )

    assert len(notes) == 2
    assert "daily budget reached" in notes[0]
    assert "cost" not in notes[0]
    assert "48 wakes" in notes[1]
    assert "2 unmeasured" in notes[1]


def test_event_without_created_at_gets_no_unprovable_rest_note():
    event = build_inbound_event(purpose="damaged old event", sender="tony")
    event.pop("created_at")
    records = [_status("2026-08-29T18:00:00Z", "resting")]

    assert operational_notes_for_event(records, event, now=DAY) == []


class _EnvelopeCapturingSession:
    def __init__(self):
        self._prior_states = []
        self._bridge = None
        self._state = {}
        self._last_raw_output = {}
        self._last_state_validation = None
        self.cycle = 0
        self.envelope = None

    def exchange(self, envelope, **_kwargs):
        self.envelope = json.loads(envelope)
        self.cycle += 1
        self._prior_states.append((self.cycle, uuid4(), {}, ""))
        return "handled"


def test_run_next_event_wires_all_rest_notes_into_the_envelope(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = build_inbound_event(purpose="waited", sender="tony")
    event["created_at"] = "2026-08-29T17:00:00Z"
    store.append(event)
    store.append(_status("2026-08-29T18:00:00Z", "resting"))
    store.append(_status("2026-08-30T00:00:00Z", "quiet"))
    store.append(_status("2026-08-30T18:00:00Z", "resting"))
    store.append(_status("2026-08-31T00:00:00Z", "active"))
    session = _EnvelopeCapturingSession()

    completed = run_next_event(
        session,
        store,
        now=datetime(2026, 8, 31, 0, 0, tzinfo=UTC),
    )

    assert completed["status"] == "completed"
    assert len(session.envelope["operational_notes"]) == 2
