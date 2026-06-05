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
    build_outcome_observation,
    build_pending_event,
    default_event_log_path,
    detect_lifecycle_anomalies,
    format_event_report,
    resolve_requested_context,
    run_next_event,
    run_pending_events,
    step_pending_events,
    summarize_event_log,
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


def test_event_store_next_pending_skips_waiting_events(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    future = _event_record()
    future["created_at"] = "2026-06-01T00:00:00+00:00"
    future["not_before"] = "2026-06-01T01:00:00+00:00"
    ready = _event_record()
    ready["created_at"] = "2026-06-01T00:00:01+00:00"
    store.append(future)
    store.append(ready)

    next_event = store.next_pending(
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    )

    assert next_event is not None
    assert next_event["event_id"] == ready["event_id"]


def test_event_store_next_pending_returns_expired_event_for_sweep(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    expired = _event_record()
    expired["created_at"] = "2026-06-01T00:00:00+00:00"
    expired["expires_at"] = "2026-05-31T23:59:00+00:00"
    ready = _event_record()
    ready["created_at"] = "2026-06-01T00:00:01+00:00"
    store.append(expired)
    store.append(ready)

    next_event = store.next_pending(
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    )

    assert next_event is not None
    assert next_event["event_id"] == expired["event_id"]


def test_event_store_claim_next_pending_is_single_claim(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    pending = _event_record()
    store.append(pending)

    claim = store.claim_next_pending(
        run_id=UUID("00000000-0000-0000-0000-000000000123")
    )
    assert claim is not None
    event, running = claim

    assert event["event_id"] == pending["event_id"]
    assert running["status"] == "running"
    assert store.claim_next_pending() is None
    assert store.latest_by_event_id()[pending["event_id"]]["status"] == "running"


def test_event_store_claim_marks_expired_without_running(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    event["expires_at"] = "2000-01-01T00:00:00+00:00"
    store.append(event)

    claim = store.claim_next_pending()

    assert claim is not None
    _event, expired = claim
    assert expired["status"] == "expired"
    assert [r["status"] for r in store.read_records()] == ["pending", "expired"]


def test_build_pending_event_accepts_and_validates_not_before():
    event = build_pending_event(
        purpose="Wait before waking.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
        not_before="2026-06-01T01:00:00Z",
    )

    assert event["not_before"] == "2026-06-01T01:00:00Z"
    with pytest.raises(ValueError):
        build_pending_event(
            purpose="Bad time.",
            requested_context=[{"tool": "recall", "cycle": 1}],
            scheduled_by_cycle=1,
            scheduled_by_record_id=UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
            not_before="not-a-timestamp",
        )


def test_build_pending_event_accepts_durable_update_contract():
    contract = {
        "required_top_level": {
            "thinking_status": {"equals": "completed"},
            "delayed_thought": {"type": "non_empty_string"},
        }
    }
    event = build_pending_event(
        purpose="Complete delayed thinking.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
        durable_update_contract=contract,
    )

    assert event["durable_update_contract"] == contract
    contract["required_top_level"]["thinking_status"]["equals"] = "changed"
    assert (
        event["durable_update_contract"]["required_top_level"]
        ["thinking_status"]["equals"]
    ) == "completed"

    with pytest.raises(ValueError, match="durable_update_contract"):
        build_pending_event(
            purpose="Bad contract.",
            requested_context=[{"tool": "recall", "cycle": 1}],
            scheduled_by_cycle=1,
            scheduled_by_record_id=UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
            durable_update_contract=["not", "an", "object"],
        )


def test_build_pending_event_accepts_durable_update_example():
    example = {
        "response": "Delayed thinking complete.",
        "thinking_status": "completed",
        "delayed_thought": "Carry the result forward.",
    }
    event = build_pending_event(
        purpose="Complete delayed thinking.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
        durable_update_example=example,
    )

    assert event["durable_update_example"] == example
    example["thinking_status"] = "changed"
    assert event["durable_update_example"]["thinking_status"] == "completed"

    with pytest.raises(ValueError, match="durable_update_example"):
        build_pending_event(
            purpose="Bad example.",
            requested_context=[{"tool": "recall", "cycle": 1}],
            scheduled_by_cycle=1,
            scheduled_by_record_id=UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
            durable_update_example=["not", "an", "object"],
        )


def test_build_pending_event_accepts_walk_context():
    event = build_pending_event(
        purpose="Inspect fork-run graph hub.",
        requested_context=[
            {
                "tool": "walk",
                "from_record_id": "00000000-0000-0000-0000-000000000111",
                "direction": "forward",
                "depth": 1,
                "mode": "adjacent",
            }
        ],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
    )

    assert event["requested_context"] == [
        {
            "tool": "walk",
            "from_record_id": "00000000-0000-0000-0000-000000000111",
            "direction": "forward",
            "depth": 1,
            "mode": "adjacent",
        }
    ]


@pytest.mark.parametrize(
    "context_request",
    [
        {"tool": "walk", "direction": "forward"},
        {
            "tool": "walk",
            "from_record_id": "00000000-0000-0000-0000-000000000111",
            "direction": "sideways",
        },
        {
            "tool": "walk",
            "from_record_id": "00000000-0000-0000-0000-000000000111",
            "mode": "fanout",
        },
        {
            "tool": "walk",
            "from_record_id": "00000000-0000-0000-0000-000000000111",
            "depth": -1,
        },
        {
            "tool": "walk",
            "from_record_id": "00000000-0000-0000-0000-000000000111",
            "unexpected": True,
        },
    ],
)
def test_build_pending_event_rejects_malformed_walk_context(context_request):
    with pytest.raises(ValueError):
        build_pending_event(
            purpose="Bad walk request.",
            requested_context=[context_request],
            scheduled_by_cycle=1,
            scheduled_by_record_id=UUID(
                "00000000-0000-0000-0000-000000000001"
            ),
        )


def test_event_store_claim_skips_not_yet_due_event(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    future = _event_record()
    future["created_at"] = "2026-06-01T00:00:00+00:00"
    future["not_before"] = "2026-06-01T01:00:00+00:00"
    ready = _event_record()
    ready["created_at"] = "2026-06-01T00:00:01+00:00"
    store.append(future)
    store.append(ready)

    claim = store.claim_next_pending(
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
        run_id=UUID("00000000-0000-0000-0000-000000000123"),
    )

    assert claim is not None
    claimed, running = claim
    assert claimed["event_id"] == ready["event_id"]
    assert running["status"] == "running"
    latest = store.latest_by_event_id()
    assert latest[future["event_id"]]["status"] == "pending"
    assert latest[ready["event_id"]]["status"] == "running"


def test_event_store_claim_returns_none_when_no_event_is_due(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    future = _event_record()
    future["not_before"] = "2026-06-01T01:00:00+00:00"
    store.append(future)

    claim = store.claim_next_pending(
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    )

    assert claim is None
    assert store.latest_by_event_id()[future["event_id"]]["status"] == "pending"


def test_run_next_event_accepts_simulated_now(tmp_path):
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
        purpose="Run only after simulated time advances.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
        not_before="2026-06-01T01:00:00+00:00",
    )
    store = EventStore(event_path)
    store.append(event)

    too_early = run_next_event(
        session,
        store,
        now=datetime(2026, 6, 1, 0, 59, tzinfo=timezone.utc),
    )
    assert too_early["status"] == "none"
    assert store.latest_by_event_id()[event["event_id"]]["status"] == "pending"

    due = run_next_event(
        session,
        store,
        now=datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc),
    )
    assert due["status"] == "completed"


def test_schedule_event_schema_exists():
    assert "schedule_event" in TOOL_SCHEMAS
    assert "purpose" in TOOL_SCHEMAS["schedule_event"]["input_schema"]["required"]
    properties = TOOL_SCHEMAS["schedule_event"]["input_schema"]["properties"]
    assert "not_before" in properties
    assert "durable_update_contract" in properties
    assert "durable_update_example" in properties
    context_item = properties["requested_context"]["items"]["properties"]
    assert context_item["tool"]["enum"] == ["recall", "compare", "walk"]
    assert context_item["mode"]["enum"] == ["path", "adjacent"]


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
            "not_before": "2026-06-01T01:00:00+00:00",
            "durable_update_contract": {
                "required_top_level": {
                    "revision_decision": {"type": "non_empty_string"}
                }
            },
            "durable_update_example": {
                "response": "The claim still holds.",
                "revision_decision": "preserve",
            },
            "reason": "future self needs evidence",
        },
    )

    assert result["status"] == "pending"
    assert result["accepted_context_count"] == 1
    assert result["not_before"] == "2026-06-01T01:00:00+00:00"
    assert result["durable_update_contract"]["required_top_level"] == {
        "revision_decision": {"type": "non_empty_string"}
    }
    assert result["durable_update_example"]["revision_decision"] == "preserve"
    assert len(executor.pending_events) == 1
    assert executor.pending_events[0]["scheduled_by_cycle"] == 4
    assert executor.pending_events[0]["not_before"] == (
        "2026-06-01T01:00:00+00:00"
    )
    assert executor.pending_events[0]["durable_update_contract"] == (
        result["durable_update_contract"]
    )
    assert executor.pending_events[0]["durable_update_example"] == (
        result["durable_update_example"]
    )
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


def test_session_without_curator_has_no_curator_context(tmp_path):
    backend = _FakeBackend()
    log_path = tmp_path / "session.jsonl"
    session = OpenTasteSession(
        backend=backend,
        log_path=str(log_path),
        project_root=tmp_path,
    )

    session.exchange("seed")

    record = json.loads(log_path.read_text().splitlines()[-1])
    assert "continuity_curation" not in record
    assert "curator_context_injection" not in record
    assert "Continuity curator summary" not in backend.calls[0]["system"]


def test_curator_output_is_logged_and_injected_next_cycle(tmp_path):
    class FakeCurator:
        def __init__(self):
            self.calls = []

        def curate(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "summary": f"carry forward from cycle {kwargs['cycle']}",
                "supported_facts": ["state was revised"],
            }

    backend = _FakeBackend()
    curator = FakeCurator()
    log_path = tmp_path / "session.jsonl"
    session = OpenTasteSession(
        backend=backend,
        log_path=str(log_path),
        project_root=tmp_path,
        continuity_curator=curator,
    )

    session.exchange("seed")
    session.exchange("resume")

    records = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    first_curation = records[0]["continuity_curation"]
    assert first_curation["status"] == "success"
    assert first_curation["source_cycle"] == 1
    assert first_curation["source_record_id"] == records[0]["record_id"]
    assert first_curation["summary"] == "carry forward from cycle 1"
    assert curator.calls[0]["state"]["reflection"] == "revised"

    assert "Continuity curator summary" in backend.calls[1]["system"]
    assert "carry forward from cycle 1" in backend.calls[1]["system"]
    assert records[1]["curator_context_injection"]["summary"] == (
        "carry forward from cycle 1"
    )
    assert records[1]["curator_context_injection"]["source_record_id"] == (
        records[0]["record_id"]
    )


def test_curator_failure_is_logged_and_not_injected(tmp_path):
    class FailingCurator:
        def curate(self, **kwargs):
            raise RuntimeError("curator boom")

    backend = _FakeBackend()
    log_path = tmp_path / "session.jsonl"
    session = OpenTasteSession(
        backend=backend,
        log_path=str(log_path),
        project_root=tmp_path,
        continuity_curator=FailingCurator(),
    )

    session.exchange("seed")
    session.exchange("resume")

    records = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    assert records[0]["continuity_curation"]["status"] == "failed"
    assert records[0]["continuity_curation"]["error"] == "curator boom"
    assert "Continuity curator summary" not in backend.calls[1]["system"]
    assert "curator_context_injection" not in records[1]


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


def test_resolve_requested_context_uses_walk_memory_tool():
    start = UUID("00000000-0000-0000-0000-000000000111")
    target = UUID("00000000-0000-0000-0000-000000000222")

    class Bridge:
        def query_edges_by_endpoint(self, record_id, direction):
            if record_id == start and direction == "forward":
                return [{
                    "from_record": start,
                    "to_record": target,
                    "relation_type": "BRANCHES_FROM",
                    "ordering": 1,
                }]
            return []

        def retrieve(self, record_id):
            assert record_id == target
            return {"record_type": "branch_result", "label": "branch-a"}

    results = resolve_requested_context(
        [
            {
                "tool": "walk",
                "from_record_id": str(start),
                "direction": "forward",
                "depth": 1,
                "mode": "adjacent",
            }
        ],
        prior_states=[],
        bridge=Bridge(),
    )

    assert results[0]["request"]["tool"] == "walk"
    assert results[0]["result"]["path"][0]["record_id"] == str(target)
    assert results[0]["result"]["path"][0]["depth"] == 1


def test_build_event_envelope_is_explicit():
    event = _event_record()
    event["durable_update_contract"] = {
        "required_top_level": {"thinking_status": {"equals": "completed"}}
    }
    event["durable_update_example"] = {
        "response": "Delayed thinking complete.",
        "thinking_status": "completed",
    }
    envelope = json.loads(build_event_envelope(event, [], "run-1"))
    assert envelope["event_type"] == "self_scheduled_reflection"
    assert envelope["event_id"] == event["event_id"]
    assert envelope["durable_update_contract"] == event["durable_update_contract"]
    assert envelope["durable_update_example"] == event["durable_update_example"]
    assert "self-scheduled reflection" in envelope["instruction"]
    assert "top-level fields" in envelope["instruction"]
    assert "Visible prose is not enough" in envelope["instruction"]
    assert "cycle and _activity_log are substrate-owned" in envelope["instruction"]


def test_build_event_envelope_preserves_walk_context():
    request = {
        "tool": "walk",
        "from_record_id": "00000000-0000-0000-0000-000000000111",
        "direction": "forward",
        "depth": 1,
        "mode": "adjacent",
    }
    event = build_pending_event(
        purpose="Inspect fork-run graph hub.",
        requested_context=[request],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
    )
    context_results = [{
        "request": request,
        "result": {
            "path": [{
                "record_id": "00000000-0000-0000-0000-000000000222",
                "edge_type": "BRANCHES_FROM",
                "depth": 1,
            }]
        },
    }]

    envelope = json.loads(build_event_envelope(event, context_results, "run-1"))

    assert envelope["requested_context"] == [request]
    assert envelope["context_results"] == context_results


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
    session._backend = _FakeBackend(
        ExchangeResult(
            raw_output={
                "response": "event handled",
                "event_reflection": "revised",
            },
            stop_reason="end_turn",
        )
    )
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
    assert result["context_results"][0]["result"]["cycle"] == 1
    records = store.read_records()
    assert [r["status"] for r in records] == ["pending", "running", "completed"]
    assert session._prior_states[-1][2]["event_reflection"] == "revised"
    observation = records[-1]["outcome_observation"]
    assert observation["state_changed"] is True
    assert observation["added_top_level_keys"] == ["event_reflection"]
    assert observation["no_durable_state_change"] is False


def test_build_outcome_observation_detects_prose_only_decision():
    observation = build_outcome_observation(
        before_state={"current_claim": "old", "cycle": 1},
        after_state={"current_claim": "old", "cycle": 2},
        response_text="I revised the claim after reflection.",
    )

    assert observation["state_changed"] is False
    assert observation["no_durable_state_change"] is True
    assert observation["response_mentions_epistemic_decision"] is True
    assert observation["response_state_mismatch"] is True


def test_build_outcome_observation_detects_load_bearing_deletion():
    observation = build_outcome_observation(
        before_state={
            "current_claim": "old",
            "state_use_norm": "preserve durable fields",
            "scratch": "x",
            "cycle": 1,
        },
        after_state={"scratch": "x", "cycle": 2},
        response_text="Declared loss.",
    )

    assert observation["state_changed"] is True
    assert observation["removed_top_level_keys"] == [
        "current_claim",
        "state_use_norm",
    ]
    assert observation["deleted_load_bearing_field"] is True
    assert observation["deleted_load_bearing_fields"] == [
        "current_claim",
        "state_use_norm",
    ]


def test_run_next_event_marks_expired(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    event["expires_at"] = "2000-01-01T00:00:00+00:00"
    store.append(event)

    result = run_next_event(SimpleNamespace(), store)

    assert result["status"] == "expired"


def test_run_next_event_reports_none_when_pending_event_not_due(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    event["not_before"] = "2999-01-01T00:00:00+00:00"
    store.append(event)

    result = run_next_event(SimpleNamespace(), store)

    assert result == {
        "status": "none",
        "message": "no runnable pending events",
    }
    assert store.latest_by_event_id()[event["event_id"]]["status"] == "pending"


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

    failed = store.read_records()[-1]
    assert failed["status"] == "failed"
    assert failed["context_results"][0]["result"]["cycle"] == 1


def test_run_pending_events_respects_limit(tmp_path):
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
    store = EventStore(event_path)
    for _ in range(2):
        store.append(build_pending_event(
            purpose="Reflect on seed.",
            requested_context=[{"tool": "recall", "cycle": 1}],
            scheduled_by_cycle=1,
            scheduled_by_record_id=session._prior_states[-1][1],
        ))

    result = run_pending_events(session, store, limit=1)

    assert result["ran"] == 1
    assert len(result["results"]) == 1
    statuses = [r["status"] for r in store.latest_by_event_id().values()]
    assert sorted(statuses) == ["completed", "pending"]


def test_step_pending_events_reports_waiting_next_wake_at(tmp_path):
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
    store = EventStore(event_path)
    expired = build_pending_event(
        purpose="Expire before the simulated step.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
        expires_at="2026-05-31T23:59:00+00:00",
    )
    expired["created_at"] = "2026-06-01T00:00:00+00:00"
    ready = build_pending_event(
        purpose="Run at the first simulated step.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
    )
    ready["created_at"] = "2026-06-01T00:00:01+00:00"
    waiting = build_pending_event(
        purpose="Run only after simulated time advances.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
        not_before="2026-06-01T01:00:00+00:00",
    )
    waiting["created_at"] = "2026-06-01T00:00:02+00:00"
    store.append(expired)
    store.append(ready)
    store.append(waiting)

    first = step_pending_events(
        session,
        store,
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert first["stop_reason"] == "waiting"
    assert first["wake_run_count"] == 1
    assert first["expired_count"] == 1
    assert first["next_wake_at"] == "2026-06-01T01:00:00+00:00"
    latest = store.latest_by_event_id()
    assert latest[expired["event_id"]]["status"] == "expired"
    assert latest[ready["event_id"]]["status"] == "completed"
    assert latest[waiting["event_id"]]["status"] == "pending"

    second = step_pending_events(
        session,
        store,
        now=datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc),
    )

    assert second["stop_reason"] == "idle"
    assert second["wake_run_count"] == 1
    assert second["expired_count"] == 0
    assert second["next_wake_at"] is None
    assert store.latest_by_event_id()[waiting["event_id"]]["status"] == (
        "completed"
    )


def test_step_pending_events_respects_fixed_now_limit(tmp_path):
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
    store = EventStore(event_path)
    ready = build_pending_event(
        purpose="Run now.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
    )
    waiting = build_pending_event(
        purpose="Do not run under fixed now.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
        not_before="2026-06-01T01:00:00+00:00",
    )
    store.append(ready)
    store.append(waiting)

    step = step_pending_events(
        session,
        store,
        limit=1,
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert step["wake_run_count"] == 1
    assert step["stop_reason"] == "waiting"
    assert step["next_wake_at"] == "2026-06-01T01:00:00+00:00"
    assert store.latest_by_event_id()[waiting["event_id"]]["status"] == "pending"


def test_summarize_event_log_reports_statuses_and_context_errors(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    completed = _event_record()
    failed = _event_record()
    pending = _event_record()
    pending["not_before"] = "2026-06-01T01:00:00+00:00"

    store.append(completed)
    store.append_running(completed, run_id=UUID("00000000-0000-0000-0000-000000000111"))
    store.append_completed(
        event=completed,
        run_id="00000000-0000-0000-0000-000000000111",
        wake_cycle=3,
        result_record_id=UUID("00000000-0000-0000-0000-000000000003"),
        response_text="handled with a context issue",
        context_results=[
            {
                "request": {"tool": "recall", "cycle": 99},
                "result": {"error": "cycle not found: 99"},
            }
        ],
        outcome_observation={
            "state_changed": False,
            "changed_load_bearing_fields": [],
            "deleted_load_bearing_fields": [],
            "deleted_load_bearing_field": False,
            "response_state_mismatch": True,
            "no_durable_state_change": True,
        },
    )
    store.append(failed)
    store.append_running(failed, run_id=UUID("00000000-0000-0000-0000-000000000222"))
    store.append_failed(
        event=failed,
        run_id="00000000-0000-0000-0000-000000000222",
        exc=RuntimeError("wake failed"),
    )
    store.append(pending)

    summary = summarize_event_log(store.read_records())

    assert summary["record_count"] == 7
    assert summary["event_count"] == 3
    assert summary["status_counts"] == {
        "completed": 1,
        "failed": 1,
        "pending": 1,
    }
    assert summary["oldest_pending"]["event_id"] == pending["event_id"]
    assert summary["oldest_pending"]["not_before"] == (
        "2026-06-01T01:00:00+00:00"
    )
    assert summary["failed"][0]["error"] == "wake failed"
    assert summary["context_errors"][0]["event_id"] == completed["event_id"]
    assert summary["outcome_warnings"][0]["event_id"] == completed["event_id"]
    assert summary["completed"][0]["outcome_warning_count"] == 2
    assert summary["completed"][0]["context_error_count"] == 1


def test_summarize_event_log_classifies_pending_runnability(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    ready = _event_record()
    ready["created_at"] = "2026-06-01T00:00:00+00:00"
    waiting = _event_record()
    waiting["created_at"] = "2026-06-01T00:00:01+00:00"
    waiting["not_before"] = "2026-06-01T01:00:00+00:00"
    expired = _event_record()
    expired["created_at"] = "2026-06-01T00:00:02+00:00"
    expired["expires_at"] = "2026-05-31T23:59:00+00:00"
    store.append(ready)
    store.append(waiting)
    store.append(expired)

    summary = summarize_event_log(
        store.read_records(),
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )

    assert summary["pending_runnable_count"] == 1
    assert summary["pending_waiting_count"] == 1
    assert summary["pending_expired_count"] == 1
    assert summary["oldest_runnable_pending"]["event_id"] == ready["event_id"]
    assert summary["oldest_waiting_pending"]["event_id"] == waiting["event_id"]
    assert summary["oldest_expired_pending"]["event_id"] == expired["event_id"]


def test_suppress_pending_marks_pending_events_terminal(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    first = _event_record()
    second = _event_record()
    store.append(first)
    store.append(second)

    suppressed = store.suppress_pending(
        policy="bounded_autonomy",
        reason="stasis cutoff",
        suppressed_by_record_id="record-1",
        suppressed_by_cycle=3,
        suppressed_by_classification="stasis",
    )

    assert len(suppressed) == 2
    latest = store.latest_by_event_id()
    assert latest[first["event_id"]]["status"] == "suppressed"
    assert latest[first["event_id"]]["suppressed_by_policy"] == (
        "bounded_autonomy"
    )
    assert latest[first["event_id"]]["suppression_reason"] == "stasis cutoff"
    assert latest[first["event_id"]]["suppressed_by_record_id"] == "record-1"
    assert latest[first["event_id"]]["suppressed_by_cycle"] == 3
    assert latest[first["event_id"]]["suppressed_by_classification"] == "stasis"


def test_suppressed_events_summarize_without_lifecycle_anomaly(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    store.append(event)
    store.suppress_pending(policy="bounded_autonomy", reason="drift")

    summary = summarize_event_log(store.read_records())

    assert summary["status_counts"] == {"suppressed": 1}
    assert summary["pending_runnable_count"] == 0
    assert summary["suppressed"][0]["event_id"] == event["event_id"]
    assert summary["suppressed"][0]["suppression_reason"] == "drift"
    assert summary["lifecycle_anomalies"] == []


def test_detect_lifecycle_anomalies_flags_invalid_history():
    anomalies = detect_lifecycle_anomalies(
        "event-1",
        [{
            "record_type": "event_status",
            "event_id": "event-1",
            "status": "completed",
        }],
    )

    kinds = {anomaly["kind"] for anomaly in anomalies}
    assert "missing_initial_pending" in kinds
    assert "terminal_without_running" in kinds
    assert "completed_missing_fields" in kinds


def test_summarize_event_log_reports_lifecycle_anomalies():
    pending = _event_record()
    running = {
        "record_type": "event_status",
        "event_id": pending["event_id"],
        "event_type": pending["event_type"],
        "status": "running",
        "run_id": "run-1",
        "started_at": "2026-06-01T00:00:00+00:00",
    }
    completed = {
        "record_type": "event_status",
        "event_id": pending["event_id"],
        "event_type": pending["event_type"],
        "status": "completed",
        "completed_at": "2026-06-01T00:01:00+00:00",
        "wake_cycle": 2,
        "result_record_id": "00000000-0000-0000-0000-000000000002",
    }
    failed = {
        "record_type": "event_status",
        "event_id": pending["event_id"],
        "event_type": pending["event_type"],
        "status": "failed",
        "failed_at": "2026-06-01T00:02:00+00:00",
        "run_id": "run-1",
    }

    summary = summarize_event_log([pending, running, completed, failed])

    kinds = {anomaly["kind"] for anomaly in summary["lifecycle_anomalies"]}
    assert "multiple_terminal_statuses" in kinds
    assert "status_after_terminal" in kinds
    assert summary["events"][0]["lifecycle_anomaly_count"] == 2


def test_summarize_event_log_reports_stale_running(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    running = {
        "record_type": "event_status",
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "status": "running",
        "run_id": "run-stale",
        "started_at": "2026-06-01T00:00:00+00:00",
    }
    store.append(event)
    store.append(running)

    summary = summarize_event_log(
        store.read_records(),
        stale_after_seconds=60,
        now=datetime(2026, 6, 1, 0, 2, tzinfo=timezone.utc),
    )

    assert summary["stale_running"][0]["event_id"] == event["event_id"]
    assert summary["stale_running"][0]["running_age_seconds"] == 120


def test_format_event_report_includes_operational_sections(tmp_path):
    event = _event_record()
    completed = {
        "record_type": "event_status",
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "status": "completed",
        "completed_at": "2026-06-01T00:00:00+00:00",
        "wake_cycle": 2,
        "result_record_id": "00000000-0000-0000-0000-000000000002",
        "response_text": "I revised in prose only.",
        "outcome_observation": {
            "state_changed": False,
            "changed_load_bearing_fields": [],
            "deleted_load_bearing_fields": [],
            "deleted_load_bearing_field": False,
            "response_state_mismatch": True,
            "no_durable_state_change": True,
        },
    }
    summary = summarize_event_log([event, completed])

    report = format_event_report(summary, path=tmp_path / "events.jsonl")

    assert "Event log:" in report
    assert "Statuses: completed=1" in report
    assert "Outcome warnings:" in report
    assert "response/state mismatch" in report
    assert "no durable state change" in report


def test_format_event_report_includes_pending_runnability(tmp_path):
    ready = _event_record()
    waiting = _event_record()
    waiting["not_before"] = "2026-06-01T01:00:00+00:00"
    expired = _event_record()
    expired["expires_at"] = "2026-05-31T23:59:00+00:00"
    summary = summarize_event_log(
        [ready, waiting, expired],
        now=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )

    report = format_event_report(summary, path=tmp_path / "events.jsonl")

    assert "Pending: runnable=1, waiting=1, expired=1" in report
    assert "Oldest runnable pending:" in report
    assert "Oldest waiting pending:" in report
    assert "Oldest expired pending:" in report


def test_format_event_report_includes_suppressed_events(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    event = _event_record()
    store.append(event)
    store.suppress_pending(policy="bounded_autonomy", reason="stasis cutoff")

    report = format_event_report(summarize_event_log(store.read_records()))

    assert "Statuses: suppressed=1" in report
    assert "Suppressed:" in report
    assert "policy=bounded_autonomy reason=stasis cutoff" in report


def test_format_event_report_includes_lifecycle_anomalies(tmp_path):
    record = {
        "record_type": "event_status",
        "event_id": "event-1",
        "event_type": "self_scheduled_reflection",
        "status": "completed",
    }
    summary = summarize_event_log([record])

    report = format_event_report(summary, path=tmp_path / "events.jsonl")

    assert "Lifecycle anomalies:" in report
    assert "missing_initial_pending" in report
    assert "completed_missing_fields" in report
