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


_MISSING = object()


def tool_compare(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Structural diff between two prior cycles.

    Returns added/removed/changed/unchanged field names, plus token and
    field-count totals for each side. With content=true, changed fields
    also carry their values on each side so the caller can read them.
    """
    cycle_a = params.get("cycle_a")
    cycle_b = params.get("cycle_b")
    field = params.get("field")
    content = params.get("content", False)

    if cycle_a is None or cycle_b is None:
        return {"error": "cycle_a and cycle_b are required"}

    entry_a = _find_by_cycle(prior_states, cycle_a)
    entry_b = _find_by_cycle(prior_states, cycle_b)
    if entry_a is None:
        return {"error": f"No state found for cycle {cycle_a}"}
    if entry_b is None:
        return {"error": f"No state found for cycle {cycle_b}"}

    _, state_a, _ = entry_a
    _, state_b, _ = entry_b

    added: list[str] = []
    removed: list[str] = []
    changed: list[dict] = []
    unchanged: list[str] = []

    if field is not None:
        a_val = state_a.get(field, _MISSING)
        b_val = state_b.get(field, _MISSING)
        if a_val is _MISSING and b_val is not _MISSING:
            added = [field]
        elif a_val is not _MISSING and b_val is _MISSING:
            removed = [field]
        elif a_val != b_val:
            entry = {
                "field": field,
                "size_a": _field_size(a_val),
                "size_b": _field_size(b_val),
            }
            if content:
                entry["value_a"] = a_val
                entry["value_b"] = b_val
            changed = [entry]
        elif a_val is not _MISSING:
            unchanged = [field]
    else:
        keys_a = set(state_a.keys())
        keys_b = set(state_b.keys())
        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        for key in sorted(keys_a & keys_b):
            if state_a[key] != state_b[key]:
                entry = {
                    "field": key,
                    "size_a": _field_size(state_a[key]),
                    "size_b": _field_size(state_b[key]),
                }
                if content:
                    entry["value_a"] = state_a[key]
                    entry["value_b"] = state_b[key]
                changed.append(entry)
            else:
                unchanged.append(key)

    return {
        "cycle_a": cycle_a,
        "cycle_b": cycle_b,
        "added_fields": added,
        "removed_fields": removed,
        "changed_fields": changed,
        "unchanged_fields": unchanged,
        "structural_delta": {
            "total_tokens_a": _token_estimate(state_a),
            "total_tokens_b": _token_estimate(state_b),
            "field_count_a": len(state_a),
            "field_count_b": len(state_b),
        },
    }


def _step_summary(state: dict) -> str:
    """One-line summary of a cycle's state for walk path steps."""
    keys = sorted(k for k in state.keys() if k != "cycle")
    if not keys:
        return "(empty state)"
    shown = ", ".join(keys[:5])
    suffix = "..." if len(keys) > 5 else ""
    return f"{len(keys)} field(s): {shown}{suffix}"


def _walk_step(entry: tuple[int, dict, str]) -> dict:
    cycle, state, timestamp = entry
    return {
        "cycle": cycle,
        "timestamp": timestamp,
        "edge_type": "refines",
        "edge_source": "harness",
        "field_names": sorted(state.keys()),
        "summary": _step_summary(state),
    }


def tool_walk(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Traverse cycles adjacent to a starting cycle.

    Only REFINES edges exist in the current graph, so traversal is cycle-
    adjacent. direction ∈ {forward, backward, both}; depth bounds the walk.
    """
    from_cycle = params.get("from_cycle")
    direction = params.get("direction", "both")
    depth = params.get("depth", 1)

    if from_cycle is None:
        return {"error": "from_cycle is required"}
    if _find_by_cycle(prior_states, from_cycle) is None:
        return {"error": f"No state found for cycle {from_cycle}"}

    # Index by cycle for O(1) lookup
    by_cycle = {c: (c, s, t) for (c, s, t) in prior_states}

    path: list[dict] = []
    if direction in ("backward", "both"):
        for offset in range(1, depth + 1):
            entry = by_cycle.get(from_cycle - offset)
            if entry is None:
                break
            path.append(_walk_step(entry))
    if direction in ("forward", "both"):
        for offset in range(1, depth + 1):
            entry = by_cycle.get(from_cycle + offset)
            if entry is None:
                break
            path.append(_walk_step(entry))

    return {"path": path}
