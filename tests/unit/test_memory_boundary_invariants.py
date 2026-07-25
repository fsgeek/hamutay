from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from hamutay.memory.receipts import (
    EpisodicRetrievalReceipt,
    IndexedMemberBoundary,
)


def valid_receipt(**changes):
    values = {
        "cycle_id": uuid4(),
        "session_id": "session-a",
        "author_model_family": "codex",
        "author_instance_id": "session-a",
        "authorship_verified": False,
        "purpose": "check a prior design decision",
        "query": "memory boundary",
        "corpus_ids": ("codex-history",),
        "limit": 10,
        "strategy": "lexical_bm25_text_en_v1",
        "match_semantics": "analyzed_any_token",
        "indexed_members": (
            IndexedMemberBoundary(
                corpus_id="codex-history",
                source_id="source-a",
                member_id="member-a",
                indexed_through_kind="byte_offset",
                indexed_through_value=123,
            ),
        ),
        "episode_ref": "episode://codex-history/session/episode",
        "returned_episode_count": 5,
        "selected_episode_rank": 1,
        "total_matches": 12,
        "total_standing": "exact",
        "search_index_standing": "available",
        "open_standing": "available",
        "retrieved_at": datetime.now(timezone.utc),
        "outcome": "used",
    }
    values.update(changes)
    return EpisodicRetrievalReceipt(**values)


def test_valid_receipt_is_immutable_and_unverified():
    receipt = valid_receipt()
    assert receipt.authorship_verified is False
    with pytest.raises(ValidationError):
        receipt.authorship_verified = True


def test_invariant_1_rejects_copied_episode_body_and_snippet():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        valid_receipt(episode_body={"response": "copied"})
    with pytest.raises(ValidationError, match="extra_forbidden"):
        valid_receipt(snippet="copied search text")


def test_invariant_2_rejects_uuid_in_place_of_episode_reference():
    with pytest.raises(ValidationError, match="episode_ref"):
        valid_receipt(episode_ref=str(uuid4()))


def test_invariant_5_requires_authoritative_open_before_use():
    with pytest.raises(ValidationError, match="authoritative open"):
        valid_receipt(open_standing="unavailable", outcome="used")


def test_total_unknown_is_explicit_null_not_zero_or_omission():
    receipt = valid_receipt(total_standing="unknown", total_matches=None)
    assert "total_matches" in receipt.model_dump()
    assert receipt.total_matches is None
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_standing="unknown", total_matches=0)


def test_exact_total_requires_nonnegative_integer():
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_standing="exact", total_matches=None)


def test_selected_rank_cannot_exceed_returned_episode_count():
    with pytest.raises(ValidationError, match="selected_episode_rank"):
        valid_receipt(returned_episode_count=2, selected_episode_rank=3)
