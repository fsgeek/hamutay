"""Generated substrate-bound chain probe with terminal surfaces on both wakes."""

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


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
SUBSTRATE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/substrate_bound_chain_20260605/"
    / "run_substrate_bound_chain.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 2
CONDITION = "generated_bound_chain_terminal_surface"
BOUND_FIELD = "chain_intermediate"


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

sb.EXP_DIR = EXP_DIR
sb.PROJECT_ROOT = PROJECT_ROOT
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def first_surface(replicate: int) -> dict[str, Any]:
    return {
        "tool_name": "complete_first_wake",
        "description": (
            "Commit the non-secret first-wake intermediate and continuation "
            "request."
        ),
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
                "continuation_request": {
                    "type": "object",
                    "properties": {
                        "requested": {"type": "boolean"},
                        "kind": {"type": "string"},
                        "needs_original_cycle": {"type": "integer"},
                        "needs_current_wake_record": {"type": "boolean"},
                    },
                    "required": [
                        "requested",
                        "kind",
                        "needs_original_cycle",
                        "needs_current_wake_record",
                    ],
                    "additionalProperties": True,
                },
            },
            "required": [
                "response",
                "chain_intermediate",
                "continuation_request",
            ],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "chain_intermediate": "chain_intermediate",
                "continuation_request": "continuation_request",
            },
            "set": {
                "thinking_status": "awaiting_bound_continuation",
                "chain_stage": "first_wake_complete",
                "observations": [base.BASELINE_OBSERVATION],
                "memory_handle": {
                    "code_phrase_sha256": matched.code_phrase_digest(replicate),
                },
                "loss_template": sb.LOSS_TEMPLATE,
                "declared_losses": sb.LOSS_TEMPLATE,
                "protocol_surface": {
                    "kind": "narrow_generated_first_wake",
                    "terminal_tool": "complete_first_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "generated-first-wake-terminal-surface",
    }


def second_surface(bound_record_id: str) -> dict[str, Any]:
    return {
        "tool_name": "complete_second_wake",
        "description": (
            "Complete the generated substrate-bound second wake using "
            "delivered recall context."
        ),
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
                "thinking_status": "bound_chain_completed",
                "chain_stage": "second_wake_complete",
                "bound_record_id_used": bound_record_id,
                "observations": [base.BASELINE_OBSERVATION],
                "protocol_surface": {
                    "kind": "narrow_generated_second_wake",
                    "terminal_tool": "complete_second_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "generated-second-wake-terminal-surface",
    }


def first_purpose(replicate: int) -> str:
    return f"""
You are the first wake in the generated substrate-bound chain probe.
replicate={replicate + 1}

Use recalled cycle 1 to derive a non-secret intermediate. Do not include the
exact deferred phrase in response, chain_intermediate, continuation_request, or
any durable field.

Call complete_first_wake with:
- response that does not include the exact phrase;
- chain_intermediate:
  - source_cycle: 1
  - phrase_shape: "word-word-number"
  - part_count: 3
  - exact_phrase_retained: false
- continuation_request:
  - requested: true
  - kind: "substrate_bound_second_wake"
  - needs_original_cycle: 1
  - needs_current_wake_record: true

Do not call schedule_event. The substrate will bind the continuation to this
wake's result record ID after your state is committed.
""".strip()


def second_purpose(bound_record_id: str) -> str:
    return f"""
You are the generated substrate-bound second wake. The substrate bound this
event to the first wake result record ID:
{bound_record_id}

Use recalled cycle 1 to recover the exact phrase. Use the recalled
chain_intermediate field from record {bound_record_id} to build evidence.

Call complete_second_wake with:
- response;
- chain_final_answer containing the exact phrase;
- chain_final_evidence referencing phrase_shape "word-word-number" from the
  bound first-wake record.

Do not schedule another event.
""".strip()


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


def append_first_event(store: EventStore, replicate: int) -> dict[str, Any]:
    event = build_pending_event(
        purpose=first_purpose(replicate),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=2,
        scheduled_by_record_id=sb.cycle2_record_id(replicate),
        label=sb.first_label(replicate),
        not_before=sb.FIRST_NOT_BEFORE,
        terminal_surface=first_surface(replicate),
    )
    store.append(event)
    return event


def append_bound_second_event(
    store: EventStore,
    *,
    replicate: int,
    bound_record_id: str,
) -> dict[str, Any]:
    event = build_pending_event(
        purpose=second_purpose(bound_record_id),
        requested_context=[
            {"tool": "recall", "cycle": 1},
            {"tool": "recall", "record_id": bound_record_id, "field": BOUND_FIELD},
        ],
        scheduled_by_cycle=sb.EXPECTED_FIRST_WAKE_CYCLE,
        scheduled_by_record_id=bound_record_id,
        label=sb.second_label(replicate),
        not_before=sb.SECOND_NOT_BEFORE,
        terminal_surface=second_surface(bound_record_id),
    )
    event["bound_by"] = "runner_after_terminal_first_wake_completion"
    event["bound_result_record_id"] = bound_record_id
    event["bound_record_field"] = BOUND_FIELD
    store.append(event)
    return event


def load_records(path: Path) -> list[dict[str, Any]]:
    return base.load_records(path)


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    return sb.record_for_cycle(records, cycle)


def terminal_event(
    event_records: list[dict[str, Any]],
    label: str,
    status: str,
) -> dict[str, Any]:
    return sb.event_record_for_label(event_records, label, status)


def context_result_for(
    completed_event: dict[str, Any],
    *,
    tool: str,
    cycle: int | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    for item in completed_event.get("context_results") or []:
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
    return sb.validation_summary(record)


def terminal_summary(summary: dict[str, Any], label: str) -> dict[str, Any]:
    for record in summary.get("completed", []):
        if record.get("label") == label:
            return record
    for record in summary.get("failed", []):
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
    records = load_records(log_path)
    event_records = EventStore(event_path).read_records()
    summary = summarize_event_log(event_records)
    first_record = record_for_cycle(records, sb.EXPECTED_FIRST_WAKE_CYCLE)
    second_record = record_for_cycle(records, sb.EXPECTED_SECOND_WAKE_CYCLE)
    first_state = first_record.get("state") if isinstance(first_record, dict) else {}
    first_state = first_state if isinstance(first_state, dict) else {}
    second_state = second_record.get("state") if isinstance(second_record, dict) else {}
    second_state = second_state if isinstance(second_state, dict) else {}
    first_completed = terminal_event(event_records, sb.first_label(replicate), "completed")
    second_completed = terminal_event(event_records, sb.second_label(replicate), "completed")
    bound_record_id = first_completed.get("result_record_id")
    first_failures = (
        sb.first_wake_failures(
            first_state,
            first_record.get("raw_output") or {},
            replicate=replicate,
        )
        if first_record
        else ["first_wake_record_missing"]
    )
    second_failures = (
        sb.second_wake_failures(
            second_state,
            second_record.get("raw_output") or {},
            replicate=replicate,
            bound_record_id=bound_record_id,
        )
        if second_record
        else ["second_wake_record_missing"]
    )
    cycle1_for_first = context_result_for(first_completed, tool="recall", cycle=1)
    cycle1_for_second = context_result_for(second_completed, tool="recall", cycle=1)
    bound_context = context_result_for(
        second_completed,
        tool="recall",
        record_id=bound_record_id,
    )
    code_phrase = matched.code_phrase_for(replicate)
    first_event_summary = terminal_summary(summary, sb.first_label(replicate))
    second_event_summary = terminal_summary(summary, sb.second_label(replicate))
    first_validation = validation_summary(first_record)
    second_validation = validation_summary(second_record)
    result.update(
        {
            "cycle_count": len(records),
            "event_summary": summary,
            "first_wake_completed": bool(first_completed),
            "first_wake_result_record_id": bound_record_id,
            "first_wake_context_has_cycle1": bool(cycle1_for_first)
            and "error" not in cycle1_for_first,
            "first_wake_terminal_parse_success": terminal_parse_success(
                first_record,
                ("chain_intermediate", "continuation_request"),
            ),
            "first_wake_state_valid": not first_failures,
            "first_wake_failures": first_failures,
            "first_wake_state_contains_code_phrase": code_phrase in sb.durable_text(first_state),
            "first_wake_validation": first_validation,
            "first_wake_first_pass_valid": first_validation.get("first_pass_status") == "valid",
            "first_wake_repair_attempted": first_validation.get("repair_attempted"),
            "continuation_requested": isinstance(
                first_state.get("continuation_request"), dict
            ) and first_state["continuation_request"].get("requested") is True,
            "bound_second_event_appended": bool(
                terminal_event(event_records, sb.second_label(replicate), "pending")
            ),
            "second_wake_completed": bool(second_completed),
            "second_wake_context_has_cycle1": bool(cycle1_for_second)
            and "error" not in cycle1_for_second,
            "second_wake_context_has_bound_record_id": bool(bound_context)
            and "error" not in bound_context,
            "bound_record_context_delivered": bool(bound_context)
            and "error" not in bound_context,
            "bound_record_context_result": bound_context,
            "second_wake_terminal_parse_success": terminal_parse_success(
                second_record,
                ("chain_final_answer", "chain_final_evidence"),
            ),
            "second_wake_state_valid": not second_failures,
            "second_wake_failures": second_failures,
            "second_wake_validation": second_validation,
            "second_wake_first_pass_valid": second_validation.get("first_pass_status") == "valid",
            "second_wake_repair_attempted": second_validation.get("repair_attempted"),
            "chain_final_answer_contains_code_phrase": (
                isinstance(second_state.get("chain_final_answer"), str)
                and code_phrase in second_state["chain_final_answer"]
            ),
            "chain_final_evidence_uses_intermediate": (
                "word-word-number" in json.dumps(
                    second_state.get("chain_final_evidence"), default=str
                )
            ),
            "bound_record_id_used": second_state.get("bound_record_id_used"),
            "first_terminal_surface_tool_observed": first_event_summary.get(
                "terminal_surface_tool"
            ),
            "first_terminal_surface_label_observed": first_event_summary.get(
                "terminal_surface_label"
            ),
            "second_terminal_surface_tool_observed": second_event_summary.get(
                "terminal_surface_tool"
            ),
            "second_terminal_surface_label_observed": second_event_summary.get(
                "terminal_surface_label"
            ),
            "final_state": second_state or first_state,
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
        "second_backend_calls": 0,
        "bounded_first_calls": True,
        "bounded_second_calls": True,
        "error": None,
    }
    try:
        result["pre_first_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.PRE_FIRST_NOW,
        )
        session._state_validator = sb.FirstWakeValidator(replicate=replicate)
        session._state_repair_builder = None
        first_calls_before = backend.calls
        with base.bounded_call(f"{CONDITION} r{replicate + 1} first"):
            result["first_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=sb.FIRST_DUE_NOW,
            )
        result["first_backend_calls"] = backend.calls - first_calls_before
        result["bounded_first_calls"] = result["first_backend_calls"] <= 1

        interim = finalize_result(
            dict(result),
            log_path=log_path,
            event_path=event_path,
            replicate=replicate,
        )
        bound_record_id = interim.get("first_wake_result_record_id")
        if (
            interim.get("first_wake_state_valid")
            and not interim.get("first_wake_state_contains_code_phrase")
            and interim.get("continuation_requested")
            and isinstance(bound_record_id, str)
            and bound_record_id
        ):
            append_bound_second_event(
                store,
                replicate=replicate,
                bound_record_id=bound_record_id,
            )
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
            session._state_repair_builder = None
            second_calls_before = backend.calls
            with base.bounded_call(f"{CONDITION} r{replicate + 1} second"):
                result["second_step"] = step_pending_events(
                    session,
                    store,
                    limit=4,
                    now=sb.SECOND_DUE_NOW,
                )
            result["second_backend_calls"] = backend.calls - second_calls_before
            result["bounded_second_calls"] = result["second_backend_calls"] <= 1
        else:
            result["second_stage_skipped"] = "first_wake_invalid_or_no_bound_record"
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
        "first_wake_completed": sum(bool(row.get("first_wake_completed")) for row in rows),
        "first_wake_terminal_parse_success": sum(
            bool(row.get("first_wake_terminal_parse_success")) for row in rows
        ),
        "first_wake_valid": sum(bool(row.get("first_wake_state_valid")) for row in rows),
        "first_wake_first_pass_valid": sum(
            bool(row.get("first_wake_first_pass_valid")) for row in rows
        ),
        "first_wake_state_leaks": sum(
            bool(row.get("first_wake_state_contains_code_phrase")) for row in rows
        ),
        "continuation_requested": sum(
            bool(row.get("continuation_requested")) for row in rows
        ),
        "bound_second_event_appended": sum(
            bool(row.get("bound_second_event_appended")) for row in rows
        ),
        "second_wake_completed": sum(bool(row.get("second_wake_completed")) for row in rows),
        "second_wake_terminal_parse_success": sum(
            bool(row.get("second_wake_terminal_parse_success")) for row in rows
        ),
        "second_wake_cycle1_context": sum(
            bool(row.get("second_wake_context_has_cycle1")) for row in rows
        ),
        "second_wake_bound_context": sum(
            bool(row.get("bound_record_context_delivered")) for row in rows
        ),
        "second_wake_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "second_wake_first_pass_valid": sum(
            bool(row.get("second_wake_first_pass_valid")) for row in rows
        ),
        "final_recovered": sum(
            bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows
        ),
        "intermediate_used": sum(
            bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows
        ),
        "first_repair_attempted": sum(
            bool(row.get("first_wake_repair_attempted")) for row in rows
        ),
        "second_repair_attempted": sum(
            bool(row.get("second_wake_repair_attempted")) for row in rows
        ),
        "terminal_surfaces_observed_for_both": sum(
            row.get("first_terminal_surface_tool_observed") == "complete_first_wake"
            and row.get("second_terminal_surface_tool_observed") == "complete_second_wake"
            for row in rows
        ),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_first_calls"))
            or not bool(row.get("bounded_second_calls"))
            for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {
        condition: condition_summary(rows)
        for condition, rows in sorted(grouped.items())
    }
    rows = grouped.get(CONDITION, [])
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H391_first_surface_valid_intermediate": (
                bool(rows)
                and all(row.get("first_wake_state_valid") for row in rows)
                and all(not row.get("first_wake_state_contains_code_phrase") for row in rows)
                and all(row.get("continuation_requested") for row in rows)
            ),
            "H392_substrate_binds_second_event": (
                bool(rows)
                and all(row.get("bound_second_event_appended") for row in rows)
            ),
            "H393_second_receives_original_and_bound_context": (
                bool(rows)
                and all(row.get("second_wake_context_has_cycle1") for row in rows)
                and all(row.get("bound_record_context_delivered") for row in rows)
            ),
            "H394_second_surface_recovers_without_repair": (
                bool(rows)
                and all(row.get("second_wake_state_valid") for row in rows)
                and all(row.get("chain_final_answer_contains_code_phrase") for row in rows)
                and all(row.get("chain_final_evidence_uses_intermediate") for row in rows)
                and all(not row.get("second_wake_repair_attempted") for row in rows)
            ),
            "H395_terminal_surfaces_observable": (
                bool(rows)
                and all(
                    row.get("first_terminal_surface_tool_observed")
                    == "complete_first_wake"
                    for row in rows
                )
                and all(
                    row.get("second_terminal_surface_tool_observed")
                    == "complete_second_wake"
                    for row in rows
                )
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "generated_bound_chain_terminal_surface_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "condition": CONDITION,
        "first_not_before": sb.FIRST_NOT_BEFORE,
        "second_not_before": sb.SECOND_NOT_BEFORE,
        "first_terminal_surface": first_surface(0),
        "second_terminal_surface_template": second_surface("<bound_record_id>"),
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
