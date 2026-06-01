"""Tests for taste_open scheduled event scaffolding."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from hamutay.events import (
    EventStore,
    build_event_envelope,
    build_pending_event,
    default_event_log_path,
    resolve_requested_context,
    run_next_event,
)
from hamutay.taste_open import ExchangeResult, OpenTasteSession
from hamutay.tools.executor import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS


class _FakeBackend:
    def __init__(
        self,
        result: ExchangeResult | None = None,
        exc: Exception | None = None,
    ):
        self._result = result or ExchangeResult(
            raw_output={"response": "event handled", "reflection": "revised"},
            stop_reason="end_turn",
        )
        self._exc = exc
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
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "extra_tools": extra_tools,
                "tool_executor": tool_executor,
            }
        )
        if self._exc is not None:
            raise self._exc
        return self._result


def _event_record(cycle: int = 1) -> dict:
    return build_pending_event(
        purpose="Reconsider the old claim.",
        requested_context=[{"tool": "recall", "cycle": cycle, "field": "claim"}],
        scheduled_by_cycle=cycle,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
    )


def test_default_event_log_path_is_sidecar():
    assert default_event_log_path("session.jsonl") == Path(
        "session.jsonl.events.jsonl"
    )


def test_event_store_append_and_latest_status(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    pending = _event_record()
    store.append(pending)
    store.append({
        "record_type": "event_status",
        "event_id": pending["event_id"],
        "status": "running",
    })

    latest = store.latest_by_event_id()[pending["event_id"]]
    assert latest["status"] == "running"


def test_event_store_next_pending_returns_oldest(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    first = _event_record()
    second = _event_record()
    second["created_at"] = "2999-01-01T00:00:00+00:00"
    store.append(first)
    store.append(second)

    assert store.next_pending()["event_id"] == first["event_id"]


def test_schedule_event_schema_exists():
    assert "schedule_event" in TOOL_SCHEMAS
    assert "purpose" in TOOL_SCHEMAS["schedule_event"]["input_schema"]["required"]


def test_executor_buffers_scheduled_event(tmp_path):
    executor = ToolExecutor(
        project_root=tmp_path,
        cycle=4,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000004"),
    )
    result = executor.execute(
        "schedule_event",
        {
            "purpose": "Check whether the claim still holds.",
            "requested_context": [{"tool": "recall", "cycle": 2}],
            "reason": "future self needs evidence",
        },
    )

    assert result["status"] == "pending"
    assert result["accepted_context_count"] == 1
    assert len(executor.pending_events) == 1
    assert executor.pending_events[0]["scheduled_by_cycle"] == 4
    assert executor.activity_log[-1]["tool"] == "schedule_event"
    assert executor.activity_log[-1]["reason"] == "future self needs evidence"


def test_executor_rejects_invalid_scheduled_event(tmp_path):
    executor = ToolExecutor(
        project_root=tmp_path,
        cycle=4,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000004"),
    )
    result = executor.execute(
        "schedule_event",
        {"purpose": "", "requested_context": [{"tool": "search_memory"}]},
    )

    assert "error" in result
    assert executor.pending_events == []


def test_session_commits_scheduled_events_after_success(tmp_path):
    class SchedulingBackend(_FakeBackend):
        def call(self, *args, **kwargs):
            executor = kwargs["tool_executor"]
            executor.execute(
                "schedule_event",
                {
                    "purpose": "Revisit cycle one.",
                    "requested_context": [{"tool": "recall", "cycle": 1}],
                },
            )
            return super().call(*args, **kwargs)

    log_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=SchedulingBackend(),
        log_path=str(log_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )
    session.exchange("schedule")

    records = [json.loads(line) for line in event_path.read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["status"] == "pending"
    assert records[0]["scheduled_by_record_id"]
    session_record = json.loads(log_path.read_text().splitlines()[-1])
    assert session_record["scheduled_events"][0]["event_id"] == records[0]["event_id"]


def test_session_does_not_commit_event_when_exchange_fails(tmp_path):
    class SchedulingFailBackend(_FakeBackend):
        def call(self, *args, **kwargs):
            kwargs["tool_executor"].execute(
                "schedule_event",
                {
                    "purpose": "Should not commit.",
                    "requested_context": [{"tool": "recall", "cycle": 1}],
                },
            )
            raise RuntimeError("boom")

    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=SchedulingFailBackend(),
        log_path=str(tmp_path / "session.jsonl"),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )

    with pytest.raises(RuntimeError, match="boom"):
        session.exchange("fail")
    assert not event_path.exists() or event_path.read_text() == ""


def test_resolve_requested_context_uses_memory_tools():
    prior_states = [
        (
            1,
            UUID("00000000-0000-0000-0000-000000000001"),
            {"claim": "old", "cycle": 1},
            "2026-06-01T00:00:00+00:00",
        ),
        (
            2,
            UUID("00000000-0000-0000-0000-000000000002"),
            {"claim": "new", "cycle": 2},
            "2026-06-01T00:01:00+00:00",
        ),
    ]

    results = resolve_requested_context(
        [
            {"tool": "recall", "cycle": 1, "field": "claim"},
            {
                "tool": "compare",
                "cycle_a": 1,
                "cycle_b": 2,
                "field": "claim",
                "content": True,
            },
        ],
        prior_states=prior_states,
    )

    assert results[0]["result"]["content"] == "old"
    assert results[1]["result"]["changed_fields"][0]["field"] == "claim"


def test_build_event_envelope_is_explicit():
    event = _event_record()
    envelope = json.loads(build_event_envelope(event, [], "run-1"))
    assert envelope["event_type"] == "self_scheduled_reflection"
    assert envelope["event_id"] == event["event_id"]
    assert "self-scheduled reflection" in envelope["instruction"]


def test_run_next_event_completes(tmp_path):
    log_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=_FakeBackend(),
        log_path=str(log_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )
    session.exchange("seed")
    event = build_pending_event(
        purpose="Reflect on claim.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
    )
    store = EventStore(event_path)
    store.append(event)

    result = run_next_event(session, store)

    assert result["status"] == "completed"
    records = store.read_records()
    assert [r["status"] for r in records] == ["pending", "running", "completed"]
    assert session._prior_states[-1][2]["reflection"] == "revised"


def test_run_next_event_marks_expired(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    event["expires_at"] = "2000-01-01T00:00:00+00:00"
    store.append(event)

    result = run_next_event(SimpleNamespace(), store)

    assert result["status"] == "expired"


def test_run_next_event_logs_failure(tmp_path):
    log_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=_FakeBackend(),
        log_path=str(log_path),
        event_log_path=str(event_path),
        project_root=tmp_path,
    )
    session.exchange("seed")
    session._backend = _FakeBackend(exc=RuntimeError("wake failed"))
    event = build_pending_event(
        purpose="Reflect and fail.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
    )
    store = EventStore(event_path)
    store.append(event)

    with pytest.raises(RuntimeError, match="wake failed"):
        run_next_event(session, store)

    assert store.read_records()[-1]["status"] == "failed"
