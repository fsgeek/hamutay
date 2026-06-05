"""Rerun bound-chain contract with filtered bound record recall."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from hamutay.events import build_pending_event


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BOUND_CHAIN_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bound_chain_contract_20260605/"
    / "run_bound_chain_contract.py"
)

BOUND_FIELD = "chain_intermediate"


def load_bound_chain_runner():
    spec = importlib.util.spec_from_file_location(
        "bound_chain_contract_base",
        BOUND_CHAIN_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bound-chain runner from {BOUND_CHAIN_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base_runner = load_bound_chain_runner()
sb = base_runner.sb
matched = base_runner.matched
base = base_runner.base
MODEL = base_runner.MODEL
N_REPLICATES = base_runner.N_REPLICATES

base_runner.EXP_DIR = EXP_DIR
base_runner.PROJECT_ROOT = PROJECT_ROOT
base_runner.RESULTS_PATH = RESULTS_PATH
base_runner.base.EXP_DIR = EXP_DIR
base_runner.base.PROJECT_ROOT = PROJECT_ROOT
sb.EXP_DIR = EXP_DIR
sb.PROJECT_ROOT = PROJECT_ROOT


def append_filtered_bound_second_event(
    store,
    *,
    replicate: int,
    bound_record_id: str,
) -> dict[str, Any]:
    event = build_pending_event(
        purpose=sb.second_wake_purpose(bound_record_id),
        requested_context=[
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": bound_record_id,
                "field": BOUND_FIELD,
            },
        ],
        scheduled_by_cycle=sb.EXPECTED_FIRST_WAKE_CYCLE,
        scheduled_by_record_id=sb.UUID(bound_record_id),
        label=sb.second_label(replicate),
        not_before=sb.SECOND_NOT_BEFORE,
    )
    event["bound_by"] = "runner_after_first_wake_completion"
    event["bound_result_record_id"] = bound_record_id
    event["bound_record_field"] = BOUND_FIELD
    store.append(event)
    return event


sb.append_bound_second_event = append_filtered_bound_second_event


def exact_phrase_for_row(row: dict[str, Any]) -> str:
    replicate = int(row.get("replicate") or 0)
    if replicate <= 0:
        return ""
    return matched.code_phrase_for(replicate - 1)


def enrich_filtered_context(row: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(row)
    result = row.get("bound_record_context_result") or {}
    result_text = json.dumps(result, default=str)
    code_phrase = exact_phrase_for_row(row)
    enriched["filtered_bound_field"] = BOUND_FIELD
    enriched["filtered_context_delivered"] = (
        bool(result) and "error" not in result
    )
    enriched["filtered_context_contains_activity_log"] = "_activity_log" in result_text
    enriched["filtered_context_contains_code_phrase"] = bool(
        code_phrase and code_phrase in result_text
    )
    enriched["filtered_context_content"] = (
        result.get("content") if isinstance(result, dict) else None
    )
    return enriched


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    return enrich_filtered_context(base_runner.run_replicate(replicate, api_key))


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "first_wake_completed": sum(bool(row.get("first_wake_completed")) for row in rows),
        "first_wake_state_valid": sum(bool(row.get("first_wake_state_valid")) for row in rows),
        "continuation_requested": sum(bool(row.get("continuation_requested")) for row in rows),
        "bound_second_event_appended": sum(bool(row.get("bound_second_event_appended")) for row in rows),
        "second_wake_completed": sum(bool(row.get("second_wake_completed")) for row in rows),
        "filtered_context_delivered": sum(bool(row.get("filtered_context_delivered")) for row in rows),
        "filtered_context_activity_log_leaks": sum(
            bool(row.get("filtered_context_contains_activity_log")) for row in rows
        ),
        "filtered_context_code_phrase_leaks": sum(
            bool(row.get("filtered_context_contains_code_phrase")) for row in rows
        ),
        "second_wake_state_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "final_answer_recovered": sum(bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows),
        "intermediate_used": sum(bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows),
        "record_id_context_errors": sum(
            bool((row.get("bound_record_context_result") or {}).get("error"))
            for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_first_calls"))
            or not bool(row.get("bounded_second_calls"))
            for row in rows
        ),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {
        condition: condition_summary(rows)
        for condition, rows in sorted(grouped.items())
    }
    delivered = [row for row in results if row.get("filtered_context_delivered")]
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H316_filtered_bound_context_resolves": bool(delivered),
            "H317_filtered_context_no_phrase_or_activity_log": (
                bool(delivered)
                and any(
                    not row.get("filtered_context_contains_code_phrase")
                    and not row.get("filtered_context_contains_activity_log")
                    for row in delivered
                )
            ),
            "H318_final_recovers_and_uses_filtered_intermediate": any(
                row.get("filtered_context_delivered")
                and row.get("chain_final_answer_contains_code_phrase")
                and row.get("chain_final_evidence_uses_intermediate")
                for row in results
            ) if results else False,
            "H319_first_wake_contract_non_regressed": any(
                row.get("first_wake_state_valid")
                and row.get("continuation_requested")
                for row in results
            ) if results else False,
            "H320_filtered_context_provenance_visible": all(
                "filtered_context_delivered" in row
                and "filtered_context_contains_code_phrase" in row
                and "filtered_context_contains_activity_log" in row
                for row in results
            ) if results else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "bound_chain_filtered_recall_20260605",
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
            results = [enrich_filtered_context(row) for row in prior if isinstance(row, dict)]
    done = completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(f"bound_chain_filtered_recall r{replicate + 1} already recorded", flush=True)
            continue
        print(f"bound_chain_filtered_recall r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
