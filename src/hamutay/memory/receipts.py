"""Strict, content-minimized receipts for cross-project episodic retrieval.

``purpose`` and ``query`` are bounded retrieval inputs, not evidence bodies.
Their producers must not copy prompts, episode bodies, credentials, or private
diagnostics into them.
"""

from __future__ import annotations

from typing import Any, Literal, Self
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


class _ValidatedFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def model_copy(
        self,
        *,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        """Copy this value object, validating every requested replacement."""
        if update is None:
            return super().model_copy(deep=deep)
        values = self.model_dump(round_trip=True)
        values.update(update)
        return type(self).model_validate(values)


class IndexedMemberBoundary(_ValidatedFrozenModel):

    corpus_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    indexed_through_kind: str = Field(min_length=1)
    indexed_through_value: StrictInt = Field(ge=0)


class EpisodicRetrievalReceipt(_ValidatedFrozenModel):

    receipt_id: UUID = Field(default_factory=uuid4)
    cycle_id: UUID
    session_id: str = Field(min_length=1)
    author_model_family: str = Field(min_length=1)
    author_instance_id: str = Field(min_length=1)
    authorship_verified: Literal[False] = False
    purpose: str = Field(min_length=1)
    query: str = Field(min_length=1)
    corpus_ids: tuple[str, ...] = Field(min_length=1)
    limit: StrictInt = Field(ge=1, le=100)
    strategy: str = Field(min_length=1)
    match_semantics: str = Field(min_length=1)
    indexed_members: tuple[IndexedMemberBoundary, ...] = Field(min_length=1)
    episode_ref: str | None = None
    returned_episode_count: StrictInt = Field(ge=0)
    selected_episode_rank: StrictInt | None = Field(default=None, ge=1)
    total_matches: StrictInt | None = Field(ge=0)
    total_standing: Literal["exact", "unknown"]
    search_index_standing: str = Field(min_length=1)
    open_standing: str = Field(min_length=1)
    retrieved_at: AwareDatetime
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
    schema_version: StrictInt = Field(default=1, ge=1, le=1)

    @field_validator("authorship_verified", mode="before")
    @classmethod
    def require_literal_unverified_authorship(cls, value: object) -> bool:
        if type(value) is not bool or value is not False:
            raise ValueError("authorship_verified must be literal False")
        return value

    @field_validator("episode_ref")
    @classmethod
    def validate_opaque_episode_reference(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if any(character.isspace() for character in value):
            raise ValueError("episode_ref must not contain whitespace")
        if not value.startswith("episode://"):
            raise ValueError("episode_ref requires the exact episode scheme")

        parsed = urlsplit(value)
        if parsed.scheme != "episode" or not parsed.netloc:
            raise ValueError("episode_ref requires a nonempty authority/corpus")
        if "@" in parsed.netloc:
            raise ValueError("episode_ref must not contain userinfo")
        if ":" in parsed.netloc:
            raise ValueError("episode_ref must not contain a port")
        if parsed.query or parsed.fragment:
            raise ValueError("episode_ref must not contain a query or fragment")

        path_parts = parsed.path.split("/")
        if (
            len(path_parts) != 3
            or path_parts[0] != ""
            or not path_parts[1]
            or not path_parts[2]
        ):
            raise ValueError("episode_ref requires exactly two nonempty path segments")
        return value

    @model_validator(mode="after")
    def validate_cross_field_standing(self) -> Self:
        has_episode_ref = self.episode_ref is not None
        has_selected_rank = self.selected_episode_rank is not None
        has_selection = has_episode_ref and has_selected_rank

        if has_episode_ref != has_selected_rank:
            raise ValueError(
                "selection requires episode_ref and selected_episode_rank together"
            )
        if self.returned_episode_count == 0 and has_selection:
            raise ValueError("zero returned episodes cannot contain selection data")
        if self.outcome == "used" and not has_selection:
            raise ValueError("used outcome requires selection data")
        if self.outcome in {"error", "unavailable", "unauthorized", "malformed"} and has_selection:
            raise ValueError(f"{self.outcome} outcome cannot contain selection data")
        if (
            self.selected_episode_rank is not None
            and self.selected_episode_rank > self.returned_episode_count
        ):
            raise ValueError(
                "selected_episode_rank exceeds returned_episode_count"
            )
        if self.returned_episode_count > self.limit:
            raise ValueError("returned_episode_count exceeds limit")
        if self.total_standing == "exact" and self.total_matches is None:
            raise ValueError("exact total_standing requires total_matches")
        if (
            self.total_standing == "exact"
            and self.total_matches is not None
            and self.total_matches < self.returned_episode_count
        ):
            raise ValueError("total_matches is less than returned_episode_count")
        if self.total_standing == "unknown" and self.total_matches is not None:
            raise ValueError("unknown total_standing requires total_matches=null")
        requested_corpora = set(self.corpus_ids)
        if any(
            member.corpus_id not in requested_corpora
            for member in self.indexed_members
        ):
            raise ValueError("indexed_members contain a corpus outside corpus_ids")
        if self.episode_ref is not None:
            episode_corpus = urlsplit(self.episode_ref).netloc
            if episode_corpus not in requested_corpora:
                raise ValueError("episode_ref corpus is outside corpus_ids")
        if self.outcome == "used" and self.open_standing != "available":
            raise ValueError("used evidence requires authoritative open standing available")
        return self
