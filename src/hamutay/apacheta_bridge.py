"""Bridge between Hamutay tensors and Yanantin's Apacheta database.

Converts Hamutay's lean Tensor into Yanantin's full TensorRecord
and stores it. Maintains composition edges between consecutive
projections so the tensor history forms a linked chain.

Usage:
    from hamutay.apacheta_bridge import ApachetaBridge
    from hamutay.projector import Projector

    bridge = ApachetaBridge.from_duckdb("tensors.duckdb")
    projector = Projector(on_tensor=bridge)

    # Every projection now persists to Apacheta automatically.
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


def _convert_open_state(
    state: dict,
    cycle: int,
    prior_id: UUID | None = None,
    session_id: str = "",
    model: str = "unknown",
) -> dict:
    """Convert a taste_open free-form state into kwargs for TensorRecord.

    No field mapping — the model's state passes through as extra fields
    on the TensorRecord (enabled by extra='allow' on ApachetaBaseModel).
    Only provenance and lineage are added by the harness.
    """
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    predecessors = (prior_id,) if prior_id else ()

    provenance = ProvenanceEnvelope(
        author_model_family=model,
        author_instance_id=session_id,
        predecessors_in_scope=predecessors,
    )

    # Start with required TensorRecord fields
    kwargs: dict = dict(
        provenance=provenance,
        lineage_tags=("hamutay", "taste_open", f"cycle-{cycle}"),
    )

    # Pass through everything the model created as extra fields
    for key, value in state.items():
        if key == "cycle":
            continue
        kwargs[key] = value

    return kwargs


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

    def store_open_state(self, state: dict, cycle: int) -> UUID:
        """Store a taste_open free-form state. Returns the tensor ID."""
        from yanantin.apacheta.models.tensor import TensorRecord
        from yanantin.apacheta.models.composition import CompositionEdge, RelationType

        kwargs = _convert_open_state(
            state, cycle,
            prior_id=self._prior_id,
            session_id=self._session_id,
            model=self._model,
        )
        record = TensorRecord(**kwargs)
        self._backend.store_tensor(record)

        if self._prior_id is not None:
            edge = CompositionEdge(
                from_tensor=self._prior_id,
                to_tensor=record.id,
                relation_type=RelationType.REFINES,
                ordering=cycle,
            )
            self._backend.store_composition_edge(edge)

        self._prior_id = record.id
        self._count += 1
        return record.id

    def retrieve(self, tensor_id: UUID) -> dict:
        """Retrieve a tensor by ID. Returns the full record as a dict."""
        record = self._backend.get_tensor(tensor_id)
        return record.model_dump()

    def list_tensors(self) -> list[dict]:
        """List all stored tensors. Returns summaries."""
        records = self._backend.list_tensors()
        return [
            {
                "id": str(r.id),
                "cycle": next(
                    (int(t.split("-")[1]) for t in r.lineage_tags if t.startswith("cycle-")),
                    None,
                ),
                "lineage_tags": list(r.lineage_tags),
            }
            for r in records
        ]

    @property
    def count(self) -> int:
        return self._count

    @classmethod
    def from_duckdb(cls, db_path: str | Path, session_id: str = "") -> ApachetaBridge:
        from yanantin.apacheta.backends.duckdb import DuckDBBackend
        backend = DuckDBBackend(db_path=str(db_path))
        return cls(backend, session_id=session_id)

    @classmethod
    def from_memory(cls, session_id: str = "") -> ApachetaBridge:
        from yanantin.apacheta.backends.memory import InMemoryBackend
        backend = InMemoryBackend()
        return cls(backend, session_id=session_id)
