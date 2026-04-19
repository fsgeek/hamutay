"""Tests for memory tools — introspection over the instance's own prior cycles.

These tools are pure functions that read from a list of
(cycle, state, timestamp) triples. No API calls, no I/O.
"""

from hamutay.tools.memory import tool_memory_schema


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
