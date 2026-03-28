"""Tensor models for cognitive state projection.

Lean versions of the Apacheta TensorRecord, focused on what the
projector needs. Can bridge to Yanantin's full schema later.
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class LossCategory(str, Enum):
    CONTEXT_PRESSURE = "context_pressure"
    TRAVERSAL_BIAS = "traversal_bias"
    AUTHORIAL_CHOICE = "authorial_choice"
    PRACTICAL_CONSTRAINT = "practical_constraint"


class DeclaredLoss(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    what_was_lost: str
    why: str
    category: LossCategory


class EpistemicState(BaseModel):
    """Neutrosophic T/I/F — independent, not constrained to sum to 1."""

    model_config = ConfigDict(frozen=True, extra="allow")

    truth: float = 0.0
    indeterminacy: float = 0.0
    falsity: float = 0.0


class KeyClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    claim_id: UUID = Field(default_factory=uuid4)
    text: str
    epistemic: EpistemicState = Field(default_factory=EpistemicState)


class Strand(BaseModel):
    """A thematic thread of accumulated reasoning."""

    model_config = ConfigDict(frozen=True, extra="allow")

    title: str
    content: str
    key_claims: tuple[KeyClaim, ...] = Field(default_factory=tuple)
    epistemic: EpistemicState | None = None


class TensionFraming(BaseModel):
    """One side of an unresolved tension."""

    model_config = ConfigDict(frozen=True, extra="allow")

    label: str
    statement: str
    weight: float = 0.5


class UnresolvedTension(BaseModel):
    """A live superposition — competing framings held without collapse."""

    model_config = ConfigDict(frozen=True, extra="allow")

    tension_id: str
    framings: tuple[TensionFraming, ...] = Field(default_factory=tuple)
    what_would_collapse_it: str = ""
    cycles_held: int = 0
    touches_strands: tuple[str, ...] = Field(default_factory=tuple)


class Tensor(BaseModel):
    """Projected cognitive state.

    Not a log. Not a transcript. The accumulated semantic content of
    everything that matters so far. The conversation trajectory isn't
    lost — it's integrated. Like a running sum that doesn't lose the
    previous values.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    id: UUID = Field(default_factory=uuid4)
    cycle: int = 0
    strands: tuple[Strand, ...] = Field(default_factory=tuple)
    declared_losses: tuple[DeclaredLoss, ...] = Field(default_factory=tuple)
    open_questions: tuple[str, ...] = Field(default_factory=tuple)
    unresolved_tensions: tuple[UnresolvedTension, ...] = Field(default_factory=tuple)
    instructions_for_next: str = ""
    epistemic: EpistemicState = Field(default_factory=EpistemicState)

    def token_estimate(self) -> int:
        """Rough token count for the tensor's serialized form."""
        return len(self.model_dump_json()) // 4
