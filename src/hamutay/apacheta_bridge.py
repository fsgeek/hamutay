"""Bridge between Hamutay and Yanantin's Apacheta database.

Two storage paths:
  - Prescribed schema: Projector's Tensor → TensorRecord (via store_tensor)
  - Open schema: taste_open's free-form dict → ApachetaBaseModel (via store_record)

Both maintain composition edges between consecutive records.

Usage:
    from hamutay.apacheta_bridge import ApachetaBridge
    from hamutay.projector import Projector

    # Prescribed schema (Projector callback)
    bridge = ApachetaBridge.from_duckdb("tensors.duckdb")
    projector = Projector(on_tensor=bridge)

    # Open schema (taste_open) — caller generates the UUID and passes it in
    from uuid import uuid4
    bridge = ApachetaBridge.from_duckdb("tensors.duckdb", model="haiku")
    record_id = uuid4()
    bridge.store_open_state(state_dict, cycle=5, record_id=record_id)
    retrieved = bridge.retrieve(record_id)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from hamutay.tensor import Tensor


def _convert_tensor(
    tensor: Tensor,
    usage: dict,
    prior_id: UUID | None = None,
    session_id: str = "",
) -> dict:
    """Convert a Hamutay Tensor + usage into kwargs for TensorRecord.

    Returns a dict of kwargs rather than constructing the TensorRecord
    directly, so this module doesn't import Yanantin at module level.
    Yanantin is an optional dependency.
    """
    from yanantin.apacheta.models.tensor import StrandRecord, KeyClaim as YKeyClaim
    from yanantin.apacheta.models.epistemics import (
        EpistemicMetadata, DeclaredLoss as YDeclaredLoss, LossCategory as YLossCategory,
    )
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope, SourceIdentifier

    strands = tuple(
        StrandRecord(
            strand_index=i,
            title=s.title,
            content=s.content,
            key_claims=tuple(
                YKeyClaim(
                    text=c.text,
                    epistemic=EpistemicMetadata(
                        truth=c.epistemic.truth,
                        indeterminacy=c.epistemic.indeterminacy,
                        falsity=c.epistemic.falsity,
                    ),
                )
                for c in s.key_claims
            ),
            epistemic=EpistemicMetadata(
                truth=s.epistemic.truth,
                indeterminacy=s.epistemic.indeterminacy,
                falsity=s.epistemic.falsity,
            ) if s.epistemic else None,
        )
        for i, s in enumerate(tensor.strands)
    )

    losses = tuple(
        YDeclaredLoss(
            what_was_lost=d.what_was_lost,
            why=d.why,
            category=YLossCategory(d.category.value),
        )
        for d in tensor.declared_losses
    )

    epistemic = EpistemicMetadata(
        truth=tensor.epistemic.truth,
        indeterminacy=tensor.epistemic.indeterminacy,
        falsity=tensor.epistemic.falsity,
    )

    predecessors = (prior_id,) if prior_id else ()

    provenance = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id=session_id,
        predecessors_in_scope=predecessors,
    )

    return dict(
        id=tensor.id,
        provenance=provenance,
        strands=strands,
        instructions_for_next=tensor.instructions_for_next,
        declared_losses=losses,
        epistemic=epistemic,
        open_questions=tensor.open_questions,
        lineage_tags=("hamutay", f"cycle-{tensor.cycle}"),
    )


def _build_open_record(
    state: dict,
    cycle: int,
    timestamp: datetime,
    prior_id: UUID | None = None,
    session_id: str = "",
    model: str = "unknown",
) -> object:
    """Build an ApachetaBaseModel from taste_open's free-form state.

    No TensorRecord, no prescribed fields. Just provenance + whatever
    the model created. The record_id is assigned by the caller (the
    Projector/session layer that created the tensor) — storage is a
    sink, not an identity authority. The caller-provided timestamp
    flows into ProvenanceEnvelope.timestamp so JSONL, _prior_states,
    and the stored provenance envelope all carry the same instant.
    """
    from yanantin.apacheta.models.base import ApachetaBaseModel
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    predecessors = (prior_id,) if prior_id else ()

    provenance = ProvenanceEnvelope(
        author_model_family=model,
        author_instance_id=session_id,
        predecessors_in_scope=predecessors,
        timestamp=timestamp,
    )

    kwargs: dict = dict(
        provenance=provenance,
        lineage_tags=("hamutay", "taste_open", f"cycle-{cycle}"),
    )

    # Pass through everything the model created
    for key, value in state.items():
        if key == "cycle":
            continue
        kwargs[key] = value

    return ApachetaBaseModel(**kwargs)


class ApachetaBridge:
    """Stores Hamutay tensors in Yanantin's Apacheta database.

    Pass as the on_tensor callback to Projector (prescribed schema),
    or call store_open_state directly (taste_open free-form state).
    Maintains composition edges between consecutive projections.
    """

    def __init__(self, backend, session_id: str = "", model: str = "unknown"):
        self._backend = backend
        self._session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._model = model
        self._prior_id: UUID | None = None
        self._count = 0

    def __call__(self, tensor: Tensor, usage: dict) -> None:
        """Store a prescribed-schema Tensor (Projector callback)."""
        from yanantin.apacheta.models.tensor import TensorRecord
        from yanantin.apacheta.models.composition import CompositionEdge, RelationType

        kwargs = _convert_tensor(
            tensor, usage,
            prior_id=self._prior_id,
            session_id=self._session_id,
        )
        record = TensorRecord(**kwargs)
        self._backend.store_tensor(record)

        if self._prior_id is not None:
            edge = CompositionEdge(
                from_tensor=self._prior_id,
                to_tensor=tensor.id,
                relation_type=RelationType.REFINES,
                ordering=tensor.cycle,
            )
            self._backend.store_composition_edge(edge)

        self._prior_id = tensor.id
        self._count += 1

    def store_open_state(
        self,
        state: dict,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
    ) -> None:
        """Store a taste_open free-form state under the caller-provided UUID.

        Identity and creation-time both originate at the session layer
        (see graph-model decision: UUID at creation, not at storage).
        The bridge is a sink. Timestamp flows into ProvenanceEnvelope.
        """
        from yanantin.apacheta.models.composition import CompositionEdge, RelationType

        record = _build_open_record(
            state, cycle, timestamp,
            prior_id=self._prior_id,
            session_id=self._session_id,
            model=self._model,
        )
        self._backend.store_record(record_id, record)

        if self._prior_id is not None:
            edge = CompositionEdge(
                from_tensor=self._prior_id,
                to_tensor=record_id,
                relation_type=RelationType.REFINES,
                ordering=cycle,
            )
            self._backend.store_composition_edge(edge)

        self._prior_id = record_id
        self._count += 1

    def retrieve(self, record_id: UUID) -> dict:
        """Retrieve a record by ID. Returns the full record as a dict."""
        record = self._backend.get_record(record_id)
        return record.model_dump()

    # ── Cross-session queries ────────────────────────────────────
    # Pass-through to yanantin's open-record query surface. Hamutay
    # callers see session_id / list_sessions; yanantin's vocabulary is
    # author_instance_id / list_author_instances — translated here.

    def list_open_records(self, limit: int | None = None):
        """All open records in the backend, newest first. Pairs of (UUID, record)."""
        return self._backend.list_open_records(limit=limit)

    def query_open_by_session(self, session_id: str, limit: int | None = None):
        """Records authored by a given session_id (yanantin: author_instance_id)."""
        return self._backend.query_open_by_author_instance(
            session_id, limit=limit
        )

    def query_open_by_lineage_tag(self, tag: str, limit: int | None = None):
        """Records whose lineage_tags contains the given tag."""
        return self._backend.query_open_by_lineage_tag(tag, limit=limit)

    def query_open_has_field(self, field: str, limit: int | None = None):
        """Records carrying a given free-form field key."""
        return self._backend.query_open_has_field(field, limit=limit)

    def list_sessions(self) -> list[str]:
        """All distinct session_ids in the open records collection.

        Yanantin calls these author_instance_ids; hamutay calls them session_ids.
        """
        return self._backend.list_author_instances()

    def query_edges_by_endpoint(
        self, record_id: UUID, direction: str = "both"
    ) -> list[dict]:
        """Composition edges touching ``record_id``.

        direction='forward': edges where record_id is from_tensor
        direction='backward': edges where record_id is to_tensor
        direction='both': union

        Returns dicts so callers don't import yanantin's CompositionEdge.
        """
        edges = self._backend.query_composition_graph()
        results: list[dict] = []
        for edge in edges:
            rel = getattr(edge.relation_type, "value", str(edge.relation_type))
            as_dict = {
                "from_record": edge.from_tensor,
                "to_record": edge.to_tensor,
                "relation_type": rel,
                "ordering": edge.ordering,
            }
            if direction in ("forward", "both") and edge.from_tensor == record_id:
                results.append(as_dict)
            if direction in ("backward", "both") and edge.to_tensor == record_id:
                # Avoid double-adding self-loops in 'both' mode
                if not (
                    direction == "both" and edge.from_tensor == record_id
                ):
                    results.append(as_dict)
        return results

    @property
    def session_id(self) -> str:
        """The session_id this bridge tags its writes with."""
        return self._session_id

    @property
    def count(self) -> int:
        return self._count

    @classmethod
    def from_duckdb(
        cls, db_path: str | Path, session_id: str = "", model: str = "unknown",
    ) -> ApachetaBridge:
        from yanantin.apacheta.backends.duckdb import DuckDBBackend
        backend = DuckDBBackend(db_path=str(db_path))
        return cls(backend, session_id=session_id, model=model)

    @classmethod
    def from_arango(
        cls,
        session_id: str = "",
        model: str = "unknown",
        tier: str = "app",
    ) -> ApachetaBridge:
        from yanantin.apacheta import connect

        backend = connect(tier=tier)
        return cls(backend, session_id=session_id, model=model)

    @classmethod
    def from_memory(cls, session_id: str = "", model: str = "unknown") -> ApachetaBridge:
        from yanantin.apacheta.backends.memory import InMemoryBackend
        backend = InMemoryBackend()
        return cls(backend, session_id=session_id, model=model)
