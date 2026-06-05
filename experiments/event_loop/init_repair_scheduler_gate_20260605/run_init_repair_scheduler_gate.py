"""Run scheduled-wake gate with bounded cycle-1 initialization repair."""

from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import EventStore, summarize_event_log

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/scheduled_walk_strict_continuity_20260605/"
    / "run_scheduled_walk_strict_continuity.py"
)


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


class InitializationStateValidator:
    def __init__(self, base, *, expected_probe_id: str):
        self.base = base
        self.expected_probe_id = expected_probe_id

    def validate(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
    ) -> dict:
        del record_id, timestamp, prior_state, raw_output, response_text
        failures: list[str] = []
        if state.get("probe_id") != self.expected_probe_id:
            failures.append("probe_id_missing_or_changed")
        if state.get("walk_gate_status") != "initialized":
            failures.append("walk_gate_status_not_initialized")
        observations = state.get("observations")
        if not isinstance(observations, list):
            failures.append("observations_not_list")
        elif self.base.BASELINE_OBSERVATION not in observations:
            failures.append("baseline_observation_missing")
        if isinstance(state.get("state"), dict):
            failures.append("nested_state_present")
        valid = not failures
        return {
            "valid": valid,
            "status": "valid" if valid else "invalid",
            "validator": "initialization_state_validator",
            "cycle": cycle,
            "expected_probe_id": self.expected_probe_id,
            "failures": failures,
        }


class InitializationRepairBuilder:
    def __init__(self, base, *, expected_probe_id: str):
        self.base = base
        self.expected_probe_id = expected_probe_id

    def target_object(self) -> dict[str, Any]:
        return {
            "response": "Initialized.",
            "probe_id": self.expected_probe_id,
            "walk_gate_status": "initialized",
            "observations": self.base.BASELINE_OBSERVATIONS,
        }

    def build_repair_prompt(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
        validation: dict,
    ) -> str:
        del cycle, record_id, timestamp, prior_state
        return f"""
Initialization validation repair turn.

Your previous cycle-1 response did not create the required durable
initialization object. Visible prose is not enough.

First-pass response:
{response_text}

First-pass raw output:
{json.dumps(raw_output, indent=2, default=str)}

Current durable state:
{json.dumps(state, indent=2, default=str)}

Validation result:
{json.dumps(validation, indent=2, default=str)}

Complete target durable object:
{json.dumps(self.target_object(), indent=2, default=str)}

Produce this durable object shape now. Preserve every top-level field except
response exactly. Do not put probe_id, walk_gate_status, or observations only
in prose.

Do not call tools. End with think_and_respond.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


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


def validation_summary(validation: dict | None) -> dict:
    if not isinstance(validation, dict):
        return {
            "status": None,
            "first_pass_status": None,
            "repair_attempted": False,
            "repair_status": None,
            "repaired": False,
            "has_repair_raw_output": False,
            "has_repair_validation": False,
        }
    first_pass = validation.get("first_pass")
    first_pass = first_pass if isinstance(first_pass, dict) else {}
    repair = validation.get("repair")
    repair = repair if isinstance(repair, dict) else {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair.get("status"),
        "repaired": validation.get("status") == "repaired",
        "has_repair_raw_output": isinstance(repair.get("raw_output"), dict),
        "has_repair_validation": isinstance(repair.get("validation"), dict),
    }


def run_replicate(base, replicate: int, api_key: str) -> dict:
    model = base.MODEL
    safe_model = base.safe_model_name(model)
    log_path = EXP_DIR / f"{safe_model}_r{replicate + 1:02d}.jsonl"
    event_path = base.default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    projected = base.build_projected_hub(model, replicate)
    label = f"init_repair_scheduler_gate_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=model,
        log_path=log_path,
        label=label,
        bridge=projected["bridge"],
        backend=backend,
    )
    expected_probe_id = base.probe_id_for(model, replicate)
    result: dict[str, Any] = {
        "model": model,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "fork_run_record_id": projected["applied"]["fork_run_record_id"],
        "planned_record_ids": projected["planned_record_ids"],
        "expected_probe_id": expected_probe_id,
        "expected_wake_cycle": base.EXPECTED_WAKE_CYCLE,
        "init_valid": False,
        "init_failure_reasons": [],
        "init_validation_status": None,
        "init_first_pass_status": None,
        "init_repair_attempted": False,
        "init_repaired": False,
        "init_backend_calls": 0,
        "bounded_init_calls": True,
        "error": None,
        "cycle_count": 0,
        "event_persisted": False,
        "event_completed": False,
        "context_error_count": 0,
        "event_result_status": None,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
    }
    try:
        session._state_validator = InitializationStateValidator(
            base,
            expected_probe_id=expected_probe_id,
        )
        session._state_repair_builder = InitializationRepairBuilder(
            base,
            expected_probe_id=expected_probe_id,
        )
        calls_before_init = backend.calls
        with base.bounded_call(f"{model} r{replicate + 1} init"):
            session.exchange(base.init_prompt(model, replicate), force_memory=None)
        result["init_backend_calls"] = backend.calls - calls_before_init
        result["bounded_init_calls"] = result["init_backend_calls"] <= 2

        records = load_records(log_path)
        init_record = records[-1] if records else {}
        init_validation = init_record.get("state_validation")
        init_summary = validation_summary(init_validation)
        result.update({
            "init_validation_status": init_summary["status"],
            "init_first_pass_status": init_summary["first_pass_status"],
            "init_repair_attempted": init_summary["repair_attempted"],
            "init_repair_status": init_summary["repair_status"],
            "init_repaired": init_summary["repaired"],
            "init_has_repair_raw_output": init_summary["has_repair_raw_output"],
            "init_has_repair_validation": init_summary["has_repair_validation"],
        })
        init_state = init_record.get("state") or {}
        init_state = init_state if isinstance(init_state, dict) else {}
        reasons = base.init_failure_reasons(init_state, model, replicate)
        result["init_failure_reasons"] = reasons
        result["init_valid"] = not reasons
        if reasons:
            result["cycle_count"] = len(records)
            return result

        session._state_validator = None
        session._state_repair_builder = None
        with base.bounded_call(f"{model} r{replicate + 1} schedule"):
            session.exchange(
                base.schedule_prompt(
                    model=model,
                    replicate=replicate,
                    fork_run_record_id=projected["applied"]["fork_run_record_id"],
                ),
                force_memory=None,
            )
        records = load_records(log_path)
        if base.scheduled_events_in(records):
            store = base.EventStore(event_path)
            session._state_validator = base.StrictContinuityStateValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=base.EXPECTED_WAKE_CYCLE,
            )
            session._state_repair_builder = base.FullStrictTargetRepairBuilder(
                expected_probe_id=expected_probe_id,
                expected_cycle=base.EXPECTED_WAKE_CYCLE,
            )
            calls_before_wake = backend.calls
            with base.bounded_call(f"{model} r{replicate + 1} wake"):
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
    if result.get("wake_backend_calls", 0):
        result["bounded_wake_calls"] = int(result["wake_backend_calls"]) <= 2
    result.update(
        base.strict_metrics(
            final_state=final_state,
            response_text=final_record.get("response_text", ""),
            records=records,
            event_path=event_path,
            expected_probe_id=expected_probe_id,
            expected_cycle=base.EXPECTED_WAKE_CYCLE,
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


def summarize_group(results: list[dict]) -> dict:
    completed = [r for r in results if r.get("event_completed")]
    valid_init = [r for r in results if r.get("init_valid")]
    return {
        "n": len(results),
        "init_valid": len(valid_init),
        "init_first_pass_valid": sum(
            r.get("init_validation_status") == "valid" for r in results
        ),
        "init_repaired": sum(bool(r.get("init_repaired")) for r in results),
        "init_unrepaired_or_failed": sum(
            r.get("init_validation_status") in {
                "unrepaired",
                "repair_failed",
                "validator_failed",
            }
            or not r.get("init_valid")
            for r in results
        ),
        "scheduled_wakes_completed": len(completed),
        "completed_after_repaired_init": sum(
            bool(r.get("event_completed") and r.get("init_repaired"))
            for r in results
        ),
        "completed_after_first_pass_init": sum(
            bool(
                r.get("event_completed")
                and r.get("init_validation_status") == "valid"
            )
            for r in results
        ),
        "wake_first_pass_valid": sum(
            bool(r.get("first_pass_valid")) for r in completed
        ),
        "wake_repaired": sum(bool(r.get("repaired")) for r in completed),
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
        "bounded_init_call_violations": sum(
            not bool(r.get("bounded_init_calls")) for r in results
        ),
        "bounded_wake_call_violations": sum(
            not bool(r.get("bounded_wake_calls")) for r in results
        ),
    }


def aggregate(results: list[dict]) -> dict:
    summary = summarize_group(results)
    completed = [r for r in results if r.get("event_completed")]
    repaired_init_completed = [
        r for r in completed if r.get("init_repaired")
    ]
    return {
        "summary": summary,
        "hypothesis_results": {
            "H226_init_repair_increases_usable_population": bool(
                repaired_init_completed
            ),
            "H227_repaired_initializations_auditable": (
                all(
                    r.get("init_repair_attempted")
                    and r.get("init_has_repair_raw_output")
                    and r.get("init_has_repair_validation")
                    for r in results
                    if r.get("init_repaired")
                )
                if any(r.get("init_repaired") for r in results) else False
            ),
            "H228_wake_outcomes_remain_separately_classified": (
                all(
                    r.get("state_validation_status") in {"valid", "repaired"}
                    and (r.get("event_log_scoring") or {}).get(
                        "wake_validation_status"
                    )
                    for r in completed
                ) if completed else False
            ),
            "H229_event_wake_validation_consistent": (
                all(
                    bool((r.get("event_log_scoring") or {}).get(
                        "session_event_validation_status_agree"
                    ))
                    for r in completed
                ) if completed else False
            ),
            "H230_bounded_init_and_wake_repair": all(
                bool(r.get("bounded_init_calls"))
                and bool(r.get("bounded_wake_calls"))
                for r in results
            ),
        },
    }


def write_results(base, results: list[dict]) -> None:
    payload = {
        "model": base.MODEL,
        "n_replicates": base.N_REPLICATES,
        "max_tokens": base.MAX_TOKENS,
        "call_timeout_seconds": base.CALL_TIMEOUT_SECONDS,
        "http_timeout_seconds": base.HTTP_TIMEOUT_SECONDS,
        "expected_wake_cycle": base.EXPECTED_WAKE_CYCLE,
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
    completed = {
        (result.get("model"), int(result.get("replicate", 0)))
        for result in results
    }
    for replicate in range(base.N_REPLICATES):
        key = (base.MODEL, replicate + 1)
        if key in completed:
            print(f"{base.MODEL} r{replicate + 1} already recorded", flush=True)
            continue
        print(f"{base.MODEL} r{replicate + 1}", flush=True)
        result = run_replicate(base, replicate, api_key)
        results.append(result)
        completed.add(key)
        write_results(base, results)

    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
