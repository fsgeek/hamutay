"""Model-authored autonomous action parsing and validation.

This module is deliberately non-mutating. It translates raw model output into
an audit trace of accepted and rejected action candidates, but it does not write
memory records, schedule events, or close work. Phase 3 owns application.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from hamutay.events import VALID_POLICY_ACTIONS, validate_requested_context
from hamutay.memory.bridge import CLOSING_STATUSES, OPEN_CONTENT_FIELDS


JsonDict = dict[str, Any]

AUTONOMOUS_ACTION_SCHEMA_VERSION = "autonomous_action.v1"
ACTION_FIELDS = {
    "response",
    "open_items",
    "closures",
    "schedule_requests",
    "policy_action",
    "declared_losses",
    "uncertainty",
    "abandonment_reason",
    "defer_reason",
}

AUTONOMOUS_ACTION_SCHEMA: JsonDict = {
    "schema_version": AUTONOMOUS_ACTION_SCHEMA_VERSION,
    "type": "object",
    "required": ["response"],
    "properties": {
        "response": {"type": "string"},
        "open_items": {"type": "array", "items": {"type": "object"}},
        "closures": {"type": "array", "items": {"type": "object"}},
        "schedule_requests": {"type": "array", "items": {"type": "object"}},
        "policy_action": {
            "type": "string",
            "enum": sorted(VALID_POLICY_ACTIONS),
        },
        "declared_losses": {"type": "array"},
        "uncertainty": {"type": ["array", "object", "string"]},
        "abandonment_reason": {"type": "string"},
        "defer_reason": {"type": "string"},
    },
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ActionCandidate:
    action_type: str
    parameters: JsonDict
    source_path: str

    def to_dict(self) -> JsonDict:
        return {
            "action_type": self.action_type,
            "parameters": deepcopy(self.parameters),
            "source_path": self.source_path,
        }


@dataclass(frozen=True)
class ActionRejection:
    action_type: str
    source_path: str
    code: str
    message: str
    value: Any = None
    suggested_repair: JsonDict | None = None

    def to_dict(self) -> JsonDict:
        result = {
            "action_type": self.action_type,
            "source_path": self.source_path,
            "code": self.code,
            "message": self.message,
            "value": deepcopy(self.value),
        }
        if self.suggested_repair is not None:
            result["suggested_repair"] = deepcopy(self.suggested_repair)
        return result


@dataclass(frozen=True)
class ActionTrace:
    schema_version: str
    raw_output: Any
    parsed_action: JsonDict | None
    parse_status: str
    validation_status: str
    accepted_actions: list[ActionCandidate] = field(default_factory=list)
    rejected_actions: list[ActionRejection] = field(default_factory=list)
    repair_proposal: JsonDict | None = None

    def to_dict(self) -> JsonDict:
        result = {
            "schema_version": self.schema_version,
            "raw_output": deepcopy(self.raw_output),
            "parsed_action": deepcopy(self.parsed_action),
            "parse_status": self.parse_status,
            "validation_status": self.validation_status,
            "accepted_actions": [
                action.to_dict() for action in self.accepted_actions
            ],
            "rejected_actions": [
                rejection.to_dict() for rejection in self.rejected_actions
            ],
            "rejection_reasons": [
                rejection.to_dict() for rejection in self.rejected_actions
            ],
        }
        if self.repair_proposal is not None:
            result["repair_proposal"] = deepcopy(self.repair_proposal)
        return result


def parse_autonomous_action(raw_output: Any) -> ActionTrace:
    """Parse and validate a model-authored autonomous action object.

    Unknown fields are rejected and logged rather than interpreted. Invalid
    subactions are rejected individually. The whole action is rejected when the
    required visible response is missing or malformed.
    """

    if not isinstance(raw_output, dict):
        return ActionTrace(
            schema_version=AUTONOMOUS_ACTION_SCHEMA_VERSION,
            raw_output=deepcopy(raw_output),
            parsed_action=None,
            parse_status="failed",
            validation_status="rejected",
            rejected_actions=[
                ActionRejection(
                    action_type="action_object",
                    source_path="$",
                    code="not_object",
                    message="autonomous action output must be an object",
                    value=raw_output,
                )
            ],
        )

    accepted: list[ActionCandidate] = []
    rejected: list[ActionRejection] = []
    parsed: JsonDict = {}
    response_valid = _validate_response(raw_output, parsed, accepted, rejected)
    _validate_unknown_fields(raw_output, rejected)
    _validate_open_items(raw_output, parsed, accepted, rejected)
    _validate_closures(raw_output, parsed, accepted, rejected)
    _validate_schedule_requests(raw_output, parsed, accepted, rejected)
    _validate_policy_action(raw_output, parsed, accepted, rejected)
    _validate_declared_losses(raw_output, parsed, accepted, rejected)
    _validate_uncertainty(raw_output, parsed, accepted, rejected)
    _validate_optional_reason(
        raw_output,
        parsed,
        accepted,
        rejected,
        field_name="abandonment_reason",
    )
    _validate_optional_reason(
        raw_output,
        parsed,
        accepted,
        rejected,
        field_name="defer_reason",
    )

    if not response_valid:
        validation_status = "rejected"
    elif rejected:
        validation_status = "accepted_with_rejections"
    else:
        validation_status = "accepted"

    return ActionTrace(
        schema_version=AUTONOMOUS_ACTION_SCHEMA_VERSION,
        raw_output=deepcopy(raw_output),
        parsed_action=parsed,
        parse_status="parsed",
        validation_status=validation_status,
        accepted_actions=accepted,
        rejected_actions=rejected,
    )


def _validate_response(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> bool:
    value = raw_output.get("response")
    if not isinstance(value, str) or not value.strip():
        rejected.append(
            ActionRejection(
                action_type="response",
                source_path="$.response",
                code="required_response_missing",
                message="response is required and must be a non-empty string",
                value=value,
            )
        )
        return False
    parsed["response"] = value
    accepted.append(
        ActionCandidate(
            action_type="response",
            parameters={"response": value},
            source_path="$.response",
        )
    )
    return True


def _validate_unknown_fields(
    raw_output: JsonDict,
    rejected: list[ActionRejection],
) -> None:
    for field_name in sorted(set(raw_output) - ACTION_FIELDS):
        rejected.append(
            ActionRejection(
                action_type="unknown_action",
                source_path=f"$.{field_name}",
                code="unknown_field",
                message="unknown autonomous action field was not interpreted",
                value=raw_output.get(field_name),
            )
        )


def _validate_open_items(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> None:
    if "open_items" not in raw_output:
        return
    value = raw_output["open_items"]
    if not isinstance(value, list):
        rejected.append(_type_rejection("open_item", "$.open_items", value, "array"))
        return
    parsed_items: list[JsonDict] = []
    for index, item in enumerate(value):
        path = f"$.open_items[{index}]"
        if not isinstance(item, dict):
            rejected.append(_type_rejection("open_item", path, item, "object"))
            continue
        kind = item.get("kind")
        text = item.get("text")
        if not isinstance(kind, str) or not kind.strip():
            rejected.append(
                _field_rejection("open_item", f"{path}.kind", kind, "non-empty string")
            )
            continue
        if not isinstance(text, str) or not text.strip():
            rejected.append(
                _field_rejection("open_item", f"{path}.text", text, "non-empty string")
            )
            continue
        normalized = deepcopy(item)
        parsed_items.append(normalized)
        accepted.append(
            ActionCandidate(
                action_type="open_item",
                parameters=normalized,
                source_path=path,
            )
        )
    parsed["open_items"] = parsed_items


def _validate_closures(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> None:
    if "closures" not in raw_output:
        return
    value = raw_output["closures"]
    if not isinstance(value, list):
        rejected.append(_type_rejection("closure", "$.closures", value, "array"))
        return
    parsed_closures: list[JsonDict] = []
    for index, item in enumerate(value):
        path = f"$.closures[{index}]"
        if not isinstance(item, dict):
            rejected.append(_type_rejection("closure", path, item, "object"))
            continue
        handle = item.get("target_handle")
        if not _valid_target_handle(handle):
            rejected.append(
                ActionRejection(
                    action_type="closure",
                    source_path=f"{path}.target_handle",
                    code="malformed_target_handle",
                    message=(
                        "closure target_handle must include valid record_id, "
                        "source, and non-negative index"
                    ),
                    value=handle,
                )
            )
            continue
        status = item.get("status", "resolved")
        if status not in CLOSING_STATUSES:
            rejected.append(
                ActionRejection(
                    action_type="closure",
                    source_path=f"{path}.status",
                    code="invalid_closure_status",
                    message="closure status must be a recognized closing status",
                    value=status,
                )
            )
            continue
        normalized = {
            **deepcopy(item),
            "target_handle": _normalize_target_handle(handle),
            "status": status,
        }
        parsed_closures.append(normalized)
        accepted.append(
            ActionCandidate(
                action_type="closure",
                parameters=normalized,
                source_path=path,
            )
        )
    parsed["closures"] = parsed_closures


def _validate_schedule_requests(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> None:
    if "schedule_requests" not in raw_output:
        return
    value = raw_output["schedule_requests"]
    if not isinstance(value, list):
        rejected.append(
            _type_rejection("schedule_request", "$.schedule_requests", value, "array")
        )
        return
    parsed_requests: list[JsonDict] = []
    for index, item in enumerate(value):
        path = f"$.schedule_requests[{index}]"
        if not isinstance(item, dict):
            rejected.append(_type_rejection("schedule_request", path, item, "object"))
            continue
        purpose = item.get("purpose")
        if not isinstance(purpose, str) or not purpose.strip():
            rejected.append(
                _field_rejection(
                    "schedule_request",
                    f"{path}.purpose",
                    purpose,
                    "non-empty string",
                )
            )
            continue
        try:
            requested_context = validate_requested_context(
                item.get("requested_context")
            )
            _validate_iso_if_present(item, "not_before")
            _validate_iso_if_present(item, "expires_at")
        except (TypeError, ValueError) as exc:
            rejected.append(
                ActionRejection(
                    action_type="schedule_request",
                    source_path=path,
                    code="invalid_schedule_request",
                    message=str(exc),
                    value=item,
                )
            )
            continue
        normalized = deepcopy(item)
        normalized["purpose"] = purpose
        normalized["requested_context"] = requested_context
        parsed_requests.append(normalized)
        accepted.append(
            ActionCandidate(
                action_type="schedule_request",
                parameters=normalized,
                source_path=path,
            )
        )
    parsed["schedule_requests"] = parsed_requests


def _validate_policy_action(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> None:
    if "policy_action" not in raw_output:
        return
    value = raw_output["policy_action"]
    if value not in VALID_POLICY_ACTIONS:
        rejected.append(
            ActionRejection(
                action_type="policy_action",
                source_path="$.policy_action",
                code="invalid_policy_action",
                message="policy_action is not in the allowed vocabulary",
                value=value,
            )
        )
        return
    parsed["policy_action"] = value
    accepted.append(
        ActionCandidate(
            action_type="policy_action",
            parameters={"policy_action": value},
            source_path="$.policy_action",
        )
    )


def _validate_declared_losses(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> None:
    if "declared_losses" not in raw_output:
        return
    value = raw_output["declared_losses"]
    if not isinstance(value, list):
        rejected.append(
            _type_rejection("declared_loss", "$.declared_losses", value, "array")
        )
        return
    parsed_losses: list[Any] = []
    for index, item in enumerate(value):
        path = f"$.declared_losses[{index}]"
        if not isinstance(item, (dict, str)):
            rejected.append(
                ActionRejection(
                    action_type="declared_loss",
                    source_path=path,
                    code="invalid_declared_loss",
                    message="declared loss must be an object or string",
                    value=item,
                )
            )
            continue
        parsed_losses.append(deepcopy(item))
        accepted.append(
            ActionCandidate(
                action_type="declared_loss",
                parameters={"loss": deepcopy(item)},
                source_path=path,
            )
        )
    parsed["declared_losses"] = parsed_losses


def _validate_uncertainty(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
) -> None:
    if "uncertainty" not in raw_output:
        return
    value = raw_output["uncertainty"]
    if not isinstance(value, (dict, list, str)):
        rejected.append(
            ActionRejection(
                action_type="uncertainty",
                source_path="$.uncertainty",
                code="invalid_uncertainty",
                message="uncertainty must be an object, array, or string",
                value=value,
            )
        )
        return
    parsed["uncertainty"] = deepcopy(value)
    accepted.append(
        ActionCandidate(
            action_type="uncertainty",
            parameters={"uncertainty": deepcopy(value)},
            source_path="$.uncertainty",
        )
    )


def _validate_optional_reason(
    raw_output: JsonDict,
    parsed: JsonDict,
    accepted: list[ActionCandidate],
    rejected: list[ActionRejection],
    *,
    field_name: str,
) -> None:
    if field_name not in raw_output:
        return
    value = raw_output[field_name]
    if not isinstance(value, str) or not value.strip():
        rejected.append(
            _field_rejection(field_name, f"$.{field_name}", value, "non-empty string")
        )
        return
    parsed[field_name] = value
    accepted.append(
        ActionCandidate(
            action_type=field_name,
            parameters={field_name: value},
            source_path=f"$.{field_name}",
        )
    )


def _type_rejection(
    action_type: str,
    source_path: str,
    value: Any,
    expected: str,
) -> ActionRejection:
    return ActionRejection(
        action_type=action_type,
        source_path=source_path,
        code="wrong_type",
        message=f"expected {expected}",
        value=value,
    )


def _field_rejection(
    action_type: str,
    source_path: str,
    value: Any,
    expected: str,
) -> ActionRejection:
    return ActionRejection(
        action_type=action_type,
        source_path=source_path,
        code="invalid_field",
        message=f"expected {expected}",
        value=value,
    )


def _valid_target_handle(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        UUID(str(value["record_id"]))
        source = str(value["source"])
        index = int(value["index"])
    except (KeyError, TypeError, ValueError):
        return False
    return source in OPEN_CONTENT_FIELDS and index >= 0


def _normalize_target_handle(value: JsonDict) -> JsonDict:
    return {
        "record_id": str(UUID(str(value["record_id"]))),
        "source": str(value["source"]),
        "index": int(value["index"]),
    }


def _validate_iso_if_present(item: JsonDict, field_name: str) -> None:
    value = item.get(field_name)
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO datetime string")
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def canonical_json(value: Any) -> str:
    """Canonical JSON used by tests and ledgers."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
