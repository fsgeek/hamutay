"""Graph-write tools — ``store`` and ``annotate_edge``.

These let the instance write typed records and composition edges into
the open records collection. Provenance is inherited from the running
session — the instance can't forge author_instance_id or model_family,
and the framework stamps every instance-authored record with the
``instance_authored`` lineage tag so these records are distinguishable
from the cycle-state stream.

Neither tool accepts a record_id from the instance. UUIDs are minted by
the framework at the moment of creation; the instance receives the id
as a result so it can reference the record later (via recall,
memory_schema, walk from_record_id, or annotate_edge).
"""

from __future__ import annotations

from uuid import UUID

from yanantin.apacheta.models.composition import RelationType


# Exposed so tool schemas / error messages can stay in sync with yanantin.
RELATION_TYPE_NAMES: tuple[str, ...] = tuple(r.name for r in RelationType)


def tool_store(
    params: dict,
    *,
    cycle: int,
    bridge=None,
) -> dict:
    """Author a typed record in the open records collection.

    Parameters:
        content (dict): The instance's payload. Required.
        tags (list[str]): Caller-supplied lineage tags. Optional.

    Returns ``{record_id, session, cycle}`` on success. The record_id
    can be used as a reference elsewhere (annotate_edge, recall,
    memory_schema) in this session or any future session.
    """
    if bridge is None:
        return {
            "error": "store requires a persistence backend (bridge not configured)"
        }

    content = params.get("content")
    if not isinstance(content, dict):
        return {"error": "store requires content (dict)"}

    if not content:
        return {"error": "store content must not be empty"}

    tags_param = params.get("tags") or []
    if not isinstance(tags_param, list) or not all(
        isinstance(t, str) for t in tags_param
    ):
        return {"error": "tags must be a list of strings"}

    try:
        record_id = bridge.store_instance_record(
            content, cycle=cycle, tags=tuple(tags_param)
        )
    except Exception as e:
        return {"error": f"Store failed: {e}"}

    return {
        "record_id": str(record_id),
        "session": getattr(bridge, "session_id", None),
        "cycle": cycle,
    }


def tool_annotate_edge(
    params: dict,
    *,
    cycle: int,
    bridge=None,
) -> dict:
    """Author a composition edge between two records.

    Parameters:
        from_record_id (str UUID): The edge's origin record. Required.
        to_record_id (str UUID): The edge's target record. Required.
        relation (str): RelationType enum name. Required. See
            RELATION_TYPE_NAMES for allowed values.

    Returns ``{edge_id, from_record_id, to_record_id, relation}``.
    """
    if bridge is None:
        return {
            "error": "annotate_edge requires a persistence backend (bridge not configured)"
        }

    from_str = params.get("from_record_id")
    to_str = params.get("to_record_id")
    relation = params.get("relation")

    if not from_str or not to_str or not relation:
        return {
            "error": "annotate_edge requires from_record_id, to_record_id, and relation"
        }

    try:
        from_id = UUID(from_str)
        to_id = UUID(to_str)
    except (ValueError, AttributeError, TypeError):
        return {
            "error": "from_record_id and to_record_id must be valid UUIDs"
        }

    if relation not in RELATION_TYPE_NAMES:
        return {
            "error": (
                f"Unknown relation: {relation!r}. "
                f"Allowed: {', '.join(RELATION_TYPE_NAMES)}"
            )
        }

    try:
        edge_id = bridge.store_edge(from_id, to_id, relation, ordering=cycle)
    except Exception as e:
        return {"error": f"Edge creation failed: {e}"}

    return {
        "edge_id": str(edge_id),
        "from_record_id": from_str,
        "to_record_id": to_str,
        "relation": relation,
    }
