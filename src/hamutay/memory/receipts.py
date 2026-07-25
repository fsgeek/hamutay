"""Strict, content-free receipts for cross-project episodic retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IndexedMemberBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    corpus_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    indexed_through_kind: str = Field(min_length=1)
    indexed_through_value: int = Field(ge=0)


class EpisodicRetrievalReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: UUID = Field(default_factory=uuid4)
    cycle_id: UUID
    session_id: str = Field(min_length=1)
    author_model_family: str = Field(min_length=1)
    author_instance_id: str = Field(min_length=1)
    authorship_verified: Literal[False] = False
    purpose: str = Field(min_length=1)
    query: str = Field(min_length=1)
    corpus_ids: tuple[str, ...] = Field(min_length=1)
    limit: int = Field(ge=1, le=100)
    strategy: str = Field(min_length=1)
    match_semantics: str = Field(min_length=1)
    indexed_members: tuple[IndexedMemberBoundary, ...] = Field(min_length=1)
    episode_ref: str = Field(pattern=r"^episode://[^/]+/[^/]+/[^/]+$")
    returned_episode_count: int = Field(ge=1)
    selected_episode_rank: int = Field(ge=1)
    total_matches: int | None = Field(ge=0)
    total_standing: Literal["exact", "unknown"]
    search_index_standing: str = Field(min_length=1)
    open_standing: str = Field(min_length=1)
    retrieved_at: datetime
    outcome: Literal[
        "used",
        "not-used",
        "unavailable",
        "withdrawn",
        "malformed",
        "unauthorized",
        "error",
    ]
    resulting_action_id: UUID | None = None
    interface_version: Literal["v1"] = "v1"
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_cross_field_standing(self) -> Self:
        if self.selected_episode_rank > self.returned_episode_count:
            raise ValueError(
                "selected_episode_rank exceeds returned_episode_count"
            )
        if self.total_standing == "exact" and self.total_matches is None:
            raise ValueError("exact total_standing requires total_matches")
        if self.total_standing == "unknown" and self.total_matches is not None:
            raise ValueError("unknown total_standing requires total_matches=null")
        if self.outcome == "used" and self.open_standing != "available":
            raise ValueError("used evidence requires authoritative open standing available")
        return self
