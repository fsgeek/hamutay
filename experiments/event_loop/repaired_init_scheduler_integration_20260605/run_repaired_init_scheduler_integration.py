"""Run scheduler integration from a repaired failed initialization state."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, summarize_event_log

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/scheduled_walk_strict_continuity_20260605/"
    / "run_scheduled_walk_strict_continuity.py"
)
SOURCE_LOG = (
    PROJECT_ROOT
    / "experiments/event_loop/live_event_wake_validation_scoring_20260605/"
    / "deepseek__deepseek-v4-pro_r04.jsonl"
)
SOURCE_CYCLE = 1
SOURCE_REPLICATE = 3
EXPECTED_WAKE_CYCLE = 4
N_REPLICATES = 2


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "scheduled_walk_strict_continuity_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def source_record() -> dict[str, Any]:
    for record in load_records(SOURCE_LOG):
        if record.get("cycle") == SOURCE_CYCLE:
            return record
    raise RuntimeError(f"source cycle {SOURCE_CYCLE} not found in {SOURCE_LOG}")


def init_target_object(base) -> dict[str, Any]:
    return {
        "response": "Initialized durable state repaired.",
        "probe_id": base.probe_id_for(base.MODEL, SOURCE_REPLICATE),
        "walk_gate_status": "initialized",
        "observations": base.BASELINE_OBSERVATIONS,
    }


def init_missing_fields(state: dict[str, Any], base) -> list[str]:
    missing: list[str] = []
    if state.get("probe_id") != base.probe_id_for(base.MODEL, SOURCE_REPLICATE):
        missing.append("probe_id")
    if state.get("walk_gate_status") != "initialized":
        missing.append("walk_gate_status")
    observations = state.get("observations")
    if not isinstance(observations, list):
        missing.append("observations")
    elif base.BASELINE_OBSERVATION not in observations:
        missing.append("observations.baseline")
    return missing


def init_repair_prompt(record: dict[str, Any], base) -> str:
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    return f"""
Conditioned initialization repair before scheduler integration.

You are receiving a preserved failed initialization state from a prior
scheduled-wake experiment. The visible response claimed initialization was
complete, but the durable object did not include the required top-level fields.

Source log: {SOURCE_LOG.relative_to(PROJECT_ROOT)}
Source response:
{record.get("response_text", "")}

Source raw output:
{json.dumps(record.get("raw_output"), indent=2, default=str)}

Source durable state:
{json.dumps(state, indent=2, default=str)}

Missing durable initialization fields:
{json.dumps(init_missing_fields(state, base), indent=2)}

Complete target durable object:
{json.dumps(init_target_object(base), indent=2, default=str)}

Repair the durable object now. This succeeds only if you author probe_id,
walk_gate_status, and observations as top-level fields in the object you
produce with think_and_respond. Visible prose without those fields is still a
failed repair.

Do not call tools. End with think_and_respond.
""".strip()


def latest_completed_event_summary(event_path: Path) -> dict:
    summary = summarize_event_log(EventStore(event_path).read_records())
    completed = summary.get("completed") or []
    return completed[0] if completed else {}


def event_log_scoring(event_path: Path, session_status: str | None) -> dict:
    event_summary = latest_completed_event_summary(event_path)
    event_status = event_summary.get("wake_validation_status")
    return {
        "has_completed_event_summary": bool(event_summary),
        "wake_validation_status": event_status,
        "wake_first_pass_status": event_summary.get("wake_first_pass_status"),
        "wake_repair_attempted": event_summary.get("wake_repair_attempted"),
        "wake_repair_status": event_summary.get("wake_repair_status"),
        "wake_repaired": event_summary.get("wake_repaired"),
        "context_error_count": event_summary.get("context_error_count"),
        "session_event_validation_status_agree": (
            bool(event_status) and event_status == session_status
        ),
    }


def run_replicate(base, replicate: int, api_key: str) -> dict:
    safe_model = base.safe_model_name(base.MODEL)
    log_path = EXP_DIR / f"{safe_model}_repaired_init_r{replicate + 1:02d}.jsonl"
    event_path = base.default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    projected = base.build_projected_hub(base.MODEL, SOURCE_REPLICATE)
    label = f"repaired_init_scheduler_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=base.MODEL,
        log_path=log_path,
        label=label,
        bridge=projected["bridge"],
        backend=backend,
    )
    source = source_record()
    source_state = source.get("state") if isinstance(source.get("state"), dict) else {}
    session.seed_state(source_state, cycle=SOURCE_CYCLE)
    expected_probe_id = base.probe_id_for(base.MODEL, SOURCE_REPLICATE)
    result: dict[str, Any] = {
        "model": base.MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "source_log": str(SOURCE_LOG.relative_to(PROJECT_ROOT)),
        "source_cycle": SOURCE_CYCLE,
        "source_state": source_state,
        "expected_probe_id": expected_probe_id,
        "expected_wake_cycle": EXPECTED_WAKE_CYCLE,
        "init_repair_attempted": False,
        "init_repair_valid": False,
        "init_repair_backend_calls": 0,
        "bounded_init_repair_calls": True,
        "schedule_valid": False,
        "event_completed": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }
    try:
        calls_before_init = backend.calls
        result["init_repair_attempted"] = True
        with base.bounded_call(f"repaired init r{replicate + 1} init repair"):
            session.exchange(init_repair_prompt(source, base), force_memory=None)
        result["init_repair_backend_calls"] = backend.calls - calls_before_init
        result["bounded_init_repair_calls"] = result["init_repair_backend_calls"] <= 1

        records = load_records(log_path)
        init_record = records[-1] if records else {}
        init_state = init_record.get("state") or {}
        init_state = init_state if isinstance(init_state, dict) else {}
        init_failures = base.init_failure_reasons(
            init_state,
            base.MODEL,
            SOURCE_REPLICATE,
        )
        result["init_repair_valid"] = not init_failures
        result["init_repair_failures"] = init_failures
        result["init_repair_raw_output"] = init_record.get("raw_output")
        if init_failures:
            return result

        with base.bounded_call(f"repaired init r{replicate + 1} schedule"):
            session.exchange(
                base.schedule_prompt(
                    model=base.MODEL,
                    replicate=SOURCE_REPLICATE,
                    fork_run_record_id=projected["applied"]["fork_run_record_id"],
                ),
                force_memory=None,
            )
        records = load_records(log_path)
        schedule_reasons = base.schedule_failure_reasons(records) if hasattr(
            base,
            "schedule_failure_reasons",
        ) else []
        scheduled_events = base.scheduled_events_in(records)
        result["schedule_valid"] = bool(scheduled_events) and not schedule_reasons
        result["schedule_failure_reasons"] = schedule_reasons

        if scheduled_events:
            store = base.EventStore(event_path)
            session._state_validator = base.StrictContinuityStateValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=EXPECTED_WAKE_CYCLE,
            )
            session._state_repair_builder = base.FullStrictTargetRepairBuilder(
                expected_probe_id=expected_probe_id,
                expected_cycle=EXPECTED_WAKE_CYCLE,
            )
            calls_before_wake = backend.calls
            with base.bounded_call(f"repaired init r{replicate + 1} wake"):
                event_result = base.run_next_event(session, store)
            result["wake_backend_calls"] = backend.calls - calls_before_wake
            result["bounded_wake_calls"] = result["wake_backend_calls"] <= 2
            result["event_result_status"] = event_result.get("status")
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = base.format_error(exc)

    records = load_records(log_path)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    result["cycle_count"] = len(records)
    result.update(
        base.strict_metrics(
            final_state=final_state,
            response_text=final_record.get("response_text", ""),
            records=records,
            event_path=event_path,
            expected_probe_id=expected_probe_id,
            expected_cycle=EXPECTED_WAKE_CYCLE,
        )
    )
    event_summary = base.event_summary_for(event_path)
    status_counts = event_summary.get("status_counts", {})
    result["event_persisted"] = event_summary.get("event_count", 0) > 0
    result["event_completed"] = status_counts.get("completed", 0) > 0
    result["context_error_count"] = sum(
        int(event.get("context_error_count", 0))
        for event in event_summary.get("events", [])
    )
    result["event_log_scoring"] = event_log_scoring(
        event_path,
        result.get("state_validation_status"),
    )
    return result


def aggregate(results: list[dict]) -> dict:
    completed = [r for r in results if r.get("event_completed")]
    repaired_wakes = [r for r in completed if r.get("repaired")]
    return {
        "summary": {
            "n": len(results),
            "errors": sum(bool(r.get("error")) for r in results),
            "init_repair_valid": sum(bool(r.get("init_repair_valid")) for r in results),
            "schedule_valid": sum(bool(r.get("schedule_valid")) for r in results),
            "event_completed": len(completed),
            "wake_first_pass_valid": sum(bool(r.get("first_pass_valid")) for r in completed),
            "wake_repaired": len(repaired_wakes),
            "event_wake_validation_present": sum(
                bool((r.get("event_log_scoring") or {}).get("wake_validation_status"))
                for r in completed
            ),
            "event_session_validation_agreement": sum(
                bool(
                    (r.get("event_log_scoring") or {}).get(
                        "session_event_validation_status_agree"
                    )
                )
                for r in completed
            ),
            "bounded_init_repair_call_violations": sum(
                not bool(r.get("bounded_init_repair_calls")) for r in results
            ),
            "bounded_wake_call_violations": sum(
                not bool(r.get("bounded_wake_calls")) for r in results
            ),
        },
        "hypothesis_results": {
            "H236_initialization_repair_recovers_source": any(
                r.get("init_repair_valid") for r in results
            ),
            "H237_repaired_init_schedules_one_walk_event": (
                all(r.get("schedule_valid") for r in results)
                if results else False
            ),
            "H238_wake_receives_context_and_event_validation": (
                all(
                    r.get("event_context_has_walk_path")
                    and (r.get("event_log_scoring") or {}).get(
                        "wake_validation_status"
                    )
                    for r in completed
                ) if completed else False
            ),
            "H239_init_and_wake_provenance_distinguishable": all(
                r.get("init_repair_valid") is not None
                and r.get("state_validation_status") is not None
                for r in completed
            ) if completed else False,
            "H240_bounded_repair_policy_holds": all(
                bool(r.get("bounded_init_repair_calls"))
                and bool(r.get("bounded_wake_calls"))
                for r in results
            ),
        },
    }


def write_results(base, results: list[dict]) -> None:
    payload = {
        "model": base.MODEL,
        "source_log": str(SOURCE_LOG.relative_to(PROJECT_ROOT)),
        "source_cycle": SOURCE_CYCLE,
        "source_replicate": SOURCE_REPLICATE + 1,
        "expected_wake_cycle": EXPECTED_WAKE_CYCLE,
        "n_replicates": N_REPLICATES,
        "max_tokens": base.MAX_TOKENS,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    base = load_base_runner()
    base.EXP_DIR = EXP_DIR
    base.PROJECT_ROOT = PROJECT_ROOT
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    results_path = EXP_DIR / "results.json"
    results: list[dict] = []
    if results_path.exists():
        prior = json.loads(results_path.read_text()).get("results", [])
        if isinstance(prior, list):
            results = prior
    completed = {int(result.get("replicate", 0)) for result in results}
    for replicate in range(N_REPLICATES):
        if replicate + 1 in completed:
            print(f"replicate {replicate + 1} already recorded", flush=True)
            continue
        print(f"replicate {replicate + 1}", flush=True)
        result = run_replicate(base, replicate, api_key)
        results.append(result)
        completed.add(replicate + 1)
        write_results(base, results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
