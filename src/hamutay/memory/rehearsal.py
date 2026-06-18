"""Restartable no-token autonomous rehearsal.

This module proves the live autonomy shape without model calls. The fake
cognition emits the same model-authored action objects a live run will need:
cycle 1 opens work and schedules a wake; cycle 2 closes the exact open handle
and stops. The parser, action ledger, action applier, persisted event log, and
restart frontier are all exercised.
"""

from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import EVENT_TYPE_REFLECTION, EventStore, build_pending_event
from hamutay.memory.action_application import AutonomousActionApplier
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.bridge import (
    OPEN_CONTENT_FIELDS,
    JsonDict,
    LocalMemorySubstrate,
)
from hamutay.memory.restart_frontier import RestartFrontierStore


WAKE_RUN_ID = UUID("60000000-0000-0000-0000-000000000001")
RUN_ID = str(WAKE_RUN_ID)
REHEARSAL_TIME = "2026-06-08T12:00:00+00:00"
EVENT_TYPE_INBOUND_MESSAGE = "inbound_message"
EVENT_TYPE_HOUSEKEEPING = "housekeeping"
SUSTAINED_REHEARSAL_TARGET_CYCLE = 10


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _cycle_record_id(cycle_id: int) -> UUID:
    return UUID(f"60000000-0000-0000-0000-0000000001{cycle_id:02d}")


@dataclass(frozen=True)
class RehearsalPaths:
    root: Path
    ledger_path: Path
    event_path: Path
    frontier_path: Path
    memory_snapshot_path: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "RehearsalPaths":
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        return cls(
            root=root,
            ledger_path=root / "actions.jsonl",
            event_path=root / "events.jsonl",
            frontier_path=root / "restart_frontier.jsonl",
            memory_snapshot_path=root / "memory_snapshot.json",
        )

    def to_dict(self) -> JsonDict:
        return {
            "root": str(self.root),
            "ledger_path": str(self.ledger_path),
            "event_path": str(self.event_path),
            "frontier_path": str(self.frontier_path),
            "memory_snapshot_path": str(self.memory_snapshot_path),
        }


@dataclass(frozen=True)
class RehearsalResult:
    paths: RehearsalPaths
    report: JsonDict

    def to_dict(self) -> JsonDict:
        return deepcopy(self.report)


class RehearsalInterrupted(RuntimeError):
    """Raised by tests to simulate a process death at a named boundary."""


class FakeActionCognition:
    """Deterministic no-token source of model-authored action objects."""

    def seed_action(self) -> JsonDict:
        return {
            "response": "I found one bounded item and scheduled the next wake.",
            "open_items": [
                {
                    "kind": "todo",
                    "text": "resolve restartable rehearsal item",
                }
            ],
            "schedule_requests": [
                {
                    "purpose": "resume and close restartable rehearsal item",
                    "requested_context": [
                        {
                            "tool": "recall",
                            "record_id": str(_cycle_record_id(1)),
                        }
                    ],
                    "not_before": REHEARSAL_TIME,
                }
            ],
        }

    def closure_action(self, *, target_handle: JsonDict) -> JsonDict:
        return {
            "response": "I closed the scheduled rehearsal item and can stop.",
            "closures": [
                {
                    "target_handle": deepcopy(target_handle),
                    "status": "resolved",
                    "basis": "model-authored closure in no-token rehearsal",
                }
            ],
            "policy_action": "stop_complete",
        }


class FakeSustainedEventCognition:
    """Deterministic no-token cognition for a mixed sustained event stream."""

    def inbound_action(self) -> JsonDict:
        return {
            "response": "I accepted the inbound IPC message and scheduled follow-up.",
            "open_items": [
                {
                    "kind": "todo",
                    "text": "finish bounded inbound request",
                }
            ],
            "schedule_requests": [
                {
                    "purpose": "continue bounded inbound request",
                    "requested_context": [
                        {
                            "tool": "recall",
                            "record_id": str(_cycle_record_id(1)),
                        }
                    ],
                    "label": "self-scheduled-continuation",
                    "not_before": REHEARSAL_TIME,
                }
            ],
            "policy_action": "continue_after",
        }

    def continuation_action(self, *, target_handle: JsonDict) -> JsonDict:
        return {
            "response": "I finished the self-scheduled continuation.",
            "closures": [
                {
                    "target_handle": deepcopy(target_handle),
                    "status": "resolved",
                    "basis": "self-scheduled continuation resolved bounded work",
                }
            ],
            "policy_action": "stop_complete",
        }


class RestartableAutonomyRehearsal:
    """Run or resume the persisted no-token rehearsal."""

    def __init__(
        self,
        *,
        paths: RehearsalPaths,
        run_id: str = RUN_ID,
        cognition: FakeActionCognition | None = None,
    ) -> None:
        self.paths = paths
        self.run_id = run_id
        self.cognition = cognition or FakeActionCognition()

    def run(self, *, interrupt_after: str | None = None) -> RehearsalResult:
        memory, ledger, event_store, frontier_store, load = self._load()
        if load.frontier is None:
            frontier_store.ensure_run_manifest(
                ledger=ledger,
                run_id=self.run_id,
                manifest={
                    "rehearsal": "restartable_no_token",
                    "model": "fake-action-cognition",
                    "live_model_calls": False,
                },
                sandbox={
                    "shell": "disabled",
                    "network": "disabled",
                    "tool_surface": "memory/event/action harness only",
                },
            )
            frontier_store.commit_frontier(
                run_id=self.run_id,
                cycle_id=0,
                result_record_id=None,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                notes={"boundary": "initial"},
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        if load.frontier.next_cycle_id <= 1:
            self._run_seed_cycle(
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                frontier_store=frontier_store,
                interrupt_after=interrupt_after,
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        if load.frontier.next_cycle_id <= 2:
            self._run_scheduled_closure_cycle(
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                frontier_store=frontier_store,
                interrupt_after=interrupt_after,
            )

        return RehearsalResult(
            paths=self.paths,
            report=reconstruct_rehearsal_report(self.paths, run_id=self.run_id),
        )

    def _run_seed_cycle(
        self,
        *,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
        interrupt_after: str | None,
    ) -> None:
        applier = self._applier(memory=memory, ledger=ledger, event_store=event_store)
        model_input = {
            "cycle_id": 1,
            "wake_reason": "initial bounded autonomy rehearsal seed",
            "frontier": "initial",
            "visible_context": [],
            "requested_action": "open one bounded item and schedule one wake",
        }
        action = self.cognition.seed_action()
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=1,
            operation_id="cycle-1:present-wake-to-model",
            operation_type="present_wake_to_model",
            actor="harness",
            raw_parameters=model_input,
            validated_parameters=model_input,
            reason="seed cycle model-facing wake input",
            precondition_checks=[
                {"name": "frontier_loaded", "ok": True},
            ],
            result_status="applied",
            result={"model_input": model_input},
        )
        result = applier.apply_trace(
            parse_autonomous_action(action).to_dict(),
            run_id=self.run_id,
            cycle_id=1,
            result_record_id=_cycle_record_id(1),
        )
        if interrupt_after == "after_seed_apply":
            raise RehearsalInterrupted("after_seed_apply")
        frontier_store.commit_frontier(
            run_id=self.run_id,
            cycle_id=1,
            result_record_id=result.result_record_id,
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            notes={"boundary": "after seed/open/schedule"},
        )

    def _run_scheduled_closure_cycle(
        self,
        *,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
        interrupt_after: str | None,
    ) -> None:
        claimed = event_store.claim_next_pending(run_id=WAKE_RUN_ID)
        if claimed is None:
            open_items = memory.open_items(reason="rehearsal idle check")
            if open_items.ok and open_items.data.get("items") == []:
                return
            raise RuntimeError("no pending event available for rehearsal closure")
        event, running = claimed
        if running.get("status") != "running":
            raise RuntimeError("rehearsal event was not claimed as running")
        if interrupt_after == "after_event_claim":
            raise RehearsalInterrupted("after_event_claim")

        open_items = memory.open_items(reason="rehearsal closure target selection")
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=2,
            operation_id="cycle-2:memory-open-items-for-closure",
            operation_type="memory_open_items",
            actor="memory",
            raw_parameters={"reason": "rehearsal closure target selection"},
            validated_parameters={"reason": "rehearsal closure target selection"},
            reason="select exact closure target for scheduled wake",
            precondition_checks=[
                {"name": "event_claimed_running", "ok": True},
            ],
            result_status="applied" if open_items.ok else "failed",
            result=open_items.to_dict(),
            error=None if open_items.ok else open_items.to_dict().get("error"),
        )
        if not open_items.ok:
            raise RuntimeError("open_items failed during rehearsal closure")
        items = open_items.data.get("items", [])
        if len(items) != 1:
            raise RuntimeError(f"expected exactly one open item, got {len(items)}")
        model_input = {
            "cycle_id": 2,
            "wake_reason": "scheduled continuation wake",
            "event": event,
            "running_event": running,
            "visible_context": [],
            "available_open_items": _json_copy(items),
            "requested_action": "close the exact open handle if resolved",
        }
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=2,
            operation_id="cycle-2:present-wake-to-model",
            operation_type="present_wake_to_model",
            actor="harness",
            raw_parameters=model_input,
            validated_parameters=model_input,
            reason="scheduled cycle model-facing wake input",
            precondition_checks=[
                {"name": "event_claimed_running", "ok": True},
                {"name": "open_items_loaded", "ok": True},
            ],
            result_status="applied",
            result={"model_input": model_input},
        )
        action = self.cognition.closure_action(
            target_handle=items[0]["handle"],
        )
        applier = self._applier(memory=memory, ledger=ledger, event_store=event_store)
        result = applier.apply_trace(
            parse_autonomous_action(action).to_dict(),
            run_id=self.run_id,
            cycle_id=2,
            result_record_id=_cycle_record_id(2),
            event=event,
        )
        completed = event_store.append_completed(
            event=event,
            run_id=str(WAKE_RUN_ID),
            wake_cycle=2,
            result_record_id=UUID(str(result.result_record_id)),
            response_text=action["response"],
            context_results=[],
        )
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=2,
            operation_id="cycle-2:complete-scheduled-event",
            operation_type="complete_rehearsal_event",
            actor="scheduler",
            raw_parameters={"event": event},
            validated_parameters={"completed_event_id": event["event_id"]},
            reason="scheduled closure cycle completed",
            precondition_checks=[
                {"name": "event_claimed_running", "ok": True},
            ],
            result_status="applied",
            result={"completed": completed},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": completed["event_id"],
                    "status": "completed",
                }
            ],
        )
        frontier_store.commit_frontier(
            run_id=self.run_id,
            cycle_id=2,
            result_record_id=result.result_record_id,
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            notes={"boundary": "after model-authored closure"},
        )

    def _load(
        self,
    ) -> tuple[
        LocalMemorySubstrate,
        ActionLedger,
        EventStore,
        RestartFrontierStore,
        Any,
    ]:
        memory = LocalMemorySubstrate()
        ledger = ActionLedger(self.paths.ledger_path)
        event_store = EventStore(self.paths.event_path)
        frontier_store = RestartFrontierStore(
            frontier_path=self.paths.frontier_path,
            memory_snapshot_path=self.paths.memory_snapshot_path,
        )
        load = frontier_store.load_latest(
            run_id=self.run_id,
            memory=memory,
            ledger=ledger,
            event_store=event_store,
        )
        return memory, ledger, event_store, frontier_store, load

    @staticmethod
    def _applier(
        *,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
    ) -> AutonomousActionApplier:
        return AutonomousActionApplier(
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            instance_id="fake-restartable-rehearsal",
        )


class SustainedEventLoopReadinessRehearsal:
    """Run or resume a mixed-event no-token sustained loop rehearsal."""

    def __init__(
        self,
        *,
        paths: RehearsalPaths,
        run_id: str = RUN_ID,
        cognition: FakeSustainedEventCognition | None = None,
    ) -> None:
        self.paths = paths
        self.run_id = run_id
        self.cognition = cognition or FakeSustainedEventCognition()

    def run(self, *, interrupt_after: str | None = None) -> RehearsalResult:
        memory, ledger, event_store, frontier_store, load = self._load()
        if load.frontier is None:
            self._initialize(
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                frontier_store=frontier_store,
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        if load.frontier.next_cycle_id <= 1:
            self._run_model_event_cycle(
                expected_event_type=EVENT_TYPE_INBOUND_MESSAGE,
                cycle_id=1,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                frontier_store=frontier_store,
                action=self.cognition.inbound_action(),
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        if load.frontier.next_cycle_id <= 2:
            open_items = memory.open_items(
                reason="sustained continuation closure target selection"
            )
            if not open_items.ok:
                raise RuntimeError("open_items failed during sustained continuation")
            items = open_items.data.get("items", [])
            if len(items) != 1:
                raise RuntimeError(
                    f"expected exactly one sustained open item, got {len(items)}"
                )
            self._run_model_event_cycle(
                expected_event_type=EVENT_TYPE_REFLECTION,
                cycle_id=2,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                frontier_store=frontier_store,
                action=self.cognition.continuation_action(
                    target_handle=items[0]["handle"],
                ),
            )
            self._append_housekeeping_event(
                ledger=ledger,
                event_store=event_store,
                scheduled_by_record_id=str(_cycle_record_id(2)),
            )
            frontier_store.commit_frontier(
                run_id=self.run_id,
                cycle_id=2,
                result_record_id=str(_cycle_record_id(2)),
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                notes={"boundary": "after continuation and housekeeping scheduling"},
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        while load.frontier.next_cycle_id <= SUSTAINED_REHEARSAL_TARGET_CYCLE:
            cycle_id = load.frontier.next_cycle_id
            self._run_housekeeping_cycle(
                cycle_id=cycle_id,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                frontier_store=frontier_store,
                interrupt_after=interrupt_after,
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        return RehearsalResult(
            paths=self.paths,
            report=reconstruct_sustained_event_loop_report(
                self.paths,
                run_id=self.run_id,
            ),
        )

    def _initialize(
        self,
        *,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
    ) -> None:
        frontier_store.ensure_run_manifest(
            ledger=ledger,
            run_id=self.run_id,
            manifest={
                "rehearsal": "sustained_mixed_event_loop_readiness_no_token",
                "model": "fake-sustained-event-cognition",
                "live_model_calls": False,
                "event_types": [
                    EVENT_TYPE_INBOUND_MESSAGE,
                    EVENT_TYPE_REFLECTION,
                    EVENT_TYPE_HOUSEKEEPING,
                ],
            },
            sandbox={
                "shell": "disabled",
                "network": "disabled",
                "tool_surface": "memory/event/action harness only",
            },
        )
        inbound_record = memory.store_episode(
            record_id=_cycle_record_id(0),
            record_type="inbound_message",
            content={
                "message": "IPC request: solve one bounded item and report closure.",
                "channel": "user-ipc",
            },
            production={
                "who": {"instance": "external-user"},
                "what": {"artifact": "inbound_message"},
                "when": {"cycle": 0},
                "where": {"project": "hamutay"},
            },
            execution_trace={
                "tool_path": "sustained_event_loop_rehearsal",
                "run_id": self.run_id,
            },
        )
        if not inbound_record.ok:
            raise RuntimeError("failed to store inbound message seed")
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=0,
            operation_id="cycle-0:ingest-inbound-message",
            operation_type="ingest_inbound_message",
            actor="ipc",
            raw_parameters={"message": inbound_record.to_dict()},
            validated_parameters={"record_id": str(_cycle_record_id(0))},
            reason="ingest user IPC message as event-loop input",
            precondition_checks=[{"name": "memory_available", "ok": True}],
            result_status="applied",
            result=inbound_record.to_dict(),
            created_records=[
                {
                    "record_type": "memory_record",
                    "record_id": str(_cycle_record_id(0)),
                }
            ],
        )
        event = build_pending_event(
            purpose="Handle inbound IPC message.",
            requested_context=[
                {"tool": "recall", "record_id": str(_cycle_record_id(0))}
            ],
            scheduled_by_cycle=0,
            scheduled_by_record_id=_cycle_record_id(0),
            label="inbound-message",
            not_before=REHEARSAL_TIME,
        )
        event["event_type"] = EVENT_TYPE_INBOUND_MESSAGE
        event_store.append(event)
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=0,
            operation_id="cycle-0:append-inbound-event",
            operation_type="append_inbound_event",
            actor="scheduler",
            raw_parameters={"event": event},
            validated_parameters={"event_id": event["event_id"]},
            reason="queue inbound message for event-loop handling",
            precondition_checks=[{"name": "event_store_available", "ok": True}],
            result_status="applied",
            result={"event_id": event["event_id"], "status": "pending"},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": event["event_id"],
                    "status": "pending",
                }
            ],
        )
        frontier_store.commit_frontier(
            run_id=self.run_id,
            cycle_id=0,
            result_record_id=str(_cycle_record_id(0)),
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            notes={"boundary": "initial inbound event queued"},
        )

    def _run_model_event_cycle(
        self,
        *,
        expected_event_type: str,
        cycle_id: int,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
        action: JsonDict,
    ) -> None:
        claimed = event_store.claim_next_pending(run_id=WAKE_RUN_ID)
        if claimed is None:
            raise RuntimeError(f"no pending event available for cycle {cycle_id}")
        event, running = claimed
        if running.get("status") != "running":
            raise RuntimeError(f"cycle {cycle_id} event was not claimed as running")
        if event.get("event_type") != expected_event_type:
            raise RuntimeError(
                f"cycle {cycle_id} expected {expected_event_type}, "
                f"got {event.get('event_type')}"
            )
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=cycle_id,
            wake_id=event["event_id"],
            operation_id=f"cycle-{cycle_id}:present-wake-to-model",
            operation_type="present_wake_to_model",
            actor="harness",
            raw_parameters={"event": event, "running_event": running},
            validated_parameters={
                "event_id": event["event_id"],
                "event_type": event.get("event_type"),
            },
            reason="present mixed-stream wake to deterministic cognition",
            precondition_checks=[
                {"name": "event_claimed_running", "ok": True},
            ],
            result_status="applied",
            result={"model_input": {"event": event, "cycle_id": cycle_id}},
        )
        applier = self._applier(memory=memory, ledger=ledger, event_store=event_store)
        result = applier.apply_trace(
            parse_autonomous_action(action).to_dict(),
            run_id=self.run_id,
            cycle_id=cycle_id,
            wake_id=event["event_id"],
            result_record_id=_cycle_record_id(cycle_id),
            event=event,
        )
        completed = event_store.append_completed(
            event=event,
            run_id=str(WAKE_RUN_ID),
            wake_cycle=cycle_id,
            result_record_id=UUID(str(result.result_record_id)),
            response_text=action["response"],
            context_results=[],
        )
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=cycle_id,
            wake_id=event["event_id"],
            operation_id=f"cycle-{cycle_id}:complete-event",
            operation_type="complete_mixed_event",
            actor="scheduler",
            raw_parameters={"event": event},
            validated_parameters={"completed_event_id": event["event_id"]},
            reason="mixed event cycle completed",
            precondition_checks=[{"name": "event_claimed_running", "ok": True}],
            result_status="applied",
            result={"completed": completed},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": completed["event_id"],
                    "status": "completed",
                }
            ],
        )
        if cycle_id != 2:
            frontier_store.commit_frontier(
                run_id=self.run_id,
                cycle_id=cycle_id,
                result_record_id=result.result_record_id,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                notes={"boundary": f"after mixed event cycle {cycle_id}"},
            )

    def _append_housekeeping_event(
        self,
        *,
        ledger: ActionLedger,
        event_store: EventStore,
        scheduled_by_cycle: int = 2,
        scheduled_by_record_id: str,
    ) -> None:
        event = build_pending_event(
            purpose="Audit open work and lifecycle cleanliness.",
            requested_context=[
                {"tool": "recall", "record_id": scheduled_by_record_id}
            ],
            scheduled_by_cycle=scheduled_by_cycle,
            scheduled_by_record_id=UUID(scheduled_by_record_id),
            label=f"housekeeping-open-work-audit-{scheduled_by_cycle + 1}",
            not_before=REHEARSAL_TIME,
        )
        event["event_type"] = EVENT_TYPE_HOUSEKEEPING
        event_store.append(event)
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=scheduled_by_cycle,
            wake_id=event["event_id"],
            operation_id=f"cycle-{scheduled_by_cycle}:append-housekeeping-event",
            operation_type="append_housekeeping_event",
            actor="scheduler",
            raw_parameters={"event": event},
            validated_parameters={"event_id": event["event_id"]},
            reason="queue first-class housekeeping event",
            precondition_checks=[{"name": "event_store_available", "ok": True}],
            result_status="applied",
            result={"event_id": event["event_id"], "status": "pending"},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": event["event_id"],
                    "status": "pending",
                }
            ],
        )

    def _run_housekeeping_cycle(
        self,
        *,
        cycle_id: int,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
        interrupt_after: str | None,
    ) -> None:
        claimed = event_store.claim_next_pending(run_id=WAKE_RUN_ID)
        if claimed is None:
            raise RuntimeError("no pending housekeeping event available")
        event, running = claimed
        if running.get("status") != "running":
            raise RuntimeError("housekeeping event was not claimed as running")
        if event.get("event_type") != EVENT_TYPE_HOUSEKEEPING:
            raise RuntimeError(
                f"expected housekeeping event, got {event.get('event_type')}"
            )
        if interrupt_after == "after_housekeeping_claim":
            raise RehearsalInterrupted("after_housekeeping_claim")

        open_items = memory.open_items(reason="housekeeping open-work audit")
        if not open_items.ok:
            raise RuntimeError("open_items failed during housekeeping audit")
        latest_events = event_store.latest_by_event_id()
        pending_or_running = [
            event_id for event_id, latest in latest_events.items()
            if latest.get("status") in {"pending", "running"}
            and event_id != event["event_id"]
        ]
        audit = {
            "open_item_count": len(open_items.data.get("items", [])),
            "pending_or_running_other_event_ids": pending_or_running,
            "event_count": len(latest_events),
            "cycle_id": cycle_id,
        }
        stored = memory.store_episode(
            record_id=_cycle_record_id(cycle_id),
            record_type="housekeeping_audit",
            content=audit,
            production={
                "who": {"instance": "hamutay-autonomous"},
                "what": {"artifact": "housekeeping_audit"},
                "when": {"cycle": cycle_id},
                "where": {"project": "hamutay"},
            },
            execution_trace={
                "tool_path": "sustained_event_loop_rehearsal",
                "run_id": self.run_id,
                "wake_id": event["event_id"],
            },
        )
        if not stored.ok:
            raise RuntimeError("failed to store housekeeping audit")
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=cycle_id,
            wake_id=event["event_id"],
            operation_id=f"cycle-{cycle_id}:run-housekeeping-audit",
            operation_type="run_housekeeping_audit",
            actor="housekeeping",
            raw_parameters={"event": event},
            validated_parameters={"event_id": event["event_id"]},
            reason="audit bounded open work and event lifecycle",
            precondition_checks=[{"name": "event_claimed_running", "ok": True}],
            result_status="applied",
            result=stored.to_dict(),
            created_records=[
                {
                    "record_type": "memory_record",
                    "record_id": str(_cycle_record_id(cycle_id)),
                }
            ],
        )
        completed = event_store.append_completed(
            event=event,
            run_id=str(WAKE_RUN_ID),
            wake_cycle=cycle_id,
            result_record_id=_cycle_record_id(cycle_id),
            response_text="housekeeping audit completed",
            context_results=[],
            outcome_observation=audit,
        )
        ledger.append_operation(
            run_id=self.run_id,
            cycle_id=cycle_id,
            wake_id=event["event_id"],
            operation_id=f"cycle-{cycle_id}:complete-housekeeping-event",
            operation_type="complete_housekeeping_event",
            actor="scheduler",
            raw_parameters={"event": event},
            validated_parameters={"completed_event_id": event["event_id"]},
            reason="housekeeping event completed",
            precondition_checks=[{"name": "event_claimed_running", "ok": True}],
            result_status="applied",
            result={"completed": completed},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": completed["event_id"],
                    "status": "completed",
                }
            ],
        )
        if cycle_id < SUSTAINED_REHEARSAL_TARGET_CYCLE:
            self._append_housekeeping_event(
                ledger=ledger,
                event_store=event_store,
                scheduled_by_cycle=cycle_id,
                scheduled_by_record_id=str(_cycle_record_id(cycle_id)),
            )
        frontier_store.commit_frontier(
            run_id=self.run_id,
            cycle_id=cycle_id,
            result_record_id=str(_cycle_record_id(cycle_id)),
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            notes={"boundary": f"after housekeeping audit cycle {cycle_id}"},
        )

    def _load(
        self,
    ) -> tuple[
        LocalMemorySubstrate,
        ActionLedger,
        EventStore,
        RestartFrontierStore,
        Any,
    ]:
        memory = LocalMemorySubstrate()
        ledger = ActionLedger(self.paths.ledger_path)
        event_store = EventStore(self.paths.event_path)
        frontier_store = RestartFrontierStore(
            frontier_path=self.paths.frontier_path,
            memory_snapshot_path=self.paths.memory_snapshot_path,
        )
        load = frontier_store.load_latest(
            run_id=self.run_id,
            memory=memory,
            ledger=ledger,
            event_store=event_store,
        )
        return memory, ledger, event_store, frontier_store, load

    @staticmethod
    def _applier(
        *,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
    ) -> AutonomousActionApplier:
        return AutonomousActionApplier(
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            instance_id="fake-sustained-event-loop",
        )


def reconstruct_rehearsal_report(
    paths: RehearsalPaths,
    *,
    run_id: str = RUN_ID,
) -> JsonDict:
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths.ledger_path)
    event_store = EventStore(paths.event_path)
    frontier_store = RestartFrontierStore(
        frontier_path=paths.frontier_path,
        memory_snapshot_path=paths.memory_snapshot_path,
    )
    load = frontier_store.load_latest(
        run_id=run_id,
        memory=memory,
        ledger=ledger,
        event_store=event_store,
    )
    open_items = memory.open_items(reason="rehearsal report final open check")
    ledger_records = ledger.read_records()
    operations = [
        record["payload"]
        for record in ledger_records
        if record.get("record_type") == "operation"
    ]
    action_traces = [
        record["payload"]["trace"]
        for record in ledger_records
        if record.get("record_type") == "action_trace"
    ]
    closure_operations = [
        op for op in operations
        if op.get("operation_type") == "apply_closure"
        and op.get("result_status") == "applied"
    ]
    memory_snapshot = memory.snapshot()
    closure_attestations = [
        attestation for attestation in memory_snapshot["attestations"]
        if attestation.get("kind") == "closure"
        and attestation.get("status") == "resolved"
    ]
    event_records = event_store.read_records()
    latest_events = _latest_event_records(event_records)
    open_item_handle_keys = _open_item_handle_keys(memory_snapshot)
    closed_handle_keys = [
        key for key in (
            _handle_key(
                op.get("validated_parameters", {}).get("target_handle")
            )
            for op in closure_operations
        )
        if key is not None
    ]
    closure_attestation_handle_keys = [
        key for key in (
            _handle_key(
                attestation.get("content", {}).get("target_handle")
            )
            for attestation in closure_attestations
        )
        if key is not None
    ]
    stop_policies = [
        record for record in event_records
        if record.get("record_type") == "policy_disposition"
        and record.get("policy_action") == "stop_complete"
    ]
    run_manifests = [
        record["payload"]
        for record in ledger_records
        if record.get("record_type") == "run_manifest"
    ]
    model_inputs = [
        {
            "cycle_id": op.get("cycle_id"),
            "wake_id": op.get("wake_id"),
            "operation_id": op.get("operation_id"),
            "model_input": deepcopy(
                (op.get("result") or {}).get("model_input")
            ),
        }
        for op in operations
        if op.get("operation_type") == "present_wake_to_model"
    ]
    model_emissions = [
        {
            "cycle_id": trace.get("parsed_action", {}).get(
                "cycle_id"
            ) or _trace_cycle_id(ledger_records, trace),
            "raw_output": deepcopy(trace.get("raw_output")),
            "parsed_action": deepcopy(trace.get("parsed_action")),
            "parse_status": trace.get("parse_status"),
            "validation_status": trace.get("validation_status"),
        }
        for trace in action_traces
    ]
    action_attempts = [
        {
            "cycle_id": _trace_cycle_id(ledger_records, trace),
            "accepted_actions": deepcopy(trace.get("accepted_actions", [])),
            "rejected_actions": deepcopy(trace.get("rejected_actions", [])),
        }
        for trace in action_traces
    ]
    memory_operations = [
        _operation_report_row(op)
        for op in operations
        if op.get("actor") == "memory"
        or op.get("operation_type") in {
            "store_autonomous_action_record",
            "apply_closure",
            "memory_open_items",
        }
    ]
    scheduler_operations = [
        _operation_report_row(op)
        for op in operations
        if op.get("actor") == "scheduler"
        or op.get("operation_type") in {
            "apply_schedule_request",
            "complete_rehearsal_event",
            "present_wake_to_model",
        }
    ]
    failure_layers = sorted(
        {
            str(error.get("layer"))
            for op in operations
            for error in [op.get("error")]
            if isinstance(error, dict) and error.get("layer")
        }
    )
    failure_taxonomy_layers = [
        "model",
        "protocol",
        "harness",
        "substrate",
        "provider",
        "scorer",
        "restart_boundary",
    ]
    frontier = load.frontier.to_payload() if load.frontier is not None else None
    open_after = open_items.to_dict()
    no_open = open_items.ok and open_after.get("items") == []
    no_open_due_to_closure = bool(no_open and closure_operations and closure_attestations)
    stopped_because = (
        "idle: no open work remained"
        if no_open else "not idle: open work remains"
    )
    invariants = {
        "ledger_verified": load.ledger_verification.ok,
        "restart_frontier_clean": len(load.ignored_ledger_records) == 0,
        "open_items_empty": no_open,
        "closure_operation_applied": bool(closure_operations),
        "closure_attestation_present": bool(closure_attestations),
        "closed_handle_had_prior_open_item": bool(closed_handle_keys)
        and all(key in open_item_handle_keys for key in closed_handle_keys),
        "closure_attestation_matches_closed_handle": bool(closed_handle_keys)
        and set(closed_handle_keys).issubset(closure_attestation_handle_keys),
        "open_item_handles_unique": (
            len(open_item_handle_keys) == len(set(open_item_handle_keys))
        ),
        "stop_policy_recorded": bool(stop_policies),
        "stop_policy_consistent_with_idle": bool(stop_policies) and no_open,
        "event_reached_completed": any(
            record.get("status") == "completed"
            for record in latest_events.values()
        ),
        "no_pending_or_running_events": not any(
            record.get("status") in {"pending", "running"}
            for record in latest_events.values()
        ),
        "no_open_items_due_to_model_authored_closure": no_open_due_to_closure,
        "model_inputs_recorded": len(model_inputs) == len(action_traces),
        "model_emissions_recorded": all(
            item["raw_output"] is not None for item in model_emissions
        ),
        "accepted_rejected_actions_reconstructable": all(
            "accepted_actions" in item and "rejected_actions" in item
            for item in action_attempts
        ),
        "memory_operations_recorded": bool(memory_operations),
        "scheduler_operations_recorded": bool(scheduler_operations),
        "run_manifest_recorded": bool(run_manifests),
    }
    return {
        "schema_version": "restartable_rehearsal_report.v1",
        "run_id": run_id,
        "paths": paths.to_dict(),
        "run_manifests": _json_copy(run_manifests),
        "frontier": frontier,
        "ledger_verification": load.ledger_verification.to_dict(),
        "ignored_ledger_count": len(load.ignored_ledger_records),
        "recovered_event_count": len(load.recovered_event_records),
        "suppressed_event_count": len(load.suppressed_event_records),
        "action_trace_count": len(action_traces),
        "model_inputs": _json_copy(model_inputs),
        "model_emissions": _json_copy(model_emissions),
        "action_attempts": _json_copy(action_attempts),
        "action_responses": [
            trace.get("parsed_action", {}).get("response")
            for trace in action_traces
        ],
        "operations": [_operation_report_row(op) for op in operations],
        "memory_operations": _json_copy(memory_operations),
        "scheduler_operations": _json_copy(scheduler_operations),
        "operation_statuses": [
            {
                "operation_type": op.get("operation_type"),
                "result_status": op.get("result_status"),
            }
            for op in operations
        ],
        "event_statuses": [
            {
                "event_id": record.get("event_id"),
                "record_type": record.get("record_type"),
                "status": record.get("status"),
                "policy_action": record.get("policy_action"),
            }
            for record in event_records
        ],
        "open_items_after": open_after,
        "closure_attestations": _json_copy(closure_attestations),
        "policy_dispositions": _json_copy(stop_policies),
        "failure_layers_observed": failure_layers,
        "failure_taxonomy_layers": failure_taxonomy_layers,
        "no_open_items_due_to_model_authored_closure": no_open_due_to_closure,
        "stopped_because": stopped_because,
        "invariants": invariants,
        "invariant_failures": [
            name for name, ok in invariants.items() if not ok
        ],
    }


def reconstruct_sustained_event_loop_report(
    paths: RehearsalPaths,
    *,
    run_id: str = RUN_ID,
) -> JsonDict:
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths.ledger_path)
    event_store = EventStore(paths.event_path)
    frontier_store = RestartFrontierStore(
        frontier_path=paths.frontier_path,
        memory_snapshot_path=paths.memory_snapshot_path,
    )
    load = frontier_store.load_latest(
        run_id=run_id,
        memory=memory,
        ledger=ledger,
        event_store=event_store,
    )
    open_items = memory.open_items(reason="sustained report final open check")
    ledger_records = ledger.read_records()
    operations = [
        record["payload"]
        for record in ledger_records
        if record.get("record_type") == "operation"
    ]
    run_manifests = [
        record["payload"]
        for record in ledger_records
        if record.get("record_type") == "run_manifest"
    ]
    event_records = event_store.read_records()
    recovered_event_records = [
        record for record in event_records
        if record.get("recovered_by") == "restart_frontier"
    ]
    latest_events = _latest_event_records(event_records)
    histories: dict[str, list[JsonDict]] = {}
    for record in event_records:
        event_id = record.get("event_id")
        if event_id is not None:
            histories.setdefault(str(event_id), []).append(record)
    lifecycle_by_event = {
        event_id: [record.get("status") for record in history]
        for event_id, history in histories.items()
    }
    completed_events = [
        record for record in event_records if record.get("status") == "completed"
    ]
    pending_events = [
        record for record in event_records if record.get("status") == "pending"
    ]
    inbound_completed = next(
        (
            record for record in completed_events
            if record.get("event_type") == EVENT_TYPE_INBOUND_MESSAGE
        ),
        None,
    )
    continuation_pending = next(
        (
            record for record in pending_events
            if record.get("label") == "self-scheduled-continuation"
        ),
        None,
    )
    housekeeping_records = [
        record for record in memory.snapshot().get("records", [])
        if record.get("record_type") == "housekeeping_audit"
    ]
    housekeeping_record = housekeeping_records[-1] if housekeeping_records else None
    open_after = open_items.to_dict()
    no_open = open_items.ok and open_after.get("items") == []
    completed_event_types = [
        record.get("event_type", EVENT_TYPE_REFLECTION)
        for record in completed_events
    ]
    latest_statuses = {
        event_id: latest.get("status")
        for event_id, latest in latest_events.items()
    }
    recovered_housekeeping = any(
        record.get("event_type") == EVENT_TYPE_HOUSEKEEPING
        for record in recovered_event_records
    )
    continuation_bound = (
        inbound_completed is not None
        and continuation_pending is not None
        and continuation_pending.get("scheduled_by_record_id")
        == inbound_completed.get("result_record_id")
    )
    invariants = {
        "ledger_verified": load.ledger_verification.ok,
        "restart_frontier_clean": len(load.ignored_ledger_records) == 0,
        "frontier_reached_sustained_target": (
            load.frontier is not None
            and load.frontier.cycle_id == SUSTAINED_REHEARSAL_TARGET_CYCLE
        ),
        "inbound_message_completed": (
            EVENT_TYPE_INBOUND_MESSAGE in completed_event_types
        ),
        "self_scheduled_continuation_completed": (
            EVENT_TYPE_REFLECTION in completed_event_types
        ),
        "housekeeping_completed": (
            EVENT_TYPE_HOUSEKEEPING in completed_event_types
        ),
        "continuation_bound_to_inbound_result": continuation_bound,
        "housekeeping_audit_recorded": housekeeping_record is not None,
        "open_items_empty": no_open,
        "no_pending_or_running_events": not any(
            status in {"pending", "running"}
            for status in latest_statuses.values()
        ),
        "all_events_have_lifecycle": all(
            statuses[:2] == ["pending", "running"]
            and statuses[-1] == "completed"
            for statuses in lifecycle_by_event.values()
        ),
        "completed_events_have_result_record": all(
            bool(record.get("result_record_id")) for record in completed_events
        ),
        "mixed_event_types_completed": {
            EVENT_TYPE_INBOUND_MESSAGE,
            EVENT_TYPE_REFLECTION,
            EVENT_TYPE_HOUSEKEEPING,
        }.issubset(set(completed_event_types)),
    }
    if recovered_event_records:
        invariants["restart_recovered_running_housekeeping"] = recovered_housekeeping
    stopped_because = (
        "idle: no open work remained"
        if no_open and invariants["no_pending_or_running_events"] else
        "not idle: open work or runnable events remain"
    )
    return {
        "schema_version": "sustained_event_loop_rehearsal_report.v1",
        "run_id": run_id,
        "target_cycle": SUSTAINED_REHEARSAL_TARGET_CYCLE,
        "paths": paths.to_dict(),
        "run_manifests": _json_copy(run_manifests),
        "frontier": (
            load.frontier.to_payload() if load.frontier is not None else None
        ),
        "ledger_verification": load.ledger_verification.to_dict(),
        "ignored_ledger_count": len(load.ignored_ledger_records),
        "recovered_event_count": len(recovered_event_records),
        "current_load_recovered_event_count": len(load.recovered_event_records),
        "suppressed_event_count": len(load.suppressed_event_records),
        "operations": [_operation_report_row(op) for op in operations],
        "event_lifecycle_by_event": lifecycle_by_event,
        "latest_event_statuses": latest_statuses,
        "completed_event_types": completed_event_types,
        "completed_event_count": len(completed_events),
        "housekeeping_audit_count": len(housekeeping_records),
        "open_items_after": open_after,
        "housekeeping_audit": (
            deepcopy(housekeeping_record.get("content"))
            if housekeeping_record is not None else None
        ),
        "stopped_because": stopped_because,
        "invariants": invariants,
        "invariant_failures": [
            name for name, ok in invariants.items() if not ok
        ],
    }


def _operation_report_row(operation: JsonDict) -> JsonDict:
    return {
        "cycle_id": operation.get("cycle_id"),
        "wake_id": operation.get("wake_id"),
        "operation_id": operation.get("operation_id"),
        "operation_type": operation.get("operation_type"),
        "actor": operation.get("actor"),
        "raw_parameters": deepcopy(operation.get("raw_parameters")),
        "validated_parameters": deepcopy(operation.get("validated_parameters")),
        "reason": deepcopy(operation.get("reason")),
        "precondition_checks": deepcopy(operation.get("precondition_checks")),
        "result_status": operation.get("result_status"),
        "result": deepcopy(operation.get("result")),
        "error": deepcopy(operation.get("error")),
        "created_records": deepcopy(operation.get("created_records")),
        "result_hash": operation.get("result_hash"),
        "truncation": deepcopy(operation.get("truncation")),
        "omission": deepcopy(operation.get("omission")),
    }


def _trace_cycle_id(ledger_records: list[JsonDict], trace: JsonDict) -> str | None:
    for record in ledger_records:
        if record.get("record_type") != "action_trace":
            continue
        payload = record.get("payload", {})
        if payload.get("trace") == trace:
            return payload.get("cycle_id")
    return None


def _latest_event_records(event_records: list[JsonDict]) -> dict[str, JsonDict]:
    latest: dict[str, JsonDict] = {}
    for record in event_records:
        event_id = record.get("event_id")
        if event_id is not None:
            latest[str(event_id)] = record
    return latest


def _open_item_handle_keys(memory_snapshot: JsonDict) -> list[str]:
    handles: list[str] = []
    for record in memory_snapshot.get("records", []):
        content = record.get("content", {})
        if not isinstance(content, dict):
            continue
        for source in OPEN_CONTENT_FIELDS:
            value = content.get(source)
            if not value:
                continue
            entries = value if isinstance(value, list) else [value]
            for index, _entry in enumerate(entries):
                handle_key = _handle_key(
                    {
                        "record_id": record.get("record_id"),
                        "source": source,
                        "index": index,
                    }
                )
                if handle_key is not None:
                    handles.append(handle_key)
    return handles


def _handle_key(handle: Any) -> str | None:
    if not isinstance(handle, dict):
        return None
    try:
        record_id = str(handle["record_id"])
        source = str(handle["source"])
        index = int(handle["index"])
    except (KeyError, TypeError, ValueError):
        return None
    if source not in OPEN_CONTENT_FIELDS:
        return None
    return f"{record_id}:{source}:{index}"


def run_fake_autonomy_rehearsal(
    *,
    output_dir: str | Path | None = None,
    interrupt_after: str | None = None,
) -> RehearsalResult:
    root = Path(output_dir) if output_dir is not None else Path(
        tempfile.mkdtemp(prefix="hamutay-rehearsal-")
    )
    paths = RehearsalPaths.from_root(root)
    return RestartableAutonomyRehearsal(paths=paths).run(
        interrupt_after=interrupt_after
    )


def main() -> None:
    result = run_fake_autonomy_rehearsal()
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
