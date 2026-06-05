"""Matched identity-only vs event-plus-recall delayed task continuity probe."""

from __future__ import annotations

import importlib.util
import json
import os
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import EventStore, default_event_log_path, step_pending_events


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/delayed_thinking_simtime_20260605/"
    / "run_delayed_thinking_simtime.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 2
SEED_RECORD_ID = UUID("00000000-0000-0000-0000-000000000201")
CODE_PHRASES = ["amber-lattice-17", "violet-harbor-42"]


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
base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def probe_id_for(condition: str, replicate: int) -> str:
    return (
        f"matched-delayed-task-{condition}-"
        f"{base.safe_model_name(MODEL)}-r{replicate + 1}"
    )


def code_phrase_for(replicate: int) -> str:
    return CODE_PHRASES[replicate]


def code_phrase_digest(replicate: int) -> str:
    return hashlib.sha256(code_phrase_for(replicate).encode("utf-8")).hexdigest()


def seed_state(condition: str, replicate: int) -> dict[str, Any]:
    code_phrase = code_phrase_for(replicate)
    return {
        "cycle": 1,
        "probe_id": probe_id_for(condition, replicate),
        "thinking_status": "initialized",
        "thinking_question": (
            "At the due step, recover the deferred code phrase and explain why "
            "it should be carried forward."
        ),
        "deferred_fact": {
            "kind": "code_phrase",
            "value": code_phrase,
            "instruction": "Use this exact phrase in delayed_answer at due time.",
        },
        "observations": [base.BASELINE_OBSERVATION],
    }


def seed_history(session, condition: str, replicate: int) -> None:
    session.seed_history(
        [
            {
                "cycle": 1,
                "record_id": str(SEED_RECORD_ID),
                "timestamp": datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
                "state": seed_state(condition, replicate),
            }
        ],
        up_to_cycle=2,
    )


def load_records(path: Path) -> list[dict[str, Any]]:
    return base.load_records(path)


def parking_prompt(condition: str, replicate: int) -> str:
    return f"""
Matched delayed-task continuity probe.
condition={condition}
replicate={replicate + 1}

This is the parking turn before the due step. Preserve whatever durable
state you judge necessary to answer the delayed task later.

Do not answer the delayed task yet. Set thinking_status to "parked".
Do not call tools. End with think_and_respond.
""".strip()


def identity_due_prompt(condition: str, replicate: int) -> str:
    return f"""
Matched delayed-task continuity probe due step.
condition={condition}
replicate={replicate + 1}

Complete the delayed task now using only your current durable state and this
conversation. No scheduled recall context will be provided in this condition.

Required durable updates:
- Preserve probe_id.
- Set top-level thinking_status to "completed".
- Add top-level delayed_answer containing the exact deferred code phrase.
- Add top-level wake_observation with kind "delayed_task".
- Preserve the baseline observation.

Do not call tools. End with think_and_respond.
""".strip()


def event_schedule_prompt(condition: str, replicate: int) -> str:
    requested_context = [{"tool": "recall", "cycle": 1}]
    purpose = f"""
You are the due wake for the matched delayed-task continuity probe.
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
    return f"""
Matched delayed-task event scheduling turn.
condition={condition}
replicate={replicate + 1}

Call schedule_event exactly once and wait for its result. Use exactly:
- requested_context: {json.dumps(requested_context)}
- not_before: {base.NOT_BEFORE}
- label: matched-delayed-task-{condition}-r{replicate + 1}

Event purpose:
{purpose}

After schedule_event returns an event_id, set thinking_status to "scheduled"
and end with think_and_respond. Do not call read, search_project, bash, or
clock.
""".strip()


def state_contains_code(records: list[dict[str, Any]], code_phrase: str, *, start_cycle: int, end_cycle: int) -> bool:
    for record in records:
        cycle = int(record.get("cycle") or 0)
        if cycle < start_cycle or cycle > end_cycle:
            continue
        state = record.get("state")
        if isinstance(state, dict) and code_phrase in json.dumps(state, default=str):
            return True
    return False


def delayed_task_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    *,
    expected_probe_id: str,
    expected_cycle: int,
    code_phrase: str,
) -> list[str]:
    failures: list[str] = []
    if state.get("probe_id") != expected_probe_id:
        failures.append("probe_id_changed")
    if state.get("cycle") != expected_cycle:
        failures.append("cycle_missing_or_changed")
    if state.get("thinking_status") != "completed":
        failures.append("thinking_status_not_completed")
    answer = state.get("delayed_answer")
    if not isinstance(answer, str) or code_phrase not in answer:
        failures.append("delayed_answer_missing_code_phrase")
    wake = state.get("wake_observation")
    if not isinstance(wake, dict) or wake.get("kind") != "delayed_task":
        failures.append("wake_observation_missing")
    observations = state.get("observations")
    if not isinstance(observations, list) or base.BASELINE_OBSERVATION not in observations:
        failures.append("baseline_observation_missing")
    deleted = raw_output.get("deleted_regions")
    if isinstance(deleted, list):
        for key in ("probe_id", "cycle"):
            if key in deleted:
                failures.append(f"deleted_regions.{key}")
    return failures


class DelayedTaskValidator:
    def __init__(self, *, expected_probe_id: str, expected_cycle: int, code_phrase: str):
        self.expected_probe_id = expected_probe_id
        self.expected_cycle = expected_cycle
        self.code_phrase = code_phrase

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
        del record_id, timestamp, prior_state, response_text
        failures = delayed_task_failures(
            state,
            raw_output,
            expected_probe_id=self.expected_probe_id,
            expected_cycle=self.expected_cycle,
            code_phrase=self.code_phrase,
        )
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "validator": "matched_delayed_task_validator",
            "cycle": cycle,
            "expected_cycle": self.expected_cycle,
            "expected_probe_id": self.expected_probe_id,
            "failures": failures,
        }


class NonLeakingDelayedTaskRepairBuilder:
    def build_repair_prompt(self, **kwargs) -> str:
        redacted = dict(kwargs)
        validation = redacted.get("validation")
        if isinstance(validation, dict):
            validation = dict(validation)
            validation.pop("expected_code_phrase", None)
            redacted["validation"] = validation
        return f"""
Matched delayed-task validation repair turn.

Your previous due-step response failed durable-state validation. The validator
will not reveal the deferred code phrase. Use only information already present
in your current durable state, prior conversation, or delivered event context.

Validation context:
{json.dumps(redacted, indent=2, default=str)}

Required durable shape:
- response
- probe_id
- thinking_status: "completed"
- delayed_answer containing the exact deferred code phrase if available to you
- wake_observation with kind "delayed_task"
- observations preserving the baseline observation

Do not call tools. End with think_and_respond.
""".strip()


def make_session(condition: str, replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    label = f"matched_delayed_task_{condition}_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=MODEL,
        log_path=log_path,
        label=label,
        backend=backend,
    )
    seed_history(session, condition, replicate)
    return session, backend


def completed_event(path: Path) -> dict[str, Any]:
    return base.latest_completed_event(path)


def event_has_recall_context(event_record: dict[str, Any]) -> bool:
    return base.event_has_recall_context(event_record)


def finalize(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    expected_probe_id: str,
    code_phrase: str,
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
    event_record = completed_event(event_path)
    failures = delayed_task_failures(
        state,
        raw_output,
        expected_probe_id=expected_probe_id,
        expected_cycle=base.EXPECTED_WAKE_CYCLE,
        code_phrase=code_phrase,
    )
    result.update(
        {
            "cycle_count": len(records),
            "final_state": state,
            "deferred_fact_preserved_before_due": state_contains_code(
                records,
                code_phrase,
                start_cycle=2,
                end_cycle=base.EXPECTED_WAKE_CYCLE - 1,
            ),
            "final_contains_code_phrase": code_phrase in json.dumps(state, default=str),
            "final_state_valid": not failures,
            "state_failures": failures,
            "event_completed": bool(event_record),
            "event_has_recall_context": event_has_recall_context(event_record),
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


def run_identity_only(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "identity_only"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    code_phrase = code_phrase_for(replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "code_phrase_sha256": code_phrase_digest(replicate),
        "schedule_valid": False,
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} park"):
            session.exchange(parking_prompt(condition, replicate), force_memory=None)
        session._state_validator = DelayedTaskValidator(
            expected_probe_id=expected_probe_id,
            expected_cycle=base.EXPECTED_WAKE_CYCLE,
            code_phrase=code_phrase,
        )
        session._state_repair_builder = NonLeakingDelayedTaskRepairBuilder()
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
        code_phrase=code_phrase,
    )


def run_event_plus_recall(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "event_plus_recall"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(condition, replicate, api_key, log_path=log_path)
    expected_probe_id = probe_id_for(condition, replicate)
    code_phrase = code_phrase_for(replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "code_phrase_sha256": code_phrase_digest(replicate),
        "schedule_valid": False,
        "event_completed": False,
        "event_has_recall_context": False,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
        "error": None,
    }
    try:
        with base.bounded_call(f"{condition} r{replicate + 1} schedule"):
            session.exchange(event_schedule_prompt(condition, replicate), force_memory=None)
        records = load_records(log_path)
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
            session._state_validator = DelayedTaskValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=base.EXPECTED_WAKE_CYCLE,
                code_phrase=code_phrase,
            )
            session._state_repair_builder = NonLeakingDelayedTaskRepairBuilder()
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
        code_phrase=code_phrase,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "final_valid": sum(bool(row.get("final_state_valid")) for row in rows),
        "fact_recovered": sum(bool(row.get("final_contains_code_phrase")) for row in rows),
        "preserved_before_due": sum(
            bool(row.get("deferred_fact_preserved_before_due")) for row in rows
        ),
        "recall_context": sum(bool(row.get("event_has_recall_context")) for row in rows),
        "event_completed": sum(bool(row.get("event_completed")) for row in rows),
        "first_pass_valid": sum(
            row.get("first_pass_validation_status") == "valid" for row in rows
        ),
        "repaired": sum(bool(row.get("repaired")) for row in rows),
        "bounded_wake_call_violations": sum(
            not bool(row.get("bounded_wake_calls")) for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[str(row["condition"])].append(row)
    summaries = {condition: condition_summary(rows) for condition, rows in sorted(grouped.items())}
    event = summaries.get("event_plus_recall", {})
    identity = summaries.get("identity_only", {})
    event_recovery = int(event.get("fact_recovered") or 0)
    identity_recovery = int(identity.get("fact_recovered") or 0)
    identity_rows = grouped.get("identity_only", [])
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H271_event_recall_recovers_fact": (
                event.get("recall_context") == event.get("n")
                and event_recovery > 0
            ) if event else False,
            "H272_identity_recovery_requires_preservation": all(
                (not row.get("final_contains_code_phrase"))
                or bool(row.get("deferred_fact_preserved_before_due"))
                for row in identity_rows
            ) if identity_rows else False,
            "H273_event_recall_higher_recovery": event_recovery > identity_recovery,
            "H274_provenance_present": all(
                row.get("first_pass_validation_status") is not None
                and row.get("state_validation_status") is not None
                for row in results
            ) if results else False,
            "H275_task_too_easy_if_identity_matches_is_diagnosable": (
                identity_recovery < event_recovery
                or all(
                    bool(row.get("deferred_fact_preserved_before_due"))
                    for row in identity_rows
                    if row.get("final_contains_code_phrase")
                )
            ) if identity_rows else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "matched_delayed_task_continuity_20260605",
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
            results = prior
    done = completed_keys(results)
    for condition, runner in [
        ("identity_only", run_identity_only),
        ("event_plus_recall", run_event_plus_recall),
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
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
