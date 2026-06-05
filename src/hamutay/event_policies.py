"""Reusable scheduler policy helpers for event-loop experiments."""

from __future__ import annotations

import json
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from hamutay.events import EventStore, build_pending_event, run_next_event

TERMINAL_EVENT_STATUSES = {"completed", "failed", "suppressed", "expired"}


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def default_fork_run_log_path(event_log_path: str | Path) -> Path:
    """Return the sidecar path for durable fork-run records."""
    path = Path(event_log_path)
    return path.with_suffix(path.suffix + ".fork_runs.jsonl")


def latest_event_records_by_label(
    event_records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return latest sidecar record keyed by original pending label."""
    label_by_event_id = {
        record["event_id"]: record.get("label")
        for record in event_records
        if record.get("status") == "pending" and record.get("label")
    }
    latest: dict[str, dict[str, Any]] = {}
    for record in event_records:
        event_id = record.get("event_id")
        label = label_by_event_id.get(event_id)
        if label:
            latest[str(label)] = record
    return latest


@dataclass(frozen=True)
class EventRunResult:
    """Structured telemetry for one scheduler-run event."""

    label: str
    status: str
    terminal_record: dict[str, Any] | None = None
    error: str | None = None

    @property
    def result_record_id(self) -> str | None:
        if not self.terminal_record:
            return None
        value = self.terminal_record.get("result_record_id")
        return str(value) if value else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "status": self.status,
            "error": self.error,
            "result_record_id": self.result_record_id,
            "terminal_record": self.terminal_record,
        }


@dataclass
class ForkRunStore:
    """Append-only JSONL store for durable fork/join run records."""

    path: Path

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    @contextmanager
    def _locked(self):
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def append(self, record: dict[str, Any]) -> None:
        with self._locked():
            with self.path.open("a") as f:
                f.write(json.dumps(record, default=str) + "\n")

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._locked():
            with self.path.open() as f:
                return [json.loads(line) for line in f if line.strip()]

    def latest_by_run_id(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for record in self.read_records():
            run_id = record.get("fork_run_id")
            if run_id:
                latest[str(run_id)] = record
        return latest


def build_fork_run_started_record(
    *,
    fork_record: dict[str, Any],
    branch_labels: list[str] | tuple[str, ...],
    fork_run_id: str | UUID | None = None,
) -> dict[str, Any]:
    run_id = str(fork_run_id or uuid4())
    return {
        "record_type": "fork_run",
        "fork_run_id": run_id,
        "status": "started",
        "scheduled_by_cycle": int(fork_record["cycle"]),
        "scheduled_by_record_id": str(fork_record["record_id"]),
        "branch_labels": list(branch_labels),
    }


def finalize_successful_fork_run(
    *,
    started_record: dict[str, Any],
    branch_results: list[EventRunResult],
    join_event: dict[str, Any],
    join_result: EventRunResult,
    sidecar_audit_projection: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        **started_record,
        "status": "joined",
        "classification": "joined",
        "branch_results": [result.to_dict() for result in branch_results],
        "branch_events": {
            label: {
                "event_id": projection.get("event_id"),
                "terminal_status": projection.get("terminal_status"),
                "result_record_id": next(
                    (
                        result.result_record_id
                        for result in branch_results
                        if result.label == label
                    ),
                    None,
                ),
            }
            for label, projection in sidecar_audit_projection.items()
        },
        "join_event_id": join_event.get("event_id"),
        "join_result": join_result.to_dict(),
        "join_result_record_id": join_result.result_record_id,
    }


def finalize_failed_fork_run(
    *,
    started_record: dict[str, Any],
    failed_branch_result: EventRunResult,
    failed_wake_record: dict[str, Any],
    suppression_records: list[dict[str, Any]],
    sidecar_audit_projection: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        **started_record,
        "status": "branch_failed",
        "classification": "branch_failed",
        "failed_branch": failed_branch_result.label,
        "failed_branch_result": failed_branch_result.to_dict(),
        "failed_branch_wake_record_id": str(failed_wake_record["record_id"]),
        "failed_branch_wake_cycle": int(failed_wake_record["cycle"]),
        "suppression_records": suppression_records,
        "suppressed_events": [
            record.get("event_id")
            for record in suppression_records
            if record.get("event_id")
        ],
        "branch_events": {
            label: {
                "event_id": projection.get("event_id"),
                "terminal_status": projection.get("terminal_status"),
                "result_record_id": (
                    failed_branch_result.result_record_id
                    if label == failed_branch_result.label
                    else None
                ),
            }
            for label, projection in sidecar_audit_projection.items()
        },
    }


def build_fork_run_graph_plan(
    final_run_record: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic graph-write operations for a fork-run record."""
    content = {
        "record_type": "fork_run",
        "fork_run_id": final_run_record["fork_run_id"],
        "classification": final_run_record.get("classification"),
        "scheduled_by_cycle": final_run_record.get("scheduled_by_cycle"),
        "scheduled_by_record_id": final_run_record.get(
            "scheduled_by_record_id"
        ),
        "branch_labels": final_run_record.get("branch_labels", []),
        "branch_events": final_run_record.get("branch_events", {}),
    }
    if final_run_record.get("join_event_id"):
        content["join_event_id"] = final_run_record["join_event_id"]
    if final_run_record.get("join_result_record_id"):
        content["join_result_record_id"] = final_run_record[
            "join_result_record_id"
        ]
    if final_run_record.get("failed_branch"):
        content["failed_branch"] = final_run_record["failed_branch"]
    if final_run_record.get("suppressed_events"):
        content["suppressed_events"] = final_run_record["suppressed_events"]

    edges: list[dict[str, Any]] = []
    root_id = final_run_record.get("scheduled_by_record_id")
    if root_id:
        edges.append({
            "role": "coordinator_root",
            "target_record_id": str(root_id),
            "relation": "DEPENDS_ON",
        })

    branch_events = final_run_record.get("branch_events", {})
    for label in sorted(branch_events):
        branch = branch_events[label]
        target = branch.get("result_record_id")
        if not target and label == final_run_record.get("failed_branch"):
            target = final_run_record.get("failed_branch_wake_record_id")
        if target:
            edges.append({
                "role": f"branch:{label}",
                "target_record_id": str(target),
                "relation": "BRANCHES_FROM",
            })

    join_target = final_run_record.get("join_result_record_id")
    if join_target:
        edges.append({
            "role": "join_result",
            "target_record_id": str(join_target),
            "relation": "COMPOSES_WITH",
        })

    suppression_records = final_run_record.get("suppression_records", [])
    suppression_content = []
    for i, record in enumerate(suppression_records):
        suppression_content.append({
            "role": f"suppression:{i}",
            "content": {
                "record_type": "fork_run_suppression",
                "fork_run_id": final_run_record["fork_run_id"],
                "suppressed_event_id": record.get("event_id"),
                "suppressed_by_record_id": record.get(
                    "suppressed_by_record_id"
                ),
                "suppressed_by_cycle": record.get("suppressed_by_cycle"),
                "suppressed_by_policy": record.get("suppressed_by_policy"),
                "suppression_reason": record.get("suppression_reason"),
            },
            "relation": "BRIDGES",
        })

    return {
        "fork_run_id": final_run_record["fork_run_id"],
        "fork_run_content": content,
        "fork_run_tags": ("fork_run", final_run_record["fork_run_id"]),
        "edges": edges,
        "suppression_records": suppression_content,
    }


def apply_fork_run_graph_plan(
    *,
    bridge: Any,
    plan: dict[str, Any],
    cycle: int,
) -> dict[str, Any]:
    """Apply a fork-run graph plan to an ApachetaBridge-like object."""
    fork_run_record_id = bridge.store_instance_record(
        plan["fork_run_content"],
        cycle=cycle,
        tags=tuple(plan.get("fork_run_tags", ())),
    )
    edges = []
    edge_source_id = fork_run_record_id
    for edge in plan.get("edges", []):
        target_id = UUID(str(edge["target_record_id"]))
        edge_id = bridge.store_edge(
            edge_source_id,
            target_id,
            edge["relation"],
            ordering=cycle,
        )
        edges.append({
            **edge,
            "from_record_id": str(edge_source_id),
            "edge_id": str(edge_id),
        })
        edge_source_id = target_id

    suppression_nodes = []
    for item in plan.get("suppression_records", []):
        suppression_id = bridge.store_instance_record(
            item["content"],
            cycle=cycle,
            tags=("fork_run", "suppression", plan["fork_run_id"]),
        )
        edge_id = bridge.store_edge(
            edge_source_id,
            suppression_id,
            item["relation"],
            ordering=cycle,
        )
        suppression_nodes.append({
            "role": item["role"],
            "record_id": str(suppression_id),
            "from_record_id": str(edge_source_id),
            "edge_id": str(edge_id),
            "content": item["content"],
        })
        edge_source_id = suppression_id

    return {
        "fork_run_id": plan["fork_run_id"],
        "fork_run_record_id": str(fork_run_record_id),
        "edges": edges,
        "suppression_nodes": suppression_nodes,
    }


@dataclass(frozen=True)
class BranchContextPolicy:
    """Policy boundary between branch-visible context and sidecar audit state."""

    hidden_state_keys: tuple[str, ...] = ("_activity_log",)

    def sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self.sanitize_value(item)
                for key, item in value.items()
                if key not in self.hidden_state_keys
            }
        if isinstance(value, list):
            return [self.sanitize_value(item) for item in value]
        return value

    def branch_visible_records(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return minimal seed records with private framework state stripped."""
        visible_records: list[dict[str, Any]] = []
        for source in _json_clone(records):
            state = source.get("state")
            if state is None:
                continue
            record = {
                key: source[key]
                for key in ("cycle", "record_id", "timestamp")
                if key in source
            }
            record["state"] = self.sanitize_value(state)
            visible_records.append(record)
        return visible_records

    def branch_visible_context_results(
        self,
        context_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return event context results safe to expose to a branch wake."""
        return self.sanitize_value(_json_clone(context_results))

    def seed_branch_session(
        self,
        session: Any,
        records: list[dict[str, Any]],
        *,
        up_to_cycle: int,
    ) -> None:
        """Seed a session through the branch-visible policy boundary."""
        session.seed_history(
            self.branch_visible_records(records),
            up_to_cycle=up_to_cycle,
        )

    def sidecar_audit_projection(
        self,
        event_records: list[dict[str, Any]],
        *,
        labels: list[str] | tuple[str, ...],
    ) -> dict[str, dict[str, Any]]:
        """Project append-only sidecar records into per-label audit entries."""
        pending_by_label = {
            record.get("label"): record
            for record in event_records
            if record.get("status") == "pending" and record.get("label")
        }
        latest_by_event_id: dict[str, dict[str, Any]] = {}
        for record in event_records:
            event_id = record.get("event_id")
            if event_id:
                latest_by_event_id[str(event_id)] = record

        projection: dict[str, dict[str, Any]] = {}
        for label in labels:
            pending = pending_by_label.get(label)
            if pending is None:
                projection[label] = {"audit_complete": False}
                continue
            latest = latest_by_event_id.get(str(pending["event_id"]), pending)
            projection[label] = {
                "audit_complete": (
                    bool(pending.get("purpose"))
                    and latest.get("status") in TERMINAL_EVENT_STATUSES
                ),
                "event_id": pending["event_id"],
                "label": label,
                "purpose": pending.get("purpose"),
                "requested_context": pending.get("requested_context", []),
                "scheduled_by_cycle": pending.get("scheduled_by_cycle"),
                "scheduled_by_record_id": pending.get("scheduled_by_record_id"),
                "terminal_status": latest.get("status"),
                "terminal_record": latest,
            }
        return projection

    def sidecar_audit_complete(
        self,
        event_records: list[dict[str, Any]],
        *,
        labels: list[str] | tuple[str, ...],
    ) -> bool:
        projection = self.sidecar_audit_projection(event_records, labels=labels)
        return all(
            projection.get(label, {}).get("audit_complete") is True
            for label in labels
        )

    def build_join_event(
        self,
        *,
        fork_record: dict[str, Any],
        branch_outputs: list[dict[str, Any]],
        label: str = "fork-join",
        requested_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build an explicit join event from selected branch outputs."""
        purpose = (
            "Join completed fork branches. Branch outputs are explicit policy "
            "context, not recalled memory:\n"
            + json.dumps(branch_outputs, indent=2, default=str)
        )
        return build_pending_event(
            purpose=purpose,
            requested_context=requested_context or [
                {"tool": "recall", "cycle": int(fork_record["cycle"])}
            ],
            scheduled_by_cycle=int(fork_record["cycle"]),
            scheduled_by_record_id=UUID(str(fork_record["record_id"])),
            label=label,
        )


@dataclass
class ForkJoinPolicyRunner:
    """Reusable runner for explicit fork/join event orchestration."""

    policy: BranchContextPolicy = field(default_factory=BranchContextPolicy)
    now: datetime | None = None
    branch_up_to_cycle: int = 3
    join_up_to_cycle: int = 3
    policy_name: str = "fork_join_policy_runner"

    def run_branch(
        self,
        *,
        label: str,
        session: Any,
        store: EventStore,
        seed_records: list[dict[str, Any]],
    ) -> EventRunResult:
        self.policy.seed_branch_session(
            session,
            seed_records,
            up_to_cycle=self.branch_up_to_cycle,
        )
        error = None
        try:
            terminal = run_next_event(session, store, now=self.now)
        except Exception as exc:  # noqa: BLE001 -- telemetry captures failures
            error = f"{type(exc).__name__}: {exc}"
            terminal = latest_event_records_by_label(
                store.read_records()
            ).get(label)
        status = str((terminal or {}).get("status", "unknown"))
        return EventRunResult(
            label=label,
            status=status,
            terminal_record=terminal,
            error=error,
        )

    def schedule_join(
        self,
        *,
        store: EventStore,
        fork_record: dict[str, Any],
        branch_outputs: list[dict[str, Any]],
        label: str = "fork-join",
        requested_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        event = self.policy.build_join_event(
            fork_record=fork_record,
            branch_outputs=branch_outputs,
            label=label,
            requested_context=requested_context,
        )
        store.append(event)
        return event

    def run_join(
        self,
        *,
        session: Any,
        store: EventStore,
        seed_records: list[dict[str, Any]],
        label: str = "fork-join",
    ) -> EventRunResult:
        session.seed_history(seed_records, up_to_cycle=self.join_up_to_cycle)
        error = None
        try:
            terminal = run_next_event(session, store, now=self.now)
        except Exception as exc:  # noqa: BLE001 -- telemetry captures failures
            error = f"{type(exc).__name__}: {exc}"
            terminal = latest_event_records_by_label(
                store.read_records()
            ).get(label)
        status = str((terminal or {}).get("status", "unknown"))
        return EventRunResult(
            label=label,
            status=status,
            terminal_record=terminal,
            error=error,
        )

    def suppress_pending_after_failure(
        self,
        *,
        store: EventStore,
        failed_wake_record: dict[str, Any],
        classification: str = "branch_failed",
        reason: str = "branch failure",
    ) -> list[dict[str, Any]]:
        return store.suppress_pending(
            policy=self.policy_name,
            reason=reason,
            suppressed_by_record_id=failed_wake_record["record_id"],
            suppressed_by_cycle=int(failed_wake_record["cycle"]),
            suppressed_by_classification=classification,
        )
