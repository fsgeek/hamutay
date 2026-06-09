"""Deterministic scheduler kernel for Hamut'ay event-loop experiments.

The kernel is intentionally small and explicit: it owns logical time, event
ordering, lifecycle transitions, context resolution through ``MemoryPort``, and
result persistence. It does not call models directly and it does not implement
wall-clock sleeping.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from hamutay.events import (
    EVENT_TYPE_REFLECTION,
    is_due,
    is_expired,
    validate_requested_context,
)
from hamutay.memory.bridge import JsonDict, MemoryPort, MemoryResponse


WakeHandler = Callable[["WakeEnvelope"], str | JsonDict]


def _parse_time(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


@dataclass
class SchedulerClock:
    """Logical clock for deterministic scheduler tests and replay."""

    current: datetime

    @classmethod
    def start(cls, value: datetime | str) -> "SchedulerClock":
        return cls(current=_parse_time(value))

    def now(self) -> datetime:
        return self.current

    def now_iso(self) -> str:
        return self.current.isoformat()

    def advance_to(self, value: datetime | str) -> None:
        target = _parse_time(value)
        if target < self.current:
            raise ValueError("SchedulerClock cannot move backward")
        self.current = target

    def advance_by(self, delta: timedelta) -> None:
        if delta.total_seconds() < 0:
            raise ValueError("SchedulerClock cannot move backward")
        self.current = self.current + delta


@dataclass
class QueueClaim:
    event: JsonDict
    running: JsonDict


@dataclass
class EventQueue:
    """Append-only in-memory lifecycle log with deterministic due ordering."""

    records: list[JsonDict] = field(default_factory=list)
    _sequence: int = 0

    def append_pending(self, event: JsonDict, *, priority: int = 0) -> JsonDict:
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        record = deepcopy(event)
        if record.get("status") != "pending":
            raise ValueError("event.status must be pending")
        if not record.get("event_id"):
            record["event_id"] = str(uuid4())
        record.setdefault("event_type", EVENT_TYPE_REFLECTION)
        record.setdefault("created_at", "1970-01-01T00:00:00+00:00")
        record["priority"] = int(priority if record.get("priority") is None else record["priority"])
        self._append(record)
        return deepcopy(record)

    def latest_by_event_id(self) -> dict[str, JsonDict]:
        latest: dict[str, JsonDict] = {}
        for record in self.records:
            event_id = record.get("event_id")
            if event_id:
                latest[str(event_id)] = record
        return deepcopy(latest)

    def pending_events(self) -> list[JsonDict]:
        pending = [
            record
            for record in self.latest_by_event_id().values()
            if record.get("status") == "pending"
        ]
        return sorted(pending, key=self._sort_key)

    def next_due(self, *, now: datetime) -> JsonDict | None:
        for event in self.pending_events():
            if is_expired(event, now=now) or is_due(event, now=now):
                return deepcopy(event)
        return None

    def claim_next_due(
        self,
        *,
        now: datetime,
        run_id: UUID | None = None,
    ) -> QueueClaim | None:
        event = self.next_due(now=now)
        if event is None:
            return None
        if is_expired(event, now=now):
            expired = self.append_expired(event, now=now)
            return QueueClaim(event=event, running=expired)
        running = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "running",
            "run_id": str(run_id or uuid4()),
            "started_at": now.isoformat(),
        }
        self._append(running)
        return QueueClaim(event=event, running=deepcopy(running))

    def append_completed(
        self,
        *,
        event: JsonDict,
        run_id: str,
        result_record_id: str,
        context_results: list[JsonDict],
        handler_result: JsonDict,
        now: datetime,
        omissions: list[JsonDict] | None = None,
    ) -> JsonDict:
        completed = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "completed",
            "run_id": run_id,
            "completed_at": now.isoformat(),
            "result_record_id": result_record_id,
            "context_results": _json_copy(context_results),
            "handler_result": _json_copy(handler_result),
        }
        if omissions:
            completed["omissions"] = _json_copy(omissions)
        self._append(completed)
        return deepcopy(completed)

    def append_failed(
        self,
        *,
        event: JsonDict,
        run_id: str,
        failure_layer: str,
        error_type: str,
        error: str,
        now: datetime,
        context_results: list[JsonDict] | None = None,
    ) -> JsonDict:
        failed = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "failed",
            "run_id": run_id,
            "failed_at": now.isoformat(),
            "failure_layer": failure_layer,
            "error_type": error_type,
            "error": error,
        }
        if context_results is not None:
            failed["context_results"] = _json_copy(context_results)
        self._append(failed)
        return deepcopy(failed)

    def append_expired(self, event: JsonDict, *, now: datetime) -> JsonDict:
        expired = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "expired",
            "expired_at": now.isoformat(),
        }
        self._append(expired)
        return deepcopy(expired)

    def _append(self, record: JsonDict) -> None:
        self._sequence += 1
        stored = deepcopy(record)
        stored["_scheduler_sequence"] = self._sequence
        self.records.append(stored)

    def _sort_key(self, event: JsonDict) -> tuple[str, int, str, str]:
        not_before = event.get("not_before") or event.get("created_at", "")
        created_at = str(event.get("created_at", ""))
        return (
            str(not_before),
            int(event.get("priority", 0)),
            created_at,
            str(event.get("event_id", "")),
        )


@dataclass
class WakeEnvelope:
    """Deterministic wake input passed to a scheduler wake handler."""

    event: JsonDict
    run_id: str
    clock: str
    context_results: list[JsonDict]
    omissions: list[JsonDict] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "event": deepcopy(self.event),
            "run_id": self.run_id,
            "clock": self.clock,
            "context_results": deepcopy(self.context_results),
            "omissions": deepcopy(self.omissions),
        }


@dataclass
class DispatchResult:
    """Outcome of one scheduler dispatch attempt."""

    status: str
    event_id: str | None = None
    run_id: str | None = None
    lifecycle_record: JsonDict | None = None
    wake_envelope: WakeEnvelope | None = None


class SchedulerDispatcher:
    """Claim due events, resolve context, invoke handler, and persist results."""

    def __init__(
        self,
        *,
        queue: EventQueue,
        clock: SchedulerClock,
        memory: MemoryPort,
        handler: WakeHandler,
        context_char_budget: int | None = None,
    ) -> None:
        self.queue = queue
        self.clock = clock
        self.memory = memory
        self.handler = handler
        self.context_char_budget = context_char_budget

    def dispatch_next(self) -> DispatchResult:
        claim = self.queue.claim_next_due(now=self.clock.now())
        if claim is None:
            return DispatchResult(status="no_due_event")
        if claim.running.get("status") == "expired":
            return DispatchResult(
                status="expired",
                event_id=claim.event.get("event_id"),
                lifecycle_record=claim.running,
            )

        event = claim.event
        running = claim.running
        run_id = str(running["run_id"])
        context_results = self._resolve_context(event)
        failed_context = next(
            (result for result in context_results if not result["ok"]),
            None,
        )
        if failed_context is not None:
            failed = self.queue.append_failed(
                event=event,
                run_id=run_id,
                failure_layer="context",
                error_type=str(failed_context["error"]["code"]),
                error=str(failed_context["error"]["message"]),
                context_results=context_results,
                now=self.clock.now(),
            )
            return DispatchResult(
                status="failed",
                event_id=event["event_id"],
                run_id=run_id,
                lifecycle_record=failed,
            )

        envelope = WakeEnvelope(
            event=deepcopy(event),
            run_id=run_id,
            clock=self.clock.now_iso(),
            context_results=context_results,
            omissions=self._context_omissions(context_results),
        )
        try:
            raw_result = self.handler(envelope)
        except Exception as exc:
            failed = self.queue.append_failed(
                event=event,
                run_id=run_id,
                failure_layer="handler",
                error_type=type(exc).__name__,
                error=str(exc),
                context_results=context_results,
                now=self.clock.now(),
            )
            return DispatchResult(
                status="failed",
                event_id=event["event_id"],
                run_id=run_id,
                lifecycle_record=failed,
                wake_envelope=envelope,
            )

        handler_result = (
            deepcopy(raw_result)
            if isinstance(raw_result, dict)
            else {"response": str(raw_result)}
        )
        stored = self.memory.store_episode(
            record_type="scheduled_wake_result",
            content={
                "event_id": event["event_id"],
                "run_id": run_id,
                "wake_envelope": envelope.to_dict(),
                "handler_result": _json_copy(handler_result),
            },
            production={
                "who": {"instance": "scheduler"},
                "what": {"artifact": "scheduled_wake_result"},
                "when": {"logical_time": self.clock.now_iso()},
                "where": {"project": "hamutay"},
            },
            execution_trace={"tool_path": "SchedulerDispatcher.dispatch_next"},
        )
        if not stored.ok:
            failed = self.queue.append_failed(
                event=event,
                run_id=run_id,
                failure_layer="memory_write",
                error_type=stored.error.code if stored.error else "unknown",
                error=stored.error.message if stored.error else "unknown",
                context_results=context_results,
                now=self.clock.now(),
            )
            return DispatchResult(
                status="failed",
                event_id=event["event_id"],
                run_id=run_id,
                lifecycle_record=failed,
                wake_envelope=envelope,
            )

        completed = self.queue.append_completed(
            event=event,
            run_id=run_id,
            result_record_id=str(stored.data["record_id"]),
            context_results=context_results,
            handler_result=handler_result,
            omissions=envelope.omissions,
            now=self.clock.now(),
        )
        return DispatchResult(
            status="completed",
            event_id=event["event_id"],
            run_id=run_id,
            lifecycle_record=completed,
            wake_envelope=envelope,
        )

    def _resolve_context(self, event: JsonDict) -> list[JsonDict]:
        requests = validate_requested_context(event.get("requested_context", []))
        results: list[JsonDict] = []
        for request in requests:
            tool = request["tool"]
            reason = {
                "text": "scheduler context resolution",
                "event_id": event["event_id"],
                "tool": tool,
            }
            if tool == "recall":
                response = self.memory.recall(
                    record_id=request["record_id"],
                    field=request.get("field"),
                    max_chars=self.context_char_budget,
                    reason=reason,
                )
            elif tool == "walk":
                response = self.memory.walk(
                    from_record_id=request["from_record_id"],
                    direction=request.get("direction", "both"),
                    depth=request.get("depth", 1),
                    reason=reason,
                )
            else:
                response = MemoryResponse.failure(
                    "unsupported_context_tool",
                    f"context tool {tool!r} is not supported by SchedulerDispatcher",
                    tool=tool,
                )
            result = response.to_dict()
            results.append(
                {
                    "request": deepcopy(request),
                    "ok": bool(response.ok),
                    "result": result if response.ok else None,
                    "error": result.get("error") if not response.ok else None,
                }
            )
        return results

    def _context_omissions(self, context_results: list[JsonDict]) -> list[JsonDict]:
        omissions: list[JsonDict] = []
        for result in context_results:
            payload = result.get("result") or {}
            if payload.get("truncated") or payload.get("omitted"):
                omissions.append(
                    {
                        "request": deepcopy(result["request"]),
                        "truncated": bool(payload.get("truncated")),
                        "omitted": deepcopy(payload.get("omitted", [])),
                    }
                )
        return omissions
