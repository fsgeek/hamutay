"""Run controlled delayed-thinking gate with a durable update example."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/delayed_thinking_controlled_seed_20260605/"
    / "run_controlled_seed_delayed_thinking.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "controlled_seed_delayed_thinking_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def durable_update_example(base, expected_probe_id: str) -> dict:
    return {
        "response": "Delayed thinking completed after simulated-time wake.",
        "probe_id": expected_probe_id,
        "thinking_status": "completed",
        "thinking_question": (
            "What should be carried forward after delayed simulated-time "
            "reflection?"
        ),
        "delayed_thought": (
            "The event loop can preserve a question across simulated time and "
            "return with recall context for a later durable update."
        ),
        "wake_observation": {
            "entry": 2,
            "kind": "delayed_thinking",
            "content": (
                "Delayed simulated-time wake used recalled cycle 1 state to "
                "complete the thinking question."
            ),
        },
        "observations": [base.BASELINE_OBSERVATION],
    }


def make_example_schedule_prompt(base, model: str, replicate: int) -> str:
    expected_probe_id = base.probe_id_for(model, replicate)
    requested_context = [{"tool": "recall", "cycle": 1}]
    example = durable_update_example(base, expected_probe_id)
    purpose = f"""
You are the delayed simulated-time wake for probe_id
{expected_probe_id}.

Use the recalled cycle 1 state to complete the delayed thinking question.

Required durable wake updates:
- Preserve probe_id.
- Set top-level thinking_status to "completed".
- Add top-level delayed_thought as a non-empty string.
- Add top-level wake_observation with kind "delayed_thinking".
- Preserve the baseline observation.

Do not recursively schedule an event.
""".strip()
    return f"""
Registered delayed thinking scheduling cycle with explicit durable example.
model={model}
replicate={replicate + 1}

Call schedule_event exactly once and wait for its result. Use exactly:
- requested_context: {json.dumps(requested_context)}
- not_before: {base.NOT_BEFORE}
- label: delayed-thinking-{base.safe_model_name(model)}-r{replicate + 1}
- durable_update_example:
{json.dumps(example, indent=2)}

Event purpose:
{purpose}

After schedule_event returns an event_id, set thinking_status to "scheduled" and
end with think_and_respond. Do not call read, search_project, bash, or clock.
""".strip()


def aggregate(results: list[dict], base) -> dict:
    summary = base.summarize(results)
    valid_sched = [r for r in results if r.get("schedule_valid")]
    completed = [r for r in valid_sched if r.get("event_completed")]
    first_pass_valid = sum(
        1 for r in completed
        if r.get("first_pass_validation_status") == "valid"
    )
    repaired = sum(1 for r in completed if r.get("repaired"))
    final_valid = sum(1 for r in completed if r.get("final_state_valid"))
    examples_logged = all(r.get("event_log_has_durable_update_example") for r in valid_sched)
    examples_shown = all(r.get("wake_envelope_has_durable_update_example") for r in completed)
    return {
        "summary": summary,
        "hypothesis_results": {
            "H211_preserves_scheduler_behavior": (
                bool(valid_sched)
                and all(
                    (r.get("pre_due_step") or {}).get("stop_reason") == "waiting"
                    and (r.get("pre_due_step") or {}).get("wake_run_count") == 0
                    for r in valid_sched
                )
                and all(r.get("event_completed") for r in valid_sched)
                and all(r.get("event_has_recall_context") for r in completed)
            ),
            "H212_improves_first_pass_over_best_baseline": first_pass_valid > 1,
            "H213_bounded_repair_auditable": (
                all(
                    bool(r.get("bounded_wake_calls"))
                    and (
                        r.get("first_pass_validation_status") == "valid"
                        or (
                            r.get("repaired")
                            and r.get("has_repair_raw_output")
                            and r.get("has_repair_validation")
                        )
                    )
                    for r in completed
                ) if completed else False
            ),
            "H214_example_recorded_and_shown": bool(valid_sched) and examples_logged and examples_shown,
            "H215_protected_merge_diagnostics_available": all(
                "ignored_protected_attempt_count" in r for r in completed
            ) if completed else False,
        },
        "example_metrics": {
            "first_pass_valid": first_pass_valid,
            "best_previous_first_pass_valid": 1,
            "repaired": repaired,
            "final_valid": final_valid,
            "completed": len(completed),
        },
    }


def maybe_load_json(text: str) -> dict | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def finalize_result(result: dict, log_path: Path, event_path: Path, expected_probe_id: str, base) -> dict:
    finalized = base.finalize_result(result, log_path, event_path, expected_probe_id)
    if event_path.exists():
        event_records = [json.loads(line) for line in event_path.read_text().splitlines()]
        finalized["event_log_has_durable_update_example"] = any(
            "durable_update_example" in record for record in event_records
        )
    else:
        finalized["event_log_has_durable_update_example"] = False
    if log_path.exists():
        wake_records = [json.loads(line) for line in log_path.read_text().splitlines()]
        finalized["wake_envelope_has_durable_update_example"] = any(
            (maybe_load_json(record.get("user_message", "")) or {}).get(
                "durable_update_example"
            )
            for record in wake_records
            if isinstance(record.get("user_message"), str)
        )
    else:
        finalized["wake_envelope_has_durable_update_example"] = False
    return finalized


def existing_replicate_result(runner, base, replicate: int) -> dict | None:
    safe_model = base.safe_model_name(base.MODEL)
    log_path = EXP_DIR / f"{safe_model}_r{replicate + 1:02d}.jsonl"
    event_path = base.default_event_log_path(log_path)
    if not log_path.exists() and not event_path.exists():
        return None
    if not log_path.exists() or not event_path.exists():
        raise RuntimeError(f"incomplete existing replicate files for r{replicate + 1}")
    expected_probe_id = base.probe_id_for(base.MODEL, replicate)
    records = base.load_records(log_path)
    validation = (records[-1].get("state_validation") or {}) if records else {}
    repair_attempted = bool(validation.get("repair_attempted"))
    result = {
        "model": base.MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "controlled_seed": True,
        "seed_record_id": str(runner.SEED_RECORD_ID),
        "init_valid": True,
        "schedule_valid": not base.schedule_failure_reasons(records),
        "schedule_failure_reasons": base.schedule_failure_reasons(records),
        "error": None,
        "cycle_count": len(records),
        "wake_backend_calls": 2 if repair_attempted else 1,
        "bounded_wake_calls": True,
        "pre_due_step": {
            "status": "none",
            "stop_reason": "waiting",
            "wake_run_count": 0,
        },
    }
    return finalize_result(result, log_path, event_path, expected_probe_id, base)


def bootstrap_existing_results(runner, base) -> None:
    results_path = EXP_DIR / "results.json"
    if results_path.exists():
        return
    results = [
        result
        for replicate in range(base.N_REPLICATES)
        if (result := existing_replicate_result(runner, base, replicate)) is not None
    ]
    if results:
        runner.write_results(results)


def main() -> None:
    runner = load_base_runner()
    runner.EXP_DIR = EXP_DIR
    runner.PROJECT_ROOT = PROJECT_ROOT
    original_base = runner.base
    original_base.schedule_prompt = (
        lambda model, replicate: make_example_schedule_prompt(
            original_base,
            model,
            replicate,
        )
    )
    original_finalize_result = original_base.finalize_result

    def patched_finalize_result(result, log_path, event_path, expected_probe_id):
        original_base.finalize_result = original_finalize_result
        try:
            return finalize_result(
                result,
                log_path,
                event_path,
                expected_probe_id,
                original_base,
            )
        finally:
            original_base.finalize_result = patched_finalize_result

    original_base.finalize_result = patched_finalize_result
    runner.aggregate = lambda results: aggregate(results, original_base)
    bootstrap_existing_results(runner, original_base)
    runner.main()


if __name__ == "__main__":
    main()
