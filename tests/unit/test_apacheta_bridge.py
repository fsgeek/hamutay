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

import pytest

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


def test_runtime_provenance_exposes_honest_authorship_status():
    from pydantic import ValidationError
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    assert "authorship_verified" in ProvenanceEnvelope.model_fields
    provenance = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id="asserted-session",
    )
    assert provenance.authorship_verified is False
    with pytest.raises(ValidationError):
        provenance.authorship_verified = True


def test_instance_edge_carries_asserted_unverified_provenance():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    left = uuid4()
    right = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, left, _now())
    bridge._prior_id = None
    bridge.store_open_state({"cycle": 1}, 1, right, _now())

    edge_id = bridge.store_edge(left, right, "CONFIRMS", ordering=2)
    edge = next(edge for edge in bridge._backend.query_composition_graph() if edge.id == edge_id)

    assert edge.authored_mapping == "hamutay.instance_tool.v1"
    assert edge.provenance.author_instance_id == "session-a"
    assert edge.provenance.author_model_family == "haiku"
    assert edge.provenance.authorship_verified is False


def test_instance_edge_rejects_missing_endpoint_without_storing():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    existing = uuid4()
    missing = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, existing, _now())
    before = tuple(bridge._backend.query_composition_graph())

    with pytest.raises(ValueError, match="edge endpoint does not exist"):
        bridge.store_edge(existing, missing, "CONFIRMS", ordering=2)

    assert tuple(bridge._backend.query_composition_graph()) == before


def test_instance_edge_rejects_self_loop():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    record_id = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, record_id, _now())

    with pytest.raises(ValueError, match="self-loop"):
        bridge.store_edge(record_id, record_id, "CONFIRMS", ordering=2)


def test_repeated_annotation_is_distinct_append_only_assertion():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    left = uuid4()
    right = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, left, _now())
    bridge._prior_id = None
    bridge.store_open_state({"cycle": 1}, 1, right, _now())

    first = bridge.store_edge(left, right, "CONFIRMS", ordering=2)
    second = bridge.store_edge(left, right, "CONFIRMS", ordering=3)

    assert first != second


def test_instance_edge_endpoints_are_generic_open_records():
    """Endpoint validation uses get_record, not the prescribed TensorRecord path."""
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    open_record = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, open_record, _now())
    instance_record = bridge.store_instance_record(
        {"observation": "generic open record"}, cycle=2
    )

    edge_id = bridge.store_edge(open_record, instance_record, "CONFIRMS")

    assert edge_id in {edge.id for edge in bridge._backend.query_composition_graph()}
