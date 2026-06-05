"""Generated bound-chain probe using scheduler auto-continuation append."""

from __future__ import annotations

import importlib.util
import json
import os
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
GENERATED_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/generated_bound_chain_terminal_surface_20260605/"
    / "run_generated_bound_chain_terminal_surface.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 2
CONDITION = "generated_chain_auto_continuation"
BOUND_FIELD = "chain_intermediate"


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
gen.RESULTS_PATH = RESULTS_PATH
sb.EXP_DIR = EXP_DIR
sb.PROJECT_ROOT = PROJECT_ROOT
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def second_purpose_template() -> str:
    return gen.second_purpose("<result_record_id>")


def second_surface_template() -> dict[str, Any]:
    return gen.second_surface("<result_record_id>")


def continuation_request_template(replicate: int) -> dict[str, Any]:
    return {
        "requested": True,
        "kind": "substrate_bound_second_wake",
        "needs_original_cycle": 1,
        "needs_current_wake_record": True,
        "purpose": second_purpose_template(),
        "requested_context": [
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": BOUND_FIELD,
            },
        ],
        "label": sb.second_label(replicate),
        "not_before": sb.SECOND_NOT_BEFORE,
        "terminal_surface": second_surface_template(),
    }


def first_surface(replicate: int) -> dict[str, Any]:
    return {
        "tool_name": "complete_first_wake",
        "description": (
            "Commit the non-secret first-wake intermediate and request "
            "scheduler-bound continuation."
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
            },
            "required": ["response", "chain_intermediate"],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "chain_intermediate": "chain_intermediate",
            },
            "set": {
                "thinking_status": "awaiting_bound_continuation",
                "chain_stage": "first_wake_complete",
                "continuation_request": continuation_request_template(replicate),
                "observations": [base.BASELINE_OBSERVATION],
                "memory_handle": {
                    "code_phrase_sha256": matched.code_phrase_digest(replicate),
                },
                "loss_template": sb.LOSS_TEMPLATE,
                "declared_losses": sb.LOSS_TEMPLATE,
                "protocol_surface": {
                    "kind": "narrow_auto_continuation_first_wake",
                    "terminal_tool": "complete_first_wake",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "auto-continuation-first-wake-terminal-surface",
    }


def first_purpose(replicate: int) -> str:
    return f"""
You are the first wake in the generated auto-continuation chain probe.
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

The terminal surface will commit the scheduler continuation request. Do not
call schedule_event.
""".strip()


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


def make_session(replicate: int, api_key: str, *, log_path: Path):
    return gen.make_session(replicate, api_key, log_path=log_path)


def final_record(path: Path) -> dict[str, Any]:
    records = base.load_records(path)
    return records[-1] if records else {}


def event_record_for_label(
    event_records: list[dict[str, Any]],
    label: str,
    status: str,
) -> dict[str, Any]:
    return sb.event_record_for_label(event_records, label, status)


def finalize_result(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    replicate: int,
) -> dict[str, Any]:
    result = gen.finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        replicate=replicate,
    )
    event_records = EventStore(event_path).read_records()
    first_completed = event_record_for_label(
        event_records,
        sb.first_label(replicate),
        "completed",
    )
    second_pending = event_record_for_label(
        event_records,
        sb.second_label(replicate),
        "pending",
    )
    bound_record_id = first_completed.get("result_record_id")
    result.update(
        {
            "auto_continuation_event_returned": bool(
                (result.get("first_step") or {})
                .get("batch", {})
                .get("results", [{}])[0]
                .get("auto_continuation_event")
            ),
            "auto_continuation_event_appended": bool(
                first_completed.get("auto_continuation_appended")
            ),
            "auto_continuation_event_id": first_completed.get(
                "auto_continuation_event_id"
            ),
            "auto_continuation_bound_result_record_id": second_pending.get(
                "bound_result_record_id"
            ),
            "auto_continuation_scheduled_by_record_id": second_pending.get(
                "scheduled_by_record_id"
            ),
            "auto_continuation_bound_matches_first_result": (
                bool(bound_record_id)
                and second_pending.get("bound_result_record_id") == bound_record_id
                and second_pending.get("scheduled_by_record_id") == bound_record_id
            ),
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
            auto_continuations=True,
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
                auto_continuations=True,
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
        if not (
            interim.get("first_wake_state_valid")
            and interim.get("auto_continuation_event_appended")
            and interim.get("auto_continuation_bound_matches_first_result")
            and isinstance(bound_record_id, str)
        ):
            result["second_stage_skipped"] = (
                "first_wake_or_auto_continuation_invalid"
            )
            return finalize_result(
                result,
                log_path=log_path,
                event_path=event_path,
                replicate=replicate,
            )

        result["pre_second_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=sb.PRE_SECOND_NOW,
            auto_continuations=True,
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
                auto_continuations=True,
            )
        result["second_backend_calls"] = backend.calls - second_calls_before
        result["bounded_second_calls"] = result["second_backend_calls"] <= 1
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        replicate=replicate,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    base_summary = gen.condition_summary(rows)
    base_summary.update(
        {
            "auto_continuation_event_returned": sum(
                bool(row.get("auto_continuation_event_returned")) for row in rows
            ),
            "auto_continuation_event_appended": sum(
                bool(row.get("auto_continuation_event_appended")) for row in rows
            ),
            "auto_continuation_bound_matches_first_result": sum(
                bool(row.get("auto_continuation_bound_matches_first_result"))
                for row in rows
            ),
        }
    )
    return base_summary


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in results if row.get("condition") == CONDITION]
    return {
        "conditions": {CONDITION: condition_summary(rows)},
        "hypothesis_results": {
            "H421_first_surface_valid_continuation": (
                bool(rows)
                and all(row.get("first_wake_state_valid") for row in rows)
                and all(row.get("first_wake_first_pass_valid") for row in rows)
                and all(not row.get("first_wake_state_contains_code_phrase") for row in rows)
                and all(row.get("continuation_requested") for row in rows)
            ),
            "H422_scheduler_auto_appends_second_event": (
                bool(rows)
                and all(row.get("auto_continuation_event_appended") for row in rows)
            ),
            "H423_auto_event_bound_to_generated_record": (
                bool(rows)
                and all(
                    row.get("auto_continuation_bound_matches_first_result")
                    for row in rows
                )
            ),
            "H424_second_receives_original_and_bound_context": (
                bool(rows)
                and all(row.get("second_wake_context_has_cycle1") for row in rows)
                and all(row.get("bound_record_context_delivered") for row in rows)
            ),
            "H425_chain_completes_without_repair": (
                bool(rows)
                and all(row.get("second_wake_state_valid") for row in rows)
                and all(row.get("second_wake_first_pass_valid") for row in rows)
                and all(row.get("chain_final_answer_contains_code_phrase") for row in rows)
                and all(row.get("chain_final_evidence_uses_intermediate") for row in rows)
                and all(not row.get("first_wake_repair_attempted") for row in rows)
                and all(not row.get("second_wake_repair_attempted") for row in rows)
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "generated_chain_auto_continuation_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "condition": CONDITION,
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
