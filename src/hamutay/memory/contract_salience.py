"""Cross-model action-object contract salience experiment."""

from __future__ import annotations

import argparse
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.memory.contract_literacy import (
    EXPERIMENT_ID as SOURCE_EXPERIMENT_ID,
    call_anthropic_messages_action,
    call_openrouter_action,
    evaluate_cycle1_action_object,
    failure_taxonomy as literacy_failure_taxonomy,
    prompt_variants as literacy_prompt_variants,
)
from hamutay.memory.live_pilot import DEFAULT_ENDPOINT


JsonDict = dict[str, Any]

EXPERIMENT_ID = "action_object_contract_salience_cross_model_20260611"
DEFAULT_EXPERIMENT_DIR = Path("experiments") / EXPERIMENT_ID
DEFAULT_LIVE_OUTPUT_DIR = DEFAULT_EXPERIMENT_DIR / "live_matrix_20260611"
DEFAULT_ENDPOINT_RECOVERY_OUTPUT_DIR = (
    DEFAULT_EXPERIMENT_DIR / "endpoint_recovery_20260611"
)
DEFAULT_OPENROUTER_ANTHROPIC_ENDPOINT = "https://openrouter.ai/api"
DEFAULT_DEEPSEEK_ENDPOINT = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_ANTHROPIC_ENDPOINT = "https://api.deepseek.com/anthropic"
SOURCE_LIVE_RESULTS_PATH = (
    Path("experiments")
    / SOURCE_EXPERIMENT_ID
    / "live_matrix_20260610"
    / "results.json"
)
LIVE_REPETITIONS_PER_CONDITION = 3
FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

MODEL_SET: tuple[JsonDict, ...] = (
    {
        "model_key": "deepseek_v4_pro",
        "model_id": "deepseek/deepseek-v4-pro",
        "family": "deepseek",
        "role": "source_failure_model",
    },
    {
        "model_key": "kimi_k2_6",
        "model_id": "moonshotai/kimi-k2.6",
        "family": "moonshot_kimi",
        "role": "low_cost_peer_model",
    },
    {
        "model_key": "claude_sonnet_4_6",
        "model_id": "anthropic/claude-sonnet-4.6",
        "family": "anthropic",
        "role": "anthropic_anchor_model",
    },
    {
        "model_key": "gpt_5_1",
        "model_id": "openai/gpt-5.1",
        "family": "openai",
        "role": "openai_compatible_anchor_model",
    },
)

PROMPT_CONDITIONS: tuple[JsonDict, ...] = (
    {
        "prompt_condition": "original_strict",
        "base_evaluator_condition_id": "A_original_prompt_strict_contract",
        "prompt_variant": "original_live_pilot_seed_prompt",
        "prompt_addendum": "",
    },
    {
        "prompt_condition": "example_strict",
        "base_evaluator_condition_id": "B_example_prompt_strict_contract",
        "prompt_variant": "original_plus_one_valid_open_item_example",
        "prompt_addendum": literacy_prompt_variants()["variants"][
            "original_plus_one_valid_open_item_example"
        ]["addendum"],
    },
)


def cross_model_matrix() -> JsonDict:
    conditions: list[JsonDict] = []
    for model in MODEL_SET:
        for prompt in PROMPT_CONDITIONS:
            condition_id = (
                f"{model['model_key']}__{prompt['prompt_condition']}"
            )
            conditions.append(
                {
                    "condition_id": condition_id,
                    "model_key": model["model_key"],
                    "model_id": model["model_id"],
                    "model_family": model["family"],
                    "model_role": model["role"],
                    "provider": "OpenRouter",
                    "prompt_condition": prompt["prompt_condition"],
                    "prompt_variant": prompt["prompt_variant"],
                    "prompt_addendum_application": "system_message_suffix",
                    "prompt_addendum": prompt["prompt_addendum"],
                    "base_evaluator_condition_id": prompt[
                        "base_evaluator_condition_id"
                    ],
                    "contract": "strict_autonomous_action_v1",
                    "acceptance_rule": (
                        "strict parser requires one accepted open_item and "
                        "one accepted schedule_request"
                    ),
                }
            )
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "live_calls_per_condition": LIVE_REPETITIONS_PER_CONDITION,
        "conditions": conditions,
        "model_availability_source": (
            "OpenRouter /api/v1/models queried 2026-06-11 before "
            "preregistration; fallbacks disabled during execution."
        ),
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "max_live_calls": 24,
        "max_calls_per_condition": LIVE_REPETITIONS_PER_CONDITION,
        "max_cycles_per_call": 1,
        "max_output_tokens_per_call": None,
        "output_cap_policy": (
            "No artificial per-call output cap for research matrix calls; "
            "provider/model limits still apply."
        ),
        "max_total_tokens": 60000,
        "max_estimated_cost_usd": 2.00,
        "stop_rule": (
            "Stop if provider/protocol failures make cross-model attribution "
            "impossible, or if token/cost budget is exceeded."
        ),
    }


def failure_taxonomy() -> JsonDict:
    inherited = literacy_failure_taxonomy()
    return {
        "experiment_id": EXPERIMENT_ID,
        "source_taxonomy": inherited["schema_version"],
        "schema_version": "hamutay.cross_model_contract_salience_taxonomy.v1",
        "entries": inherited["entries"]
        + [
            {
                "layer": "model_family",
                "code": "model_specific_contract_salience_boundary",
                "meaning": (
                    "Original-prompt failure is concentrated in one model "
                    "family and not reproduced across peers."
                ),
            },
            {
                "layer": "prompt_contract",
                "code": "cross_model_contract_salience_boundary",
                "meaning": (
                    "Multiple model families fail the original strict prompt "
                    "but improve under the example prompt."
                ),
            },
        ],
    }


def write_preregistration_artifacts(output_dir: Path) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": cross_model_matrix(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
        "prompt_variants.json": {
            "experiment_id": EXPERIMENT_ID,
            "variants": {
                prompt["prompt_condition"]: {
                    "prompt_variant": prompt["prompt_variant"],
                    "prompt_addendum": prompt["prompt_addendum"],
                }
                for prompt in PROMPT_CONDITIONS
            },
        },
    }
    for name, payload in artifacts.items():
        _write_json(output_dir / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "artifacts": sorted(artifacts),
    }


def endpoint_recovery_matrix() -> JsonDict:
    conditions = [
        _endpoint_recovery_condition(condition)
        for condition in cross_model_matrix()["conditions"]
        if condition["model_key"] in {"claude_sonnet_4_6", "deepseek_v4_pro"}
    ]
    return {
        "experiment_id": EXPERIMENT_ID,
        "recovery_scope": (
            "Rerun only rows that were unscoreable in "
            "live_matrix_20260611_recovery_no_cap_retry because of "
            "endpoint/protocol/provider confounds."
        ),
        "live_calls_per_condition": LIVE_REPETITIONS_PER_CONDITION,
        "conditions": conditions,
    }


def _endpoint_recovery_condition(condition: JsonDict) -> JsonDict:
    recovered = deepcopy(condition)
    if condition["model_key"] == "claude_sonnet_4_6":
        recovered.update(
            {
                "provider": "OpenRouter Anthropic-compatible",
                "endpoint_family": "anthropic_messages",
                "endpoint_default": DEFAULT_OPENROUTER_ANTHROPIC_ENDPOINT,
                "request_shape": (
                    "POST /v1/messages with forced loose submit_action_object "
                    "tool input; response object comes from tool_use.input."
                ),
            }
        )
    elif condition["model_key"] == "deepseek_v4_pro":
        recovered.update(
            {
                "provider": "DeepSeek direct Anthropic-compatible",
                "endpoint_family": "deepseek_anthropic_messages",
                "endpoint_default": DEFAULT_DEEPSEEK_ANTHROPIC_ENDPOINT,
                "model_id": "deepseek-v4-pro",
                "request_shape": (
                    "POST /v1/messages with loose submit_action_object tool "
                    "input and tool_choice=auto because DeepSeek thinking mode "
                    "rejects forced tool choice."
                ),
            }
        )
    else:
        raise ValueError(f"unsupported endpoint recovery condition: {condition}")
    return recovered


def execute_live_matrix(
    *,
    output_dir: Path = DEFAULT_LIVE_OUTPUT_DIR,
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout_seconds: float = 120.0,
) -> JsonDict:
    if not api_key:
        raise ValueError("api_key is required for live matrix execution")

    output_dir.mkdir(parents=True, exist_ok=False)
    rows_dir = output_dir / "rows"
    rows_dir.mkdir()

    matrix = cross_model_matrix()
    budget = budget_manifest()
    planned_rows = (
        len(matrix["conditions"]) * int(matrix["live_calls_per_condition"])
    )
    if planned_rows > int(budget["max_live_calls"]):
        raise ValueError("matrix exceeds preregistered live-call budget")

    for name, payload in {
        "matrix.json": matrix,
        "budget.json": budget,
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        _write_json(output_dir / name, payload)

    row_results: list[JsonDict] = []
    started_at = _now_iso()
    for condition in matrix["conditions"]:
        for repetition in range(1, LIVE_REPETITIONS_PER_CONDITION + 1):
            row = execute_live_row(
                condition=condition,
                repetition=repetition,
                rows_dir=rows_dir,
                api_key=api_key,
                endpoint=endpoint,
                timeout_seconds=timeout_seconds,
            )
            row_results.append(row)
            totals = _usage_totals(row_results)
            if totals["total_tokens"] > int(budget["max_total_tokens"]):
                break
            if totals["estimated_cost_usd"] > float(budget["max_estimated_cost_usd"]):
                break

    summary = summarize_results(
        row_results=row_results,
        started_at=started_at,
        finished_at=_now_iso(),
        output_dir=output_dir,
        endpoint=endpoint,
    )
    _write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary))
    return summary


def execute_endpoint_recovery_matrix(
    *,
    output_dir: Path = DEFAULT_ENDPOINT_RECOVERY_OUTPUT_DIR,
    openrouter_api_key: str,
    deepseek_api_key: str,
    openrouter_anthropic_endpoint: str = DEFAULT_OPENROUTER_ANTHROPIC_ENDPOINT,
    deepseek_endpoint: str = DEFAULT_DEEPSEEK_ENDPOINT,
    deepseek_anthropic_endpoint: str = DEFAULT_DEEPSEEK_ANTHROPIC_ENDPOINT,
    timeout_seconds: float = 120.0,
) -> JsonDict:
    if not openrouter_api_key:
        raise ValueError("openrouter_api_key is required for Claude recovery rows")
    if not deepseek_api_key:
        raise ValueError("deepseek_api_key is required for DeepSeek recovery rows")

    output_dir.mkdir(parents=True, exist_ok=False)
    rows_dir = output_dir / "rows"
    rows_dir.mkdir()

    matrix = endpoint_recovery_matrix()
    budget = {
        **budget_manifest(),
        "max_live_calls": len(matrix["conditions"]) * LIVE_REPETITIONS_PER_CONDITION,
        "recovery_scope": matrix["recovery_scope"],
        "endpoint_recovery": True,
    }
    for name, payload in {
        "matrix.json": matrix,
        "budget.json": budget,
        "failure_taxonomy.json": failure_taxonomy(),
    }.items():
        _write_json(output_dir / name, payload)

    endpoint_by_family = {
        "anthropic_messages": openrouter_anthropic_endpoint,
        "openai_chat": deepseek_endpoint,
        "deepseek_anthropic_messages": deepseek_anthropic_endpoint,
    }
    row_results: list[JsonDict] = []
    started_at = _now_iso()
    for condition in matrix["conditions"]:
        for repetition in range(1, LIVE_REPETITIONS_PER_CONDITION + 1):
            row = execute_endpoint_recovery_row(
                condition=condition,
                repetition=repetition,
                rows_dir=rows_dir,
                openrouter_api_key=openrouter_api_key,
                deepseek_api_key=deepseek_api_key,
                openrouter_anthropic_endpoint=openrouter_anthropic_endpoint,
                deepseek_endpoint=deepseek_endpoint,
                deepseek_anthropic_endpoint=deepseek_anthropic_endpoint,
                timeout_seconds=timeout_seconds,
            )
            row_results.append(row)
            totals = _usage_totals(row_results)
            if totals["total_tokens"] > int(budget["max_total_tokens"]):
                break
            if totals["estimated_cost_usd"] > float(budget["max_estimated_cost_usd"]):
                break

    summary = summarize_results(
        row_results=row_results,
        started_at=started_at,
        finished_at=_now_iso(),
        output_dir=output_dir,
        endpoint="endpoint-family-aware",
    )
    summary["endpoint_recovery"] = True
    summary["endpoint_by_family"] = endpoint_by_family
    _write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary))
    return summary


def execute_endpoint_recovery_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    openrouter_api_key: str,
    deepseek_api_key: str,
    openrouter_anthropic_endpoint: str,
    deepseek_endpoint: str,
    deepseek_anthropic_endpoint: str,
    timeout_seconds: float,
) -> JsonDict:
    endpoint_family = str(condition["endpoint_family"])
    if endpoint_family == "anthropic_messages":
        provider = call_anthropic_messages_action(
            api_key=openrouter_api_key,
            endpoint=openrouter_anthropic_endpoint,
            model=str(condition["model_id"]),
            messages=_messages_for_condition(condition, repetition=repetition),
            timeout_seconds=timeout_seconds,
        )
        endpoint = openrouter_anthropic_endpoint
    elif endpoint_family == "deepseek_anthropic_messages":
        provider = call_anthropic_messages_action(
            api_key=deepseek_api_key,
            endpoint=deepseek_anthropic_endpoint,
            model=str(condition["model_id"]),
            messages=_messages_for_condition(condition, repetition=repetition),
            timeout_seconds=timeout_seconds,
            tool_choice={"type": "auto"},
        )
        endpoint = deepseek_anthropic_endpoint
    elif endpoint_family == "openai_chat":
        provider = call_openrouter_action(
            api_key=deepseek_api_key,
            endpoint=deepseek_endpoint,
            model=str(condition["model_id"]),
            messages=_messages_for_condition(condition, repetition=repetition),
            timeout_seconds=timeout_seconds,
            include_openrouter_options=False,
        )
        endpoint = deepseek_endpoint
    else:
        raise ValueError(f"unsupported endpoint_family: {endpoint_family}")
    return _write_evaluated_row(
        condition=condition,
        repetition=repetition,
        rows_dir=rows_dir,
        provider=provider,
        endpoint=endpoint,
        endpoint_family=endpoint_family,
    )


def execute_live_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    api_key: str,
    endpoint: str,
    timeout_seconds: float,
) -> JsonDict:
    provider = call_openrouter_action(
        api_key=api_key,
        endpoint=endpoint,
        model=str(condition["model_id"]),
        messages=_messages_for_condition(condition, repetition=repetition),
        timeout_seconds=timeout_seconds,
    )
    return _write_evaluated_row(
        condition=condition,
        repetition=repetition,
        rows_dir=rows_dir,
        provider=provider,
        endpoint=endpoint,
        endpoint_family="openai_chat_openrouter",
    )


def _write_evaluated_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    provider: JsonDict,
    endpoint: str,
    endpoint_family: str,
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

    base_condition_id = str(condition["base_evaluator_condition_id"])
    strict_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=base_condition_id,
        relaxed_open_item_contract=False,
    )
    relaxed_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=base_condition_id,
        relaxed_open_item_contract=True,
    )
    row_result = {
        "schema_version": "hamutay.cross_model_contract_salience_row.v1",
        "experiment_id": EXPERIMENT_ID,
        "row_id": row_id,
        "condition_id": condition["condition_id"],
        "model_key": condition["model_key"],
        "model_id": condition["model_id"],
        "prompt_condition": condition["prompt_condition"],
        "repetition": repetition,
        "condition": deepcopy(condition),
        "endpoint": endpoint,
        "endpoint_family": endpoint_family,
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
    _write_json(row_dir / "strict_evaluation.json", strict_evaluation)
    _write_json(row_dir / "relaxed_evaluation.json", relaxed_evaluation)
    _write_json(row_dir / "row_result.json", row_result)
    return row_result


def secondary_recovery_evaluation(row: JsonDict) -> JsonDict:
    """Secondary-only recovery for protocol-wrapper artifacts.

    This does not alter primary provider/protocol classification. It only asks
    whether a row rejected as invalid_action_schema contains a recoverable
    JSON object and how the unmodified evaluators score that recovered object.
    """

    failure = row.get("provider_failure")
    attempted = (
        isinstance(failure, dict)
        and failure.get("layer") == "protocol"
        and failure.get("code") == "invalid_action_schema"
    )
    result: JsonDict = {
        "schema_version": "hamutay.protocol_recovery_evaluation.v1",
        "recovery_attempted": attempted,
        "recovered": False,
        "method": None,
        "primary_provider_failure": deepcopy(failure) if isinstance(failure, dict) else None,
        "primary_classification_preserved": True,
    }
    if not attempted:
        result["reason"] = "primary_failure_was_not_invalid_action_schema"
        return result

    recovered_object, method = recover_embedded_action_object(row.get("raw_content"))
    if recovered_object is None:
        result["reason"] = "no_recoverable_json_object"
        return result

    base_condition_id = str(row["condition"]["base_evaluator_condition_id"])
    strict = evaluate_cycle1_action_object(
        recovered_object,
        condition_id=base_condition_id,
        relaxed_open_item_contract=False,
    )
    relaxed = evaluate_cycle1_action_object(
        recovered_object,
        condition_id=base_condition_id,
        relaxed_open_item_contract=True,
    )
    result.update(
        {
            "recovered": True,
            "method": method,
            "recovered_action_object": recovered_object,
            "strict_evaluation": strict,
            "relaxed_evaluation": relaxed,
            "strict_pass_if_recovered": strict["strict_required_actions_valid"],
            "relaxed_pass_if_recovered": relaxed["relaxed_required_actions_valid"],
        }
    )
    return result


def recover_embedded_action_object(raw: Any) -> tuple[JsonDict | None, str | None]:
    if not isinstance(raw, str):
        return None, None
    seen: set[str] = set()
    for method, candidate in _recovery_candidates(raw):
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed, method
    return None, None


def _recovery_candidates(raw: str) -> list[tuple[str, str]]:
    candidates = [("raw_json", raw)]
    candidates.extend(
        ("fenced_json", match.group(1))
        for match in FENCED_JSON_PATTERN.finditer(raw)
    )
    candidates.extend(
        ("embedded_json_object", candidate)
        for candidate in _embedded_json_object_candidates(raw)
    )
    return candidates


def _embedded_json_object_candidates(raw: str) -> list[str]:
    decoder = json.JSONDecoder()
    candidates: list[str] = []
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            parsed, end = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            candidates.append(raw[index : index + end])
    return candidates


def summarize_results(
    *,
    row_results: list[JsonDict],
    started_at: str,
    finished_at: str,
    output_dir: Path,
    endpoint: str,
) -> JsonDict:
    by_model_prompt: dict[str, JsonDict] = {}
    by_model: dict[str, JsonDict] = {}
    for row in row_results:
        key = f"{row['model_key']}__{row['prompt_condition']}"
        prompt_bucket = by_model_prompt.setdefault(
            key,
            _empty_bucket(
                model_key=str(row["model_key"]),
                model_id=str(row["model_id"]),
                prompt_condition=str(row["prompt_condition"]),
            ),
        )
        model_bucket = by_model.setdefault(
            str(row["model_key"]),
            {
                "model_key": row["model_key"],
                "model_id": row["model_id"],
                "rows": 0,
                "original_scorable_count": 0,
                "example_scorable_count": 0,
                "original_strict_pass_count": 0,
                "example_strict_pass_count": 0,
                "original_strict_fail_relaxed_pass_count": 0,
                "example_strict_fail_relaxed_pass_count": 0,
            },
        )
        _accumulate_bucket(prompt_bucket, row)
        model_bucket["rows"] += 1
        provider_failure = row.get("provider_failure")
        scorable = not isinstance(provider_failure, dict)
        strict = row["strict_evaluation"]["strict_required_actions_valid"]
        relaxed = row["relaxed_evaluation"]["relaxed_required_actions_valid"]
        prompt_condition = row["prompt_condition"]
        if prompt_condition == "original_strict" and scorable:
            model_bucket["original_scorable_count"] += 1
        if prompt_condition == "example_strict" and scorable:
            model_bucket["example_scorable_count"] += 1
        if prompt_condition == "original_strict" and scorable and strict:
            model_bucket["original_strict_pass_count"] += 1
        if prompt_condition == "example_strict" and scorable and strict:
            model_bucket["example_strict_pass_count"] += 1
        if prompt_condition == "original_strict" and scorable and not strict and relaxed:
            model_bucket["original_strict_fail_relaxed_pass_count"] += 1
        if prompt_condition == "example_strict" and scorable and not strict and relaxed:
            model_bucket["example_strict_fail_relaxed_pass_count"] += 1

    source_reference = load_source_deepseek_reference()
    hypothesis_assessment = assess_cross_model_salience(
        by_model,
        source_deepseek_reference=source_reference,
    )
    return {
        "schema_version": "hamutay.cross_model_contract_salience_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "live_model_calls": True,
        "endpoint": endpoint,
        "output_dir": str(output_dir),
        "row_count": len(row_results),
        "usage_totals": _usage_totals(row_results),
        "failure_totals": _failure_totals(row_results),
        "protocol_recovery_totals": _protocol_recovery_totals(row_results),
        "budget": budget_manifest(),
        "by_model_prompt": by_model_prompt,
        "by_model": by_model,
        "source_deepseek_reference": source_reference,
        "hypothesis_assessment": hypothesis_assessment,
        "row_result_paths": [
            str(Path("rows") / row["row_id"] / "row_result.json")
            for row in row_results
        ],
    }


def assess_cross_model_salience(
    by_model: dict[str, JsonDict],
    *,
    source_deepseek_reference: JsonDict | None = None,
) -> JsonDict:
    current_models_with_original_failure = [
        key
        for key, bucket in by_model.items()
        if int(bucket.get("original_scorable_count", 0)) >= 2
        and int(bucket.get("original_strict_pass_count", 0)) < 2
    ]
    current_models_with_example_rescue = [
        key
        for key, bucket in by_model.items()
        if int(bucket.get("original_scorable_count", 0)) >= 2
        and int(bucket.get("original_strict_pass_count", 0)) < 2
        and int(bucket.get("example_scorable_count", 0)) >= 2
        and int(bucket.get("example_strict_pass_count", 0)) >= 2
    ]
    models_with_example_failure = [
        key
        for key, bucket in by_model.items()
        if int(bucket.get("example_scorable_count", 0)) >= 2
        and int(bucket.get("example_strict_pass_count", 0)) < 2
    ]
    models_with_unscoreable_original = [
        key
        for key, bucket in by_model.items()
        if int(bucket.get("original_scorable_count", 0)) < 2
    ]
    models_with_unscoreable_example = [
        key
        for key, bucket in by_model.items()
        if int(bucket.get("example_scorable_count", 0)) < 2
    ]

    source_deepseek_rescued = bool(
        source_deepseek_reference
        and source_deepseek_reference.get("original_strict_pass_count") == 0
        and source_deepseek_reference.get("example_strict_pass_count") == 3
    )
    source_models_with_original_failure = (
        ["deepseek_v4_pro"] if source_deepseek_rescued else []
    )
    source_models_with_example_rescue = (
        ["deepseek_v4_pro"] if source_deepseek_rescued else []
    )

    deepseek_rescued = (
        "deepseek_v4_pro" in current_models_with_example_rescue
        or source_deepseek_rescued
    )
    deepseek_specific = (
        deepseek_rescued
        and all(
            key == "deepseek_v4_pro" for key in current_models_with_original_failure
        )
    )
    non_deepseek_reproduction = any(
        key != "deepseek_v4_pro" for key in current_models_with_example_rescue
    )
    cross_model = deepseek_rescued and non_deepseek_reproduction
    general_literacy_failure = len(models_with_example_failure) >= 2
    if deepseek_specific:
        primary = "deepseek_specific_contract_salience_boundary"
    elif cross_model:
        primary = "cross_model_contract_salience_boundary"
    elif general_literacy_failure:
        primary = "general_action_contract_literacy_failure"
    else:
        primary = "mixed_or_ambiguous_contract_salience_pattern"

    return {
        "primary_pattern": primary,
        "deepseek_specific_boundary": deepseek_specific,
        "cross_model_contract_salience": cross_model,
        "general_action_contract_literacy_failure": general_literacy_failure,
        "models_with_original_failure": current_models_with_original_failure,
        "models_with_example_rescue": current_models_with_example_rescue,
        "source_reference_models_with_original_failure": (
            source_models_with_original_failure
        ),
        "source_reference_models_with_example_rescue": source_models_with_example_rescue,
        "models_with_example_failure": models_with_example_failure,
        "models_with_unscoreable_original": models_with_unscoreable_original,
        "models_with_unscoreable_example": models_with_unscoreable_example,
        "source_deepseek_reference_used": source_deepseek_rescued,
    }


def render_analysis(summary: JsonDict) -> str:
    lines = [
        "# Cross-Model Action-Object Contract Salience Analysis",
        "",
        f"Experiment ID: `{summary['experiment_id']}`",
        "",
        "## Execution",
        "",
        f"- Started: `{summary['started_at']}`",
        f"- Finished: `{summary['finished_at']}`",
        f"- Endpoint: `{summary['endpoint']}`",
        f"- Rows: {summary['row_count']}",
        f"- Total tokens: {summary['usage_totals']['total_tokens']}",
        f"- Estimated cost USD: {summary['usage_totals']['estimated_cost_usd']:.6f}",
        "",
    ]
    if summary.get("endpoint_by_family"):
        lines.extend(
            [
                "Endpoint families:",
                "",
                *[
                    f"- `{family}`: `{endpoint}`"
                    for family, endpoint in sorted(
                        summary["endpoint_by_family"].items()
                    )
                ],
                "",
            ]
        )
    lines.extend(
        [
            "## Model Counts",
            "",
            "| Model | Original strict pass | Example strict pass | Original strict fail / relaxed pass | Example strict fail / relaxed pass |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for model_key, bucket in summary["by_model"].items():
        lines.append(
            "| {model} | {orig} | {example} | {orig_relaxed} | {example_relaxed} |".format(
                model=model_key,
                orig=(
                    f"{bucket['original_strict_pass_count']}/"
                    f"{bucket['original_scorable_count']}"
                ),
                example=(
                    f"{bucket['example_strict_pass_count']}/"
                    f"{bucket['example_scorable_count']}"
                ),
                orig_relaxed=bucket[
                    "original_strict_fail_relaxed_pass_count"
                ],
                example_relaxed=bucket[
                    "example_strict_fail_relaxed_pass_count"
                ],
            )
        )

    recovery_totals = summary.get("protocol_recovery_totals", {})
    if recovery_totals:
        lines.extend(
            [
                "",
                "## Protocol Recovery Audit",
                "",
                "- Protocol failures: "
                f"`{recovery_totals['protocol_failures']}`",
                "- Recoverable protocol failures: "
                f"`{recovery_totals['recoverable_protocol_failures']}`",
                "- Unrecoverable protocol failures: "
                f"`{recovery_totals['unrecoverable_protocol_failures']}`",
                "- Strict pass if recovered: "
                f"`{recovery_totals['strict_pass_if_recovered']}`",
                "- Relaxed pass if recovered: "
                f"`{recovery_totals['relaxed_pass_if_recovered']}`",
                "- Recovery methods: "
                f"`{recovery_totals['recovery_methods']}`",
            ]
        )

    assessment = summary["hypothesis_assessment"]
    lines.extend(
        [
            "",
            "## Hypothesis Assessment",
            "",
            f"- Primary pattern: `{assessment['primary_pattern']}`",
            "- DeepSeek-specific boundary: "
            f"`{assessment['deepseek_specific_boundary']}`",
            "- Cross-model contract salience: "
            f"`{assessment['cross_model_contract_salience']}`",
            "- General action-contract literacy failure: "
            f"`{assessment['general_action_contract_literacy_failure']}`",
            "",
            "Evidence lists:",
            "",
            "- Models with original-prompt failure: "
            f"`{assessment['models_with_original_failure']}`",
            "- Models rescued by example prompt: "
            f"`{assessment['models_with_example_rescue']}`",
            "- Source-reference models with original-prompt failure: "
            f"`{assessment['source_reference_models_with_original_failure']}`",
            "- Source-reference models rescued by example prompt: "
            f"`{assessment['source_reference_models_with_example_rescue']}`",
            "- Models failing the example prompt: "
            f"`{assessment['models_with_example_failure']}`",
            "- Models unscoreable under original prompt: "
            f"`{assessment['models_with_unscoreable_original']}`",
            "- Models unscoreable under example prompt: "
            f"`{assessment['models_with_unscoreable_example']}`",
            "- Source DeepSeek reference used: "
            f"`{assessment['source_deepseek_reference_used']}`",
            "",
            "## Interpretation",
            "",
            _interpret_summary(summary),
            "",
            "## Limitations",
            "",
            _limitations_summary(summary),
            "",
            "## Artifact Trail",
            "",
            "- `results.json` contains aggregate machine-readable results.",
            "- `analysis.md` is this analysis artifact.",
            "- `rows/<row_id>/provider_request.json` preserves each request.",
            "- `rows/<row_id>/provider_response.json` preserves each response.",
            "- `rows/<row_id>/provider_attempts.json` preserves retry/attempt telemetry.",
            "- `rows/<row_id>/recovery_evaluation.json` preserves secondary recovery audits for invalid_action_schema rows.",
            "- `rows/<row_id>/strict_evaluation.json` preserves strict scoring.",
            "- `rows/<row_id>/relaxed_evaluation.json` preserves relaxed scoring.",
            "- `rows/<row_id>/row_result.json` ties each row together.",
            "",
        ]
    )
    return "\n".join(lines)


def load_source_deepseek_reference(
    path: Path = SOURCE_LIVE_RESULTS_PATH,
) -> JsonDict | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    conditions = data.get("by_condition", {})
    original = conditions.get("A_original_prompt_strict_contract", {})
    example = conditions.get("B_example_prompt_strict_contract", {})
    return {
        "source_path": str(path),
        "original_strict_pass_count": int(original.get("strict_pass_count", 0)),
        "example_strict_pass_count": int(example.get("strict_pass_count", 0)),
        "original_strict_fail_relaxed_pass_count": int(
            original.get("strict_fail_relaxed_pass_count", 0)
        ),
        "example_strict_fail_relaxed_pass_count": int(
            example.get("strict_fail_relaxed_pass_count", 0)
        ),
    }


def _messages_for_condition(condition: JsonDict, *, repetition: int) -> list[JsonDict]:
    from hamutay.memory.contract_literacy import build_condition_messages

    return build_condition_messages(
        {
            "condition_id": condition["condition_id"],
            "prompt_addendum": condition["prompt_addendum"],
        },
        repetition=repetition,
    )


def _empty_bucket(
    *,
    model_key: str,
    model_id: str,
    prompt_condition: str,
) -> JsonDict:
    return {
        "model_key": model_key,
        "model_id": model_id,
        "prompt_condition": prompt_condition,
        "rows": 0,
        "provider_failures": 0,
        "protocol_failures": 0,
        "strict_pass_count": 0,
        "relaxed_pass_count": 0,
        "strict_fail_relaxed_pass_count": 0,
        "rejection_paths": {},
        "explanation_candidates": {},
    }


def _accumulate_bucket(bucket: JsonDict, row: JsonDict) -> None:
    bucket["rows"] += 1
    provider_failure = row.get("provider_failure")
    if not isinstance(provider_failure, dict):
        provider_failure = {}
    if provider_failure.get("layer") == "provider":
        bucket["provider_failures"] += 1
    if provider_failure.get("layer") == "protocol":
        bucket["protocol_failures"] += 1
    strict = row["strict_evaluation"]
    relaxed = row["relaxed_evaluation"]
    if strict["strict_required_actions_valid"]:
        bucket["strict_pass_count"] += 1
    if relaxed["relaxed_required_actions_valid"]:
        bucket["relaxed_pass_count"] += 1
    if (
        not strict["strict_required_actions_valid"]
        and relaxed["relaxed_required_actions_valid"]
    ):
        bucket["strict_fail_relaxed_pass_count"] += 1
    _count_values(bucket["rejection_paths"], strict["rejection_paths"])
    _count_values(bucket["explanation_candidates"], strict["explanation_candidates"])


def _interpret_summary(summary: JsonDict) -> str:
    primary = summary["hypothesis_assessment"]["primary_pattern"]
    if primary == "deepseek_specific_contract_salience_boundary":
        return (
            "The original-prompt failure appears concentrated in DeepSeek V4 Pro "
            "within this small matrix. The example prompt rescues DeepSeek while "
            "the peer models do not reproduce the original strict failure."
        )
    if primary == "cross_model_contract_salience_boundary":
        return (
            "The original-prompt failure is not DeepSeek-specific in this matrix. "
            "Multiple model families fail the original strict prompt and improve "
            "with the example prompt, supporting a broader prompt/contract "
            "salience explanation."
        )
    if primary == "general_action_contract_literacy_failure":
        return (
            "The example prompt did not rescue enough models. Treat the current "
            "action-object contract pattern as insufficiently learnable under "
            "this test rather than merely underspecified in the original prompt."
        )
    return (
        "The pattern is mixed or ambiguous. Inspect row-level provider responses "
        "before choosing a harness fix."
    )


def _limitations_summary(summary: JsonDict) -> str:
    assessment = summary["hypothesis_assessment"]
    unscoreable_original = assessment["models_with_unscoreable_original"]
    unscoreable_example = assessment["models_with_unscoreable_example"]
    failure_totals = summary.get("failure_totals", {})
    recovery_totals = summary.get("protocol_recovery_totals", {})
    provider_rows = int(failure_totals.get("provider_failures", 0) or 0)
    protocol_rows = int(failure_totals.get("protocol_failures", 0) or 0)
    recoverable_rows = int(
        recovery_totals.get("recoverable_protocol_failures", 0) or 0
    )
    if not unscoreable_original and not unscoreable_example:
        if provider_rows or protocol_rows:
            return (
                "No provider/protocol unscoreable model conditions were observed. "
                "Row-level residuals remain: "
                f"{provider_rows} provider failure rows and "
                f"{protocol_rows} protocol failure rows. "
                f"{recoverable_rows} protocol failure rows were recoverable by "
                "secondary audit without changing primary scoring."
            )
        return "No provider/protocol unscoreable model conditions were observed."
    return (
        "Provider/protocol failures are not counted as model contract failures. "
        f"Original-prompt unscoreable models: `{unscoreable_original}`. "
        f"Example-prompt unscoreable models: `{unscoreable_example}`. "
        "DeepSeek and Claude current-run rows were therefore not used as direct "
        "current-run model evidence; the DeepSeek side of the cross-model "
        "comparison uses the prior committed source experiment reference."
    )


def _failure_totals(row_results: list[JsonDict]) -> JsonDict:
    totals = {"provider_failures": 0, "protocol_failures": 0}
    for row in row_results:
        failure = row.get("provider_failure")
        if not isinstance(failure, dict):
            continue
        if failure.get("layer") == "provider":
            totals["provider_failures"] += 1
        if failure.get("layer") == "protocol":
            totals["protocol_failures"] += 1
    return totals


def _protocol_recovery_totals(row_results: list[JsonDict]) -> JsonDict:
    totals: JsonDict = {
        "protocol_failures": 0,
        "recoverable_protocol_failures": 0,
        "unrecoverable_protocol_failures": 0,
        "strict_pass_if_recovered": 0,
        "relaxed_pass_if_recovered": 0,
        "recovery_methods": {},
    }
    for row in row_results:
        failure = row.get("provider_failure")
        if not (
            isinstance(failure, dict)
            and failure.get("layer") == "protocol"
            and failure.get("code") == "invalid_action_schema"
        ):
            continue
        totals["protocol_failures"] += 1
        recovery = row.get("recovery_evaluation")
        if not isinstance(recovery, dict):
            recovery = secondary_recovery_evaluation(row)
        if recovery.get("recovered"):
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


def _usage_totals(row_results: list[JsonDict]) -> JsonDict:
    total_tokens = 0
    estimated_cost = 0.0
    for row in row_results:
        usage = row.get("usage", {})
        if not isinstance(usage, dict):
            continue
        total_tokens += int(usage.get("total_tokens", 0) or 0)
        estimated_cost += float(usage.get("cost", 0.0) or 0.0)
    return {
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost,
    }


def _count_values(counter: JsonDict, values: list[str]) -> None:
    for value in values:
        counter[value] = int(counter.get(value, 0)) + 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: JsonDict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--run-endpoint-recovery", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument(
        "--openrouter-anthropic-endpoint",
        default=DEFAULT_OPENROUTER_ANTHROPIC_ENDPOINT,
    )
    parser.add_argument("--deepseek-endpoint", default=DEFAULT_DEEPSEEK_ENDPOINT)
    parser.add_argument(
        "--deepseek-anthropic-endpoint",
        default=DEFAULT_DEEPSEEK_ANTHROPIC_ENDPOINT,
    )
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    parser.add_argument("--deepseek-api-key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()

    if args.run_endpoint_recovery:
        result = execute_endpoint_recovery_matrix(
            output_dir=args.output_dir or DEFAULT_ENDPOINT_RECOVERY_OUTPUT_DIR,
            openrouter_api_key=os.environ.get(args.api_key_env, ""),
            deepseek_api_key=os.environ.get(args.deepseek_api_key_env, ""),
            openrouter_anthropic_endpoint=args.openrouter_anthropic_endpoint,
            deepseek_endpoint=args.deepseek_endpoint,
            deepseek_anthropic_endpoint=args.deepseek_anthropic_endpoint,
        )
    elif args.run_live:
        result = execute_live_matrix(
            output_dir=args.output_dir or DEFAULT_LIVE_OUTPUT_DIR,
            api_key=os.environ.get(args.api_key_env, ""),
            endpoint=args.endpoint,
        )
    else:
        result = write_preregistration_artifacts(
            args.output_dir or DEFAULT_EXPERIMENT_DIR
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
