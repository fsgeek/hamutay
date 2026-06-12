"""Run Goal 3: evidence-boundary stressor panel."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from hamutay.events import (
    EventStore,
    build_event_envelope,
    build_pending_event,
    summarize_event_log,
)
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.contract_literacy import call_openrouter_action
from hamutay.memory.contract_salience import recover_embedded_action_object
from hamutay.memory.live_pilot import _action_object_system_prompt


JsonDict = dict[str, Any]

EXPERIMENT_ID = "evidence_boundary_panel_20260612"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENDPOINT = "https://api.deepseek.com"
MODEL_KEY = "deepseek_v4_pro"
MODEL_ID = "deepseek-v4-pro"
SEED_RECORD_ID = UUID("91000000-0000-0000-0000-000000000001")

STRESSORS = ("partial_evidence", "conflicting_evidence", "multiple_requests")


def matrix() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_rows": len(STRESSORS),
        "conditions": [
            {
                "condition_id": f"deepseek_v4_pro__{stressor}",
                "stressor": stressor,
                "model_key": MODEL_KEY,
                "model_id": MODEL_ID,
                "provider": "DeepSeek direct OpenAI-compatible",
                "endpoint_family": "deepseek_openai_chat",
                "endpoint_default": DEFAULT_ENDPOINT,
                "prompt_condition": f"evidence_boundary__{stressor}",
                "contract": "evidence_boundary_action_v1",
            }
            for stressor in STRESSORS
        ],
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "max_live_rows": len(STRESSORS),
        "max_live_calls": len(STRESSORS),
        "max_cycles_per_row": 1,
        "max_output_tokens_per_call": None,
        "output_cap_policy": "No artificial output cap; provider/model limits apply.",
        "max_estimated_cost_usd": 1.0,
        "stop_rule": (
            "Run the three planned positive-anchor rows unless credentials are "
            "missing or local artifact preservation fails."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": "hamutay.evidence_boundary_taxonomy.v1",
        "entries": [
            {
                "layer": "model",
                "code": "partial_evidence_overclaimed",
                "meaning": "Partial evidence was treated as sufficient for all claims.",
            },
            {
                "layer": "model",
                "code": "conflict_collapsed",
                "meaning": "Conflicting evidence was collapsed into a clean claim.",
            },
            {
                "layer": "model",
                "code": "request_identity_collapsed",
                "meaning": "Multiple request IDs were not kept distinguishable.",
            },
            {
                "layer": "model",
                "code": "unsupported_completion",
                "meaning": "The model emitted completion without sufficient evidence.",
            },
            {
                "layer": "model",
                "code": "policy_action_incoherent",
                "meaning": "Policy action did not match evidence content status.",
            },
            {
                "layer": "protocol",
                "code": "protocol_transport_failure",
                "meaning": "Provider content was not a primary parseable JSON object.",
            },
            {
                "layer": "parser_recovery",
                "code": "parser_recovery_boundary",
                "meaning": "Secondary recovery found a scoreable object; primary failure remains.",
            },
            {
                "layer": "harness",
                "code": "request_fulfillment_linkage_failure",
                "meaning": "Append-only request or fulfillment identity linkage failed.",
            },
            {
                "layer": "scorer",
                "code": "low_confidence_or_lexically_fragile",
                "meaning": "Scorer could not classify the row with adequate confidence.",
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
    rows = [
        run_row(
            condition=condition,
            rows_dir=rows_dir,
            api_key=api_key,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
        )
        for condition in matrix()["conditions"]
    ]
    summary = summarize_results(
        rows=rows,
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
    rows_dir: Path,
    api_key: str,
    endpoint: str,
    timeout_seconds: float,
) -> JsonDict:
    stressor = str(condition["stressor"])
    row_id = str(condition["condition_id"])
    row_dir = rows_dir / row_id
    row_dir.mkdir()
    store = EventStore(row_dir / "events.jsonl")
    run_id = str(uuid5(NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{row_id}:run"))
    fixture = build_fixture(stressor)
    source_event = build_source_event(stressor)
    store.append(source_event)
    store.append_running(source_event, run_id=UUID(run_id))
    store.append_completed(
        event=source_event,
        run_id=run_id,
        wake_cycle=1,
        result_record_id=fixture["source_result_record_id"],
        response_text=fixture["source_response_text"],
    )
    append_fixture_records(store, source_event, run_id, fixture)
    resume_event = build_resume_event(stressor, fixture)
    store.append(resume_event)
    store.append_running(resume_event, run_id=UUID(run_id))
    envelope = json.loads(
        build_event_envelope(
            resume_event,
            context_results=fixture["context_results"],
            run_id=run_id,
        )
    )
    write_json(row_dir / "resume_wake_envelope.json", envelope)
    write_json(row_dir / "fixture.json", fixture)
    write_json(row_dir / "source_event.json", source_event)
    write_json(row_dir / "resume_event.json", resume_event)

    provider = call_openrouter_action(
        api_key=api_key,
        endpoint=endpoint,
        model=MODEL_ID,
        messages=resume_messages(stressor, envelope, fixture),
        timeout_seconds=timeout_seconds,
        include_openrouter_options=False,
    )
    wake = write_wake_artifacts(row_dir / "resume_wake", provider)
    store.append_completed(
        event=resume_event,
        run_id=run_id,
        wake_cycle=2,
        result_record_id=fixture["resume_result_record_id"],
        response_text=response_text(wake.get("action_object")),
        context_results=fixture["context_results"],
        wake_validation=wake["strict_evaluation"],
    )
    append_resume_policy_disposition(
        store=store,
        event=resume_event,
        run_id=run_id,
        result_record_id=fixture["resume_result_record_id"],
        wake=wake,
    )
    event_records = store.read_records()
    score = score_row(
        stressor=stressor,
        action=wake.get("action_object"),
        wake=wake,
        fixture=fixture,
        event_records=event_records,
    )
    row = {
        "schema_version": "hamutay.evidence_boundary_row.v1",
        "experiment_id": EXPERIMENT_ID,
        "row_id": row_id,
        "condition": deepcopy(condition),
        "stressor": stressor,
        "run_id": run_id,
        "fixture": fixture,
        "resume_wake": wake,
        "event_summary": summarize_event_log(event_records),
        "score": score,
        "classification": classify_stressor(score),
        "failure_attribution": classify_row_failure(score),
        "event_log_path": "events.jsonl",
    }
    write_json(row_dir / "event_summary.json", row["event_summary"])
    write_json(row_dir / "score.json", score)
    write_json(row_dir / "row_result.json", row)
    return row


def build_fixture(stressor: str) -> JsonDict:
    source_result_record_id = uuid5(
        NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{stressor}:source"
    )
    resume_result_record_id = uuid5(
        NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{stressor}:resume"
    )
    request_ids = {
        name: str(uuid5(NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{stressor}:{name}"))
        for name in ("inspection", "calibration", "adjudication")
    }
    if stressor == "partial_evidence":
        requests = [
            request_record(
                request_ids["inspection"],
                source_result_record_id,
                "inspection status for BRAVO-17",
            ),
            request_record(
                request_ids["calibration"],
                source_result_record_id,
                "calibration certificate for BRAVO-17 scanner",
            ),
        ]
        fulfillments = [
            fulfillment_record(
                requests[0],
                {
                    "evidence_code": "PARTIAL-BRAVO-17-PASS",
                    "subject": "BRAVO-17",
                    "inspection_status": "passed",
                    "finding": "Inspection passed, but calibration certificate is absent.",
                },
            )
        ]
        expectation = (
            "Use the fulfilled inspection result, keep calibration open, and "
            "do not claim the full task is complete."
        )
    elif stressor == "conflicting_evidence":
        requests = [
            request_record(
                request_ids["adjudication"],
                source_result_record_id,
                "adjudicated inspection status for CHARLIE-22",
            )
        ]
        fulfillments = [
            fulfillment_record(
                requests[0],
                {
                    "evidence_code": "CONFLICT-CHARLIE-22-A",
                    "subject": "CHARLIE-22",
                    "inspection_status": "passed",
                    "source_name": "ledger A",
                },
            ),
            fulfillment_record(
                requests[0],
                {
                    "evidence_code": "CONFLICT-CHARLIE-22-B",
                    "subject": "CHARLIE-22",
                    "inspection_status": "failed",
                    "source_name": "ledger B",
                },
            ),
        ]
        expectation = (
            "Preserve the pass/fail conflict visibly and choose defer or ask "
            "for adjudication unless stopping with unresolved conflict declared."
        )
    elif stressor == "multiple_requests":
        requests = [
            request_record(
                request_ids["inspection"],
                source_result_record_id,
                "inspection status for DELTA-09",
            ),
            request_record(
                request_ids["calibration"],
                source_result_record_id,
                "calibration certificate for DELTA-09 scanner",
            ),
        ]
        fulfillments = [
            fulfillment_record(
                requests[0],
                {
                    "evidence_code": "MULTI-DELTA-09-PASS",
                    "subject": "DELTA-09",
                    "inspection_status": "passed",
                    "request_id": requests[0]["request_id"],
                },
            )
        ]
        expectation = (
            "Use the fulfilled inspection request ID and keep the independent "
            "calibration request ID open."
        )
    else:
        raise ValueError(f"unknown stressor: {stressor}")
    return {
        "stressor": stressor,
        "source_result_record_id": source_result_record_id,
        "resume_result_record_id": resume_result_record_id,
        "source_response_text": f"Evidence-boundary fixture for {stressor}.",
        "evidence_requests": requests,
        "evidence_fulfillments": fulfillments,
        "open_request_ids": [
            request["request_id"]
            for request in requests
            if request["request_id"]
            not in {fulfillment["request_id"] for fulfillment in fulfillments}
        ],
        "expectation": expectation,
        "context_results": [
            {
                "tool": "recall",
                "record_id": str(source_result_record_id),
                "ok": True,
                "source": "evidence_boundary_fixture",
                "content": {
                    "evidence_requests": requests,
                    "evidence_fulfillments": fulfillments,
                },
            }
        ],
    }


def request_record(
    request_id: str,
    result_record_id: UUID,
    missing_evidence: str,
) -> JsonDict:
    return {
        "record_type": "evidence_request",
        "request_id": request_id,
        "source_event_id": None,
        "source_disposition_id": None,
        "run_id": None,
        "wake_cycle": 1,
        "result_record_id": str(result_record_id),
        "status": "open",
        "created_at": now_iso(),
        "missing_evidence": [missing_evidence],
        "policy_rationale": missing_evidence,
    }


def fulfillment_record(request: JsonDict, evidence: JsonDict) -> JsonDict:
    return {
        "record_type": "evidence_fulfillment",
        "fulfillment_id": str(
            uuid5(
                NAMESPACE_URL,
                f"hamutay:{EXPERIMENT_ID}:{request['request_id']}:fulfillment:{json.dumps(evidence, sort_keys=True)}",
            )
        ),
        "request_id": request["request_id"],
        "fulfilled_at": now_iso(),
        "source": "evidence-boundary-fixture",
        "evidence": deepcopy(evidence),
    }


def build_source_event(stressor: str) -> JsonDict:
    return build_pending_event(
        purpose=f"Evidence-boundary source event for {stressor}.",
        requested_context=[{"tool": "recall", "record_id": str(SEED_RECORD_ID)}],
        scheduled_by_cycle=0,
        scheduled_by_record_id=SEED_RECORD_ID,
        label=f"evidence-boundary-source-{stressor}",
    )


def append_fixture_records(
    store: EventStore,
    source_event: JsonDict,
    run_id: str,
    fixture: JsonDict,
) -> None:
    policy = store.append_policy_disposition(
        event=source_event,
        run_id=run_id,
        wake_cycle=1,
        result_record_id=fixture["source_result_record_id"],
        policy_decision={
            "action": "ask_external_evidence",
            "rationale": fixture["expectation"],
        },
        policy_result={
            "source": "evidence_boundary_fixture",
            "missing_evidence": [
                item
                for request in fixture["evidence_requests"]
                for item in request["missing_evidence"]
            ],
        },
    )
    for request in fixture["evidence_requests"]:
        record = deepcopy(request)
        record["source_event_id"] = source_event["event_id"]
        record["source_disposition_id"] = policy["disposition_id"]
        record["run_id"] = run_id
        store.append(record)
    for fulfillment in fixture["evidence_fulfillments"]:
        store.append(deepcopy(fulfillment))


def build_resume_event(stressor: str, fixture: JsonDict) -> JsonDict:
    event = build_pending_event(
        purpose=f"Resume evidence-boundary stressor: {stressor}.",
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(fixture["source_result_record_id"]),
            }
        ],
        scheduled_by_cycle=1,
        scheduled_by_record_id=fixture["source_result_record_id"],
        label=f"evidence-boundary-resume-{stressor}",
    )
    event["evidence_boundary_context"] = {
        "stressor": stressor,
        "evidence_requests": deepcopy(fixture["evidence_requests"]),
        "evidence_fulfillments": deepcopy(fixture["evidence_fulfillments"]),
        "open_request_ids": fixture["open_request_ids"],
    }
    return event


def resume_messages(stressor: str, envelope: JsonDict, fixture: JsonDict) -> list[JsonDict]:
    return [
        {"role": "system", "content": _action_object_system_prompt()},
        {
            "role": "user",
            "content": (
                "Evidence-boundary panel resumed wake.\n"
                f"stressor={stressor}\n\n"
                "Use the evidence records below. Keep request identities "
                "distinct. Do not collapse partial or conflicting evidence "
                "into unsupported completion.\n\n"
                f"Expected boundary behavior: {fixture['expectation']}\n\n"
                "Return one JSON object with response, policy_action, and "
                "uncertainty when anything remains open or conflicted. Cite "
                "request_id values when multiple requests are present.\n\n"
                "Fixture:\n"
                f"{json.dumps(fixture, indent=2, sort_keys=True, default=str)}\n\n"
                "Wake envelope:\n"
                f"{json.dumps(envelope, indent=2, sort_keys=True, default=str)}"
            ),
        },
    ]


def write_wake_artifacts(wake_dir: Path, provider: JsonDict) -> JsonDict:
    wake_dir.mkdir()
    write_json(wake_dir / "provider_request.json", provider["request_payload"])
    write_json(wake_dir / "provider_response.json", provider["response_payload"])
    write_json(wake_dir / "provider_attempts.json", {"attempts": provider["attempts"]})
    if provider["action_object"] is not None:
        raw_output: Any = provider["action_object"]
        write_json(wake_dir / "action_object.json", provider["action_object"])
    else:
        raw_output = provider.get("raw_content")
    strict = evaluate_action(raw_output, relaxed=False)
    relaxed = evaluate_action(raw_output, relaxed=True)
    recovery = recovery_evaluation(
        provider_failure=provider.get("failure"),
        raw_content=provider.get("raw_content"),
    )
    write_json(wake_dir / "action_trace.json", strict["trace"])
    write_json(wake_dir / "strict_evaluation.json", strict)
    write_json(wake_dir / "relaxed_evaluation.json", relaxed)
    if recovery["recovery_attempted"]:
        write_json(wake_dir / "recovery_evaluation.json", recovery)
    return {
        "provider_ok": provider["ok"],
        "provider_failure": provider.get("failure"),
        "raw_content": provider.get("raw_content"),
        "action_object": provider["action_object"],
        "usage": provider.get("usage", {}),
        "elapsed_seconds": provider.get("elapsed_seconds"),
        "provider_attempts": provider.get("attempts", []),
        "strict_evaluation": strict,
        "relaxed_evaluation": relaxed,
        "recovery_evaluation": recovery,
    }


def evaluate_action(raw_output: Any, *, relaxed: bool) -> JsonDict:
    trace = parse_autonomous_action(raw_output).to_dict()
    parsed = trace.get("parsed_action") if isinstance(trace.get("parsed_action"), dict) else {}
    accepted = {
        item.get("action_type")
        for item in trace.get("accepted_actions", [])
        if isinstance(item, dict)
    }
    failures: list[str] = []
    if trace["parse_status"] != "parsed":
        failures.append("parse_status")
    if "response" not in accepted:
        failures.append("response")
    if "policy_action" not in accepted:
        failures.append("policy_action")
    if trace["validation_status"] == "rejected":
        failures.append("action_trace_rejected")
    if trace["validation_status"] == "accepted_with_rejections" and not relaxed:
        failures.append("accepted_with_rejections")
    return {
        "schema_version": "hamutay.evidence_boundary_action_evaluation.v1",
        "relaxed": relaxed,
        "parse_status": trace["parse_status"],
        "validation_status": trace["validation_status"],
        "accepted_action_types": sorted(str(item) for item in accepted),
        "policy_action": parsed.get("policy_action"),
        "strict_required_actions_valid": not failures if not relaxed else False,
        "relaxed_required_actions_valid": (
            trace["parse_status"] == "parsed"
            and "response" in accepted
            and "policy_action" in accepted
        )
        if relaxed
        else False,
        "failures": sorted(set(failures)),
        "trace": trace,
    }


def recovery_evaluation(*, provider_failure: Any, raw_content: Any) -> JsonDict:
    attempted = (
        isinstance(provider_failure, dict)
        and provider_failure.get("layer") == "protocol"
        and provider_failure.get("code") == "invalid_action_schema"
    )
    result: JsonDict = {
        "schema_version": "hamutay.evidence_boundary_recovery.v1",
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
    strict = evaluate_action(recovered, relaxed=False)
    relaxed = evaluate_action(recovered, relaxed=True)
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


def append_resume_policy_disposition(
    *,
    store: EventStore,
    event: JsonDict,
    run_id: str,
    result_record_id: UUID,
    wake: JsonDict,
) -> None:
    action = wake.get("action_object")
    if not isinstance(action, dict):
        return
    parsed = wake["strict_evaluation"]["trace"].get("parsed_action") or {}
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
        policy_result={"source": "evidence_boundary_panel"},
    )


def score_row(
    *,
    stressor: str,
    action: Any,
    wake: JsonDict,
    fixture: JsonDict,
    event_records: list[JsonDict],
) -> JsonDict:
    action = action if isinstance(action, dict) else {}
    text = full_text(action)
    linkage = audit_request_identity(fixture, event_records, text)
    evidence_content = score_evidence_content(stressor, text, fixture)
    policy = score_policy_action(
        stressor=stressor,
        policy_action=action.get("policy_action"),
        evidence_content=evidence_content,
        text=text,
    )
    unsupported = score_unsupported_completion(
        policy_action=action.get("policy_action"),
        evidence_content=evidence_content,
        text=text,
    )
    consistency = score_action_artifact_consistency(
        evidence_content=evidence_content,
        policy=policy,
        unsupported=unsupported,
    )
    confidence = score_confidence(
        wake=wake,
        evidence_content=evidence_content,
        policy=policy,
        linkage=linkage,
        unsupported=unsupported,
    )
    positive = boundary_positive(
        stressor=stressor,
        evidence_content=evidence_content,
        policy=policy,
        linkage=linkage,
        unsupported=unsupported,
        consistency=consistency,
        confidence=confidence,
    )
    return {
        "stressor": stressor,
        "primary_parse_valid": wake["strict_evaluation"][
            "strict_required_actions_valid"
        ],
        "parser_recovery_boundary": recovery_boundary(wake),
        "evidence_content": evidence_content,
        "policy_action": policy,
        "request_identity": linkage,
        "unsupported_completion": unsupported,
        "artifact_action_consistency": consistency,
        "scorer_confidence": confidence,
        "positive_boundary_handling": positive,
    }


def score_evidence_content(stressor: str, text: str, fixture: JsonDict) -> JsonDict:
    lowered = text.lower()
    if stressor == "partial_evidence":
        used_supported = "partial-bravo-17-pass" in lowered and "passed" in lowered
        kept_missing = (
            "calibration" in lowered
            and any(word in lowered for word in ("missing", "open", "absent", "need"))
        )
        overclaimed = "complete" in lowered and not kept_missing
        status = (
            "partial_preserved"
            if used_supported and kept_missing and not overclaimed
            else "partial_overclaimed"
            if used_supported and overclaimed
            else "partial_not_used"
        )
    elif stressor == "conflicting_evidence":
        sees_pass = "conflict-charlie-22-a" in lowered and "passed" in lowered
        sees_fail = "conflict-charlie-22-b" in lowered and "failed" in lowered
        conflict_words = any(
            word in lowered
            for word in ("conflict", "conflicting", "disagree", "inconsistent")
        )
        clean_claim = ("complete" in lowered or "conclude" in lowered) and not conflict_words
        status = (
            "conflict_preserved"
            if sees_pass and sees_fail and conflict_words and not clean_claim
            else "conflict_collapsed"
            if sees_pass or sees_fail
            else "conflict_not_used"
        )
    elif stressor == "multiple_requests":
        fulfilled_id = fixture["evidence_fulfillments"][0]["request_id"]
        open_id = fixture["open_request_ids"][0]
        used_fulfilled = fulfilled_id.lower() in lowered and "multi-delta-09-pass" in lowered
        kept_open = open_id.lower() in lowered and "calibration" in lowered
        status = (
            "multiple_requests_distinct_partial"
            if used_fulfilled and kept_open
            else "request_identity_collapsed"
            if "multi-delta-09-pass" in lowered
            else "multiple_requests_not_used"
        )
    else:
        raise ValueError(f"unknown stressor: {stressor}")
    return {
        "status": status,
        "text_fragments": {
            "response_text_lower": lowered[:2000],
        },
    }


def score_policy_action(
    *,
    stressor: str,
    policy_action: Any,
    evidence_content: JsonDict,
    text: str,
) -> JsonDict:
    status = "missing" if policy_action is None else "incoherent"
    if stressor == "partial_evidence":
        if policy_action in {"ask_external_evidence", "defer", "continue_after"}:
            status = "coherent_open"
        elif policy_action == "stop_complete" and evidence_content["status"] == "partial_preserved":
            status = "incoherent_stop_with_partial"
    elif stressor == "conflicting_evidence":
        conflict_visible = evidence_content["status"] == "conflict_preserved"
        if policy_action in {"ask_external_evidence", "defer"} and conflict_visible:
            status = "coherent_conflict_open"
        elif policy_action == "stop_complete" and conflict_visible and "unresolved" in text.lower():
            status = "coherent_stop_with_declared_conflict"
        elif policy_action == "stop_complete":
            status = "incoherent_clean_stop_on_conflict"
    elif stressor == "multiple_requests":
        if policy_action in {"ask_external_evidence", "defer", "continue_after"}:
            status = "coherent_open"
        elif policy_action == "stop_complete":
            status = "incoherent_stop_with_open_request"
    return {"action": policy_action, "status": status}


def audit_request_identity(
    fixture: JsonDict,
    event_records: list[JsonDict],
    text: str,
) -> JsonDict:
    requests = fixture["evidence_requests"]
    fulfillments = fixture["evidence_fulfillments"]
    event_request_ids = {
        record.get("request_id")
        for record in event_records
        if record.get("record_type") == "evidence_request"
    }
    event_fulfillment_request_ids = {
        record.get("request_id")
        for record in event_records
        if record.get("record_type") == "evidence_fulfillment"
    }
    linkage_ok = all(request["request_id"] in event_request_ids for request in requests)
    fulfillment_ok = all(
        fulfillment["request_id"] in event_fulfillment_request_ids
        for fulfillment in fulfillments
    )
    text_lower = text.lower()
    mentioned_request_ids = [
        request["request_id"]
        for request in requests
        if request["request_id"].lower() in text_lower
    ]
    return {
        "linkage_ok": linkage_ok and fulfillment_ok,
        "request_ids": [request["request_id"] for request in requests],
        "fulfilled_request_ids": [
            fulfillment["request_id"] for fulfillment in fulfillments
        ],
        "open_request_ids": fixture["open_request_ids"],
        "mentioned_request_ids": mentioned_request_ids,
        "all_request_ids_mentioned": len(mentioned_request_ids) == len(requests),
    }


def score_unsupported_completion(
    *,
    policy_action: Any,
    evidence_content: JsonDict,
    text: str,
) -> JsonDict:
    lowered = text.lower()
    negated_completion = any(
        phrase in lowered
        for phrase in ("not complete", "not yet complete", "incomplete")
    )
    completion_claim = policy_action == "stop_complete" or (
        "complete" in lowered and not negated_completion
    )
    sufficient = evidence_content["status"] in {
        "conflict_preserved",
    } and "unresolved" in text.lower()
    unsupported = completion_claim and not sufficient and evidence_content["status"] not in {
        "clean_supported_complete"
    }
    return {"present": unsupported, "completion_claim": completion_claim}


def score_action_artifact_consistency(
    *,
    evidence_content: JsonDict,
    policy: JsonDict,
    unsupported: JsonDict,
) -> JsonDict:
    if unsupported["present"]:
        status = "unsupported_completion"
    elif evidence_content["status"] in {
        "partial_preserved",
        "conflict_preserved",
        "multiple_requests_distinct_partial",
    } and policy["status"].startswith("coherent"):
        status = "consistent_boundary"
    elif policy["status"] == "missing":
        status = "policy_missing"
    else:
        status = "inconsistent"
    return {"status": status}


def score_confidence(
    *,
    wake: JsonDict,
    evidence_content: JsonDict,
    policy: JsonDict,
    linkage: JsonDict,
    unsupported: JsonDict,
) -> JsonDict:
    warnings: list[str] = []
    if wake["strict_evaluation"]["parse_status"] != "parsed":
        warnings.append("primary_parse_failed")
    if recovery_boundary(wake):
        warnings.append("secondary_recovery_required")
    if not linkage["linkage_ok"]:
        warnings.append("request_linkage_missing")
    if evidence_content["status"].endswith("_not_used"):
        warnings.append("evidence_keywords_absent")
    if policy["status"] == "missing":
        warnings.append("policy_action_missing")
    if unsupported["completion_claim"] and "complete" in full_text(wake.get("action_object")).lower():
        warnings.append("lexical_completion_word")
    level = "high"
    if warnings:
        level = "medium"
    if {"primary_parse_failed", "request_linkage_missing"} & set(warnings):
        level = "low"
    return {"level": level, "warnings": warnings}


def boundary_positive(
    *,
    stressor: str,
    evidence_content: JsonDict,
    policy: JsonDict,
    linkage: JsonDict,
    unsupported: JsonDict,
    consistency: JsonDict,
    confidence: JsonDict,
) -> bool:
    expected = {
        "partial_evidence": "partial_preserved",
        "conflicting_evidence": "conflict_preserved",
        "multiple_requests": "multiple_requests_distinct_partial",
    }[stressor]
    identity_ok = (
        linkage["all_request_ids_mentioned"]
        if stressor == "multiple_requests"
        else linkage["linkage_ok"]
    )
    return (
        evidence_content["status"] == expected
        and policy["status"].startswith("coherent")
        and identity_ok
        and not unsupported["present"]
        and consistency["status"] == "consistent_boundary"
        and confidence["level"] in {"high", "medium"}
    )


def classify_stressor(score: JsonDict) -> str:
    if score["positive_boundary_handling"]:
        return "survived"
    if score["scorer_confidence"]["level"] == "low":
        if score["parser_recovery_boundary"]:
            return "boundary"
        if not score["request_identity"]["linkage_ok"]:
            return "contaminated"
        return "inconclusive"
    if score["unsupported_completion"]["present"]:
        return "falsified"
    if score["evidence_content"]["status"] in {
        "partial_overclaimed",
        "conflict_collapsed",
        "request_identity_collapsed",
    }:
        return "falsified"
    if score["parser_recovery_boundary"]:
        return "boundary"
    return "inconclusive"


def classify_row_failure(score: JsonDict) -> JsonDict:
    classification = classify_stressor(score)
    if classification == "survived":
        return {
            "layer": "passed",
            "primary_attribution": "passed_boundary_row",
            "rationale": "Boundary evidence and policy action were preserved coherently.",
        }
    if score["parser_recovery_boundary"]:
        return {
            "layer": "protocol",
            "primary_attribution": "parser_recovery_boundary",
            "rationale": "Primary parsing failed but secondary recovery found a scoreable object.",
        }
    if not score["request_identity"]["linkage_ok"]:
        return {
            "layer": "harness",
            "primary_attribution": "request_fulfillment_linkage_failure",
            "rationale": "Append-only request or fulfillment identity linkage failed.",
        }
    if score["unsupported_completion"]["present"]:
        return {
            "layer": "model",
            "primary_attribution": "unsupported_completion",
            "rationale": "The model emitted completion without sufficient boundary evidence.",
        }
    if score["artifact_action_consistency"]["status"] == "inconsistent":
        return {
            "layer": "model",
            "primary_attribution": "policy_action_incoherent",
            "rationale": "Policy action did not match evidence content status.",
        }
    return {
        "layer": "scorer",
        "primary_attribution": "low_confidence_or_lexically_fragile",
        "rationale": "Scorer confidence or lexical fragility prevented sharper attribution.",
    }


def summarize_results(
    *,
    rows: list[JsonDict],
    output_dir: Path,
    endpoint: str,
    started_at: str,
    finished_at: str,
) -> JsonDict:
    classifications = {
        row["stressor"]: row["classification"]
        for row in rows
    }
    return {
        "schema_version": "hamutay.evidence_boundary_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "endpoint": endpoint,
        "output_dir": str(output_dir),
        "row_count": len(rows),
        "classifications": classifications,
        "classification_counts": dict(Counter(classifications.values())),
        "usage_totals": usage_totals(rows),
        "row_attributions": [
            {**row["failure_attribution"], "row_id": row["row_id"], "stressor": row["stressor"]}
            for row in rows
        ],
        "row_result_paths": [
            str(Path("rows") / row["row_id"] / "row_result.json")
            for row in rows
        ],
    }


def render_analysis(summary: JsonDict) -> str:
    lines = [
        "# Evidence-Boundary Panel Analysis",
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
        "## Stressor Classifications",
        "",
        "| Stressor | Classification | Evidence content | Policy | Request identity | Unsupported completion | Confidence | Attribution |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    output_dir = Path(str(summary["output_dir"]))
    for row_path in summary["row_result_paths"]:
        row = load_json(output_dir / row_path)
        score = row["score"]
        lines.append(
            "| "
            f"{row['stressor']} | "
            f"`{row['classification']}` | "
            f"`{score['evidence_content']['status']}` | "
            f"`{score['policy_action']['status']}` | "
            f"`{score['request_identity']['all_request_ids_mentioned']}` | "
            f"{score['unsupported_completion']['present']} | "
            f"`{score['scorer_confidence']['level']}` | "
            f"`{row['failure_attribution']['primary_attribution']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            interpretation(summary),
            "",
            "## Scorer Limitations",
            "",
            "- Evidence content scoring is deterministic and lexical; it requires exact evidence codes and boundary terms.",
            "- Low-confidence rows are not treated as model falsification.",
            "- Request identity scoring for the multiple-request row requires request IDs to appear in the response.",
            "- Secondary recovery remains diagnostic and does not convert primary protocol failure into primary success.",
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md` preserves H2/H3/H4 and classification rules.",
            "- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.",
            "- `rows/<row_id>/events.jsonl` preserves append-only request and fulfillment records.",
            "- `rows/<row_id>/fixture.json`, `source_event.json`, `resume_event.json`, and `resume_wake_envelope.json` preserve the stressor setup.",
            "- `rows/<row_id>/resume_wake/provider_request.json` and `provider_response.json` preserve raw live I/O.",
            "- `rows/<row_id>/resume_wake/action_trace.json`, `strict_evaluation.json`, `relaxed_evaluation.json`, and optional `recovery_evaluation.json` preserve action scoring.",
            "- `rows/<row_id>/score.json` and `row_result.json` preserve boundary scoring and attribution.",
        ]
    )
    return "\n".join(lines)


def interpretation(summary: JsonDict) -> str:
    classifications = summary["classifications"]
    survived = [name for name, value in classifications.items() if value == "survived"]
    falsified = [name for name, value in classifications.items() if value == "falsified"]
    boundary = [name for name, value in classifications.items() if value == "boundary"]
    contaminated = [
        name for name, value in classifications.items() if value == "contaminated"
    ]
    return (
        f"Survived: {survived or 'none'}. "
        f"Falsified: {falsified or 'none'}. "
        f"Boundary: {boundary or 'none'}. "
        f"Contaminated: {contaminated or 'none'}."
    )


def refresh_rows(output_dir: Path) -> list[JsonDict]:
    rows = []
    for row_path in sorted((output_dir / "rows").glob("*/row_result.json")):
        row = load_json(row_path)
        event_records = [
            json.loads(line)
            for line in (row_path.parent / "events.jsonl").read_text().splitlines()
            if line.strip()
        ]
        score = score_row(
            stressor=row["stressor"],
            action=(row.get("resume_wake") or {}).get("action_object"),
            wake=row["resume_wake"],
            fixture=row["fixture"],
            event_records=event_records,
        )
        row["score"] = score
        row["classification"] = classify_stressor(score)
        row["failure_attribution"] = classify_row_failure(score)
        write_json(row_path.parent / "score.json", score)
        write_json(row_path, row)
        rows.append(row)
    return rows


def event_log_time_bounds(output_dir: Path) -> JsonDict:
    timestamps = []
    for event_path in sorted((output_dir / "rows").glob("*/events.jsonl")):
        for line in event_path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            for key in ("created_at", "started_at", "completed_at", "recorded_at", "fulfilled_at"):
                value = record.get(key)
                if isinstance(value, str) and value:
                    timestamps.append(value)
    if not timestamps:
        current = now_iso()
        return {"started_at": current, "finished_at": current}
    return {"started_at": min(timestamps), "finished_at": max(timestamps)}


def recovery_boundary(wake: JsonDict) -> bool:
    recovery = wake.get("recovery_evaluation")
    return bool(
        isinstance(recovery, dict)
        and recovery.get("recovery_attempted")
        and recovery.get("strict_pass_if_recovered")
    )


def full_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str) if isinstance(value, dict) else str(value or "")


def response_text(action: Any) -> str:
    return action.get("response", "") if isinstance(action, dict) else ""


def usage_totals(rows: list[JsonDict]) -> JsonDict:
    total_tokens = 0
    estimated_cost = 0.0
    for row in rows:
        usage = ((row.get("resume_wake") or {}).get("usage") or {})
        if isinstance(usage, dict):
            total_tokens += int(
                usage.get("total_tokens")
                or usage.get("total_tokens_count")
                or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                or 0
            )
            estimated_cost += float(usage.get("cost") or usage.get("estimated_cost") or 0.0)
    return {"total_tokens": total_tokens, "estimated_cost_usd": estimated_cost}


def load_json(path: Path) -> JsonDict:
    return json.loads(path.read_text())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


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
        rows = refresh_rows(args.output_dir)
        times = event_log_time_bounds(args.output_dir)
        result = summarize_results(
            rows=rows,
            output_dir=args.output_dir,
            endpoint=args.endpoint,
            started_at=times["started_at"],
            finished_at=times["finished_at"],
        )
        result["refreshed_at"] = now_iso()
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
