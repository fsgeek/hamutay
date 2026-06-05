"""Reusable scheduler policy helpers for event-loop experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from hamutay.events import EventStore, build_pending_event, run_next_event

TERMINAL_EVENT_STATUSES = {"completed", "failed", "suppressed", "expired"}


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


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
