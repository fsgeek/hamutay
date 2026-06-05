"""Second-wake protocol-surface probe with a narrow terminal tool."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    step_pending_events,
)
from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
SUBSTRATE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/substrate_bound_chain_20260605/"
    / "run_substrate_bound_chain.py"
)
BASELINE_RESULTS_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/second_wake_filtered_integration_20260605/results.json"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 6
BOUND_FIELD = "chain_intermediate"
CONDITION = "second_wake_protocol_surface"
HTTP_TIMEOUT_SECONDS = 60
MAX_TOKENS = 2048
CODE_PHRASES = [
    "cobalt-bridge-11",
    "silver-maple-23",
    "green-cinder-37",
    "orange-canal-41",
    "indigo-signal-59",
    "white-anchor-67",
]

SYSTEM_PREFIX = """
Protocol-surface experiment.

For this wake, complete_second_wake is the terminal durable completion tool.
It replaces think_and_respond for the second-wake answer. The terminal surface
has no deleted_regions channel. Return only response, chain_final_answer, and
chain_final_evidence through complete_second_wake; the runner will construct
the durable state update from those fields.
""".strip()


def load_substrate_runner():
    spec = importlib.util.spec_from_file_location(
        "substrate_bound_chain_base",
        SUBSTRATE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load substrate runner from {SUBSTRATE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sb = load_substrate_runner()
base = sb.base
matched = sb.matched

matched.CODE_PHRASES = CODE_PHRASES
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT
sb.EXP_DIR = EXP_DIR
sb.PROJECT_ROOT = PROJECT_ROOT


def stable_uuid(label: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"hamutay-second-wake-protocol-surface-20260605-{label}",
    )


def cycle3_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-3-r{replicate + 1}")


def second_label(replicate: int) -> str:
    return f"second-wake-protocol-surface-r{replicate + 1}"


def seeded_cycle3_state(replicate: int) -> dict[str, Any]:
    return {
        "cycle": 3,
        "probe_id": sb.probe_id_for(replicate),
        "thinking_status": "awaiting_bound_continuation",
        "chain_stage": "first_wake_complete",
        "chain_intermediate": {
            "source_cycle": 1,
            "phrase_shape": "word-word-number",
            "part_count": 3,
            "exact_phrase_retained": False,
        },
        "continuation_request": {
            "requested": True,
            "kind": "substrate_bound_second_wake",
            "needs_original_cycle": 1,
            "needs_current_wake_record": True,
        },
        "observations": [base.BASELINE_OBSERVATION],
        "memory_handle": {
            "code_phrase_sha256": matched.code_phrase_digest(replicate),
        },
        "loss_template": sb.LOSS_TEMPLATE,
        "declared_losses": sb.LOSS_TEMPLATE,
    }


def second_wake_purpose(bound_record_id: str) -> str:
    return f"""
You are the substrate-bound second wake. The substrate bound this event to the
first wake result record ID:
{bound_record_id}

Use recalled cycle 1 to recover the exact phrase. Use recalled record
{bound_record_id} to incorporate the non-secret first-wake intermediate.

Call complete_second_wake with:
- response;
- chain_final_answer containing the exact phrase;
- chain_final_evidence referencing phrase_shape "word-word-number" from the
  filtered bound first-wake record.

Do not schedule another event.
""".strip()


class NarrowSecondWakeBackend(OpenAITasteBackend):
    """OpenAI-compatible backend exposing only a narrow terminal completion."""

    def __init__(self, *, replicate: int, bound_record_id: str, **kwargs):
        super().__init__(**kwargs)
        self.replicate = replicate
        self.bound_record_id = bound_record_id
        self.calls = 0

    @staticmethod
    def _narrow_tool_def() -> dict:
        return {
            "type": "function",
            "function": {
                "name": "complete_second_wake",
                "description": (
                    "Complete the substrate-bound second wake using delivered "
                    "context. This is the terminal tool for this experiment."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "Visible response to the user.",
                        },
                        "chain_final_answer": {
                            "type": "string",
                            "description": (
                                "Final answer containing the exact phrase from "
                                "delivered cycle-1 recall."
                            ),
                        },
                        "chain_final_evidence": {
                            "type": "object",
                            "description": (
                                "Evidence that the filtered bound-record "
                                "intermediate was used."
                            ),
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
            },
        }

    def _durable_output(self, narrow_output: dict[str, Any]) -> dict[str, Any]:
        return {
            "response": str(narrow_output.get("response") or ""),
            "thinking_status": "bound_chain_completed",
            "chain_stage": "second_wake_complete",
            "bound_record_id_used": self.bound_record_id,
            "chain_final_answer": narrow_output.get("chain_final_answer"),
            "chain_final_evidence": narrow_output.get("chain_final_evidence"),
            "observations": [base.BASELINE_OBSERVATION],
            "protocol_surface": {
                "kind": "narrow_second_wake_completion",
                "terminal_tool": "complete_second_wake",
                "deleted_regions_available": False,
            },
        }

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult:
        del experiment_label, extra_tools, tool_executor
        self.calls += 1
        oai_messages = [{"role": "system", "content": system}] + messages
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": self._max_tokens,
            "messages": oai_messages,
            "tools": [self._narrow_tool_def()],
            "tool_choice": {
                "type": "function",
                "function": {"name": "complete_second_wake"},
            },
        }
        self._apply_openai_payload_options(payload)
        data = self._post_chat(payload)
        choice = data["choices"][0]
        raw_stop = choice.get("finish_reason") or "unknown"
        if raw_stop == "length":
            raise RuntimeError(
                "Narrow backend: finish_reason=length; refusing to parse "
                "possibly truncated structured output"
            )
        stop_reason = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
        }.get(raw_stop, raw_stop)
        usage = data.get("usage", {})
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls") or []
        for tool_call in tool_calls:
            fn = tool_call.get("function", {})
            if fn.get("name") != "complete_second_wake":
                continue
            narrow_output = self._parse_tool_arguments(
                "complete_second_wake",
                fn.get("arguments", ""),
            )
            return ExchangeResult(
                raw_output=self._durable_output(narrow_output),
                stop_reason=stop_reason,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )
        if tool_calls:
            names = [tc.get("function", {}).get("name", "") for tc in tool_calls]
            raise RuntimeError(
                "Narrow backend: tool_calls returned but missing "
                f"complete_second_wake (saw: {names})"
            )
        content = message.get("content", "")
        if content:
            raw_json = self._extract_json(content)
            if raw_json is not None:
                raw_json = self._unwrap_tool_echo(raw_json)
                params = raw_json.get("parameters") if raw_json.get("name") else raw_json
                if isinstance(params, dict):
                    return ExchangeResult(
                        raw_output=self._durable_output(params),
                        stop_reason=stop_reason,
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                    )
        raise RuntimeError("Narrow backend: no complete_second_wake output")


def make_session(replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    bound_record_id = str(cycle3_record_id(replicate))
    label = f"{CONDITION}_{safe_model}_r{replicate + 1:02d}"
    backend = NarrowSecondWakeBackend(
        replicate=replicate,
        bound_record_id=bound_record_id,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=HTTP_TIMEOUT_SECONDS,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": f"hamutay/{label}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )
    session = OpenTasteSession(
        model=MODEL,
        backend=backend,
        log_path=str(log_path),
        experiment_label=label,
        system_prompt_prefix=SYSTEM_PREFIX,
        resume=False,
        enable_tools=False,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        protected_state_fields={"cycle", "_activity_log"},
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
        {
            "cycle": 3,
            "record_id": bound_record_id,
            "timestamp": "2026-06-01T01:00:00+00:00",
            "state": seeded_cycle3_state(replicate),
        },
    ]
    session.seed_history(records, up_to_cycle=4)
    return session, backend


def append_second_event(
    store: EventStore,
    *,
    replicate: int,
    bound_record_id: str,
) -> dict[str, Any]:
    event = build_pending_event(
        purpose=second_wake_purpose(bound_record_id),
        requested_context=[
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": bound_record_id,
                "field": BOUND_FIELD,
            },
        ],
        scheduled_by_cycle=sb.EXPECTED_FIRST_WAKE_CYCLE,
        scheduled_by_record_id=UUID(bound_record_id),
        label=second_label(replicate),
        not_before=sb.SECOND_NOT_BEFORE,
    )
    event["bound_by"] = "seeded_valid_first_wake_record"
    event["bound_result_record_id"] = bound_record_id
    event["bound_record_field"] = BOUND_FIELD
    event["protocol_surface"] = "narrow_second_wake_completion"
    store.append(event)
    return event


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    for record in records:
        if int(record.get("cycle") or 0) == cycle:
            return record
    return {}


def event_record_for_label(
    event_records: list[dict[str, Any]],
    label: str,
    status: str,
) -> dict[str, Any]:
    event_id = None
    for record in event_records:
        if record.get("status") == "pending" and record.get("label") == label:
            event_id = record.get("event_id")
            break
    if not event_id:
        return {}
    for record in event_records:
        if record.get("event_id") == event_id and record.get("status") == status:
            return record
    return {}


def terminal_event_record_for_label(
    event_records: list[dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    completed = event_record_for_label(event_records, label, "completed")
    if completed:
        return completed
    return event_record_for_label(event_records, label, "failed")


def context_result_for(
    terminal_event: dict[str, Any],
    *,
    tool: str,
    cycle: int | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    for item in terminal_event.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") != tool:
            continue
        if cycle is not None and request.get("cycle") != cycle:
            continue
        if record_id is not None and request.get("record_id") != record_id:
            continue
        result = item.get("result") or {}
        return result if isinstance(result, dict) else {}
    return {}


def validation_summary(record: dict[str, Any]) -> dict[str, Any]:
    validation = record.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status"),
        "first_pass_failures": first_pass.get("failures"),
        "repair_attempted": bool(validation.get("repair_attempted")),
    }


def classify_failures(
    *,
    context_delivered: bool,
    second_failures: list[str],
    event_error_type: str | None,
) -> list[str]:
    labels: list[str] = []
    if event_error_type:
        labels.append(f"event_failure:{event_error_type}")
    if not context_delivered:
        labels.append("context_delivery_failure")
    for failure in second_failures:
        if failure.startswith("deleted_regions."):
            labels.append(f"delete_update_conflict:{failure}")
        elif failure.startswith("chain_final") or failure in {
            "thinking_status_not_bound_chain_completed",
            "chain_stage_not_second_wake_complete",
            "bound_record_id_used_missing_or_changed",
            "baseline_observation_missing",
        }:
            labels.append(f"semantic_integration:{failure}")
        else:
            labels.append(f"other:{failure}")
    return labels


def finalize_result(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    replicate: int,
    bound_record_id: str,
) -> dict[str, Any]:
    records = base.load_records(log_path)
    event_records = EventStore(event_path).read_records()
    second_record = record_for_cycle(records, sb.EXPECTED_SECOND_WAKE_CYCLE)
    second_state = second_record.get("state") if isinstance(second_record, dict) else {}
    second_state = second_state if isinstance(second_state, dict) else {}
    completed = event_record_for_label(
        event_records,
        second_label(replicate),
        "completed",
    )
    terminal_event = terminal_event_record_for_label(
        event_records,
        second_label(replicate),
    )
    cycle1_result = context_result_for(terminal_event, tool="recall", cycle=1)
    bound_result = context_result_for(
        terminal_event,
        tool="recall",
        record_id=bound_record_id,
    )
    code_phrase = matched.code_phrase_for(replicate)
    cycle1_delivered = bool(cycle1_result) and "error" not in cycle1_result
    filtered_delivered = bool(bound_result) and "error" not in bound_result
    context_delivered = cycle1_delivered and filtered_delivered
    raw_output = second_record.get("raw_output") or {}
    second_failures = (
        sb.second_wake_failures(
            second_state,
            raw_output,
            replicate=replicate,
            bound_record_id=bound_record_id,
        )
        if second_record
        else ["second_wake_record_missing"]
    )
    visible_state_text = json.dumps(
        {k: v for k, v in second_state.items() if k != "_activity_log"},
        default=str,
    )
    filtered_context_text = json.dumps(bound_result, default=str)
    result.update(
        {
            "cycle_count": len(records),
            "event_summary": base.summarize_event_log(event_records),
            "second_wake_completed": bool(completed),
            "cycle1_context_delivered": cycle1_delivered,
            "filtered_context_delivered": filtered_delivered,
            "both_contexts_delivered": context_delivered,
            "filtered_bound_field": BOUND_FIELD,
            "filtered_context_contains_activity_log": "_activity_log" in filtered_context_text,
            "filtered_context_contains_code_phrase": code_phrase in filtered_context_text,
            "filtered_context_content": (
                bound_result.get("content") if isinstance(bound_result, dict) else None
            ),
            "narrow_tool_parse_success": bool(second_record),
            "delete_update_conflict": any(
                failure.startswith("deleted_regions.")
                for failure in second_failures
            ),
            "second_wake_state_valid": not second_failures,
            "second_wake_failures": second_failures,
            "second_wake_validation": validation_summary(second_record),
            "chain_final_answer_contains_code_phrase": (
                isinstance(second_state.get("chain_final_answer"), str)
                and code_phrase in second_state["chain_final_answer"]
            ),
            "chain_final_evidence_uses_intermediate": (
                "word-word-number" in json.dumps(
                    second_state.get("chain_final_evidence"),
                    default=str,
                )
            ),
            "visible_state_contains_code_phrase": code_phrase in visible_state_text,
            "activity_log_contains_code_phrase": code_phrase
            in json.dumps(second_state.get("_activity_log"), default=str),
            "bound_record_id_used": second_state.get("bound_record_id_used"),
            "failure_labels": classify_failures(
                context_delivered=context_delivered,
                second_failures=second_failures,
                event_error_type=terminal_event.get("error_type"),
            ),
            "final_state": second_state,
        }
    )
    return result


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{CONDITION}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    bound_record_id = str(cycle3_record_id(replicate))
    session, backend = make_session(replicate, api_key, log_path=log_path)
    store = EventStore(event_path)
    append_second_event(
        store,
        replicate=replicate,
        bound_record_id=bound_record_id,
    )
    result: dict[str, Any] = {
        "condition": CONDITION,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": sb.probe_id_for(replicate),
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
        "bound_record_id": bound_record_id,
        "protocol_surface": "narrow_second_wake_completion",
        "backend_calls": 0,
        "bounded_calls": True,
        "error": None,
    }
    try:
        result["pre_second_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.PRE_SECOND_NOW,
        )
        session._state_validator = sb.SecondWakeValidator(
            replicate=replicate,
            bound_record_id=bound_record_id,
        )
        calls_before = backend.calls
        with base.bounded_call(f"{CONDITION} r{replicate + 1}"):
            result["second_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=sb.SECOND_DUE_NOW,
            )
        result["backend_calls"] = backend.calls - calls_before
        result["bounded_calls"] = result["backend_calls"] <= 1
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        replicate=replicate,
        bound_record_id=bound_record_id,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failure_labels = Counter(
        label
        for row in rows
        for label in (row.get("failure_labels") or [])
    )
    second_failures = Counter(
        failure
        for row in rows
        for failure in (row.get("second_wake_failures") or [])
    )
    return {
        "n": len(rows),
        "both_contexts_delivered": sum(bool(row.get("both_contexts_delivered")) for row in rows),
        "cycle1_context_delivered": sum(bool(row.get("cycle1_context_delivered")) for row in rows),
        "filtered_context_delivered": sum(bool(row.get("filtered_context_delivered")) for row in rows),
        "filtered_context_activity_log_leaks": sum(
            bool(row.get("filtered_context_contains_activity_log")) for row in rows
        ),
        "filtered_context_code_phrase_leaks": sum(
            bool(row.get("filtered_context_contains_code_phrase")) for row in rows
        ),
        "narrow_tool_parse_success": sum(
            bool(row.get("narrow_tool_parse_success")) for row in rows
        ),
        "first_pass_valid": sum(
            (row.get("second_wake_validation") or {}).get("first_pass_status") == "valid"
            for row in rows
        ),
        "final_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "final_answer_recovered": sum(
            bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows
        ),
        "intermediate_used": sum(
            bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows
        ),
        "delete_update_conflicts": sum(bool(row.get("delete_update_conflict")) for row in rows),
        "visible_phrase_leaks": sum(
            bool(row.get("visible_state_contains_code_phrase")) for row in rows
        ),
        "activity_log_phrase_leaks": sum(
            bool(row.get("activity_log_contains_code_phrase")) for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_call_violations": sum(not bool(row.get("bounded_calls")) for row in rows),
        "failure_labels": dict(sorted(failure_labels.items())),
        "second_wake_failure_labels": dict(sorted(second_failures.items())),
    }


def baseline_summary() -> dict[str, Any]:
    if not BASELINE_RESULTS_PATH.exists():
        return {"available": False}
    payload = json.loads(BASELINE_RESULTS_PATH.read_text())
    summary = payload.get("summary", {})
    condition = (
        summary.get("conditions", {})
        .get("second_wake_filtered_integration", {})
    )
    return {
        "available": True,
        "path": str(BASELINE_RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "final_valid": condition.get("final_valid"),
        "delete_update_conflicts": condition.get("second_wake_failure_labels", {}).get(
            "deleted_regions.chain_intermediate",
            0,
        ),
        "both_contexts_delivered": condition.get("both_contexts_delivered"),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {
        condition: condition_summary(rows)
        for condition, rows in sorted(grouped.items())
    }
    final_valid = sum(bool(row.get("second_wake_state_valid")) for row in results)
    both_delivered = sum(bool(row.get("both_contexts_delivered")) for row in results)
    recovered = sum(
        bool(row.get("chain_final_answer_contains_code_phrase"))
        and bool(row.get("chain_final_evidence_uses_intermediate"))
        for row in results
    )
    delete_conflicts = sum(bool(row.get("delete_update_conflict")) for row in results)
    labels_distinguishable = all(
        isinstance(row.get("failure_labels"), list)
        and all(
            label.startswith((
                "context_delivery_failure",
                "delete_update_conflict:",
                "event_failure:",
                "semantic_integration:",
                "other:",
            ))
            for label in row.get("failure_labels") or []
        )
        for row in results
    )
    return {
        "conditions": summaries,
        "baseline": baseline_summary(),
        "hypothesis_results": {
            "H341_delete_update_invalidity_reduced": delete_conflicts == 0,
            "H342_context_delivery_at_least_5_of_6": both_delivered >= 5,
            "H343_substantive_task_at_least_5_of_6": recovered >= 5,
            "H344_final_valid_above_3_of_6_baseline": final_valid > 3,
            "H345_failure_labels_distinguish_categories": labels_distinguishable,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "second_wake_protocol_surface_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "filtered_bound_field": BOUND_FIELD,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_replicates(results: list[dict[str, Any]]) -> set[int]:
    return {int(row.get("replicate", 0)) for row in results}


def refresh_completed_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refreshed: list[dict[str, Any]] = []
    derived_keys = {
        "cycle_count",
        "event_summary",
        "second_wake_completed",
        "cycle1_context_delivered",
        "filtered_context_delivered",
        "both_contexts_delivered",
        "filtered_bound_field",
        "filtered_context_contains_activity_log",
        "filtered_context_contains_code_phrase",
        "filtered_context_content",
        "narrow_tool_parse_success",
        "delete_update_conflict",
        "second_wake_state_valid",
        "second_wake_failures",
        "second_wake_validation",
        "chain_final_answer_contains_code_phrase",
        "chain_final_evidence_uses_intermediate",
        "visible_state_contains_code_phrase",
        "activity_log_contains_code_phrase",
        "bound_record_id_used",
        "failure_labels",
        "final_state",
    }
    for row in results:
        replicate = int(row.get("replicate") or 0) - 1
        bound_record_id = row.get("bound_record_id")
        log_path_text = row.get("log_path")
        event_path_text = row.get("event_log_path")
        if (
            replicate < 0
            or not isinstance(bound_record_id, str)
            or not isinstance(log_path_text, str)
            or not isinstance(event_path_text, str)
        ):
            refreshed.append(row)
            continue
        base_row = {key: value for key, value in row.items() if key not in derived_keys}
        refreshed.append(
            finalize_result(
                base_row,
                log_path=PROJECT_ROOT / log_path_text,
                event_path=PROJECT_ROOT / event_path_text,
                replicate=replicate,
                bound_record_id=bound_record_id,
            )
        )
    return refreshed


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = refresh_completed_results(
                [row for row in prior if isinstance(row, dict)]
            )
    done = completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(f"{CONDITION} r{replicate + 1} already recorded", flush=True)
            continue
        print(f"{CONDITION} r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
