"""Live smoke for first-class scheduled-event terminal surfaces."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

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
BOUND_FIELD = "chain_intermediate"
CONDITION = "terminal_surface_substrate_smoke"
CODE_PHRASES = ["cobalt-bridge-11", "silver-maple-23"]


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
        f"hamutay-terminal-surface-substrate-smoke-20260605-{label}",
    )


def cycle3_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-3-r{replicate + 1}")


def second_label(replicate: int) -> str:
    return f"terminal-surface-substrate-smoke-r{replicate + 1}"


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


def terminal_surface(bound_record_id: str) -> dict[str, Any]:
    return {
        "tool_name": "complete_second_wake",
        "description": (
            "Complete the substrate-bound second wake using delivered recall "
            "context."
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
                    "kind": "narrow_second_wake_completion",
                    "terminal_tool": "complete_second_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "second-wake-terminal-surface",
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
        {
            "cycle": 3,
            "record_id": str(cycle3_record_id(replicate)),
            "timestamp": "2026-06-01T01:00:00+00:00",
            "state": seeded_cycle3_state(replicate),
        },
    ]
    session.seed_history(records, up_to_cycle=4)
    return session, backend


def append_second_event(store: EventStore, *, replicate: int, bound_record_id: str):
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
        terminal_surface=terminal_surface(bound_record_id),
    )
    event["bound_by"] = "seeded_valid_first_wake_record"
    event["bound_result_record_id"] = bound_record_id
    event["bound_record_field"] = BOUND_FIELD
    store.append(event)
    return event


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    for record in records:
        if int(record.get("cycle") or 0) == cycle:
            return record
    return {}


def terminal_event(event_records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    event_id = None
    for record in event_records:
        if record.get("status") == "pending" and record.get("label") == label:
            event_id = record.get("event_id")
            break
    for status in ("completed", "failed"):
        for record in event_records:
            if record.get("event_id") == event_id and record.get("status") == status:
                return record
    return {}


def context_result_for(
    terminal: dict[str, Any],
    *,
    tool: str,
    cycle: int | None = None,
    record_id: str | None = None,
) -> dict[str, Any]:
    for item in terminal.get("context_results") or []:
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
    first_pass = validation.get("first_pass") if isinstance(validation, dict) else {}
    first_pass = first_pass if isinstance(first_pass, dict) else {}
    return {
        "status": validation.get("status") if isinstance(validation, dict) else None,
        "first_pass_status": first_pass.get("status"),
        "first_pass_failures": first_pass.get("failures"),
    }


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
    terminal = terminal_event(event_records, second_label(replicate))
    cycle1 = context_result_for(terminal, tool="recall", cycle=1)
    bound = context_result_for(terminal, tool="recall", record_id=bound_record_id)
    code_phrase = matched.code_phrase_for(replicate)
    failures = (
        sb.second_wake_failures(
            second_state,
            second_record.get("raw_output") or {},
            replicate=replicate,
            bound_record_id=bound_record_id,
        )
        if second_record
        else ["second_wake_record_missing"]
    )
    summary = summarize_event_log(event_records)
    completed = summary.get("completed", [])
    completed_event = completed[0] if completed else {}
    result.update({
        "cycle_count": len(records),
        "event_summary": summary,
        "terminal_parse_success": bool(second_record),
        "cycle1_context_delivered": bool(cycle1) and "error" not in cycle1,
        "filtered_context_delivered": bool(bound) and "error" not in bound,
        "both_contexts_delivered": (
            bool(cycle1) and "error" not in cycle1
            and bool(bound) and "error" not in bound
        ),
        "second_wake_state_valid": not failures,
        "second_wake_failures": failures,
        "second_wake_validation": validation_summary(second_record),
        "chain_final_answer_contains_code_phrase": (
            isinstance(second_state.get("chain_final_answer"), str)
            and code_phrase in second_state["chain_final_answer"]
        ),
        "chain_final_evidence_uses_intermediate": (
            "word-word-number" in json.dumps(
                second_state.get("chain_final_evidence"), default=str
            )
        ),
        "terminal_surface_tool_observed": completed_event.get("terminal_surface_tool"),
        "terminal_surface_label_observed": completed_event.get("terminal_surface_label"),
        "final_state": second_state,
    })
    return result


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{CONDITION}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    bound_record_id = str(cycle3_record_id(replicate))
    session, backend = make_session(replicate, api_key, log_path=log_path)
    session._state_validator = sb.SecondWakeValidator(
        replicate=replicate,
        bound_record_id=bound_record_id,
    )
    store = EventStore(event_path)
    append_second_event(store, replicate=replicate, bound_record_id=bound_record_id)
    result: dict[str, Any] = {
        "condition": CONDITION,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "bound_record_id": bound_record_id,
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


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    failures = Counter(
        failure
        for row in results
        for failure in (row.get("second_wake_failures") or [])
    )
    return {
        "n": len(results),
        "both_contexts_delivered": sum(
            bool(row.get("both_contexts_delivered")) for row in results
        ),
        "terminal_parse_success": sum(
            bool(row.get("terminal_parse_success")) for row in results
        ),
        "final_valid": sum(bool(row.get("second_wake_state_valid")) for row in results),
        "final_answer_recovered": sum(
            bool(row.get("chain_final_answer_contains_code_phrase"))
            for row in results
        ),
        "intermediate_used": sum(
            bool(row.get("chain_final_evidence_uses_intermediate"))
            for row in results
        ),
        "terminal_surface_observed": sum(
            row.get("terminal_surface_tool_observed") == "complete_second_wake"
            and row.get("terminal_surface_label_observed")
            == "second-wake-terminal-surface"
            for row in results
        ),
        "errors": sum(bool(row.get("error")) for row in results),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_calls")) for row in results
        ),
        "failure_labels": dict(sorted(failures.items())),
        "hypothesis_results": {
            "H361_contexts_delivered_both_rows": (
                sum(bool(row.get("both_contexts_delivered")) for row in results)
                == N_REPLICATES
            ),
            "H362_terminal_tool_success_both_rows": (
                sum(bool(row.get("terminal_parse_success")) for row in results)
                == N_REPLICATES
            ),
            "H363_final_valid_both_rows": (
                sum(bool(row.get("second_wake_state_valid")) for row in results)
                == N_REPLICATES
            ),
            "H364_phrase_and_intermediate_both_rows": (
                sum(
                    bool(row.get("chain_final_answer_contains_code_phrase"))
                    and bool(row.get("chain_final_evidence_uses_intermediate"))
                    for row in results
                )
                == N_REPLICATES
            ),
            "H365_terminal_surface_observed_both_rows": (
                sum(
                    row.get("terminal_surface_tool_observed")
                    == "complete_second_wake"
                    and row.get("terminal_surface_label_observed")
                    == "second-wake-terminal-surface"
                    for row in results
                )
                == N_REPLICATES
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "terminal_surface_substrate_smoke_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "filtered_bound_field": BOUND_FIELD,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_replicates(results: list[dict[str, Any]]) -> set[int]:
    return {int(row.get("replicate", 0)) for row in results}


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = [row for row in prior if isinstance(row, dict)]
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
