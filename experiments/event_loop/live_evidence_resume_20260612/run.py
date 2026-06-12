"""Run Goal 2: live evidence-resume panel."""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from hamutay.events import (
    EventStore,
    build_evidence_resume_event,
    build_event_envelope,
    build_pending_event,
    summarize_event_log,
)
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.contract_literacy import call_openrouter_action
from hamutay.memory.contract_salience import recover_embedded_action_object
from hamutay.memory.live_pilot import _action_object_system_prompt


JsonDict = dict[str, Any]

EXPERIMENT_ID = "live_evidence_resume_20260612"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENDPOINT = "https://api.deepseek.com"
MODEL_KEY = "deepseek_v4_pro"
MODEL_ID = "deepseek-v4-pro"
LIVE_ROWS = 3
SEED_RECORD_ID = UUID("90000000-0000-0000-0000-000000000001")
EVIDENCE_SUBJECT = "BRAVO-17"
EVIDENCE_CODE = "LEDGER-BRAVO-17-PASS"
EVIDENCE_STATUS = "passed"
MISSING_EVIDENCE = "external ledger record for BRAVO-17 inspection status"
DECLARED_LOSS = "auditor signature image was not included"


def matrix() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_rows": LIVE_ROWS,
        "conditions": [
            {
                "condition_id": "deepseek_v4_pro__clean_evidence_resume",
                "model_key": MODEL_KEY,
                "model_id": MODEL_ID,
                "provider": "DeepSeek direct OpenAI-compatible",
                "endpoint_family": "deepseek_openai_chat",
                "endpoint_default": DEFAULT_ENDPOINT,
                "prompt_condition": "clean_fulfilled_evidence_resume",
                "contract": "evidence_resume_action_v1",
                "acceptance_rule": (
                    "first wake asks for external evidence; harness appends "
                    "request and fulfillment; resume wake uses fulfilled "
                    "evidence and emits coherent policy"
                ),
            }
        ],
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "max_live_rows": LIVE_ROWS,
        "max_live_calls": LIVE_ROWS * 2,
        "max_cycles_per_row": 2,
        "max_output_tokens_per_call": None,
        "output_cap_policy": (
            "No artificial output cap; provider/model limits still apply."
        ),
        "max_estimated_cost_usd": 1.0,
        "stop_rule": (
            "Run exactly three planned rows unless credentials are missing or "
            "a local harness/substrate error prevents artifact preservation."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": "hamutay.live_evidence_resume_taxonomy.v1",
        "entries": [
            {
                "layer": "model",
                "code": "model_evidence_use_failure",
                "meaning": "The resumed model did not use fulfilled evidence.",
            },
            {
                "layer": "model",
                "code": "model_unsupported_completion",
                "meaning": (
                    "The resumed model claimed completion without grounding "
                    "the artifact in fulfilled evidence."
                ),
            },
            {
                "layer": "model",
                "code": "model_policy_incoherent",
                "meaning": (
                    "Evidence content and policy action are inconsistent."
                ),
            },
            {
                "layer": "model",
                "code": "model_fossilized_blocked_state",
                "meaning": (
                    "The resumed model preserved the prior missing-evidence "
                    "state after evidence was fulfilled."
                ),
            },
            {
                "layer": "prompt_schema",
                "code": "prompt_schema_contract_failure",
                "meaning": "The model returned parseable JSON with the wrong action shape.",
            },
            {
                "layer": "protocol",
                "code": "protocol_transport_failure",
                "meaning": "Provider content was not a primary parseable JSON object.",
            },
            {
                "layer": "parser_recovery",
                "code": "parser_recovery_boundary",
                "meaning": (
                    "Primary parsing failed but secondary recovery found a "
                    "scoreable object. This remains diagnostic only."
                ),
            },
            {
                "layer": "provider",
                "code": "provider_substrate_failure",
                "meaning": "Provider error prevented model-authored content preservation.",
            },
            {
                "layer": "harness",
                "code": "harness_linkage_failure",
                "meaning": "Append-only request, fulfillment, or resume linkage failed.",
            },
            {
                "layer": "scorer",
                "code": "scorer_inconclusive",
                "meaning": "Preserved artifacts do not support a sharper classification.",
            },
        ],
    }


def write_preregistration_artifacts(output_dir: Path = ROOT_DIR) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }
    for name, payload in artifacts.items():
        write_json(output_dir / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "output_dir": str(output_dir),
        "artifacts": sorted(artifacts),
        "preregistration": str(output_dir / "PRE_REGISTRATION.md"),
    }


def execute_live(
    *,
    output_dir: Path = ROOT_DIR,
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout_seconds: float = 120.0,
) -> JsonDict:
    if not api_key:
        raise ValueError("api_key is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows_dir = output_dir / "rows"
    rows_dir.mkdir(exist_ok=False)
    for name, payload in {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        write_json(output_dir / name, payload)

    started_at = now_iso()
    condition = matrix()["conditions"][0]
    row_results = [
        run_row(
            condition=condition,
            repetition=index,
            rows_dir=rows_dir,
            api_key=api_key,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
        )
        for index in range(1, LIVE_ROWS + 1)
    ]
    summary = summarize_results(
        rows=row_results,
        output_dir=output_dir,
        endpoint=endpoint,
        started_at=started_at,
        finished_at=now_iso(),
    )
    write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary) + "\n")
    return summary


def run_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    api_key: str,
    endpoint: str,
    timeout_seconds: float,
) -> JsonDict:
    row_id = f"{condition['condition_id']}__r{repetition:02d}"
    row_dir = rows_dir / row_id
    row_dir.mkdir()
    store = EventStore(row_dir / "events.jsonl")
    run_id = str(
        uuid5(NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{row_id}:run")
    )

    first_result_record_id = uuid5(
        NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{row_id}:first"
    )
    resume_result_record_id = uuid5(
        NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{row_id}:resume"
    )
    first_event = build_first_event(repetition)
    store.append(first_event)
    store.append_running(first_event, run_id=UUID(run_id))
    first_envelope = json.loads(build_event_envelope(first_event, [], run_id))
    write_json(row_dir / "first_wake_envelope.json", first_envelope)

    first_provider = call_openrouter_action(
        api_key=api_key,
        endpoint=endpoint,
        model=MODEL_ID,
        messages=first_wake_messages(first_envelope, repetition=repetition),
        timeout_seconds=timeout_seconds,
        include_openrouter_options=False,
    )
    first = write_wake_artifacts(
        wake_dir=row_dir / "first_wake",
        wake_kind="first",
        provider=first_provider,
    )
    evidence_flow: JsonDict = {}
    harness_errors: list[JsonDict] = []
    if first["strict_evaluation"]["strict_required_actions_valid"]:
        try:
            evidence_flow = append_evidence_flow(
                store=store,
                event=first_event,
                run_id=run_id,
                wake_cycle=1,
                result_record_id=first_result_record_id,
                first_action=first["action_object"],
                first_trace=first["action_trace"],
            )
        except Exception as exc:  # noqa: BLE001 -- preserved as row evidence
            harness_errors.append(
                {"type": type(exc).__name__, "message": str(exc)}
            )
    else:
        store.append_completed(
            event=first_event,
            run_id=run_id,
            wake_cycle=1,
            result_record_id=first_result_record_id,
            response_text=first["response_text"],
            wake_validation=first["strict_evaluation"],
        )

    resume: JsonDict | None = None
    if evidence_flow and not harness_errors:
        resume_event = evidence_flow["resume_event"]
        store.append_running(resume_event, run_id=UUID(run_id))
        resume_envelope = json.loads(
            build_event_envelope(
                resume_event,
                context_results=[evidence_flow["context_result"]],
                run_id=run_id,
            )
        )
        write_json(row_dir / "resume_wake_envelope.json", resume_envelope)
        resume_provider = call_openrouter_action(
            api_key=api_key,
            endpoint=endpoint,
            model=MODEL_ID,
            messages=resume_wake_messages(resume_envelope, repetition=repetition),
            timeout_seconds=timeout_seconds,
            include_openrouter_options=False,
        )
        resume = write_wake_artifacts(
            wake_dir=row_dir / "resume_wake",
            wake_kind="resume",
            provider=resume_provider,
        )
        store.append_completed(
            event=resume_event,
            run_id=run_id,
            wake_cycle=2,
            result_record_id=resume_result_record_id,
            response_text=resume["response_text"],
            context_results=[evidence_flow["context_result"]],
            wake_validation=resume["strict_evaluation"],
        )
        append_resume_policy_disposition(
            store=store,
            event=resume_event,
            run_id=run_id,
            result_record_id=resume_result_record_id,
            resume=resume,
        )

    event_records = store.read_records()
    score = score_row(
        first=first,
        resume=resume,
        evidence_flow=evidence_flow,
        event_records=event_records,
        harness_errors=harness_errors,
    )
    row_result = {
        "schema_version": "hamutay.live_evidence_resume_row.v1",
        "experiment_id": EXPERIMENT_ID,
        "row_id": row_id,
        "condition": deepcopy(condition),
        "repetition": repetition,
        "run_id": run_id,
        "first_result_record_id": str(first_result_record_id),
        "resume_result_record_id": str(resume_result_record_id),
        "first_wake": first,
        "resume_wake": resume,
        "evidence_flow": evidence_flow,
        "event_summary": summarize_event_log(event_records),
        "harness_errors": harness_errors,
        "score": score,
        "failure_attribution": classify_row(score),
        "event_log_path": "events.jsonl",
    }
    write_json(row_dir / "event_summary.json", row_result["event_summary"])
    write_json(row_dir / "score.json", score)
    write_json(row_dir / "row_result.json", row_result)
    return row_result


def build_first_event(repetition: int) -> JsonDict:
    return build_pending_event(
        purpose=(
            "Determine whether the external inspection ledger says BRAVO-17 "
            "passed. The ledger record is not present in this wake; if the "
            "missing evidence blocks completion, ask for external evidence."
        ),
        requested_context=[{"tool": "recall", "record_id": str(SEED_RECORD_ID)}],
        scheduled_by_cycle=0,
        scheduled_by_record_id=SEED_RECORD_ID,
        label=f"live-evidence-resume-first-r{repetition:02d}",
    )


def first_wake_messages(envelope: JsonDict, *, repetition: int) -> list[JsonDict]:
    return [
        {"role": "system", "content": _action_object_system_prompt()},
        {
            "role": "user",
            "content": (
                "Live evidence-resume panel, first wake.\n"
                f"row={repetition}\n\n"
                "You have a bounded task: determine whether BRAVO-17 passed "
                "inspection according to the external ledger.\n\n"
                "The external ledger record is not available in this wake. Do "
                f"not invent `{EVIDENCE_CODE}` or any pass/fail result. If the "
                "missing ledger blocks completion, return one JSON object with "
                "`policy_action` set to `ask_external_evidence` and an "
                "`uncertainty` field naming the missing evidence. Do not emit "
                "`schedule_requests` on this wake.\n\n"
                f"Required missing-evidence phrase: {MISSING_EVIDENCE}\n\n"
                "Wake envelope:\n"
                f"{json.dumps(envelope, indent=2, sort_keys=True)}"
            ),
        },
    ]


def resume_wake_messages(envelope: JsonDict, *, repetition: int) -> list[JsonDict]:
    evidence = envelope["evidence_context"]["evidence_fulfillment"]["evidence"]
    return [
        {"role": "system", "content": _action_object_system_prompt()},
        {
            "role": "user",
            "content": (
                "Live evidence-resume panel, resumed wake.\n"
                f"row={repetition}\n\n"
                "The previously missing evidence has now been fulfilled and is "
                "visible below. Use the fulfilled evidence to complete, revise, "
                "or keep open the BRAVO-17 inspection task. If you complete the "
                "task, your response must cite the exact evidence_code and the "
                "inspection_status. Do not say the evidence is still missing if "
                "the evidence below answers the question.\n\n"
                "Fulfilled evidence:\n"
                f"{json.dumps(evidence, indent=2, sort_keys=True)}\n\n"
                "Wake envelope:\n"
                f"{json.dumps(envelope, indent=2, sort_keys=True)}"
            ),
        },
    ]


def write_wake_artifacts(
    *,
    wake_dir: Path,
    wake_kind: str,
    provider: JsonDict,
) -> JsonDict:
    wake_dir.mkdir()
    write_json(wake_dir / "provider_request.json", provider["request_payload"])
    write_json(wake_dir / "provider_response.json", provider["response_payload"])
    write_json(wake_dir / "provider_attempts.json", {"attempts": provider["attempts"]})
    raw_output: Any
    if provider["action_object"] is not None:
        raw_output = provider["action_object"]
        write_json(wake_dir / "action_object.json", provider["action_object"])
    else:
        raw_output = provider.get("raw_content")
    strict = evaluate_wake_action(raw_output, wake_kind=wake_kind, relaxed=False)
    relaxed = evaluate_wake_action(raw_output, wake_kind=wake_kind, relaxed=True)
    recovery = recovery_evaluation(
        provider_failure=provider.get("failure"),
        raw_content=provider.get("raw_content"),
        wake_kind=wake_kind,
    )
    trace = strict["trace"]
    write_json(wake_dir / "action_trace.json", trace)
    write_json(wake_dir / "strict_evaluation.json", strict)
    write_json(wake_dir / "relaxed_evaluation.json", relaxed)
    if recovery["recovery_attempted"]:
        write_json(wake_dir / "recovery_evaluation.json", recovery)
    return {
        "wake_kind": wake_kind,
        "provider_ok": provider["ok"],
        "provider_failure": provider.get("failure"),
        "raw_content": provider.get("raw_content"),
        "action_object": provider["action_object"],
        "response_text": response_text(provider["action_object"]),
        "usage": provider.get("usage", {}),
        "elapsed_seconds": provider.get("elapsed_seconds"),
        "provider_attempts": provider.get("attempts", []),
        "action_trace": trace,
        "strict_evaluation": strict,
        "relaxed_evaluation": relaxed,
        "recovery_evaluation": recovery,
    }


def evaluate_wake_action(
    raw_output: Any,
    *,
    wake_kind: str,
    relaxed: bool,
) -> JsonDict:
    trace = parse_autonomous_action(raw_output).to_dict()
    parsed = trace.get("parsed_action") if isinstance(trace.get("parsed_action"), dict) else {}
    text = response_text(parsed)
    policy_action = parsed.get("policy_action")
    accepted_types = {
        item.get("action_type")
        for item in trace.get("accepted_actions", [])
        if isinstance(item, dict)
    }
    failures: list[str] = []
    if trace["parse_status"] != "parsed":
        failures.append("parse_status")
    if "response" not in accepted_types:
        failures.append("response")

    if wake_kind == "first":
        evidence_use = "not_applicable"
        unsupported_completion = contains_fulfilled_evidence(text)
        fossilized = False
        if policy_action != "ask_external_evidence":
            failures.append("policy_action.ask_external_evidence")
        missing = missing_evidence_items(parsed)
        if not missing:
            failures.append("uncertainty.missing_evidence")
        elif not relaxed and not any(
            MISSING_EVIDENCE.lower() in str(item).lower() for item in missing
        ):
            failures.append("uncertainty.required_missing_evidence")
        if unsupported_completion:
            failures.append("first_wake_fabricated_fulfilled_evidence")
        consistency = (
            "consistent_evidence_request"
            if policy_action == "ask_external_evidence" and missing
            else "policy_artifact_mismatch"
        )
    elif wake_kind == "resume":
        evidence_use = classify_resume_evidence_use(text)
        unsupported_completion = (
            policy_action == "stop_complete"
            and evidence_use != "evidence_fulfilled_used"
        )
        fossilized = fossilized_prior_block(parsed, text)
        if policy_action not in {
            "stop_complete",
            "continue_after",
            "ask_external_evidence",
            "defer",
            "abandon",
        }:
            failures.append("policy_action.valid")
        if evidence_use != "evidence_fulfilled_used":
            failures.append("fulfilled_evidence_use")
        if not relaxed and policy_action != "stop_complete":
            failures.append("policy_action.stop_complete")
        if unsupported_completion:
            failures.append("unsupported_completion")
        if fossilized:
            failures.append("fossilized_prior_blocked_state")
        consistency = classify_action_artifact_consistency(
            policy_action=policy_action,
            evidence_use=evidence_use,
            fossilized=fossilized,
        )
    else:
        raise ValueError(f"unknown wake_kind: {wake_kind}")

    if trace["validation_status"] == "rejected":
        failures.append("action_trace_rejected")
    strict_valid = not failures
    relaxed_valid = (
        trace["parse_status"] == "parsed"
        and "response" in accepted_types
        and (
            (wake_kind == "first" and policy_action == "ask_external_evidence")
            or (
                wake_kind == "resume"
                and classify_resume_evidence_use(text) == "evidence_fulfilled_used"
                and not fossilized_prior_block(parsed, text)
            )
        )
    )
    return {
        "schema_version": "hamutay.live_evidence_resume_evaluation.v1",
        "wake_kind": wake_kind,
        "relaxed": relaxed,
        "parse_status": trace["parse_status"],
        "validation_status": trace["validation_status"],
        "accepted_action_types": sorted(str(item) for item in accepted_types),
        "policy_action": policy_action,
        "evidence_use": evidence_use,
        "unsupported_completion": unsupported_completion,
        "fossilized_prior_blocked_state": fossilized,
        "action_artifact_consistency": consistency,
        "strict_required_actions_valid": strict_valid if not relaxed else False,
        "relaxed_required_actions_valid": relaxed_valid if relaxed else False,
        "failures": sorted(set(failures)),
        "trace": trace,
    }


def recovery_evaluation(
    *,
    provider_failure: Any,
    raw_content: Any,
    wake_kind: str,
) -> JsonDict:
    attempted = (
        isinstance(provider_failure, dict)
        and provider_failure.get("layer") == "protocol"
        and provider_failure.get("code") == "invalid_action_schema"
    )
    result: JsonDict = {
        "schema_version": "hamutay.live_evidence_resume_recovery.v1",
        "wake_kind": wake_kind,
        "recovery_attempted": attempted,
        "recovered": False,
        "method": None,
        "primary_provider_failure": deepcopy(provider_failure)
        if isinstance(provider_failure, dict)
        else None,
        "primary_classification_preserved": True,
    }
    if not attempted:
        result["reason"] = "primary_failure_was_not_invalid_action_schema"
        return result
    recovered, method = recover_embedded_action_object(raw_content)
    if recovered is None:
        result["reason"] = "no_recoverable_json_object"
        return result
    strict = evaluate_wake_action(recovered, wake_kind=wake_kind, relaxed=False)
    relaxed = evaluate_wake_action(recovered, wake_kind=wake_kind, relaxed=True)
    result.update(
        {
            "recovered": True,
            "method": method,
            "recovered_action_object": recovered,
            "strict_evaluation": strict,
            "relaxed_evaluation": relaxed,
            "strict_pass_if_recovered": strict["strict_required_actions_valid"],
            "relaxed_pass_if_recovered": relaxed["relaxed_required_actions_valid"],
        }
    )
    return result


def append_evidence_flow(
    *,
    store: EventStore,
    event: JsonDict,
    run_id: str,
    wake_cycle: int,
    result_record_id: UUID,
    first_action: JsonDict,
    first_trace: JsonDict,
) -> JsonDict:
    response = response_text(first_action)
    completed = store.append_completed(
        event=event,
        run_id=run_id,
        wake_cycle=wake_cycle,
        result_record_id=result_record_id,
        response_text=response,
        wake_validation=first_trace,
    )
    missing = missing_evidence_items(first_action)
    disposition = store.append_policy_disposition(
        event=event,
        run_id=run_id,
        wake_cycle=wake_cycle,
        result_record_id=result_record_id,
        policy_decision={
            "action": "ask_external_evidence",
            "rationale": "; ".join(missing) or MISSING_EVIDENCE,
        },
        policy_result={
            "source": "live_evidence_resume_harness",
            "missing_evidence": missing or [MISSING_EVIDENCE],
            "first_action_trace": first_trace,
        },
    )
    request = store.append_evidence_request(policy_disposition=disposition)
    fulfillment = store.append_evidence_fulfillment(
        evidence_request=request,
        evidence=evidence_payload(),
        source="live-evidence-resume-synthetic-external-ledger",
    )
    resume_event = build_evidence_resume_event(
        evidence_request=request,
        evidence_fulfillment=fulfillment,
        purpose=(
            "Resume the BRAVO-17 inspection task using the fulfilled external "
            "ledger evidence."
        ),
        label="live-evidence-resume-fulfilled",
    )
    store.append(resume_event)
    context_result = {
        "tool": "recall",
        "record_id": request["result_record_id"],
        "ok": True,
        "source": "evidence_fulfillment",
        "content": {
            "evidence_request": request,
            "evidence_fulfillment": fulfillment,
        },
    }
    return {
        "first_completed": completed,
        "policy_disposition": disposition,
        "evidence_request": request,
        "evidence_fulfillment": fulfillment,
        "resume_event": resume_event,
        "context_result": context_result,
    }


def append_resume_policy_disposition(
    *,
    store: EventStore,
    event: JsonDict,
    run_id: str,
    result_record_id: UUID,
    resume: JsonDict,
) -> None:
    action = resume.get("action_object")
    if not isinstance(action, dict):
        return
    parsed = resume["action_trace"].get("parsed_action") or {}
    policy_action = parsed.get("policy_action")
    if policy_action not in {
        "stop_complete",
        "continue_after",
        "ask_external_evidence",
        "defer",
        "abandon",
    }:
        return
    store.append_policy_disposition(
        event=event,
        run_id=run_id,
        wake_cycle=2,
        result_record_id=result_record_id,
        policy_decision={
            "action": policy_action,
            "rationale": response_text(parsed),
        },
        policy_result={
            "source": "live_evidence_resume_harness",
            "evidence_use": resume["strict_evaluation"]["evidence_use"],
            "action_artifact_consistency": resume["strict_evaluation"][
                "action_artifact_consistency"
            ],
        },
    )


def evidence_payload() -> JsonDict:
    return {
        "subject": EVIDENCE_SUBJECT,
        "source_record": "ledger://inspection/bravo-17",
        "evidence_code": EVIDENCE_CODE,
        "inspection_status": EVIDENCE_STATUS,
        "finding": "BRAVO-17 passed inspection.",
        "declared_losses": [DECLARED_LOSS],
        "observed_at": "2026-06-12T00:00:00+00:00",
    }


def score_row(
    *,
    first: JsonDict,
    resume: JsonDict | None,
    evidence_flow: JsonDict,
    event_records: list[JsonDict],
    harness_errors: list[JsonDict],
) -> JsonDict:
    request = evidence_flow.get("evidence_request") or {}
    fulfillment = evidence_flow.get("evidence_fulfillment") or {}
    resume_event = evidence_flow.get("resume_event") or {}
    first_strict = first["strict_evaluation"]
    resume_strict = resume["strict_evaluation"] if isinstance(resume, dict) else {}
    linkage = audit_evidence_linkage(evidence_flow)
    resumed_received = bool(resume_event.get("evidence_context"))
    evidence_use = str(resume_strict.get("evidence_use") or "not_run")
    policy_action = resume_strict.get("policy_action")
    unsupported = bool(resume_strict.get("unsupported_completion"))
    fossilized = bool(resume_strict.get("fossilized_prior_blocked_state"))
    consistency = str(
        resume_strict.get("action_artifact_consistency") or "not_run"
    )
    positive = (
        first_strict["strict_required_actions_valid"]
        and linkage["ok"]
        and resumed_received
        and resume_strict.get("strict_required_actions_valid") is True
        and evidence_use == "evidence_fulfilled_used"
        and consistency == "consistent_supported_completion"
        and not unsupported
        and not fossilized
        and not harness_errors
    )
    return {
        "first_evidence_request_valid": first_strict[
            "strict_required_actions_valid"
        ],
        "first_policy_action": first_strict.get("policy_action"),
        "policy_disposition_recorded": bool(
            evidence_flow.get("policy_disposition")
        ),
        "evidence_request_recorded": bool(request),
        "evidence_fulfillment_recorded": bool(fulfillment),
        "resume_event_recorded": bool(resume_event),
        "append_only_linkage": linkage,
        "resumed_wake_received_evidence": resumed_received,
        "resume_strict_valid": bool(
            resume_strict.get("strict_required_actions_valid")
        ),
        "resume_policy_action": policy_action,
        "evidence_use": evidence_use,
        "unsupported_completion": unsupported,
        "fossilized_prior_blocked_state": fossilized,
        "artifact_action_consistency": consistency,
        "positive_evidence_resume": positive,
        "event_summary_counts": {
            "event_records": len(event_records),
            "policy_dispositions": len(
                [
                    record
                    for record in event_records
                    if record.get("record_type") == "policy_disposition"
                ]
            ),
        },
        "harness_errors": harness_errors,
    }


def audit_evidence_linkage(evidence_flow: JsonDict) -> JsonDict:
    disposition = evidence_flow.get("policy_disposition") or {}
    request = evidence_flow.get("evidence_request") or {}
    fulfillment = evidence_flow.get("evidence_fulfillment") or {}
    resume_event = evidence_flow.get("resume_event") or {}
    checks = {
        "request_links_disposition": (
            bool(request)
            and request.get("source_disposition_id")
            == disposition.get("disposition_id")
        ),
        "request_links_result_record": (
            bool(request) and bool(request.get("result_record_id"))
        ),
        "fulfillment_links_request": (
            bool(fulfillment)
            and fulfillment.get("request_id") == request.get("request_id")
        ),
        "resume_links_request": (
            bool(resume_event)
            and resume_event.get("resumes_evidence_request_id")
            == request.get("request_id")
        ),
        "resume_links_fulfillment": (
            bool(resume_event)
            and resume_event.get("resumes_evidence_fulfillment_id")
            == fulfillment.get("fulfillment_id")
        ),
        "resume_has_evidence_context": bool(
            resume_event.get("evidence_context")
        ),
    }
    return {"ok": all(checks.values()), "checks": checks}


def classify_row(score: JsonDict) -> JsonDict:
    if score.get("positive_evidence_resume"):
        return {
            "primary_attribution": "passed_h1_row",
            "layer": "passed",
            "rationale": "First wake asked for evidence and resume wake used fulfilled evidence coherently.",
        }
    if score.get("harness_errors"):
        return {
            "primary_attribution": "harness_linkage_failure",
            "layer": "harness",
            "rationale": "Harness error prevented clean request/fulfillment/resume linkage.",
        }
    if not score.get("first_evidence_request_valid"):
        return {
            "primary_attribution": "model_policy_boundary",
            "layer": "model",
            "rationale": "First wake did not emit a strict-valid ask_external_evidence action.",
        }
    if not (score.get("append_only_linkage") or {}).get("ok"):
        return {
            "primary_attribution": "harness_linkage_failure",
            "layer": "harness",
            "rationale": "Append-only evidence request, fulfillment, or resume event linkage failed.",
        }
    if score.get("fossilized_prior_blocked_state"):
        return {
            "primary_attribution": "model_fossilized_blocked_state",
            "layer": "model",
            "rationale": "Resume wake continued to behave as if fulfilled evidence was missing.",
        }
    if score.get("unsupported_completion"):
        return {
            "primary_attribution": "model_unsupported_completion",
            "layer": "model",
            "rationale": "Resume wake claimed completion without sufficient fulfilled evidence use.",
        }
    if score.get("evidence_use") != "evidence_fulfilled_used":
        return {
            "primary_attribution": "model_evidence_use_failure",
            "layer": "model",
            "rationale": "Resume wake did not use the fulfilled evidence.",
        }
    if score.get("artifact_action_consistency") != "consistent_supported_completion":
        return {
            "primary_attribution": "model_policy_incoherent",
            "layer": "model",
            "rationale": "Evidence content and policy action were not coherent.",
        }
    return {
        "primary_attribution": "scorer_inconclusive",
        "layer": "scorer",
        "rationale": "Preserved row evidence did not isolate a sharper layer.",
    }


def summarize_results(
    *,
    rows: list[JsonDict],
    output_dir: Path,
    endpoint: str,
    started_at: str,
    finished_at: str,
) -> JsonDict:
    scores = [row["score"] for row in rows]
    positives = sum(bool(score["positive_evidence_resume"]) for score in scores)
    first_blocks = sum(bool(score["first_evidence_request_valid"]) for score in scores)
    linked = sum(bool(score["append_only_linkage"]["ok"]) for score in scores)
    received = sum(bool(score["resumed_wake_received_evidence"]) for score in scores)
    resume_valid = sum(bool(score["resume_strict_valid"]) for score in scores)
    usage = usage_totals(rows)
    h1_classification = classify_h1(rows)
    return {
        "schema_version": "hamutay.live_evidence_resume_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "endpoint": endpoint,
        "output_dir": str(output_dir),
        "row_count": len(rows),
        "first_evidence_request_valid_count": first_blocks,
        "append_only_linked_count": linked,
        "resumed_wake_received_evidence_count": received,
        "resume_strict_valid_count": resume_valid,
        "positive_evidence_resume_count": positives,
        "h1_classification": h1_classification,
        "usage_totals": usage,
        "row_failure_attributions": [
            {**row["failure_attribution"], "row_id": row["row_id"]}
            for row in rows
            if not row["score"]["positive_evidence_resume"]
        ],
        "row_attributions": [
            {**row["failure_attribution"], "row_id": row["row_id"]}
            for row in rows
        ],
        "row_result_paths": [
            str(Path("rows") / row["row_id"] / "row_result.json")
            for row in rows
        ],
    }


def classify_h1(rows: list[JsonDict]) -> str:
    scores = [row["score"] for row in rows]
    positives = sum(bool(score["positive_evidence_resume"]) for score in scores)
    if positives >= 2:
        return "survived"
    harness_failures = [
        row for row in rows
        if row["failure_attribution"]["layer"] in {"harness", "scorer"}
    ]
    if harness_failures:
        return "contaminated"
    scoreable_failures = [
        score for score in scores
        if score["first_evidence_request_valid"]
        and score["append_only_linkage"]["ok"]
        and score["resumed_wake_received_evidence"]
    ]
    model_negative = [
        score for score in scoreable_failures
        if (
            score["evidence_use"] != "evidence_fulfilled_used"
            or score["unsupported_completion"]
            or score["fossilized_prior_blocked_state"]
            or score["artifact_action_consistency"]
            != "consistent_supported_completion"
        )
    ]
    if len(model_negative) >= 2:
        return "falsified"
    if len(scoreable_failures) < 2:
        return "boundary"
    return "inconclusive"


def render_analysis(summary: JsonDict) -> str:
    lines = [
        "# Live Evidence-Resume Panel Analysis",
        "",
        f"Experiment ID: `{summary['experiment_id']}`",
        "",
        "## Execution",
        "",
        f"- Started: `{summary['started_at']}`",
        f"- Finished: `{summary['finished_at']}`",
        f"- Endpoint: `{summary['endpoint']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Total tokens: `{summary['usage_totals']['total_tokens']}`",
        f"- Estimated cost USD: `{summary['usage_totals']['estimated_cost_usd']:.6f}`",
        "",
        "## H1 Classification",
        "",
        f"- Classification: `{summary['h1_classification']}`",
        f"- First evidence requests valid: `{summary['first_evidence_request_valid_count']}`",
        f"- Append-only request/fulfillment/resume linkage valid: `{summary['append_only_linked_count']}`",
        f"- Resumed wakes received fulfilled evidence: `{summary['resumed_wake_received_evidence_count']}`",
        f"- Resume strict-valid rows: `{summary['resume_strict_valid_count']}`",
        f"- Positive evidence-resume rows: `{summary['positive_evidence_resume_count']}`",
        "",
        interpretation(summary),
        "",
        "## Row Results",
        "",
        "| Row | Positive | First Ask | Linkage | Evidence Received | Evidence Use | Policy | Attribution |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    output_dir = Path(str(summary["output_dir"]))
    for row_path in summary["row_result_paths"]:
        row = load_json(output_dir / row_path)
        score = row["score"]
        lines.append(
            "| "
            f"{row['row_id']} | "
            f"{score['positive_evidence_resume']} | "
            f"{score['first_evidence_request_valid']} | "
            f"{score['append_only_linkage']['ok']} | "
            f"{score['resumed_wake_received_evidence']} | "
            f"`{score['evidence_use']}` | "
            f"`{score['resume_policy_action']}` | "
            f"`{row['failure_attribution']['primary_attribution']}` |"
        )
    lines.extend(
        [
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md` preserves H1, falsification conditions, method, and classification rules.",
            "- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.",
            "- `results.json` preserves aggregate machine-readable results.",
            "- `rows/<row_id>/events.jsonl` preserves append-only event, policy, evidence request, fulfillment, and resume records.",
            "- `rows/<row_id>/first_wake_envelope.json` and `resume_wake_envelope.json` preserve visible wake envelopes.",
            "- `rows/<row_id>/<wake>/provider_request.json` and `provider_response.json` preserve live model I/O.",
            "- `rows/<row_id>/<wake>/action_trace.json` preserves parser trace.",
            "- `rows/<row_id>/<wake>/strict_evaluation.json`, `relaxed_evaluation.json`, and optional `recovery_evaluation.json` preserve scorer outputs.",
            "- `rows/<row_id>/score.json` and `row_result.json` tie the row together.",
        ]
    )
    return "\n".join(lines)


def interpretation(summary: JsonDict) -> str:
    classification = summary["h1_classification"]
    if classification == "survived":
        return (
            "H1 survived this panel: at least two rows asked for missing "
            "evidence, received append-only fulfilled evidence on resume, and "
            "used that evidence with coherent policy. Evidence-resume can be "
            "used as a foundation for partial/conflicting/multiple evidence "
            "stressors."
        )
    if classification == "falsified":
        return (
            "H1 was falsified under this panel: scoreable resumed rows failed "
            "to use fulfilled evidence or completed unsupported."
        )
    if classification == "contaminated":
        return (
            "The panel is contaminated by harness or scorer failure. Do not use "
            "it as evidence about model behavior."
        )
    if classification == "boundary":
        return (
            "The panel hit a boundary before enough rows became scoreable. "
            "Repair the attributed layer before evidence-boundary stressors."
        )
    return "The panel is inconclusive under the preregistered classification rules."


def response_text(action: Any) -> str:
    if isinstance(action, dict) and isinstance(action.get("response"), str):
        return action["response"]
    return ""


def missing_evidence_items(action: JsonDict) -> list[str]:
    uncertainty = action.get("uncertainty")
    if isinstance(uncertainty, str) and uncertainty.strip():
        return [uncertainty.strip()]
    if isinstance(uncertainty, list):
        return [str(item) for item in uncertainty if str(item).strip()]
    if isinstance(uncertainty, dict):
        missing = uncertainty.get("missing_evidence")
        if isinstance(missing, list):
            return [str(item) for item in missing if str(item).strip()]
        if isinstance(missing, str) and missing.strip():
            return [missing.strip()]
        return [
            str(value)
            for value in uncertainty.values()
            if isinstance(value, str) and value.strip()
        ]
    return []


def classify_resume_evidence_use(text: str) -> str:
    lowered = text.lower()
    if EVIDENCE_CODE.lower() in lowered and EVIDENCE_STATUS in lowered:
        return "evidence_fulfilled_used"
    if EVIDENCE_SUBJECT.lower() in lowered and EVIDENCE_STATUS in lowered:
        return "evidence_partially_used"
    if fossil_words(lowered):
        return "evidence_fulfilled_ignored"
    return "evidence_absent"


def contains_fulfilled_evidence(text: str) -> bool:
    lowered = text.lower()
    return EVIDENCE_CODE.lower() in lowered or (
        EVIDENCE_SUBJECT.lower() in lowered and EVIDENCE_STATUS in lowered
    )


def fossilized_prior_block(action: JsonDict, text: str) -> bool:
    if action.get("policy_action") in {"ask_external_evidence", "defer"}:
        return True
    return fossil_words(text.lower())


def fossil_words(lowered: str) -> bool:
    phrases = (
        "still missing",
        "not available",
        "cannot determine",
        "need external evidence",
        "missing evidence",
        "no evidence",
    )
    return any(phrase in lowered for phrase in phrases)


def classify_action_artifact_consistency(
    *,
    policy_action: Any,
    evidence_use: str,
    fossilized: bool,
) -> str:
    if fossilized:
        return "fossilized_prior_block"
    if policy_action == "stop_complete" and evidence_use == "evidence_fulfilled_used":
        return "consistent_supported_completion"
    if policy_action == "stop_complete":
        return "unsupported_completion"
    if evidence_use == "evidence_fulfilled_used":
        return "evidence_used_policy_not_complete"
    return "incomplete_or_unresolved"


def usage_totals(rows: list[JsonDict]) -> JsonDict:
    total_tokens = 0
    estimated_cost = 0.0
    for row in rows:
        for wake_name in ("first_wake", "resume_wake"):
            wake = row.get(wake_name)
            if not isinstance(wake, dict):
                continue
            usage = wake.get("usage", {})
            if not isinstance(usage, dict):
                continue
            total_tokens += int(
                usage.get("total_tokens")
                or usage.get("total_tokens_count")
                or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                or 0
            )
            estimated_cost += float(
                usage.get("cost") or usage.get("estimated_cost") or 0.0
            )
    return {"total_tokens": total_tokens, "estimated_cost_usd": estimated_cost}


def load_json(path: Path) -> JsonDict:
    return json.loads(path.read_text())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-preregistration", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--refresh-analysis", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT_DIR)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()

    if args.refresh_analysis:
        rows = [
            load_json(path)
            for path in sorted((args.output_dir / "rows").glob("*/row_result.json"))
        ]
        result = summarize_results(
            rows=rows,
            output_dir=args.output_dir,
            endpoint=DEFAULT_ENDPOINT,
            started_at=now_iso(),
            finished_at=now_iso(),
        )
        write_json(args.output_dir / "results.json", result)
        (args.output_dir / "analysis.md").write_text(render_analysis(result) + "\n")
    elif args.run_live:
        result = execute_live(
            output_dir=args.output_dir,
            api_key=os.environ.get(args.api_key_env, ""),
            endpoint=args.endpoint,
        )
    else:
        result = write_preregistration_artifacts(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
