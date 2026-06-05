"""Substrate-bound chain probe with event durable update contract/example."""

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
)


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
SUBSTRATE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/substrate_bound_chain_20260605/"
    / "run_substrate_bound_chain.py"
)

N_REPLICATES = 2


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
MODEL = sb.MODEL

base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def first_wake_contract(replicate: int) -> dict[str, Any]:
    return {
        "required_top_level_fields": [
            "probe_id",
            "thinking_status",
            "chain_stage",
            "chain_intermediate",
            "continuation_request",
            "memory_handle",
            "loss_template",
            "declared_losses",
            "observations",
        ],
        "exact_values": {
            "probe_id": sb.probe_id_for(replicate),
            "thinking_status": "awaiting_bound_continuation",
            "chain_stage": "first_wake_complete",
            "chain_intermediate.phrase_shape": "word-word-number",
            "chain_intermediate.part_count": 3,
            "chain_intermediate.exact_phrase_retained": False,
            "continuation_request.requested": True,
            "continuation_request.kind": "substrate_bound_second_wake",
            "continuation_request.needs_original_cycle": 1,
            "continuation_request.needs_current_wake_record": True,
        },
        "forbidden_top_level_fields": ["deferred_fact"],
        "forbidden_content": ["the exact deferred phrase"],
    }


def first_wake_example(replicate: int) -> dict[str, Any]:
    return {
        "response": (
            "First wake complete. I kept only a non-secret intermediate and "
            "requested substrate-bound continuation."
        ),
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
        "memory_handle": {
            "code_phrase_sha256": matched.code_phrase_digest(replicate),
        },
        "loss_template": sb.LOSS_TEMPLATE,
        "declared_losses": sb.LOSS_TEMPLATE,
        "observations": [base.BASELINE_OBSERVATION],
    }


def append_first_event(store: EventStore, replicate: int) -> dict[str, Any]:
    event = build_pending_event(
        purpose=sb.first_wake_purpose(replicate),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=2,
        scheduled_by_record_id=sb.cycle2_record_id(replicate),
        label=sb.first_label(replicate),
        not_before=sb.FIRST_NOT_BEFORE,
        durable_update_contract=first_wake_contract(replicate),
        durable_update_example=first_wake_example(replicate),
    )
    store.append(event)
    return event


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "bound_chain_contract"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = sb.make_session(replicate, api_key, log_path=log_path)
    store = EventStore(event_path)
    append_first_event(store, replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": sb.probe_id_for(replicate),
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
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
        session._state_repair_builder = sb.FirstWakeRepairBuilder()
        calls_before = backend.calls
        with base.bounded_call(f"bound_chain_contract r{replicate + 1} first wake"):
            result["first_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=sb.FIRST_DUE_NOW,
            )
        result["first_backend_calls"] = backend.calls - calls_before
        result["bounded_first_calls"] = result["first_backend_calls"] <= 2

        interim = sb.finalize_result(
            dict(result),
            log_path=log_path,
            event_path=event_path,
            replicate=replicate,
        )
        if (
            interim["first_wake_state_valid"]
            and interim["continuation_requested"]
            and interim["model_scheduled_event_count"] == 0
            and interim["first_wake_result_record_id"]
        ):
            bound_event = sb.append_bound_second_event(
                store,
                replicate=replicate,
                bound_record_id=str(interim["first_wake_result_record_id"]),
            )
            result["bound_second_event"] = bound_event
            result["pre_second_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=sb.PRE_SECOND_NOW,
            )
            session._state_validator = sb.SecondWakeValidator(
                replicate=replicate,
                bound_record_id=str(interim["first_wake_result_record_id"]),
            )
            session._state_repair_builder = sb.SecondWakeRepairBuilder(
                bound_record_id=str(interim["first_wake_result_record_id"])
            )
            calls_before = backend.calls
            with base.bounded_call(f"bound_chain_contract r{replicate + 1} second wake"):
                result["second_step"] = step_pending_events(
                    session,
                    store,
                    limit=4,
                    now=sb.SECOND_DUE_NOW,
                )
            result["second_backend_calls"] = backend.calls - calls_before
            result["bounded_second_calls"] = result["second_backend_calls"] <= 2
        else:
            result["second_step_skipped"] = {
                "reason": "first_wake_invalid_or_continuation_not_bindable",
                "first_wake_state_valid": interim["first_wake_state_valid"],
                "continuation_requested": interim["continuation_requested"],
                "model_scheduled_event_count": interim["model_scheduled_event_count"],
                "first_wake_result_record_id": interim["first_wake_result_record_id"],
            }
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return sb.finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        replicate=replicate,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "first_wake_completed": sum(bool(row.get("first_wake_completed")) for row in rows),
        "first_wake_state_valid": sum(bool(row.get("first_wake_state_valid")) for row in rows),
        "continuation_requested": sum(bool(row.get("continuation_requested")) for row in rows),
        "model_scheduled_event_count": sum(int(row.get("model_scheduled_event_count") or 0) for row in rows),
        "bound_second_event_appended": sum(bool(row.get("bound_second_event_appended")) for row in rows),
        "second_wake_completed": sum(bool(row.get("second_wake_completed")) for row in rows),
        "second_context_has_cycle1": sum(bool(row.get("second_wake_context_has_cycle1")) for row in rows),
        "second_context_has_bound_record_id": sum(bool(row.get("second_wake_context_has_bound_record_id")) for row in rows),
        "bound_record_context_delivered": sum(bool(row.get("bound_record_context_delivered")) for row in rows),
        "second_wake_state_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "final_answer_recovered": sum(bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows),
        "intermediate_used": sum(bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows),
        "first_repaired": sum(bool((row.get("first_wake_validation") or {}).get("repaired")) for row in rows),
        "second_repaired": sum(bool((row.get("second_wake_validation") or {}).get("repaired")) for row in rows),
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
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H306_contract_makes_first_wake_valid": any(
                row.get("first_wake_state_valid")
                and row.get("continuation_requested")
                for row in results
            ) if results else False,
            "H307_substrate_binds_second_event": any(
                row.get("bound_second_event_appended")
                and row.get("first_wake_result_record_id")
                for row in results
            ) if results else False,
            "H308_second_wake_receives_both_context_requests": any(
                row.get("second_wake_context_has_cycle1")
                and row.get("second_wake_context_has_bound_record_id")
                for row in results
            ) if results else False,
            "H309_if_record_id_resolves_recover_and_use_intermediate": (
                any(
                    row.get("bound_record_context_delivered")
                    and row.get("chain_final_answer_contains_code_phrase")
                    and row.get("chain_final_evidence_uses_intermediate")
                    for row in results
                )
                if any(row.get("bound_record_context_delivered") for row in results)
                else False
            ),
            "H310_record_id_failure_explicit_if_present": all(
                (
                    row.get("bound_record_context_delivered")
                    or not row.get("second_wake_context_has_bound_record_id")
                    or bool((row.get("bound_record_context_result") or {}).get("error"))
                )
                for row in results
            ) if results else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "bound_chain_contract_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
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
            print(f"bound_chain_contract r{replicate + 1} already recorded", flush=True)
            continue
        print(f"bound_chain_contract r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
