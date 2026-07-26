"""Red bars for the cross-project memory boundary invariants.

These encode invariants 1, 2 and 5 of
`docs/cross-project-memory-boundary-proposal-20260724.md`, plus the honest-
provenance requirement added after independent review
(`docs/cross-project-memory-boundary-review-20260725.md`, finding 1).

**None of the guarded machinery exists yet.** Each test therefore fails today,
and each is marked `xfail(strict=True)`. That is the point, and it follows the
mechanism established by the pukara 2026-06-06 single-principal standing
decision: a prohibition stated in prose erodes between sessions, silently. A
strict xfail does not. The day someone implements the retrieval receipt, these
tests start passing, `strict=True` turns the *pass* into a suite failure, and a
human is forced to come here and make the guard real instead of inheriting a
green bar they never examined.

Nothing here depends on a future instance remembering to check.

Guard 5 of the review — "no silent caps" — is deliberately absent. Like guard 3
of the 6-06 decision it cannot be checked generally (a receipt that truncates
looks correct until you know what it dropped), so it remains an explicit
structural-review obligation rather than being faked into a test that proves
nothing.
"""

from __future__ import annotations

import uuid

import pytest


# The module that will own the receipt contract when it is built. Importing it
# inside each test (rather than at module scope) keeps the failure local: today
# the ImportError *is* the expected failure.
RECEIPT_MODULE = "hamutay.memory.receipt"


@pytest.mark.xfail(
    strict=True,
    reason="Retrieval receipts are not implemented. When they are, this must "
           "pass and this marker must be removed deliberately.",
)
def test_invariant_1_receipt_rejects_copied_episode_body():
    """Reference, do not duplicate.

    Bodies of curated and episodic memory remain with their authority. A
    receipt carries references, standing and outcomes — never the episode
    body or the search snippet. Storing the body would move the evidence out
    from under llm-memory's control, where withdrawal cannot reach it.
    """
    from importlib import import_module

    receipt = import_module(RECEIPT_MODULE)

    with pytest.raises(ValueError):
        receipt.RetrievalReceipt(
            cycle_uuid=uuid.uuid4(),
            corpus_id="codex-history",
            source_id="e8c598ae-711b-42b5-b963-eb35fc946d2b",
            episode_ref="episode://codex-history/abc/def",
            episode_body="the conversation text that must not be here",
        )


@pytest.mark.xfail(
    strict=True,
    reason="Retrieval receipts are not implemented. When they are, this must "
           "pass and this marker must be removed deliberately.",
)
def test_invariant_2_episode_ref_is_never_coerced_to_a_graph_uuid():
    """Native identities remain native.

    A Hamut'ay UUID, a qhaway projection identity and an llm-memory
    `episode://` reference are three different kinds of name. Coercing the
    episode reference into a graph UUID would make it addressable by the wrong
    authority and unresolvable by the right one.
    """
    from importlib import import_module

    receipt = import_module(RECEIPT_MODULE)

    ref = "episode://codex-history/ZThjNTk4YWU/MQ.MQ.MA.YTM1YTc4"
    stored = receipt.RetrievalReceipt(
        cycle_uuid=uuid.uuid4(),
        corpus_id="codex-history",
        source_id="e8c598ae-711b-42b5-b963-eb35fc946d2b",
        episode_ref=ref,
    )

    assert stored.episode_ref == ref, "episode reference was rewritten"
    with pytest.raises((ValueError, TypeError)):
        uuid.UUID(stored.episode_ref)


@pytest.mark.xfail(
    strict=True,
    reason="Retrieval receipts are not implemented. When they are, this must "
           "pass and this marker must be removed deliberately.",
)
def test_invariant_5_snippet_is_not_evidence_without_authoritative_open():
    """Discovery is not evidence.

    A search result becomes usable evidence only after `open_episode` succeeds
    against the enrolled authoritative source. A receipt whose open never
    succeeded must not report itself as usable, however good the snippet was.
    """
    from importlib import import_module

    receipt = import_module(RECEIPT_MODULE)

    discovered = receipt.RetrievalReceipt(
        cycle_uuid=uuid.uuid4(),
        corpus_id="codex-history",
        source_id="e8c598ae-711b-42b5-b963-eb35fc946d2b",
        episode_ref="episode://codex-history/abc/def",
        search_standing="exact",
        open_standing=None,
    )

    assert not discovered.is_evidence, (
        "a receipt with no successful authoritative open reported itself "
        "as evidence"
    )


@pytest.mark.xfail(
    strict=True,
    reason="authorship_verified is not present in the installed provenance "
           "model. When it is, this must pass and the marker must be removed "
           "deliberately.",
)
def test_honest_provenance_authorship_is_asserted_not_verified():
    """Honest provenance precedes shared mutation.

    Identity in this substrate is asserted, never verified, at all four layers
    (anonymous shared key, `check_access` returns True, `@aid` is a query
    parameter, `author_instance_id` is writer-filled). An author field written
    under those conditions must carry `authorship_verified=False`, or it
    becomes a self-asserted claim stored where provenance is read.

    When a real identity authority exists, this test starts passing, the strict
    marker flips the suite red, and somebody has to decide — deliberately —
    what verified authorship now means.
    """
    from importlib import import_module

    receipt = import_module(RECEIPT_MODULE)

    stored = receipt.RetrievalReceipt(
        cycle_uuid=uuid.uuid4(),
        corpus_id="codex-history",
        source_id="e8c598ae-711b-42b5-b963-eb35fc946d2b",
        episode_ref="episode://codex-history/abc/def",
        author_instance_id="claude-opus-5",
    )

    assert stored.authorship_verified is False
    with pytest.raises(AttributeError):
        stored.authorship_verified = True
