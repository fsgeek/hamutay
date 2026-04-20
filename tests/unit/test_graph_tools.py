"""Tests for tool_store and tool_annotate_edge — instance writes to the graph."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.tools.graph import (
    RELATION_TYPE_NAMES,
    tool_annotate_edge,
    tool_store,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# tool_store
# ---------------------------------------------------------------------------


def test_store_calls_bridge_with_content():
    bridge = MagicMock()
    bridge.session_id = "test-session"
    bridge.store_instance_record.return_value = UUID(
        "00000000-0000-0000-0000-000000000099"
    )
    result = tool_store(
        {"content": {"observation": "pattern X recurs"},
         "tags": ["hypothesis"]},
        cycle=5,
        bridge=bridge,
    )
    assert result["record_id"] == "00000000-0000-0000-0000-000000000099"
    assert result["session"] == "test-session"
    assert result["cycle"] == 5
    bridge.store_instance_record.assert_called_once_with(
        {"observation": "pattern X recurs"},
        cycle=5,
        tags=("hypothesis",),
    )


def test_store_without_bridge_errors():
    result = tool_store(
        {"content": {"x": 1}},
        cycle=5,
        bridge=None,
    )
    assert "error" in result


def test_store_requires_content():
    bridge = MagicMock()
    result = tool_store({"tags": ["x"]}, cycle=5, bridge=bridge)
    assert "error" in result


def test_store_rejects_non_dict_content():
    bridge = MagicMock()
    result = tool_store({"content": "just a string"}, cycle=5, bridge=bridge)
    assert "error" in result


def test_store_rejects_empty_content():
    bridge = MagicMock()
    result = tool_store({"content": {}}, cycle=5, bridge=bridge)
    assert "error" in result


def test_store_rejects_malformed_tags():
    bridge = MagicMock()
    result = tool_store(
        {"content": {"x": 1}, "tags": [1, 2, 3]},
        cycle=5,
        bridge=bridge,
    )
    assert "error" in result


def test_store_end_to_end_with_real_bridge():
    """Real bridge over in-memory backend: stored record is retrievable."""
    bridge = ApachetaBridge.from_memory(session_id="s", model="haiku")
    result = tool_store(
        {"content": {"hypothesis": "X causes Y"}, "tags": ["provisional"]},
        cycle=3,
        bridge=bridge,
    )
    record_id = UUID(result["record_id"])
    # Retrieve the same record through the bridge's read path.
    retrieved = bridge.retrieve(record_id)
    assert retrieved["hypothesis"] == "X causes Y"
    # Instance-authored lineage tag applied.
    assert "instance_authored" in retrieved["lineage_tags"]
    assert "provisional" in retrieved["lineage_tags"]


def test_store_tagged_records_discoverable_via_lineage_tag():
    """query_open_by_lineage_tag('instance_authored') finds them."""
    bridge = ApachetaBridge.from_memory(session_id="s", model="haiku")
    # A framework-authored record (no instance_authored tag)
    bridge.store_open_state(
        {"cycle": 1, "field_a": "framework"},
        cycle=1, record_id=uuid4(), timestamp=_now(),
    )
    # An instance-authored record
    tool_store(
        {"content": {"hypothesis": "test"}},
        cycle=2,
        bridge=bridge,
    )
    results = bridge.query_open_by_lineage_tag("instance_authored")
    assert len(results) == 1
    _, record = results[0]
    assert getattr(record, "hypothesis", None) == "test"


# ---------------------------------------------------------------------------
# tool_annotate_edge
# ---------------------------------------------------------------------------


def test_annotate_edge_calls_store_edge():
    bridge = MagicMock()
    bridge.store_edge.return_value = UUID(
        "00000000-0000-0000-0000-0000000000ee"
    )
    rid_a = "00000000-0000-0000-0000-000000000001"
    rid_b = "00000000-0000-0000-0000-000000000002"
    result = tool_annotate_edge(
        {
            "from_record_id": rid_a,
            "to_record_id": rid_b,
            "relation": "REFINES",
        },
        cycle=5,
        bridge=bridge,
    )
    assert result["edge_id"] == "00000000-0000-0000-0000-0000000000ee"
    assert result["from_record_id"] == rid_a
    assert result["to_record_id"] == rid_b
    assert result["relation"] == "REFINES"
    bridge.store_edge.assert_called_once_with(
        UUID(rid_a), UUID(rid_b), "REFINES", ordering=5,
    )


def test_annotate_edge_rejects_unknown_relation():
    bridge = MagicMock()
    result = tool_annotate_edge(
        {
            "from_record_id": "00000000-0000-0000-0000-000000000001",
            "to_record_id": "00000000-0000-0000-0000-000000000002",
            "relation": "NOT_A_REAL_RELATION",
        },
        cycle=5,
        bridge=bridge,
    )
    assert "error" in result
    bridge.store_edge.assert_not_called()


def test_annotate_edge_rejects_malformed_uuid():
    bridge = MagicMock()
    result = tool_annotate_edge(
        {
            "from_record_id": "not-a-uuid",
            "to_record_id": "also-not",
            "relation": "REFINES",
        },
        cycle=5,
        bridge=bridge,
    )
    assert "error" in result


def test_annotate_edge_without_bridge_errors():
    result = tool_annotate_edge(
        {
            "from_record_id": "00000000-0000-0000-0000-000000000001",
            "to_record_id": "00000000-0000-0000-0000-000000000002",
            "relation": "REFINES",
        },
        cycle=5,
        bridge=None,
    )
    assert "error" in result


def test_annotate_edge_requires_all_fields():
    bridge = MagicMock()
    result = tool_annotate_edge(
        {"from_record_id": "00000000-0000-0000-0000-000000000001"},
        cycle=5,
        bridge=bridge,
    )
    assert "error" in result


def test_relation_type_names_nonempty():
    """Sanity check: enum values are exposed for schemas/errors to reference."""
    assert "REFINES" in RELATION_TYPE_NAMES
    assert len(RELATION_TYPE_NAMES) >= 2


def test_annotate_edge_end_to_end_with_real_bridge():
    """Real bridge: edge authored by annotate_edge is traversable by walk."""
    from hamutay.tools.memory import tool_walk

    bridge = ApachetaBridge.from_memory(session_id="s", model="haiku")
    # Two disconnected records
    rid_a = uuid4()
    rid_b = uuid4()
    bridge.store_open_state(
        {"cycle": 1, "label": "A"}, cycle=1, record_id=rid_a, timestamp=_now(),
    )
    # Reset _prior_id so the second record doesn't auto-link to A
    bridge._prior_id = None
    bridge.store_open_state(
        {"cycle": 1, "label": "B"}, cycle=1, record_id=rid_b, timestamp=_now(),
    )

    # Verify walk from A finds nothing before the annotation
    before = tool_walk(
        {"from_record_id": str(rid_a), "direction": "forward", "depth": 1},
        prior_states=[], bridge=bridge,
    )
    assert before["path"] == []

    # Author an explicit edge A -> B with CONFIRMS relation
    result = tool_annotate_edge(
        {
            "from_record_id": str(rid_a),
            "to_record_id": str(rid_b),
            "relation": "CONFIRMS",
        },
        cycle=2,
        bridge=bridge,
    )
    assert "edge_id" in result

    # Now walk forward from A reaches B via the authored edge
    after = tool_walk(
        {"from_record_id": str(rid_a), "direction": "forward", "depth": 1},
        prior_states=[], bridge=bridge,
    )
    assert len(after["path"]) == 1
    assert after["path"][0]["record_id"] == str(rid_b)
    # Edge type in walk results carries the enum value, not the name.
    assert after["path"][0]["edge_type"] == "confirms"
