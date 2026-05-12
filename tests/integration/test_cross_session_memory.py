"""Integration test — two sessions, cross-session memory access.

Exercises the full chain end-to-end through yanantin's in-memory backend:
session A writes records; session B uses the memory tools with a bridge
to read what A wrote, via every cross-session entry point.

No mocks for the bridge or backend; only the API call is stubbed out
(these tools don't need one).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.tools.memory import (
    tool_memory_schema,
    tool_recall,
    tool_search_memory,
    tool_walk,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_session_b_reads_session_a_records_by_session_id():
    """recall with scope=cross_session surfaces A's records when B queries."""
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku"
    )

    rid_a1 = uuid4()
    rid_a2 = uuid4()
    bridge_a.store_open_state(
        {"cycle": 1, "shared_marker": "A-cycle-1-value"},
        cycle=1, record_id=rid_a1, timestamp=_now(),
    )
    bridge_a.store_open_state(
        {"cycle": 2, "shared_marker": "A-cycle-2-value"},
        cycle=2, record_id=rid_a2, timestamp=_now(),
    )

    # Session B: no in-session prior states, bridge shared with A
    result = tool_recall(
        {"random": True, "field": "shared_marker", "scope": "cross_session"},
        prior_states=[],
        bridge=bridge_b,
    )
    assert result["content"].startswith("A-cycle-")
    assert result["session"] == "session-a"


def test_session_b_searches_across_session_a_records():
    """search_memory scope=all finds hamutay-tagged records from other sessions."""
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku"
    )

    rid = uuid4()
    bridge_a.store_open_state(
        {"cycle": 5, "note": "unique-phrase-to-find"},
        cycle=5, record_id=rid, timestamp=_now(),
    )

    result = tool_search_memory(
        {"query": "unique-phrase", "scope": "cross_session"},
        prior_states=[],
        bridge=bridge_b,
    )
    assert len(result["results"]) == 1
    hit = result["results"][0]
    assert hit["session"] == "session-a"
    assert hit["record_id"] == str(rid)


def test_session_b_inspects_session_a_record_schema_by_id():
    """memory_schema record_id mode reads cross-session record structure."""
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku"
    )
    rid = uuid4()
    bridge_a.store_open_state(
        {"cycle": 3, "theme": "opening", "notes": ["a", "b", "c"]},
        cycle=3, record_id=rid, timestamp=_now(),
    )

    result = tool_memory_schema(
        {"record_id": str(rid)}, prior_states=[], bridge=bridge_b,
    )
    assert "theme" in result["field_names"]
    assert "notes" in result["field_names"]
    # Envelope stripped so the instance sees its own shape.
    assert "provenance" not in result["field_names"]
    assert result["field_sizes"]["notes"] == 3


def test_session_b_retrieves_session_a_record_by_id():
    """recall record_id mode fetches the specific cross-session record."""
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku"
    )
    rid = uuid4()
    bridge_a.store_open_state(
        {"cycle": 7, "payload": "specific-content-here"},
        cycle=7, record_id=rid, timestamp=_now(),
    )

    result = tool_recall(
        {"record_id": str(rid), "field": "payload"},
        prior_states=[],
        bridge=bridge_b,
    )
    assert result["content"] == "specific-content-here"


def test_walk_follows_composition_edges_across_cycles():
    """walk from_record_id traverses real composition edges in the backend.

    Session A writes three sequential records; the bridge auto-maintains
    REFINES edges between consecutive writes. Forward walk from the
    middle reaches the third; backward reaches the first.
    """
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    rid_1 = uuid4()
    rid_2 = uuid4()
    rid_3 = uuid4()
    bridge.store_open_state({"cycle": 1}, cycle=1, record_id=rid_1, timestamp=_now())
    bridge.store_open_state({"cycle": 2}, cycle=2, record_id=rid_2, timestamp=_now())
    bridge.store_open_state({"cycle": 3}, cycle=3, record_id=rid_3, timestamp=_now())

    forward = tool_walk(
        {"from_record_id": str(rid_2), "direction": "forward", "depth": 1},
        prior_states=[], bridge=bridge,
    )
    assert len(forward["path"]) == 1
    assert forward["path"][0]["record_id"] == str(rid_3)

    backward = tool_walk(
        {"from_record_id": str(rid_2), "direction": "backward", "depth": 1},
        prior_states=[], bridge=bridge,
    )
    assert len(backward["path"]) == 1
    assert backward["path"][0]["record_id"] == str(rid_1)


def test_list_sessions_surfaces_all_participating_sessions():
    """list_sessions reflects everyone who's written to the shared backend."""
    bridge_a = ApachetaBridge.from_memory(session_id="a", model="haiku")
    bridge_b = ApachetaBridge(backend=bridge_a._backend, session_id="b", model="haiku")
    bridge_c = ApachetaBridge(backend=bridge_a._backend, session_id="c", model="haiku")

    bridge_a.store_open_state({"cycle": 1}, cycle=1, record_id=uuid4(), timestamp=_now())
    bridge_b.store_open_state({"cycle": 1}, cycle=1, record_id=uuid4(), timestamp=_now())
    bridge_c.store_open_state({"cycle": 1}, cycle=1, record_id=uuid4(), timestamp=_now())

    sessions = bridge_a.list_sessions()
    assert set(sessions) >= {"a", "b", "c"}


def test_scope_session_does_not_leak_across_sessions():
    """Default scope=session stays in prior_states, ignores the bridge completely."""
    # Simulate session B with only its own in-session history plus a bridge
    # that holds records from session A.
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku"
    )
    bridge_a.store_open_state(
        {"cycle": 1, "leak_test": "from-A"},
        cycle=1, record_id=uuid4(), timestamp=_now(),
    )

    b_prior_states = [
        (
            1,
            UUID("00000000-0000-0000-0000-000000000001"),
            {"cycle": 1, "leak_test": "from-B"},
            _now().isoformat(),
        ),
    ]

    # Default scope=session: only B's in-session state is eligible.
    result = tool_recall(
        {"random": True, "field": "leak_test"},
        prior_states=b_prior_states,
        bridge=bridge_b,
    )
    assert result["content"] == "from-B"
