"""Append-only event log for taste_open scheduled wakeups."""

from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from hamutay.terminal_surface import validate_terminal_surface

EVENT_TYPE_REFLECTION = "self_scheduled_reflection"
VALID_CONTEXT_TOOLS = {"recall", "compare", "walk"}
VALID_WALK_DIRECTIONS = {"forward", "backward", "both"}
VALID_WALK_MODES = {"path", "adjacent"}
VALID_POLICY_ACTIONS = {
    "continue_after",
    "stop_complete",
    "ask_external_evidence",
}
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
        elif tool == "compare":
            if "cycle_a" not in request or "cycle_b" not in request:
                raise ValueError("compare context requires cycle_a and cycle_b")
            allowed = {"tool", "cycle_a", "cycle_b", "field", "content"}
        else:
            if "from_record_id" not in request:
                raise ValueError("walk context requires from_record_id")
            direction = request.get("direction")
            if direction is not None and direction not in VALID_WALK_DIRECTIONS:
                raise ValueError(
                    "walk context direction must be one of: "
                    f"{', '.join(sorted(VALID_WALK_DIRECTIONS))}"
                )
            mode = request.get("mode")
            if mode is not None and mode not in VALID_WALK_MODES:
                raise ValueError(
                    "walk context mode must be one of: "
                    f"{', '.join(sorted(VALID_WALK_MODES))}"
                )
            depth = request.get("depth")
            if (
                depth is not None
                and (
                    not isinstance(depth, int)
                    or isinstance(depth, bool)
                    or depth < 0
                )
            ):
                raise ValueError(
                    "walk context depth must be a non-negative integer"
                )
            allowed = {"tool", "from_record_id", "direction", "depth", "mode"}
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
    durable_update_contract: dict | None = None,
    durable_update_example: dict | None = None,
    terminal_surface: dict | None = None,
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
    if durable_update_contract is not None:
        if not isinstance(durable_update_contract, dict):
            raise ValueError("durable_update_contract must be an object")
        record["durable_update_contract"] = json.loads(
            json.dumps(durable_update_contract, default=str)
        )
    if durable_update_example is not None:
        if not isinstance(durable_update_example, dict):
            raise ValueError("durable_update_example must be an object")
        record["durable_update_example"] = json.loads(
            json.dumps(durable_update_example, default=str)
        )
    if terminal_surface is not None:
        record["terminal_surface"] = validate_terminal_surface(terminal_surface)
    if not_before:
        # Validate parseability but preserve original ISO spelling.
        datetime.fromisoformat(str(not_before).replace("Z", "+00:00"))
        record["not_before"] = str(not_before)
    if expires_at:
        # Validate parseability but preserve original ISO spelling.
        datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        record["expires_at"] = str(expires_at)
    return record


def build_evidence_resume_event(
    *,
    evidence_request: dict,
    evidence_fulfillment: dict,
    purpose: str,
    label: str | None = None,
    not_before: str | None = None,
    terminal_surface: dict | None = None,
) -> dict:
    """Build a pending event that resumes work after evidence fulfillment."""
    if not isinstance(evidence_request, dict):
        raise ValueError("evidence_request must be an object")
    if not isinstance(evidence_fulfillment, dict):
        raise ValueError("evidence_fulfillment must be an object")
    if evidence_fulfillment.get("request_id") != evidence_request.get("request_id"):
        raise ValueError("evidence_fulfillment.request_id must match request")
    result_record_id = evidence_request.get("result_record_id")
    if not result_record_id:
        raise ValueError("evidence_request.result_record_id is required")
    wake_cycle = evidence_request.get("wake_cycle")
    if not isinstance(wake_cycle, int) or isinstance(wake_cycle, bool):
        raise ValueError("evidence_request.wake_cycle must be an integer")
    event = build_pending_event(
        purpose=purpose,
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(UUID(str(result_record_id))),
            }
        ],
        scheduled_by_cycle=wake_cycle,
        scheduled_by_record_id=UUID(str(result_record_id)),
        label=label,
        not_before=not_before,
        terminal_surface=terminal_surface,
    )
    event["resumes_evidence_request_id"] = evidence_request.get("request_id")
    event["resumes_evidence_fulfillment_id"] = (
        evidence_fulfillment.get("fulfillment_id")
    )
    event["evidence_context"] = {
        "evidence_request": json.loads(json.dumps(evidence_request, default=str)),
        "evidence_fulfillment": json.loads(
            json.dumps(evidence_fulfillment, default=str)
        ),
    }
    return event


def _expand_result_record_id(value: object, result_record_id: str) -> object:
    if isinstance(value, str):
        return value.replace("<result_record_id>", result_record_id)
    if isinstance(value, list):
        return [_expand_result_record_id(item, result_record_id) for item in value]
    if isinstance(value, dict):
        return {
            key: (
                json.loads(json.dumps(item, default=str))
                if key == "continuation_request"
                else _expand_result_record_id(item, result_record_id)
            )
            for key, item in value.items()
        }
    return value


def build_bound_continuation_event(
    *,
    completed_event: dict,
    continuation_request: dict,
) -> dict | None:
    """Build a pending event bound to a completed event's result record.

    The helper is intentionally pure: it validates and returns a pending event
    record, but does not append to EventStore. A model-owned durable
    continuation request can use the string placeholder ``<result_record_id>``
    anywhere in JSON-safe fields to refer to the completed wake record.
    """
    if not isinstance(completed_event, dict):
        raise ValueError("completed_event must be an object")
    if not isinstance(continuation_request, dict):
        raise ValueError("continuation_request must be an object")
    if continuation_request.get("requested") is not True:
        return None

    result_record_id = completed_event.get("result_record_id")
    if not result_record_id:
        raise ValueError("completed_event.result_record_id is required")
    result_record_id = str(UUID(str(result_record_id)))

    wake_cycle = completed_event.get("wake_cycle")
    if not isinstance(wake_cycle, int) or isinstance(wake_cycle, bool):
        raise ValueError("completed_event.wake_cycle must be an integer")

    purpose = _expand_result_record_id(
        continuation_request.get("purpose"),
        result_record_id,
    )
    if not isinstance(purpose, str) or not purpose.strip():
        raise ValueError("continuation_request.purpose is required")

    requested_context = _expand_result_record_id(
        continuation_request.get("requested_context"),
        result_record_id,
    )
    label = _expand_result_record_id(
        continuation_request.get("label"),
        result_record_id,
    )
    not_before = _expand_result_record_id(
        continuation_request.get("not_before"),
        result_record_id,
    )
    expires_at = _expand_result_record_id(
        continuation_request.get("expires_at"),
        result_record_id,
    )
    terminal_surface = _expand_result_record_id(
        continuation_request.get("terminal_surface"),
        result_record_id,
    )
    contract = _expand_result_record_id(
        continuation_request.get("durable_update_contract"),
        result_record_id,
    )
    example = _expand_result_record_id(
        continuation_request.get("durable_update_example"),
        result_record_id,
    )

    event = build_pending_event(
        purpose=purpose,
        requested_context=requested_context,
        scheduled_by_cycle=wake_cycle,
        scheduled_by_record_id=UUID(result_record_id),
        label=label if isinstance(label, str) and label else None,
        not_before=not_before if isinstance(not_before, str) and not_before else None,
        expires_at=expires_at if isinstance(expires_at, str) and expires_at else None,
        durable_update_contract=contract if isinstance(contract, dict) else None,
        durable_update_example=example if isinstance(example, dict) else None,
        terminal_surface=terminal_surface if isinstance(terminal_surface, dict) else None,
    )
    event["bound_by"] = "continuation_request"
    event["bound_source_event_id"] = completed_event.get("event_id")
    event["bound_result_record_id"] = result_record_id
    if continuation_request.get("kind") is not None:
        event["continuation_kind"] = str(continuation_request["kind"])
    return event


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
        wake_validation: dict | None = None,
        auto_continuation_event: dict | None = None,
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
        if wake_validation is not None:
            record["wake_validation"] = wake_validation
        if auto_continuation_event is not None:
            record["auto_continuation_appended"] = True
            record["auto_continuation_event_id"] = (
                auto_continuation_event.get("event_id")
            )
        self.append(record)
        return record

    def append_policy_disposition(
        self,
        *,
        event: dict,
        run_id: str,
        wake_cycle: int,
        result_record_id: UUID | str,
        policy_decision: dict,
        policy_result: dict | None = None,
        auto_continuation_event: dict | None = None,
    ) -> dict:
        """Append a lifecycle-neutral policy disposition for a completed wake."""
        if not isinstance(policy_decision, dict):
            raise ValueError("policy_decision must be an object")
        action = policy_decision.get("action")
        if action not in VALID_POLICY_ACTIONS:
            raise ValueError(
                "policy_decision.action must be one of: "
                f"{', '.join(sorted(VALID_POLICY_ACTIONS))}"
            )
        result = policy_result if isinstance(policy_result, dict) else {}
        record = {
            "record_type": "policy_disposition",
            "disposition_id": str(uuid4()),
            "source_event_id": event["event_id"],
            "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
            "run_id": run_id,
            "wake_cycle": int(wake_cycle),
            "result_record_id": str(result_record_id),
            "recorded_at": utc_now_iso(),
            "policy_action": action,
            "policy_rationale": policy_decision.get("rationale"),
            "completion_condition": policy_decision.get("completion_condition"),
        }
        if result:
            record["policy_result"] = json.loads(json.dumps(result, default=str))
            missing = result.get("missing_evidence")
            if isinstance(missing, list):
                record["missing_evidence"] = json.loads(
                    json.dumps(missing, default=str)
                )
        if action == "ask_external_evidence":
            record["classification"] = "evidence_blocked"
        elif action == "stop_complete":
            record["classification"] = "complete"
        elif action == "continue_after":
            record["classification"] = "continued"
        if auto_continuation_event is not None:
            record["continuation_event_id"] = auto_continuation_event.get(
                "event_id"
            )
            if auto_continuation_event.get("continuation_kind") is not None:
                record["continuation_kind"] = auto_continuation_event.get(
                    "continuation_kind"
                )
        self.append(record)
        return record

    def append_evidence_request(
        self,
        *,
        policy_disposition: dict,
    ) -> dict:
        """Append an open evidence request from an evidence-block disposition."""
        if not isinstance(policy_disposition, dict):
            raise ValueError("policy_disposition must be an object")
        if policy_disposition.get("policy_action") != "ask_external_evidence":
            raise ValueError(
                "policy_disposition.policy_action must be ask_external_evidence"
            )
        missing = policy_disposition.get("missing_evidence")
        if not isinstance(missing, list) or not missing:
            raise ValueError("policy_disposition.missing_evidence is required")
        record = {
            "record_type": "evidence_request",
            "request_id": str(uuid4()),
            "source_event_id": policy_disposition.get("source_event_id"),
            "source_disposition_id": policy_disposition.get("disposition_id"),
            "run_id": policy_disposition.get("run_id"),
            "wake_cycle": policy_disposition.get("wake_cycle"),
            "result_record_id": policy_disposition.get("result_record_id"),
            "status": "open",
            "created_at": utc_now_iso(),
            "missing_evidence": json.loads(json.dumps(missing, default=str)),
            "policy_rationale": policy_disposition.get("policy_rationale"),
        }
        self.append(record)
        return record

    def append_evidence_fulfillment(
        self,
        *,
        evidence_request: dict,
        evidence: dict,
        source: str | None = None,
    ) -> dict:
        """Append evidence satisfying an evidence request."""
        if not isinstance(evidence_request, dict):
            raise ValueError("evidence_request must be an object")
        if evidence_request.get("record_type") != "evidence_request":
            raise ValueError("evidence_request.record_type must be evidence_request")
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError("evidence must be a non-empty object")
        record = {
            "record_type": "evidence_fulfillment",
            "fulfillment_id": str(uuid4()),
            "request_id": evidence_request.get("request_id"),
            "fulfilled_at": utc_now_iso(),
            "source": source,
            "evidence": json.loads(json.dumps(evidence, default=str)),
        }
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

    def suppress_pending(
        self,
        *,
        reason: str,
        policy: str,
        suppressed_by_record_id: str | UUID | None = None,
        suppressed_by_cycle: int | None = None,
        suppressed_by_classification: str | None = None,
    ) -> list[dict]:
        """Mark all currently pending events as suppressed by scheduler policy."""
        suppressed: list[dict] = []
        with self._locked():
            latest = self._latest_by_event_id_from_records(
                self._read_records_unlocked()
            )
            pending = [
                record for record in latest.values()
                if record.get("status") == "pending"
            ]
            pending.sort(key=lambda record: str(record.get("created_at", "")))
            for event in pending:
                record = {
                    "record_type": "event_status",
                    "event_id": event["event_id"],
                    "event_type": event.get("event_type", EVENT_TYPE_REFLECTION),
                    "status": "suppressed",
                    "suppressed_at": utc_now_iso(),
                    "suppressed_by_policy": policy,
                    "suppression_reason": reason,
                }
                if suppressed_by_record_id is not None:
                    record["suppressed_by_record_id"] = str(
                        suppressed_by_record_id
                    )
                if suppressed_by_cycle is not None:
                    record["suppressed_by_cycle"] = int(suppressed_by_cycle)
                if suppressed_by_classification is not None:
                    record["suppressed_by_classification"] = (
                        suppressed_by_classification
                    )
                self._append_unlocked(record)
                suppressed.append(record)
        return suppressed


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
    from hamutay.tools.memory import tool_compare, tool_recall, tool_walk

    context = validate_requested_context(requests)
    results: list[dict] = []
    for request in context:
        params = {k: v for k, v in request.items() if k != "tool"}
        if request["tool"] == "recall":
            result = tool_recall(params, prior_states=prior_states, bridge=bridge)
        elif request["tool"] == "compare":
            result = tool_compare(params, prior_states=prior_states)
        elif request["tool"] == "walk":
            result = tool_walk(params, prior_states=prior_states, bridge=bridge)
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
        "durable_update_contract": event.get("durable_update_contract"),
        "durable_update_example": event.get("durable_update_example"),
        "terminal_surface": event.get("terminal_surface"),
        "evidence_context": event.get("evidence_context"),
        "context_results": context_results,
        "instruction": (
            "This is a self-scheduled reflection event. Use the provided "
            "context to decide whether to revise, preserve, defer, or "
            "declare losses. If the purpose names required durable wake "
            "updates, those updates must be committed as top-level fields in "
            "the object you produce with think_and_respond. Visible prose is "
            "not enough. Preserve model-owned continuity fields unless the "
            "purpose explicitly says to change them; framework-owned fields "
            "such as cycle and _activity_log are substrate-owned. End the "
            "cycle with the declared terminal surface if terminal_surface is "
            "present; otherwise use think_and_respond."
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


def build_wake_validation_summary(validation: dict | None) -> dict | None:
    """Summarize a wake validation artifact for event-log observability."""
    if not isinstance(validation, dict):
        return None
    first_pass = validation.get("first_pass")
    first_pass = first_pass if isinstance(first_pass, dict) else {}
    repair = validation.get("repair")
    repair = repair if isinstance(repair, dict) else {}
    summary = {
        "status": validation.get("status"),
        "validation_record_id": validation.get("record_id"),
        "source_cycle": validation.get("source_cycle"),
        "source_record_id": validation.get("source_record_id"),
        "first_pass_status": first_pass.get("status"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repaired": validation.get("status") == "repaired",
    }
    if repair:
        summary["repair_status"] = repair.get("status")
        summary["has_repair_raw_output"] = isinstance(
            repair.get("raw_output"),
            dict,
        )
        summary["has_repair_validation"] = isinstance(
            repair.get("validation"),
            dict,
        )
        diagnostics = repair.get("state_merge_diagnostics")
        if isinstance(diagnostics, dict):
            summary["repair_ignored_protected_attempt_count"] = int(
                diagnostics.get("ignored_protected_attempt_count", 0)
            )
            summary["repair_ignored_protected_updates"] = list(
                diagnostics.get("ignored_protected_updates") or []
            )
            summary["repair_ignored_protected_deletions"] = list(
                diagnostics.get("ignored_protected_deletions") or []
            )
    return {
        key: value for key, value in json.loads(
            json.dumps(summary, default=str)
        ).items()
        if value is not None
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


TERMINAL_EVENT_STATUSES = {"completed", "failed", "expired", "suppressed"}


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
    wake_validation = latest.get("wake_validation")
    if not isinstance(wake_validation, dict):
        wake_validation = {}
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
        "suppressed_at": latest.get("suppressed_at"),
        "suppressed_by_policy": latest.get("suppressed_by_policy"),
        "suppression_reason": latest.get("suppression_reason"),
        "suppressed_by_record_id": latest.get("suppressed_by_record_id"),
        "suppressed_by_cycle": latest.get("suppressed_by_cycle"),
        "suppressed_by_classification": latest.get(
            "suppressed_by_classification"
        ),
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
        "terminal_surface_tool": (
            first.get("terminal_surface", {}) or {}
        ).get("tool_name"),
        "terminal_surface_label": (
            first.get("terminal_surface", {}) or {}
        ).get("label"),
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
        "wake_validation_status": wake_validation.get("status"),
        "wake_first_pass_status": wake_validation.get("first_pass_status"),
        "wake_repair_attempted": wake_validation.get("repair_attempted"),
        "wake_repair_status": wake_validation.get("repair_status"),
        "wake_repaired": wake_validation.get("repaired"),
        "wake_repair_ignored_protected_attempt_count": (
            wake_validation.get("repair_ignored_protected_attempt_count")
        ),
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

    policy_dispositions = [
        record for record in records
        if record.get("record_type") == "policy_disposition"
    ]
    policy_dispositions.sort(
        key=lambda record: str(record.get("recorded_at", "")),
        reverse=True,
    )
    policy_disposition_counts: dict[str, int] = {}
    for record in policy_dispositions:
        action = str(record.get("policy_action", "unknown"))
        policy_disposition_counts[action] = (
            policy_disposition_counts.get(action, 0) + 1
        )

    evidence_requests = [
        record for record in records
        if record.get("record_type") == "evidence_request"
    ]
    evidence_requests.sort(
        key=lambda record: str(record.get("created_at", "")),
        reverse=True,
    )
    evidence_fulfillments = [
        record for record in records
        if record.get("record_type") == "evidence_fulfillment"
    ]
    evidence_fulfillments.sort(
        key=lambda record: str(record.get("fulfilled_at", "")),
        reverse=True,
    )
    fulfilled_request_ids = {
        str(record.get("request_id"))
        for record in evidence_fulfillments
        if record.get("request_id")
    }
    evidence_request_summaries = []
    for record in evidence_requests:
        request = dict(record)
        request["status"] = (
            "fulfilled"
            if str(record.get("request_id")) in fulfilled_request_ids
            else "open"
        )
        evidence_request_summaries.append(request)
    open_evidence_requests = [
        record for record in evidence_request_summaries
        if record.get("status") == "open"
    ]
    fulfilled_evidence_requests = [
        record for record in evidence_request_summaries
        if record.get("status") == "fulfilled"
    ]

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
    suppressed = [
        event for event in events if event.get("status") == "suppressed"
    ]
    suppressed.sort(
        key=lambda event: str(event.get("suppressed_at", "")), reverse=True
    )
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
        "policy_disposition_count": len(policy_dispositions),
        "policy_disposition_counts": dict(
            sorted(policy_disposition_counts.items())
        ),
        "policy_dispositions": policy_dispositions[:limit],
        "evidence_request_count": len(evidence_requests),
        "open_evidence_request_count": len(open_evidence_requests),
        "fulfilled_evidence_request_count": len(fulfilled_evidence_requests),
        "evidence_requests": evidence_request_summaries[:limit],
        "evidence_fulfillment_count": len(evidence_fulfillments),
        "evidence_fulfillments": evidence_fulfillments[:limit],
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
        "suppressed": suppressed[:limit],
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
    disposition_counts = report.get("policy_disposition_counts", {})
    if disposition_counts:
        disposition_text = ", ".join(
            f"{action}={count}"
            for action, count in disposition_counts.items()
        )
        lines.append(f"Policy dispositions: {disposition_text}")
    if report.get("evidence_request_count"):
        lines.append(
            "Evidence requests: "
            f"open={report.get('open_evidence_request_count', 0)}, "
            f"fulfilled={report.get('fulfilled_evidence_request_count', 0)}"
        )
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

    if report.get("suppressed"):
        lines.append("")
        lines.append("Suppressed:")
        for event in report["suppressed"]:
            lines.append(
                "  "
                f"{event['event_id']} "
                f"policy={event.get('suppressed_by_policy', '?')} "
                f"reason={event.get('suppression_reason', '')}"
            )

    if report.get("policy_dispositions"):
        lines.append("")
        lines.append("Policy dispositions:")
        for record in report["policy_dispositions"]:
            extra = ""
            if record.get("continuation_event_id"):
                extra = f" continuation={record.get('continuation_event_id')}"
            elif record.get("missing_evidence"):
                extra = (
                    " missing="
                    + ", ".join(str(item) for item in record["missing_evidence"])
                )
            lines.append(
                "  "
                f"{record.get('source_event_id', '?')} "
                f"action={record.get('policy_action', '?')} "
                f"classification={record.get('classification', '?')}"
                f"{extra}"
            )

    if report.get("evidence_requests"):
        lines.append("")
        lines.append("Evidence requests:")
        for record in report["evidence_requests"]:
            missing = ", ".join(
                str(item) for item in record.get("missing_evidence", []) or []
            )
            lines.append(
                "  "
                f"{record.get('request_id', '?')} "
                f"status={record.get('status', '?')} "
                f"source_event={record.get('source_event_id', '?')} "
                f"missing={missing}"
            )

    if report.get("evidence_fulfillments"):
        lines.append("")
        lines.append("Evidence fulfillments:")
        for record in report["evidence_fulfillments"]:
            lines.append(
                "  "
                f"{record.get('fulfillment_id', '?')} "
                f"request={record.get('request_id', '?')} "
                f"source={record.get('source', '?')}"
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
            validation = ""
            if event.get("wake_validation_status") is not None:
                validation = (
                    f" validation={event.get('wake_validation_status')}"
                    f" first_pass={event.get('wake_first_pass_status')}"
                )
                if event.get("wake_repair_attempted"):
                    validation += f" repair={event.get('wake_repair_status')}"
            lines.append(
                "  "
                f"{event['event_id']} "
                f"wake_cycle={event.get('wake_cycle', '?')} "
                f"context_errors={event.get('context_error_count', 0)} "
                f"{validation} "
                f"response={snippet}"
            )

    return "\n".join(lines)


def run_next_event(
    session,
    store: EventStore,
    *,
    now: datetime | None = None,
    auto_continuations: bool = False,
    policy_dispositions: bool = False,
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
        response = session.exchange(
            envelope,
            force_memory=None,
            terminal_surface=event.get("terminal_surface"),
        )
        after_state = _json_safe_state(getattr(session, "_state", None))
        outcome_observation = build_outcome_observation(
            before_state=before_state,
            after_state=after_state,
            response_text=response,
        )
        wake_validation = build_wake_validation_summary(
            getattr(session, "_last_state_validation", None)
        )
        result_record_id = session._prior_states[-1][1]
        wake_cycle = session.cycle
        auto_continuation_event = None
        raw_output = getattr(session, "_last_raw_output", None)
        raw_output = raw_output if isinstance(raw_output, dict) else {}
        if auto_continuations:
            continuation_request = raw_output.get("continuation_request")
            if isinstance(continuation_request, dict):
                auto_continuation_event = build_bound_continuation_event(
                    completed_event={
                        "event_id": event["event_id"],
                        "status": "completed",
                        "run_id": run_id,
                        "wake_cycle": wake_cycle,
                        "result_record_id": str(result_record_id),
                    },
                    continuation_request=continuation_request,
                )
        completed = store.append_completed(
            event=event,
            run_id=run_id,
            wake_cycle=wake_cycle,
            result_record_id=result_record_id,
            response_text=response,
            context_results=context_results,
            outcome_observation=outcome_observation,
            wake_validation=wake_validation,
            auto_continuation_event=auto_continuation_event,
        )
        if auto_continuation_event is not None:
            store.append(auto_continuation_event)
            completed["auto_continuation_event"] = auto_continuation_event
        if policy_dispositions:
            policy_decision = raw_output.get("policy_decision")
            if isinstance(policy_decision, dict):
                policy_disposition = store.append_policy_disposition(
                    event=event,
                    run_id=run_id,
                    wake_cycle=wake_cycle,
                    result_record_id=result_record_id,
                    policy_decision=policy_decision,
                    policy_result=raw_output.get("policy_result"),
                    auto_continuation_event=auto_continuation_event,
                )
                completed["policy_disposition"] = policy_disposition
        return completed
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
    auto_continuations: bool = False,
    policy_dispositions: bool = False,
    max_auto_continuations: int | None = None,
) -> dict:
    """Run up to limit pending events and return a batch summary."""
    if (
        max_auto_continuations is not None
        and (
            not isinstance(max_auto_continuations, int)
            or isinstance(max_auto_continuations, bool)
            or max_auto_continuations < 0
        )
    ):
        raise ValueError("max_auto_continuations must be a non-negative integer")
    results: list[dict] = []
    auto_continuation_count = 0
    auto_continuation_limit_reached = False
    for _ in range(limit):
        try:
            result = run_next_event(
                session,
                store,
                now=now,
                auto_continuations=auto_continuations,
                policy_dispositions=policy_dispositions,
            )
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
        if result.get("auto_continuation_event") is not None:
            auto_continuation_count += 1
        if result.get("status") == "none":
            break
        if result.get("status") == "failed" and stop_on_failure:
            break
        if (
            max_auto_continuations is not None
            and auto_continuation_count >= max_auto_continuations
        ):
            auto_continuation_limit_reached = True
            break
    return {
        "status": "completed",
        "limit": limit,
        "ran": len([r for r in results if r.get("status") != "none"]),
        "auto_continuation_count": auto_continuation_count,
        "max_auto_continuations": max_auto_continuations,
        "auto_continuation_limit_reached": auto_continuation_limit_reached,
        "results": results,
    }


def step_pending_events(
    session,
    store: EventStore,
    *,
    limit: int = 10,
    stop_on_failure: bool = True,
    now: datetime | None = None,
    auto_continuations: bool = False,
    policy_dispositions: bool = False,
    max_auto_continuations: int | None = None,
) -> dict:
    """Run one fixed-time scheduler step and report why the step stopped.

    This is the DES-facing wrapper around run_pending_events: it never advances
    time by itself, and it reports the earliest future not_before boundary when
    work is waiting.
    """
    batch = run_pending_events(
        session,
        store,
        limit=limit,
        stop_on_failure=stop_on_failure,
        now=now,
        auto_continuations=auto_continuations,
        policy_dispositions=policy_dispositions,
        max_auto_continuations=max_auto_continuations,
    )
    summary = summarize_event_log(store.read_records(), now=now)
    results = batch.get("results", [])
    completed_or_failed = [
        result for result in results
        if result.get("status") in {"completed", "failed"}
    ]
    expired = [result for result in results if result.get("status") == "expired"]
    failed = [result for result in results if result.get("status") == "failed"]
    reached_limit = (
        limit > 0
        and len([r for r in results if r.get("status") != "none"]) >= limit
        and (
            summary.get("pending_runnable_count", 0)
            or summary.get("pending_expired_count", 0)
        )
    )
    if batch.get("auto_continuation_limit_reached"):
        stop_reason = "auto_continuation_limit_reached"
    elif failed and stop_on_failure:
        stop_reason = "failed"
    elif reached_limit:
        stop_reason = "limit_reached"
    elif summary.get("pending_expired_count", 0):
        stop_reason = "expired_pending"
    elif summary.get("pending_runnable_count", 0):
        stop_reason = "runnable_pending"
    elif summary.get("pending_waiting_count", 0):
        stop_reason = "waiting"
    else:
        stop_reason = "idle"

    waiting = summary.get("oldest_waiting_pending") or {}
    next_wake_at = waiting.get("not_before")
    return {
        "status": "completed",
        "stop_reason": stop_reason,
        "now": (now or datetime.now(timezone.utc)).isoformat(),
        "limit": limit,
        "wake_run_count": len(completed_or_failed),
        "expired_count": len(expired),
        "terminalized_count": len(completed_or_failed) + len(expired),
        "next_wake_at": next_wake_at,
        "pending_runnable_count": summary.get("pending_runnable_count", 0),
        "pending_waiting_count": summary.get("pending_waiting_count", 0),
        "pending_expired_count": summary.get("pending_expired_count", 0),
        "batch": batch,
        "summary": summary,
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
