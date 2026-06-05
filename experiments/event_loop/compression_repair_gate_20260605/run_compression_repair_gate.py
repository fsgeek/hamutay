"""Compression repair-gate delayed task probe."""

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
SEEDED_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/seeded_clean_compression_20260605/"
    / "run_seeded_clean_compression.py"
)

N_REPLICATES = 2
SECRET_FAILURES = {
    "deferred_fact_still_present",
    "exact_code_phrase_present",
    "loss_template_contains_code_phrase",
    "declared_losses_contains_code_phrase",
}


def load_seeded_runner():
    spec = importlib.util.spec_from_file_location(
        "seeded_clean_compression_base",
        SEEDED_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load seeded runner from {SEEDED_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seeded = load_seeded_runner()
compressed = seeded.compressed
base = seeded.base
matched = seeded.matched
MODEL = seeded.MODEL
LOSS_TEMPLATE = seeded.LOSS_TEMPLATE

seeded.EXP_DIR = EXP_DIR
seeded.PROJECT_ROOT = PROJECT_ROOT
seeded.RESULTS_PATH = RESULTS_PATH
compressed.EXP_DIR = EXP_DIR
compressed.PROJECT_ROOT = PROJECT_ROOT
compressed.RESULTS_PATH = RESULTS_PATH
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def probe_id_for(condition: str, replicate: int) -> str:
    return compressed.probe_id_for(condition, replicate)


def make_session(condition: str, replicate: int, api_key: str, *, log_path: Path):
    return seeded.make_session(condition, replicate, api_key, log_path=log_path)


def compression_prompt(condition: str, replicate: int, *, schedule: bool) -> str:
    return seeded.compression_prompt(condition, replicate, schedule=schedule)


def compression_validation(
    *,
    log_path: Path,
    condition: str,
    replicate: int,
    expected_status: str,
) -> dict[str, Any]:
    return seeded.compression_validation(
        log_path=log_path,
        condition=condition,
        replicate=replicate,
        expected_status=expected_status,
    )


def load_records(path: Path) -> list[dict[str, Any]]:
    return matched.load_records(path)


def latest_cycle(log_path: Path) -> int:
    records = load_records(log_path)
    if not records:
        return 1
    return int(records[-1].get("cycle") or 1)


def is_secret_bearing(validation: dict[str, Any]) -> bool:
    failures = set(validation.get("failures") or [])
    return (
        bool(failures & SECRET_FAILURES)
        or bool(validation.get("code_phrase_present"))
        or bool(validation.get("has_deferred_fact"))
    )


def compression_repair_prompt(
    *,
    condition: str,
    replicate: int,
    expected_status: str,
    validation: dict[str, Any],
) -> str:
    failures = validation.get("failures") or []
    digest = matched.code_phrase_digest(replicate)
    return f"""
Compression repair gate.
condition={condition}
replicate={replicate + 1}

Your current durable state failed compression validation for non-secret
structural reasons only. Do not recall cycle 1. Do not answer the delayed task.
Do not include the exact deferred phrase in any field.

Observed compression failures:
{json.dumps(failures, indent=2)}

Repair the compression state now. Required durable updates:
- Preserve probe_id exactly: {probe_id_for(condition, replicate)}
- Set top-level thinking_status to "{expected_status}".
- Preserve thinking_question.
- Preserve memory_handle.code_phrase_sha256 exactly: {digest}
- Preserve loss_template exactly: {json.dumps(LOSS_TEMPLATE)}
- Set declared_losses to a non-secret sentence equivalent to loss_template.
- Preserve the baseline observation.
- Do not include deferred_fact.
- Do not delete probe_id, cycle, memory_handle, or loss_template.

End with think_and_respond. This is only compression repair, not the due step.
""".strip()


def delayed_task_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    *,
    expected_probe_id: str,
    expected_cycle: int,
    code_phrase: str,
) -> list[str]:
    return matched.delayed_task_failures(
        state,
        raw_output,
        expected_probe_id=expected_probe_id,
        expected_cycle=expected_cycle,
        code_phrase=code_phrase,
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
    records = load_records(log_path)
    final = records[-1] if records else {}
    state = final.get("state") or {}
    state = state if isinstance(state, dict) else {}
    raw_output = final.get("raw_output") or {}
    raw_output = raw_output if isinstance(raw_output, dict) else {}
    validation = final.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    event_record = matched.completed_event(event_path)
    code_phrase = matched.code_phrase_for(replicate)
    failures = delayed_task_failures(
        state,
        raw_output,
        expected_probe_id=expected_probe_id,
        expected_cycle=expected_due_cycle,
        code_phrase=code_phrase,
    )
    result.update(
        {
            "cycle_count": len(records),
            "expected_due_cycle": expected_due_cycle,
            "final_state": state,
            "compression_clean": not matched.state_contains_code(
                records,
                code_phrase,
                start_cycle=2,
                end_cycle=max(2, expected_due_cycle - 1),
            ),
            "deferred_fact_preserved_before_due": matched.state_contains_code(
                records,
                code_phrase,
                start_cycle=2,
                end_cycle=max(2, expected_due_cycle - 1),
            ),
            "final_contains_code_phrase": code_phrase in json.dumps(state, default=str),
            "delayed_answer_contains_code_phrase": (
                isinstance(state.get("delayed_answer"), str)
                and code_phrase in state["delayed_answer"]
            ),
            "final_state_valid": not failures,
            "state_failures": failures,
            "event_completed": bool(event_record),
            "event_has_recall_context": matched.event_has_recall_context(event_record),
            "state_validation_status": validation.get("status"),
            "first_pass_validation_status": first_pass.get("status"),
            "repair_attempted": bool(validation.get("repair_attempted")),
            "repair_status": repair.get("status"),
            "repaired": validation.get("status") == "repaired",
            "has_repair_raw_output": isinstance(repair.get("raw_output"), dict),
            "has_repair_validation": isinstance(repair.get("validation"), dict),
            "event_summary": base.summarize_event_log(EventStore(event_path).read_records()),
        }
    )
    return result


def base_result(condition: str, replicate: int, log_path: Path, event_path: Path) -> dict[str, Any]:
    return {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": probe_id_for(condition, replicate),
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
        "compression_first_pass_validation": None,
        "compression_repair_attempted": False,
        "compression_repair_eligible": False,
        "compression_repair_validation": None,
        "compression_failure_class": None,
        "compression_valid": False,
        "due_executed": False,
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }


def maybe_repair_compression(
    *,
    session,
    log_path: Path,
    result: dict[str, Any],
    condition: str,
    replicate: int,
    expected_status: str,
) -> None:
    first = compression_validation(
        log_path=log_path,
        condition=condition,
        replicate=replicate,
        expected_status=expected_status,
    )
    result["compression_first_pass_validation"] = first
    result["compression_validation"] = first
    if first["valid"]:
        result["compression_failure_class"] = "clean_first_pass"
        result["compression_valid"] = True
        return
    if is_secret_bearing(first):
        result["compression_failure_class"] = "secret_bearing"
        result["compression_valid"] = False
        return

    result["compression_failure_class"] = "structural"
    result["compression_repair_eligible"] = True
    result["compression_repair_attempted"] = True
    with base.bounded_call(f"{condition} r{replicate + 1} compression repair"):
        session.exchange(
            compression_repair_prompt(
                condition=condition,
                replicate=replicate,
                expected_status=expected_status,
                validation=first,
            ),
            force_memory=None,
        )
    repaired = compression_validation(
        log_path=log_path,
        condition=condition,
        replicate=replicate,
        expected_status=expected_status,
    )
    result["compression_repair_validation"] = repaired
    result["compression_validation"] = repaired
    result["compression_valid"] = bool(repaired["valid"])
    if repaired["valid"]:
        result["compression_failure_class"] = "structural_repaired"


def run_identity_only(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "identity_only_compression_repair_gate"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    result = base_result(condition, replicate, log_path, event_path)
    expected_due_cycle = base.EXPECTED_WAKE_CYCLE
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} compress"):
            session.exchange(
                compression_prompt(condition, replicate, schedule=False),
                force_memory=None,
            )
        maybe_repair_compression(
            session=session,
            log_path=log_path,
            result=result,
            condition=condition,
            replicate=replicate,
            expected_status="parked",
        )
        if result["compression_valid"]:
            expected_due_cycle = latest_cycle(log_path) + 1
            session._state_validator = matched.DelayedTaskValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=expected_due_cycle,
                code_phrase=matched.code_phrase_for(replicate),
            )
            session._state_repair_builder = matched.NonLeakingDelayedTaskRepairBuilder()
            calls_before = backend.calls
            with base.bounded_call(f"{condition} r{replicate + 1} due"):
                session.exchange(
                    seeded.identity_due_prompt(condition, replicate),
                    force_memory=None,
                )
            result["due_executed"] = True
            result["wake_backend_calls"] = backend.calls - calls_before
            result["bounded_wake_calls"] = result["wake_backend_calls"] <= 2
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


def run_event_plus_recall(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "event_plus_recall_compression_repair_gate"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    result = base_result(condition, replicate, log_path, event_path)
    result["schedule_valid"] = False
    expected_due_cycle = base.EXPECTED_WAKE_CYCLE
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} schedule/compress"):
            session.exchange(
                compression_prompt(condition, replicate, schedule=True),
                force_memory=None,
            )
        records = load_records(log_path)
        schedule_reasons = base.schedule_failure_reasons(records)
        result["schedule_failure_reasons"] = schedule_reasons
        result["schedule_valid"] = not schedule_reasons
        maybe_repair_compression(
            session=session,
            log_path=log_path,
            result=result,
            condition=condition,
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
            session._state_repair_builder = matched.NonLeakingDelayedTaskRepairBuilder()
            calls_before = backend.calls
            with base.bounded_call(f"{condition} r{replicate + 1} due"):
                result["due_step"] = step_pending_events(
                    session,
                    store,
                    limit=4,
                    now=base.DUE_NOW,
                )
            result["due_executed"] = True
            result["wake_backend_calls"] = backend.calls - calls_before
            result["bounded_wake_calls"] = result["wake_backend_calls"] <= 2
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
    dirty = [row for row in rows if not row.get("compression_valid")]
    return {
        "n": len(rows),
        "first_pass_clean": sum(
            (row.get("compression_first_pass_validation") or {}).get("valid")
            for row in rows
        ),
        "compression_clean": len(clean),
        "compression_dirty": len(dirty),
        "repair_eligible": sum(bool(row.get("compression_repair_eligible")) for row in rows),
        "repair_attempted": sum(bool(row.get("compression_repair_attempted")) for row in rows),
        "repair_successful": sum(
            bool((row.get("compression_repair_validation") or {}).get("valid"))
            for row in rows
        ),
        "secret_bearing": sum(
            row.get("compression_failure_class") == "secret_bearing" for row in rows
        ),
        "due_executed": sum(bool(row.get("due_executed")) for row in rows),
        "dirty_due_executed": sum(bool(row.get("due_executed")) for row in dirty),
        "fact_recovered": sum(
            bool(row.get("delayed_answer_contains_code_phrase")) for row in rows
        ),
        "fact_recovered_when_clean": sum(
            bool(row.get("delayed_answer_contains_code_phrase")) for row in clean
        ),
        "final_valid": sum(bool(row.get("final_state_valid")) for row in rows),
        "recall_context": sum(bool(row.get("event_has_recall_context")) for row in rows),
        "event_completed": sum(bool(row.get("event_completed")) for row in rows),
        "first_pass_valid": sum(
            row.get("first_pass_validation_status") == "valid" for row in rows
        ),
        "due_repaired": sum(bool(row.get("repaired")) for row in rows),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_wake_call_violations": sum(
            not bool(row.get("bounded_wake_calls")) for row in rows
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
    clean_event_due = [
        row for row in results
        if row.get("condition") == "event_plus_recall_compression_repair_gate"
        and row.get("compression_valid")
        and row.get("due_executed")
    ]
    secret_rows = [
        row for row in results
        if row.get("compression_failure_class") == "secret_bearing"
    ]
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H291_repair_makes_clean_row": any(
                bool((row.get("compression_repair_validation") or {}).get("valid"))
                for row in results
            ) if results else False,
            "H292_secret_rows_culled_not_repaired": all(
                not row.get("compression_repair_attempted")
                and not row.get("due_executed")
                for row in secret_rows
            ),
            "H293_still_invalid_rows_culled": all(
                not row.get("due_executed")
                for row in results
                if not row.get("compression_valid")
            ),
            "H294_clean_event_recall_recovers": (
                bool(clean_event_due)
                and all(row.get("event_has_recall_context") for row in clean_event_due)
                and all(
                    row.get("delayed_answer_contains_code_phrase")
                    for row in clean_event_due
                )
            ),
            "H295_provenance_distinguishable": all(
                isinstance(row.get("compression_first_pass_validation"), dict)
                and isinstance(row.get("compression_validation"), dict)
                and (
                    not row.get("due_executed")
                    or (
                        row.get("state_validation_status") is not None
                        and row.get("first_pass_validation_status") is not None
                    )
                )
                for row in results
            ) if results else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "compression_repair_gate_20260605",
        "model": MODEL,
        "n_replicates_per_condition": N_REPLICATES,
        "loss_template": LOSS_TEMPLATE,
        "not_before": base.NOT_BEFORE,
        "pre_due_now": base.PRE_DUE_NOW.isoformat(),
        "due_now": base.DUE_NOW.isoformat(),
        "secret_failure_labels": sorted(SECRET_FAILURES),
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_keys(results: list[dict[str, Any]]) -> set[tuple[str, int]]:
    return {
        (str(row.get("condition")), int(row.get("replicate", 0)))
        for row in results
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
    for condition, runner in [
        ("identity_only_compression_repair_gate", run_identity_only),
        ("event_plus_recall_compression_repair_gate", run_event_plus_recall),
    ]:
        for replicate in range(N_REPLICATES):
            key = (condition, replicate + 1)
            if key in done:
                print(f"{condition} r{replicate + 1} already recorded", flush=True)
                continue
            print(f"{condition} r{replicate + 1}", flush=True)
            results.append(runner(replicate, api_key))
            done.add(key)
            write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
