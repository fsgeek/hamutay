"""Tests for memory tools — introspection over the instance's own prior cycles.

These tools are pure functions that read from a list of
(cycle, record_id, state, timestamp) 4-tuples. No API calls, no I/O.

Cross-session scope is exercised via a MagicMock bridge; the real bridge
is tested in test_apacheta_bridge.py.
"""

from unittest.mock import MagicMock
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
# recall — cross-session scope and record_id addressing
# ---------------------------------------------------------------------------


_CROSS_RID = UUID("11111111-1111-1111-1111-111111111111")


def _mock_bridge_with_field(field: str, value, session: str = "other"):
    """Mock bridge whose query_open_has_field returns a single cross-session hit."""
    from yanantin.apacheta.models.base import ApachetaBaseModel
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    prov = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id=session,
        predecessors_in_scope=(),
    )
    record = ApachetaBaseModel(provenance=prov, **{field: value})
    bridge = MagicMock()
    bridge.query_open_has_field.return_value = [(_CROSS_RID, record)]
    bridge.retrieve.return_value = {field: value}
    bridge.session_id = "test-current"
    return bridge


def test_recall_scope_session_default_does_not_touch_bridge():
    """Default scope=session must not call the bridge at all."""
    bridge = MagicMock()
    result = tool_recall(
        {"cycle": 1, "field": "greeting"},
        prior_states=_make_prior_states(),
        bridge=bridge,
    )
    assert result["content"] == "hello"
    bridge.list_open_records.assert_not_called()
    bridge.query_open_has_field.assert_not_called()


def test_recall_random_scope_cross_session_uses_bridge_only():
    """scope=cross_session skips in-session prior_states entirely."""
    bridge = _mock_bridge_with_field("theme", "cross-session-value", session="ghost")
    import random
    random.seed(0)
    result = tool_recall(
        {"random": True, "field": "theme", "scope": "cross_session"},
        prior_states=_make_prior_states(),  # has 'theme' in cycles 2,3
        bridge=bridge,
    )
    # Must be the cross-session hit, not an in-session one.
    assert result["content"] == "cross-session-value"
    assert result["record_id"] == str(_CROSS_RID)
    assert result["session"] == "ghost"
    assert "cycle" not in result


def test_recall_random_scope_all_unions_sources():
    """scope=all allows both in-session and cross-session candidates."""
    bridge = _mock_bridge_with_field("theme", "cross-value")
    import random
    random.seed(1)
    result = tool_recall(
        {"random": True, "field": "theme", "scope": "all"},
        prior_states=_make_prior_states(),
        bridge=bridge,
    )
    # Content populated; either source is legitimate.
    assert "content" in result


def test_recall_recent_scope_all_appends_cross_session():
    """recent scope=all returns in-session first, then cross-session to fill."""
    bridge = _mock_bridge_with_field("greeting", "cross-greeting")
    result = tool_recall(
        {"recent": 5, "field": "greeting", "scope": "all"},
        prior_states=_make_prior_states(),
        bridge=bridge,
    )
    # 3 in-session + 1 cross-session = 4 hits total (recent caps at 5).
    assert len(result["content"]) == 4
    # In-session entries come first and carry cycle.
    assert result["content"][0]["cycle"] == 3
    # Cross-session entry carries record_id and session, no cycle.
    last = result["content"][-1]
    assert last["value"] == "cross-greeting"
    assert last["record_id"] == str(_CROSS_RID)
    assert "cycle" not in last


def test_recall_by_record_id_requires_bridge():
    """record_id mode needs a bridge — honest error otherwise."""
    result = tool_recall(
        {"record_id": str(_CROSS_RID)},
        prior_states=[],
        bridge=None,
    )
    assert "error" in result


def test_recall_by_record_id_retrieves_cross_session():
    """record_id addresses cross-session records directly."""
    bridge = MagicMock()
    bridge.retrieve.return_value = {"theme": "from-other", "cycle": 7}
    result = tool_recall(
        {"record_id": str(_CROSS_RID), "field": "theme"},
        prior_states=[],
        bridge=bridge,
    )
    assert result["content"] == "from-other"
    assert result["record_id"] == str(_CROSS_RID)


def test_recall_by_record_id_missing_field_errors():
    bridge = MagicMock()
    bridge.retrieve.return_value = {"cycle": 7}
    result = tool_recall(
        {"record_id": str(_CROSS_RID), "field": "theme"},
        prior_states=[],
        bridge=bridge,
    )
    assert "error" in result


def test_recall_by_record_id_invalid_uuid_errors():
    bridge = MagicMock()
    result = tool_recall(
        {"record_id": "not-a-uuid"},
        prior_states=[],
        bridge=bridge,
    )
    assert "error" in result


def test_recall_cycle_mode_ignores_scope():
    """cycle is session-scoped by construction; scope=all doesn't change that."""
    bridge = MagicMock()
    result = tool_recall(
        {"cycle": 2, "field": "theme", "scope": "all"},
        prior_states=_make_prior_states(),
        bridge=bridge,
    )
    assert result["content"] == "curiosity"
    # Bridge not consulted for cycle mode even with scope=all.
    bridge.query_open_has_field.assert_not_called()


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


# ---------------------------------------------------------------------------
# search_memory — cross-session scope
# ---------------------------------------------------------------------------


def _mock_bridge_lineage_records(records):
    """Mock bridge whose query_open_by_lineage_tag returns the given records.

    ``records`` is a list of (record_id_str, extras_dict, session_id).
    """
    from yanantin.apacheta.models.base import ApachetaBaseModel
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    pairs = []
    for rid_str, extras, session_id in records:
        prov = ProvenanceEnvelope(
            author_model_family="haiku",
            author_instance_id=session_id,
            predecessors_in_scope=(),
        )
        pairs.append((UUID(rid_str), ApachetaBaseModel(provenance=prov, **extras)))

    bridge = MagicMock()
    bridge.query_open_by_lineage_tag.return_value = pairs
    bridge.session_id = "test-current"
    return bridge


def test_search_memory_scope_session_default_ignores_bridge():
    """Default scope=session must not consult the bridge."""
    bridge = MagicMock()
    result = tool_search_memory(
        {"query": "pattern"},  # default scope=session
        prior_states=_searchable_prior_states(),
        bridge=bridge,
    )
    bridge.query_open_by_lineage_tag.assert_not_called()
    assert result["results"]  # in-session hits still returned


def test_search_memory_scope_all_includes_cross_session():
    """scope=all merges in-session and cross-session hits."""
    bridge = _mock_bridge_lineage_records([
        ("11111111-1111-1111-1111-111111111111",
         {"theme": "pattern from elsewhere"}, "other-session"),
    ])
    result = tool_search_memory(
        {"query": "pattern", "scope": "all"},
        prior_states=_searchable_prior_states(),
        bridge=bridge,
    )
    in_session = [r for r in result["results"] if "cycle" in r]
    cross = [r for r in result["results"] if "cycle" not in r]
    assert len(in_session) >= 1
    assert len(cross) == 1
    assert cross[0]["session"] == "other-session"
    assert "pattern" in cross[0]["snippets"]["theme"]


def test_search_memory_scope_cross_session_only():
    """scope=cross_session returns only cross-session hits."""
    bridge = _mock_bridge_lineage_records([
        ("11111111-1111-1111-1111-111111111111",
         {"theme": "pattern from elsewhere"}, "other"),
    ])
    result = tool_search_memory(
        {"query": "pattern", "scope": "cross_session"},
        prior_states=_searchable_prior_states(),
        bridge=bridge,
    )
    assert all("cycle" not in r for r in result["results"])
    assert len(result["results"]) == 1


def test_search_memory_cross_session_respects_fields_filter():
    """narrow_by.fields scopes search to named fields cross-session too."""
    bridge = _mock_bridge_lineage_records([
        ("11111111-1111-1111-1111-111111111111",
         {"theme": "opening", "note": "pattern hidden here"}, "other"),
    ])
    result = tool_search_memory(
        {"query": "pattern", "narrow_by": {"fields": ["theme"]},
         "scope": "cross_session"},
        prior_states=[],
        bridge=bridge,
    )
    # The 'pattern' substring is in 'note', not 'theme' — fields filter excludes it.
    assert result["results"] == []


def test_memory_schema_by_record_id():
    """record_id mode inspects structure of a cross-session record."""
    bridge = MagicMock()
    rid = UUID("11111111-1111-1111-1111-111111111111")
    bridge.retrieve.return_value = {
        "theme": "cross-session",
        "notes": ["a", "b", "c"],
        "provenance": {"author_instance_id": "other-session"},
        "lineage_tags": ["hamutay", "cycle-5"],
    }
    result = tool_memory_schema(
        {"record_id": str(rid)},
        prior_states=[],
        bridge=bridge,
    )
    assert result["record_id"] == str(rid)
    assert set(result["field_names"]) >= {"theme", "notes"}
    assert result["field_types"]["notes"] == "list"
    assert result["field_sizes"]["notes"] == 3
    assert result["total_tokens"] > 0


def test_memory_schema_record_id_without_bridge_errors():
    result = tool_memory_schema(
        {"record_id": "11111111-1111-1111-1111-111111111111"},
        prior_states=[],
        bridge=None,
    )
    assert "error" in result


def test_memory_schema_record_id_invalid_uuid_errors():
    bridge = MagicMock()
    result = tool_memory_schema(
        {"record_id": "not-a-uuid"},
        prior_states=[],
        bridge=bridge,
    )
    assert "error" in result


def test_walk_from_record_id_forward():
    """from_record_id traverses composition edges forward."""
    bridge = MagicMock()
    rid_from = UUID("11111111-1111-1111-1111-111111111111")
    rid_next = UUID("22222222-2222-2222-2222-222222222222")

    def edges_for(record_id, direction):
        if direction == "forward" and record_id == rid_from:
            return [
                {
                    "from_record": rid_from,
                    "to_record": rid_next,
                    "relation_type": "refines",
                    "ordering": 2,
                }
            ]
        return []

    bridge.query_edges_by_endpoint.side_effect = edges_for
    bridge.retrieve.return_value = {
        "theme": "next",
        "provenance": {"author_instance_id": "s"},
    }

    result = tool_walk(
        {
            "from_record_id": str(rid_from),
            "direction": "forward",
            "depth": 1,
        },
        prior_states=[],
        bridge=bridge,
    )
    assert len(result["path"]) == 1
    step = result["path"][0]
    assert step["record_id"] == str(rid_next)
    assert step["edge_type"] == "refines"


def test_walk_from_record_id_backward():
    """Backward traversal follows edges into the record."""
    bridge = MagicMock()
    rid_prev = UUID("11111111-1111-1111-1111-111111111111")
    rid_at = UUID("22222222-2222-2222-2222-222222222222")

    def edges_for(record_id, direction):
        if direction == "backward" and record_id == rid_at:
            return [
                {
                    "from_record": rid_prev,
                    "to_record": rid_at,
                    "relation_type": "refines",
                    "ordering": 1,
                }
            ]
        return []

    bridge.query_edges_by_endpoint.side_effect = edges_for
    bridge.retrieve.return_value = {"theme": "earlier"}

    result = tool_walk(
        {
            "from_record_id": str(rid_at),
            "direction": "backward",
            "depth": 1,
        },
        prior_states=[],
        bridge=bridge,
    )
    assert len(result["path"]) == 1
    assert result["path"][0]["record_id"] == str(rid_prev)


def test_walk_from_record_id_boundary_no_edges():
    """No edges → empty path, not error."""
    bridge = MagicMock()
    bridge.query_edges_by_endpoint.return_value = []

    result = tool_walk(
        {
            "from_record_id": "11111111-1111-1111-1111-111111111111",
            "direction": "forward",
            "depth": 3,
        },
        prior_states=[],
        bridge=bridge,
    )
    assert result["path"] == []


def test_walk_from_record_id_requires_bridge():
    result = tool_walk(
        {"from_record_id": "11111111-1111-1111-1111-111111111111"},
        prior_states=[],
        bridge=None,
    )
    assert "error" in result


def test_search_memory_metadata_includes_cross_session_count():
    """search_metadata surfaces cross-session count for introspection."""
    bridge = _mock_bridge_lineage_records([
        ("11111111-1111-1111-1111-111111111111",
         {"theme": "pattern A"}, "other-1"),
        ("22222222-2222-2222-2222-222222222222",
         {"theme": "pattern B"}, "other-2"),
    ])
    result = tool_search_memory(
        {"query": "pattern", "scope": "all", "limit": 10},
        prior_states=_searchable_prior_states(),
        bridge=bridge,
    )
    assert "cross_session_count" in result["search_metadata"]
    assert result["search_metadata"]["cross_session_count"] == 2
