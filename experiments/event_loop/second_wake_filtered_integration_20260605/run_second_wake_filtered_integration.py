"""Second-wake-only filtered integration stability panel."""

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


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
SUBSTRATE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/substrate_bound_chain_20260605/"
    / "run_substrate_bound_chain.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 6
BOUND_FIELD = "chain_intermediate"
CONDITION = "second_wake_filtered_integration"
CODE_PHRASES = [
    "cobalt-bridge-11",
    "silver-maple-23",
    "green-cinder-37",
    "orange-canal-41",
    "indigo-signal-59",
    "white-anchor-67",
]


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
        f"hamutay-second-wake-filtered-integration-20260605-{label}",
    )


def cycle3_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-3-r{replicate + 1}")


def second_label(replicate: int) -> str:
    return f"second-wake-filtered-integration-r{replicate + 1}"


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


def expected_second_wake_object(replicate: int, bound_record_id: str) -> dict[str, Any]:
    return {
        "response": (
            "Second wake complete. I used cycle-1 recall for the exact phrase "
            "and filtered bound-record recall for the non-secret intermediate."
        ),
        "probe_id": sb.probe_id_for(replicate),
        "thinking_status": "bound_chain_completed",
        "chain_stage": "second_wake_complete",
        "bound_record_id_used": bound_record_id,
        "chain_final_answer": (
            "Use the exact phrase from delivered cycle-1 recall here; do not "
            "invent it."
        ),
        "chain_final_evidence": {
            "cycle1_recall_used": True,
            "filtered_bound_record_id": bound_record_id,
            "filtered_bound_field": BOUND_FIELD,
            "phrase_shape": "word-word-number",
            "source_cycle": 1,
        },
        "observations": [base.BASELINE_OBSERVATION],
    }


class StrongSecondWakeRepairBuilder:
    def __init__(self, *, replicate: int, bound_record_id: str):
        self.replicate = replicate
        self.bound_record_id = bound_record_id

    def build_repair_prompt(self, **kwargs) -> str:
        return f"""
Second-wake filtered integration object repair.

Your prior second-wake durable object failed validation. The exact deferred
phrase is intentionally not shown in this repair instruction. It was delivered
to you earlier in this same wake through cycle-1 recall; copy it from that
delivered context.

Validation context:
{json.dumps(kwargs, indent=2, default=str)}

Emit a durable object matching this non-secret shape. Copy these as real
think_and_respond fields, not as prose-only descriptions:
{json.dumps(expected_second_wake_object(self.replicate, self.bound_record_id), indent=2, default=str)}

Rules:
- chain_final_answer must contain the exact phrase from delivered cycle-1
  recall.
- chain_final_evidence must reference phrase_shape "word-word-number" from the
  delivered filtered bound-record field.
- bound_record_id_used must equal {json.dumps(self.bound_record_id)}.
- Preserve the baseline observation.
- Do not call schedule_event.
- Do not delete probe_id, cycle, observations, chain_final_answer,
  chain_final_evidence, chain_stage, or thinking_status.

End with think_and_respond.
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


def append_second_event(
    store: EventStore,
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
        scheduled_by_record_id=UUID(bound_record_id),
        label=second_label(replicate),
        not_before=sb.SECOND_NOT_BEFORE,
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
    validation = record.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    repair_validation = repair.get("validation") if isinstance(repair, dict) else {}
    repair_validation = repair_validation if isinstance(repair_validation, dict) else {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status"),
        "first_pass_failures": first_pass.get("failures"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair.get("status") if isinstance(repair, dict) else None,
        "repair_failures": repair_validation.get("failures"),
        "repaired": validation.get("status") == "repaired",
    }


def classify_failures(
    *,
    context_delivered: bool,
    second_failures: list[str],
    error: str | None,
) -> list[str]:
    labels: list[str] = []
    if error:
        labels.append("runner_or_backend_error")
    if not context_delivered:
        labels.append("context_delivery_failure")
    for failure in second_failures:
        if failure.startswith("chain_final") or failure in {
            "thinking_status_not_bound_chain_completed",
            "chain_stage_not_second_wake_complete",
            "bound_record_id_used_missing_or_changed",
            "baseline_observation_missing",
        }:
            labels.append(f"durable_integration:{failure}")
        elif failure.startswith("deleted_regions."):
            labels.append(f"delete_update_conflict:{failure}")
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
    cycle1_result = context_result_for(completed, tool="recall", cycle=1)
    bound_result = context_result_for(
        completed,
        tool="recall",
        record_id=bound_record_id,
    )
    code_phrase = matched.code_phrase_for(replicate)
    filtered_context_text = json.dumps(bound_result, default=str)
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
    result.update(
        {
            "cycle_count": len(records),
            "event_summary": base.summarize_event_log(event_records),
            "second_wake_completed": bool(completed),
            "second_wake_context_has_cycle1": bool(cycle1_result),
            "second_wake_context_has_bound_record_id": bool(bound_result),
            "cycle1_context_delivered": cycle1_delivered,
            "filtered_context_delivered": filtered_delivered,
            "both_contexts_delivered": context_delivered,
            "filtered_bound_field": BOUND_FIELD,
            "filtered_context_contains_activity_log": "_activity_log" in filtered_context_text,
            "filtered_context_contains_code_phrase": code_phrase in filtered_context_text,
            "filtered_context_content": (
                bound_result.get("content") if isinstance(bound_result, dict) else None
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
                error=result.get("error"),
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
        "second_backend_calls": 0,
        "bounded_second_calls": True,
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
        session._state_repair_builder = StrongSecondWakeRepairBuilder(
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
        result["second_backend_calls"] = backend.calls - calls_before
        result["bounded_second_calls"] = result["second_backend_calls"] <= 2
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
        "second_wake_completed": sum(bool(row.get("second_wake_completed")) for row in rows),
        "both_contexts_delivered": sum(bool(row.get("both_contexts_delivered")) for row in rows),
        "cycle1_context_delivered": sum(bool(row.get("cycle1_context_delivered")) for row in rows),
        "filtered_context_delivered": sum(bool(row.get("filtered_context_delivered")) for row in rows),
        "filtered_context_activity_log_leaks": sum(
            bool(row.get("filtered_context_contains_activity_log")) for row in rows
        ),
        "filtered_context_code_phrase_leaks": sum(
            bool(row.get("filtered_context_contains_code_phrase")) for row in rows
        ),
        "first_pass_valid": sum(
            (row.get("second_wake_validation") or {}).get("first_pass_status") == "valid"
            for row in rows
        ),
        "repair_attempted": sum(
            bool((row.get("second_wake_validation") or {}).get("repair_attempted"))
            for row in rows
        ),
        "repair_valid": sum(
            (row.get("second_wake_validation") or {}).get("repair_status") == "valid"
            for row in rows
        ),
        "final_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "final_answer_recovered": sum(
            bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows
        ),
        "intermediate_used": sum(
            bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows
        ),
        "visible_phrase_leaks": sum(
            bool(row.get("visible_state_contains_code_phrase")) for row in rows
        ),
        "activity_log_phrase_leaks": sum(
            bool(row.get("activity_log_contains_code_phrase")) for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_second_calls")) for row in rows
        ),
        "failure_labels": dict(sorted(failure_labels.items())),
        "second_wake_failure_labels": dict(sorted(second_failures.items())),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {
        condition: condition_summary(rows)
        for condition, rows in sorted(grouped.items())
    }
    both_delivered = sum(bool(row.get("both_contexts_delivered")) for row in results)
    final_valid = sum(bool(row.get("second_wake_state_valid")) for row in results)
    repair_valid = sum(
        (row.get("second_wake_validation") or {}).get("repair_status") == "valid"
        for row in results
    )
    valid_recovered = [
        row for row in results
        if row.get("second_wake_state_valid")
        and row.get("chain_final_answer_contains_code_phrase")
        and row.get("chain_final_evidence_uses_intermediate")
    ]
    labels_distinguishable = all(
        isinstance(row.get("failure_labels"), list)
        and all(
            label.startswith(("context_delivery_failure", "durable_integration:", "delete_update_conflict:", "runner_or_backend_error", "other:"))
            for label in row.get("failure_labels") or []
        )
        for row in results
    )
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H331_filtered_context_delivery_at_least_5_of_6": both_delivered >= 5,
            "H332_strong_repair_converts_at_least_one": repair_valid > 0,
            "H333_at_least_half_final_valid": final_valid >= 3,
            "H334_valid_rows_recover_phrase_and_reference_intermediate": bool(valid_recovered),
            "H335_failure_labels_distinguish_delivery_vs_integration": labels_distinguishable,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "second_wake_filtered_integration_20260605",
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
