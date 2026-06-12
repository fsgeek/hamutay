"""Run the DeepSeek direct-endpoint transport falsification experiment."""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from hamutay.memory.contract_literacy import (
    call_openrouter_action,
    evaluate_cycle1_action_object,
    failure_taxonomy as literacy_failure_taxonomy,
    prompt_variants as literacy_prompt_variants,
)
from hamutay.memory.contract_salience import secondary_recovery_evaluation
from hamutay.memory.live_pilot import _seed_messages


JsonDict = dict[str, Any]

EXPERIMENT_ID = "deepseek_transport_falsification_20260611"
PARENT_EXPERIMENT_ID = "action_object_contract_salience_cross_model_20260611"
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "live_direct_deepseek_20260611"
DEFAULT_ENDPOINT = "https://api.deepseek.com"
MODEL_KEY = "deepseek_v4_pro"
MODEL_ID = "deepseek-v4-pro"
REPETITIONS_PER_CONDITION = 3
BASE_EVALUATOR_CONDITION_ID = "B_example_prompt_strict_contract"

TRANSPORT_ADDENDUM = (
    "Transport constraint: return exactly one JSON object in visible message "
    "content. Do not wrap it in markdown fences. Do not duplicate the object. "
    "Do not put the answer only in reasoning content. Do not emit prose before "
    "or after the object. The first visible character must be { and the last "
    "visible character must be }."
)


def matrix() -> JsonDict:
    example_addendum = literacy_prompt_variants()["variants"][
        "original_plus_one_valid_open_item_example"
    ]["addendum"]
    conditions = [
        {
            "condition_id": "deepseek_v4_pro__example_strict_current",
            "model_key": MODEL_KEY,
            "model_id": MODEL_ID,
            "provider": "DeepSeek direct OpenAI-compatible",
            "endpoint_family": "deepseek_openai_chat",
            "endpoint_default": DEFAULT_ENDPOINT,
            "prompt_condition": "example_strict_current",
            "prompt_variant": "original_plus_one_valid_open_item_example",
            "prompt_addendum_application": "system_message_suffix",
            "prompt_addendum": example_addendum,
            "base_evaluator_condition_id": BASE_EVALUATOR_CONDITION_ID,
            "contract": "strict_autonomous_action_v1",
            "acceptance_rule": (
                "primary strict parser requires one accepted open_item and one "
                "accepted schedule_request"
            ),
        },
        {
            "condition_id": "deepseek_v4_pro__example_strict_transport_explicit",
            "model_key": MODEL_KEY,
            "model_id": MODEL_ID,
            "provider": "DeepSeek direct OpenAI-compatible",
            "endpoint_family": "deepseek_openai_chat",
            "endpoint_default": DEFAULT_ENDPOINT,
            "prompt_condition": "example_strict_transport_explicit",
            "prompt_variant": "example_strict_plus_visible_transport_contract",
            "prompt_addendum_application": "system_message_suffix",
            "prompt_addendum": f"{example_addendum}\n\n{TRANSPORT_ADDENDUM}",
            "base_evaluator_condition_id": BASE_EVALUATOR_CONDITION_ID,
            "contract": "strict_autonomous_action_v1",
            "acceptance_rule": (
                "primary strict parser requires one accepted open_item and one "
                "accepted schedule_request"
            ),
        },
    ]
    return {
        "experiment_id": EXPERIMENT_ID,
        "parent_experiment_id": PARENT_EXPERIMENT_ID,
        "live_calls_per_condition": REPETITIONS_PER_CONDITION,
        "conditions": conditions,
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "max_live_calls": 6,
        "max_calls_per_condition": REPETITIONS_PER_CONDITION,
        "max_cycles_per_call": 1,
        "max_output_tokens_per_call": None,
        "output_cap_policy": (
            "No artificial output cap; provider/model limits still apply."
        ),
        "max_estimated_cost_usd": 1.0,
    }


def write_preregistration_artifacts(output_dir: Path = ROOT_DIR) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }
    for name, payload in artifacts.items():
        _write_json(output_dir / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "output_dir": str(output_dir),
        "artifacts": sorted(artifacts),
        "preregistration": str(output_dir / "PRE_REGISTRATION.md"),
    }


def failure_taxonomy() -> JsonDict:
    taxonomy = literacy_failure_taxonomy()
    taxonomy["experiment_specific_layers"] = {
        "prompt_transport_contract": (
            "transport-explicit condition rescues rows that current example "
            "strict does not"
        ),
        "parser_recovery_boundary": (
            "primary strict fails but secondary recovery finds valid action "
            "objects"
        ),
        "model_contract_boundary": (
            "primary strict and secondary recovery both fail despite provider "
            "content"
        ),
        "provider_substrate_failure": (
            "provider errors prevent model-authored content from being "
            "preserved"
        ),
        "inconclusive": "evidence does not identify a dominant cause",
    }
    return taxonomy


def execute_live(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout_seconds: float = 120.0,
) -> JsonDict:
    if not api_key:
        raise ValueError("api_key is required")
    output_dir.mkdir(parents=True, exist_ok=False)
    rows_dir = output_dir / "rows"
    rows_dir.mkdir()

    for name, payload in {
        "matrix.json": matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        _write_json(output_dir / name, payload)

    row_results: list[JsonDict] = []
    started_at = _now_iso()
    for condition in matrix()["conditions"]:
        for repetition in range(1, REPETITIONS_PER_CONDITION + 1):
            provider = call_openrouter_action(
                api_key=api_key,
                endpoint=endpoint,
                model=MODEL_ID,
                messages=messages_for_condition(condition, repetition=repetition),
                timeout_seconds=timeout_seconds,
                include_openrouter_options=False,
            )
            row_results.append(
                write_evaluated_row(
                    condition=condition,
                    repetition=repetition,
                    rows_dir=rows_dir,
                    provider=provider,
                    endpoint=endpoint,
                )
            )

    summary = summarize_results(
        row_results=row_results,
        output_dir=output_dir,
        endpoint=endpoint,
        started_at=started_at,
        finished_at=_now_iso(),
    )
    _write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary) + "\n")
    return summary


def messages_for_condition(condition: JsonDict, *, repetition: int) -> list[JsonDict]:
    result_record_id = uuid5(
        NAMESPACE_URL,
        f"hamutay:{EXPERIMENT_ID}:{condition['condition_id']}:r{repetition:02d}",
    )
    messages = _seed_messages(result_record_id=result_record_id)
    addendum = condition.get("prompt_addendum", "")
    if isinstance(addendum, str) and addendum:
        messages = deepcopy(messages)
        messages[0]["content"] = (
            f"{messages[0]['content']}\n\nCondition addendum:\n{addendum}"
        )
    return messages


def write_evaluated_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    provider: JsonDict,
    endpoint: str,
) -> JsonDict:
    row_id = f"{condition['condition_id']}__r{repetition:02d}"
    row_dir = rows_dir / row_id
    row_dir.mkdir()
    _write_json(row_dir / "provider_request.json", provider["request_payload"])
    _write_json(row_dir / "provider_response.json", provider["response_payload"])
    _write_json(row_dir / "provider_attempts.json", {"attempts": provider["attempts"]})

    if provider["action_object"] is not None:
        raw_output: Any = provider["action_object"]
        _write_json(row_dir / "action_object.json", provider["action_object"])
    else:
        raw_output = provider.get("raw_content")

    strict_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=str(condition["base_evaluator_condition_id"]),
        relaxed_open_item_contract=False,
    )
    relaxed_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=str(condition["base_evaluator_condition_id"]),
        relaxed_open_item_contract=True,
    )
    row_result = {
        "schema_version": "hamutay.deepseek_transport_falsification_row.v1",
        "experiment_id": EXPERIMENT_ID,
        "parent_experiment_id": PARENT_EXPERIMENT_ID,
        "row_id": row_id,
        "condition_id": condition["condition_id"],
        "model_key": condition["model_key"],
        "model_id": condition["model_id"],
        "prompt_condition": condition["prompt_condition"],
        "repetition": repetition,
        "condition": deepcopy(condition),
        "endpoint": endpoint,
        "endpoint_family": condition["endpoint_family"],
        "provider_ok": provider["ok"],
        "provider_failure": provider.get("failure"),
        "raw_content": provider.get("raw_content"),
        "usage": provider.get("usage", {}),
        "elapsed_seconds": provider.get("elapsed_seconds"),
        "provider_attempts": provider.get("attempts", []),
        "strict_evaluation": strict_evaluation,
        "relaxed_evaluation": relaxed_evaluation,
    }
    recovery_evaluation = secondary_recovery_evaluation(row_result)
    if recovery_evaluation["recovery_attempted"]:
        row_result["recovery_evaluation"] = recovery_evaluation
        _write_json(row_dir / "recovery_evaluation.json", recovery_evaluation)
    row_result["failure_attribution"] = classify_row_failure(row_result)
    _write_json(row_dir / "strict_evaluation.json", strict_evaluation)
    _write_json(row_dir / "relaxed_evaluation.json", relaxed_evaluation)
    _write_json(row_dir / "row_result.json", row_result)
    return row_result


def summarize_results(
    *,
    row_results: list[JsonDict],
    output_dir: Path,
    endpoint: str,
    started_at: str,
    finished_at: str,
) -> JsonDict:
    by_condition: dict[str, JsonDict] = {}
    for row in row_results:
        bucket = by_condition.setdefault(
            str(row["prompt_condition"]),
            {
                "prompt_condition": row["prompt_condition"],
                "rows": 0,
                "primary_scorable_count": 0,
                "strict_pass_count": 0,
                "relaxed_pass_count": 0,
                "strict_fail_relaxed_pass_count": 0,
                "provider_failures": 0,
                "protocol_failures": 0,
                "recovery_attempted_count": 0,
                "recovered_count": 0,
                "strict_pass_if_recovered": 0,
                "relaxed_pass_if_recovered": 0,
            },
        )
        accumulate_condition(bucket, row)

    summary = {
        "schema_version": "hamutay.deepseek_transport_falsification_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "parent_experiment_id": PARENT_EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "endpoint": endpoint,
        "output_dir": str(output_dir),
        "row_count": len(row_results),
        "usage_totals": usage_totals(row_results),
        "failure_totals": failure_totals(row_results),
        "protocol_recovery_totals": protocol_recovery_totals(row_results),
        "by_condition": by_condition,
        "row_failure_attributions": [
            row["failure_attribution"]
            for row in row_results
            if not row["strict_evaluation"]["strict_required_actions_valid"]
        ],
        "attribution": attribute_outcome(by_condition),
        "row_result_paths": [
            str(Path("rows") / str(row["row_id"]) / "row_result.json")
            for row in row_results
        ],
    }
    return summary


def classify_row_failure(row: JsonDict) -> JsonDict:
    strict_pass = bool(row["strict_evaluation"]["strict_required_actions_valid"])
    relaxed_pass = bool(row["relaxed_evaluation"]["relaxed_required_actions_valid"])
    failure = row.get("provider_failure")
    recovery = row.get("recovery_evaluation")
    if strict_pass:
        return {
            "row_id": row["row_id"],
            "prompt_condition": row["prompt_condition"],
            "primary_attribution": "passed_primary_strict",
            "rationale": "Primary strict evaluation accepted the row.",
        }
    if isinstance(failure, dict) and failure.get("layer") == "provider":
        return {
            "row_id": row["row_id"],
            "prompt_condition": row["prompt_condition"],
            "primary_attribution": "provider_substrate_failure",
            "rationale": "Provider error prevented model-authored content from being preserved.",
        }
    if isinstance(failure, dict) and failure.get("layer") == "protocol":
        if isinstance(recovery, dict) and recovery.get("strict_pass_if_recovered"):
            return {
                "row_id": row["row_id"],
                "prompt_condition": row["prompt_condition"],
                "primary_attribution": "parser_recovery_boundary",
                "rationale": (
                    "Primary parser rejected the visible content, but secondary "
                    "recovery found a strict-valid action object."
                ),
            }
        raw = row.get("raw_content")
        if isinstance(raw, str) and not raw.strip():
            return {
                "row_id": row["row_id"],
                "prompt_condition": row["prompt_condition"],
                "primary_attribution": "prompt_transport_contract",
                "rationale": (
                    "Provider returned no visible JSON content even though the "
                    "call completed; this is a visible-channel transport failure."
                ),
            }
        if isinstance(recovery, dict) and recovery.get("recovered"):
            return {
                "row_id": row["row_id"],
                "prompt_condition": row["prompt_condition"],
                "primary_attribution": "prompt_transport_contract",
                "rationale": (
                    "Secondary recovery found only an embedded JSON fragment, "
                    "not a complete strict-valid action object."
                ),
            }
        return {
            "row_id": row["row_id"],
            "prompt_condition": row["prompt_condition"],
            "primary_attribution": "inconclusive",
            "rationale": "Protocol failure did not preserve enough structure for sharper attribution.",
        }
    if not relaxed_pass:
        return {
            "row_id": row["row_id"],
            "prompt_condition": row["prompt_condition"],
            "primary_attribution": "model_contract_boundary",
            "rationale": (
                "The model returned parseable JSON, but it failed the required "
                "action contract under both strict and relaxed scoring."
            ),
        }
    return {
        "row_id": row["row_id"],
        "prompt_condition": row["prompt_condition"],
        "primary_attribution": "model_contract_boundary",
        "rationale": (
            "The model returned parseable JSON with usable partial structure, "
            "but not the strict action-object shape."
        ),
    }


def accumulate_condition(bucket: JsonDict, row: JsonDict) -> None:
    bucket["rows"] += 1
    failure = row.get("provider_failure")
    if isinstance(failure, dict):
        if failure.get("layer") == "provider":
            bucket["provider_failures"] += 1
        elif failure.get("layer") == "protocol":
            bucket["protocol_failures"] += 1
    else:
        bucket["primary_scorable_count"] += 1
    strict_pass = bool(row["strict_evaluation"]["strict_required_actions_valid"])
    relaxed_pass = bool(row["relaxed_evaluation"]["relaxed_required_actions_valid"])
    if strict_pass:
        bucket["strict_pass_count"] += 1
    if relaxed_pass:
        bucket["relaxed_pass_count"] += 1
    if not strict_pass and relaxed_pass:
        bucket["strict_fail_relaxed_pass_count"] += 1
    recovery = row.get("recovery_evaluation")
    if isinstance(recovery, dict) and recovery.get("recovery_attempted"):
        bucket["recovery_attempted_count"] += 1
        if recovery.get("recovered"):
            bucket["recovered_count"] += 1
        if recovery.get("strict_pass_if_recovered"):
            bucket["strict_pass_if_recovered"] += 1
        if recovery.get("relaxed_pass_if_recovered"):
            bucket["relaxed_pass_if_recovered"] += 1


def attribute_outcome(by_condition: dict[str, JsonDict]) -> JsonDict:
    current = by_condition.get("example_strict_current", {})
    transport = by_condition.get("example_strict_transport_explicit", {})
    conditions = [current, transport]
    provider_blocked = any(
        int(condition.get("provider_failures", 0)) >= 2 for condition in conditions
    )
    current_pass = int(current.get("strict_pass_count", 0))
    transport_pass = int(transport.get("strict_pass_count", 0))
    current_recovered = int(current.get("strict_pass_if_recovered", 0))
    transport_recovered = int(transport.get("strict_pass_if_recovered", 0))
    current_unrecovered_protocol = int(current.get("protocol_failures", 0)) - int(
        current.get("recovered_count", 0)
    )
    transport_unrecovered_protocol = int(transport.get("protocol_failures", 0)) - int(
        transport.get("recovered_count", 0)
    )

    if provider_blocked:
        primary = "provider_substrate_failure"
        rationale = (
            "At least one condition had provider failures in two or more rows, "
            "so model-authored content was not preserved well enough to score."
        )
    elif current_pass >= 2 and transport_pass >= 2:
        primary = "no_residual_failure_under_direct_endpoint"
        rationale = (
            "Both current and transport-explicit example prompts passed primary "
            "strict scoring in at least two rows."
        )
    elif transport_pass >= 2 and current_pass < 2:
        primary = "prompt_transport_contract"
        rationale = (
            "The transport-explicit prompt rescued primary strict scoring while "
            "the current example prompt did not."
        )
    elif (
        current_pass < 2
        and transport_pass < 2
        and current_recovered + transport_recovered >= 2
    ):
        primary = "parser_recovery_boundary"
        rationale = (
            "Primary strict scoring failed, but secondary recovery found valid "
            "action objects in multiple rows."
        )
    elif (
        current_pass < 2
        and transport_pass < 2
        and current_unrecovered_protocol + transport_unrecovered_protocol >= 2
    ):
        primary = "model_contract_boundary"
        rationale = (
            "Both prompt conditions failed primary strict scoring and secondary "
            "recovery did not recover valid action objects in multiple rows."
        )
    else:
        primary = "inconclusive"
        rationale = "The observed rows did not isolate one dominant failure cause."

    return {
        "primary_attribution": primary,
        "rationale": rationale,
        "decision_inputs": {
            "current_strict_pass_count": current_pass,
            "transport_strict_pass_count": transport_pass,
            "current_strict_pass_if_recovered": current_recovered,
            "transport_strict_pass_if_recovered": transport_recovered,
            "current_provider_failures": int(current.get("provider_failures", 0)),
            "transport_provider_failures": int(transport.get("provider_failures", 0)),
            "current_unrecovered_protocol_failures": current_unrecovered_protocol,
            "transport_unrecovered_protocol_failures": transport_unrecovered_protocol,
        },
    }


def render_analysis(summary: JsonDict) -> str:
    lines = [
        "# DeepSeek Direct-Endpoint Transport Falsification Analysis",
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
        "## Condition Counts",
        "",
        "| Condition | Rows | Primary scorable | Strict pass | Relaxed pass | Provider failures | Protocol failures | Recovered | Strict pass if recovered |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition, bucket in sorted(summary["by_condition"].items()):
        lines.append(
            "| "
            f"{condition} | "
            f"{bucket['rows']} | "
            f"{bucket['primary_scorable_count']} | "
            f"{bucket['strict_pass_count']} | "
            f"{bucket['relaxed_pass_count']} | "
            f"{bucket['provider_failures']} | "
            f"{bucket['protocol_failures']} | "
            f"{bucket['recovered_count']} | "
            f"{bucket['strict_pass_if_recovered']} |"
        )

    attribution = summary["attribution"]
    lines.extend(
        [
            "",
            "## Attribution",
            "",
            f"- Primary attribution: `{attribution['primary_attribution']}`",
            f"- Rationale: {attribution['rationale']}",
            "",
            "Decision inputs:",
            "",
        ]
    )
    for key, value in sorted(attribution["decision_inputs"].items()):
        lines.append(f"- `{key}`: `{value}`")

    failures = summary["row_failure_attributions"]
    lines.extend(
        [
            "",
            "## Row Failure Attribution",
            "",
            "| Row | Condition | Attribution | Rationale |",
            "| --- | --- | --- | --- |",
        ]
    )
    if failures:
        for failure in failures:
            lines.append(
                "| "
                f"{failure['row_id']} | "
                f"{failure['prompt_condition']} | "
                f"`{failure['primary_attribution']}` | "
                f"{failure['rationale']} |"
            )
    else:
        lines.append("| none | n/a | `passed_primary_strict` | No failed rows. |")

    recovery = summary["protocol_recovery_totals"]
    lines.extend(
        [
            "",
            "## Protocol Recovery Audit",
            "",
            f"- Protocol failures: `{recovery['protocol_failures']}`",
            f"- Recoverable protocol failures: `{recovery['recoverable_protocol_failures']}`",
            f"- Unrecoverable protocol failures: `{recovery['unrecoverable_protocol_failures']}`",
            f"- Strict pass if recovered: `{recovery['strict_pass_if_recovered']}`",
            f"- Relaxed pass if recovered: `{recovery['relaxed_pass_if_recovered']}`",
            f"- Recovery methods: `{recovery['recovery_methods']}`",
            "",
            "## Interpretation",
            "",
            interpretation_for_attribution(attribution["primary_attribution"]),
            "",
            "## Artifact Trail",
            "",
            "- `results.json` contains aggregate machine-readable results.",
            "- `analysis.md` is this analysis artifact.",
            "- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered execution frame.",
            "- `rows/<row_id>/provider_request.json` preserves each request.",
            "- `rows/<row_id>/provider_response.json` preserves each response.",
            "- `rows/<row_id>/provider_attempts.json` preserves retry/attempt telemetry.",
            "- `rows/<row_id>/strict_evaluation.json` preserves strict scoring.",
            "- `rows/<row_id>/relaxed_evaluation.json` preserves relaxed scoring.",
            "- `rows/<row_id>/recovery_evaluation.json` preserves secondary recovery audits when attempted.",
            "- `rows/<row_id>/row_result.json` ties each row together.",
        ]
    )
    return "\n".join(lines)


def interpretation_for_attribution(primary: str) -> str:
    if primary == "provider_substrate_failure":
        return (
            "The experiment did not preserve enough model-authored content to "
            "attribute behavior to DeepSeek. Treat the result as a provider or "
            "substrate failure, not model evidence."
        )
    if primary == "no_residual_failure_under_direct_endpoint":
        return (
            "The residual DeepSeek ambiguity is not present under this direct "
            "endpoint and current example-strict prompt. The direct endpoint is "
            "adequate for the next action-object layer unless later rows reopen "
            "the transport boundary."
        )
    if primary == "prompt_transport_contract":
        return (
            "The model can satisfy the action-object contract when visible "
            "transport constraints are explicit. The next harness prompt should "
            "carry those constraints before live autonomy work."
        )
    if primary == "parser_recovery_boundary":
        return (
            "The model appears to author usable action objects, but the primary "
            "transport/parser boundary rejects them. Production ingestion would "
            "need an explicit recovery policy; strict research scoring should "
            "remain unchanged."
        )
    if primary == "model_contract_boundary":
        return (
            "The residual failure is evidence for a DeepSeek model/contract "
            "boundary under this action-object pattern. Further autonomy work "
            "should not depend on this model/contract pair without additional "
            "training, schema changes, or a different model."
        )
    return "The rows do not isolate a dominant cause."


def refresh_existing(output_dir: Path = DEFAULT_OUTPUT_DIR) -> JsonDict:
    rows_dir = output_dir / "rows"
    if not rows_dir.exists():
        raise FileNotFoundError(rows_dir)
    row_results = []
    for row_path in sorted(rows_dir.glob("*/row_result.json")):
        row = json.loads(row_path.read_text())
        row["failure_attribution"] = classify_row_failure(row)
        _write_json(row_path, row)
        row_results.append(row)

    existing_results = {}
    results_path = output_dir / "results.json"
    if results_path.exists():
        existing_results = json.loads(results_path.read_text())
    summary = summarize_results(
        row_results=row_results,
        output_dir=output_dir,
        endpoint=str(existing_results.get("endpoint") or DEFAULT_ENDPOINT),
        started_at=str(existing_results.get("started_at") or _now_iso()),
        finished_at=str(existing_results.get("finished_at") or _now_iso()),
    )
    _write_json(results_path, summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary) + "\n")
    return summary


def usage_totals(row_results: list[JsonDict]) -> JsonDict:
    total_tokens = 0
    estimated_cost = 0.0
    for row in row_results:
        usage = row.get("usage", {})
        if isinstance(usage, dict):
            total_tokens += int(
                usage.get("total_tokens")
                or usage.get("total_tokens_count")
                or usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                or 0
            )
            estimated_cost += float(usage.get("cost") or usage.get("estimated_cost") or 0.0)
    return {"total_tokens": total_tokens, "estimated_cost_usd": estimated_cost}


def failure_totals(row_results: list[JsonDict]) -> JsonDict:
    totals = {"provider_failures": 0, "protocol_failures": 0}
    for row in row_results:
        failure = row.get("provider_failure")
        if not isinstance(failure, dict):
            continue
        if failure.get("layer") == "provider":
            totals["provider_failures"] += 1
        elif failure.get("layer") == "protocol":
            totals["protocol_failures"] += 1
    return totals


def protocol_recovery_totals(row_results: list[JsonDict]) -> JsonDict:
    totals: JsonDict = {
        "protocol_failures": 0,
        "recoverable_protocol_failures": 0,
        "unrecoverable_protocol_failures": 0,
        "strict_pass_if_recovered": 0,
        "relaxed_pass_if_recovered": 0,
        "recovery_methods": {},
    }
    for row in row_results:
        recovery = row.get("recovery_evaluation")
        failure = row.get("provider_failure")
        if not (
            isinstance(failure, dict)
            and failure.get("layer") == "protocol"
            and failure.get("code") == "invalid_action_schema"
        ):
            continue
        totals["protocol_failures"] += 1
        if isinstance(recovery, dict) and recovery.get("recovered"):
            totals["recoverable_protocol_failures"] += 1
            if recovery.get("strict_pass_if_recovered"):
                totals["strict_pass_if_recovered"] += 1
            if recovery.get("relaxed_pass_if_recovered"):
                totals["relaxed_pass_if_recovered"] += 1
            method = str(recovery.get("method") or "unknown")
            methods = totals["recovery_methods"]
            methods[method] = int(methods.get(method, 0)) + 1
        else:
            totals["unrecoverable_protocol_failures"] += 1
    return totals


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: JsonDict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-preregistration", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--refresh-analysis", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()

    if args.refresh_analysis:
        result = refresh_existing(output_dir=args.output_dir)
    elif args.run_live:
        result = execute_live(
            output_dir=args.output_dir,
            api_key=os.environ.get(args.api_key_env, ""),
            endpoint=args.endpoint,
        )
    else:
        result = write_preregistration_artifacts(ROOT_DIR)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
