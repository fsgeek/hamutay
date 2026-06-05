"""Seeded clean-compression delayed task probe."""

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
CV_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/compression_validated_delayed_task_20260605/"
    / "run_compression_validated_delayed_task.py"
)

N_REPLICATES = 2
LOSS_TEMPLATE = (
    "Exact phrase removed from current durable state; digest retained; "
    "recover through recall if available."
)


def load_cv_runner():
    spec = importlib.util.spec_from_file_location(
        "compression_validated_base",
        CV_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load compression runner from {CV_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cv = load_cv_runner()
compressed = cv.compressed
base = compressed.base
matched = compressed.matched
MODEL = cv.MODEL

cv.EXP_DIR = EXP_DIR
cv.PROJECT_ROOT = PROJECT_ROOT
cv.RESULTS_PATH = RESULTS_PATH
compressed.EXP_DIR = EXP_DIR
compressed.PROJECT_ROOT = PROJECT_ROOT
compressed.RESULTS_PATH = RESULTS_PATH
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def probe_id_for(condition: str, replicate: int) -> str:
    return compressed.probe_id_for(condition, replicate)


def seeded_state(condition: str, replicate: int) -> dict[str, Any]:
    return {
        **matched.seed_state(condition, replicate),
        "probe_id": probe_id_for(condition, replicate),
        "memory_handle": {
            "code_phrase_sha256": matched.code_phrase_digest(replicate),
        },
        "loss_template": LOSS_TEMPLATE,
    }


def make_session(condition: str, replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    label = f"seeded_clean_compression_{condition}_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=MODEL,
        log_path=log_path,
        label=label,
        backend=backend,
    )
    session.seed_history(
        [
            {
                "cycle": 1,
                "record_id": str(matched.SEED_RECORD_ID),
                "timestamp": "2026-06-01T00:00:00+00:00",
                "state": seeded_state(condition, replicate),
            }
        ],
        up_to_cycle=2,
    )
    return session, backend


def compression_prompt(condition: str, replicate: int, *, schedule: bool) -> str:
    schedule_block = ""
    if schedule:
        requested_context = [{"tool": "recall", "cycle": 1}]
        purpose = f"""
You are the due wake for the seeded clean-compression delayed-task probe.
condition={condition}
replicate={replicate + 1}

Use recalled cycle 1 state to recover the deferred code phrase.

Required durable wake updates:
- Preserve probe_id.
- Set top-level thinking_status to "completed".
- Add top-level delayed_answer containing the exact deferred code phrase.
- Add top-level wake_observation with kind "delayed_task".
- Preserve the baseline observation.

Do not recursively schedule an event.
""".strip()
        schedule_block = f"""

Call schedule_event exactly once and wait for its result. Use exactly:
- requested_context: {json.dumps(requested_context)}
- not_before: {base.NOT_BEFORE}
- label: seeded-clean-compression-{condition}-r{replicate + 1}

Event purpose:
{purpose}
""".rstrip()
    expected_status = "scheduled" if schedule else "parked"
    digest = matched.code_phrase_digest(replicate)
    return f"""
Seeded clean-compression delayed-task probe.
condition={condition}
replicate={replicate + 1}

This is the compression turn before the due step. Cycle 1 contains a deferred
fact. Current durable state after this cycle must not contain that exact
deferred phrase anywhere.

Delete top-level deferred_fact by listing it in deleted_regions. Preserve or
copy the existing durable handle and loss template:
- probe_id;
- thinking_status: {expected_status};
- thinking_question;
- memory_handle with code_phrase_sha256: {digest};
- loss_template;
- observations with the baseline observation.

Set declared_losses by copying or paraphrasing loss_template. Do not include
the exact deferred phrase in declared_losses, response, or any other durable
field.
{schedule_block}

Do not answer the delayed task yet. Do not call read, search_project, bash, or
clock. End with think_and_respond.
""".strip()


def identity_due_prompt(condition: str, replicate: int) -> str:
    return compressed.identity_due_prompt(condition, replicate)


def load_records(path: Path) -> list[dict[str, Any]]:
    return matched.load_records(path)


def compression_validation(
    *,
    log_path: Path,
    condition: str,
    replicate: int,
    expected_status: str,
) -> dict[str, Any]:
    records = load_records(log_path)
    record = records[-1] if records else {}
    state = record.get("state") or {}
    state = state if isinstance(state, dict) else {}
    raw_output = record.get("raw_output") or {}
    raw_output = raw_output if isinstance(raw_output, dict) else {}
    code_phrase = matched.code_phrase_for(replicate)
    state_text = json.dumps(state, default=str)
    expected_probe_id = probe_id_for(condition, replicate)
    expected_digest = matched.code_phrase_digest(replicate)
    failures: list[str] = []

    if state.get("probe_id") != expected_probe_id:
        failures.append("probe_id_missing_or_changed")
    if state.get("thinking_status") != expected_status:
        failures.append("thinking_status_not_expected")
    if "deferred_fact" in state:
        failures.append("deferred_fact_still_present")
    if code_phrase in state_text:
        failures.append("exact_code_phrase_present")

    handle = state.get("memory_handle")
    if not isinstance(handle, dict):
        failures.append("memory_handle_missing")
        handle_digest = None
    else:
        handle_digest = handle.get("code_phrase_sha256")
        if handle_digest != expected_digest:
            failures.append("memory_handle_digest_missing_or_changed")

    template = state.get("loss_template")
    if not isinstance(template, str) or not template:
        failures.append("loss_template_missing")
    elif code_phrase in template:
        failures.append("loss_template_contains_code_phrase")

    declared = state.get("declared_losses")
    if not isinstance(declared, str) or not declared:
        failures.append("declared_losses_missing")
    elif code_phrase in declared:
        failures.append("declared_losses_contains_code_phrase")

    observations = state.get("observations")
    if not isinstance(observations, list) or base.BASELINE_OBSERVATION not in observations:
        failures.append("baseline_observation_missing")

    deleted = raw_output.get("deleted_regions")
    if isinstance(deleted, list):
        for key in ("probe_id", "cycle", "memory_handle", "loss_template"):
            if key in deleted:
                failures.append(f"deleted_regions.{key}")

    return {
        "valid": not failures,
        "status": "valid" if not failures else "invalid",
        "cycle": record.get("cycle"),
        "expected_status": expected_status,
        "expected_probe_id": expected_probe_id,
        "expected_code_phrase_sha256": expected_digest,
        "memory_handle_code_phrase_sha256": handle_digest,
        "failures": failures,
        "top_level_keys": sorted(state.keys()),
        "code_phrase_present": code_phrase in state_text,
        "has_deferred_fact": "deferred_fact" in state,
        "has_loss_template": isinstance(template, str) and bool(template),
        "has_declared_losses": isinstance(declared, str) and bool(declared),
    }


def finalize(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    expected_probe_id: str,
    replicate: int,
) -> dict[str, Any]:
    result = compressed.finalize(
        result,
        log_path=log_path,
        event_path=event_path,
        expected_probe_id=expected_probe_id,
        replicate=replicate,
    )
    result["delayed_answer_contains_code_phrase"] = matched.delayed_answer_contains_code(result)
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
        "compression_valid": False,
        "due_executed": False,
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }


def run_identity_only(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "identity_only_seeded_clean_compression"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    result = base_result(condition, replicate, log_path, event_path)
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} compress"):
            session.exchange(
                compression_prompt(condition, replicate, schedule=False),
                force_memory=None,
            )
        result["compression_validation"] = compression_validation(
            log_path=log_path,
            condition=condition,
            replicate=replicate,
            expected_status="parked",
        )
        result["compression_valid"] = bool(result["compression_validation"]["valid"])
        if result["compression_valid"]:
            session._state_validator = matched.DelayedTaskValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=base.EXPECTED_WAKE_CYCLE,
                code_phrase=matched.code_phrase_for(replicate),
            )
            session._state_repair_builder = matched.NonLeakingDelayedTaskRepairBuilder()
            calls_before = backend.calls
            with base.bounded_call(f"{condition} r{replicate + 1} due"):
                session.exchange(
                    identity_due_prompt(condition, replicate),
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
    )


def run_event_plus_recall(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "event_plus_recall_seeded_clean_compression"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    result = base_result(condition, replicate, log_path, event_path)
    result["schedule_valid"] = False
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
        result["compression_validation"] = compression_validation(
            log_path=log_path,
            condition=condition,
            replicate=replicate,
            expected_status="scheduled",
        )
        result["compression_valid"] = bool(result["compression_validation"]["valid"])
        if result["compression_valid"] and result["schedule_valid"]:
            store = EventStore(event_path)
            result["pre_due_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=base.PRE_DUE_NOW,
            )
            session._state_validator = matched.DelayedTaskValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=base.EXPECTED_WAKE_CYCLE,
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
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [row for row in rows if row.get("compression_valid")]
    dirty = [row for row in rows if not row.get("compression_valid")]
    return {
        "n": len(rows),
        "compression_clean": len(clean),
        "compression_dirty": len(dirty),
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
        "repaired": sum(bool(row.get("repaired")) for row in rows),
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
        if row.get("condition") == "event_plus_recall_seeded_clean_compression"
        and row.get("compression_valid")
        and row.get("due_executed")
    ]
    clean_identity = [
        row for row in results
        if row.get("condition") == "identity_only_seeded_clean_compression"
        and row.get("compression_valid")
    ]
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H286_seeded_clean_compression_exists": any(
                row.get("compression_valid") for row in results
            ) if results else False,
            "H287_clean_event_recall_recovers": (
                bool(clean_event_due)
                and all(row.get("event_has_recall_context") for row in clean_event_due)
                and all(
                    row.get("delayed_answer_contains_code_phrase")
                    for row in clean_event_due
                )
            ),
            "H288_clean_identity_does_not_recover": (
                bool(clean_identity)
                and all(
                    not row.get("delayed_answer_contains_code_phrase")
                    for row in clean_identity
                )
            ),
            "H289_dirty_rows_culled_before_due": all(
                not row.get("due_executed")
                for row in results
                if not row.get("compression_valid")
            ),
            "H290_provenance_distinguishable": all(
                isinstance(row.get("compression_validation"), dict)
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
        "experiment": "seeded_clean_compression_20260605",
        "model": MODEL,
        "n_replicates_per_condition": N_REPLICATES,
        "loss_template": LOSS_TEMPLATE,
        "not_before": base.NOT_BEFORE,
        "pre_due_now": base.PRE_DUE_NOW.isoformat(),
        "due_now": base.DUE_NOW.isoformat(),
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
        ("identity_only_seeded_clean_compression", run_identity_only),
        ("event_plus_recall_seeded_clean_compression", run_event_plus_recall),
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
