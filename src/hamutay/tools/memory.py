"""Memory tools — introspection over the instance's own prior cycles.

Each tool is a pure function:
    tool_name(params: dict, *, prior_states: list[tuple[int, dict, str]]) -> dict

prior_states is the session's accumulated history, one triple per cycle:
(cycle, state_dict, timestamp_iso). The session's OpenTasteSession maintains
this list and passes a live reference to the ToolExecutor, which passes it
through to each memory tool.

Tools return dicts with either content or error — never both.
"""

from __future__ import annotations

import json
import random as _random


def _find_by_cycle(
    prior_states: list[tuple[int, dict, str]], cycle: int
) -> tuple[int, dict, str] | None:
    """Return the first (cycle, state, timestamp) triple matching cycle, or None."""
    for entry in prior_states:
        if entry[0] == cycle:
            return entry
    return None


def _type_name(value) -> str:
    """Compact Python type name for a JSON-ish value."""
    return type(value).__name__


def _field_size(value) -> int:
    """Rough size: len for containers and strings, 1 otherwise."""
    if isinstance(value, (list, tuple, dict, set, str)):
        return len(value)
    return 1


def _token_estimate(state: dict) -> int:
    """Rough token count: JSON bytes / 4."""
    return len(json.dumps(state, default=str)) // 4


def tool_memory_schema(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Return structure of a prior cycle's state without retrieving content."""
    cycle = params.get("cycle")
    if cycle is None:
        return {"error": "cycle is required"}

    found = _find_by_cycle(prior_states, cycle)
    if found is None:
        return {"error": f"No state found for cycle {cycle}"}

    _cycle, state, timestamp = found
    return {
        "cycle": _cycle,
        "timestamp": timestamp,
        "field_names": sorted(state.keys()),
        "field_types": {k: _type_name(v) for k, v in state.items()},
        "field_sizes": {k: _field_size(v) for k, v in state.items()},
        "total_tokens": _token_estimate(state),
    }


def tool_recall(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Retrieve content from prior cycles. Four mutually exclusive modes.

    - cycle=N, field=X → one field's value at one cycle (surgical)
    - cycle=N         → the full state dict at one cycle
    - recent=N, field=X → last N values of X across cycles, most-recent first
    - random=True, field=X → one value of X from a random cycle that has it
    """
    cycle = params.get("cycle")
    field = params.get("field")
    recent = params.get("recent")
    is_random = params.get("random", False)

    if cycle is not None:
        found = _find_by_cycle(prior_states, cycle)
        if found is None:
            return {"error": f"No state found for cycle {cycle}"}
        _cycle, state, timestamp = found
        if field is not None:
            if field not in state:
                return {
                    "error": f"Field {field!r} not in state at cycle {cycle}"
                }
            return {
                "cycle": _cycle,
                "timestamp": timestamp,
                "content": state[field],
            }
        return {
            "cycle": _cycle,
            "timestamp": timestamp,
            "content": dict(state),
        }

    if recent is not None:
        if field is None:
            return {"error": "recent mode requires field"}
        collected = []
        for _cycle, state, timestamp in reversed(prior_states):
            if field in state:
                collected.append(
                    {
                        "cycle": _cycle,
                        "timestamp": timestamp,
                        "value": state[field],
                    }
                )
                if len(collected) >= recent:
                    break
        return {"content": collected}

    if is_random:
        if field is None:
            return {"error": "random mode requires field"}
        candidates = [
            (c, s, t) for (c, s, t) in prior_states if field in s
        ]
        if not candidates:
            return {"error": f"No prior cycles contain field {field!r}"}
        _cycle, state, timestamp = _random.choice(candidates)
        return {
            "cycle": _cycle,
            "timestamp": timestamp,
            "content": state[field],
        }

    return {"error": "recall requires one of: cycle, recent, random"}
