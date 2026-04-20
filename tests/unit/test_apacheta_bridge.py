"""Tests for ApachetaBridge — storage sink + cross-session query surface.

The bridge wraps a yanantin backend. Writes originate at the session layer
with caller-minted UUIDs (framework-mints-identity, storage-is-sink). Reads
are pass-through with vocabulary translation at the boundary: hamutay callers
see session_id / list_sessions, yanantin sees author_instance_id /
list_author_instances.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from hamutay.apacheta_bridge import ApachetaBridge


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_bridge_list_open_records_from_memory():
    """All stored records returned, addressable by UUID."""
    bridge = ApachetaBridge.from_memory(session_id="test-session", model="haiku")
    rid_1 = uuid4()
    rid_2 = uuid4()
    bridge.store_open_state(
        {"cycle": 1, "theme": "opening"}, cycle=1, record_id=rid_1, timestamp=_now()
    )
    bridge.store_open_state(
        {"cycle": 2, "theme": "explore"}, cycle=2, record_id=rid_2, timestamp=_now()
    )
    results = bridge.list_open_records()
    ids = {rid for (rid, _) in results}
    assert {rid_1, rid_2} <= ids


def test_bridge_query_by_session_isolates_sessions():
    """Records from different sessions don't leak into a session-filtered query."""
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku",
    )
    rid_a = uuid4()
    rid_b = uuid4()
    bridge_a.store_open_state({"cycle": 1}, cycle=1, record_id=rid_a, timestamp=_now())
    bridge_b.store_open_state({"cycle": 1}, cycle=1, record_id=rid_b, timestamp=_now())

    results = bridge_a.query_open_by_session("session-a")
    ids = {rid for (rid, _) in results}
    assert rid_a in ids
    assert rid_b not in ids


def test_bridge_list_sessions():
    """list_sessions surfaces every distinct author_instance_id in the store."""
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku",
    )
    bridge_a.store_open_state({"cycle": 1}, cycle=1, record_id=uuid4(), timestamp=_now())
    bridge_b.store_open_state({"cycle": 1}, cycle=1, record_id=uuid4(), timestamp=_now())

    sessions = bridge_a.list_sessions()
    assert "session-a" in sessions
    assert "session-b" in sessions


def test_bridge_query_has_field():
    """query_open_has_field surfaces records carrying a given free-form key."""
    bridge = ApachetaBridge.from_memory(session_id="test", model="haiku")
    rid_with = uuid4()
    rid_without = uuid4()
    bridge.store_open_state(
        {"cycle": 1, "marker": "here"},
        cycle=1, record_id=rid_with, timestamp=_now(),
    )
    bridge.store_open_state(
        {"cycle": 2}, cycle=2, record_id=rid_without, timestamp=_now(),
    )

    results = bridge.query_open_has_field("marker")
    ids = {rid for (rid, _) in results}
    assert rid_with in ids
    assert rid_without not in ids


def test_bridge_query_by_lineage_tag():
    """Records stored carry default lineage_tags; cycle-N tag locates a specific cycle."""
    bridge = ApachetaBridge.from_memory(session_id="test", model="haiku")
    rid = uuid4()
    bridge.store_open_state(
        {"cycle": 5, "note": "here"},
        cycle=5, record_id=rid, timestamp=_now(),
    )

    results = bridge.query_open_by_lineage_tag("cycle-5")
    ids = {r for (r, _) in results}
    assert rid in ids


def test_bridge_session_id_property():
    """Bridge exposes the session_id it tags its own writes with."""
    bridge = ApachetaBridge.from_memory(session_id="the-current-one", model="haiku")
    assert bridge.session_id == "the-current-one"


def test_bridge_respects_limit():
    bridge = ApachetaBridge.from_memory(session_id="s", model="haiku")
    for i in range(5):
        bridge.store_open_state(
            {"cycle": i}, cycle=i, record_id=uuid4(), timestamp=_now()
        )
    results = bridge.list_open_records(limit=2)
    assert len(results) == 2
