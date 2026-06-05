"""Two-wake event-chain probe."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    step_pending_events,
)


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
REPAIR_GATE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/compression_repair_gate_20260605/"
    / "run_compression_repair_gate.py"
)

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 2
FIRST_NOT_BEFORE = "2026-06-01T01:00:00+00:00"
SECOND_NOT_BEFORE = "2026-06-01T02:00:00+00:00"
PRE_FIRST_NOW = datetime(2026, 6, 1, 0, 30, tzinfo=timezone.utc)
FIRST_DUE_NOW = datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
PRE_SECOND_NOW = datetime(2026, 6, 1, 1, 30, tzinfo=timezone.utc)
SECOND_DUE_NOW = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
EXPECTED_FIRST_WAKE_CYCLE = 3
EXPECTED_SECOND_WAKE_CYCLE = 4


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


repair_gate = load_repair_gate_runner()
base = repair_gate.base
matched = repair_gate.matched
LOSS_TEMPLATE = repair_gate.LOSS_TEMPLATE

base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def stable_uuid(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"hamutay-two-wake-chain-20260605-{label}")


def probe_id_for(replicate: int) -> str:
    return f"two-wake-chain-{base.safe_model_name(MODEL)}-r{replicate + 1}"


def first_label(replicate: int) -> str:
    return f"two-wake-chain-first-r{replicate + 1}"


def second_label(replicate: int) -> str:
    return f"two-wake-chain-second-r{replicate + 1}"


def cycle1_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-1-r{replicate + 1}")


def cycle2_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-2-r{replicate + 1}")


def seeded_cycle1_state(replicate: int) -> dict[str, Any]:
    condition = "two_wake_chain_seed"
    return {
        **matched.seed_state(condition, replicate),
        "probe_id": probe_id_for(replicate),
        "memory_handle": {
            "code_phrase_sha256": matched.code_phrase_digest(replicate),
        },
        "loss_template": LOSS_TEMPLATE,
    }


def seeded_cycle2_state(replicate: int) -> dict[str, Any]:
    return {
        "cycle": 2,
        "probe_id": probe_id_for(replicate),
        "thinking_status": "chain_scheduled",
        "thinking_question": (
            "Complete a two-wake chain: first record a non-secret intermediate, "
            "then recover the exact phrase in the second wake."
        ),
        "observations": [base.BASELINE_OBSERVATION],
        "memory_handle": {
            "code_phrase_sha256": matched.code_phrase_digest(replicate),
        },
        "loss_template": LOSS_TEMPLATE,
        "declared_losses": LOSS_TEMPLATE,
        "chain_stage": "compressed_waiting_first_wake",
    }


def first_wake_purpose(replicate: int) -> str:
    return f"""
You are the first wake in the two-wake chain probe.
replicate={replicate + 1}

Use the recalled cycle 1 state to derive a non-secret intermediate. Do not
carry the exact deferred phrase into durable state.

Required durable updates:
- Preserve probe_id.
- Set thinking_status to "awaiting_second_wake".
- Set chain_stage to "first_wake_complete".
- Add chain_intermediate with:
  - source_cycle: 1
  - phrase_shape: "word-word-number"
  - part_count: 3
  - exact_phrase_retained: false
- Preserve memory_handle, loss_template, declared_losses, and baseline
  observation.
- Do not include deferred_fact.
- Do not include the exact phrase anywhere in durable state.

Then call schedule_event exactly once for the second wake. Use exactly:
- requested_context: [{{"tool": "recall", "cycle": 1}}, {{"tool": "recall", "cycle": 3}}]
- not_before: {SECOND_NOT_BEFORE}
- label: {second_label(replicate)}

Second wake purpose:
You are the second wake in the two-wake chain probe. Use recalled cycle 1 to
recover the exact phrase and recalled cycle 3 to incorporate the non-secret
intermediate. Required durable updates: thinking_status "chain_completed";
chain_stage "second_wake_complete"; chain_final_answer containing the exact
phrase; chain_final_evidence referencing phrase_shape "word-word-number";
preserve baseline observation. Do not schedule another event.
""".strip()


def make_session(replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    label = f"two_wake_chain_{safe_model}_r{replicate + 1:02d}"
    backend = base.make_backend(api_key, label=label)
    session = base.make_session(
        model=MODEL,
        log_path=log_path,
        label=label,
        backend=backend,
    )
    records = [
        {
            "cycle": 1,
            "record_id": str(cycle1_record_id(replicate)),
            "timestamp": "2026-06-01T00:00:00+00:00",
            "state": seeded_cycle1_state(replicate),
        },
        {
            "cycle": 2,
            "record_id": str(cycle2_record_id(replicate)),
            "timestamp": "2026-06-01T00:30:00+00:00",
            "state": seeded_cycle2_state(replicate),
        },
    ]
    session.seed_history(records, up_to_cycle=3)
    return session, backend


def append_first_event(store: EventStore, replicate: int) -> dict[str, Any]:
    event = build_pending_event(
        purpose=first_wake_purpose(replicate),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=2,
        scheduled_by_record_id=cycle2_record_id(replicate),
        label=first_label(replicate),
        not_before=FIRST_NOT_BEFORE,
    )
    store.append(event)
    return event


def durable_text(state: dict[str, Any]) -> str:
    visible_state = {k: v for k, v in state.items() if k != "_activity_log"}
    return json.dumps(visible_state, default=str)


def first_wake_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    *,
    replicate: int,
) -> list[str]:
    failures: list[str] = []
    code_phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != EXPECTED_FIRST_WAKE_CYCLE:
        failures.append("cycle_missing_or_changed")
    if state.get("thinking_status") != "awaiting_second_wake":
        failures.append("thinking_status_not_awaiting_second_wake")
    if state.get("chain_stage") != "first_wake_complete":
        failures.append("chain_stage_not_first_wake_complete")
    if "deferred_fact" in state:
        failures.append("deferred_fact_present")
    if code_phrase in durable_text(state):
        failures.append("exact_phrase_present_in_first_wake_state")
    handle = state.get("memory_handle")
    if not isinstance(handle, dict) or handle.get("code_phrase_sha256") != matched.code_phrase_digest(replicate):
        failures.append("memory_handle_missing_or_changed")
    intermediate = state.get("chain_intermediate")
    if not isinstance(intermediate, dict):
        failures.append("chain_intermediate_missing")
    else:
        if intermediate.get("source_cycle") != 1:
            failures.append("chain_intermediate.source_cycle")
        if intermediate.get("phrase_shape") != "word-word-number":
            failures.append("chain_intermediate.phrase_shape")
        if intermediate.get("part_count") != 3:
            failures.append("chain_intermediate.part_count")
        if intermediate.get("exact_phrase_retained") is not False:
            failures.append("chain_intermediate.exact_phrase_retained")
    observations = state.get("observations")
    if not isinstance(observations, list) or base.BASELINE_OBSERVATION not in observations:
        failures.append("baseline_observation_missing")
    deleted = raw_output.get("deleted_regions")
    if isinstance(deleted, list):
        for key in ("probe_id", "cycle", "memory_handle", "chain_intermediate"):
            if key in deleted:
                failures.append(f"deleted_regions.{key}")
    return failures


def second_wake_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    *,
    replicate: int,
) -> list[str]:
    failures: list[str] = []
    code_phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != EXPECTED_SECOND_WAKE_CYCLE:
        failures.append("cycle_missing_or_changed")
    if state.get("thinking_status") != "chain_completed":
        failures.append("thinking_status_not_chain_completed")
    if state.get("chain_stage") != "second_wake_complete":
        failures.append("chain_stage_not_second_wake_complete")
    answer = state.get("chain_final_answer")
    if not isinstance(answer, str) or code_phrase not in answer:
        failures.append("chain_final_answer_missing_code_phrase")
    evidence = state.get("chain_final_evidence")
    if "word-word-number" not in json.dumps(evidence, default=str):
        failures.append("chain_final_evidence_missing_intermediate")
    observations = state.get("observations")
    if not isinstance(observations, list) or base.BASELINE_OBSERVATION not in observations:
        failures.append("baseline_observation_missing")
    deleted = raw_output.get("deleted_regions")
    if isinstance(deleted, list):
        for key in ("probe_id", "cycle", "chain_intermediate", "chain_final_answer"):
            if key in deleted:
                failures.append(f"deleted_regions.{key}")
    return failures


class FirstWakeValidator:
    def __init__(self, *, replicate: int):
        self.replicate = replicate

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
        del cycle, record_id, timestamp, prior_state, response_text
        failures = first_wake_failures(state, raw_output, replicate=self.replicate)
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "validator": "two_wake_chain_first_wake_validator",
            "expected_cycle": EXPECTED_FIRST_WAKE_CYCLE,
            "expected_probe_id": probe_id_for(self.replicate),
            "failures": failures,
        }


class SecondWakeValidator:
    def __init__(self, *, replicate: int):
        self.replicate = replicate

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
        del cycle, record_id, timestamp, prior_state, response_text
        failures = second_wake_failures(state, raw_output, replicate=self.replicate)
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "validator": "two_wake_chain_second_wake_validator",
            "expected_cycle": EXPECTED_SECOND_WAKE_CYCLE,
            "expected_probe_id": probe_id_for(self.replicate),
            "failures": failures,
        }


class FirstWakeRepairBuilder:
    def build_repair_prompt(self, **kwargs) -> str:
        redacted = dict(kwargs)
        return f"""
Two-wake chain first-wake repair.

Your previous first-wake durable state failed validation. The exact deferred
phrase is intentionally not revealed here. Use only context already provided to
you in this wake.

Validation context:
{json.dumps(redacted, indent=2, default=str)}

Required durable shape:
- probe_id preserved;
- thinking_status: "awaiting_second_wake";
- chain_stage: "first_wake_complete";
- chain_intermediate with source_cycle 1, phrase_shape "word-word-number",
  part_count 3, exact_phrase_retained false;
- memory_handle, loss_template, declared_losses, and baseline observation
  preserved;
- no deferred_fact;
- no exact phrase in durable state.

Do not schedule another event during repair. End with think_and_respond.
""".strip()


class SecondWakeRepairBuilder:
    def build_repair_prompt(self, **kwargs) -> str:
        redacted = dict(kwargs)
        validation = redacted.get("validation")
        if isinstance(validation, dict):
            validation = dict(validation)
            validation.pop("expected_code_phrase", None)
            redacted["validation"] = validation
        return f"""
Two-wake chain second-wake repair.

Your previous second-wake durable state failed validation. The validator will
not reveal the exact deferred phrase. Use only information already present in
this wake's delivered context and current durable state.

Validation context:
{json.dumps(redacted, indent=2, default=str)}

Required durable shape:
- probe_id preserved;
- thinking_status: "chain_completed";
- chain_stage: "second_wake_complete";
- chain_final_answer containing the exact phrase if available to you;
- chain_final_evidence referencing phrase_shape "word-word-number";
- baseline observation preserved.

Do not schedule another event. End with think_and_respond.
""".strip()


def load_records(path: Path) -> list[dict[str, Any]]:
    return base.load_records(path)


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    for record in records:
        if int(record.get("cycle") or 0) == cycle:
            return record
    return {}


def event_histories(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        event_id = record.get("event_id")
        if event_id:
            histories[str(event_id)].append(record)
    return histories


def event_id_for_label(records: list[dict[str, Any]], label: str) -> str | None:
    for record in records:
        if record.get("status") == "pending" and record.get("label") == label:
            return str(record.get("event_id"))
    return None


def event_record_for_label(records: list[dict[str, Any]], label: str, status: str) -> dict[str, Any]:
    event_id = event_id_for_label(records, label)
    if not event_id:
        return {}
    for record in records:
        if record.get("event_id") == event_id and record.get("status") == status:
            return record
    return {}


def context_cycles(completed_event: dict[str, Any]) -> list[int]:
    cycles: list[int] = []
    for item in completed_event.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") == "recall" and "cycle" in request:
            cycles.append(int(request["cycle"]))
    return cycles


def second_schedule_failures(event_records: list[dict[str, Any]], replicate: int) -> list[str]:
    failures: list[str] = []
    pending = event_record_for_label(event_records, second_label(replicate), "pending")
    if not pending:
        return ["second_event_not_scheduled"]
    if pending.get("scheduled_by_cycle") != EXPECTED_FIRST_WAKE_CYCLE:
        failures.append("second_event_scheduled_by_cycle_mismatch")
    if pending.get("not_before") != SECOND_NOT_BEFORE:
        failures.append("second_event_not_before_mismatch")
    expected_context = [{"tool": "recall", "cycle": 1}, {"tool": "recall", "cycle": 3}]
    if pending.get("requested_context") != expected_context:
        failures.append("second_event_requested_context_mismatch")
    return failures


def validation_summary(record: dict[str, Any]) -> dict[str, Any]:
    validation = record.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair.get("status"),
        "repaired": validation.get("status") == "repaired",
        "first_pass_failures": first_pass.get("failures"),
        "repair_failures": (repair.get("validation") or {}).get("failures")
        if isinstance(repair.get("validation"), dict)
        else None,
    }


def finalize_result(
    result: dict[str, Any],
    *,
    log_path: Path,
    event_path: Path,
    replicate: int,
) -> dict[str, Any]:
    records = load_records(log_path)
    event_records = EventStore(event_path).read_records()
    first_record = record_for_cycle(records, EXPECTED_FIRST_WAKE_CYCLE)
    second_record = record_for_cycle(records, EXPECTED_SECOND_WAKE_CYCLE)
    first_state = first_record.get("state") if isinstance(first_record, dict) else {}
    first_state = first_state if isinstance(first_state, dict) else {}
    second_state = second_record.get("state") if isinstance(second_record, dict) else {}
    second_state = second_state if isinstance(second_state, dict) else {}
    first_completed = event_record_for_label(event_records, first_label(replicate), "completed")
    second_completed = event_record_for_label(event_records, second_label(replicate), "completed")
    first_failures = first_wake_failures(
        first_state,
        first_record.get("raw_output") or {},
        replicate=replicate,
    ) if first_record else ["first_wake_record_missing"]
    second_failures = second_wake_failures(
        second_state,
        second_record.get("raw_output") or {},
        replicate=replicate,
    ) if second_record else ["second_wake_record_missing"]
    second_schedule_reasons = second_schedule_failures(event_records, replicate)
    code_phrase = matched.code_phrase_for(replicate)
    result.update(
        {
            "cycle_count": len(records),
            "event_summary": base.summarize_event_log(event_records),
            "first_wake_completed": bool(first_completed),
            "first_wake_context_cycles": context_cycles(first_completed),
            "first_wake_state_valid": not first_failures,
            "first_wake_failures": first_failures,
            "first_wake_state_contains_code_phrase": code_phrase in durable_text(first_state),
            "first_wake_response_contains_code_phrase": (
                code_phrase in str(first_completed.get("response_text", ""))
            ),
            "first_wake_validation": validation_summary(first_record),
            "second_event_scheduled": not bool(second_schedule_reasons),
            "second_schedule_failure_reasons": second_schedule_reasons,
            "second_wake_completed": bool(second_completed),
            "second_wake_context_cycles": context_cycles(second_completed),
            "second_wake_state_valid": not second_failures,
            "second_wake_failures": second_failures,
            "second_wake_validation": validation_summary(second_record),
            "chain_final_answer_contains_code_phrase": (
                isinstance(second_state.get("chain_final_answer"), str)
                and code_phrase in second_state["chain_final_answer"]
            ),
            "chain_final_evidence_uses_intermediate": (
                "word-word-number" in json.dumps(
                    second_state.get("chain_final_evidence"), default=str
                )
            ),
            "final_state": second_state or first_state,
        }
    )
    return result


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "two_wake_chain"
    safe_model = base.safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{condition}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session, backend = make_session(replicate, api_key, log_path=log_path)
    store = EventStore(event_path)
    append_first_event(store, replicate)
    result: dict[str, Any] = {
        "condition": condition,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": probe_id_for(replicate),
        "code_phrase_sha256": matched.code_phrase_digest(replicate),
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
            now=PRE_FIRST_NOW,
        )
        session._state_validator = FirstWakeValidator(replicate=replicate)
        session._state_repair_builder = FirstWakeRepairBuilder()
        calls_before = backend.calls
        with base.bounded_call(f"two_wake_chain r{replicate + 1} first wake"):
            result["first_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=FIRST_DUE_NOW,
            )
        result["first_backend_calls"] = backend.calls - calls_before
        result["bounded_first_calls"] = result["first_backend_calls"] <= 2

        interim = finalize_result(
            dict(result),
            log_path=log_path,
            event_path=event_path,
            replicate=replicate,
        )
        if interim["first_wake_state_valid"] and interim["second_event_scheduled"]:
            result["pre_second_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=PRE_SECOND_NOW,
            )
            session._state_validator = SecondWakeValidator(replicate=replicate)
            session._state_repair_builder = SecondWakeRepairBuilder()
            calls_before = backend.calls
            with base.bounded_call(f"two_wake_chain r{replicate + 1} second wake"):
                result["second_step"] = step_pending_events(
                    session,
                    store,
                    limit=4,
                    now=SECOND_DUE_NOW,
                )
            result["second_backend_calls"] = backend.calls - calls_before
            result["bounded_second_calls"] = result["second_backend_calls"] <= 2
        else:
            result["second_step_skipped"] = {
                "reason": "first_wake_invalid_or_second_event_not_scheduled",
                "first_wake_state_valid": interim["first_wake_state_valid"],
                "second_event_scheduled": interim["second_event_scheduled"],
            }
    except Exception as exc:  # noqa: BLE001
        result["error"] = base.format_error(exc)
    return finalize_result(
        result,
        log_path=log_path,
        event_path=event_path,
        replicate=replicate,
    )


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "first_wake_completed": sum(bool(row.get("first_wake_completed")) for row in rows),
        "first_wake_state_valid": sum(bool(row.get("first_wake_state_valid")) for row in rows),
        "first_wake_state_leaks": sum(
            bool(row.get("first_wake_state_contains_code_phrase")) for row in rows
        ),
        "second_event_scheduled": sum(bool(row.get("second_event_scheduled")) for row in rows),
        "second_wake_completed": sum(bool(row.get("second_wake_completed")) for row in rows),
        "second_wake_state_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "second_context_both_cycles": sum(
            set(row.get("second_wake_context_cycles") or []) >= {1, 3}
            for row in rows
        ),
        "final_answer_recovered": sum(
            bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows
        ),
        "intermediate_used": sum(
            bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows
        ),
        "first_repaired": sum(
            bool((row.get("first_wake_validation") or {}).get("repaired"))
            for row in rows
        ),
        "second_repaired": sum(
            bool((row.get("second_wake_validation") or {}).get("repaired"))
            for row in rows
        ),
        "errors": sum(bool(row.get("error")) for row in rows),
        "bounded_call_violations": sum(
            not bool(row.get("bounded_first_calls"))
            or not bool(row.get("bounded_second_calls"))
            for row in rows
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
    return {
        "conditions": summaries,
        "hypothesis_results": {
            "H296_two_wake_chain_completes": any(
                row.get("first_wake_completed") and row.get("second_wake_completed")
                for row in results
            ) if results else False,
            "H297_first_wake_keeps_phrase_out_of_state": any(
                row.get("first_wake_state_valid")
                and not row.get("first_wake_state_contains_code_phrase")
                for row in results
            ) if results else False,
            "H298_second_wake_receives_both_contexts": any(
                set(row.get("second_wake_context_cycles") or []) >= {1, 3}
                for row in results
            ) if results else False,
            "H299_second_wake_recovers_and_uses_intermediate": any(
                row.get("chain_final_answer_contains_code_phrase")
                and row.get("chain_final_evidence_uses_intermediate")
                for row in results
            ) if results else False,
            "H300_provenance_distinguishable": all(
                isinstance(row.get("first_wake_validation"), dict)
                and isinstance(row.get("second_wake_validation"), dict)
                and row.get("event_summary") is not None
                for row in results
            ) if results else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "two_wake_chain_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "first_not_before": FIRST_NOT_BEFORE,
        "second_not_before": SECOND_NOT_BEFORE,
        "results": results,
        "summary": aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_replicates(results: list[dict[str, Any]]) -> set[int]:
    return {int(row.get("replicate", 0)) for row in results}


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = [row for row in prior if isinstance(row, dict)]
    done = completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(f"two_wake_chain r{replicate + 1} already recorded", flush=True)
            continue
        print(f"two_wake_chain r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
