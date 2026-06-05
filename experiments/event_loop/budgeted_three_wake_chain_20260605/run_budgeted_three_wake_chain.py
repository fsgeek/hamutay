"""Live budgeted three-wake generated continuation chain."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    step_pending_events,
    summarize_event_log,
)


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
GEN_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/generated_chain_auto_continuation_20260605/"
    / "run_generated_chain_auto_continuation.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 2
CONDITION = "budgeted_three_wake_chain"
BOUND_FIELD = "chain_intermediate"
BRIDGE_FIELD = "chain_bridge"
BRIDGE_NOT_BEFORE = "2026-06-01T02:00:00+00:00"
FINAL_NOT_BEFORE = "2026-06-01T03:00:00+00:00"
PRE_BRIDGE_NOW = datetime(2026, 6, 1, 1, 30, tzinfo=timezone.utc)
BRIDGE_DUE_NOW = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
PRE_FINAL_NOW = datetime(2026, 6, 1, 2, 30, tzinfo=timezone.utc)
FINAL_DUE_NOW = datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc)
EXPECTED_FIRST_CYCLE = 3
EXPECTED_BRIDGE_CYCLE = 4
EXPECTED_FINAL_CYCLE = 5


def load_generated_runner():
    spec = importlib.util.spec_from_file_location(
        "generated_chain_auto_continuation_base",
        GEN_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated runner from {GEN_RUNNER_PATH}")
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
    return f"budgeted-three-wake-first-r{replicate + 1}"


def bridge_label(replicate: int) -> str:
    return f"budgeted-three-wake-bridge-r{replicate + 1}"


def final_label(replicate: int) -> str:
    return f"budgeted-three-wake-final-r{replicate + 1}"


def bridge_purpose(bound_record_id: str) -> str:
    return f"""
You are the bridge wake in the budgeted three-wake chain. The substrate bound
this event to first-wake result record:
{bound_record_id}

Use recalled cycle 1 and the recalled chain_intermediate field from
{bound_record_id}. Call complete_bridge_wake with:
- response;
- chain_bridge summarizing that the first wake produced phrase_shape
  "word-word-number" and did not retain the exact phrase.

Do not include the exact phrase in chain_bridge. Do not schedule events.
""".strip()


def final_purpose(bound_record_id: str) -> str:
    return f"""
You are the final wake in the budgeted three-wake chain. The substrate bound
this event to bridge-wake result record:
{bound_record_id}

Use recalled cycle 1 to recover the exact phrase. Use recalled chain_bridge
from {bound_record_id} as the generated intermediate evidence.

Call complete_final_wake with:
- response;
- chain_final_answer containing the exact phrase;
- chain_final_evidence referencing phrase_shape "word-word-number" and the
  bridge record.

Do not request another continuation and do not schedule events.
""".strip()


def final_surface(bound_record_id: str) -> dict[str, Any]:
    return {
        "tool_name": "complete_final_wake",
        "description": "Complete the budgeted three-wake chain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "chain_final_answer": {"type": "string"},
                "chain_final_evidence": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
            "required": [
                "response",
                "chain_final_answer",
                "chain_final_evidence",
            ],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "chain_final_answer": "chain_final_answer",
                "chain_final_evidence": "chain_final_evidence",
            },
            "set": {
                "thinking_status": "budgeted_chain_completed",
                "chain_stage": "final_wake_complete",
                "bound_bridge_record_id_used": bound_record_id,
                "observations": [base.BASELINE_OBSERVATION],
                "protocol_surface": {
                    "kind": "budgeted_final_wake",
                    "terminal_tool": "complete_final_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "budgeted-final-wake-terminal-surface",
    }


def final_continuation_template(replicate: int) -> dict[str, Any]:
    return {
        "requested": True,
        "kind": "budgeted_final_wake",
        "purpose": final_purpose("<result_record_id>"),
        "requested_context": [
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": BRIDGE_FIELD,
            },
        ],
        "label": final_label(replicate),
        "not_before": FINAL_NOT_BEFORE,
        "terminal_surface": final_surface("<result_record_id>"),
    }


def bridge_surface(replicate: int, bound_record_id: str) -> dict[str, Any]:
    return {
        "tool_name": "complete_bridge_wake",
        "description": "Commit bridge evidence and request final continuation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "chain_bridge": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
            "required": ["response", "chain_bridge"],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {"chain_bridge": "chain_bridge"},
            "set": {
                "thinking_status": "awaiting_final_continuation",
                "chain_stage": "bridge_wake_complete",
                "bound_first_record_id_used": bound_record_id,
                "continuation_request": final_continuation_template(replicate),
                "observations": [base.BASELINE_OBSERVATION],
                "protocol_surface": {
                    "kind": "budgeted_bridge_wake",
                    "terminal_tool": "complete_bridge_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "budgeted-bridge-wake-terminal-surface",
    }


def bridge_continuation_template(replicate: int) -> dict[str, Any]:
    return {
        "requested": True,
        "kind": "budgeted_bridge_wake",
        "purpose": bridge_purpose("<result_record_id>"),
        "requested_context": [
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": BOUND_FIELD,
            },
        ],
        "label": bridge_label(replicate),
        "not_before": BRIDGE_NOT_BEFORE,
        "terminal_surface": bridge_surface(replicate, "<result_record_id>"),
    }


def first_surface(replicate: int) -> dict[str, Any]:
    return {
        "tool_name": "complete_first_wake",
        "description": "Commit first non-secret intermediate and request bridge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "chain_intermediate": {
                    "type": "object",
                    "properties": {
                        "source_cycle": {"type": "integer"},
                        "phrase_shape": {"type": "string"},
                        "part_count": {"type": "integer"},
                        "exact_phrase_retained": {"type": "boolean"},
                    },
                    "required": [
                        "source_cycle",
                        "phrase_shape",
                        "part_count",
                        "exact_phrase_retained",
                    ],
                    "additionalProperties": True,
                },
            },
            "required": ["response", "chain_intermediate"],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {"chain_intermediate": "chain_intermediate"},
            "set": {
                "thinking_status": "awaiting_bridge_continuation",
                "chain_stage": "first_wake_complete",
                "continuation_request": bridge_continuation_template(replicate),
                "observations": [base.BASELINE_OBSERVATION],
                "memory_handle": {
                    "code_phrase_sha256": matched.code_phrase_digest(replicate),
                },
                "loss_template": sb.LOSS_TEMPLATE,
                "declared_losses": sb.LOSS_TEMPLATE,
                "protocol_surface": {
                    "kind": "budgeted_first_wake",
                    "terminal_tool": "complete_first_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "budgeted-first-wake-terminal-surface",
    }


def first_purpose(replicate: int) -> str:
    return f"""
You are the first wake in the budgeted three-wake chain.
replicate={replicate + 1}

Use recalled cycle 1 to derive a non-secret intermediate. Do not include the
exact deferred phrase in response, chain_intermediate, or any durable field.

Call complete_first_wake with:
- response that does not include the exact phrase;
- chain_intermediate:
  - source_cycle: 1
  - phrase_shape: "word-word-number"
  - part_count: 3
  - exact_phrase_retained: false

The terminal surface will request the bridge continuation. Do not call
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
    return gen.make_session(replicate, api_key, log_path=log_path)


def event_ids_for_label(event_records: list[dict[str, Any]], label: str) -> set[str]:
    return {
        str(record.get("event_id"))
        for record in event_records
        if record.get("label") == label and record.get("event_id")
    }


def completed_for_label(event_records: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    ids = event_ids_for_label(event_records, label)
    return [
        record for record in event_records
        if record.get("status") == "completed"
        and str(record.get("event_id")) in ids
    ]


def latest_completed(event_records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    completed = completed_for_label(event_records, label)
    return completed[-1] if completed else {}


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


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    for record in records:
        if int(record.get("cycle") or 0) == cycle:
            return record
    return {}


def validation_summary(record: dict[str, Any]) -> dict[str, Any]:
    validation = record.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "first_pass_failures": first_pass.get("failures"),
    }


def durable_text(state: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in state.items() if k != "_activity_log"}, default=str)


def first_failures(state: dict[str, Any], raw_output: dict[str, Any], replicate: int) -> list[str]:
    failures: list[str] = []
    phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != sb.probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != EXPECTED_FIRST_CYCLE:
        failures.append("cycle")
    if state.get("thinking_status") != "awaiting_bridge_continuation":
        failures.append("thinking_status")
    if phrase in durable_text(state):
        failures.append("phrase_leak")
    intermediate = state.get("chain_intermediate")
    if not isinstance(intermediate, dict):
        failures.append("chain_intermediate_missing")
    else:
        if intermediate.get("phrase_shape") != "word-word-number":
            failures.append("chain_intermediate.phrase_shape")
        if intermediate.get("exact_phrase_retained") is not False:
            failures.append("chain_intermediate.exact_phrase_retained")
    request = raw_output.get("continuation_request")
    if not isinstance(request, dict) or request.get("kind") != "budgeted_bridge_wake":
        failures.append("raw_continuation_request_missing")
    return failures


def bridge_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    replicate: int,
    bound_first_id: str | None,
) -> list[str]:
    failures: list[str] = []
    phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != sb.probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != EXPECTED_BRIDGE_CYCLE:
        failures.append("cycle")
    if state.get("thinking_status") != "awaiting_final_continuation":
        failures.append("thinking_status")
    if bound_first_id and state.get("bound_first_record_id_used") != bound_first_id:
        failures.append("bound_first_record_id_used")
    if phrase in durable_text(state):
        failures.append("phrase_leak")
    bridge = state.get("chain_bridge")
    if not isinstance(bridge, dict):
        failures.append("chain_bridge_missing")
    elif "word-word-number" not in json.dumps(bridge, default=str):
        failures.append("chain_bridge_missing_shape")
    request = raw_output.get("continuation_request")
    if not isinstance(request, dict) or request.get("kind") != "budgeted_final_wake":
        failures.append("raw_continuation_request_missing")
    return failures


def final_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    replicate: int,
    bound_bridge_id: str | None,
) -> list[str]:
    failures: list[str] = []
    phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != sb.probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != EXPECTED_FINAL_CYCLE:
        failures.append("cycle")
    if state.get("thinking_status") != "budgeted_chain_completed":
        failures.append("thinking_status")
    if bound_bridge_id and state.get("bound_bridge_record_id_used") != bound_bridge_id:
        failures.append("bound_bridge_record_id_used")
    answer = state.get("chain_final_answer")
    if not isinstance(answer, str) or phrase not in answer:
        failures.append("chain_final_answer")
    evidence_text = json.dumps(state.get("chain_final_evidence"), default=str)
    if "word-word-number" not in evidence_text:
        failures.append("chain_final_evidence_shape")
    if raw_output.get("continuation_request") is not None:
        failures.append("raw_continuation_request_present")
    return failures


class FirstValidator:
    def __init__(self, replicate: int):
        self.replicate = replicate

    def validate(self, **kwargs) -> dict:
        failures = first_failures(kwargs["state"], kwargs["raw_output"], self.replicate)
        return {"valid": not failures, "status": "valid" if not failures else "invalid", "failures": failures}


class BridgeValidator:
    def __init__(self, replicate: int, bound_first_id: str | None):
        self.replicate = replicate
        self.bound_first_id = bound_first_id

    def validate(self, **kwargs) -> dict:
        failures = bridge_failures(
            kwargs["state"],
            kwargs["raw_output"],
            self.replicate,
            self.bound_first_id,
        )
        return {"valid": not failures, "status": "valid" if not failures else "invalid", "failures": failures}


class FinalValidator:
    def __init__(self, replicate: int, bound_bridge_id: str | None):
        self.replicate = replicate
        self.bound_bridge_id = bound_bridge_id

    def validate(self, **kwargs) -> dict:
        failures = final_failures(
            kwargs["state"],
            kwargs["raw_output"],
            self.replicate,
            self.bound_bridge_id,
        )
        return {"valid": not failures, "status": "valid" if not failures else "invalid", "failures": failures}


def finalize_result(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    replicate: int,
) -> dict[str, Any]:
    records = base.load_records(log_path)
    event_records = EventStore(event_path).read_records()
    first_record = record_for_cycle(records, EXPECTED_FIRST_CYCLE)
    bridge_record = record_for_cycle(records, EXPECTED_BRIDGE_CYCLE)
    final_record = record_for_cycle(records, EXPECTED_FINAL_CYCLE)
    first_state = first_record.get("state") if isinstance(first_record, dict) else {}
    first_state = first_state if isinstance(first_state, dict) else {}
    bridge_state = bridge_record.get("state") if isinstance(bridge_record, dict) else {}
    bridge_state = bridge_state if isinstance(bridge_state, dict) else {}
    final_state = final_record.get("state") if isinstance(final_record, dict) else {}
    final_state = final_state if isinstance(final_state, dict) else {}
    first_completed = latest_completed(event_records, first_label(replicate))
    bridge_completed = latest_completed(event_records, bridge_label(replicate))
    final_completed = latest_completed(event_records, final_label(replicate))
    first_id = first_completed.get("result_record_id")
    bridge_id = bridge_completed.get("result_record_id")
    first_validation = validation_summary(first_record)
    bridge_validation = validation_summary(bridge_record)
    final_validation = validation_summary(final_record)
    phrase = matched.code_phrase_for(replicate)
    result.update({
        "cycle_count": len(records),
        "event_summary": summarize_event_log(event_records),
        "first_wake_completed": bool(first_completed),
        "bridge_wake_completed": bool(bridge_completed),
        "final_wake_completed": bool(final_completed),
        "first_wake_result_record_id": first_id,
        "bridge_wake_result_record_id": bridge_id,
        "first_wake_state_valid": not (
            first_failures(first_state, first_record.get("raw_output") or {}, replicate)
            if first_record else ["missing"]
        ),
        "bridge_wake_state_valid": not (
            bridge_failures(bridge_state, bridge_record.get("raw_output") or {}, replicate, first_id)
            if bridge_record else ["missing"]
        ),
        "final_wake_state_valid": not (
            final_failures(final_state, final_record.get("raw_output") or {}, replicate, bridge_id)
            if final_record else ["missing"]
        ),
        "first_validation": first_validation,
        "bridge_validation": bridge_validation,
        "final_validation": final_validation,
        "first_first_pass_valid": first_validation.get("first_pass_status") == "valid",
        "bridge_first_pass_valid": bridge_validation.get("first_pass_status") == "valid",
        "final_first_pass_valid": final_validation.get("first_pass_status") == "valid",
        "first_repair_attempted": first_validation.get("repair_attempted"),
        "bridge_repair_attempted": bridge_validation.get("repair_attempted"),
        "final_repair_attempted": final_validation.get("repair_attempted"),
        "first_phrase_leak": phrase in durable_text(first_state),
        "bridge_phrase_leak": phrase in durable_text(bridge_state),
        "bridge_has_cycle1_context": bool(context_result_for(bridge_completed, cycle=1)),
        "bridge_has_first_record_context": bool(context_result_for(bridge_completed, record_id=first_id)),
        "final_has_cycle1_context": bool(context_result_for(final_completed, cycle=1)),
        "final_has_bridge_record_context": bool(context_result_for(final_completed, record_id=bridge_id)),
        "final_recovered": isinstance(final_state.get("chain_final_answer"), str)
        and phrase in final_state["chain_final_answer"],
        "final_uses_bridge": "word-word-number" in json.dumps(
            final_state.get("chain_final_evidence"), default=str
        )
        and bool(bridge_id)
        and bridge_id in json.dumps(final_state.get("chain_final_evidence"), default=str),
        "step1_stop_reason": (result.get("step1") or {}).get("stop_reason"),
        "step2_stop_reason": (result.get("step2") or {}).get("stop_reason"),
        "step3_stop_reason": (result.get("step3") or {}).get("stop_reason"),
        "step1_auto_continuations": ((result.get("step1") or {}).get("batch") or {}).get("auto_continuation_count"),
        "step2_auto_continuations": ((result.get("step2") or {}).get("batch") or {}).get("auto_continuation_count"),
        "step3_auto_continuations": ((result.get("step3") or {}).get("batch") or {}).get("auto_continuation_count"),
        "final_state": final_state or bridge_state or first_state,
    })
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
        "error": None,
    }
    try:
        result["pre_first_step"] = step_pending_events(session, store, limit=4, now=sb.PRE_FIRST_NOW)
        session._state_validator = FirstValidator(replicate)
        session._state_repair_builder = None
        calls_before = backend.calls
        result["step1"] = step_pending_events(
            session,
            store,
            limit=10,
            now=sb.FIRST_DUE_NOW,
            auto_continuations=True,
            max_auto_continuations=1,
        )
        result["step1_backend_calls"] = backend.calls - calls_before
        interim = finalize_result(dict(result), log_path=log_path, event_path=event_path, replicate=replicate)
        first_id = interim.get("first_wake_result_record_id")
        result["pre_bridge_step"] = step_pending_events(session, store, limit=4, now=PRE_BRIDGE_NOW)
        session._state_validator = BridgeValidator(replicate, first_id)
        calls_before = backend.calls
        result["step2"] = step_pending_events(
            session,
            store,
            limit=10,
            now=BRIDGE_DUE_NOW,
            auto_continuations=True,
            max_auto_continuations=1,
        )
        result["step2_backend_calls"] = backend.calls - calls_before
        interim = finalize_result(dict(result), log_path=log_path, event_path=event_path, replicate=replicate)
        bridge_id = interim.get("bridge_wake_result_record_id")
        result["pre_final_step"] = step_pending_events(session, store, limit=4, now=PRE_FINAL_NOW)
        session._state_validator = FinalValidator(replicate, bridge_id)
        calls_before = backend.calls
        result["step3"] = step_pending_events(
            session,
            store,
            limit=10,
            now=FINAL_DUE_NOW,
            auto_continuations=True,
            max_auto_continuations=1,
        )
        result["step3_backend_calls"] = backend.calls - calls_before
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return finalize_result(result, log_path=log_path, event_path=event_path, replicate=replicate)


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "first_valid": sum(bool(row.get("first_wake_state_valid")) for row in rows),
        "bridge_valid": sum(bool(row.get("bridge_wake_state_valid")) for row in rows),
        "final_valid": sum(bool(row.get("final_wake_state_valid")) for row in rows),
        "first_first_pass_valid": sum(bool(row.get("first_first_pass_valid")) for row in rows),
        "bridge_first_pass_valid": sum(bool(row.get("bridge_first_pass_valid")) for row in rows),
        "final_first_pass_valid": sum(bool(row.get("final_first_pass_valid")) for row in rows),
        "step1_budget_stop": sum(row.get("step1_stop_reason") == "auto_continuation_limit_reached" for row in rows),
        "step2_budget_stop": sum(row.get("step2_stop_reason") == "auto_continuation_limit_reached" for row in rows),
        "step3_quiescent": sum(row.get("step3_stop_reason") in {"idle", "waiting"} for row in rows),
        "bridge_first_context": sum(bool(row.get("bridge_has_first_record_context")) for row in rows),
        "final_bridge_context": sum(bool(row.get("final_has_bridge_record_context")) for row in rows),
        "final_recovered": sum(bool(row.get("final_recovered")) for row in rows),
        "final_uses_bridge": sum(bool(row.get("final_uses_bridge")) for row in rows),
        "repairs": sum(
            bool(row.get("first_repair_attempted"))
            or bool(row.get("bridge_repair_attempted"))
            or bool(row.get("final_repair_attempted"))
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
        "conditions": {CONDITION: condition_summary(rows)},
        "hypothesis_results": {
            "H461_step1_budget_stop": bool(rows) and all(
                row.get("step1_stop_reason") == "auto_continuation_limit_reached"
                and row.get("step1_auto_continuations") == 1
                for row in rows
            ),
            "H462_step2_budget_stop": bool(rows) and all(
                row.get("step2_stop_reason") == "auto_continuation_limit_reached"
                and row.get("step2_auto_continuations") == 1
                for row in rows
            ),
            "H463_final_quiesces": bool(rows) and all(
                row.get("step3_stop_reason") in {"idle", "waiting"}
                and row.get("step3_auto_continuations") == 0
                and row.get("final_recovered")
                for row in rows
            ),
            "H464_generated_context_delivered": bool(rows) and all(
                row.get("bridge_has_first_record_context")
                and row.get("final_has_bridge_record_context")
                for row in rows
            ),
            "H465_first_pass_no_repair": bool(rows) and all(
                row.get("first_first_pass_valid")
                and row.get("bridge_first_pass_valid")
                and row.get("final_first_pass_valid")
                and not row.get("first_repair_attempted")
                and not row.get("bridge_repair_attempted")
                and not row.get("final_repair_attempted")
                for row in rows
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "budgeted_three_wake_chain_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "condition": CONDITION,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_keys(results: list[dict[str, Any]]) -> set[int]:
    return {int(row.get("replicate", 0)) for row in results if row.get("condition") == CONDITION}


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
