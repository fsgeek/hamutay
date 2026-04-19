"""Tests for memory tools — introspection over the instance's own prior cycles.

These tools are pure functions that read from a list of
(cycle, state, timestamp) triples. No API calls, no I/O.
"""

from hamutay.tools.memory import tool_memory_schema, tool_recall


def _make_prior_states():
    """Fixture: three cycles of prior state with varied structure."""
    return [
        (1, {"greeting": "hello", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
        (2, {"greeting": "hi", "theme": "curiosity", "cycle": 2},
         "2026-04-18T10:01:00+00:00"),
        (3, {"greeting": "hey", "theme": "care", "notes": ["a", "b"], "cycle": 3},
         "2026-04-18T10:02:00+00:00"),
    ]


def test_memory_schema_returns_structure():
    prior_states = _make_prior_states()
    result = tool_memory_schema({"cycle": 3}, prior_states=prior_states)
    assert result["cycle"] == 3
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
    """cycle + field returns just that field."""
    result = tool_recall(
        {"cycle": 2, "field": "theme"},
        prior_states=_make_prior_states(),
    )
    assert result["cycle"] == 2
    assert result["content"] == "curiosity"


def test_recall_full_snapshot():
    """cycle alone returns the full state dict."""
    result = tool_recall({"cycle": 3}, prior_states=_make_prior_states())
    assert result["cycle"] == 3
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
