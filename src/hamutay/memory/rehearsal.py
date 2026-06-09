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

from hamutay.events import EventStore
from hamutay.memory.action_application import AutonomousActionApplier
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.bridge import JsonDict, LocalMemorySubstrate
from hamutay.memory.restart_frontier import RestartFrontierStore


WAKE_RUN_ID = UUID("60000000-0000-0000-0000-000000000001")
RUN_ID = str(WAKE_RUN_ID)
REHEARSAL_TIME = "2026-06-08T12:00:00+00:00"


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
        result = applier.apply_trace(
            parse_autonomous_action(self.cognition.seed_action()).to_dict(),
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
        if not open_items.ok:
            raise RuntimeError("open_items failed during rehearsal closure")
        items = open_items.data.get("items", [])
        if len(items) != 1:
            raise RuntimeError(f"expected exactly one open item, got {len(items)}")
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
    frontier = load.frontier.to_payload() if load.frontier is not None else None
    open_after = open_items.to_dict()
    no_open = open_items.ok and open_after.get("items") == []
    no_open_due_to_closure = bool(no_open and closure_operations and closure_attestations)
    stopped_because = (
        "idle: no open work remained"
        if no_open else "not idle: open work remains"
    )
    return {
        "schema_version": "restartable_rehearsal_report.v1",
        "run_id": run_id,
        "paths": paths.to_dict(),
        "frontier": frontier,
        "ledger_verification": load.ledger_verification.to_dict(),
        "ignored_ledger_count": len(load.ignored_ledger_records),
        "recovered_event_count": len(load.recovered_event_records),
        "suppressed_event_count": len(load.suppressed_event_records),
        "action_trace_count": len(action_traces),
        "action_responses": [
            trace.get("parsed_action", {}).get("response")
            for trace in action_traces
        ],
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
        "no_open_items_due_to_model_authored_closure": no_open_due_to_closure,
        "stopped_because": stopped_because,
    }


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
