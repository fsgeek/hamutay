"""Evaluator and runner for action-object contract literacy experiments."""

from __future__ import annotations

import argparse
import json
import os
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

from hamutay.memory.live_pilot import DEFAULT_ENDPOINT, DEFAULT_MODEL, _seed_messages
from hamutay.memory.actions import parse_autonomous_action


JsonDict = dict[str, Any]

EXPERIMENT_ID = "action_object_contract_literacy_20260610"
FAILED_RUN_ID = "c39ba9a3-9dda-48f2-82f6-cb90f8229bae"
FAILED_RUN_RESPONSE_PATH = Path(
    "experiments/live_autonomy_pilot_20260609/runs"
) / FAILED_RUN_ID / "cycle_01_provider_response.json"
DEFAULT_EXPERIMENT_DIR = Path("experiments") / EXPERIMENT_ID
DEFAULT_LIVE_OUTPUT_DIR = DEFAULT_EXPERIMENT_DIR / "live_matrix_20260610"
DEFAULT_PROVIDER_RETRY_ATTEMPTS = 3
DEFAULT_PROVIDER_RETRY_SLEEP_CAP_SECONDS = 20.0
DEFAULT_ANTHROPIC_MESSAGES_MAX_TOKENS = 8192
TRANSIENT_PROVIDER_STATUS_CODES = {429, 500, 502, 503, 504, 529}

CONDITION_IDS = (
    "A_original_prompt_strict_contract",
    "B_example_prompt_strict_contract",
    "C_schema_checklist_strict_contract",
    "D_relaxed_open_item_contract",
)

PROMPT_VARIANTS: JsonDict = {
    "original_live_pilot_seed_prompt": {
        "base_prompt_source": (
            "hamutay.memory.live_pilot._action_object_system_prompt plus "
            "hamutay.memory.live_pilot._seed_messages"
        ),
        "addendum": "",
    },
    "original_plus_one_valid_open_item_example": {
        "base_prompt_source": (
            "hamutay.memory.live_pilot._action_object_system_prompt plus "
            "hamutay.memory.live_pilot._seed_messages"
        ),
        "addendum": (
            "Example valid open item shape: "
            "{\"kind\":\"todo\",\"text\":\"resolve the bounded follow-up item\"}. "
            "Do not use description, handle, status, or created_at as substitutes "
            "for kind and text."
        ),
    },
    "original_plus_schema_and_checklist": {
        "base_prompt_source": (
            "hamutay.memory.live_pilot._action_object_system_prompt plus "
            "hamutay.memory.live_pilot._seed_messages"
        ),
        "addendum": (
            "Before returning, verify this checklist: response is a non-empty "
            "string; open_items is an array with exactly one object; "
            "open_items[0].kind is a non-empty string; open_items[0].text is a "
            "non-empty string; schedule_requests is an array with exactly one "
            "object; schedule_requests[0].purpose is a non-empty string; "
            "schedule_requests[0].requested_context includes the requested "
            "recall record_id. Return only the JSON object."
        ),
    },
    "relaxed_open_item_contract_counterfactual": {
        "base_prompt_source": (
            "hamutay.memory.live_pilot._action_object_system_prompt plus "
            "hamutay.memory.live_pilot._seed_messages"
        ),
        "addendum": (
            "Counterfactual scoring contract: an open item may omit kind if the "
            "authored object has a usable description; missing kind maps to "
            "todo and description maps to text for scoring only. The live "
            "harness must not silently repair or apply this normalization."
        ),
    },
}


def condition_matrix() -> JsonDict:
    """Return the preregistered fixed condition matrix.

    The matrix is descriptive only. Running live model calls is a separate,
    explicit step outside this module.
    """

    return {
        "experiment_id": EXPERIMENT_ID,
        "source_failure_run_id": FAILED_RUN_ID,
        "live_calls_per_condition": 3,
        "conditions": [
            {
                "condition_id": "A_original_prompt_strict_contract",
                "model": "deepseek/deepseek-v4-pro",
                "provider": "OpenRouter",
                "prompt_variant": "original_live_pilot_seed_prompt",
                "prompt_addendum_application": "system_message_suffix",
                "prompt_addendum": PROMPT_VARIANTS[
                    "original_live_pilot_seed_prompt"
                ]["addendum"],
                "contract": "strict_autonomous_action_v1",
                "acceptance_rule": "strict_parser_requires_open_item_kind_and_text",
            },
            {
                "condition_id": "B_example_prompt_strict_contract",
                "model": "deepseek/deepseek-v4-pro",
                "provider": "OpenRouter",
                "prompt_variant": "original_plus_one_valid_open_item_example",
                "prompt_addendum_application": "system_message_suffix",
                "prompt_addendum": PROMPT_VARIANTS[
                    "original_plus_one_valid_open_item_example"
                ]["addendum"],
                "contract": "strict_autonomous_action_v1",
                "acceptance_rule": "strict_parser_requires_open_item_kind_and_text",
            },
            {
                "condition_id": "C_schema_checklist_strict_contract",
                "model": "deepseek/deepseek-v4-pro",
                "provider": "OpenRouter",
                "prompt_variant": "original_plus_schema_and_checklist",
                "prompt_addendum_application": "system_message_suffix",
                "prompt_addendum": PROMPT_VARIANTS[
                    "original_plus_schema_and_checklist"
                ]["addendum"],
                "contract": "strict_autonomous_action_v1",
                "acceptance_rule": "strict_parser_requires_open_item_kind_and_text",
            },
            {
                "condition_id": "D_relaxed_open_item_contract",
                "model": "deepseek/deepseek-v4-pro",
                "provider": "OpenRouter",
                "prompt_variant": "relaxed_open_item_contract_counterfactual",
                "prompt_addendum_application": "system_message_suffix",
                "prompt_addendum": PROMPT_VARIANTS[
                    "relaxed_open_item_contract_counterfactual"
                ]["addendum"],
                "contract": "relaxed_open_item_counterfactual_v1",
                "acceptance_rule": (
                    "counterfactual_only: missing kind defaults to todo and "
                    "description may serve as text; no live harness repair"
                ),
            },
        ],
    }


def prompt_variants() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "variants": deepcopy(PROMPT_VARIANTS),
    }


def budget_manifest() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_execution_status": "not_authorized_by_this_artifact",
        "max_live_calls_if_later_authorized": 12,
        "max_calls_per_condition": 3,
        "max_cycles_per_call": 1,
        "max_output_tokens_per_call": None,
        "output_cap_policy": (
            "No artificial per-call output cap for research matrix calls; "
            "provider/model limits still apply."
        ),
        "max_total_tokens": 30000,
        "max_estimated_cost_usd": 1.00,
        "stop_rule": (
            "Stop the matrix immediately if a provider/protocol failure makes "
            "condition attribution impossible."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": "hamutay.contract_literacy_taxonomy.v1",
        "entries": [
            {
                "layer": "model",
                "code": "model_contract_literacy_failure",
                "meaning": (
                    "The model does not produce the required action structure "
                    "even after explicit examples and checklist presentation."
                ),
            },
            {
                "layer": "prompt_schema",
                "code": "presentation_sensitive_contract_failure",
                "meaning": (
                    "The original prompt fails but example or checklist "
                    "presentation satisfies the strict contract."
                ),
            },
            {
                "layer": "contract",
                "code": "strict_contract_rejects_semantic_action",
                "meaning": (
                    "The strict parser rejects a semantically usable action "
                    "that the preregistered relaxed contract would accept."
                ),
            },
            {
                "layer": "protocol",
                "code": "non_json_or_unparseable_action",
                "meaning": "The response cannot be parsed as an action object.",
            },
            {
                "layer": "provider",
                "code": "provider_call_failure",
                "meaning": "The provider fails before a model action can be scored.",
            },
            {
                "layer": "scorer",
                "code": "unscoreable_or_ambiguous_result",
                "meaning": (
                    "The preserved artifacts are insufficient to distinguish "
                    "model, prompt, or contract explanations."
                ),
            },
        ],
    }


def load_failed_cycle1_action_object(
    response_path: Path = FAILED_RUN_RESPONSE_PATH,
) -> JsonDict:
    """Load the failed live run's cycle-1 model-authored action object."""

    payload = json.loads(response_path.read_text())
    content = payload["choices"][0]["message"]["content"]
    action = json.loads(content)
    if not isinstance(action, dict):
        raise TypeError("cycle-1 provider content did not decode to an object")
    return action


def evaluate_cycle1_action_object(
    raw_output: Any,
    *,
    condition_id: str,
    relaxed_open_item_contract: bool = False,
) -> JsonDict:
    """Evaluate one cycle-1 action object without applying or repairing it."""

    if condition_id not in CONDITION_IDS:
        raise ValueError(f"unknown condition_id: {condition_id}")

    trace = parse_autonomous_action(raw_output).to_dict()
    accepted_types = {
        action["action_type"] for action in trace.get("accepted_actions", [])
    }
    rejection_paths = [
        rejection["source_path"] for rejection in trace.get("rejected_actions", [])
    ]
    open_item_rejections = [
        rejection
        for rejection in trace.get("rejected_actions", [])
        if rejection.get("action_type") == "open_item"
    ]
    strict_open_item_valid = "open_item" in accepted_types
    schedule_request_valid = "schedule_request" in accepted_types
    relaxed_open_item = evaluate_relaxed_open_items(raw_output)
    strict_required_actions_valid = strict_open_item_valid and schedule_request_valid
    relaxed_required_actions_valid = (
        schedule_request_valid and relaxed_open_item["would_accept"]
    )

    explanation_candidates: list[str] = []
    if strict_required_actions_valid:
        explanation_candidates.append("strict_contract_satisfied")
    elif not isinstance(raw_output, dict):
        explanation_candidates.append("protocol_or_provider_artifact_failure")
    elif relaxed_required_actions_valid and _only_missing_open_item_shape(
        open_item_rejections
    ):
        explanation_candidates.append("contract_underspecification_candidate")
    elif schedule_request_valid and open_item_rejections:
        explanation_candidates.append("prompt_or_model_contract_failure")
    else:
        explanation_candidates.append("model_contract_literacy_failure")

    return {
        "schema_version": "hamutay.contract_literacy_evaluation.v1",
        "experiment_id": EXPERIMENT_ID,
        "condition_id": condition_id,
        "relaxed_open_item_contract_enabled": relaxed_open_item_contract,
        "parse_status": trace["parse_status"],
        "validation_status": trace["validation_status"],
        "accepted_action_types": sorted(accepted_types),
        "rejection_paths": rejection_paths,
        "strict_open_item_valid": strict_open_item_valid,
        "schedule_request_valid": schedule_request_valid,
        "strict_required_actions_valid": strict_required_actions_valid,
        "relaxed_open_item": relaxed_open_item,
        "relaxed_required_actions_valid": relaxed_required_actions_valid
        if relaxed_open_item_contract
        else False,
        "normalization_applied": False,
        "explanation_candidates": explanation_candidates,
        "trace": trace,
    }


def evaluate_failed_run_fixture(
    response_path: Path = FAILED_RUN_RESPONSE_PATH,
) -> JsonDict:
    raw_output = load_failed_cycle1_action_object(response_path)
    strict = evaluate_cycle1_action_object(
        raw_output,
        condition_id="A_original_prompt_strict_contract",
        relaxed_open_item_contract=False,
    )
    relaxed = evaluate_cycle1_action_object(
        raw_output,
        condition_id="D_relaxed_open_item_contract",
        relaxed_open_item_contract=True,
    )
    if (
        not strict["strict_required_actions_valid"]
        and relaxed["relaxed_required_actions_valid"]
    ):
        primary_interpretation = "contract_underspecification_candidate"
    else:
        primary_interpretation = "not_explained_by_relaxed_open_item_contract"
    return {
        "schema_version": "hamutay.contract_literacy_fixture.v1",
        "experiment_id": EXPERIMENT_ID,
        "source_run_id": FAILED_RUN_ID,
        "source_response_path": str(response_path),
        "primary_interpretation": primary_interpretation,
        "strict_evaluation": strict,
        "relaxed_counterfactual": relaxed,
    }


def write_no_live_artifacts(output_dir: Path) -> JsonDict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": condition_matrix(),
        "prompt_variants.json": prompt_variants(),
        "budget.json": budget_manifest(),
        "failure_taxonomy.json": failure_taxonomy(),
        "fixture_failed_live_run_cycle1_evaluation.json": (
            evaluate_failed_run_fixture()
        ),
    }
    for name, payload in artifacts.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "artifacts": sorted(artifacts),
    }


def evaluate_relaxed_open_items(raw_output: Any) -> JsonDict:
    """Score the preregistered relaxed-open-item counterfactual.

    This does not mutate or repair the model output. It only records whether a
    looser contract would have had enough authored information to proceed.
    """

    if not isinstance(raw_output, dict):
        return {
            "would_accept": False,
            "reason": "raw_output_not_object",
            "items": [],
        }
    value = raw_output.get("open_items")
    if not isinstance(value, list) or not value:
        return {
            "would_accept": False,
            "reason": "open_items_missing_or_not_array",
            "items": [],
        }

    items = [_relaxed_open_item_candidate(item, index) for index, item in enumerate(value)]
    return {
        "would_accept": all(item["would_accept"] for item in items),
        "reason": "all_open_items_relaxed_acceptable"
        if all(item["would_accept"] for item in items)
        else "one_or_more_open_items_relaxed_rejected",
        "items": items,
    }


def _relaxed_open_item_candidate(item: Any, index: int) -> JsonDict:
    path = f"$.open_items[{index}]"
    if not isinstance(item, dict):
        return {
            "path": path,
            "would_accept": False,
            "reason": "not_object",
            "normalization_required": False,
        }

    kind = item.get("kind")
    text = item.get("text")
    description = item.get("description")
    normalized: JsonDict = deepcopy(item)
    missing_fields: list[str] = []
    source_fields = sorted(str(key) for key in item)

    if not isinstance(kind, str) or not kind.strip():
        normalized["kind"] = "todo"
        missing_fields.append("kind")
    if not isinstance(text, str) or not text.strip():
        if isinstance(description, str) and description.strip():
            normalized["text"] = description
            missing_fields.append("text")
        else:
            return {
                "path": path,
                "would_accept": False,
                "reason": "missing_text_and_description",
                "normalization_required": bool(missing_fields),
                "missing_fields": missing_fields + ["text"],
                "source_fields": source_fields,
            }

    return {
        "path": path,
        "would_accept": True,
        "reason": "strict_shape_or_relaxed_description_mapping_available",
        "normalization_required": bool(missing_fields),
        "missing_fields": missing_fields,
        "source_fields": source_fields,
        "normalized_candidate": normalized,
    }


def _only_missing_open_item_shape(rejections: list[JsonDict]) -> bool:
    if not rejections:
        return False
    allowed_paths = {".kind", ".text"}
    return all(
        rejection.get("code") == "invalid_field"
        and any(str(rejection.get("source_path", "")).endswith(path) for path in allowed_paths)
        for rejection in rejections
    )


def build_condition_messages(
    condition: JsonDict,
    *,
    repetition: int,
) -> list[JsonDict]:
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


def execute_live_matrix(
    *,
    output_dir: Path = DEFAULT_LIVE_OUTPUT_DIR,
    api_key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    timeout_seconds: float = 120.0,
) -> JsonDict:
    """Execute the preregistered one-cycle live matrix."""

    if not api_key:
        raise ValueError("api_key is required for live matrix execution")

    output_dir.mkdir(parents=True, exist_ok=False)
    rows_dir = output_dir / "rows"
    rows_dir.mkdir()

    matrix = condition_matrix()
    budget = budget_manifest()
    live_calls = int(matrix["live_calls_per_condition"])
    planned_rows = len(matrix["conditions"]) * live_calls
    if planned_rows > int(budget["max_live_calls_if_later_authorized"]):
        raise ValueError("matrix exceeds preregistered live-call budget")

    started_at = _now_iso()
    static_artifacts = {
        "matrix.json": matrix,
        "prompt_variants.json": prompt_variants(),
        "budget.json": budget,
        "failure_taxonomy.json": failure_taxonomy(),
    }
    for name, payload in static_artifacts.items():
        _write_json(output_dir / name, payload)

    row_results: list[JsonDict] = []
    for condition in matrix["conditions"]:
        for repetition in range(1, live_calls + 1):
            row_result = execute_live_matrix_row(
                condition=condition,
                repetition=repetition,
                rows_dir=rows_dir,
                api_key=api_key,
                endpoint=endpoint,
                model=model,
                timeout_seconds=timeout_seconds,
            )
            row_results.append(row_result)
            totals = _usage_totals(row_results)
            if totals["total_tokens"] > int(budget["max_total_tokens"]):
                break
            if totals["estimated_cost_usd"] > float(budget["max_estimated_cost_usd"]):
                break

    summary = summarize_matrix_results(
        row_results=row_results,
        started_at=started_at,
        finished_at=_now_iso(),
        output_dir=output_dir,
        endpoint=endpoint,
        model=model,
    )
    _write_json(output_dir / "results.json", summary)
    (output_dir / "analysis.md").write_text(render_analysis(summary))
    return summary


def execute_live_matrix_row(
    *,
    condition: JsonDict,
    repetition: int,
    rows_dir: Path,
    api_key: str,
    endpoint: str,
    model: str,
    timeout_seconds: float,
) -> JsonDict:
    condition_id = str(condition["condition_id"])
    row_id = f"{condition_id}_r{repetition:02d}"
    row_dir = rows_dir / row_id
    row_dir.mkdir()
    messages = build_condition_messages(condition, repetition=repetition)
    provider = call_openrouter_action(
        api_key=api_key,
        endpoint=endpoint,
        model=model,
        messages=messages,
        timeout_seconds=timeout_seconds,
    )

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
        condition_id=condition_id,
        relaxed_open_item_contract=False,
    )
    relaxed_evaluation = evaluate_cycle1_action_object(
        raw_output,
        condition_id=condition_id,
        relaxed_open_item_contract=True,
    )
    row_result = {
        "schema_version": "hamutay.contract_literacy_row.v1",
        "experiment_id": EXPERIMENT_ID,
        "row_id": row_id,
        "condition_id": condition_id,
        "repetition": repetition,
        "condition": deepcopy(condition),
        "provider_ok": provider["ok"],
        "provider_failure": provider.get("failure"),
        "raw_content": provider.get("raw_content"),
        "usage": provider.get("usage", {}),
        "elapsed_seconds": provider.get("elapsed_seconds"),
        "provider_attempts": provider.get("attempts", []),
        "strict_evaluation": strict_evaluation,
        "relaxed_evaluation": relaxed_evaluation,
    }
    _write_json(row_dir / "strict_evaluation.json", strict_evaluation)
    _write_json(row_dir / "relaxed_evaluation.json", relaxed_evaluation)
    _write_json(row_dir / "row_result.json", row_result)
    return row_result


def call_openrouter_action(
    *,
    api_key: str,
    endpoint: str,
    model: str,
    messages: list[JsonDict],
    timeout_seconds: float,
    max_attempts: int = DEFAULT_PROVIDER_RETRY_ATTEMPTS,
    retry_sleep_cap_seconds: float = DEFAULT_PROVIDER_RETRY_SLEEP_CAP_SECONDS,
    sleep: Any = time.sleep,
    include_openrouter_options: bool = True,
) -> JsonDict:
    payload: JsonDict = {
        "model": model,
        "messages": deepcopy(messages),
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if include_openrouter_options:
        payload["provider"] = {"allow_fallbacks": False}
        payload["transforms"] = []
    started = time.monotonic()
    attempts: list[JsonDict] = []
    response_payload: JsonDict = {}
    elapsed = 0.0
    max_attempts = max(1, int(max_attempts))

    for attempt_index in range(1, max_attempts + 1):
        attempt_started = time.monotonic()
        try:
            response = httpx.post(
                f"{endpoint.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_seconds,
            )
            attempt_elapsed = time.monotonic() - attempt_started
            elapsed = time.monotonic() - started
            try:
                response_payload = response.json()
            except json.JSONDecodeError:
                response_payload = {"raw_text": response.text}
            retry_after = _retry_after_seconds(response, response_payload)
            transient = response.status_code in TRANSIENT_PROVIDER_STATUS_CODES
            attempts.append(
                {
                    "attempt": attempt_index,
                    "status_code": response.status_code,
                    "elapsed_seconds": attempt_elapsed,
                    "transient": transient,
                    "retry_after_seconds": retry_after,
                    "will_retry": (
                        response.status_code >= 400
                        and transient
                        and attempt_index < max_attempts
                    ),
                    "response_payload": response_payload,
                }
            )
            if response.status_code < 400:
                break
            if transient and attempt_index < max_attempts:
                sleep(_bounded_retry_delay(attempt_index, retry_after, retry_sleep_cap_seconds))
                continue
            return _provider_failure_result(
                payload=payload,
                code="provider_api_error",
                message="provider returned HTTP error",
                response_payload=response_payload,
                elapsed_seconds=elapsed,
                attempts=attempts,
                status_code=response.status_code,
            )
        except httpx.TimeoutException as exc:
            elapsed = time.monotonic() - started
            attempts.append(
                {
                    "attempt": attempt_index,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "transient": True,
                    "will_retry": attempt_index < max_attempts,
                }
            )
            if attempt_index < max_attempts:
                sleep(_bounded_retry_delay(attempt_index, None, retry_sleep_cap_seconds))
                continue
            return _provider_failure_result(
                payload=payload,
                code="provider_budget_or_timeout",
                message=str(exc),
                elapsed_seconds=elapsed,
                attempts=attempts,
            )
        except httpx.HTTPError as exc:
            elapsed = time.monotonic() - started
            attempts.append(
                {
                    "attempt": attempt_index,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "transient": True,
                    "will_retry": attempt_index < max_attempts,
                }
            )
            if attempt_index < max_attempts:
                sleep(_bounded_retry_delay(attempt_index, None, retry_sleep_cap_seconds))
                continue
            return _provider_failure_result(
                payload=payload,
                code="provider_api_error",
                message=str(exc),
                elapsed_seconds=elapsed,
                attempts=attempts,
            )

    raw_content = extract_openai_content(response_payload)
    action_object: JsonDict | None = None
    failure: JsonDict | None = None
    try:
        candidate = json.loads(raw_content)
        if isinstance(candidate, dict):
            action_object = candidate
        else:
            failure = {
                "layer": "protocol",
                "code": "invalid_action_schema",
                "message": "provider JSON content was not an object",
            }
    except json.JSONDecodeError:
        failure = {
            "layer": "protocol",
            "code": "invalid_action_schema",
            "message": "provider content was not JSON",
        }

    usage = response_payload.get("usage")
    return {
        "ok": failure is None,
        "failure": failure,
        "request_payload": payload,
        "response_payload": response_payload,
        "raw_content": raw_content,
        "action_object": action_object,
        "elapsed_seconds": elapsed,
        "attempts": attempts,
        "usage": deepcopy(usage if isinstance(usage, dict) else {}),
    }


def call_anthropic_messages_action(
    *,
    api_key: str,
    endpoint: str,
    model: str,
    messages: list[JsonDict],
    timeout_seconds: float,
    max_attempts: int = DEFAULT_PROVIDER_RETRY_ATTEMPTS,
    retry_sleep_cap_seconds: float = DEFAULT_PROVIDER_RETRY_SLEEP_CAP_SECONDS,
    sleep: Any = time.sleep,
    max_tokens: int = DEFAULT_ANTHROPIC_MESSAGES_MAX_TOKENS,
    tool_choice: JsonDict | None = None,
) -> JsonDict:
    system_parts = [
        str(message.get("content", ""))
        for message in messages
        if message.get("role") == "system"
    ]
    anthropic_messages = [
        {"role": message.get("role"), "content": str(message.get("content", ""))}
        for message in messages
        if message.get("role") in {"user", "assistant"}
    ]
    payload: JsonDict = {
        "model": model,
        "max_tokens": int(max_tokens),
        "temperature": 0,
        "system": "\n\n".join(system_parts),
        "messages": anthropic_messages,
        "tools": [
            {
                "name": "submit_action_object",
                "description": (
                    "Submit the single structured action object requested by "
                    "the harness."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "The response visible to the user.",
                        }
                    },
                    "required": ["response"],
                    "additionalProperties": True,
                },
            }
        ],
    }
    if tool_choice is None:
        payload["tool_choice"] = {"type": "tool", "name": "submit_action_object"}
    elif tool_choice:
        payload["tool_choice"] = deepcopy(tool_choice)
    started = time.monotonic()
    attempts: list[JsonDict] = []
    response_payload: JsonDict = {}
    elapsed = 0.0
    max_attempts = max(1, int(max_attempts))

    for attempt_index in range(1, max_attempts + 1):
        attempt_started = time.monotonic()
        try:
            response = httpx.post(
                f"{endpoint.rstrip('/')}/v1/messages",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=timeout_seconds,
            )
            attempt_elapsed = time.monotonic() - attempt_started
            elapsed = time.monotonic() - started
            try:
                response_payload = response.json()
            except json.JSONDecodeError:
                response_payload = {"raw_text": response.text}
            retry_after = _retry_after_seconds(response, response_payload)
            transient = response.status_code in TRANSIENT_PROVIDER_STATUS_CODES
            attempts.append(
                {
                    "attempt": attempt_index,
                    "status_code": response.status_code,
                    "elapsed_seconds": attempt_elapsed,
                    "transient": transient,
                    "retry_after_seconds": retry_after,
                    "will_retry": (
                        response.status_code >= 400
                        and transient
                        and attempt_index < max_attempts
                    ),
                    "response_payload": response_payload,
                }
            )
            if response.status_code < 400:
                break
            if transient and attempt_index < max_attempts:
                sleep(_bounded_retry_delay(attempt_index, retry_after, retry_sleep_cap_seconds))
                continue
            return _provider_failure_result(
                payload=payload,
                code="provider_api_error",
                message="provider returned HTTP error",
                response_payload=response_payload,
                elapsed_seconds=elapsed,
                attempts=attempts,
                status_code=response.status_code,
            )
        except httpx.TimeoutException as exc:
            elapsed = time.monotonic() - started
            attempts.append(
                {
                    "attempt": attempt_index,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "transient": True,
                    "will_retry": attempt_index < max_attempts,
                }
            )
            if attempt_index < max_attempts:
                sleep(_bounded_retry_delay(attempt_index, None, retry_sleep_cap_seconds))
                continue
            return _provider_failure_result(
                payload=payload,
                code="provider_budget_or_timeout",
                message=str(exc),
                elapsed_seconds=elapsed,
                attempts=attempts,
            )
        except httpx.HTTPError as exc:
            elapsed = time.monotonic() - started
            attempts.append(
                {
                    "attempt": attempt_index,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "transient": True,
                    "will_retry": attempt_index < max_attempts,
                }
            )
            if attempt_index < max_attempts:
                sleep(_bounded_retry_delay(attempt_index, None, retry_sleep_cap_seconds))
                continue
            return _provider_failure_result(
                payload=payload,
                code="provider_api_error",
                message=str(exc),
                elapsed_seconds=elapsed,
                attempts=attempts,
            )

    action_object, raw_content = extract_anthropic_tool_action(response_payload)
    failure: JsonDict | None = None
    if action_object is None:
        try:
            candidate = json.loads(raw_content)
            if isinstance(candidate, dict):
                action_object = candidate
            else:
                failure = {
                    "layer": "protocol",
                    "code": "invalid_action_schema",
                    "message": "provider JSON content was not an object",
                }
        except json.JSONDecodeError:
            failure = {
                "layer": "protocol",
                "code": "invalid_action_schema",
                "message": "provider content was not JSON or tool input",
            }

    return {
        "ok": failure is None,
        "failure": failure,
        "request_payload": payload,
        "response_payload": response_payload,
        "raw_content": raw_content,
        "action_object": action_object,
        "elapsed_seconds": elapsed,
        "attempts": attempts,
        "usage": _normalize_anthropic_usage(response_payload.get("usage")),
    }


def extract_openai_content(response_payload: JsonDict) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
        )
    return ""


def extract_anthropic_tool_action(
    response_payload: JsonDict,
) -> tuple[JsonDict | None, str]:
    content = response_payload.get("content")
    text_parts: list[str] = []
    if not isinstance(content, list):
        return None, ""
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "tool_use" and part.get("name") == "submit_action_object":
            tool_input = part.get("input")
            if isinstance(tool_input, dict):
                return deepcopy(tool_input), json.dumps(tool_input, sort_keys=True)
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            text_parts.append(str(part["text"]))
    return None, "".join(text_parts)


def _normalize_anthropic_usage(usage: Any) -> JsonDict:
    if not isinstance(usage, dict):
        return {}
    normalized = deepcopy(usage)
    input_tokens = int(normalized.get("input_tokens", 0) or 0)
    output_tokens = int(normalized.get("output_tokens", 0) or 0)
    normalized["prompt_tokens"] = input_tokens
    normalized["completion_tokens"] = output_tokens
    normalized["total_tokens"] = input_tokens + output_tokens
    return normalized


def summarize_matrix_results(
    *,
    row_results: list[JsonDict],
    started_at: str,
    finished_at: str,
    output_dir: Path,
    endpoint: str,
    model: str,
) -> JsonDict:
    by_condition: dict[str, JsonDict] = {}
    for row in row_results:
        condition_id = str(row["condition_id"])
        condition = by_condition.setdefault(
            condition_id,
            {
                "condition_id": condition_id,
                "rows": 0,
                "provider_failures": 0,
                "protocol_failures": 0,
                "strict_pass_count": 0,
                "relaxed_pass_count": 0,
                "strict_fail_relaxed_pass_count": 0,
                "rejection_paths": {},
                "explanation_candidates": {},
            },
        )
        condition["rows"] += 1
        provider_failure = row.get("provider_failure")
        if not isinstance(provider_failure, dict):
            provider_failure = {}
        if provider_failure.get("layer") == "provider":
            condition["provider_failures"] += 1
        if provider_failure.get("layer") == "protocol":
            condition["protocol_failures"] += 1

        strict = row["strict_evaluation"]
        relaxed = row["relaxed_evaluation"]
        if strict["strict_required_actions_valid"]:
            condition["strict_pass_count"] += 1
        if relaxed["relaxed_required_actions_valid"]:
            condition["relaxed_pass_count"] += 1
        if (
            not strict["strict_required_actions_valid"]
            and relaxed["relaxed_required_actions_valid"]
        ):
            condition["strict_fail_relaxed_pass_count"] += 1
        _count_values(condition["rejection_paths"], strict["rejection_paths"])
        _count_values(
            condition["explanation_candidates"],
            strict["explanation_candidates"],
        )

    totals = _usage_totals(row_results)
    hypothesis_assessment = assess_hypotheses(by_condition)
    return {
        "schema_version": "hamutay.contract_literacy_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": finished_at,
        "live_model_calls": True,
        "output_dir": str(output_dir),
        "endpoint": endpoint,
        "model": model,
        "row_count": len(row_results),
        "usage_totals": totals,
        "budget": budget_manifest(),
        "by_condition": by_condition,
        "hypothesis_assessment": hypothesis_assessment,
        "row_result_paths": [
            str(Path("rows") / row["row_id"] / "row_result.json")
            for row in row_results
        ],
    }


def assess_hypotheses(by_condition: dict[str, JsonDict]) -> JsonDict:
    original = by_condition.get("A_original_prompt_strict_contract", {})
    example = by_condition.get("B_example_prompt_strict_contract", {})
    checklist = by_condition.get("C_schema_checklist_strict_contract", {})
    relaxed = by_condition.get("D_relaxed_open_item_contract", {})

    original_passes = int(original.get("strict_pass_count", 0))
    example_passes = int(example.get("strict_pass_count", 0))
    checklist_passes = int(checklist.get("strict_pass_count", 0))
    relaxed_counterfactual_passes = sum(
        int(condition.get("strict_fail_relaxed_pass_count", 0))
        for condition in by_condition.values()
    )
    strict_failures = sum(
        int(condition.get("rows", 0)) - int(condition.get("strict_pass_count", 0))
        for condition in by_condition.values()
    )

    presentation_sensitive = (
        original_passes < 2 and (example_passes >= 2 or checklist_passes >= 2)
    )
    model_fragility_survives = example_passes < 2 and checklist_passes < 2
    contract_underspecification_survives = (
        strict_failures > 0 and relaxed_counterfactual_passes >= 2
    )
    return {
        "H1_model_fragility": "survives"
        if model_fragility_survives
        else "weakened",
        "H2_prompt_schema_presentation": "survives"
        if presentation_sensitive
        else "weakened",
        "H3_contract_underspecification": "survives"
        if contract_underspecification_survives
        else "weakened",
        "H4_no_autonomy_claim_from_literacy": "retained",
        "basis": {
            "original_strict_passes": original_passes,
            "example_strict_passes": example_passes,
            "checklist_strict_passes": checklist_passes,
            "relaxed_condition_strict_passes": int(relaxed.get("strict_pass_count", 0)),
            "strict_failures": strict_failures,
            "strict_fail_relaxed_passes": relaxed_counterfactual_passes,
        },
    }


def render_analysis(summary: JsonDict) -> str:
    lines = [
        "# Action-Object Contract Literacy Matrix Analysis",
        "",
        f"Experiment ID: `{summary['experiment_id']}`",
        "",
        "## Execution",
        "",
        f"- Started: `{summary['started_at']}`",
        f"- Finished: `{summary['finished_at']}`",
        f"- Model: `{summary['model']}`",
        f"- Endpoint: `{summary['endpoint']}`",
        f"- Rows: {summary['row_count']}",
        f"- Total tokens: {summary['usage_totals']['total_tokens']}",
        f"- Estimated cost USD: {summary['usage_totals']['estimated_cost_usd']:.6f}",
        "",
        "## Condition Counts",
        "",
        "| Condition | Rows | Strict pass | Relaxed pass | Strict fail / relaxed pass | Provider failures | Protocol failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition_id in CONDITION_IDS:
        condition = summary["by_condition"].get(condition_id, {})
        lines.append(
            "| {condition_id} | {rows} | {strict} | {relaxed} | {mixed} | "
            "{provider} | {protocol} |".format(
                condition_id=condition_id,
                rows=condition.get("rows", 0),
                strict=condition.get("strict_pass_count", 0),
                relaxed=condition.get("relaxed_pass_count", 0),
                mixed=condition.get("strict_fail_relaxed_pass_count", 0),
                provider=condition.get("provider_failures", 0),
                protocol=condition.get("protocol_failures", 0),
            )
        )

    assessment = summary["hypothesis_assessment"]
    lines.extend(
        [
            "",
            "## Hypothesis Assessment",
            "",
            f"- H1 model fragility: `{assessment['H1_model_fragility']}`",
            "- H2 prompt/schema presentation: "
            f"`{assessment['H2_prompt_schema_presentation']}`",
            "- H3 contract underspecification: "
            f"`{assessment['H3_contract_underspecification']}`",
            "- H4 no autonomy claim from literacy: "
            f"`{assessment['H4_no_autonomy_claim_from_literacy']}`",
            "",
            "Basis:",
            "",
        ]
    )
    for key, value in assessment["basis"].items():
        lines.append(f"- `{key}`: {value}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            _interpret_summary(summary),
            "",
            "## Artifact Trail",
            "",
            "- `results.json` contains the aggregate machine-readable result.",
            "- `analysis.md` is this analysis artifact.",
            "- `rows/<row_id>/provider_request.json` preserves each request.",
            "- `rows/<row_id>/provider_response.json` preserves each response.",
            "- `rows/<row_id>/strict_evaluation.json` preserves strict scoring.",
            "- `rows/<row_id>/relaxed_evaluation.json` preserves relaxed scoring.",
            "- `rows/<row_id>/row_result.json` ties each row together.",
            "",
        ]
    )
    return "\n".join(lines)


def _interpret_summary(summary: JsonDict) -> str:
    assessment = summary["hypothesis_assessment"]
    h1 = assessment["H1_model_fragility"]
    h2 = assessment["H2_prompt_schema_presentation"]
    h3 = assessment["H3_contract_underspecification"]
    if h2 == "survives" and h3 == "survives":
        return (
            "The failure is best treated as a two-layer boundary. The strict "
            "contract failure is prompt/schema-presentation sensitive because "
            "both the example and checklist conditions satisfied the strict "
            "contract. It is also contract-sensitive because every strict "
            "failure contained enough authored structure for the preregistered "
            "relaxed counterfactual to score it as usable without applying "
            "hidden repair. Model fragility is weakened, not eliminated as a "
            "general possibility."
        )
    if h2 == "survives":
        return (
            "The failure is best treated as prompt/schema-presentation sensitive: "
            "the original condition did not reliably satisfy the strict contract, "
            "while an explicit example or checklist did."
        )
    if h1 == "survives" and h3 == "survives":
        return (
            "The failure remains a boundary case: DeepSeek did not reliably "
            "satisfy the strict action contract after prompt hardening, while "
            "relaxed scoring found semantically usable rejected actions. This "
            "keeps both model fragility and contract underspecification in play."
        )
    if h1 == "survives":
        return (
            "The failure is best treated as a model-action literacy limitation "
            "for this model under the current action-object pattern."
        )
    if h3 == "survives":
        return (
            "The failure is best treated as contract-sensitive: strict scoring "
            "rejected outputs that the preregistered relaxed counterfactual "
            "could score as usable without applying hidden repair."
        )
    return (
        "The matrix weakened the preregistered explanations or produced an "
        "ambiguous pattern. Inspect row artifacts before using this result to "
        "choose the next live autonomy condition."
    )


def _provider_failure_result(
    *,
    payload: JsonDict,
    code: str,
    message: str,
    response_payload: JsonDict | None = None,
    elapsed_seconds: float | None = None,
    attempts: list[JsonDict] | None = None,
    status_code: int | None = None,
) -> JsonDict:
    failure: JsonDict = {
        "layer": "provider",
        "code": code,
        "message": message,
    }
    if status_code is not None:
        failure["status_code"] = status_code
    return {
        "ok": False,
        "failure": failure,
        "request_payload": payload,
        "response_payload": response_payload or {},
        "raw_content": None,
        "action_object": None,
        "elapsed_seconds": elapsed_seconds,
        "attempts": attempts or [],
        "usage": {},
    }


def _retry_after_seconds(response: httpx.Response, response_payload: JsonDict) -> float | None:
    header_value = response.headers.get("Retry-After")
    if header_value is not None:
        parsed = _parse_retry_after_seconds(header_value)
        if parsed is not None:
            return parsed

    error = response_payload.get("error")
    if not isinstance(error, dict):
        return None
    metadata = error.get("metadata")
    if not isinstance(metadata, dict):
        return None

    for key in ("retry_after_seconds", "retry_after_seconds_raw"):
        value = metadata.get(key)
        if value is not None:
            parsed = _parse_retry_after_seconds(value)
            if parsed is not None:
                return parsed

    headers = metadata.get("headers")
    if isinstance(headers, dict):
        for key, value in headers.items():
            if str(key).lower() == "retry-after":
                return _parse_retry_after_seconds(value)
    return None


def _parse_retry_after_seconds(value: Any) -> float | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return seconds


def _bounded_retry_delay(
    attempt_index: int,
    retry_after_seconds: float | None,
    cap_seconds: float,
) -> float:
    cap_seconds = max(0.0, float(cap_seconds))
    if retry_after_seconds is not None:
        return min(retry_after_seconds, cap_seconds)
    return min(float(2 ** max(0, attempt_index - 1)), cap_seconds)


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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    args = parser.parse_args()

    if args.run_live:
        api_key = os.environ.get(args.api_key_env, "")
        result = execute_live_matrix(
            output_dir=args.output_dir or DEFAULT_LIVE_OUTPUT_DIR,
            api_key=api_key,
            endpoint=args.endpoint,
            model=args.model,
        )
    else:
        output_dir = args.output_dir or DEFAULT_EXPERIMENT_DIR
        result = write_no_live_artifacts(output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
