from datetime import timedelta
from uuid import UUID

import pytest

from hamutay.events import build_pending_event
from hamutay.memory.bridge import LocalMemorySubstrate, MemoryResponse
from hamutay.scheduler import EventQueue, SchedulerClock, SchedulerDispatcher


BASE_TIME = "2026-06-08T12:00:00+00:00"
RID_1 = UUID("20000000-0000-0000-0000-000000000001")
RID_2 = UUID("20000000-0000-0000-0000-000000000002")


def _store_record(
    substrate: LocalMemorySubstrate,
    *,
    record_id: UUID = RID_1,
    content: dict | None = None,
) -> str:
    stored = substrate.store_episode(
        record_id=record_id,
        record_type="fixture",
        content=content or {"claim": "ready", "body": "short"},
        production={
            "who": {"instance": "fixture"},
            "what": {"artifact": "fixture"},
            "when": {"cycle": 1},
            "where": {"project": "hamutay"},
        },
        execution_trace={"tool_path": "test"},
    )
    assert stored.ok
    return str(record_id)


def _event(
    *,
    event_id: str,
    record_id: UUID = RID_1,
    created_at: str = BASE_TIME,
    not_before: str | None = None,
    expires_at: str | None = None,
    priority: int | None = None,
    field: str | None = "claim",
) -> dict:
    event = build_pending_event(
        purpose=f"wake {event_id}",
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(record_id),
                **({"field": field} if field else {}),
            }
        ],
        scheduled_by_cycle=1,
        scheduled_by_record_id=record_id,
        not_before=not_before,
        expires_at=expires_at,
    )
    event["event_id"] = event_id
    event["created_at"] = created_at
    if priority is not None:
        event["priority"] = priority
    return event


def test_clock_advances_monotonically_and_rejects_backward_time():
    clock = SchedulerClock.start(BASE_TIME)

    clock.advance_by(timedelta(minutes=5))
    assert clock.now_iso() == "2026-06-08T12:05:00+00:00"
    clock.advance_to("2026-06-08T12:10:00+00:00")
    assert clock.now_iso() == "2026-06-08T12:10:00+00:00"

    with pytest.raises(ValueError, match="cannot move backward"):
        clock.advance_to(BASE_TIME)


def test_event_queue_due_order_is_not_before_priority_created_event_id():
    queue = EventQueue()
    now = SchedulerClock.start(BASE_TIME).now()
    events = [
        _event(
            event_id="d",
            created_at="2026-06-08T11:59:00+00:00",
            not_before="2026-06-08T12:00:00+00:00",
            priority=2,
        ),
        _event(
            event_id="c",
            created_at="2026-06-08T11:58:00+00:00",
            not_before="2026-06-08T12:00:00+00:00",
            priority=1,
        ),
        _event(
            event_id="b",
            created_at="2026-06-08T11:57:00+00:00",
            not_before="2026-06-08T12:01:00+00:00",
            priority=0,
        ),
        _event(
            event_id="a",
            created_at="2026-06-08T11:56:00+00:00",
            not_before="2026-06-08T11:59:00+00:00",
            priority=9,
        ),
    ]
    for event in events:
        queue.append_pending(event)

    first = queue.claim_next_due(now=now)
    second = queue.claim_next_due(now=now)
    third = queue.claim_next_due(now=now)
    fourth = queue.claim_next_due(now=now)

    assert [claim.event["event_id"] for claim in (first, second, third)] == [
        "a",
        "c",
        "d",
    ]
    assert fourth is None


def test_event_queue_no_due_event_does_not_change_lifecycle_log():
    queue = EventQueue()
    queue.append_pending(
        _event(
            event_id="future",
            not_before="2026-06-08T13:00:00+00:00",
        )
    )

    claim = queue.claim_next_due(now=SchedulerClock.start(BASE_TIME).now())

    assert claim is None
    assert [record["status"] for record in queue.records] == ["pending"]


def test_event_queue_expired_event_is_recorded_without_running():
    queue = EventQueue()
    queue.append_pending(
        _event(
            event_id="expired",
            expires_at="2026-06-08T11:00:00+00:00",
        )
    )

    claim = queue.claim_next_due(now=SchedulerClock.start(BASE_TIME).now())

    assert claim is not None
    assert claim.running["status"] == "expired"
    assert [record["status"] for record in queue.records] == [
        "pending",
        "expired",
    ]


def test_dispatcher_resolves_context_invokes_handler_stores_result_and_completes():
    memory = LocalMemorySubstrate()
    _store_record(memory)
    queue = EventQueue()
    queue.append_pending(_event(event_id="event-1"))
    clock = SchedulerClock.start(BASE_TIME)
    seen = []

    def handler(envelope):
        seen.append(envelope.to_dict())
        return {"response": "completed", "saw": envelope.context_results[0]["result"]}

    dispatcher = SchedulerDispatcher(
        queue=queue,
        clock=clock,
        memory=memory,
        handler=handler,
    )

    result = dispatcher.dispatch_next()

    assert result.status == "completed"
    assert result.lifecycle_record is not None
    assert result.lifecycle_record["status"] == "completed"
    assert result.lifecycle_record["result_record_id"]
    assert seen[0]["event"]["event_id"] == "event-1"
    assert seen[0]["context_results"][0]["ok"] is True
    recalled = memory.recall(record_id=result.lifecycle_record["result_record_id"])
    assert recalled.ok
    assert recalled.data["content"]["content"]["event_id"] == "event-1"


def test_dispatcher_context_failure_marks_failed_and_skips_handler():
    memory = LocalMemorySubstrate()
    queue = EventQueue()
    queue.append_pending(_event(event_id="missing"))
    calls = []

    dispatcher = SchedulerDispatcher(
        queue=queue,
        clock=SchedulerClock.start(BASE_TIME),
        memory=memory,
        handler=lambda envelope: calls.append(envelope) or "should not run",
    )

    result = dispatcher.dispatch_next()

    assert result.status == "failed"
    assert calls == []
    assert result.lifecycle_record is not None
    assert result.lifecycle_record["failure_layer"] == "context"
    assert result.lifecycle_record["error_type"] == "record_not_found"


def test_dispatcher_records_bounded_context_omission_on_completion():
    memory = LocalMemorySubstrate()
    _store_record(memory, content={"body": "x" * 200})
    queue = EventQueue()
    queue.append_pending(_event(event_id="bounded", field="body"))
    captured = []

    def handler(envelope):
        captured.append(envelope)
        return "bounded response"

    dispatcher = SchedulerDispatcher(
        queue=queue,
        clock=SchedulerClock.start(BASE_TIME),
        memory=memory,
        handler=handler,
        context_char_budget=12,
    )

    result = dispatcher.dispatch_next()

    assert result.status == "completed"
    assert captured[0].omissions == [
        {
            "request": {
                "tool": "recall",
                "record_id": str(RID_1),
                "field": "body",
            },
            "truncated": True,
            "omitted": ["payload_truncated"],
        }
    ]
    assert result.lifecycle_record is not None
    assert result.lifecycle_record["omissions"] == captured[0].omissions


def test_dispatcher_handler_failure_marks_failed_without_result_record():
    memory = LocalMemorySubstrate()
    _store_record(memory)
    queue = EventQueue()
    queue.append_pending(_event(event_id="handler-fail"))

    def handler(_envelope):
        raise RuntimeError("handler broke")

    dispatcher = SchedulerDispatcher(
        queue=queue,
        clock=SchedulerClock.start(BASE_TIME),
        memory=memory,
        handler=handler,
    )

    result = dispatcher.dispatch_next()

    assert result.status == "failed"
    assert result.lifecycle_record is not None
    assert result.lifecycle_record["failure_layer"] == "handler"
    assert result.lifecycle_record["error_type"] == "RuntimeError"
    assert "result_record_id" not in result.lifecycle_record


class _WriteFailingMemory(LocalMemorySubstrate):
    def store_episode(self, **kwargs):
        if kwargs.get("record_type") == "scheduled_wake_result":
            return MemoryResponse.failure(
                "forced_write_failure",
                "test write failure",
            )
        return super().store_episode(**kwargs)


def test_dispatcher_memory_write_failure_marks_failed_after_context_and_handler():
    memory = _WriteFailingMemory()
    _store_record(memory)
    queue = EventQueue()
    queue.append_pending(_event(event_id="write-fail"))
    calls = []

    dispatcher = SchedulerDispatcher(
        queue=queue,
        clock=SchedulerClock.start(BASE_TIME),
        memory=memory,
        handler=lambda envelope: calls.append(envelope) or "done",
    )

    result = dispatcher.dispatch_next()

    assert len(calls) == 1
    assert result.status == "failed"
    assert result.lifecycle_record is not None
    assert result.lifecycle_record["failure_layer"] == "memory_write"
    assert result.lifecycle_record["error_type"] == "forced_write_failure"


def test_dispatch_order_is_deterministic_for_replay():
    def run_once() -> list[str]:
        memory = LocalMemorySubstrate()
        _store_record(memory)
        queue = EventQueue()
        for event_id, priority in [("z", 3), ("a", 1), ("m", 2)]:
            queue.append_pending(
                _event(
                    event_id=event_id,
                    created_at="2026-06-08T11:00:00+00:00",
                    not_before="2026-06-08T12:00:00+00:00",
                    priority=priority,
                )
            )
        seen = []
        dispatcher = SchedulerDispatcher(
            queue=queue,
            clock=SchedulerClock.start(BASE_TIME),
            memory=memory,
            handler=lambda envelope: seen.append(envelope.event["event_id"]) or "ok",
        )
        while dispatcher.dispatch_next().status == "completed":
            pass
        return seen

    assert run_once() == ["a", "m", "z"]
    assert run_once() == ["a", "m", "z"]


def test_queue_mints_deterministic_local_ids_for_replay_without_caller_ids():
    def run_once() -> list[tuple[str, str]]:
        queue = EventQueue()
        for purpose in ["first", "second"]:
            queue.append_pending(
                {
                    "status": "pending",
                    "event_type": "reflection",
                    "not_before": BASE_TIME,
                    "created_at": BASE_TIME,
                    "purpose": purpose,
                }
            )

        claims = []
        now = SchedulerClock.start(BASE_TIME).now()
        while claim := queue.claim_next_due(now=now):
            claims.append((claim.event["event_id"], claim.running["run_id"]))
        return claims

    first = run_once()
    second = run_once()

    assert first == second
    assert len({event_id for event_id, _run_id in first}) == 2
    assert len({run_id for _event_id, run_id in first}) == 2


def test_tied_events_with_minted_ids_dispatch_deterministically():
    """Two events identical in every ordering field must dispatch in a stable
    order across constructions."""
    tie = {
        "status": "pending",
        "event_type": "reflection",
        "not_before": BASE_TIME,
        "created_at": BASE_TIME,
        "purpose": "tie",
    }
    orders = set()
    for _ in range(64):
        queue = EventQueue()
        first = queue.append_pending(dict(tie))
        second = queue.append_pending(dict(tie))
        position = {
            first["event_id"]: "first_appended",
            second["event_id"]: "second_appended",
        }
        dispatched = tuple(
            position[event["event_id"]] for event in queue.pending_events()
        )
        orders.add(dispatched)
    assert len(orders) == 1, (
        f"tied events dispatched in {len(orders)} distinct orders across "
        f"identical constructions: {orders}"
    )
