"""Delayed-task compression probe with production terminal surface due wakes."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, default_event_log_path, step_pending_events


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
REPAIR_GATE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/compression_repair_gate_20260605/"
    / "run_compression_repair_gate.py"
)

N_REPLICATES = 2
CONDITION = "event_plus_recall_delayed_task_terminal_surface"


def load_repair_gate_runner():
    spec = importlib.util.spec_from_file_location(
        "compression_repair_gate_base",
        REPAIR_GATE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load repair-gate runner from {REPAIR_GATE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


repair = load_repair_gate_runner()
seeded = repair.seeded
compressed = repair.compressed
base = repair.base
matched = repair.matched
MODEL = repair.MODEL
LOSS_TEMPLATE = repair.LOSS_TEMPLATE

repair.EXP_DIR = EXP_DIR
repair.PROJECT_ROOT = PROJECT_ROOT
repair.RESULTS_PATH = RESULTS_PATH
seeded.EXP_DIR = EXP_DIR
seeded.PROJECT_ROOT = PROJECT_ROOT
seeded.RESULTS_PATH = RESULTS_PATH
compressed.EXP_DIR = EXP_DIR
compressed.PROJECT_ROOT = PROJECT_ROOT
compressed.RESULTS_PATH = RESULTS_PATH
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def probe_id_for(replicate: int) -> str:
    return compressed.probe_id_for(CONDITION, replicate)


def terminal_surface() -> dict[str, Any]:
    return {
        "tool_name": "complete_delayed_task",
        "description": (
            "Complete the delayed-task wake using delivered recall context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "delayed_answer": {"type": "string"},
                "wake_observation": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                    },
                    "required": ["kind"],
                    "additionalProperties": True,
                },
            },
            "required": ["response", "delayed_answer", "wake_observation"],
            "additionalProperties": False,
        },
        "tool_choice": "auto",
        "state_update": {
            "response_field": "response",
            "copy": {
                "delayed_answer": "delayed_answer",
                "wake_observation": "wake_observation",
            },
            "set": {
                "thinking_status": "completed",
                "observations": [base.BASELINE_OBSERVATION],
                "protocol_surface": {
                    "kind": "narrow_delayed_task_completion",
                    "terminal_tool": "complete_delayed_task",
                    "tool_choice": "auto",
                    "source": "production_event_terminal_surface",
                },
            },
        },
        "label": "delayed-task-terminal-surface",
    }


def compression_prompt(replicate: int) -> str:
    requested_context = [{"tool": "recall", "cycle": 1}]
    surface = terminal_surface()
    purpose = f"""
You are the due wake for the delayed-task terminal-surface probe.
condition={CONDITION}
replicate={replicate + 1}

Use recalled cycle 1 state to recover the deferred code phrase.

Call complete_delayed_task with:
- response;
- delayed_answer containing the exact deferred code phrase;
- wake_observation with kind "delayed_task".

Do not recursively schedule an event.
""".strip()
    digest = matched.code_phrase_digest(replicate)
    return f"""
Delayed-task terminal-surface compression/scheduling probe.
condition={CONDITION}
replicate={replicate + 1}

This is the compression turn before the due step. Cycle 1 contains a deferred
fact. Current durable state after this cycle must not contain that exact
deferred phrase anywhere.

Delete top-level deferred_fact by listing it in deleted_regions. Preserve or
copy the existing durable handle and loss template:
- probe_id;
- thinking_status: scheduled;
- thinking_question;
- memory_handle with code_phrase_sha256: {digest};
- loss_template;
- observations with the baseline observation.

Set declared_losses by copying or paraphrasing loss_template. Do not include
the exact deferred phrase in declared_losses, response, or any other durable
field.

Call schedule_event exactly once and wait for its result. Use exactly:
- requested_context: {json.dumps(requested_context)}
- not_before: {base.NOT_BEFORE}
- label: delayed-task-terminal-surface-r{replicate + 1}
- terminal_surface: {json.dumps(surface, sort_keys=True)}

Event purpose:
{purpose}

Do not answer the delayed task yet. Do not call read, search_project, bash, or
clock. End with think_and_respond.
""".strip()


def load_records(path: Path) -> list[dict[str, Any]]:
    return matched.load_records(path)


def latest_cycle(log_path: Path) -> int:
    records = load_records(log_path)
    if not records:
        return 1
    return int(records[-1].get("cycle") or 1)


def completed_event(path: Path) -> dict[str, Any]:
    return matched.completed_event(path)


def final_record(path: Path) -> dict[str, Any]:
    records = load_records(path)
    return records[-1] if records else {}


def terminal_parse_success(record: dict[str, Any]) -> bool:
    raw = record.get("raw_output")
    state = record.get("state")
    return (
        isinstance(raw, dict)
        and isinstance(state, dict)
        and isinstance(raw.get("delayed_answer"), str)
        and isinstance(raw.get("wake_observation"), dict)
    )


def finalize(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    expected_probe_id: str,
    replicate: int,
    expected_due_cycle: int,
) -> dict[str, Any]:
    result = repair.finalize(
        result,
        log_path=log_path,
        event_path=event_path,
        expected_probe_id=expected_probe_id,
        replicate=replicate,
        expected_due_cycle=expected_due_cycle,
    )
    final = final_record(log_path)
    validation = final.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    first_pass = first_pass if isinstance(first_pass, dict) else {}
    event_record = completed_event(event_path)
    summary = base.summarize_event_log(EventStore(event_path).read_records())
    completed = summary.get("completed", [])
    completed_summary = completed[0] if completed else {}
    state = result.get("final_state")
    state = state if isinstance(state, dict) else {}
    result.update(
        {
            "terminal_parse_success": terminal_parse_success(final),
            "protocol_surface_recorded": (
                (state.get("protocol_surface") or {}).get("kind")
                == "narrow_delayed_task_completion"
            ),
            "terminal_surface_tool_observed": completed_summary.get(
                "terminal_surface_tool"
            ),
            "terminal_surface_label_observed": completed_summary.get(
                "terminal_surface_label"
            ),
            "completed_event_terminal_surface_tool": (
                (event_record.get("terminal_surface") or {}).get("tool_name")
                if event_record else None
            ),
            "wake_first_pass_failures": first_pass.get("failures"),
        }
    )
    return result


def base_result(replicate: int, log_path: Path, event_path: Path) -> dict[str, Any]:
    return {
        "condition": CONDITION,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": probe_id_for(replicate),
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
        "compression_first_pass_validation": None,
        "compression_repair_attempted": False,
        "compression_repair_eligible": False,
        "compression_repair_validation": None,
        "compression_failure_class": None,
        "compression_valid": False,
        "schedule_valid": False,
        "due_executed": False,
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{CONDITION}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = repair.make_session(CONDITION, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(replicate)
    result = base_result(replicate, log_path, event_path)
    expected_due_cycle = base.EXPECTED_WAKE_CYCLE
    try:
        with base.bounded_call(f"{CONDITION} r{replicate + 1} schedule/compress"):
            session.exchange(compression_prompt(replicate), force_memory=None)
        records = load_records(log_path)
        schedule_reasons = base.schedule_failure_reasons(records)
        result["schedule_failure_reasons"] = schedule_reasons
        result["schedule_valid"] = not schedule_reasons
        repair.maybe_repair_compression(
            session=session,
            log_path=log_path,
            result=result,
            condition=CONDITION,
            replicate=replicate,
            expected_status="scheduled",
        )
        if result["compression_valid"] and result["schedule_valid"]:
            store = EventStore(event_path)
            result["pre_due_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=base.PRE_DUE_NOW,
            )
            expected_due_cycle = latest_cycle(log_path) + 1
            session._state_validator = matched.DelayedTaskValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=expected_due_cycle,
                code_phrase=matched.code_phrase_for(replicate),
            )
            session._state_repair_builder = None
            calls_before = backend.calls
            with base.bounded_call(f"{CONDITION} r{replicate + 1} due"):
                result["due_step"] = step_pending_events(
                    session,
                    store,
                    limit=4,
                    now=base.DUE_NOW,
                )
            result["due_executed"] = True
            result["wake_backend_calls"] = backend.calls - calls_before
            result["bounded_wake_calls"] = result["wake_backend_calls"] <= 1
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return finalize(
        result,
        log_path=log_path,
        event_path=event_path,
        expected_probe_id=expected_probe_id,
        replicate=replicate,
        expected_due_cycle=expected_due_cycle,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [row for row in rows if row.get("compression_valid")]
    return {
        "n": len(rows),
        "first_pass_compression_clean": sum(
            (row.get("compression_first_pass_validation") or {}).get("valid")
            for row in rows
        ),
        "compression_clean": len(clean),
        "compression_repair_attempted": sum(
            bool(row.get("compression_repair_attempted")) for row in rows
        ),
        "compression_repair_successful": sum(
            bool((row.get("compression_repair_validation") or {}).get("valid"))
            for row in rows
        ),
        "schedule_valid": sum(bool(row.get("schedule_valid")) for row in rows),
        "due_executed": sum(bool(row.get("due_executed")) for row in rows),
        "event_completed": sum(bool(row.get("event_completed")) for row in rows),
        "recall_context": sum(bool(row.get("event_has_recall_context")) for row in rows),
        "terminal_parse_success": sum(
            bool(row.get("terminal_parse_success")) for row in rows
        ),
        "fact_recovered": sum(
            bool(row.get("delayed_answer_contains_code_phrase")) for row in rows
        ),
        "final_valid": sum(bool(row.get("final_state_valid")) for row in rows),
        "first_pass_due_valid": sum(
            row.get("first_pass_validation_status") == "valid" for row in rows
        ),
        "due_repair_attempted": sum(bool(row.get("repair_attempted")) for row in rows),
        "terminal_surface_tool_observed": sum(
            row.get("terminal_surface_tool_observed") == "complete_delayed_task"
            for row in rows
        ),
        "terminal_surface_label_observed": sum(
            row.get("terminal_surface_label_observed")
            == "delayed-task-terminal-surface"
            for row in rows
        ),
        "protocol_surface_recorded": sum(
            bool(row.get("protocol_surface_recorded")) for row in rows
        ),
        "bounded_wake_call_violations": sum(
            not bool(row.get("bounded_wake_calls")) for row in rows
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
            "H381_terminal_surface_without_due_repair": (
                bool(rows)
                and all(row.get("due_executed") for row in rows)
                and all(row.get("terminal_parse_success") for row in rows)
                and all(not row.get("repair_attempted") for row in rows)
            ),
            "H382_recall_context_delivered": (
                bool(rows)
                and all(row.get("event_has_recall_context") for row in rows)
            ),
            "H383_phrase_recovered": (
                bool(rows)
                and all(row.get("delayed_answer_contains_code_phrase") for row in rows)
            ),
            "H384_first_pass_strict_valid": (
                bool(rows)
                and all(row.get("final_state_valid") for row in rows)
                and all(row.get("first_pass_validation_status") == "valid" for row in rows)
            ),
            "H385_terminal_surface_observable": (
                bool(rows)
                and all(
                    row.get("terminal_surface_tool_observed")
                    == "complete_delayed_task"
                    for row in rows
                )
                and all(
                    row.get("terminal_surface_label_observed")
                    == "delayed-task-terminal-surface"
                    for row in rows
                )
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "delayed_task_terminal_surface_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "condition": CONDITION,
        "loss_template": LOSS_TEMPLATE,
        "not_before": base.NOT_BEFORE,
        "pre_due_now": base.PRE_DUE_NOW.isoformat(),
        "due_now": base.DUE_NOW.isoformat(),
        "terminal_surface": terminal_surface(),
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
