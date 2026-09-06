"""Independent adversarial validation for quiet-with-reason.

These tests intentionally exercise orderings and production compositions that
the implementing session's happy-path suite does not cover.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from itertools import permutations
from uuid import uuid4

import pytest

from hamutay.events import (
    EventStore,
    build_inbound_event,
    build_pending_event,
    format_event_report,
    joined_quiet_declarations,
    operational_notes_for_event,
    quiet_declaration_for_latest_wake,
    run_next_event,
    summarize_event_log,
)
from hamutay.heartbeat import (
    CONSTITUTION,
    HeartbeatLoop,
    build_parser,
    derive_quiet_reason,
)
from hamutay.taste_open import ExchangeResult, OpenTasteSession
from hamutay.tools.executor import ToolExecutor


UTC = timezone.utc


def _declaration(
    record_id: str,
    *,
    cycle: int = 1,
    reason: object = "resident words",
    created_at: str = "2026-09-05T00:00:00+00:00",
    until: str | None = None,
) -> dict:
    record = {
        "record_type": "quiet_declaration",
        "declaration_id": str(uuid4()),
        "declared_by_cycle": cycle,
        "declared_by_record_id": record_id,
        "reason": reason,
        "created_at": created_at,
    }
    if until is not None:
        record["until"] = until
    return record


def _completed(
    record_id: str,
    *,
    cycle: int = 1,
    completed_at: str = "2026-09-05T01:00:00+00:00",
    event_id: str | None = None,
) -> dict:
    return {
        "record_type": "event_status",
        "event_id": event_id or str(uuid4()),
        "event_type": "inbound_message",
        "status": "completed",
        "run_id": str(uuid4()),
        "completed_at": completed_at,
        "wake_cycle": cycle,
        "result_record_id": record_id,
        "response_text": "done",
    }


def _failed(*, event_id: str | None = None) -> dict:
    return {
        "record_type": "event_status",
        "event_id": event_id or str(uuid4()),
        "event_type": "inbound_message",
        "status": "failed",
        "run_id": str(uuid4()),
        "failed_at": "2026-09-05T02:00:00+00:00",
        "error_type": "RuntimeError",
        "error": "wake failed",
    }


def _expired(*, event_id: str | None = None) -> dict:
    return {
        "record_type": "event_status",
        "event_id": event_id or str(uuid4()),
        "event_type": "inbound_message",
        "status": "expired",
        "expired_at": "2026-09-05T02:00:00+00:00",
    }


def _running(event_id: str, started_at: str) -> dict:
    return {
        "record_type": "event_status",
        "event_id": event_id,
        "event_type": "inbound_message",
        "status": "running",
        "run_id": str(uuid4()),
        "started_at": started_at,
    }


class _NaturalBackend:
    wake_mode = "natural"

    def __init__(self, actions=(), *, fail: Exception | None = None):
        self.actions = list(actions)
        self.fail = fail
        self.calls: list[dict] = []
        self.terminal_calls: list[dict] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        del model, messages, experiment_label
        self.calls.append({"system": system, "extra_tools": extra_tools})
        for tool, parameters in self.actions:
            tool_executor.execute(tool, parameters)
        if self.fail is not None:
            raise self.fail
        return ExchangeResult(
            raw_output={"response": "done"},
            tool_activity=tool_executor.activity_log if tool_executor else None,
            stop_reason="end_turn",
        )

    def call_terminal_surface(
        self,
        model,
        system,
        messages,
        experiment_label,
        terminal_surface,
    ):
        del model, messages, experiment_label
        self.terminal_calls.append(
            {"system": system, "terminal_surface": terminal_surface}
        )
        return ExchangeResult(
            raw_output={"response": "bounded result"},
            stop_reason="tool_use",
        )


class _TerminalBackend:
    def __init__(self):
        self.calls: list[dict] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        del model, messages, experiment_label, tool_executor
        self.calls.append({"system": system, "extra_tools": extra_tools})
        return ExchangeResult(
            raw_output={"response": "done"}, stop_reason="end_turn"
        )


def _session(
    tmp_path,
    backend,
    *,
    wake_mode: str = "natural",
    name: str = "session",
    system_prompt_prefix: str | None = None,
) -> OpenTasteSession:
    return OpenTasteSession(
        model="validation-model",
        backend=backend,
        log_path=str(tmp_path / f"{name}.jsonl"),
        event_log_path=str(tmp_path / f"{name}.events.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
        wake_mode=wake_mode,
        system_prompt_prefix=system_prompt_prefix,
    )


def _terminal_surface() -> dict:
    return {
        "tool_name": "finish_bounded_work",
        "description": "Finish one bounded event.",
        "input_schema": {
            "type": "object",
            "properties": {"response": {"type": "string"}},
            "required": ["response"],
            "additionalProperties": False,
        },
        "tool_choice": "force",
        "state_update": {"response_field": "response"},
    }


# Join, orphan, failure, and expiry semantics.


@pytest.mark.parametrize("order", list(permutations(("joined", "completed", "orphan"))))
def test_join_and_orphan_semantics_are_independent_of_every_append_order(order):
    joined_id = str(uuid4())
    records_by_name = {
        "joined": _declaration(joined_id, reason="joined"),
        "completed": _completed(joined_id),
        "orphan": _declaration(str(uuid4()), cycle=2, reason="orphan"),
    }
    records = [records_by_name[name] for name in order]

    declaration = quiet_declaration_for_latest_wake(records)
    joined, orphan_count = joined_quiet_declarations(records)

    assert declaration == records_by_name["joined"]
    assert joined == [records_by_name["joined"]]
    assert orphan_count == 1
    assert derive_quiet_reason(records) == "declared_quiet"


@pytest.mark.parametrize("declaration_position", (0, 1, 2))
def test_later_failed_wake_wins_even_if_old_declaration_is_appended_later(
    declaration_position,
):
    record_id = str(uuid4())
    declaration = _declaration(record_id)
    records = [_completed(record_id), _failed()]
    records.insert(declaration_position, declaration)

    assert quiet_declaration_for_latest_wake(records) is None
    assert derive_quiet_reason(records) == "undeclared_quiet"
    assert summarize_event_log(records)["latest_quiet_declaration"] == declaration


@pytest.mark.parametrize(
    ("records_order", "expected"),
    (("expired_first", "declared_quiet"), ("expired_last", "starved_expired")),
)
def test_expiry_applies_only_when_appended_after_the_latest_wake_outcome(
    records_order, expected
):
    record_id = str(uuid4())
    declaration = _declaration(record_id)
    completed = _completed(record_id)
    expired = _expired()
    records = (
        [expired, declaration, completed]
        if records_order == "expired_first"
        else [declaration, completed, expired]
    )

    assert derive_quiet_reason(records) == expected


def test_expiry_before_a_later_failed_wake_does_not_mask_undeclared_failure():
    record_id = str(uuid4())
    records = [_declaration(record_id), _completed(record_id), _expired(), _failed()]

    assert derive_quiet_reason(records) == "undeclared_quiet"


def test_multiple_historical_declarations_for_one_wake_use_last_append():
    record_id = str(uuid4())
    first = _declaration(record_id, reason="first")
    last = _declaration(record_id, reason="last")
    records = [first, _completed(record_id), last]

    assert quiet_declaration_for_latest_wake(records) == last


def test_failed_event_commit_leaves_declaration_orphaned_and_inert(tmp_path, monkeypatch):
    backend = _NaturalBackend(
        actions=[("declare_quiet", {"reason": "will not bind"})]
    )
    session = _session(tmp_path, backend)
    store = session._event_store
    store.append(build_inbound_event(purpose="trigger failure", sender="tony"))

    def fail_completed_commit(**kwargs):
        del kwargs
        raise OSError("completion write failed")

    monkeypatch.setattr(store, "append_completed_atomic", fail_completed_commit)

    with pytest.raises(OSError, match="completion write failed"):
        run_next_event(session, store)

    records = store.read_records()
    summary = summarize_event_log(records)
    assert [r["status"] for r in records if r.get("record_type") == "event_status"] == [
        "pending",
        "running",
        "failed",
    ]
    assert summary["orphan_quiet_declaration_count"] == 1
    assert summary["latest_quiet_declaration"] is None
    assert derive_quiet_reason(records) == "awaiting_first_event"


# Executor validation and last-valid-call behavior.


def test_non_string_reason_is_invalid_and_does_not_erase_an_earlier_valid_call(
    tmp_path,
):
    executor = ToolExecutor(
        project_root=tmp_path, cycle=8, scheduled_by_record_id=uuid4()
    )
    assert "error" not in executor.execute("declare_quiet", {"reason": "valid"})

    result = executor.execute("declare_quiet", {"reason": ["not", "a", "string"]})

    assert "error" in result
    assert executor.pending_quiet_declaration["reason"] == "valid"


def test_present_but_empty_until_is_invalid_and_preserves_the_last_valid_call(
    tmp_path,
):
    executor = ToolExecutor(
        project_root=tmp_path, cycle=8, scheduled_by_record_id=uuid4()
    )
    assert "error" not in executor.execute("declare_quiet", {"reason": "valid"})

    result = executor.execute(
        "declare_quiet", {"reason": "must not replace", "until": ""}
    )

    assert "error" in result
    assert executor.pending_quiet_declaration["reason"] == "valid"


def test_only_last_valid_declaration_is_stored_but_every_attempt_is_logged(tmp_path):
    backend = _NaturalBackend(
        actions=[
            ("declare_quiet", {"reason": "first"}),
            ("declare_quiet", {"reason": "last valid"}),
            ("declare_quiet", {}),
        ]
    )
    session = _session(tmp_path, backend)

    session.exchange("wake", event_managed=True)

    declarations = [
        record
        for record in session._event_store.read_records()
        if record.get("record_type") == "quiet_declaration"
    ]
    log_record = json.loads((tmp_path / "session.jsonl").read_text().splitlines()[-1])
    attempts = [
        entry
        for entry in log_record["tool_activity_full"]
        if entry.get("tool") == "declare_quiet"
    ]
    assert len(declarations) == 1
    assert declarations[0]["reason"] == "last valid"
    assert len(attempts) == 3
    assert "error" in attempts[-1]["result"]


# Event-managed capability scope and prompt/tool agreement.


def test_run_next_event_offers_and_names_declare_quiet(tmp_path):
    backend = _NaturalBackend()
    session = _session(tmp_path, backend)
    session._event_store.append(
        build_inbound_event(purpose="managed wake", sender="tony")
    )

    run_next_event(session, session._event_store)

    offered = [tool["name"] for tool in backend.calls[-1]["extra_tools"]]
    assert "declare_quiet" in offered
    assert "declare_quiet" in backend.calls[-1]["system"]


def test_direct_natural_exchange_neither_offers_nor_names_declare_quiet(tmp_path):
    backend = _NaturalBackend()
    session = _session(tmp_path, backend)

    session.exchange("direct")

    offered = [tool["name"] for tool in backend.calls[-1]["extra_tools"]]
    assert "declare_quiet" not in offered
    assert "declare_quiet" not in backend.calls[-1]["system"]


def test_terminal_mode_neither_offers_nor_names_declare_quiet(tmp_path):
    backend = _TerminalBackend()
    session = _session(tmp_path, backend, wake_mode="terminal")

    session.exchange("terminal", event_managed=True)

    offered = [tool["name"] for tool in backend.calls[-1]["extra_tools"]]
    assert "declare_quiet" not in offered
    assert "declare_quiet" not in backend.calls[-1]["system"]


def test_natural_event_with_terminal_surface_neither_offers_nor_names_tool(tmp_path):
    backend = _NaturalBackend()
    session = _session(tmp_path, backend)

    session.exchange(
        "bounded", event_managed=True, terminal_surface=_terminal_surface()
    )

    assert len(backend.calls) == 0
    assert len(backend.terminal_calls) == 1
    assert "declare_quiet" not in backend.terminal_calls[0]["system"]


def test_production_constitution_does_not_name_unoffered_tool_on_terminal_surface(
    tmp_path,
):
    """The daemon combines this prefix with event-managed terminal surfaces."""
    backend = _NaturalBackend()
    session = _session(
        tmp_path, backend, system_prompt_prefix=CONSTITUTION, name="production"
    )

    session.exchange(
        "bounded", event_managed=True, terminal_surface=_terminal_surface()
    )

    assert len(backend.calls) == 0
    assert len(backend.terminal_calls) == 1
    assert "declare_quiet" not in backend.terminal_calls[-1]["system"]


# Envelope note intervals, ordering, and self-scheduled wakes.


def test_quiet_note_uses_completion_to_claim_even_when_event_predates_completion():
    record_id = str(uuid4())
    event_id = str(uuid4())
    event = {
        "record_type": "event_status",
        "event_id": event_id,
        "event_type": "inbound_message",
        "status": "pending",
        "created_at": "2026-09-04T20:00:00+00:00",
        "purpose": "already queued",
        "sender": "tony",
    }
    records = [
        event,
        _declaration(
            record_id,
            cycle=11,
            reason="deliberate pause",
            created_at="2026-09-05T00:59:00+00:00",
        ),
        _completed(record_id, cycle=11, completed_at="2026-09-05T01:00:00+00:00"),
        _running(event_id, "2026-09-06T03:30:00+00:00"),
    ]

    notes = operational_notes_for_event(
        records, event, now=datetime(2026, 9, 6, 4, tzinfo=UTC)
    )

    assert len(notes) == 1
    assert "after 1d 2h" in notes[0]
    assert "2026-09-05T00:59:00+00:00" in notes[0]


def test_quiet_note_falls_back_to_now_only_when_no_running_claim_exists():
    record_id = str(uuid4())
    event = build_inbound_event(purpose="unclaimed", sender="tony")
    records = [
        _declaration(record_id),
        _completed(record_id, completed_at="2026-09-05T01:00:00+00:00"),
        event,
    ]

    notes = operational_notes_for_event(
        records, event, now=datetime(2026, 9, 5, 5, 45, tzinfo=UTC)
    )

    assert notes[0].endswith("This wake ends that quiet after 4h 45m.")


@pytest.mark.parametrize(
    ("completed_at", "started_at"),
    (
        ("not-a-time", "2026-09-05T02:00:00+00:00"),
        ("2026-09-05T03:00:00+00:00", "2026-09-05T02:00:00+00:00"),
        ("2026-09-05T01:00:00+00:00", "not-a-time"),
    ),
)
def test_invalid_quiet_interval_omits_duration(completed_at, started_at):
    record_id = str(uuid4())
    event = build_inbound_event(purpose="claim", sender="tony")
    records = [
        _declaration(record_id),
        _completed(record_id, completed_at=completed_at),
        event,
        _running(event["event_id"], started_at),
    ]

    note = operational_notes_for_event(
        records, event, now=datetime(2026, 9, 5, 4, tzinfo=UTC)
    )[0]

    assert note.endswith("This wake ends that quiet.")
    assert " after " not in note


def test_rest_note_precedes_declaration_note_without_deduplication():
    record_id = str(uuid4())
    event = build_inbound_event(purpose="after rest", sender="tony")
    event["created_at"] = "2026-09-05T01:30:00+00:00"
    records = [
        _declaration(record_id, reason="also quiet"),
        _completed(record_id, completed_at="2026-09-05T01:00:00+00:00"),
        event,
        {
            "record_type": "heartbeat_status",
            "heartbeat_record_id": str(uuid4()),
            "status": "resting",
            "reason": "daily_budget_reached",
            "created_at": "2026-09-05T02:00:00+00:00",
            "detail": {"day": "2026-09-05", "wakes": 48},
        },
        {
            "record_type": "heartbeat_status",
            "heartbeat_record_id": str(uuid4()),
            "status": "active",
            "reason": "runnable_pending",
            "created_at": "2026-09-06T00:00:00+00:00",
        },
        _running(event["event_id"], "2026-09-06T00:00:00+00:00"),
    ]

    notes = operational_notes_for_event(
        records, event, now=datetime(2026, 9, 6, tzinfo=UTC)
    )

    assert len(notes) == 2
    assert notes[0].startswith("heartbeat rested")
    assert notes[1].startswith("Your cycle")


def test_future_self_scheduled_event_receives_declaration_note():
    record_id = str(uuid4())
    event = build_pending_event(
        purpose="future self wake",
        requested_context=[{"tool": "recall", "cycle": 12}],
        scheduled_by_cycle=12,
        scheduled_by_record_id=uuid4(),
        not_before="2026-09-20T00:00:00Z",
    )
    records = [
        event,
        _declaration(record_id, cycle=12, reason="until my own future wake"),
        _completed(record_id, cycle=12, completed_at="2026-09-05T01:00:00+00:00"),
        _running(event["event_id"], "2026-09-20T01:00:00+00:00"),
    ]

    note = operational_notes_for_event(
        records, event, now=datetime(2026, 9, 20, 1, tzinfo=UTC)
    )[0]

    assert '"until my own future wake"' in note
    assert "after 15d 0h" in note


# Daemon transition records and de-duplication.


class _NoopSession:
    pass


def _quiet_loop(store, now):
    return HeartbeatLoop(
        _NoopSession(),
        store,
        poll_interval=30,
        now=lambda: now,
        sleep=lambda _: None,
        run_pending=lambda *args, **kwargs: {"ran": 0, "results": []},
        summarize=lambda records, now=None: {
            "pending_runnable_count": 0,
            "pending_waiting_count": 0,
        },
    )


def test_heartbeat_step_records_complete_declared_detail_once(tmp_path):
    store = EventStore(tmp_path / "declared.events.jsonl")
    record_id = str(uuid4())
    declaration = _declaration(
        record_id,
        cycle=17,
        reason="reading slowly",
        created_at="2026-09-05T01:02:03+00:00",
        until="2026-09-12T00:00:00Z",
    )
    store.append(declaration)
    store.append(_completed(record_id, cycle=17))
    loop = _quiet_loop(store, datetime(2026, 9, 5, 2, tzinfo=UTC))

    assert loop.step()["state"] == "quiet"
    assert loop.step()["state"] == "quiet"

    statuses = [
        record
        for record in store.read_records()
        if record.get("record_type") == "heartbeat_status"
    ]
    assert len(statuses) == 1
    assert statuses[0]["status"] == "quiet"
    assert statuses[0]["reason"] == "declared_quiet"
    assert statuses[0]["detail"] == {
        "reason": "reading slowly",
        "until": "2026-09-12T00:00:00Z",
        "declared_by_cycle": 17,
        "declared_at": "2026-09-05T01:02:03+00:00",
    }


def test_heartbeat_step_records_undeclared_without_detail_once(tmp_path):
    store = EventStore(tmp_path / "undeclared.events.jsonl")
    store.append(_completed(str(uuid4())))
    loop = _quiet_loop(store, datetime(2026, 9, 5, 2, tzinfo=UTC))

    loop.step()
    loop.step()

    statuses = [
        record
        for record in store.read_records()
        if record.get("record_type") == "heartbeat_status"
    ]
    assert len(statuses) == 1
    assert statuses[0]["reason"] == "undeclared_quiet"
    assert "detail" not in statuses[0]


# JSON/text report behavior and historical compatibility.


def test_report_uses_latest_joined_declaration_counts_orphans_and_keeps_json_full():
    old_id, latest_id = str(uuid4()), str(uuid4())
    long_reason = "x" * 400 + "TAIL-MUST-BE-JSON-ONLY"
    old = _declaration(old_id, cycle=1, reason="old joined")
    latest = _declaration(latest_id, cycle=2, reason=long_reason)
    orphan = _declaration(str(uuid4()), cycle=3, reason="orphan should not win")
    historical_heartbeat = {
        "record_type": "heartbeat_status",
        "heartbeat_record_id": str(uuid4()),
        "status": "quiet",
        "reason": "chosen_quiet",
        "created_at": "2026-08-01T00:00:00+00:00",
    }
    records = [
        old,
        _completed(old_id, cycle=1),
        _completed(latest_id, cycle=2),
        latest,
        orphan,
        historical_heartbeat,
    ]

    report = summarize_event_log(records, limit=1)
    text = format_event_report(report)

    assert report["latest_quiet_declaration"] == latest
    assert report["orphan_quiet_declaration_count"] == 1
    assert report["latest_heartbeat_status"] == historical_heartbeat
    assert long_reason in json.dumps(report)
    quiet_line = next(line for line in text.splitlines() if line.startswith("Quiet declared"))
    assert "x" * 400 in quiet_line
    assert "TAIL-MUST-BE-JSON-ONLY" not in quiet_line
    assert "Heartbeat: quiet (chosen_quiet)" in text
    assert "Orphan quiet declarations (wake never completed): 1" in text


# Constitution and parser defaults.


def test_constitution_names_capability_without_prescribing_when_to_use_it():
    lowered = CONSTITUTION.lower()
    assert "recorded as chosen" not in lowered
    assert "declare_quiet" in CONSTITUTION
    assert "schedules nothing" in lowered
    assert "undeclared quiet" in lowered
    for prescription in (
        "when you should declare",
        "declare before",
        "declare after every",
        "always declare",
        "must declare",
        "should declare",
    ):
        assert prescription not in lowered


def test_parser_defaults_are_1_5_dollars_and_48_wakes():
    args = build_parser().parse_args(["--log-path", "validation.jsonl"])

    assert args.daily_budget_usd == 1.5
    assert args.daily_wake_cap == 48


# Session-log shape and one append_many for all cycle effects.


def test_session_writes_scheduled_event_and_last_declaration_in_one_batch(
    tmp_path, monkeypatch
):
    backend = _NaturalBackend(
        actions=[
            (
                "schedule_event",
                {
                    "purpose": "wake later",
                    "requested_context": [{"tool": "recall", "cycle": 1}],
                },
            ),
            ("declare_quiet", {"reason": "first"}),
            ("declare_quiet", {"reason": "last"}),
            ("declare_quiet", {}),
        ]
    )
    session = _session(tmp_path, backend, name="batched")
    original_append_many = session._event_store.append_many
    batches: list[list[dict]] = []

    def capture(records):
        batches.append(list(records))
        original_append_many(records)

    monkeypatch.setattr(session._event_store, "append_many", capture)

    session.exchange("managed", event_managed=True)

    assert len(batches) == 1
    assert [record["record_type"] for record in batches[0]] == [
        "event_status",
        "quiet_declaration",
    ]
    assert batches[0][0]["status"] == "pending"
    assert batches[0][1]["reason"] == "last"
    log_record = json.loads(
        (tmp_path / "batched.jsonl").read_text().splitlines()[-1]
    )
    assert log_record["scheduled_events"] == [batches[0][0]]
    assert log_record["quiet_declaration"] == batches[0][1]


def test_session_log_quiet_declaration_is_explicitly_null_when_not_declared(tmp_path):
    session = _session(tmp_path, _NaturalBackend(), name="null")

    session.exchange("managed", event_managed=True)

    log_record = json.loads((tmp_path / "null.jsonl").read_text().splitlines()[-1])
    assert "quiet_declaration" in log_record
    assert log_record["quiet_declaration"] is None
