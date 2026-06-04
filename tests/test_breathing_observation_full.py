"""Pin the `breathing` property against its own canonical exemplar.

Found by the three-lens fossil hunt (2026-06-03): the C5 self-correction
re-grounded `TrajectoryProfile.breathing` as
`recovery_rate >= 0.8 AND consecutive_precursor_rate == 0.0`. That `== 0.0`
term returned **False on observation_full** — the very dataset the breathing
finding (ledger B1) is named after — because cycles 51-52 are a consecutive
precursor pair that *recovers at 53*
(metacognitive_breathing_analysis.md: "one two-cycle pair (51-52) recovers at
53"). The detector named `breathing` rejected the canonical case of breathing.

The fix dropped the `== 0.0` term: a consecutive pair is only a collapse signal
when it does NOT recover, which `recovery_rate` already captures. These tests
fix that behavior so the husk cannot silently return.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hamutay.eval.trajectory import process_health, trajectory_stats
from hamutay.tensor import Tensor

OBS = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "observation_full"
    / "observations.jsonl"
)


def _profile():
    if not OBS.exists():
        pytest.skip(f"observation_full corpus not present at {OBS}")
    recs = [json.loads(l) for l in OBS.read_text().splitlines() if l.strip()]
    tensors = [Tensor.model_validate(r["tensor"]) for r in recs]
    return process_health(trajectory_stats(tensors))


def test_observation_full_reads_as_breathing():
    """The canonical healthy-breathing exemplar MUST read as breathing.

    This is the regression that catches the C5 husk: a `breathing` definition
    that returns False here is rejecting the data it was built to recognise.
    """
    ph = _profile()
    assert ph.breathing is True, (
        f"breathing=False on observation_full — the canonical exemplar. "
        f"recovery_rate={ph.precursor_recovery_rate:.3f}, "
        f"consecutive_rate={ph.consecutive_precursor_rate:.3f}. "
        "A consecutive precursor pair that recovers (cycles 51-52) is healthy "
        "breathing, not collapse; do not gate on consecutive_rate == 0.0."
    )


def test_observation_full_has_a_recovering_consecutive_pair():
    """Guards the *reason* the husk existed: this corpus genuinely contains a
    consecutive precursor pair (so the old `== 0.0` term genuinely fired), yet
    it is still breathing. If this corpus ever loses its consecutive pair the
    regression above would pass vacuously — this test keeps it meaningful."""
    ph = _profile()
    assert ph.consecutive_precursor_rate > 0.0, (
        "observation_full no longer has a consecutive precursor pair; the "
        "breathing regression test is now vacuous and needs a new exemplar."
    )
    assert ph.precursor_recovery_rate >= 0.8
