from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from hamutay.events import (
    EventStore,
    build_bound_continuation_event,
    build_outcome_observation,
    build_pending_event,
    build_event_envelope,
    build_wake_validation_summary,
    resolve_requested_context,
    summarize_event_log,
)
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.restart_frontier import RestartFrontierStore
from hamutay.taste_open import ExchangeResult, OpenTasteSession


EXPERIMENT_ID = "live_sustained_loop_provider_readiness_20260617"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_MAX_TOKENS = 4096


JsonDict = dict[str, Any]


class ScriptedTerminalBackend:
    """Small deterministic backend for dry probe tests."""

    def __init__(self, outputs: list[JsonDict | Exception]):
        self.outputs = list(outputs)
        self.calls: list[JsonDict] = []

    def call_terminal_surface(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        terminal_surface: JsonDict,
    ) -> ExchangeResult:
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "experiment_label": experiment_label,
                "terminal_surface": terminal_surface,
            }
        )
        if not self.outputs:
            raise RuntimeError("no scripted terminal output remaining")
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return ExchangeResult(raw_output=output, stop_reason="tool_use")


@dataclass
class ProbePaths:
    output_root: Path
    session_log: Path
    event_log: Path
    action_log: Path
    frontier_log: Path
    memory_snapshot: Path
    attempts_log: Path
    failures_log: Path


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def default_terminal_tool_choice(endpoint: str) -> str:
    if "api.deepseek.com" in endpoint:
        return "auto"
    return "force"


def prepare_output_root(output_root: Path, *, overwrite: bool) -> ProbePaths:
    if output_root.exists() and overwrite:
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    return ProbePaths(
        output_root=output_root,
        session_log=output_root / "taste_open.jsonl",
        event_log=output_root / "events.jsonl",
        action_log=output_root / "actions.jsonl",
        frontier_log=output_root / "restart_frontier.jsonl",
        memory_snapshot=output_root / "memory_snapshot.json",
        attempts_log=output_root / "attempts.jsonl",
        failures_log=output_root / "failures.jsonl",
    )


def append_jsonl(path: Path, record: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def write_json(path: Path, record: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")


def terminal_surface(
    *,
    tool_name: str,
    description: str,
    tool_choice: str,
    properties: JsonDict,
    required: list[str],
    copy_fields: list[str],
) -> JsonDict:
    return {
        "tool_name": tool_name,
        "description": description,
        "tool_choice": tool_choice,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
        "state_update": {
            "response_field": "response",
            "copy": {field: field for field in copy_fields},
        },
    }


def open_items_schema() -> JsonDict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "text": {"type": "string"},
            },
            "required": ["kind", "text"],
        },
    }


def continuation_request_schema() -> JsonDict:
    return {
        "type": "object",
        "properties": {
            "requested": {"type": "boolean"},
            "kind": {"type": "string"},
            "purpose": {"type": "string"},
            "symbolic_context": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "enum": ["completed_wake_state"],
                        },
                        "field": {"type": "string"},
                    },
                    "required": ["source"],
                },
            },
            "label": {"type": "string"},
        },
        "required": ["requested", "purpose", "symbolic_context", "label"],
    }


def inbound_terminal_surface(*, tool_choice: str) -> JsonDict:
    return terminal_surface(
        tool_name="handle_inbound_ipc",
        description=(
            "Handle an inbound IPC-style message and request a continuation. "
            "Return response exactly: inbound IPC accepted"
        ),
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["inbound IPC accepted"],
            },
            "inbound_status": {"type": "string"},
            "open_items": open_items_schema(),
            "continuation_request": continuation_request_schema(),
        },
        required=[
            "response",
            "inbound_status",
            "open_items",
            "continuation_request",
        ],
        copy_fields=["inbound_status", "open_items", "continuation_request"],
    )


def seed_terminal_surface(*, tool_choice: str) -> JsonDict:
    return terminal_surface(
        tool_name="initialize_live_loop_probe",
        description="Initialize durable state for the live event-loop probe.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string"},
            "probe_status": {"type": "string"},
            "open_items": open_items_schema(),
        },
        required=["response", "probe_status", "open_items"],
        copy_fields=["probe_status", "open_items"],
    )


def continuation_terminal_surface(*, tool_choice: str) -> JsonDict:
    return terminal_surface(
        tool_name="complete_bound_continuation",
        description=(
            "Complete the framework-bound continuation. Return response exactly: "
            "bound continuation complete"
        ),
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["bound continuation complete"],
            },
            "continuation_status": {
                "type": "string",
                "enum": ["completed"],
            },
            "open_items": {"type": "array", "maxItems": 0},
        },
        required=["response", "continuation_status", "open_items"],
        copy_fields=["continuation_status", "open_items"],
    )


def housekeeping_terminal_surface(*, tool_choice: str) -> JsonDict:
    return terminal_surface(
        tool_name="complete_housekeeping_audit",
        description=(
            "Complete a restart-recovered housekeeping event. If no open items "
            "remain, return response exactly: housekeeping audit clean"
        ),
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["housekeeping audit clean"],
            },
            "open_items": open_items_schema(),
            "housekeeping_audit": {
                "type": "object",
                "properties": {
                    "audit_index": {"type": "integer"},
                    "open_item_count": {"type": "integer"},
                    "status": {"type": "string", "enum": ["clean"]},
                },
                "required": ["audit_index", "open_item_count", "status"],
            },
        },
        required=["response", "open_items", "housekeeping_audit"],
        copy_fields=["open_items", "housekeeping_audit"],
    )


def scripted_success_outputs(tool_choice: str) -> list[JsonDict]:
    del tool_choice
    return [
        {
            "response": "live loop probe initialized",
            "probe_status": "ready",
            "open_items": [],
        },
        {
            "response": "accepted inbound IPC work",
            "inbound_status": "accepted",
            "open_items": [{"kind": "todo", "text": "finish inbound work"}],
            "continuation_request": {
                "requested": True,
                "kind": "session_bound_continuation",
                "purpose": "Finish inbound work from <result_record_id>.",
                "symbolic_context": [
                    {
                        "source": "completed_wake_state",
                        "field": "inbound_status",
                    }
                ],
                "label": "finish-inbound-work",
            },
        },
        {
            "response": "finished bound continuation",
            "continuation_status": "closed",
            "open_items": [],
        },
        {
            "response": "housekeeping audit complete",
            "open_items": [],
            "housekeeping_audit": {
                "audit_index": 1,
                "open_item_count": 0,
                "status": "clean",
            },
        },
    ]


def classify_exception(exc: Exception, *, stage: str) -> JsonDict:
    error = str(exc)
    error_lower = error.lower()
    exc_name = type(exc).__name__
    layer = "harness"
    code = "unexpected_exception"
    if (
        "thinking mode does not support" in error_lower
        or "tool_choice" in error_lower
        and "support" in error_lower
    ):
        layer = "provider"
        code = "provider_rejected_tool_choice"
    elif any(
        marker in error_lower
        for marker in (
            "timeout",
            "connection",
            "rate limit",
            "unauthorized",
            "forbidden",
            "bad request",
            "status code",
            "api",
        )
    ):
        layer = "provider"
        code = "provider_api_error"
    elif "no " in error_lower and "terminal surface output" in error_lower:
        layer = "protocol"
        code = "missing_terminal_surface_output"
    elif "finish_reason=length" in error:
        layer = "protocol"
        code = "truncated_terminal_surface_output"
    elif stage in {"context_resolution", "claim", "continuation_build"}:
        layer = "scheduler"
        code = f"{stage}_failed"
    elif stage in {"frontier_commit", "frontier_load", "resume"}:
        layer = "persistence"
        code = f"{stage}_failed"
    return {
        "surface": "present",
        "layer": layer,
        "code": code,
        "stage": stage,
        "error_type": exc_name,
        "error": error,
    }


def model_output_failure(*, code: str, stage: str, message: str) -> JsonDict:
    return {
        "surface": "present",
        "layer": "model_output",
        "code": code,
        "stage": stage,
        "error_type": "ModelOutputInvariantViolation",
        "error": message,
    }


def bind_symbolic_continuation_request(
    continuation_request: JsonDict,
    *,
    terminal_tool_choice: str,
) -> tuple[JsonDict | None, JsonDict | None]:
    if continuation_request.get("requested") is not True:
        return None, None
    symbolic_context = continuation_request.get("symbolic_context")
    if not isinstance(symbolic_context, list) or not symbolic_context:
        return None, model_output_failure(
            code="invalid_symbolic_context",
            stage="continuation_binding",
            message=(
                "continuation_request.symbolic_context must be a non-empty "
                "list of symbolic context requests"
            ),
        )

    requested_context: list[JsonDict] = []
    for index, item in enumerate(symbolic_context):
        if not isinstance(item, dict):
            return None, model_output_failure(
                code="invalid_symbolic_context_item",
                stage="continuation_binding",
                message=f"symbolic_context[{index}] must be an object",
            )
        source = item.get("source")
        if source != "completed_wake_state":
            return None, model_output_failure(
                code="unsupported_symbolic_context_source",
                stage="continuation_binding",
                message=(
                    "symbolic context source must be completed_wake_state"
                ),
            )
        request: JsonDict = {
            "tool": "recall",
            "record_id": "<result_record_id>",
        }
        field = item.get("field")
        if isinstance(field, str) and field:
            request["field"] = field
        requested_context.append(request)

    bound_request: JsonDict = {
        "requested": True,
        "kind": str(
            continuation_request.get("kind") or "framework_bound_continuation"
        ),
        "purpose": (
            "Complete the inbound IPC work from <result_record_id>. Set "
            "continuation_status to completed, set open_items to [], and "
            "return response exactly: bound continuation complete."
        ),
        "requested_context": requested_context,
        "label": str(
            continuation_request.get("label") or "framework-bound-continuation"
        ),
        "terminal_surface": continuation_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
        "binding_contract": "framework_bound_symbolic_continuation.v1",
        "symbolic_context": json.loads(json.dumps(symbolic_context, default=str)),
        "model_requested_purpose": str(
            continuation_request.get("purpose") or ""
        ).strip(),
    }
    ignored = sorted(
        key for key in ("requested_context", "terminal_surface")
        if key in continuation_request
    )
    if ignored:
        bound_request["ignored_model_authored_fields"] = ignored
    return bound_request, None


def record_failure(paths: ProbePaths, failure: JsonDict, **evidence: Any) -> JsonDict:
    record = {
        "record_type": "probe_failure",
        "recorded_at": utc_now_iso(),
        "failure_attribution": failure,
        "evidence": evidence,
    }
    append_jsonl(paths.failures_log, record)
    return record


def mirror_session_state(memory: LocalMemorySubstrate, session: OpenTasteSession) -> str:
    if not session._prior_states:
        raise RuntimeError("session has no durable state to mirror")
    cycle, record_id, state, _timestamp = session._prior_states[-1]
    stored = memory.store_episode(
        record_id=record_id,
        record_type="open_taste_cycle",
        content=state,
        production={
            "who": {"instance": "open-taste-session"},
            "what": {"artifact": "open_taste_cycle"},
            "when": {"cycle": cycle},
            "where": {"project": "hamutay"},
        },
        execution_trace={"tool_path": EXPERIMENT_ID},
    )
    if (
        not stored.ok
        and stored.error is not None
        and stored.error.code != "duplicate_record"
    ):
        raise RuntimeError(json.dumps(stored.to_dict(), sort_keys=True))
    return str(record_id)


def commit_frontier(
    *,
    paths: ProbePaths,
    frontier: RestartFrontierStore,
    memory: LocalMemorySubstrate,
    ledger: ActionLedger,
    store: EventStore,
    session: OpenTasteSession,
    run_id: str,
    notes: JsonDict,
) -> JsonDict | None:
    try:
        result_record_id = mirror_session_state(memory, session)
        frontier_record = frontier.commit_frontier(
            run_id=run_id,
            cycle_id=session.cycle,
            result_record_id=result_record_id,
            memory=memory,
            ledger=ledger,
            event_store=store,
            notes=notes,
        )
    except Exception as exc:
        failure = classify_exception(exc, stage="frontier_commit")
        record_failure(paths, failure, notes=notes)
        return failure
    return frontier_record.to_payload()


def append_probe_event(
    store: EventStore,
    *,
    event_type: str,
    label: str,
    purpose: str,
    scheduled_by_cycle: int,
    scheduled_by_record_id: UUID | str,
    terminal_surface: JsonDict,
    requested_context: list[JsonDict] | None = None,
) -> JsonDict:
    context = requested_context or [{"tool": "recall", "cycle": scheduled_by_cycle}]
    event = build_pending_event(
        purpose=purpose,
        requested_context=context,
        scheduled_by_cycle=scheduled_by_cycle,
        scheduled_by_record_id=UUID(str(scheduled_by_record_id)),
        label=label,
        terminal_surface=terminal_surface,
    )
    event["event_type"] = event_type
    store.append(event)
    return event


def run_attributed_event(
    *,
    session: OpenTasteSession,
    store: EventStore,
    paths: ProbePaths,
    auto_continuations: bool,
    terminal_tool_choice: str,
) -> JsonDict:
    claim = store.claim_next_pending()
    if claim is None:
        return {"status": "none", "message": "no runnable pending events"}
    event, running = claim
    if running.get("status") == "expired":
        return running
    run_id = str(running["run_id"])
    context_results: list[JsonDict] | None = None
    envelope = ""
    try:
        context_results = resolve_requested_context(
            event.get("requested_context", []),
            prior_states=session._prior_states,
            bridge=session._bridge,
        )
        envelope = build_event_envelope(event, context_results, run_id)
        append_jsonl(
            paths.attempts_log,
            {
                "record_type": "event_attempt",
                "recorded_at": utc_now_iso(),
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "run_id": run_id,
                "terminal_surface": event.get("terminal_surface"),
                "envelope": json.loads(envelope),
            },
        )
        before_state = json.loads(json.dumps(getattr(session, "_state", None)))
        response = session.exchange(
            envelope,
            force_memory=None,
            terminal_surface=event.get("terminal_surface"),
        )
        after_state = json.loads(json.dumps(getattr(session, "_state", None)))
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
        raw_output = getattr(session, "_last_raw_output", None)
        raw_output = raw_output if isinstance(raw_output, dict) else {}
        auto_continuation_event = None
        continuation_binding_failure = None
        bound_continuation_request = None
        if auto_continuations:
            continuation_request = raw_output.get("continuation_request")
            if isinstance(continuation_request, dict):
                bound_continuation_request, continuation_binding_failure = (
                    bind_symbolic_continuation_request(
                        continuation_request,
                        terminal_tool_choice=terminal_tool_choice,
                    )
                )
            if bound_continuation_request is not None:
                auto_continuation_event = build_bound_continuation_event(
                    completed_event={
                        "event_id": event["event_id"],
                        "status": "completed",
                        "run_id": run_id,
                        "wake_cycle": wake_cycle,
                        "result_record_id": str(result_record_id),
                    },
                    continuation_request=bound_continuation_request,
                )
                if auto_continuation_event is not None:
                    auto_continuation_event[
                        "binding_contract"
                    ] = "framework_bound_symbolic_continuation.v1"
                    auto_continuation_event["model_symbolic_context"] = (
                        bound_continuation_request.get("symbolic_context")
                    )
                    if bound_continuation_request.get(
                        "ignored_model_authored_fields"
                    ):
                        auto_continuation_event[
                            "ignored_model_authored_fields"
                        ] = bound_continuation_request[
                            "ignored_model_authored_fields"
                        ]
                    auto_continuation_event["model_requested_purpose"] = (
                        bound_continuation_request.get("model_requested_purpose")
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
        return {
            **completed,
            "raw_output": raw_output,
            "auto_continuation_event": auto_continuation_event,
            "continuation_binding_failure": continuation_binding_failure,
            "bound_continuation_request": bound_continuation_request,
        }
    except Exception as exc:
        failure = classify_exception(exc, stage="event_exchange")
        failed = store.append_failed(
            event=event,
            run_id=run_id,
            exc=exc,
            context_results=context_results,
        )
        store.append(
            {
                "record_type": "failure_attribution",
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "run_id": run_id,
                "recorded_at": utc_now_iso(),
                "failure_attribution": failure,
            }
        )
        record_failure(
            paths,
            failure,
            event=event,
            running=running,
            failed=failed,
            envelope=json.loads(envelope) if envelope else None,
        )
        return {**failed, "failure_attribution": failure}


def make_live_backend(
    *,
    endpoint: str,
    api_key: str,
    max_tokens: int,
):
    from hamutay.taste_open import OpenAITasteBackend

    return OpenAITasteBackend(
        base_url=endpoint,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout=180,
        provider_name="openrouter" if "openrouter" in endpoint else "openai",
        extra_headers={
            "X-Title": f"hamutay/{EXPERIMENT_ID}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        max_retries=1,
    )


def make_session(
    *,
    paths: ProbePaths,
    backend: Any,
    model: str,
    resume: bool,
) -> OpenTasteSession:
    return OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(paths.session_log),
        event_log_path=str(paths.event_log),
        experiment_label=EXPERIMENT_ID,
        system_prompt_prefix=(
            "You are running inside a Hamut'ay event-loop readiness probe. "
            "Return exactly the requested terminal object. Preserve durable "
            "state fields needed for the next wake. Messages are IPC-like "
            "events, not chat turns."
        ),
        memory_base_probability=0,
        enable_tools=False,
        project_root=paths.output_root,
        resume=resume,
    )


def required_success(summary: JsonDict, completed_types: list[str]) -> JsonDict:
    completed_events = [
        event for event in summary.get("events", [])
        if event.get("status") == "completed"
    ]
    completed_tools = [
        str(event.get("terminal_surface_tool"))
        for event in completed_events
    ]
    checks = {
        "completed_three_events": summary.get("status_counts") == {"completed": 3},
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
        "no_outcome_warnings": summary.get("outcome_warnings") == [],
        "mixed_event_types": completed_types
        == ["inbound_message", "self_scheduled_reflection", "housekeeping"],
        "terminal_surface_sequence": completed_tools
        == [
            "handle_inbound_ipc",
            "complete_bound_continuation",
            "complete_housekeeping_audit",
        ],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_types": completed_types,
        "completed_terminal_surface_tools": completed_tools,
    }


def context_error_failures(records: list[JsonDict]) -> list[JsonDict]:
    event_ids = {
        str(record.get("event_id"))
        for record in records
        if record.get("event_id")
    }
    result_record_ids = {
        str(record.get("result_record_id"))
        for record in records
        if record.get("result_record_id")
    }
    failures = []
    for record in records:
        if record.get("record_type") != "event_status":
            continue
        if record.get("status") != "completed":
            continue
        for item in record.get("context_results", []) or []:
            if not isinstance(item, dict):
                continue
            result = item.get("result")
            if not isinstance(result, dict) or "error" not in result:
                continue
            request = item.get("request") if isinstance(item.get("request"), dict) else {}
            requested_record_id = request.get("record_id")
            layer = "scheduler"
            code = "context_resolution_error"
            message = "one or more event context resolutions returned errors"
            if (
                requested_record_id is not None
                and str(requested_record_id) in event_ids
                and str(requested_record_id) not in result_record_ids
            ):
                layer = "model_output"
                code = "model_authored_event_id_as_record_id"
                message = (
                    "model-authored continuation requested an event_id where "
                    "a durable result record_id was required"
                )
            failures.append(
                {
                    "record_type": "probe_postcondition_failure",
                    "recorded_at": utc_now_iso(),
                    "failure_attribution": {
                        "surface": "present",
                        "layer": layer,
                        "code": code,
                        "stage": "postcondition",
                        "error_type": "ProbePostconditionFailed",
                        "error": message,
                    },
                    "evidence": {
                        "event_id": record.get("event_id"),
                        "event_type": record.get("event_type"),
                        "request": request,
                        "result": result,
                    },
                }
            )
    return failures


def postcondition_failures(success: JsonDict) -> list[JsonDict]:
    checks = success.get("checks", {})
    failures = []
    mapping = {
        "completed_three_events": (
            "scheduler",
            "completed_event_count_mismatch",
            "the probe did not complete exactly three event records",
        ),
        "clean_idle": (
            "scheduler",
            "not_clean_idle",
            "the probe finished with runnable pending work",
        ),
        "no_lifecycle_anomalies": (
            "scheduler",
            "lifecycle_anomaly",
            "the event log contains lifecycle anomalies",
        ),
        "no_outcome_warnings": (
            "model_output",
            "outcome_warning",
            "a completed wake produced an outcome warning",
        ),
        "mixed_event_types": (
            "scheduler",
            "event_type_sequence_mismatch",
            "the completed event type sequence did not match the probe contract",
        ),
        "terminal_surface_sequence": (
            "model_output",
            "terminal_surface_sequence_mismatch",
            "the completed terminal surface sequence did not match the probe contract",
        ),
    }
    for check, passed in checks.items():
        if passed:
            continue
        if check not in mapping:
            continue
        layer, code, message = mapping[check]
        failures.append(
            {
                "record_type": "probe_postcondition_failure",
                "recorded_at": utc_now_iso(),
                "failure_attribution": {
                    "surface": "present",
                    "layer": layer,
                    "code": code,
                    "stage": "postcondition",
                    "error_type": "ProbePostconditionFailed",
                    "error": message,
                },
                "evidence": {
                    "check": check,
                    "success": success,
                },
            }
        )
    return failures


def collect_failures(
    paths: ProbePaths,
    records: list[JsonDict],
    success: JsonDict,
) -> list[JsonDict]:
    failures: list[JsonDict] = []
    if paths.failures_log.exists():
        failures.extend(
            json.loads(line)
            for line in paths.failures_log.read_text().splitlines()
            if line.strip()
        )
    for record in records:
        if record.get("record_type") == "failure_attribution":
            failures.append(record)
    failures.extend(context_error_failures(records))
    failures.extend(postcondition_failures(success))
    return failures


def finalize_results(
    *,
    paths: ProbePaths,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
    store: EventStore,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = summarize_event_log(records)
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    success = required_success(summary, completed_types)
    failures = collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.live_sustained_loop_provider_readiness.v1",
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "finished_at": utc_now_iso(),
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model,
        "terminal_tool_choice": terminal_tool_choice,
        "classification": classification,
        "success": success,
        "event_summary": summary,
        "failure_attribution": failures,
        "evidence": {
            "session_log": paths.session_log.name,
            "event_log": paths.event_log.name,
            "attempts_log": paths.attempts_log.name,
            "failures_log": paths.failures_log.name,
            "restart_frontier": paths.frontier_log.name,
            "memory_snapshot": paths.memory_snapshot.name,
            "action_log": paths.action_log.name,
        },
    }
    if extra:
        results.update(extra)
    write_json(paths.output_root / "results.json", results)
    return results


def run_probe(
    *,
    output_root: Path = ROOT_DIR,
    overwrite: bool = False,
    live_model_calls: bool = False,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    terminal_tool_choice: str | None = None,
    backend: Any | None = None,
    run_id: str | None = None,
) -> JsonDict:
    if live_model_calls and not api_key and backend is None:
        raise ValueError("api_key is required for live model calls")
    paths = prepare_output_root(output_root, overwrite=overwrite)
    run_id = run_id or str(uuid4())
    terminal_tool_choice = terminal_tool_choice or default_terminal_tool_choice(endpoint)
    if backend is None:
        if live_model_calls:
            backend = make_live_backend(
                endpoint=endpoint,
                api_key=api_key or "",
                max_tokens=max_tokens,
            )
        else:
            backend = ScriptedTerminalBackend(
                scripted_success_outputs(terminal_tool_choice)
            )

    write_json(
        paths.output_root / "config.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "live_model_calls": live_model_calls,
            "endpoint": endpoint if live_model_calls else None,
            "model": model,
            "max_tokens": max_tokens,
            "terminal_tool_choice": terminal_tool_choice,
        },
    )
    store = EventStore(paths.event_log)
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths.action_log)
    frontier = RestartFrontierStore(
        frontier_path=paths.frontier_log,
        memory_snapshot_path=paths.memory_snapshot,
    )
    frontier.ensure_run_manifest(
        ledger=ledger,
        run_id=run_id,
        manifest={
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "endpoint": endpoint if live_model_calls else None,
            "model": model,
            "terminal_tool_choice": terminal_tool_choice,
        },
        sandbox={"network": "enabled" if live_model_calls else "disabled"},
    )
    session = make_session(
        paths=paths,
        backend=backend,
        model=model,
        resume=False,
    )
    seed_request = {
        "event": "initialize_live_loop_probe",
        "instruction": (
            "Initialize durable state for a live event-loop readiness probe. "
            "Do not start the mixed event stream yet."
        ),
        "required_output": {
            "response": "<brief initialization note>",
            "probe_status": "ready",
            "open_items": [],
        },
    }
    try:
        append_jsonl(
            paths.attempts_log,
            {
                "record_type": "session_seed_attempt",
                "recorded_at": utc_now_iso(),
                "terminal_surface": seed_terminal_surface(
                    tool_choice=terminal_tool_choice
                ),
                "request": seed_request,
            },
        )
        session.exchange(
            json.dumps(seed_request, indent=2, sort_keys=True),
            terminal_surface=seed_terminal_surface(
                tool_choice=terminal_tool_choice
            ),
            force_memory=None,
        )
    except Exception as exc:
        failure = classify_exception(exc, stage="seed_exchange")
        record_failure(paths, failure, request=seed_request)
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "seed_exchange"},
        )
    frontier_failure = commit_frontier(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes={"boundary": "after seed"},
    )
    if isinstance(frontier_failure, dict) and frontier_failure.get("layer"):
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "seed_frontier_commit"},
        )

    inbound_event = append_probe_event(
        store,
        event_type="inbound_message",
        label="inbound-ipc",
        purpose=(
            "Handle inbound IPC message: record that the live loop accepted "
            "work, leave one open item, and request a bound continuation. "
            "The continuation_request must use symbolic_context with source "
            "completed_wake_state. Do not write event_id, record_id, run_id, "
            "requested_context, or terminal_surface inside the continuation; "
            "the framework binds those scheduler-owned fields after this wake. "
            "Return response exactly: inbound IPC accepted."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=inbound_terminal_surface(tool_choice=terminal_tool_choice),
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(session._prior_states[-1][1]),
            }
        ],
    )
    inbound_result = run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=True,
        terminal_tool_choice=terminal_tool_choice,
    )
    if inbound_result.get("status") != "completed":
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "inbound_event"},
        )
    frontier_failure = commit_frontier(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes={"boundary": "after inbound event"},
    )
    if isinstance(frontier_failure, dict) and frontier_failure.get("layer"):
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "inbound_frontier_commit"},
        )

    continuation_event = inbound_result.get("auto_continuation_event")
    binding_failure = inbound_result.get("continuation_binding_failure")
    if isinstance(binding_failure, dict):
        record_failure(
            paths,
            binding_failure,
            event=inbound_event,
            raw_output=inbound_result.get("raw_output"),
        )
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "continuation_binding"},
        )
    if not isinstance(continuation_event, dict):
        failure = model_output_failure(
            code="missing_continuation_request",
            stage="inbound_event",
            message="inbound event completed without a continuation_request",
        )
        record_failure(paths, failure, event=inbound_event, result=inbound_result)
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "inbound_continuation_check"},
        )

    continuation_result = run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if continuation_result.get("status") != "completed":
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "continuation_event"},
        )
    frontier_failure = commit_frontier(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes={"boundary": "after bound continuation"},
    )
    if isinstance(frontier_failure, dict) and frontier_failure.get("layer"):
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "continuation_frontier_commit"},
        )

    append_probe_event(
        store,
        event_type="housekeeping",
        label="housekeeping-restart",
        purpose=(
            "Run a terse housekeeping audit after restart recovery. If the "
            "recalled state has no open items, return response exactly "
            "'housekeeping audit clean', open_items as [], and "
            "housekeeping_audit.status as clean."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=housekeeping_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(session._prior_states[-1][1]),
            }
        ],
    )
    claimed = store.claim_next_pending(run_id=UUID(run_id))
    if claimed is None:
        failure = model_output_failure(
            code="missing_housekeeping_claim",
            stage="housekeeping_claim",
            message="housekeeping event could not be claimed for restart test",
        )
        record_failure(paths, failure)
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "housekeeping_claim"},
        )

    resumed_memory = LocalMemorySubstrate()
    resumed_ledger = ActionLedger(paths.action_log)
    resumed_frontier = RestartFrontierStore(
        frontier_path=paths.frontier_log,
        memory_snapshot_path=paths.memory_snapshot,
    )
    try:
        load = resumed_frontier.load_latest(
            run_id=run_id,
            memory=resumed_memory,
            ledger=resumed_ledger,
            event_store=store,
        )
    except Exception as exc:
        failure = classify_exception(exc, stage="frontier_load")
        record_failure(paths, failure, claimed=claimed)
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "frontier_load"},
        )
    if len(load.recovered_event_records) != 1:
        failure = model_output_failure(
            code="restart_recovered_event_count_mismatch",
            stage="frontier_load",
            message=(
                "restart frontier did not recover exactly one claimed "
                "housekeeping event"
            ),
        )
        record_failure(
            paths,
            failure,
            recovered_event_records=load.recovered_event_records,
            suppressed_event_records=load.suppressed_event_records,
        )
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "frontier_recovery_check"},
        )

    try:
        resumed = make_session(
            paths=paths,
            backend=backend,
            model=model,
            resume=True,
        )
    except Exception as exc:
        failure = classify_exception(exc, stage="resume")
        record_failure(paths, failure)
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "session_resume"},
        )

    housekeeping_result = run_attributed_event(
        session=resumed,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if housekeeping_result.get("status") == "completed":
        commit_frontier(
            paths=paths,
            frontier=resumed_frontier,
            memory=resumed_memory,
            ledger=resumed_ledger,
            store=store,
            session=resumed,
            run_id=run_id,
            notes={"boundary": "after recovered housekeeping"},
        )

    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--terminal-tool-choice",
        choices=["auto", "required", "force"],
        default=None,
    )
    args = parser.parse_args(argv)
    api_key = os.environ.get(args.api_key_env) if args.live else None
    results = run_probe(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=api_key,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        terminal_tool_choice=args.terminal_tool_choice,
    )
    print(json.dumps(results, indent=2, sort_keys=True, default=str))
    return 0 if results["classification"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
