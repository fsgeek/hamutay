"""Append-only event log for taste_open scheduled wakeups."""

from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

EVENT_TYPE_REFLECTION = "self_scheduled_reflection"
VALID_CONTEXT_TOOLS = {"recall", "compare"}
LOAD_BEARING_FIELDS = {
    "current_claim",
    "revision_decision",
    "evidence_register",
    "state_use_norm",
}
STATE_DELTA_IGNORED_KEYS = {"cycle"}
EPISTEMIC_DECISION_WORDS = {
    "revise",
    "revised",
    "revision",
    "narrow",
    "narrowed",
    "preserve",
    "preserved",
    "defer",
    "deferred",
    "loss",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_event_log_path(session_log_path: str | Path) -> Path:
    """Return the sidecar event log path for a session JSONL."""
    path = Path(session_log_path)
    return path.with_suffix(path.suffix + ".events.jsonl")


def validate_requested_context(requests: object) -> list[dict]:
    """Validate v1 requested_context entries and return JSON-safe copies."""
    if not isinstance(requests, list) or not requests:
        raise ValueError("requested_context must be a non-empty list")

    validated: list[dict] = []
    for i, request in enumerate(requests):
        if not isinstance(request, dict):
            raise ValueError(f"requested_context[{i}] must be an object")
        tool = request.get("tool")
        if tool not in VALID_CONTEXT_TOOLS:
            raise ValueError(
                f"requested_context[{i}].tool must be one of: "
                f"{', '.join(sorted(VALID_CONTEXT_TOOLS))}"
            )
        if tool == "recall":
            has_cycle = "cycle" in request
            has_record = "record_id" in request
            if has_cycle == has_record:
                raise ValueError(
                    "recall context requires exactly one of cycle or record_id"
                )
            allowed = {"tool", "cycle", "record_id", "field"}
        else:
            if "cycle_a" not in request or "cycle_b" not in request:
                raise ValueError("compare context requires cycle_a and cycle_b")
            allowed = {"tool", "cycle_a", "cycle_b", "field", "content"}
        extra = set(request) - allowed
        if extra:
            raise ValueError(
                f"requested_context[{i}] has unsupported keys: {sorted(extra)}"
            )
        validated.append({k: v for k, v in request.items() if k in allowed})

    return json.loads(json.dumps(validated, default=str))


def build_pending_event(
    *,
    purpose: str,
    requested_context: list[dict],
    scheduled_by_cycle: int,
    scheduled_by_record_id: UUID,
    label: str | None = None,
    not_before: str | None = None,
    expires_at: str | None = None,
) -> dict:
    """Create a pending event record. Does not write it."""
    purpose = str(purpose).strip()
    if not purpose:
        raise ValueError("purpose is required")
    context = validate_requested_context(requested_context)
    event_id = uuid4()
    record = {
        "record_type": "event_status",
        "event_id": str(event_id),
        "event_type": EVENT_TYPE_REFLECTION,
        "status": "pending",
        "created_at": utc_now_iso(),
        "scheduled_by_cycle": scheduled_by_cycle,
        "scheduled_by_record_id": str(scheduled_by_record_id),
        "purpose": purpose,
        "requested_context": context,
    }
    if label:
        record["label"] = str(label)
    if not_before:
        # Validate parseability but preserve original ISO spelling.
        datetime.fromisoformat(str(not_before).replace("Z", "+00:00"))
        record["not_before"] = str(not_before)
    if expires_at:
        # Validate parseability but preserve original ISO spelling.
        datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        record["expires_at"] = str(expires_at)
    return record


@dataclass
class EventStore:
    """Append-only JSONL event store."""

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

    def _append_unlocked(self, record: dict) -> None:
        with self.path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _read_records_unlocked(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open() as f:
            return [json.loads(line) for line in f if line.strip()]

    @staticmethod
    def _latest_by_event_id_from_records(records: list[dict]) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for record in records:
            event_id = record.get("event_id")
            if event_id:
                latest[str(event_id)] = record
        return latest

    def append(self, record: dict) -> None:
        with self._locked():
            self._append_unlocked(record)

    def append_many(self, records: list[dict]) -> None:
        if not records:
            return
        with self._locked():
            for record in records:
                self._append_unlocked(record)

    def read_records(self) -> list[dict]:
        with self._locked():
            return self._read_records_unlocked()

    def latest_by_event_id(self) -> dict[str, dict]:
        return self._latest_by_event_id_from_records(self.read_records())

    def next_pending(self, *, now: datetime | None = None) -> dict | None:
        """Return the oldest claimable pending event by created_at, if any."""
        pending = [
            r for r in self.latest_by_event_id().values()
            if r.get("status") == "pending"
        ]
        if not pending:
            return None
        pending.sort(key=lambda r: r.get("created_at", ""))
        for event in pending:
            if is_expired(event, now=now) or is_due(event, now=now):
                return event
        return None

    def append_running(self, event: dict, run_id: UUID | None = None) -> dict:
        record = self._build_running(event, run_id=run_id)
        self.append(record)
        return record

    def _build_running(self, event: dict, run_id: UUID | None = None) -> dict:
        return {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "running",
            "run_id": str(run_id or uuid4()),
            "started_at": utc_now_iso(),
        }

    def claim_next_pending(
        self,
        *,
        now: datetime | None = None,
        run_id: UUID | None = None,
    ) -> tuple[dict, dict] | None:
        """Atomically mark the oldest runnable pending event as running."""
        with self._locked():
            latest = self._latest_by_event_id_from_records(
                self._read_records_unlocked()
            )
            pending = [
                r for r in latest.values()
                if r.get("status") == "pending"
            ]
            pending.sort(key=lambda r: r.get("created_at", ""))
            for event in pending:
                if is_expired(event, now=now):
                    expired = {
                        "record_type": "event_status",
                        "event_id": event["event_id"],
                        "event_type": event.get(
                            "event_type", EVENT_TYPE_REFLECTION
                        ),
                        "status": "expired",
                        "expired_at": utc_now_iso(),
                    }
                    self._append_unlocked(expired)
                    return event, expired
                if not is_due(event, now=now):
                    continue
                running = self._build_running(event, run_id=run_id)
                self._append_unlocked(running)
                return event, running
        return None

    def append_completed(
        self,
        *,
        event: dict,
        run_id: str,
        wake_cycle: int,
        result_record_id: UUID,
        response_text: str,
        context_results: list[dict] | None = None,
        outcome_observation: dict | None = None,
    ) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "completed",
            "run_id": run_id,
            "completed_at": utc_now_iso(),
            "wake_cycle": wake_cycle,
            "result_record_id": str(result_record_id),
            "response_text": response_text,
        }
        if context_results is not None:
            record["context_results"] = context_results
        if outcome_observation is not None:
            record["outcome_observation"] = outcome_observation
        self.append(record)
        return record

    def append_failed(
        self,
        *,
        event: dict,
        run_id: str,
        exc: Exception,
        context_results: list[dict] | None = None,
    ) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "failed",
            "run_id": run_id,
            "failed_at": utc_now_iso(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        if context_results is not None:
            record["context_results"] = context_results
        self.append(record)
        return record

    def append_expired(self, event: dict) -> dict:
        record = {
            "record_type": "event_status",
            "event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "status": "expired",
            "expired_at": utc_now_iso(),
        }
        self.append(record)
        return record


def is_expired(event: dict, *, now: datetime | None = None) -> bool:
    expires_at = event.get("expires_at")
    if not expires_at:
        return False
    deadline = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) >= deadline


def is_due(event: dict, *, now: datetime | None = None) -> bool:
    not_before = event.get("not_before")
    if not not_before:
        return True
    threshold = datetime.fromisoformat(str(not_before).replace("Z", "+00:00"))
    if threshold.tzinfo is None:
        threshold = threshold.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) >= threshold


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def resolve_requested_context(
    requests: list[dict],
    *,
    prior_states: list[tuple[int, UUID, dict, str]],
    bridge=None,
) -> list[dict]:
    """Resolve a v1 requested_context list using existing memory tools."""
    from hamutay.tools.memory import tool_compare, tool_recall

    context = validate_requested_context(requests)
    results: list[dict] = []
    for request in context:
        params = {k: v for k, v in request.items() if k != "tool"}
        if request["tool"] == "recall":
            result = tool_recall(params, prior_states=prior_states, bridge=bridge)
        elif request["tool"] == "compare":
            result = tool_compare(params, prior_states=prior_states)
        else:
            result = {"error": f"Unsupported context tool: {request['tool']}"}
        results.append({"request": request, "result": result})
    return results


def build_event_envelope(event: dict, context_results: list[dict], run_id: str) -> str:
    """Build the explicit user-message envelope for a wake cycle."""
    envelope = {
        "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
        "event_id": event["event_id"],
        "run_id": run_id,
        "scheduled_by_cycle": event.get("scheduled_by_cycle"),
        "scheduled_by_record_id": event.get("scheduled_by_record_id"),
        "purpose": event.get("purpose", ""),
        "requested_context": event.get("requested_context", []),
        "context_results": context_results,
        "instruction": (
            "This is a self-scheduled reflection event. Use the provided "
            "context to decide whether to revise, preserve, defer, or "
            "declare losses. End the cycle with think_and_respond."
        ),
    }
    return json.dumps(envelope, indent=2, default=str)


def _json_safe_state(state: object) -> dict:
    if not isinstance(state, dict):
        return {}
    return json.loads(json.dumps(state, default=str))


def _response_mentions_epistemic_decision(response_text: str) -> bool:
    lowered = response_text.lower()
    return any(word in lowered for word in EPISTEMIC_DECISION_WORDS)


def build_outcome_observation(
    *,
    before_state: dict | None,
    after_state: dict | None,
    response_text: str,
) -> dict:
    """Capture wake outcome deltas without changing event behavior."""
    before = _json_safe_state(before_state)
    after = _json_safe_state(after_state)
    before_keys = set(before) - STATE_DELTA_IGNORED_KEYS
    after_keys = set(after) - STATE_DELTA_IGNORED_KEYS
    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)
    changed = sorted(
        key for key in before_keys & after_keys
        if before.get(key) != after.get(key)
    )
    changed_or_removed = sorted(set(changed) | set(removed))
    changed_load_bearing = sorted(
        set(changed_or_removed) & LOAD_BEARING_FIELDS
    )
    deleted_load_bearing = sorted(set(removed) & LOAD_BEARING_FIELDS)
    response_mentions_decision = _response_mentions_epistemic_decision(
        response_text
    )
    durable_state_changed = bool(added or removed or changed)
    return {
        "state_changed": durable_state_changed,
        "added_top_level_keys": added,
        "removed_top_level_keys": removed,
        "changed_top_level_keys": changed,
        "changed_or_removed_top_level_keys": changed_or_removed,
        "changed_load_bearing_fields": changed_load_bearing,
        "deleted_load_bearing_fields": deleted_load_bearing,
        "deleted_load_bearing_field": bool(deleted_load_bearing),
        "response_mentions_epistemic_decision": response_mentions_decision,
        "response_state_mismatch": (
            response_mentions_decision and not changed_load_bearing
        ),
        "no_durable_state_change": not durable_state_changed,
    }


def _shorten(value: object, *, limit: int = 160) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _context_error_count(history: list[dict]) -> int:
    count = 0
    for record in history:
        for item in record.get("context_results", []) or []:
            result = item.get("result") if isinstance(item, dict) else None
            if isinstance(result, dict) and "error" in result:
                count += 1
    return count


TERMINAL_EVENT_STATUSES = {"completed", "failed", "expired"}


def detect_lifecycle_anomalies(event_id: str, history: list[dict]) -> list[dict]:
    """Detect suspicious event-status histories without mutating the log."""
    statuses = [str(record.get("status", "unknown")) for record in history]
    anomalies: list[dict] = []

    def add(kind: str, message: str) -> None:
        anomalies.append({
            "event_id": event_id,
            "kind": kind,
            "message": message,
            "statuses": statuses,
        })

    if not statuses:
        add("empty_history", "event history has no records")
        return anomalies

    if statuses[0] != "pending":
        add(
            "missing_initial_pending",
            "event history does not start with a pending record",
        )
    if statuses.count("pending") > 1:
        add("duplicate_pending", "event history has multiple pending records")

    terminal_indexes = [
        i for i, status in enumerate(statuses)
        if status in TERMINAL_EVENT_STATUSES
    ]
    if len(terminal_indexes) > 1:
        add(
            "multiple_terminal_statuses",
            "event history has more than one terminal status",
        )
    if terminal_indexes and terminal_indexes[0] != len(statuses) - 1:
        add(
            "status_after_terminal",
            "event history has records after its first terminal status",
        )

    for index, status in enumerate(statuses):
        prior = statuses[:index]
        if status == "running" and "pending" not in prior:
            add(
                "running_without_pending",
                "running status appears before any pending record",
            )
        if status in {"completed", "failed"} and "running" not in prior:
            add(
                "terminal_without_running",
                f"{status} status appears before any running record",
            )
        if status == "completed":
            record = history[index]
            missing = [
                field for field in ("wake_cycle", "result_record_id")
                if record.get(field) is None
            ]
            if missing:
                add(
                    "completed_missing_fields",
                    "completed record is missing: " + ", ".join(missing),
                )

    return anomalies


def summarize_event_history(
    event_id: str,
    history: list[dict],
    *,
    snippet_limit: int = 160,
) -> dict:
    """Return a compact summary for one event's append-only history."""
    first = history[0]
    latest = history[-1]
    response_text = latest.get("response_text")
    outcome = latest.get("outcome_observation")
    if not isinstance(outcome, dict):
        outcome = {}
    lifecycle_anomalies = detect_lifecycle_anomalies(event_id, history)
    summary = {
        "event_id": event_id,
        "event_type": first.get("event_type", latest.get("event_type")),
        "status": latest.get("status"),
        "record_count": len(history),
        "created_at": first.get("created_at"),
        "started_at": next(
            (r.get("started_at") for r in history if r.get("started_at")),
            None,
        ),
        "completed_at": latest.get("completed_at"),
        "failed_at": latest.get("failed_at"),
        "expired_at": latest.get("expired_at"),
        "not_before": first.get("not_before"),
        "expires_at": first.get("expires_at"),
        "scheduled_by_cycle": first.get("scheduled_by_cycle"),
        "scheduled_by_record_id": first.get("scheduled_by_record_id"),
        "wake_cycle": latest.get("wake_cycle"),
        "result_record_id": latest.get("result_record_id"),
        "run_id": latest.get("run_id"),
        "label": first.get("label"),
        "purpose": first.get("purpose", ""),
        "requested_context_count": len(first.get("requested_context", []) or []),
        "context_error_count": _context_error_count(history),
        "outcome_warning_count": sum(
            1
            for key in (
                "response_state_mismatch",
                "deleted_load_bearing_field",
                "no_durable_state_change",
            )
            if outcome.get(key)
        ),
        "state_changed": outcome.get("state_changed"),
        "response_state_mismatch": outcome.get("response_state_mismatch"),
        "deleted_load_bearing_field": outcome.get("deleted_load_bearing_field"),
        "no_durable_state_change": outcome.get("no_durable_state_change"),
        "changed_load_bearing_fields": outcome.get("changed_load_bearing_fields"),
        "deleted_load_bearing_fields": outcome.get("deleted_load_bearing_fields"),
        "lifecycle_anomaly_count": len(lifecycle_anomalies),
        "lifecycle_anomalies": lifecycle_anomalies,
        "error_type": latest.get("error_type"),
        "error": latest.get("error"),
        "response_snippet": (
            _shorten(response_text, limit=snippet_limit)
            if response_text is not None else None
        ),
    }
    return {k: v for k, v in summary.items() if v is not None}


def summarize_event_log(
    records: list[dict],
    *,
    limit: int = 10,
    snippet_limit: int = 160,
    stale_after_seconds: int = 3600,
    now: datetime | None = None,
) -> dict:
    """Summarize an append-only event log for observability."""
    histories: dict[str, list[dict]] = {}
    for record in records:
        event_id = record.get("event_id")
        if event_id:
            histories.setdefault(str(event_id), []).append(record)

    events = [
        summarize_event_history(
            event_id,
            history,
            snippet_limit=snippet_limit,
        )
        for event_id, history in histories.items()
    ]
    status_counts: dict[str, int] = {}
    for event in events:
        status = str(event.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1

    current_time = now or datetime.now(timezone.utc)
    pending = [event for event in events if event.get("status") == "pending"]
    pending.sort(key=lambda event: str(event.get("created_at", "")))
    pending_expired = [
        event for event in pending
        if is_expired(event, now=current_time)
    ]
    pending_runnable = [
        event for event in pending
        if not is_expired(event, now=current_time)
        and is_due(event, now=current_time)
    ]
    pending_waiting = [
        event for event in pending
        if not is_expired(event, now=current_time)
        and not is_due(event, now=current_time)
    ]
    failed = [event for event in events if event.get("status") == "failed"]
    failed.sort(key=lambda event: str(event.get("failed_at", "")), reverse=True)
    completed = [event for event in events if event.get("status") == "completed"]
    completed.sort(key=lambda event: str(event.get("completed_at", "")), reverse=True)
    context_errors = [
        event for event in events
        if int(event.get("context_error_count", 0)) > 0
    ]
    context_errors.sort(
        key=lambda event: str(
            event.get("completed_at")
            or event.get("failed_at")
            or event.get("created_at")
            or ""
        ),
        reverse=True,
    )
    outcome_warnings = [
        event for event in events
        if int(event.get("outcome_warning_count", 0)) > 0
    ]
    outcome_warnings.sort(
        key=lambda event: str(
            event.get("completed_at")
            or event.get("failed_at")
            or event.get("created_at")
            or ""
        ),
        reverse=True,
    )
    lifecycle_anomalies = []
    for event in events:
        lifecycle_anomalies.extend(event.get("lifecycle_anomalies", []) or [])
    stale_running = []
    for event in events:
        if event.get("status") != "running":
            continue
        started_at = _parse_iso(event.get("started_at"))
        if started_at is None:
            continue
        age_seconds = (current_time - started_at).total_seconds()
        if age_seconds >= stale_after_seconds:
            stale = dict(event)
            stale["running_age_seconds"] = int(age_seconds)
            stale_running.append(stale)
    stale_running.sort(
        key=lambda event: int(event.get("running_age_seconds", 0)),
        reverse=True,
    )

    return {
        "record_count": len(records),
        "event_count": len(events),
        "status_counts": dict(sorted(status_counts.items())),
        "pending_runnable_count": len(pending_runnable),
        "pending_waiting_count": len(pending_waiting),
        "pending_expired_count": len(pending_expired),
        "oldest_pending": pending[0] if pending else None,
        "oldest_runnable_pending": (
            pending_runnable[0] if pending_runnable else None
        ),
        "oldest_waiting_pending": (
            pending_waiting[0] if pending_waiting else None
        ),
        "oldest_expired_pending": (
            pending_expired[0] if pending_expired else None
        ),
        "stale_running": stale_running[:limit],
        "failed": failed[:limit],
        "completed": completed[:limit],
        "context_errors": context_errors[:limit],
        "outcome_warnings": outcome_warnings[:limit],
        "lifecycle_anomalies": lifecycle_anomalies[:limit],
        "events": sorted(
            events,
            key=lambda event: str(
                event.get("created_at")
                or event.get("started_at")
                or event.get("completed_at")
                or ""
            ),
        ),
    }


def format_event_report(report: dict, *, path: str | Path | None = None) -> str:
    """Render an event-log summary for humans."""
    lines: list[str] = []
    if path is not None:
        lines.append(f"Event log: {path}")
    lines.append(
        f"Records: {report['record_count']} | Events: {report['event_count']}"
    )
    status_counts = report.get("status_counts", {})
    status_text = ", ".join(
        f"{status}={count}" for status, count in status_counts.items()
    ) or "none"
    lines.append(f"Statuses: {status_text}")
    pending_counts = (
        report.get("pending_runnable_count", 0),
        report.get("pending_waiting_count", 0),
        report.get("pending_expired_count", 0),
    )
    if any(pending_counts):
        lines.append(
            "Pending: "
            f"runnable={pending_counts[0]}, "
            f"waiting={pending_counts[1]}, "
            f"expired={pending_counts[2]}"
        )

    oldest_pending = report.get("oldest_runnable_pending")
    if oldest_pending:
        not_before = (
            f" not_before={oldest_pending['not_before']}"
            if oldest_pending.get("not_before")
            else ""
        )
        lines.append("")
        lines.append("Oldest runnable pending:")
        lines.append(
            "  "
            f"{oldest_pending['event_id']} "
            f"cycle={oldest_pending.get('scheduled_by_cycle', '?')} "
            f"context={oldest_pending.get('requested_context_count', 0)} "
            f"purpose={oldest_pending.get('purpose', '')}"
            f"{not_before}"
        )

    waiting_pending = report.get("oldest_waiting_pending")
    if waiting_pending:
        lines.append("")
        lines.append("Oldest waiting pending:")
        lines.append(
            "  "
            f"{waiting_pending['event_id']} "
            f"not_before={waiting_pending.get('not_before', '?')} "
            f"cycle={waiting_pending.get('scheduled_by_cycle', '?')} "
            f"context={waiting_pending.get('requested_context_count', 0)} "
            f"purpose={waiting_pending.get('purpose', '')}"
        )

    expired_pending = report.get("oldest_expired_pending")
    if expired_pending:
        lines.append("")
        lines.append("Oldest expired pending:")
        lines.append(
            "  "
            f"{expired_pending['event_id']} "
            f"expires_at={expired_pending.get('expires_at', '?')} "
            f"cycle={expired_pending.get('scheduled_by_cycle', '?')} "
            f"context={expired_pending.get('requested_context_count', 0)} "
            f"purpose={expired_pending.get('purpose', '')}"
        )

    if report.get("failed"):
        lines.append("")
        lines.append("Failed:")
        for event in report["failed"]:
            lines.append(
                "  "
                f"{event['event_id']} "
                f"{event.get('error_type', 'Error')}: "
                f"{event.get('error', '')}"
            )

    if report.get("stale_running"):
        lines.append("")
        lines.append("Stale running:")
        for event in report["stale_running"]:
            lines.append(
                "  "
                f"{event['event_id']} "
                f"age={event.get('running_age_seconds', '?')}s "
                f"run_id={event.get('run_id', '?')} "
                f"purpose={event.get('purpose', '')}"
            )

    if report.get("context_errors"):
        lines.append("")
        lines.append("Context errors:")
        for event in report["context_errors"]:
            lines.append(
                "  "
                f"{event['event_id']} "
                f"errors={event.get('context_error_count', 0)} "
                f"purpose={event.get('purpose', '')}"
            )

    if report.get("lifecycle_anomalies"):
        lines.append("")
        lines.append("Lifecycle anomalies:")
        for anomaly in report["lifecycle_anomalies"]:
            statuses = ",".join(anomaly.get("statuses", []))
            lines.append(
                "  "
                f"{anomaly.get('event_id', '?')} "
                f"{anomaly.get('kind', 'anomaly')} "
                f"statuses={statuses} "
                f"{anomaly.get('message', '')}"
            )

    if report.get("outcome_warnings"):
        lines.append("")
        lines.append("Outcome warnings:")
        for event in report["outcome_warnings"]:
            flags = []
            if event.get("response_state_mismatch"):
                flags.append("response/state mismatch")
            if event.get("deleted_load_bearing_field"):
                flags.append("load-bearing deletion")
            if event.get("no_durable_state_change"):
                flags.append("no durable state change")
            flag_text = ", ".join(flags) or "warning"
            lines.append(
                "  "
                f"{event['event_id']} "
                f"{flag_text} "
                f"changed={event.get('changed_load_bearing_fields', [])} "
                f"deleted={event.get('deleted_load_bearing_fields', [])}"
            )

    if report.get("completed"):
        lines.append("")
        lines.append("Recently completed:")
        for event in report["completed"]:
            snippet = event.get("response_snippet") or ""
            lines.append(
                "  "
                f"{event['event_id']} "
                f"wake_cycle={event.get('wake_cycle', '?')} "
                f"context_errors={event.get('context_error_count', 0)} "
                f"response={snippet}"
            )

    return "\n".join(lines)


def run_next_event(
    session,
    store: EventStore,
    *,
    now: datetime | None = None,
) -> dict:
    """Run the oldest pending event once using an OpenTasteSession."""
    claim = store.claim_next_pending(now=now)
    if claim is None:
        return {"status": "none", "message": "no runnable pending events"}
    event, running = claim
    if running.get("status") == "expired":
        return running

    run_id = running["run_id"]
    context_results: list[dict] | None = None
    try:
        context_results = resolve_requested_context(
            event.get("requested_context", []),
            prior_states=session._prior_states,
            bridge=session._bridge,
        )
        envelope = build_event_envelope(event, context_results, run_id)
        before_state = _json_safe_state(getattr(session, "_state", None))
        response = session.exchange(envelope, force_memory=None)
        after_state = _json_safe_state(getattr(session, "_state", None))
        outcome_observation = build_outcome_observation(
            before_state=before_state,
            after_state=after_state,
            response_text=response,
        )
        return store.append_completed(
            event=event,
            run_id=run_id,
            wake_cycle=session.cycle,
            result_record_id=session._prior_states[-1][1],
            response_text=response,
            context_results=context_results,
            outcome_observation=outcome_observation,
        )
    except Exception as e:
        store.append_failed(
            event=event,
            run_id=run_id,
            exc=e,
            context_results=context_results,
        )
        raise


def run_pending_events(
    session,
    store: EventStore,
    *,
    limit: int = 10,
    stop_on_failure: bool = True,
    now: datetime | None = None,
) -> dict:
    """Run up to limit pending events and return a batch summary."""
    results: list[dict] = []
    for _ in range(limit):
        try:
            result = run_next_event(session, store, now=now)
        except Exception as e:
            failure = {
                "status": "failed",
                "error_type": type(e).__name__,
                "error": str(e),
            }
            results.append(failure)
            if stop_on_failure:
                break
            continue
        results.append(result)
        if result.get("status") == "none":
            break
        if result.get("status") == "failed" and stop_on_failure:
            break
    return {
        "status": "completed",
        "limit": limit,
        "ran": len([r for r in results if r.get("status") != "none"]),
        "results": results,
    }


def main() -> None:
    import argparse
    import os

    from hamutay.taste_open import (
        AnthropicTasteBackend,
        OpenAITasteBackend,
        OpenTasteSession,
    )

    parser = argparse.ArgumentParser(
        description="Run one pending taste_open scheduled event."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-next")
    run.add_argument("--log-path", required=True)
    run.add_argument("--event-log-path", default=None)
    run.add_argument("--model", default="claude-haiku-4-5")
    run.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    run.add_argument("--base-url", default=None)
    run.add_argument("--api-key", default=None)
    run.add_argument("--project-root", default=".")
    run.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum output tokens for the wake cycle.",
    )
    run_all = sub.add_parser("run-all")
    run_all.add_argument("--log-path", required=True)
    run_all.add_argument("--event-log-path", default=None)
    run_all.add_argument("--model", default="claude-haiku-4-5")
    run_all.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    run_all.add_argument("--base-url", default=None)
    run_all.add_argument("--api-key", default=None)
    run_all.add_argument("--project-root", default=".")
    run_all.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum output tokens for each wake cycle.",
    )
    run_all.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of pending events to run.",
    )
    run_all.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Keep processing later events after a wake failure.",
    )
    report = sub.add_parser("report")
    report.add_argument(
        "--log-path",
        default=None,
        help="Session JSONL path; event sidecar is derived from this path.",
    )
    report.add_argument(
        "--event-log-path",
        default=None,
        help="Event JSONL path. Overrides --log-path sidecar derivation.",
    )
    report.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON rather than human-readable text.",
    )
    report.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum failed/completed/context-error rows to show.",
    )
    args = parser.parse_args()

    if args.command == "report":
        if args.event_log_path is None and args.log_path is None:
            raise SystemExit("report requires --event-log-path or --log-path")
        event_log_path = (
            args.event_log_path
            or str(default_event_log_path(args.log_path))
        )
        store = EventStore(event_log_path)
        summary = summarize_event_log(store.read_records(), limit=args.limit)
        if args.json:
            print(json.dumps(summary, indent=2, default=str))
        else:
            print(format_event_report(summary, path=event_log_path))
        return

    backend = None
    if args.provider == "anthropic":
        backend = AnthropicTasteBackend(max_tokens=args.max_tokens)
    else:
        if args.provider == "openrouter":
            base_url = args.base_url or "https://openrouter.ai/api/v1"
            api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
            extra_headers = {
                "X-Title": "hamutay/event-runner",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            }
        else:
            base_url = args.base_url or "https://api.openai.com/v1"
            api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
            extra_headers = {}
        if not api_key:
            raise SystemExit(
                f"No API key for {args.provider}: pass --api-key or set env"
            )
        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            max_tokens=args.max_tokens,
            extra_headers=extra_headers,
            provider_name=args.provider,
        )

    event_log_path = args.event_log_path or str(default_event_log_path(args.log_path))
    session = OpenTasteSession(
        model=args.model,
        backend=backend,
        log_path=args.log_path,
        event_log_path=event_log_path,
        resume=True,
        enable_tools=True,
        project_root=Path(args.project_root),
    )
    store = EventStore(event_log_path)
    if args.command == "run-all":
        result = run_pending_events(
            session,
            store,
            limit=args.limit,
            stop_on_failure=not args.continue_on_failure,
        )
    else:
        result = run_next_event(session, store)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
