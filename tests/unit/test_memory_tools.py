"""Tests for memory tools — introspection over the instance's own prior cycles.

These tools are pure functions that read from a list of
(cycle, record_id, state, timestamp) 4-tuples. No API calls, no I/O.
"""

from uuid import UUID

from hamutay.tools.memory import (
    tool_compare,
    tool_memory_schema,
    tool_recall,
    tool_search_memory,
    tool_walk,
)


# Deterministic UUIDs so assertions can name them when needed.
_RID_1 = UUID("00000000-0000-0000-0000-000000000001")
_RID_2 = UUID("00000000-0000-0000-0000-000000000002")
_RID_3 = UUID("00000000-0000-0000-0000-000000000003")
_RID_4 = UUID("00000000-0000-0000-0000-000000000004")
_RID_5 = UUID("00000000-0000-0000-0000-000000000005")


def _make_prior_states():
    """Fixture: three cycles of prior state with varied structure."""
    return [
        (1, _RID_1, {"greeting": "hello", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
        (2, _RID_2, {"greeting": "hi", "theme": "curiosity", "cycle": 2},
         "2026-04-18T10:01:00+00:00"),
        (3, _RID_3, {"greeting": "hey", "theme": "care", "notes": ["a", "b"], "cycle": 3},
         "2026-04-18T10:02:00+00:00"),
    ]


def test_memory_schema_returns_structure():
    prior_states = _make_prior_states()
    result = tool_memory_schema({"cycle": 3}, prior_states=prior_states)
    assert result["cycle"] == 3
    assert result["record_id"] == str(_RID_3)
    assert result["timestamp"] == "2026-04-18T10:02:00+00:00"
    assert set(result["field_names"]) == {"greeting", "theme", "notes", "cycle"}
    assert result["field_types"]["notes"] == "list"
    assert result["field_types"]["greeting"] == "str"
    assert result["field_sizes"]["notes"] == 2
    assert result["total_tokens"] > 0


def test_memory_schema_missing_cycle():
    prior_states = _make_prior_states()
    result = tool_memory_schema({"cycle": 99}, prior_states=prior_states)
    assert "error" in result


def test_memory_schema_no_prior_states():
    result = tool_memory_schema({"cycle": 1}, prior_states=[])
    assert "error" in result


# ---------------------------------------------------------------------------
# recall — four modes
# ---------------------------------------------------------------------------


def test_recall_surgical():
    """cycle + field returns just that field, with record_id."""
    result = tool_recall(
        {"cycle": 2, "field": "theme"},
        prior_states=_make_prior_states(),
    )
    assert result["cycle"] == 2
    assert result["record_id"] == str(_RID_2)
    assert result["content"] == "curiosity"


def test_recall_full_snapshot():
    """cycle alone returns the full state dict, with record_id."""
    result = tool_recall({"cycle": 3}, prior_states=_make_prior_states())
    assert result["cycle"] == 3
    assert result["record_id"] == str(_RID_3)
    assert result["content"]["theme"] == "care"
    assert result["content"]["notes"] == ["a", "b"]


def test_recall_recent_trajectory():
    """recent=N, field=X returns last N values of X across cycles, most recent first."""
    result = tool_recall(
        {"recent": 3, "field": "greeting"},
        prior_states=_make_prior_states(),
    )
    assert len(result["content"]) == 3
    assert result["content"][0]["cycle"] == 3
    assert result["content"][0]["record_id"] == str(_RID_3)
    assert result["content"][0]["value"] == "hey"
    assert result["content"][2]["value"] == "hello"


def test_recall_recent_skips_missing_field():
    """recent mode skips cycles where the field doesn't exist."""
    result = tool_recall(
        {"recent": 5, "field": "theme"},
        prior_states=_make_prior_states(),
    )
    # Only cycles 2 and 3 have "theme"
    assert len(result["content"]) == 2
    cycles_returned = {e["cycle"] for e in result["content"]}
    assert cycles_returned == {2, 3}


def test_recall_random_picks_from_history():
    """random=true, field=X picks any prior state that has field X."""
    import random
    random.seed(42)
    result = tool_recall(
        {"random": True, "field": "greeting"},
        prior_states=_make_prior_states(),
    )
    assert result["cycle"] in {1, 2, 3}
    assert "content" in result


def test_recall_missing_cycle():
    result = tool_recall({"cycle": 99}, prior_states=_make_prior_states())
    assert "error" in result


def test_recall_missing_field_surgical():
    result = tool_recall(
        {"cycle": 1, "field": "theme"},  # cycle 1 has no "theme"
        prior_states=_make_prior_states(),
    )
    assert "error" in result


def test_recall_no_mode_is_error():
    """Calling recall with no mode selector is an error."""
    result = tool_recall({}, prior_states=_make_prior_states())
    assert "error" in result


# ---------------------------------------------------------------------------
# compare — structural diff between two cycles
# ---------------------------------------------------------------------------


def test_compare_added_and_changed():
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 2},
        prior_states=_make_prior_states(),
    )
    assert result["cycle_a"] == 1
    assert result["cycle_b"] == 2
    assert "theme" in result["added_fields"]
    changed_field_names = [c["field"] for c in result["changed_fields"]]
    assert "greeting" in changed_field_names
    # Without content=true, no values in the delta
    greeting_change = next(
        c for c in result["changed_fields"] if c["field"] == "greeting"
    )
    assert "value_a" not in greeting_change
    assert "value_b" not in greeting_change


def test_compare_with_content_shows_values():
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 2, "content": True},
        prior_states=_make_prior_states(),
    )
    greeting_change = next(
        c for c in result["changed_fields"] if c["field"] == "greeting"
    )
    assert greeting_change["value_a"] == "hello"
    assert greeting_change["value_b"] == "hi"


def test_compare_carries_record_ids():
    """compare surfaces record_id for both endpoints so the instance can
    address them cross-session."""
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 2},
        prior_states=_make_prior_states(),
    )
    assert result["record_id_a"] == str(_RID_1)
    assert result["record_id_b"] == str(_RID_2)


def test_compare_field_scopes_delta():
    """When field=X, only that field is compared."""
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 3, "field": "greeting"},
        prior_states=_make_prior_states(),
    )
    assert result["changed_fields"] == [
        {"field": "greeting", "size_a": 5, "size_b": 3}
    ]
    assert result["added_fields"] == []
    assert result["removed_fields"] == []


def test_compare_missing_cycle_errors():
    result = tool_compare(
        {"cycle_a": 99, "cycle_b": 1},
        prior_states=_make_prior_states(),
    )
    assert "error" in result


# ---------------------------------------------------------------------------
# walk — cycle-adjacent traversal
# ---------------------------------------------------------------------------


def _wide_prior_states():
    """Five cycles with varied field presence."""
    return [
        (1, _RID_1, {"theme": "opening", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
        (2, _RID_2, {"theme": "exploring", "cycle": 2}, "2026-04-18T10:01:00+00:00"),
        (3, _RID_3, {"theme": "focus", "pivot": True, "cycle": 3},
         "2026-04-18T10:02:00+00:00"),
        (4, _RID_4, {"theme": "deepening", "cycle": 4}, "2026-04-18T10:03:00+00:00"),
        (5, _RID_5, {"theme": "closing", "cycle": 5}, "2026-04-18T10:04:00+00:00"),
    ]


def test_walk_forward():
    result = tool_walk(
        {"from_cycle": 2, "direction": "forward", "depth": 2},
        prior_states=_wide_prior_states(),
    )
    cycles_in_path = [step["cycle"] for step in result["path"]]
    assert cycles_in_path == [3, 4]


def test_walk_backward():
    result = tool_walk(
        {"from_cycle": 4, "direction": "backward", "depth": 2},
        prior_states=_wide_prior_states(),
    )
    cycles_in_path = [step["cycle"] for step in result["path"]]
    assert cycles_in_path == [3, 2]


def test_walk_both():
    result = tool_walk(
        {"from_cycle": 3, "direction": "both", "depth": 1},
        prior_states=_wide_prior_states(),
    )
    cycles_in_path = [step["cycle"] for step in result["path"]]
    assert set(cycles_in_path) == {2, 4}


def test_walk_path_steps_have_summary():
    result = tool_walk(
        {"from_cycle": 1, "direction": "forward", "depth": 2},
        prior_states=_wide_prior_states(),
    )
    step = result["path"][0]
    assert "cycle" in step
    assert "record_id" in step
    assert step["record_id"] == str(_RID_2)
    assert "timestamp" in step
    assert "field_names" in step
    assert "edge_type" in step
    assert step["edge_type"] == "refines"
    assert isinstance(step["summary"], str)


def test_walk_from_missing_cycle():
    result = tool_walk(
        {"from_cycle": 99, "direction": "forward"},
        prior_states=_wide_prior_states(),
    )
    assert "error" in result


def test_walk_boundaries_are_not_errors():
    """Walking past the ends returns what's available, not an error."""
    result = tool_walk(
        {"from_cycle": 5, "direction": "forward", "depth": 3},
        prior_states=_wide_prior_states(),
    )
    assert result["path"] == []


# ---------------------------------------------------------------------------
# search_memory — keyword search with structural narrowing
# ---------------------------------------------------------------------------


def _searchable_prior_states():
    return [
        (1, _RID_1, {"theme": "opening", "mood": "tentative", "cycle": 1},
         "2026-04-18T10:00:00+00:00"),
        (2, _RID_2, {"theme": "curiosity", "mood": "tentative", "cycle": 2},
         "2026-04-18T10:01:00+00:00"),
        (3, _RID_3, {"theme": "care", "notes": ["first surprise", "pattern noticed"],
             "cycle": 3},
         "2026-04-18T10:02:00+00:00"),
        (4, _RID_4, {"theme": "pattern", "mood": "settled", "cycle": 4},
         "2026-04-18T10:03:00+00:00"),
    ]


def test_search_memory_basic_match():
    result = tool_search_memory(
        {"query": "pattern"},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert set(matched_cycles) == {3, 4}
    # Every result carries record_id so the instance can address it cross-session.
    for r in result["results"]:
        assert "record_id" in r
    rid_by_cycle = {r["cycle"]: r["record_id"] for r in result["results"]}
    assert rid_by_cycle[3] == str(_RID_3)
    assert rid_by_cycle[4] == str(_RID_4)


def test_search_memory_ranks_recent_first():
    result = tool_search_memory(
        {"query": "tentative"},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [2, 1]


def test_search_memory_narrow_by_cycle_range():
    result = tool_search_memory(
        {"query": "pattern", "narrow_by": {"cycle_range": [4, 10]}},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [4]


def test_search_memory_narrow_by_fields():
    result = tool_search_memory(
        {"query": "pattern", "narrow_by": {"fields": ["theme"]}},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [4]


def test_search_memory_narrow_by_has_field():
    result = tool_search_memory(
        {"query": "a", "narrow_by": {"has_field": "notes"}},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [3]


def test_search_memory_limit():
    result = tool_search_memory(
        {"query": "cycle", "limit": 2},
        prior_states=_searchable_prior_states(),
    )
    assert len(result["results"]) <= 2


def test_search_memory_metadata():
    result = tool_search_memory(
        {"query": "pattern"},
        prior_states=_searchable_prior_states(),
    )
    assert result["search_metadata"]["total_candidates"] == 4
    assert result["search_metadata"]["narrowed_to"] >= len(result["results"])


def test_search_memory_no_match():
    result = tool_search_memory(
        {"query": "nonexistentstring"},
        prior_states=_searchable_prior_states(),
    )
    assert result["results"] == []


def test_search_memory_missing_query():
    result = tool_search_memory({}, prior_states=_searchable_prior_states())
    assert "error" in result
