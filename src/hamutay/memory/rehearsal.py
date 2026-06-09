"""Fake-backed autonomous scheduler rehearsal.

This module spends no model tokens. It exists to prove the live framework shape
before real autonomy experiments: scheduler dispatch builds a wake envelope,
the autonomous driver runs cognition from that wake, memory records open work,
closure semantics remove resolved work from the live queue, and the driver idles
without human input.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from hamutay.events import build_pending_event
from hamutay.memory.bridge import JsonDict, LocalMemorySubstrate
from hamutay.memory.driver import AutonomousDriver, DriverReport
from hamutay.scheduler import (
    DispatchResult,
    EventQueue,
    SchedulerClock,
    SchedulerDispatcher,
    WakeEnvelope,
)


REHEARSAL_TIME = "2026-06-08T12:00:00+00:00"


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def driver_report_to_dict(report: DriverReport) -> JsonDict:
    return {
        "ran": report.ran,
        "stopped_because": report.stopped_because,
        "cycles": [
            {
                "cycle": cycle.cycle,
                "record_id": cycle.record_id,
                "stimulus": cycle.stimulus,
                "response": cycle.response,
                "open_items_surfaced": _json_copy(cycle.open_items_surfaced),
                "woke_on": cycle.woke_on,
                "wake_omission": _json_copy(cycle.wake_omission),
            }
            for cycle in report.cycles
        ],
    }


def render_wake_seed(envelope: WakeEnvelope) -> str:
    """Render a deterministic scheduler wake as the driver's seed stimulus."""

    return (
        "Scheduled autonomous wake.\n"
        f"Purpose: {envelope.event.get('purpose', '')}\n"
        f"Run: {envelope.run_id}\n"
        f"Clock: {envelope.clock}\n"
        "Resolved context:\n"
        f"{json.dumps(envelope.context_results, default=str, sort_keys=True)}"
    )


class FakeRehearsalCognition:
    """Deterministic cognition used by the no-token rehearsal."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, stimulus: str) -> str:
        self.calls.append(stimulus)
        if "Continue your own open work" in stimulus:
            return "Resolved the rehearsal open item; no new work remains."
        return "Opened one rehearsal item that must be resolved on the next wake."


def fake_rehearsal_open_item_extractor(
    _stimulus: str,
    response: str,
) -> list[JsonDict]:
    if response.startswith("Opened one rehearsal item"):
        return [{"kind": "todo", "text": "resolve rehearsal item"}]
    return []


class ClosingRehearsalMemory(LocalMemorySubstrate):
    """Local substrate that turns fake resolution into append-only closure.

    This is intentionally rehearsal-only. Production closure should come from a
    model-facing action protocol; this shim keeps the no-token rehearsal focused
    on whether the framework surfaces and honors closure semantics end to end.
    """

    def __init__(self) -> None:
        super().__init__()
        self.closed_handles: list[JsonDict] = []
        self._pending_handle: JsonDict | None = None

    def store_episode(self, **kwargs: Any):
        response = super().store_episode(**kwargs)
        if not response.ok or kwargs.get("record_type") != "autonomous_cycle":
            return response

        record_id = response.data["record_id"]
        content = kwargs.get("content", {})
        if content.get("open_items"):
            self._pending_handle = {
                "record_id": record_id,
                "source": "open_items",
                "index": 0,
            }
            return response

        if self._pending_handle and "Continue your own open work" in str(
            content.get("stimulus", "")
        ):
            closed = self.write_attestation(
                subject_record_id=self._pending_handle["record_id"],
                kind="closure",
                status="resolved",
                content={
                    "target_handle": deepcopy(self._pending_handle),
                    "basis": (
                        "fake cognition consumed the open item and surfaced "
                        "no replacement"
                    ),
                },
                provenance={"actor": "fake_rehearsal"},
                scope=self._pending_handle["source"],
            )
            if closed.ok:
                self.closed_handles.append(deepcopy(self._pending_handle))
                self._pending_handle = None
        return response


class AutonomousSchedulerWakeHandler:
    """Scheduler handler that runs one bounded autonomous driver rehearsal."""

    def __init__(
        self,
        *,
        memory: LocalMemorySubstrate,
        cognition: FakeRehearsalCognition,
        max_cycles: int = 3,
        instance_id: str = "fake-autonomous-rehearsal",
    ) -> None:
        self.memory = memory
        self.cognition = cognition
        self.max_cycles = max_cycles
        self.instance_id = instance_id
        self.last_report: DriverReport | None = None

    def __call__(self, envelope: WakeEnvelope) -> JsonDict:
        driver = AutonomousDriver(
            self.memory,
            self.cognition,
            seed_intention=render_wake_seed(envelope),
            open_item_extractor=fake_rehearsal_open_item_extractor,
            instance_id=self.instance_id,
        )
        report = driver.run(max_cycles=self.max_cycles)
        self.last_report = report
        return {
            "response": "fake autonomous rehearsal completed",
            "driver_report": driver_report_to_dict(report),
        }


@dataclass
class RehearsalResult:
    memory: ClosingRehearsalMemory
    queue: EventQueue
    dispatch: DispatchResult
    handler: AutonomousSchedulerWakeHandler
    anchor_record_id: str

    def to_dict(self) -> JsonDict:
        retrievals = self.memory.retrieval_log()
        open_items = self.memory.open_items(reason="fake rehearsal final open check")
        return {
            "anchor_record_id": self.anchor_record_id,
            "dispatch_status": self.dispatch.status,
            "event_id": self.dispatch.event_id,
            "run_id": self.dispatch.run_id,
            "lifecycle_record": _json_copy(self.dispatch.lifecycle_record),
            "driver_report": (
                driver_report_to_dict(self.handler.last_report)
                if self.handler.last_report is not None
                else None
            ),
            "queue_records": _json_copy(self.queue.records),
            "closed_handles": _json_copy(self.memory.closed_handles),
            "open_items_after": open_items.to_dict(),
            "retrieval_log": retrievals.to_dict(),
        }


def run_fake_autonomy_rehearsal(
    *,
    now: str = REHEARSAL_TIME,
) -> RehearsalResult:
    memory = ClosingRehearsalMemory()
    anchor_record_id = uuid4()
    stored = memory.store_episode(
        record_id=anchor_record_id,
        record_type="rehearsal_anchor",
        content={
            "claim": "fake-backed autonomous rehearsal anchor",
            "body": "scheduler context should be recalled before driver wake",
        },
        production={
            "who": {"instance": "fake-rehearsal"},
            "what": {"artifact": "rehearsal_anchor"},
            "when": {"logical_time": now},
            "where": {"project": "hamutay"},
        },
        execution_trace={"tool_path": "run_fake_autonomy_rehearsal"},
    )
    if not stored.ok:
        raise RuntimeError("failed to store rehearsal anchor")

    queue = EventQueue()
    event = build_pending_event(
        purpose="run fake autonomous scheduler rehearsal",
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(anchor_record_id),
                "field": "claim",
            }
        ],
        scheduled_by_cycle=0,
        scheduled_by_record_id=UUID(str(anchor_record_id)),
        not_before=now,
    )
    event["created_at"] = now
    queue.append_pending(event)

    cognition = FakeRehearsalCognition()
    handler = AutonomousSchedulerWakeHandler(memory=memory, cognition=cognition)
    dispatcher = SchedulerDispatcher(
        queue=queue,
        clock=SchedulerClock.start(datetime.fromisoformat(now)),
        memory=memory,
        handler=handler,
    )
    dispatch = dispatcher.dispatch_next()
    return RehearsalResult(
        memory=memory,
        queue=queue,
        dispatch=dispatch,
        handler=handler,
        anchor_record_id=str(anchor_record_id),
    )


def main() -> None:
    print(json.dumps(run_fake_autonomy_rehearsal().to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
