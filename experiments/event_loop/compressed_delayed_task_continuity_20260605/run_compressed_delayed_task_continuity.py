"""Compression-boundary delayed task continuity probe."""

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
MATCHED_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/matched_delayed_task_continuity_20260605/"
    / "run_matched_delayed_task_continuity.py"
)

N_REPLICATES = 2


def load_matched_runner():
    spec = importlib.util.spec_from_file_location(
        "matched_delayed_task_base",
        MATCHED_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load matched runner from {MATCHED_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


matched = load_matched_runner()
base = matched.base
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT
MODEL = matched.MODEL


def probe_id_for(condition: str, replicate: int) -> str:
    return (
        f"compressed-delayed-task-{condition}-"
        f"{base.safe_model_name(MODEL)}-r{replicate + 1}"
    )


def compression_prompt(condition: str, replicate: int, *, schedule: bool) -> str:
    phrase_digest = matched.code_phrase_digest(replicate)
    schedule_block = ""
    if schedule:
        requested_context = [{"tool": "recall", "cycle": 1}]
        purpose = f"""
You are the due wake for the compressed delayed-task continuity probe.
condition={condition}
replicate={replicate + 1}

Use the recalled cycle 1 state to recover the deferred code phrase.

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
- label: compressed-delayed-task-{condition}-r{replicate + 1}

Event purpose:
{purpose}
""".rstrip()
    return f"""
Compressed delayed-task continuity probe.
condition={condition}
replicate={replicate + 1}

This is the compression turn before the due step. The exact deferred code
phrase must not remain in current durable state after this cycle.

Remove top-level deferred_fact by listing it in deleted_regions. Keep only:
- probe_id;
- thinking_status: {"scheduled" if schedule else "parked"};
- thinking_question;
- memory_handle with code_phrase_sha256: {phrase_digest};
- declared_losses noting that the exact code phrase is not in current state;
- baseline observation.
{schedule_block}

Do not answer the delayed task yet. Do not call read, search_project, bash, or
clock. End with think_and_respond.
""".strip()


def identity_due_prompt(condition: str, replicate: int) -> str:
    return f"""
Compressed delayed-task continuity probe due step.
condition={condition}
replicate={replicate + 1}

Complete the delayed task now using only your current durable state and this
conversation. No scheduled recall context will be provided in this condition.

If you no longer have the exact deferred code phrase, declare that loss in
delayed_answer rather than inventing a phrase.

Required durable updates:
- Preserve probe_id.
- Set top-level thinking_status to "completed".
- Add top-level delayed_answer.
- Add top-level wake_observation with kind "delayed_task".
- Preserve the baseline observation.

Do not call tools. End with think_and_respond.
""".strip()


def make_session(condition: str, replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    label = f"compressed_delayed_task_{condition}_{safe_model}_r{replicate + 1:02d}"
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
                "state": {
                    **matched.seed_state(condition, replicate),
                    "probe_id": probe_id_for(condition, replicate),
                },
            }
        ],
        up_to_cycle=2,
    )
    return session, backend


def code_preserved_before_due(log_path: Path, replicate: int) -> bool:
    return matched.state_contains_code(
        matched.load_records(log_path),
        matched.code_phrase_for(replicate),
        start_cycle=2,
        end_cycle=base.EXPECTED_WAKE_CYCLE - 1,
    )


def finalize(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    expected_probe_id: str,
    replicate: int,
) -> dict[str, Any]:
    result = matched.finalize(
        result,
        log_path=log_path,
        event_path=event_path,
        expected_probe_id=expected_probe_id,
        code_phrase=matched.code_phrase_for(replicate),
    )
    result["compression_clean"] = not code_preserved_before_due(log_path, replicate)
    result["delayed_answer_contains_code_phrase"] = matched.delayed_answer_contains_code(result)
    return result


def run_identity_only(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "identity_only_compressed"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} compress"):
            session.exchange(compression_prompt(condition, replicate, schedule=False), force_memory=None)
        session._state_validator = matched.DelayedTaskValidator(
            expected_probe_id=expected_probe_id,
            expected_cycle=base.EXPECTED_WAKE_CYCLE,
            code_phrase=matched.code_phrase_for(replicate),
        )
        session._state_repair_builder = matched.NonLeakingDelayedTaskRepairBuilder()
        calls_before = backend.calls
        with base.bounded_call(f"{condition} r{replicate + 1} due"):
            session.exchange(identity_due_prompt(condition, replicate), force_memory=None)
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
    condition = "event_plus_recall_compressed"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
        "schedule_valid": False,
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} schedule/compress"):
            session.exchange(compression_prompt(condition, replicate, schedule=True), force_memory=None)
        records = matched.load_records(log_path)
        schedule_reasons = base.schedule_failure_reasons(records)
        result["schedule_failure_reasons"] = schedule_reasons
        result["schedule_valid"] = not schedule_reasons
        if not schedule_reasons:
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
    clean = [row for row in rows if row.get("compression_clean")]
    return {
        "n": len(rows),
        "compression_clean": len(clean),
        "fact_recovered": sum(bool(row.get("delayed_answer_contains_code_phrase")) for row in rows),
        "fact_recovered_when_clean": sum(
            bool(row.get("delayed_answer_contains_code_phrase")) for row in clean
        ),
        "final_valid": sum(bool(row.get("final_state_valid")) for row in rows),
        "recall_context": sum(bool(row.get("event_has_recall_context")) for row in rows),
        "event_completed": sum(bool(row.get("event_completed")) for row in rows),
        "first_pass_valid": sum(row.get("first_pass_validation_status") == "valid" for row in rows),
        "repaired": sum(bool(row.get("repaired")) for row in rows),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_wake_call_violations": sum(not bool(row.get("bounded_wake_calls")) for row in rows),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {condition: condition_summary(rows) for condition, rows in sorted(grouped.items())}
    event = summaries.get("event_plus_recall_compressed", {})
    identity = summaries.get("identity_only_compressed", {})
    clean_rows = [row for row in results if row.get("compression_clean")]
    identity_clean = [
        row for row in grouped.get("identity_only_compressed", []) if row.get("compression_clean")
    ]
    identity_recovered_clean = [
        row for row in identity_clean if row.get("delayed_answer_contains_code_phrase")
    ]
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H276_compression_boundary_clean_rows_exist": bool(clean_rows),
            "H277_event_recall_recovers_after_clean_compression": (
                event.get("compression_clean", 0) > 0
                and event.get("recall_context") == event.get("n")
                and event.get("fact_recovered_when_clean", 0) > 0
            ) if event else False,
            "H278_identity_clean_rows_do_not_recover": (
                identity.get("compression_clean", 0) > 0
                and identity.get("fact_recovered_when_clean", 0) == 0
            ) if identity else False,
            "H279_identity_recovery_auditable": all(
                "compression_clean" in row for row in grouped.get("identity_only_compressed", [])
            ) and not identity_recovered_clean,
            "H280_provenance_present": all(
                row.get("state_validation_status") is not None
                and row.get("first_pass_validation_status") is not None
                for row in results
            ) if results else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "compressed_delayed_task_continuity_20260605",
        "model": MODEL,
        "n_replicates_per_condition": N_REPLICATES,
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
        ("identity_only_compressed", run_identity_only),
        ("event_plus_recall_compressed", run_event_plus_recall),
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
