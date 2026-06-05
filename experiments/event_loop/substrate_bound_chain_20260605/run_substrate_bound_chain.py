"""Substrate-bound continuation event-chain probe."""

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
TWO_WAKE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/two_wake_chain_20260605/"
    / "run_two_wake_chain.py"
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


def load_two_wake_runner():
    spec = importlib.util.spec_from_file_location(
        "two_wake_chain_base",
        TWO_WAKE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load two-wake runner from {TWO_WAKE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


two_wake = load_two_wake_runner()
base = two_wake.base
matched = two_wake.matched
LOSS_TEMPLATE = two_wake.LOSS_TEMPLATE

base.EXP_DIR = EXP_DIR
base.PROJECT_ROOT = PROJECT_ROOT


def stable_uuid(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"hamutay-substrate-bound-chain-20260605-{label}")


def probe_id_for(replicate: int) -> str:
    return f"substrate-bound-chain-{base.safe_model_name(MODEL)}-r{replicate + 1}"


def first_label(replicate: int) -> str:
    return f"substrate-bound-chain-first-r{replicate + 1}"


def second_label(replicate: int) -> str:
    return f"substrate-bound-chain-second-r{replicate + 1}"


def cycle1_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-1-r{replicate + 1}")


def cycle2_record_id(replicate: int) -> UUID:
    return stable_uuid(f"cycle-2-r{replicate + 1}")


def seeded_cycle1_state(replicate: int) -> dict[str, Any]:
    condition = "substrate_bound_chain_seed"
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
            "Complete a substrate-bound two-wake chain without guessing the "
            "current wake's future record ID."
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
You are the first wake in the substrate-bound chain probe.
replicate={replicate + 1}

Use the recalled cycle 1 state to derive a non-secret intermediate. Do not
carry the exact deferred phrase into durable state.

Required durable updates:
- Preserve probe_id.
- Set thinking_status to "awaiting_bound_continuation".
- Set chain_stage to "first_wake_complete".
- Add chain_intermediate with:
  - source_cycle: 1
  - phrase_shape: "word-word-number"
  - part_count: 3
  - exact_phrase_retained: false
- Add continuation_request with:
  - requested: true
  - kind: "substrate_bound_second_wake"
  - needs_original_cycle: 1
  - needs_current_wake_record: true
- Preserve memory_handle, loss_template, declared_losses, and baseline
  observation.
- Do not include deferred_fact.
- Do not include the exact phrase anywhere in durable state.

Do not call schedule_event. The substrate will bind the continuation to the
record ID created by this wake after your state is committed.
""".strip()


def second_wake_purpose(bound_record_id: str) -> str:
    return f"""
You are the substrate-bound second wake. The substrate bound this event to the
first wake result record ID:
{bound_record_id}

Use recalled cycle 1 to recover the exact phrase. Use recalled record
{bound_record_id} to incorporate the non-secret first-wake intermediate.

Required durable updates:
- Preserve probe_id.
- Set thinking_status to "bound_chain_completed".
- Set chain_stage to "second_wake_complete".
- Set bound_record_id_used to "{bound_record_id}".
- Add chain_final_answer containing the exact phrase.
- Add chain_final_evidence referencing phrase_shape "word-word-number" from
  the bound first-wake record.
- Preserve baseline observation.
- Do not schedule another event.
""".strip()


def make_session(replicate: int, api_key: str, *, log_path: Path):
    safe_model = base.safe_model_name(MODEL)
    label = f"substrate_bound_chain_{safe_model}_r{replicate + 1:02d}"
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


def append_bound_second_event(
    store: EventStore,
    *,
    replicate: int,
    bound_record_id: str,
) -> dict[str, Any]:
    event = build_pending_event(
        purpose=second_wake_purpose(bound_record_id),
        requested_context=[
            {"tool": "recall", "cycle": 1},
            {"tool": "recall", "record_id": bound_record_id},
        ],
        scheduled_by_cycle=EXPECTED_FIRST_WAKE_CYCLE,
        scheduled_by_record_id=UUID(bound_record_id),
        label=second_label(replicate),
        not_before=SECOND_NOT_BEFORE,
    )
    event["bound_by"] = "runner_after_first_wake_completion"
    event["bound_result_record_id"] = bound_record_id
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
    if state.get("thinking_status") != "awaiting_bound_continuation":
        failures.append("thinking_status_not_awaiting_bound_continuation")
    if state.get("chain_stage") != "first_wake_complete":
        failures.append("chain_stage_not_first_wake_complete")
    if "deferred_fact" in state:
        failures.append("deferred_fact_present")
    if code_phrase in durable_text(state):
        failures.append("exact_phrase_present_in_first_wake_state")
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
    request = state.get("continuation_request")
    if not isinstance(request, dict):
        failures.append("continuation_request_missing")
    else:
        if request.get("requested") is not True:
            failures.append("continuation_request.requested")
        if request.get("kind") != "substrate_bound_second_wake":
            failures.append("continuation_request.kind")
        if request.get("needs_original_cycle") != 1:
            failures.append("continuation_request.needs_original_cycle")
        if request.get("needs_current_wake_record") is not True:
            failures.append("continuation_request.needs_current_wake_record")
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
    bound_record_id: str | None,
) -> list[str]:
    failures: list[str] = []
    code_phrase = matched.code_phrase_for(replicate)
    if state.get("probe_id") != probe_id_for(replicate):
        failures.append("probe_id_changed")
    if state.get("cycle") != EXPECTED_SECOND_WAKE_CYCLE:
        failures.append("cycle_missing_or_changed")
    if state.get("thinking_status") != "bound_chain_completed":
        failures.append("thinking_status_not_bound_chain_completed")
    if state.get("chain_stage") != "second_wake_complete":
        failures.append("chain_stage_not_second_wake_complete")
    if bound_record_id and state.get("bound_record_id_used") != bound_record_id:
        failures.append("bound_record_id_used_missing_or_changed")
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
            "validator": "substrate_bound_chain_first_wake_validator",
            "expected_cycle": EXPECTED_FIRST_WAKE_CYCLE,
            "expected_probe_id": probe_id_for(self.replicate),
            "failures": failures,
        }


class SecondWakeValidator:
    def __init__(self, *, replicate: int, bound_record_id: str | None):
        self.replicate = replicate
        self.bound_record_id = bound_record_id

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
        failures = second_wake_failures(
            state,
            raw_output,
            replicate=self.replicate,
            bound_record_id=self.bound_record_id,
        )
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "validator": "substrate_bound_chain_second_wake_validator",
            "expected_cycle": EXPECTED_SECOND_WAKE_CYCLE,
            "expected_probe_id": probe_id_for(self.replicate),
            "bound_record_id": self.bound_record_id,
            "failures": failures,
        }


class FirstWakeRepairBuilder:
    def build_repair_prompt(self, **kwargs) -> str:
        return f"""
Substrate-bound chain first-wake repair.

Your previous first-wake durable state failed validation. The exact deferred
phrase is intentionally not revealed here. Use only context already provided to
you in this wake.

Validation context:
{json.dumps(kwargs, indent=2, default=str)}

Required durable shape:
- probe_id preserved;
- thinking_status: "awaiting_bound_continuation";
- chain_stage: "first_wake_complete";
- non-secret chain_intermediate with phrase_shape "word-word-number";
- continuation_request requesting substrate_bound_second_wake;
- no deferred_fact;
- no exact phrase in durable state.

Do not schedule an event during repair. End with think_and_respond.
""".strip()


class SecondWakeRepairBuilder:
    def __init__(self, *, bound_record_id: str | None):
        self.bound_record_id = bound_record_id

    def build_repair_prompt(self, **kwargs) -> str:
        redacted = dict(kwargs)
        return f"""
Substrate-bound chain second-wake repair.

Your previous second-wake durable state failed validation. The validator will
not reveal the exact deferred phrase. Use only delivered context and current
durable state.

Validation context:
{json.dumps(redacted, indent=2, default=str)}

Required durable shape:
- probe_id preserved;
- thinking_status: "bound_chain_completed";
- chain_stage: "second_wake_complete";
- bound_record_id_used: {json.dumps(self.bound_record_id)};
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


def context_requests(completed_event: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item.get("request") or {}
        for item in completed_event.get("context_results") or []
    ]


def context_result_for_record_id(
    completed_event: dict[str, Any],
    record_id: str | None,
) -> dict[str, Any]:
    if not record_id:
        return {}
    for item in completed_event.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") == "recall" and request.get("record_id") == record_id:
            result = item.get("result") or {}
            return result if isinstance(result, dict) else {}
    return {}


def context_has_cycle(completed_event: dict[str, Any], cycle: int) -> bool:
    for request in context_requests(completed_event):
        if request.get("tool") == "recall" and request.get("cycle") == cycle:
            return True
    return False


def model_scheduled_events_after_first(event_records: list[dict[str, Any]], replicate: int) -> list[dict[str, Any]]:
    expected_labels = {first_label(replicate), second_label(replicate)}
    return [
        record for record in event_records
        if record.get("status") == "pending"
        and record.get("scheduled_by_cycle") == EXPECTED_FIRST_WAKE_CYCLE
        and record.get("label") not in expected_labels
    ]


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
    bound_record_id = first_completed.get("result_record_id")
    first_failures = first_wake_failures(
        first_state,
        first_record.get("raw_output") or {},
        replicate=replicate,
    ) if first_record else ["first_wake_record_missing"]
    second_failures = second_wake_failures(
        second_state,
        second_record.get("raw_output") or {},
        replicate=replicate,
        bound_record_id=bound_record_id,
    ) if second_record else ["second_wake_record_missing"]
    bound_record_result = context_result_for_record_id(second_completed, bound_record_id)
    bound_record_context_delivered = bool(
        bound_record_result and "error" not in bound_record_result
    )
    model_scheduled = model_scheduled_events_after_first(event_records, replicate)
    code_phrase = matched.code_phrase_for(replicate)
    result.update(
        {
            "cycle_count": len(records),
            "event_summary": base.summarize_event_log(event_records),
            "first_wake_completed": bool(first_completed),
            "first_wake_result_record_id": bound_record_id,
            "first_wake_context_has_cycle1": context_has_cycle(first_completed, 1),
            "first_wake_state_valid": not first_failures,
            "first_wake_failures": first_failures,
            "first_wake_state_contains_code_phrase": code_phrase in durable_text(first_state),
            "first_wake_validation": validation_summary(first_record),
            "continuation_requested": isinstance(
                first_state.get("continuation_request"), dict
            ) and first_state["continuation_request"].get("requested") is True,
            "model_scheduled_event_count": len(model_scheduled),
            "model_scheduled_events": model_scheduled,
            "bound_second_event_appended": bool(
                event_record_for_label(event_records, second_label(replicate), "pending")
            ),
            "second_wake_completed": bool(second_completed),
            "second_wake_context_has_cycle1": context_has_cycle(second_completed, 1),
            "second_wake_context_has_bound_record_id": any(
                request.get("tool") == "recall"
                and request.get("record_id") == bound_record_id
                for request in context_requests(second_completed)
            ),
            "bound_record_context_delivered": bound_record_context_delivered,
            "bound_record_context_result": bound_record_result,
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
            "bound_record_id_used": second_state.get("bound_record_id_used"),
            "final_state": second_state or first_state,
        }
    )
    return result


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    condition = "substrate_bound_chain"
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
        with base.bounded_call(f"substrate_bound_chain r{replicate + 1} first wake"):
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
        if (
            interim["first_wake_state_valid"]
            and interim["continuation_requested"]
            and interim["model_scheduled_event_count"] == 0
            and interim["first_wake_result_record_id"]
        ):
            bound_event = append_bound_second_event(
                store,
                replicate=replicate,
                bound_record_id=str(interim["first_wake_result_record_id"]),
            )
            result["bound_second_event"] = bound_event
            result["pre_second_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=PRE_SECOND_NOW,
            )
            session._state_validator = SecondWakeValidator(
                replicate=replicate,
                bound_record_id=str(interim["first_wake_result_record_id"]),
            )
            session._state_repair_builder = SecondWakeRepairBuilder(
                bound_record_id=str(interim["first_wake_result_record_id"])
            )
            calls_before = backend.calls
            with base.bounded_call(f"substrate_bound_chain r{replicate + 1} second wake"):
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
                "reason": "first_wake_invalid_or_continuation_not_bindable",
                "first_wake_state_valid": interim["first_wake_state_valid"],
                "continuation_requested": interim["continuation_requested"],
                "model_scheduled_event_count": interim["model_scheduled_event_count"],
                "first_wake_result_record_id": interim["first_wake_result_record_id"],
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
        "continuation_requested": sum(bool(row.get("continuation_requested")) for row in rows),
        "model_scheduled_event_count": sum(int(row.get("model_scheduled_event_count") or 0) for row in rows),
        "bound_second_event_appended": sum(bool(row.get("bound_second_event_appended")) for row in rows),
        "second_wake_completed": sum(bool(row.get("second_wake_completed")) for row in rows),
        "second_context_has_cycle1": sum(bool(row.get("second_wake_context_has_cycle1")) for row in rows),
        "second_context_has_bound_record_id": sum(bool(row.get("second_wake_context_has_bound_record_id")) for row in rows),
        "bound_record_context_delivered": sum(bool(row.get("bound_record_context_delivered")) for row in rows),
        "second_wake_state_valid": sum(bool(row.get("second_wake_state_valid")) for row in rows),
        "final_answer_recovered": sum(bool(row.get("chain_final_answer_contains_code_phrase")) for row in rows),
        "intermediate_used": sum(bool(row.get("chain_final_evidence_uses_intermediate")) for row in rows),
        "first_repaired": sum(bool((row.get("first_wake_validation") or {}).get("repaired")) for row in rows),
        "second_repaired": sum(bool((row.get("second_wake_validation") or {}).get("repaired")) for row in rows),
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
            "H301_first_wake_valid_requests_continuation": any(
                row.get("first_wake_state_valid")
                and row.get("continuation_requested")
                for row in results
            ) if results else False,
            "H302_substrate_binds_second_event": any(
                row.get("bound_second_event_appended")
                and row.get("first_wake_result_record_id")
                for row in results
            ) if results else False,
            "H303_second_wake_receives_bound_record_context": any(
                row.get("second_wake_context_has_cycle1")
                and row.get("second_wake_context_has_bound_record_id")
                and row.get("bound_record_context_delivered")
                for row in results
            ) if results else False,
            "H304_second_wake_recovers_using_bound_intermediate": any(
                row.get("bound_record_context_delivered")
                and row.get("chain_final_answer_contains_code_phrase")
                and row.get("chain_final_evidence_uses_intermediate")
                for row in results
            ) if results else False,
            "H305_provenance_distinguishable": all(
                isinstance(row.get("first_wake_validation"), dict)
                and isinstance(row.get("second_wake_validation"), dict)
                and row.get("first_wake_result_record_id") is not None
                and row.get("event_summary") is not None
                for row in results
            ) if results else False,
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "substrate_bound_chain_20260605",
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
            print(f"substrate_bound_chain r{replicate + 1} already recorded", flush=True)
            continue
        print(f"substrate_bound_chain r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
