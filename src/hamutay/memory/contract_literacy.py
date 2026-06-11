"""No-live evaluator for action-object contract literacy experiments."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from hamutay.memory.actions import parse_autonomous_action


JsonDict = dict[str, Any]

EXPERIMENT_ID = "action_object_contract_literacy_20260610"
FAILED_RUN_ID = "c39ba9a3-9dda-48f2-82f6-cb90f8229bae"
FAILED_RUN_RESPONSE_PATH = Path(
    "experiments/live_autonomy_pilot_20260609/runs"
) / FAILED_RUN_ID / "cycle_01_provider_response.json"

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


def main() -> None:
    output_dir = Path("experiments") / EXPERIMENT_ID
    result = write_no_live_artifacts(output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
