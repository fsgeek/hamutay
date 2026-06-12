"""Reusable row-level attribution for model action/control experiments."""

from __future__ import annotations

from typing import Any


JsonDict = dict[str, Any]


def classify_action_row_failure(row: JsonDict) -> JsonDict:
    """Classify one row without mutating primary scoring.

    The classifier is intentionally conservative. It reports the layer most
    directly supported by preserved row artifacts; it does not reinterpret a
    primary strict failure as success.
    """

    strict = row.get("strict_evaluation", {})
    relaxed = row.get("relaxed_evaluation", {})
    strict_pass = bool(strict.get("strict_required_actions_valid"))
    relaxed_pass = bool(relaxed.get("relaxed_required_actions_valid"))
    failure = row.get("provider_failure")
    recovery = row.get("recovery_evaluation")

    if strict_pass:
        return _result(
            row,
            "passed_primary_strict",
            "Primary strict evaluation accepted the row.",
        )

    if isinstance(failure, dict) and failure.get("layer") == "provider":
        return _result(
            row,
            "provider_substrate_failure",
            "Provider error prevented model-authored content from being preserved.",
        )

    if isinstance(failure, dict) and failure.get("layer") == "protocol":
        return _classify_protocol_failure(row, recovery)

    rejection_paths = _rejection_paths(strict)
    rejection_codes = _rejection_codes(strict)
    if _has_only_schedule_shape_failure(rejection_paths, rejection_codes):
        return _result(
            row,
            "model_contract_boundary",
            "The model returned parseable JSON but failed a required nested schedule_request shape.",
        )
    if _has_open_item_shape_failure(rejection_paths):
        return _result(
            row,
            "prompt_schema_contract",
            "The model returned parseable JSON but did not make the required open_item shape salient.",
        )
    if relaxed_pass:
        return _result(
            row,
            "prompt_schema_contract",
            "Relaxed scoring found usable structure, but primary strict contract shape failed.",
        )
    if strict.get("parse_status") == "parsed":
        return _result(
            row,
            "model_contract_boundary",
            "The model returned parseable JSON, but it failed the required action contract under strict and relaxed scoring.",
        )
    return _result(
        row,
        "inconclusive",
        "The row did not preserve enough evidence for sharper attribution.",
    )


def _classify_protocol_failure(row: JsonDict, recovery: Any) -> JsonDict:
    raw = row.get("raw_content")
    if isinstance(recovery, dict) and recovery.get("strict_pass_if_recovered"):
        return _result(
            row,
            "parser_recovery_boundary",
            "Primary parser rejected the visible content, but secondary recovery found a strict-valid action object.",
        )
    if isinstance(raw, str) and not raw.strip():
        return _result(
            row,
            "prompt_transport_contract",
            "Provider returned no visible JSON content even though the call completed.",
        )
    if isinstance(recovery, dict) and recovery.get("recovered"):
        return _result(
            row,
            "prompt_transport_contract",
            "Secondary recovery found embedded JSON, but not a complete strict-valid action object.",
        )
    return _result(
        row,
        "protocol_transport_failure",
        "Primary parser rejected provider content and secondary recovery found no strict-valid action object.",
    )


def _rejection_paths(evaluation: JsonDict) -> set[str]:
    paths = evaluation.get("rejection_paths")
    if isinstance(paths, list):
        return {str(path) for path in paths}
    return set()


def _rejection_codes(evaluation: JsonDict) -> set[str]:
    trace = evaluation.get("trace")
    if not isinstance(trace, dict):
        return set()
    rejected = trace.get("rejected_actions")
    if not isinstance(rejected, list):
        return set()
    return {
        str(item.get("code"))
        for item in rejected
        if isinstance(item, dict) and item.get("code")
    }


def _has_only_schedule_shape_failure(paths: set[str], codes: set[str]) -> bool:
    if not paths:
        return False
    return all(path.startswith("$.schedule_requests") for path in paths) and (
        not codes or codes <= {"invalid_schedule_request"}
    )


def _has_open_item_shape_failure(paths: set[str]) -> bool:
    return any(path.startswith("$.open_items") for path in paths)


def _result(row: JsonDict, attribution: str, rationale: str) -> JsonDict:
    return {
        "row_id": row.get("row_id"),
        "prompt_condition": row.get("prompt_condition"),
        "primary_attribution": attribution,
        "rationale": rationale,
    }
