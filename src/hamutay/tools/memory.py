"""Memory tools — introspection over the instance's own prior cycles.

Each tool is a pure function:
    tool_name(params: dict, *, prior_states: list[tuple[int, UUID, dict, str]]) -> dict

prior_states is the session's accumulated history, one 4-tuple per cycle:
(cycle, record_id, state_dict, timestamp_iso). The session's OpenTasteSession
maintains this list and passes a live reference to the ToolExecutor, which
passes it through to each memory tool.

record_id is the UUID assigned when the record was created — stable across
branches/merges and the canonical address for cross-session reference.
In-session tool responses surface record_id alongside cycle so the instance
can author edges (annotate_edge) that bridge in-session and cross-session.

Tools return dicts with either content or error — never both.
"""

from __future__ import annotations

import json
import random as _random
from uuid import UUID


def _find_by_cycle(
    prior_states: list[tuple[int, UUID, dict, str]], cycle: int
) -> tuple[int, UUID, dict, str] | None:
    """Return the first (cycle, record_id, state, timestamp) tuple matching cycle, or None."""
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
    prior_states: list[tuple[int, UUID, dict, str]],
    bridge=None,
) -> dict:
    """Return structure of a prior state without retrieving content.

    Two addressing modes:
    - cycle=N → in-session state from prior_states
    - record_id=<UUID> → cross-session record via bridge
    """
    cycle = params.get("cycle")
    record_id_str = params.get("record_id")

    if record_id_str is not None:
        if bridge is None:
            return {
                "error": "record_id mode requires a bridge (persistence backend)"
            }
        try:
            record_id = UUID(record_id_str)
        except (ValueError, AttributeError, TypeError):
            return {
                "error": f"record_id is not a valid UUID: {record_id_str!r}"
            }
        try:
            content = bridge.retrieve(record_id)
        except Exception as e:
            return {"error": f"Record {record_id} not found: {e}"}
        # Strip framework-authored envelope fields for the schema view — the
        # instance asked about *its* data, not the provenance envelope.
        view = {
            k: v for k, v in content.items()
            if k not in ("provenance", "lineage_tags")
        }
        return {
            "record_id": str(record_id),
            "field_names": sorted(view.keys()),
            "field_types": {k: _type_name(v) for k, v in view.items()},
            "field_sizes": {k: _field_size(v) for k, v in view.items()},
            "total_tokens": _token_estimate(view),
        }

    if cycle is None:
        return {"error": "memory_schema requires one of: cycle, record_id"}

    found = _find_by_cycle(prior_states, cycle)
    if found is None:
        return {"error": f"No state found for cycle {cycle}"}

    _cycle, record_id, state, timestamp = found
    return {
        "cycle": _cycle,
        "record_id": str(record_id),
        "timestamp": timestamp,
        "field_names": sorted(state.keys()),
        "field_types": {k: _type_name(v) for k, v in state.items()},
        "field_sizes": {k: _field_size(v) for k, v in state.items()},
        "total_tokens": _token_estimate(state),
    }


def tool_recall(
    params: dict,
    *,
    prior_states: list[tuple[int, UUID, dict, str]],
    bridge=None,
) -> dict:
    """Retrieve content from prior cycles. Five addressing modes.

    Session-scoped by default; set ``scope`` to reach cross-session records.

    Modes (mutually exclusive; precedence top-down):
    - record_id=<UUID>, field=X → one field's value at a specific record
      (cross-session by construction; requires bridge)
    - record_id=<UUID> → the full record content
    - cycle=N, field=X → one field's value at one cycle (session-scoped)
    - cycle=N → the full state dict at one cycle (session-scoped)
    - recent=N, field=X → last N values of X across cycles, most-recent first
      (respects scope)
    - random=True, field=X → one value of X from a random record that has it
      (respects scope)

    Scopes (for recent and random modes):
    - "session" (default): in-session prior_states only
    - "cross_session": bridge only, skips in-session state
    - "all": union of both, in-session first
    """
    cycle = params.get("cycle")
    field = params.get("field")
    recent = params.get("recent")
    is_random = params.get("random", False)
    record_id_str = params.get("record_id")
    scope = params.get("scope", "session")

    # Mode 1: record_id — cross-session by construction
    if record_id_str is not None:
        if bridge is None:
            return {
                "error": "record_id mode requires a bridge (persistence backend)"
            }
        try:
            record_id = UUID(record_id_str)
        except (ValueError, AttributeError, TypeError):
            return {
                "error": f"record_id is not a valid UUID: {record_id_str!r}"
            }
        try:
            content = bridge.retrieve(record_id)
        except Exception as e:
            return {"error": f"Record {record_id} not found: {e}"}
        if field is not None:
            if field not in content:
                return {
                    "error": f"Field {field!r} not in record {record_id}"
                }
            return {
                "record_id": str(record_id),
                "content": content[field],
            }
        return {
            "record_id": str(record_id),
            "content": content,
        }

    # Mode 2: cycle — always session-scoped (cycles are session-local)
    if cycle is not None:
        found = _find_by_cycle(prior_states, cycle)
        if found is None:
            return {"error": f"No state found for cycle {cycle}"}
        _cycle, record_id, state, timestamp = found
        if field is not None:
            if field not in state:
                return {
                    "error": f"Field {field!r} not in state at cycle {cycle}"
                }
            return {
                "cycle": _cycle,
                "record_id": str(record_id),
                "timestamp": timestamp,
                "content": state[field],
            }
        return {
            "cycle": _cycle,
            "record_id": str(record_id),
            "timestamp": timestamp,
            "content": dict(state),
        }

    # Mode 3: recent — respects scope
    if recent is not None:
        if field is None:
            return {"error": "recent mode requires field"}
        collected = _collect_recent(prior_states, field, recent, scope, bridge)
        return {"content": collected}

    # Mode 4: random — respects scope
    if is_random:
        if field is None:
            return {"error": "random mode requires field"}
        candidates = _candidates_with_field(prior_states, field, scope, bridge)
        if not candidates:
            return {"error": f"No records contain field {field!r}"}
        return _random.choice(candidates)

    return {"error": "recall requires one of: cycle, record_id, recent, random"}


def _collect_recent(
    prior_states: list[tuple[int, UUID, dict, str]],
    field: str,
    recent: int,
    scope: str,
    bridge,
) -> list[dict]:
    """Walk recent → oldest, collect up to ``recent`` hits on ``field``.
    In-session first under scope=all; cross-session fills remaining capacity.
    """
    collected: list[dict] = []

    if scope in ("session", "all"):
        for _cycle, record_id, state, timestamp in reversed(prior_states):
            if field in state:
                collected.append(
                    {
                        "cycle": _cycle,
                        "record_id": str(record_id),
                        "timestamp": timestamp,
                        "value": state[field],
                    }
                )
                if len(collected) >= recent:
                    return collected

    if scope in ("cross_session", "all") and bridge is not None:
        remaining = recent - len(collected)
        if remaining > 0:
            results = bridge.query_open_has_field(field, limit=remaining)
            for (rid, record) in results:
                extras = getattr(record, "model_extra", None) or {}
                if field not in extras:
                    continue
                session = getattr(
                    getattr(record, "provenance", None),
                    "author_instance_id",
                    None,
                )
                collected.append(
                    {
                        "record_id": str(rid),
                        "session": session,
                        "value": extras[field],
                    }
                )
                if len(collected) >= recent:
                    break

    return collected


def _candidates_with_field(
    prior_states: list[tuple[int, UUID, dict, str]],
    field: str,
    scope: str,
    bridge,
) -> list[dict]:
    """Build a list of result-dicts eligible for random selection."""
    candidates: list[dict] = []

    if scope in ("session", "all"):
        for _cycle, record_id, state, timestamp in prior_states:
            if field in state:
                candidates.append(
                    {
                        "cycle": _cycle,
                        "record_id": str(record_id),
                        "timestamp": timestamp,
                        "content": state[field],
                    }
                )

    if scope in ("cross_session", "all") and bridge is not None:
        results = bridge.query_open_has_field(field)
        for (rid, record) in results:
            extras = getattr(record, "model_extra", None) or {}
            if field not in extras:
                continue
            session = getattr(
                getattr(record, "provenance", None),
                "author_instance_id",
                None,
            )
            candidates.append(
                {
                    "record_id": str(rid),
                    "session": session,
                    "content": extras[field],
                }
            )

    return candidates


_MISSING = object()


def tool_compare(
    params: dict,
    *,
    prior_states: list[tuple[int, UUID, dict, str]],
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

    _, record_id_a, state_a, _ = entry_a
    _, record_id_b, state_b, _ = entry_b

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
        "record_id_a": str(record_id_a),
        "record_id_b": str(record_id_b),
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


def _walk_step(entry: tuple[int, UUID, dict, str]) -> dict:
    cycle, record_id, state, timestamp = entry
    return {
        "cycle": cycle,
        "record_id": str(record_id),
        "timestamp": timestamp,
        "edge_type": "refines",
        "edge_source": "harness",
        "field_names": sorted(state.keys()),
        "summary": _step_summary(state),
    }


def tool_walk(
    params: dict,
    *,
    prior_states: list[tuple[int, UUID, dict, str]],
    bridge=None,
) -> dict:
    """Traverse the composition graph adjacent to a starting point.

    Two addressing modes:
    - from_cycle=N → in-session cycle-adjacency traversal
    - from_record_id=<UUID> → cross-session edge-driven traversal via
      composition graph (requires bridge)

    direction ∈ {forward, backward, both}; depth bounds the walk.
    """
    from_cycle = params.get("from_cycle")
    from_record_id_str = params.get("from_record_id")
    direction = params.get("direction", "both")
    depth = params.get("depth", 1)

    if from_record_id_str is not None:
        if bridge is None:
            return {
                "error": "from_record_id mode requires a bridge (persistence backend)"
            }
        try:
            from_record_id = UUID(from_record_id_str)
        except (ValueError, AttributeError, TypeError):
            return {
                "error": f"from_record_id is not a valid UUID: {from_record_id_str!r}"
            }
        return _walk_by_record_id(from_record_id, direction, depth, bridge)

    if from_cycle is None:
        return {"error": "walk requires one of: from_cycle, from_record_id"}
    if _find_by_cycle(prior_states, from_cycle) is None:
        return {"error": f"No state found for cycle {from_cycle}"}

    # Index by cycle for O(1) lookup
    by_cycle = {c: (c, rid, s, t) for (c, rid, s, t) in prior_states}

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


def _walk_by_record_id(
    from_record_id: UUID, direction: str, depth: int, bridge
) -> dict:
    """Cross-session traversal via composition graph edges.

    For depth > 1, re-queries edges from the most recently reached record —
    naive sequential chaining, not a BFS. Cycles in the graph are possible
    in principle but rare (the append-only tensor interface forecloses
    them for edges authored by the session layer); if encountered, the
    visited set short-circuits to avoid infinite loops.
    """
    path: list[dict] = []
    visited: set[UUID] = {from_record_id}

    def extend(current: UUID, edge_direction: str) -> None:
        for _ in range(depth):
            edges = bridge.query_edges_by_endpoint(current, edge_direction)
            if not edges:
                break
            # Pick the first edge we haven't walked through. Deterministic
            # for single-edge cases; arbitrary otherwise. AQL graph traversal
            # will give better semantics later.
            next_id: UUID | None = None
            chosen_edge: dict | None = None
            for edge in edges:
                candidate = (
                    edge["to_record"]
                    if edge_direction == "forward"
                    else edge["from_record"]
                )
                if candidate not in visited:
                    next_id = candidate
                    chosen_edge = edge
                    break
            if next_id is None or chosen_edge is None:
                break
            visited.add(next_id)
            try:
                content = bridge.retrieve(next_id)
            except Exception:
                break
            view = {
                k: v for k, v in content.items()
                if k not in ("provenance", "lineage_tags")
            }
            session = None
            prov = content.get("provenance")
            if isinstance(prov, dict):
                session = prov.get("author_instance_id")
            path.append(
                {
                    "record_id": str(next_id),
                    "session": session,
                    "edge_type": chosen_edge["relation_type"],
                    "edge_source": "composition_graph",
                    "field_names": sorted(view.keys()),
                    "summary": _step_summary(view),
                }
            )
            current = next_id

    if direction in ("backward", "both"):
        extend(from_record_id, "backward")
    if direction in ("forward", "both"):
        extend(from_record_id, "forward")

    return {"path": path}


def _value_contains(value, query_lower: str) -> bool:
    """Recursively check whether query appears as substring within value."""
    if isinstance(value, str):
        return query_lower in value.lower()
    if isinstance(value, dict):
        return any(_value_contains(v, query_lower) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_value_contains(v, query_lower) for v in value)
    return query_lower in str(value).lower()


def _snippet(value, query_lower: str, max_len: int = 120) -> str:
    """Extract a snippet around the first match for display."""
    text = json.dumps(value, default=str)
    idx = text.lower().find(query_lower)
    if idx < 0:
        return text[:max_len]
    start = max(0, idx - 30)
    end = min(len(text), idx + len(query_lower) + 60)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end] + suffix


def tool_search_memory(
    params: dict,
    *,
    prior_states: list[tuple[int, UUID, dict, str]],
    bridge=None,
) -> dict:
    """Keyword/substring search over prior states with structural narrowing.

    Structural narrowing (cycle_range, has_field, fields) happens first.
    Then the query is matched case-insensitively within the narrowed set.
    Results are sorted most-recent-first: in-session (cycle descending) then
    cross-session.

    Scopes:
    - "session" (default): in-session prior_states only
    - "cross_session": bridge only (hamutay-tagged records), no prior_states
    - "all": union of both; in-session first

    cycle_range narrow_by applies to in-session only — cycle numbers are
    session-local. has_field and fields apply symmetrically to both.
    """
    query = params.get("query")
    narrow_by = params.get("narrow_by") or {}
    limit = params.get("limit", 5)
    scope = params.get("scope", "session")

    if not query:
        return {"error": "query is required"}

    query_lower = query.lower()
    total = len(prior_states)

    in_session_matches: list[dict] = []
    narrowed_in_session = 0
    if scope in ("session", "all"):
        in_session_matches, narrowed_in_session = _match_in_session(
            prior_states, query_lower, narrow_by
        )

    cross_matches: list[dict] = []
    if scope in ("cross_session", "all") and bridge is not None:
        cross_matches = _match_cross_session(bridge, query_lower, narrow_by)

    # Rank: in-session by cycle desc first, then cross-session.
    combined = in_session_matches + cross_matches
    limited = combined[:limit]

    return {
        "results": limited,
        "search_metadata": {
            "total_candidates": total,
            "narrowed_to": narrowed_in_session,
            "matched_count": len(combined),
            "cross_session_count": len(cross_matches),
        },
    }


def _match_in_session(
    prior_states: list[tuple[int, UUID, dict, str]],
    query_lower: str,
    narrow_by: dict,
) -> tuple[list[dict], int]:
    """Apply narrowing + keyword match to in-session prior_states.
    Returns (matches, narrowed_candidate_count).
    """
    candidates = list(prior_states)

    cycle_range = narrow_by.get("cycle_range")
    if cycle_range:
        lo, hi = cycle_range
        candidates = [
            (c, rid, s, t) for (c, rid, s, t) in candidates if lo <= c <= hi
        ]

    has_field = narrow_by.get("has_field")
    if has_field:
        candidates = [
            (c, rid, s, t) for (c, rid, s, t) in candidates if has_field in s
        ]

    field_filter = narrow_by.get("fields")

    matches: list[dict] = []
    for cycle, record_id, state, timestamp in candidates:
        matched_fields: list[str] = []
        snippets: dict[str, str] = {}
        search_fields = field_filter if field_filter else list(state.keys())
        for key in search_fields:
            if key not in state:
                continue
            if _value_contains(state[key], query_lower):
                matched_fields.append(key)
                snippets[key] = _snippet(state[key], query_lower)
        if matched_fields:
            matches.append(
                {
                    "cycle": cycle,
                    "record_id": str(record_id),
                    "timestamp": timestamp,
                    "relevance": 1.0,
                    "matched_fields": matched_fields,
                    "snippets": snippets,
                }
            )

    matches.sort(key=lambda r: r["cycle"], reverse=True)
    return matches, len(candidates)


def _match_cross_session(bridge, query_lower: str, narrow_by: dict) -> list[dict]:
    """Keyword search across hamutay-tagged records from other sessions."""
    # Bound the cross-session search to hamutay-authored records via lineage tag.
    candidates = bridge.query_open_by_lineage_tag("hamutay")

    has_field = narrow_by.get("has_field")
    field_filter = narrow_by.get("fields")

    matches: list[dict] = []
    for rid, record in candidates:
        extras = getattr(record, "model_extra", None) or {}

        if has_field and has_field not in extras:
            continue

        search_fields = field_filter if field_filter else list(extras.keys())
        matched_fields: list[str] = []
        snippets: dict[str, str] = {}
        for key in search_fields:
            if key not in extras:
                continue
            if _value_contains(extras[key], query_lower):
                matched_fields.append(key)
                snippets[key] = _snippet(extras[key], query_lower)
        if matched_fields:
            session = getattr(
                getattr(record, "provenance", None),
                "author_instance_id",
                None,
            )
            matches.append(
                {
                    "record_id": str(rid),
                    "session": session,
                    "relevance": 1.0,
                    "matched_fields": matched_fields,
                    "snippets": snippets,
                }
            )

    return matches
