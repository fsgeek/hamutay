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


def valid_member(**changes):
    values = {
        "corpus_id": "codex-history",
        "source_id": "source-a",
        "member_id": "member-a",
        "indexed_through_kind": "byte_offset",
        "indexed_through_value": 123,
    }
    values.update(changes)
    return IndexedMemberBoundary(**values)


def test_valid_receipt_is_immutable_and_unverified():
    receipt = valid_receipt()
    assert receipt.authorship_verified is False
    with pytest.raises(ValidationError):
        receipt.authorship_verified = True


def test_authorship_verified_rejects_integer_false():
    with pytest.raises(ValidationError, match="authorship_verified"):
        valid_receipt(authorship_verified=0)


@pytest.mark.parametrize("invalid", [True, 1.0, "1"])
@pytest.mark.parametrize(
    ("field", "builder"),
    [
        ("indexed_through_value", valid_member),
        ("limit", valid_receipt),
        ("returned_episode_count", valid_receipt),
        ("selected_episode_rank", valid_receipt),
        ("schema_version", valid_receipt),
    ],
)
def test_numeric_fields_reject_coercible_non_integer_values(field, builder, invalid):
    with pytest.raises(ValidationError, match=field):
        builder(**{field: invalid})


def test_model_copy_validates_member_numeric_updates():
    member = valid_member()

    with pytest.raises(ValidationError, match="indexed_through_value"):
        member.model_copy(update={"indexed_through_value": True})


def test_model_copy_cannot_forge_verified_authorship():
    receipt = valid_receipt()

    with pytest.raises(ValidationError, match="authorship_verified"):
        receipt.model_copy(update={"authorship_verified": True})


def test_model_copy_rechecks_authoritative_open_before_use():
    receipt = valid_receipt()

    with pytest.raises(ValidationError, match="authoritative open"):
        receipt.model_copy(update={"open_standing": "unavailable"})


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


def test_zero_result_receipt_has_no_selection():
    receipt = valid_receipt(
        returned_episode_count=0,
        episode_ref=None,
        selected_episode_rank=None,
        total_matches=0,
        open_standing="not-attempted",
        outcome="not-used",
    )

    assert receipt.returned_episode_count == 0
    assert receipt.episode_ref is None
    assert receipt.selected_episode_rank is None


@pytest.mark.parametrize("outcome", ["error", "unavailable", "unauthorized", "malformed"])
def test_preselection_failures_have_no_invented_selection(outcome):
    receipt = valid_receipt(
        returned_episode_count=0,
        episode_ref=None,
        selected_episode_rank=None,
        total_matches=None,
        total_standing="unknown",
        search_index_standing=outcome,
        open_standing="not-attempted",
        outcome=outcome,
    )

    assert receipt.episode_ref is None
    assert receipt.selected_episode_rank is None


@pytest.mark.parametrize(
    "changes",
    [
        {"episode_ref": None},
        {"selected_episode_rank": None},
        {
            "returned_episode_count": 0,
            "episode_ref": "episode://codex-history/session/episode",
            "selected_episode_rank": 1,
        },
        {
            "outcome": "error",
            "returned_episode_count": 1,
            "episode_ref": "episode://codex-history/session/episode",
            "selected_episode_rank": 1,
        },
    ],
)
def test_selection_fields_are_coherent_with_each_other_and_outcome(changes):
    with pytest.raises(ValidationError, match="selection"):
        valid_receipt(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"limit": 2, "returned_episode_count": 3},
        {"returned_episode_count": 5, "total_matches": 4},
    ],
)
def test_impossible_result_cardinality_is_rejected(changes):
    with pytest.raises(ValidationError, match="returned_episode_count|total_matches"):
        valid_receipt(**changes)


def test_indexed_member_corpus_must_be_requested():
    with pytest.raises(ValidationError, match="indexed_members"):
        valid_receipt(indexed_members=(valid_member(corpus_id="foreign-history"),))


def test_selected_episode_corpus_must_be_requested():
    with pytest.raises(ValidationError, match="episode_ref"):
        valid_receipt(episode_ref="episode://foreign-history/session/episode")


@pytest.mark.parametrize(
    "episode_ref",
    [
        "Episode://codex-history/session/episode",
        "episode:///session/episode",
        "episode://codex-history/episode",
        "episode://codex-history/session/episode/extra",
        "episode://codex-history/session//episode",
        "episode://codex-history/sess ion/episode",
        "episode://user@codex-history/session/episode",
        "episode://codex-history:443/session/episode",
        "episode://codex-history/session/episode?mode=raw",
        "episode://codex-history/session/episode#fragment",
    ],
)
def test_episode_reference_rejects_malformed_opaque_uri(episode_ref):
    with pytest.raises(ValidationError, match="episode_ref"):
        valid_receipt(episode_ref=episode_ref)


def test_retrieved_at_requires_timezone_awareness():
    with pytest.raises(ValidationError, match="retrieved_at"):
        valid_receipt(retrieved_at=datetime.now())


def test_total_unknown_is_explicit_null_not_zero_or_omission():
    receipt = valid_receipt(total_standing="unknown", total_matches=None)
    assert "total_matches" in receipt.model_dump()
    assert receipt.total_matches is None
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_standing="unknown", total_matches=0)


def test_exact_total_requires_nonnegative_integer():
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_standing="exact", total_matches=None)


@pytest.mark.parametrize("total_matches", [True, 1.0, "1"])
def test_total_matches_rejects_coercible_non_integer_values(total_matches):
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_matches=total_matches)


def test_total_matches_is_required_not_implicitly_defaulted():
    values = valid_receipt().model_dump()
    values.pop("total_matches")
    with pytest.raises(ValidationError, match="total_matches"):
        EpisodicRetrievalReceipt(**values)


def test_selected_rank_cannot_exceed_returned_episode_count():
    with pytest.raises(ValidationError, match="selected_episode_rank"):
        valid_receipt(returned_episode_count=2, selected_episode_rank=3)
