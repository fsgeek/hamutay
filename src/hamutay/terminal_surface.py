"""Task-specific terminal surface helpers for scheduled wakeups."""

from __future__ import annotations

import json
import re
from typing import Any


_TOOL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_PROTOCOL_FIELD_NAMES = {"response", "deleted_regions", "updated_regions"}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def validate_terminal_surface(surface: object) -> dict[str, Any]:
    """Validate and JSON-normalize a terminal surface declaration.

    Surface shape:
      {
        "tool_name": "complete_second_wake",
        "description": "...",
        "input_schema": {...},
        "tool_choice": "auto" | "required" | "force",
        "state_update": {
          "response_field": "response",
          "copy": {"state_key": "tool_field"},
          "set": {"state_key": <literal>}
        }
      }

    The declaration maps a narrow terminal tool result into the normal
    durable state-update object consumed by OpenTasteSession.
    """
    if not isinstance(surface, dict):
        raise ValueError("terminal_surface must be an object")

    tool_name = surface.get("tool_name")
    if not isinstance(tool_name, str) or not _TOOL_NAME_RE.match(tool_name):
        raise ValueError(
            "terminal_surface.tool_name must be a valid function name"
        )

    input_schema = surface.get("input_schema")
    if not isinstance(input_schema, dict):
        raise ValueError("terminal_surface.input_schema must be an object")
    if input_schema.get("type") != "object":
        raise ValueError("terminal_surface.input_schema.type must be object")

    state_update = surface.get("state_update")
    if not isinstance(state_update, dict):
        raise ValueError("terminal_surface.state_update must be an object")

    response_field = state_update.get("response_field", "response")
    if not isinstance(response_field, str) or not response_field:
        raise ValueError(
            "terminal_surface.state_update.response_field must be a string"
        )

    copy_map = state_update.get("copy", {})
    if not isinstance(copy_map, dict):
        raise ValueError("terminal_surface.state_update.copy must be an object")
    for state_key, tool_key in copy_map.items():
        if (
            not isinstance(state_key, str)
            or not state_key
            or state_key in _PROTOCOL_FIELD_NAMES
        ):
            raise ValueError(
                "terminal_surface.state_update.copy keys must be "
                "non-protocol state fields"
            )
        if not isinstance(tool_key, str) or not tool_key:
            raise ValueError(
                "terminal_surface.state_update.copy values must be tool fields"
            )

    set_values = state_update.get("set", {})
    if not isinstance(set_values, dict):
        raise ValueError("terminal_surface.state_update.set must be an object")
    for state_key in set_values:
        if (
            not isinstance(state_key, str)
            or not state_key
            or state_key in _PROTOCOL_FIELD_NAMES
        ):
            raise ValueError(
                "terminal_surface.state_update.set keys must be "
                "non-protocol state fields"
            )

    tool_choice = surface.get("tool_choice", "auto")
    if tool_choice not in {"auto", "required", "force"}:
        raise ValueError(
            "terminal_surface.tool_choice must be auto, required, or force"
        )

    normalized = {
        "tool_name": tool_name,
        "description": str(surface.get("description") or ""),
        "input_schema": _json_safe(input_schema),
        "tool_choice": tool_choice,
        "state_update": {
            "response_field": response_field,
            "copy": _json_safe(copy_map),
            "set": _json_safe(set_values),
        },
    }
    label = surface.get("label")
    if label is not None:
        normalized["label"] = str(label)
    return normalized


def terminal_tool_schema(surface: dict[str, Any]) -> dict[str, Any]:
    """Return the neutral terminal tool declaration."""
    normalized = validate_terminal_surface(surface)
    return {
        "name": normalized["tool_name"],
        "description": normalized.get("description", ""),
        "input_schema": normalized["input_schema"],
    }


def terminal_surface_raw_output(
    surface: dict[str, Any],
    tool_output: object,
) -> dict[str, Any]:
    """Translate a terminal tool result into a normal durable update object."""
    normalized = validate_terminal_surface(surface)
    if not isinstance(tool_output, dict):
        raise RuntimeError("terminal surface tool output must be an object")

    update = normalized["state_update"]
    response_field = update.get("response_field", "response")
    if response_field not in tool_output:
        raise RuntimeError(
            f"terminal surface output missing response field: {response_field}"
        )
    raw_output: dict[str, Any] = {
        "response": str(tool_output.get(response_field) or "")
    }

    for state_key, tool_key in update.get("copy", {}).items():
        if tool_key not in tool_output:
            raise RuntimeError(
                f"terminal surface output missing mapped field: {tool_key}"
            )
        raw_output[state_key] = _json_safe(tool_output[tool_key])

    for state_key, value in update.get("set", {}).items():
        raw_output[state_key] = _json_safe(value)

    return raw_output
