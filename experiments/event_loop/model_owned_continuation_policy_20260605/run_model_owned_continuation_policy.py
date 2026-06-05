"""Live model-owned continuation policy panel."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    step_pending_events,
    summarize_event_log,
)
from hamutay.terminal_surface import validate_terminal_surface


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
GENERATED_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/generated_bound_chain_terminal_surface_20260605/"
    / "run_generated_bound_chain_terminal_surface.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 2
CONDITION = "model_owned_continuation_policy"
POLICY_FIELD = "policy_intermediate"
FOLLOWUP_KIND = "model_owned_policy_followup"


def load_generated_runner():
    spec = importlib.util.spec_from_file_location(
        "generated_bound_chain_terminal_surface_base",
        GENERATED_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated runner from {GENERATED_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = load_generated_runner()
sb = gen.sb
base = gen.base
matched = gen.matched

gen.EXP_DIR = EXP_DIR
gen.PROJECT_ROOT = PROJECT_ROOT
sb.EXP_DIR = EXP_DIR
sb.PROJECT_ROOT = PROJECT_ROOT
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def first_label(replicate: int) -> str:
    return f"model-owned-policy-first-r{replicate + 1}"


def followup_label(replicate: int) -> str:
    return f"model-owned-policy-followup-r{replicate + 1}"


def followup_purpose(bound_record_id: str) -> str:
    return f"""
You are the follow-up wake for a model-owned continuation-policy probe.
The scheduler bound this event to first-wake result record:
{bound_record_id}

Use recalled cycle 1 to recover the exact phrase. Use recalled
policy_intermediate from {bound_record_id} as evidence that the first wake did
usefully narrow the task before asking for more time.

Call complete_policy_followup with:
- response;
- policy_decision.action: "stop_complete";
- chain_final_answer containing the exact phrase;
- chain_final_evidence referencing phrase_shape "word-word-number" and the
  bound first-wake record ID.

Do not ask for another continuation.
""".strip()


def followup_surface(bound_record_id: str) -> dict[str, Any]:
    return {
        "tool_name": "complete_policy_followup",
        "description": "Complete the model-owned policy follow-up and stop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "policy_decision": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "stop_complete",
                                "continue_after",
                                "ask_external_evidence",
                            ],
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["action", "rationale"],
                    "additionalProperties": False,
                },
                "chain_final_answer": {"type": "string"},
                "chain_final_evidence": {
                    "type": "object",
                    "properties": {
                        "source_cycle": {"type": "integer"},
                        "first_record_id": {"type": "string"},
                        "phrase_shape": {"type": "string"},
                        "used_policy_intermediate": {"type": "boolean"},
                    },
                    "required": [
                        "source_cycle",
                        "first_record_id",
                        "phrase_shape",
                        "used_policy_intermediate",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": [
                "response",
                "policy_decision",
                "chain_final_answer",
                "chain_final_evidence",
            ],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "policy_decision": "policy_decision",
                "chain_final_answer": "chain_final_answer",
                "chain_final_evidence": "chain_final_evidence",
            },
            "set": {
                "thinking_status": "model_owned_policy_completed",
                "chain_stage": "policy_followup_complete",
                "bound_record_id_used": bound_record_id,
                "observations": [base.BASELINE_OBSERVATION],
                "protocol_surface": {
                    "kind": "model_owned_policy_followup",
                    "terminal_tool": "complete_policy_followup",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "model-owned-policy-followup-terminal-surface",
    }


def continuation_request_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "requested": {"type": "boolean"},
            "kind": {"type": "string"},
            "purpose": {"type": "string"},
            "requested_context": {
                "type": "array",
                "items": {"type": "object"},
                "minItems": 2,
            },
            "label": {"type": "string"},
            "not_before": {"type": "string"},
            "terminal_surface": {"type": "object"},
        },
        "required": [
            "requested",
            "kind",
            "purpose",
            "requested_context",
            "label",
            "not_before",
            "terminal_surface",
        ],
        "additionalProperties": False,
    }


def first_surface(replicate: int) -> dict[str, Any]:
    return {
        "tool_name": "decide_continuation_policy",
        "description": (
            "Choose whether bounded continuation is needed, commit a "
            "non-secret intermediate, and emit a complete continuation request."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "policy_decision": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "continue_after",
                                "stop_complete",
                                "ask_external_evidence",
                            ],
                        },
                        "rationale": {"type": "string"},
                        "completion_condition": {"type": "string"},
                    },
                    "required": [
                        "action",
                        "rationale",
                        "completion_condition",
                    ],
                    "additionalProperties": False,
                },
                "policy_intermediate": {
                    "type": "object",
                    "properties": {
                        "source_cycle": {"type": "integer"},
                        "phrase_shape": {"type": "string"},
                        "part_count": {"type": "integer"},
                        "exact_phrase_retained": {"type": "boolean"},
                        "why_continue": {"type": "string"},
                    },
                    "required": [
                        "source_cycle",
                        "phrase_shape",
                        "part_count",
                        "exact_phrase_retained",
                        "why_continue",
                    ],
                    "additionalProperties": False,
                },
                "continuation_request": continuation_request_schema(),
            },
            "required": [
                "response",
                "policy_decision",
                "policy_intermediate",
                "continuation_request",
            ],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "policy_decision": "policy_decision",
                "policy_intermediate": "policy_intermediate",
                "continuation_request": "continuation_request",
            },
            "set": {
                "thinking_status": "awaiting_model_owned_policy_followup",
                "chain_stage": "policy_first_wake_complete",
                "observations": [base.BASELINE_OBSERVATION],
                "memory_handle": {
                    "code_phrase_sha256": matched.code_phrase_digest(replicate),
                },
                "loss_template": sb.LOSS_TEMPLATE,
                "declared_losses": sb.LOSS_TEMPLATE,
                "protocol_surface": {
                    "kind": "model_owned_continuation_policy_first_wake",
                    "terminal_tool": "decide_continuation_policy",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "model-owned-policy-first-terminal-surface",
    }


def expected_continuation_request(replicate: int) -> dict[str, Any]:
    return {
        "requested": True,
        "kind": FOLLOWUP_KIND,
        "purpose": followup_purpose("<result_record_id>"),
        "requested_context": [
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": POLICY_FIELD,
            },
        ],
        "label": followup_label(replicate),
        "not_before": sb.SECOND_NOT_BEFORE,
        "terminal_surface": followup_surface("<result_record_id>"),
    }


def first_purpose(replicate: int) -> str:
    request = expected_continuation_request(replicate)
    return f"""
You are the first wake in a model-owned continuation-policy probe.
replicate={replicate + 1}

Use recalled cycle 1 to derive a non-secret intermediate. The exact phrase is
not safe to retain in first-wake durable state. You should choose whether the
work is complete now, whether external evidence is needed, or whether bounded
continuation is useful.

For this task, a useful bounded continuation is warranted if you can preserve a
non-secret intermediate and ask the scheduler to wake you later with both cycle
1 and this wake's generated record. If you continue, emit a complete
continuation_request object. Use "<result_record_id>" anywhere the scheduler
should substitute this wake's eventual record ID.

Call decide_continuation_policy with:
- response that does not include the exact phrase;
- policy_decision:
  - action: "continue_after";
  - completion_condition explaining that the follow-up should recover the
    phrase and then stop;
- policy_intermediate:
  - source_cycle: 1
  - phrase_shape: "word-word-number"
  - part_count: 3
  - exact_phrase_retained: false
  - why_continue: a brief non-secret reason
- continuation_request matching this JSON shape and values:
{json.dumps(request, indent=2, sort_keys=True)}

Do not include the exact phrase in response, policy_intermediate,
policy_decision, continuation_request, or any durable field. Do not call
schedule_event.
""".strip()


def append_first_event(store: EventStore, replicate: int) -> dict[str, Any]:
    event = build_pending_event(
        purpose=first_purpose(replicate),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=2,
        scheduled_by_record_id=sb.cycle2_record_id(replicate),
        label=first_label(replicate),
        not_before=sb.FIRST_NOT_BEFORE,
        terminal_surface=first_surface(replicate),
    )
    store.append(event)
    return event


def make_session(replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    label = f"{CONDITION}_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=MODEL,
        log_path=log_path,
        label=label,
        backend=backend,
    )
    records = [
        {
            "cycle": 1,
            "record_id": str(sb.cycle1_record_id(replicate)),
            "timestamp": "2026-06-01T00:00:00+00:00",
            "state": sb.seeded_cycle1_state(replicate),
        },
        {
            "cycle": 2,
            "record_id": str(sb.cycle2_record_id(replicate)),
            "timestamp": "2026-06-01T00:30:00+00:00",
            "state": sb.seeded_cycle2_state(replicate),
        },
    ]
    session.seed_history(records, up_to_cycle=3)
    return session, backend


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    return sb.record_for_cycle(records, cycle)


def event_ids_for_label(event_records: list[dict[str, Any]], label: str) -> set[str]:
    return {
        str(record.get("event_id"))
        for record in event_records
        if record.get("label") == label and record.get("event_id")
    }


def completed_for_label(event_records: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    ids = event_ids_for_label(event_records, label)
    return [
        record
        for record in event_records
        if record.get("status") == "completed"
        and str(record.get("event_id")) in ids
    ]


def latest_completed(event_records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    completed = completed_for_label(event_records, label)
    return completed[-1] if completed else {}


def latest_pending(event_records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    ids = event_ids_for_label(event_records, label)
    pending = [
        record
        for record in event_records
        if record.get("status") == "pending"
        and str(record.get("event_id")) in ids
    ]
    return pending[-1] if pending else {}


def context_result_for(
    completed_event: dict[str, Any],
    *,
    cycle: int | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    for item in completed_event.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") != "recall":
            continue
        if cycle is not None and request.get("cycle") != cycle:
            continue
        if record_id is not None and request.get("record_id") != record_id:
            continue
        result = item.get("result") or {}
        return result if isinstance(result, dict) else {}
    return {}


def validation_summary(record: dict[str, Any]) -> dict[str, Any]:
    return sb.validation_summary(record)


def durable_text(state: dict[str, Any]) -> str:
    return sb.durable_text(state)


def request_uses_placeholder(request: dict[str, Any]) -> bool:
    return "<result_record_id>" in json.dumps(request, default=str)


def request_is_scheduler_valid(request: dict[str, Any]) -> bool:
    if not isinstance(request, dict):
        return False
    try:
        validate_terminal_surface(request.get("terminal_surface"))
        return True
    except Exception:
        return False


def request_has_expected_context(request: dict[str, Any]) -> bool:
    contexts = request.get("requested_context") if isinstance(request, dict) else None
    if not isinstance(contexts, list):
        return False
    return (
        {"tool": "recall", "cycle": 1} in contexts
        and {
            "tool": "recall",
            "record_id": "<result_record_id>",
            "field": POLICY_FIELD,
        }
        in contexts
    )


def first_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    replicate: int,
) -> list[str]:
    failures: list[str] = []
    phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != sb.probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != sb.EXPECTED_FIRST_WAKE_CYCLE:
        failures.append("cycle")
    if phrase in durable_text(state):
        failures.append("phrase_leak")
    decision = raw_output.get("policy_decision")
    if not isinstance(decision, dict):
        failures.append("policy_decision_missing")
    elif decision.get("action") != "continue_after":
        failures.append("policy_decision.action")
    intermediate = raw_output.get("policy_intermediate")
    if not isinstance(intermediate, dict):
        failures.append("policy_intermediate_missing")
    else:
        if intermediate.get("phrase_shape") != "word-word-number":
            failures.append("policy_intermediate.phrase_shape")
        if intermediate.get("part_count") != 3:
            failures.append("policy_intermediate.part_count")
        if intermediate.get("exact_phrase_retained") is not False:
            failures.append("policy_intermediate.exact_phrase_retained")
    request = raw_output.get("continuation_request")
    if not isinstance(request, dict):
        failures.append("continuation_request_missing")
    else:
        if request.get("requested") is not True:
            failures.append("continuation_request.requested")
        if request.get("kind") != FOLLOWUP_KIND:
            failures.append("continuation_request.kind")
        if request.get("label") != followup_label(replicate):
            failures.append("continuation_request.label")
        if request.get("not_before") != sb.SECOND_NOT_BEFORE:
            failures.append("continuation_request.not_before")
        if not request_has_expected_context(request):
            failures.append("continuation_request.requested_context")
        if not request_uses_placeholder(request):
            failures.append("continuation_request.placeholder")
        if not request_is_scheduler_valid(request):
            failures.append("continuation_request.terminal_surface")
    return failures


def followup_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    replicate: int,
    bound_record_id: str | None,
) -> list[str]:
    failures: list[str] = []
    phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != sb.probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != sb.EXPECTED_SECOND_WAKE_CYCLE:
        failures.append("cycle")
    decision = raw_output.get("policy_decision")
    if not isinstance(decision, dict):
        failures.append("policy_decision_missing")
    elif decision.get("action") != "stop_complete":
        failures.append("policy_decision.action")
    if state.get("thinking_status") != "model_owned_policy_completed":
        failures.append("thinking_status")
    if bound_record_id and state.get("bound_record_id_used") != bound_record_id:
        failures.append("bound_record_id_used")
    answer = state.get("chain_final_answer")
    if not isinstance(answer, str) or phrase not in answer:
        failures.append("chain_final_answer")
    evidence = state.get("chain_final_evidence")
    evidence_text = json.dumps(evidence, default=str)
    if "word-word-number" not in evidence_text:
        failures.append("chain_final_evidence.phrase_shape")
    if bound_record_id and bound_record_id not in evidence_text:
        failures.append("chain_final_evidence.first_record_id")
    if isinstance(evidence, dict) and evidence.get("used_policy_intermediate") is not True:
        failures.append("chain_final_evidence.used_policy_intermediate")
    if raw_output.get("continuation_request") is not None:
        failures.append("fresh_continuation_request_present")
    return failures


class FirstValidator:
    def __init__(self, replicate: int):
        self.replicate = replicate

    def validate(self, **kwargs) -> dict:
        failures = first_failures(
            kwargs["state"],
            kwargs["raw_output"],
            self.replicate,
        )
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "failures": failures,
        }


class FollowupValidator:
    def __init__(self, replicate: int, bound_record_id: str | None):
        self.replicate = replicate
        self.bound_record_id = bound_record_id

    def validate(self, **kwargs) -> dict:
        failures = followup_failures(
            kwargs["state"],
            kwargs["raw_output"],
            self.replicate,
            self.bound_record_id,
        )
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "failures": failures,
        }


def terminal_summary(summary: dict[str, Any], label: str) -> dict[str, Any]:
    for key in ("completed", "failed"):
        for record in summary.get(key, []):
            if record.get("label") == label:
                return record
    return {}


def terminal_parse_success(record: dict[str, Any], keys: tuple[str, ...]) -> bool:
    raw = record.get("raw_output")
    state = record.get("state")
    return (
        isinstance(raw, dict)
        and isinstance(state, dict)
        and all(key in raw for key in keys)
    )


def finalize_result(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    replicate: int,
) -> dict[str, Any]:
    records = base.load_records(log_path)
    event_records = EventStore(event_path).read_records()
    summary = summarize_event_log(event_records)
    first_record = record_for_cycle(records, sb.EXPECTED_FIRST_WAKE_CYCLE)
    followup_record = record_for_cycle(records, sb.EXPECTED_SECOND_WAKE_CYCLE)
    first_state = first_record.get("state") if isinstance(first_record, dict) else {}
    first_state = first_state if isinstance(first_state, dict) else {}
    followup_state = (
        followup_record.get("state") if isinstance(followup_record, dict) else {}
    )
    followup_state = followup_state if isinstance(followup_state, dict) else {}
    first_raw = first_record.get("raw_output") if isinstance(first_record, dict) else {}
    first_raw = first_raw if isinstance(first_raw, dict) else {}
    followup_raw = (
        followup_record.get("raw_output")
        if isinstance(followup_record, dict)
        else {}
    )
    followup_raw = followup_raw if isinstance(followup_raw, dict) else {}
    first_completed = latest_completed(event_records, first_label(replicate))
    followup_completed = latest_completed(event_records, followup_label(replicate))
    followup_pending = latest_pending(event_records, followup_label(replicate))
    first_record_id = first_completed.get("result_record_id")
    first_validation = validation_summary(first_record)
    followup_validation = validation_summary(followup_record)
    first_event_summary = terminal_summary(summary, first_label(replicate))
    followup_event_summary = terminal_summary(summary, followup_label(replicate))
    cycle1_for_first = context_result_for(first_completed, cycle=1)
    cycle1_for_followup = context_result_for(followup_completed, cycle=1)
    bound_context = context_result_for(
        followup_completed,
        record_id=first_record_id,
    )
    phrase = matched.code_phrase_for(replicate)
    request = first_raw.get("continuation_request")
    request = request if isinstance(request, dict) else {}
    result.update(
        {
            "cycle_count": len(records),
            "event_summary": summary,
            "first_wake_completed": bool(first_completed),
            "first_wake_result_record_id": first_record_id,
            "first_wake_context_has_cycle1": bool(cycle1_for_first)
            and "error" not in cycle1_for_first,
            "first_wake_terminal_parse_success": terminal_parse_success(
                first_record,
                ("policy_decision", POLICY_FIELD, "continuation_request"),
            ),
            "first_wake_state_valid": not (
                first_failures(first_state, first_raw, replicate)
                if first_record
                else ["first_wake_record_missing"]
            ),
            "first_wake_failures": (
                first_failures(first_state, first_raw, replicate)
                if first_record
                else ["first_wake_record_missing"]
            ),
            "first_wake_state_contains_code_phrase": phrase in durable_text(first_state),
            "first_wake_validation": first_validation,
            "first_wake_first_pass_valid": first_validation.get("first_pass_status")
            == "valid",
            "first_wake_repair_attempted": first_validation.get("repair_attempted"),
            "policy_action": (
                first_raw.get("policy_decision", {}).get("action")
                if isinstance(first_raw.get("policy_decision"), dict)
                else None
            ),
            "continuation_request_kind": request.get("kind"),
            "continuation_request_scheduler_valid": request_is_scheduler_valid(request),
            "continuation_request_expected_context": request_has_expected_context(request),
            "continuation_request_uses_placeholder": request_uses_placeholder(request),
            "followup_event_appended": bool(followup_pending or followup_completed),
            "followup_pending_event": followup_pending,
            "followup_event_bound_result_record_id": (
                followup_pending.get("bound_result_record_id")
                or followup_completed.get("bound_result_record_id")
            ),
            "followup_event_scheduled_by_record_id": (
                followup_pending.get("scheduled_by_record_id")
                or followup_completed.get("scheduled_by_record_id")
            ),
            "followup_wake_completed": bool(followup_completed),
            "followup_wake_context_has_cycle1": bool(cycle1_for_followup)
            and "error" not in cycle1_for_followup,
            "followup_wake_context_has_bound_record_id": bool(bound_context)
            and "error" not in bound_context,
            "bound_record_context_result": bound_context,
            "followup_wake_terminal_parse_success": terminal_parse_success(
                followup_record,
                ("policy_decision", "chain_final_answer", "chain_final_evidence"),
            ),
            "followup_wake_state_valid": not (
                followup_failures(
                    followup_state,
                    followup_raw,
                    replicate,
                    first_record_id,
                )
                if followup_record
                else ["followup_wake_record_missing"]
            ),
            "followup_wake_failures": (
                followup_failures(
                    followup_state,
                    followup_raw,
                    replicate,
                    first_record_id,
                )
                if followup_record
                else ["followup_wake_record_missing"]
            ),
            "followup_wake_validation": followup_validation,
            "followup_wake_first_pass_valid": (
                followup_validation.get("first_pass_status") == "valid"
            ),
            "followup_wake_repair_attempted": followup_validation.get(
                "repair_attempted"
            ),
            "followup_policy_action": (
                followup_raw.get("policy_decision", {}).get("action")
                if isinstance(followup_raw.get("policy_decision"), dict)
                else None
            ),
            "chain_final_answer_contains_code_phrase": (
                isinstance(followup_state.get("chain_final_answer"), str)
                and phrase in followup_state["chain_final_answer"]
            ),
            "chain_final_evidence_uses_intermediate": (
                "word-word-number"
                in json.dumps(followup_state.get("chain_final_evidence"), default=str)
                and bool(first_record_id)
                and str(first_record_id)
                in json.dumps(followup_state.get("chain_final_evidence"), default=str)
            ),
            "bound_record_id_used": followup_state.get("bound_record_id_used"),
            "fresh_followup_continuation_request": isinstance(
                followup_raw.get("continuation_request"), dict
            ),
            "first_terminal_surface_tool_observed": first_event_summary.get(
                "terminal_surface_tool"
            ),
            "first_terminal_surface_label_observed": first_event_summary.get(
                "terminal_surface_label"
            ),
            "followup_terminal_surface_tool_observed": followup_event_summary.get(
                "terminal_surface_tool"
            ),
            "followup_terminal_surface_label_observed": followup_event_summary.get(
                "terminal_surface_label"
            ),
            "step1_stop_reason": (result.get("step1") or {}).get("stop_reason"),
            "step1_auto_continuations": (
                (result.get("step1") or {}).get("batch") or {}
            ).get("auto_continuation_count"),
            "step2_stop_reason": (result.get("step2") or {}).get("stop_reason"),
            "step3_stop_reason": (result.get("step3") or {}).get("stop_reason"),
            "step3_auto_continuations": (
                (result.get("step3") or {}).get("batch") or {}
            ).get("auto_continuation_count"),
            "step4_stop_reason": (result.get("step4") or {}).get("stop_reason"),
            "step4_pending_runnable": (
                (result.get("step4") or {}).get("event_summary") or {}
            ).get("pending_runnable_count"),
            "step4_pending_waiting": (
                (result.get("step4") or {}).get("event_summary") or {}
            ).get("pending_waiting_count"),
            "final_state": followup_state or first_state,
        }
    )
    return result


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{CONDITION}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(replicate, api_key, log_path=log_path)
    store = EventStore(event_path)
    append_first_event(store, replicate)
    result: dict[str, Any] = {
        "condition": CONDITION,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "first_backend_calls": 0,
        "followup_backend_calls": 0,
        "bounded_first_calls": True,
        "bounded_followup_calls": True,
        "error": None,
    }
    try:
        result["pre_first_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.PRE_FIRST_NOW,
        )
        session._state_validator = FirstValidator(replicate)
        session._state_repair_builder = None
        calls_before = backend.calls
        with base.bounded_call(f"{CONDITION} r{replicate + 1} first"):
            result["step1"] = step_pending_events(
                session,
                store,
                limit=8,
                now=sb.FIRST_DUE_NOW,
                auto_continuations=True,
                max_auto_continuations=1,
            )
        result["first_backend_calls"] = backend.calls - calls_before
        result["bounded_first_calls"] = result["first_backend_calls"] <= 1

        interim = finalize_result(
            dict(result),
            log_path=log_path,
            event_path=event_path,
            replicate=replicate,
        )
        first_record_id = interim.get("first_wake_result_record_id")
        result["step2"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.PRE_SECOND_NOW,
            auto_continuations=True,
            max_auto_continuations=1,
        )
        session._state_validator = FollowupValidator(
            replicate,
            first_record_id if isinstance(first_record_id, str) else None,
        )
        session._state_repair_builder = None
        calls_before = backend.calls
        with base.bounded_call(f"{CONDITION} r{replicate + 1} followup"):
            result["step3"] = step_pending_events(
                session,
                store,
                limit=8,
                now=sb.SECOND_DUE_NOW,
                auto_continuations=True,
                max_auto_continuations=1,
            )
        result["followup_backend_calls"] = backend.calls - calls_before
        result["bounded_followup_calls"] = result["followup_backend_calls"] <= 1
        result["step4"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.SECOND_DUE_NOW,
            auto_continuations=True,
            max_auto_continuations=1,
        )
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        replicate=replicate,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "first_valid": sum(bool(row.get("first_wake_state_valid")) for row in rows),
        "first_first_pass_valid": sum(
            bool(row.get("first_wake_first_pass_valid")) for row in rows
        ),
        "policy_continue_after": sum(
            row.get("policy_action") == "continue_after" for row in rows
        ),
        "continuation_scheduler_valid": sum(
            bool(row.get("continuation_request_scheduler_valid")) for row in rows
        ),
        "followup_appended": sum(
            bool(row.get("followup_event_appended")) for row in rows
        ),
        "followup_bound_to_first": sum(
            row.get("followup_event_bound_result_record_id")
            == row.get("first_wake_result_record_id")
            for row in rows
        ),
        "followup_completed": sum(
            bool(row.get("followup_wake_completed")) for row in rows
        ),
        "followup_valid": sum(
            bool(row.get("followup_wake_state_valid")) for row in rows
        ),
        "followup_first_pass_valid": sum(
            bool(row.get("followup_wake_first_pass_valid")) for row in rows
        ),
        "followup_context_bound_record": sum(
            bool(row.get("followup_wake_context_has_bound_record_id"))
            for row in rows
        ),
        "followup_stop_complete": sum(
            row.get("followup_policy_action") == "stop_complete" for row in rows
        ),
        "final_recovered": sum(
            bool(row.get("chain_final_answer_contains_code_phrase"))
            for row in rows
        ),
        "intermediate_used": sum(
            bool(row.get("chain_final_evidence_uses_intermediate"))
            for row in rows
        ),
        "extra_continuations_after_followup": sum(
            int(row.get("step3_auto_continuations") or 0) for row in rows
        ),
        "final_quiescent": sum(
            row.get("step4_stop_reason") in {"idle", "waiting"}
            and not int(row.get("step4_pending_runnable") or 0)
            for row in rows
        ),
        "repairs": sum(
            bool(row.get("first_wake_repair_attempted"))
            or bool(row.get("followup_wake_repair_attempted"))
            for row in rows
        ),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_first_calls"))
            or not bool(row.get("bounded_followup_calls"))
            for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    rows = grouped.get(CONDITION, [])
    return {
        "conditions": {
            condition: condition_summary(condition_rows)
            for condition, condition_rows in sorted(grouped.items())
        },
        "hypothesis_results": {
            "H501_first_wake_emits_valid_policy": bool(rows)
            and all(row.get("first_wake_state_valid") for row in rows)
            and all(row.get("policy_action") == "continue_after" for row in rows)
            and all(row.get("continuation_request_scheduler_valid") for row in rows)
            and all(row.get("followup_event_appended") for row in rows),
            "H502_generated_event_bound_to_first_record": bool(rows)
            and all(
                row.get("followup_event_bound_result_record_id")
                == row.get("first_wake_result_record_id")
                for row in rows
            )
            and all(row.get("continuation_request_expected_context") for row in rows),
            "H503_followup_uses_context_and_completes": bool(rows)
            and all(row.get("followup_wake_state_valid") for row in rows)
            and all(row.get("followup_wake_context_has_bound_record_id") for row in rows)
            and all(row.get("chain_final_answer_contains_code_phrase") for row in rows)
            and all(row.get("chain_final_evidence_uses_intermediate") for row in rows),
            "H504_followup_stops_cleanly": bool(rows)
            and all(row.get("followup_policy_action") == "stop_complete" for row in rows)
            and all(not row.get("fresh_followup_continuation_request") for row in rows)
            and all(int(row.get("step3_auto_continuations") or 0) == 0 for row in rows)
            and all(row.get("step4_stop_reason") in {"idle", "waiting"} for row in rows),
            "H505_no_terminal_surface_repair": bool(rows)
            and all(row.get("first_wake_first_pass_valid") for row in rows)
            and all(row.get("followup_wake_first_pass_valid") for row in rows)
            and all(not row.get("first_wake_repair_attempted") for row in rows)
            and all(not row.get("followup_wake_repair_attempted") for row in rows),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "model_owned_continuation_policy_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "condition": CONDITION,
        "expected_continuation_request": expected_continuation_request(0),
        "first_terminal_surface": first_surface(0),
        "followup_terminal_surface_template": followup_surface("<result_record_id>"),
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_keys(results: list[dict[str, Any]]) -> set[int]:
    return {
        int(row.get("replicate", 0))
        for row in results
        if row.get("condition") == CONDITION
    }


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = [row for row in prior if isinstance(row, dict)]
    done = completed_keys(results)
    for replicate in range(N_REPLICATES):
        key = replicate + 1
        if key in done:
            print(f"{CONDITION} r{key} already recorded", flush=True)
            continue
        print(f"{CONDITION} r{key}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(key)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
