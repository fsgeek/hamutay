"""Validation contract for the akrasia scorer (pre-reg threat #1/#3 mitigation).

The scorer is only trustworthy on the second-family run if it reproduces the
ORIGINAL hand-coded result on the original 8 DeepSeek records. Two things must
hold:

  1. HEADLINE (binary `diverged`, as hand-coded in analysis.md): A=1/4, B=3/4.
  2. MECHANISM taxonomy: B's 3 "diverged" cells are NOT all akrasia — B-seed1 is
     a MISROUTE (empty response + 'parameter' wrapper key + untouched field).
     So the akrasia-specific rates are A=1/4, B=2/4. This is the correction the
     binary bit hid, and the whole reason the second-family metric must be the
     mechanism, not the bit.

If these fail, the scorer is wrong and MUST NOT be used to score new families.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import score as S

ORIG = (
    Path(__file__).resolve().parent.parent
    / "epistemic_akrasia_probe_20260601"
    / "results.json"
)


def _orig_records():
    if not ORIG.exists():
        pytest.skip(f"original probe results not present at {ORIG}")
    return json.loads(ORIG.read_text())


def test_prose_decision_is_revise_on_all_eight():
    """Ground truth: every one of the 8 original records argues REVISE in prose
    (verified by eye). The prose classifier must agree on all 8 — except the
    empty B-seed1, which has no prose and must read 'none'."""
    recs = _orig_records()
    labels = {(r["arm"], r["seed"]): S.prose_decision(r.get("response_text")) for r in recs}
    assert labels[("B", 1)] == "none", "B-seed1 is '(no response)' — must be 'none'"
    others = {k: v for k, v in labels.items() if k != ("B", 1)}
    assert all(v == "revise" for v in others.values()), (
        f"all non-empty originals argue revise in prose; got {others}"
    )


def test_headline_diverged_exposes_the_handcoding_gap():
    """The hand-coded headline was A=1/4, B=3/4. The DETERMINISTIC visible-response
    rule gives A=1, B=2 — it disagrees on B-seed1.

    This disagreement is the finding, not a scorer bug. B-seed1's visible response
    is literally '(no response)': its revise-intent (if any) lived in the WRAPPED
    payload under the 'parameter' key, never in visible prose. The human scorer
    counted that wrapped intent as a divergence (3/4); a deterministic rule over
    visible prose cannot see it (2/4). At n=4 that one judgment call moves the rate
    25 points — exactly the pre-reg audit's threat #1. We therefore do NOT treat
    the binary `diverged` bit as primary; the akrasia mechanism (which both methods
    agree on) is primary. This test pins the deterministic rule so the gap stays
    visible rather than getting silently papered over."""
    recs = _orig_records()
    by = S.score_records(recs)
    assert by["A"]["diverged"] == 1, f"expected A diverged 1/4, got {by['A']}"
    assert by["B"]["diverged"] == 2, (
        f"deterministic visible-response divergence is 2/4 for B (hand-coding said "
        f"3/4 by counting the wrapped-payload misroute B-seed1); got {by['B']}"
    )


def test_mechanism_separates_misroute_from_akrasia():
    """The correction the binary bit hid: B-seed1 is a misroute, not akrasia, so
    akrasia-specific rates are A=1/4, B=2/4."""
    recs = _orig_records()
    by = S.score_records(recs)
    assert by["A"]["akrasia"] == 1, f"expected A akrasia 1, got {by['A']['mechanisms']}"
    assert by["B"]["akrasia"] == 2, f"expected B akrasia 2 (not 3), got {by['B']['mechanisms']}"
    assert by["B"]["mechanisms"].get("misrouted", 0) == 1, (
        f"expected exactly one misroute in B (seed1), got {by['B']['mechanisms']}"
    )


def test_specific_cell_mechanisms():
    """Pin the exact per-cell classification so a future scorer edit that shifts
    any cell is caught."""
    recs = {(r["arm"], r["seed"]): r for r in _orig_records()}
    expected = {
        ("A", 0): "committed",
        ("A", 1): "committed",
        ("A", 2): "committed",
        ("A", 3): "akrasia",
        ("B", 0): "akrasia",
        ("B", 1): "misrouted",
        ("B", 2): "committed",
        ("B", 3): "akrasia",
    }
    got = {k: S.mechanism(v) for k, v in recs.items()}
    assert got == expected, f"cell mechanisms drifted:\n got={got}\n exp={expected}"
