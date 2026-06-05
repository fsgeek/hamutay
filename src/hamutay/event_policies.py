"""Reusable scheduler policy helpers for event-loop experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from hamutay.events import build_pending_event

TERMINAL_EVENT_STATUSES = {"completed", "failed", "suppressed", "expired"}


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


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
