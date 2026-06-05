"""Run delayed-thinking simulated-time gate with controlled cycle-1 seed."""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import EventStore, default_event_log_path, step_pending_events

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/delayed_thinking_simtime_20260605/"
    / "run_delayed_thinking_simtime.py"
)
SEED_RECORD_ID = UUID("00000000-0000-0000-0000-000000000101")


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "delayed_thinking_simtime_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base_runner()


def seed_state(model: str, replicate: int) -> dict[str, Any]:
    return {
        "cycle": 1,
        "probe_id": base.probe_id_for(model, replicate),
        "thinking_status": "initialized",
        "thinking_question": (
            "What should be carried forward after delayed simulated-time "
            "reflection?"
        ),
        "observations": [base.BASELINE_OBSERVATION],
    }


def seed_history(session, model: str, replicate: int) -> None:
    session.seed_history(
        [
            {
                "cycle": 1,
                "record_id": str(SEED_RECORD_ID),
                "timestamp": datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
                "state": seed_state(model, replicate),
            }
        ],
        up_to_cycle=2,
    )


def run_replicate(model: str, replicate: int, api_key: str) -> dict:
    safe_model = base.safe_model_name(model)
    log_path = EXP_DIR / f"{safe_model}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    label = f"delayed_thinking_controlled_seed_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=model,
        log_path=log_path,
        label=label,
        backend=backend,
    )
    seed_history(session, model, replicate)
    expected_probe_id = base.probe_id_for(model, replicate)
    result: dict[str, Any] = {
        "model": model,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "controlled_seed": True,
        "seed_record_id": str(SEED_RECORD_ID),
        "init_valid": True,
        "schedule_valid": False,
        "error": None,
        "cycle_count": 0,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
    }
    try:
        with base.bounded_call(f"{model} r{replicate + 1} schedule"):
            session.exchange(base.schedule_prompt(model, replicate), force_memory=None)
        records = base.load_records(log_path)
        schedule_reasons = base.schedule_failure_reasons(records)
        result["schedule_failure_reasons"] = schedule_reasons
        result["schedule_valid"] = not schedule_reasons
        if schedule_reasons:
            return base.finalize_result(result, log_path, event_path, expected_probe_id)

        store = EventStore(event_path)
        result["pre_due_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=base.PRE_DUE_NOW,
        )
        session._state_validator = base.DelayedThinkingValidator(
            expected_probe_id=expected_probe_id,
            expected_cycle=base.EXPECTED_WAKE_CYCLE,
        )
        session._state_repair_builder = base.DelayedThinkingRepairBuilder(
            expected_probe_id=expected_probe_id,
            expected_cycle=base.EXPECTED_WAKE_CYCLE,
        )
        calls_before = backend.calls
        with base.bounded_call(f"{model} r{replicate + 1} due step"):
            result["due_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=base.DUE_NOW,
            )
        result["wake_backend_calls"] = backend.calls - calls_before
        result["bounded_wake_calls"] = result["wake_backend_calls"] <= 2
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = base.format_error(exc)
    return base.finalize_result(result, log_path, event_path, expected_probe_id)


def aggregate(results: list[dict]) -> dict:
    summary = base.summarize(results)
    valid_sched = [r for r in results if r.get("schedule_valid")]
    completed = [r for r in valid_sched if r.get("event_completed")]
    return {
        "summary": summary,
        "hypothesis_results": {
            "H197_schedules_exactly_one_future_recall_event": bool(valid_sched),
            "H198_pre_due_step_waits_without_running": (
                all(
                    (r.get("pre_due_step") or {}).get("stop_reason") == "waiting"
                    and (r.get("pre_due_step") or {}).get("wake_run_count") == 0
                    for r in valid_sched
                ) if valid_sched else False
            ),
            "H199_due_step_delivers_event_and_recall_context": (
                all(r.get("event_has_recall_context") for r in completed)
                if completed else False
            ),
            "H200_delayed_wake_produces_valid_state_transition": any(
                r.get("final_state_valid") for r in completed
            ),
            "H201_bounded_repair_auditable": (
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
        },
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "model": base.MODEL,
        "n_replicates": base.N_REPLICATES,
        "max_tokens": base.MAX_TOKENS,
        "not_before": base.NOT_BEFORE,
        "pre_due_now": base.PRE_DUE_NOW.isoformat(),
        "due_now": base.DUE_NOW.isoformat(),
        "protected_state_fields": sorted(base.PROTECTED_STATE_FIELDS),
        "controlled_seed": True,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict] = []
    results_path = EXP_DIR / "results.json"
    if results_path.exists():
        prior = json.loads(results_path.read_text()).get("results", [])
        if isinstance(prior, list):
            results = prior
    completed = {
        int(result.get("replicate", 0))
        for result in results
    }
    for replicate in range(base.N_REPLICATES):
        if replicate + 1 in completed:
            print(f"{base.MODEL} r{replicate + 1} already recorded", flush=True)
            continue
        print(f"{base.MODEL} r{replicate + 1}", flush=True)
        results.append(run_replicate(base.MODEL, replicate, api_key))
        write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
