"""Trajectory analysis for tensor sequences.

A single tensor is a snapshot. A sequence of tensors is a trajectory —
and the trajectory's shape tells you things the snapshots can't.

Strand birth/death rates, loss channel evolution, capacity allocation
shifts, IFN compensation patterns — these are the tensor's vital signs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from hamutay.tensor import Tensor, LossCategory
from hamutay.eval.divergence import (
    capacity_allocation,
    loss_distribution,
    content_similarity,
    component_divergence,
    ComponentDivergence,
    CapacityAllocation,
    LossDistribution,
    _tokenize,
    _cosine_bow,
)


# ── Trajectory Stats ────────────────────────────────────────────────

@dataclass
class StrandEvent:
    """A strand appearing, disappearing, or merging."""
    cycle: int
    event_type: str  # "birth", "death", "persist"
    title: str


@dataclass
class TrajectoryStats:
    """Vital signs for a tensor sequence."""

    cycles: int
    strand_counts: list[int]
    strand_events: list[StrandEvent]
    loss_counts: list[int]
    loss_distributions: list[LossDistribution]
    ifn_lengths: list[int]  # character length of instructions_for_next
    question_counts: list[int]
    capacity_series: list[CapacityAllocation]
    total_token_series: list[int]
    epistemic_truth_series: list[float]
    epistemic_indeterminacy_series: list[float]

    # Derived: consecutive divergence (how much does cycle N differ from N-1)
    consecutive_divergence: list[ComponentDivergence]

    @property
    def strand_birth_rate(self) -> float:
        """Average new strands per cycle."""
        births = sum(1 for e in self.strand_events if e.event_type == "birth")
        return births / max(1, self.cycles)

    @property
    def strand_death_rate(self) -> float:
        """Average strand disappearances per cycle."""
        deaths = sum(1 for e in self.strand_events if e.event_type == "death")
        return deaths / max(1, self.cycles)

    @property
    def strand_stability(self) -> float:
        """Fraction of strand-cycles that are persistent (not birth/death)."""
        persists = sum(1 for e in self.strand_events if e.event_type == "persist")
        total = len(self.strand_events)
        return persists / max(1, total)

    @property
    def loss_evolution(self) -> str:
        """Characterize the loss channel evolution.

        Returns a label: 'stable', 'growing', 'shrinking', 'volatile', 'empty'.
        """
        if not self.loss_counts or all(c == 0 for c in self.loss_counts):
            return "empty"

        # Trend: linear regression slope via least squares
        n = len(self.loss_counts)
        if n < 3:
            return "stable"

        x_mean = (n - 1) / 2
        y_mean = sum(self.loss_counts) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(self.loss_counts))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Volatility: coefficient of variation
        if y_mean > 0:
            variance = sum((y - y_mean) ** 2 for y in self.loss_counts) / n
            cv = (variance ** 0.5) / y_mean
        else:
            cv = 0

        if cv > 0.5:
            return "volatile"
        if slope > 0.02:
            return "growing"
        if slope < -0.02:
            return "shrinking"
        return "stable"

    @property
    def ifn_compensation_detected(self) -> bool:
        """Check for IFN compensation pattern from Q2.

        If loss count drops and IFN length increases in the same window,
        that's the coupled channel compensation pattern.
        """
        if len(self.loss_counts) < 10 or len(self.ifn_lengths) < 10:
            return False

        # Compare first half to second half
        mid = len(self.loss_counts) // 2
        loss_first = sum(self.loss_counts[:mid]) / mid
        loss_second = sum(self.loss_counts[mid:]) / (len(self.loss_counts) - mid)
        ifn_first = sum(self.ifn_lengths[:mid]) / mid
        ifn_second = sum(self.ifn_lengths[mid:]) / (len(self.ifn_lengths) - mid)

        # Loss decreasing AND IFN increasing = compensation
        return loss_second < loss_first * 0.7 and ifn_second > ifn_first * 1.3

    @property
    def metacognitive_ratio_series(self) -> list[float]:
        """Meta-fraction over time. Rising = tensor eating itself."""
        return [cap.meta_frac for cap in self.capacity_series]

    def summary(self) -> dict:
        """Compact summary for display."""
        return {
            "cycles": self.cycles,
            "strand_count_range": f"{min(self.strand_counts)}-{max(self.strand_counts)}",
            "strand_birth_rate": f"{self.strand_birth_rate:.2f}/cycle",
            "strand_death_rate": f"{self.strand_death_rate:.2f}/cycle",
            "strand_stability": f"{self.strand_stability:.2f}",
            "loss_evolution": self.loss_evolution,
            "loss_count_range": f"{min(self.loss_counts)}-{max(self.loss_counts)}",
            "ifn_length_range": f"{min(self.ifn_lengths)}-{max(self.ifn_lengths)}",
            "ifn_compensation": self.ifn_compensation_detected,
            "token_range": f"{min(self.total_token_series)}-{max(self.total_token_series)}",
            "mean_consecutive_divergence": (
                f"{sum(d.overall for d in self.consecutive_divergence) / len(self.consecutive_divergence):.3f}"
                if self.consecutive_divergence else "n/a"
            ),
            "final_meta_frac": f"{self.capacity_series[-1].meta_frac:.2f}" if self.capacity_series else "n/a",
        }


def _detect_strand_events(
    prev_titles: set[str], curr_titles: set[str], cycle: int
) -> list[StrandEvent]:
    """Detect strand births, deaths, and persists between consecutive cycles."""
    events = []
    for t in curr_titles - prev_titles:
        events.append(StrandEvent(cycle=cycle, event_type="birth", title=t))
    for t in prev_titles - curr_titles:
        events.append(StrandEvent(cycle=cycle, event_type="death", title=t))
    for t in prev_titles & curr_titles:
        events.append(StrandEvent(cycle=cycle, event_type="persist", title=t))
    return events


def trajectory_stats(tensors: Sequence[Tensor]) -> TrajectoryStats:
    """Compute trajectory statistics for a sequence of tensors.

    Tensors should be in cycle order.
    """
    if not tensors:
        return TrajectoryStats(
            cycles=0, strand_counts=[], strand_events=[],
            loss_counts=[], loss_distributions=[], ifn_lengths=[],
            question_counts=[], capacity_series=[], total_token_series=[],
            epistemic_truth_series=[], epistemic_indeterminacy_series=[],
            consecutive_divergence=[],
        )

    strand_counts = []
    strand_events: list[StrandEvent] = []
    loss_counts = []
    loss_dists = []
    ifn_lengths = []
    question_counts = []
    cap_series = []
    token_series = []
    truth_series = []
    indet_series = []
    consec_div = []

    prev_titles: set[str] = set()

    for i, t in enumerate(tensors):
        strand_counts.append(len(t.strands))
        loss_counts.append(len(t.declared_losses))
        loss_dists.append(loss_distribution(t))
        ifn_lengths.append(len(t.instructions_for_next))
        question_counts.append(len(t.open_questions))
        cap_series.append(capacity_allocation(t))
        token_series.append(t.token_estimate())
        truth_series.append(t.epistemic.truth)
        indet_series.append(t.epistemic.indeterminacy)

        # Strand events
        curr_titles = {s.title for s in t.strands}
        if i > 0:
            strand_events.extend(_detect_strand_events(prev_titles, curr_titles, t.cycle))
        prev_titles = curr_titles

        # Consecutive divergence
        if i > 0:
            consec_div.append(component_divergence(tensors[i - 1], t))

    return TrajectoryStats(
        cycles=len(tensors),
        strand_counts=strand_counts,
        strand_events=strand_events,
        loss_counts=loss_counts,
        loss_distributions=loss_dists,
        ifn_lengths=ifn_lengths,
        question_counts=question_counts,
        capacity_series=cap_series,
        total_token_series=token_series,
        epistemic_truth_series=truth_series,
        epistemic_indeterminacy_series=indet_series,
        consecutive_divergence=consec_div,
    )


# ── Cross-Trajectory Comparison ─────────────────────────────────────

@dataclass
class TrajectoryComparison:
    """Compare two tensor trajectories (e.g., Q2 control vs treatment)."""

    stats_a: TrajectoryStats
    stats_b: TrajectoryStats

    # Per-cycle divergence between the two trajectories at matching cycles
    cross_divergence: list[ComponentDivergence]

    # Content similarity at each matching cycle
    cross_content_similarity: list[float]

    @property
    def mean_cross_divergence(self) -> float:
        if not self.cross_divergence:
            return 0.0
        return sum(d.overall for d in self.cross_divergence) / len(self.cross_divergence)

    @property
    def divergence_trend(self) -> str:
        """Is the divergence increasing, decreasing, or stable over time?"""
        if len(self.cross_divergence) < 5:
            return "insufficient_data"

        divs = [d.overall for d in self.cross_divergence]
        n = len(divs)
        x_mean = (n - 1) / 2
        y_mean = sum(divs) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(divs))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator
        if slope > 0.001:
            return "diverging"
        if slope < -0.001:
            return "converging"
        return "stable"

    @property
    def max_divergence_cycle(self) -> int | None:
        """Cycle at which the two trajectories are most different."""
        if not self.cross_divergence:
            return None
        max_idx = max(range(len(self.cross_divergence)),
                      key=lambda i: self.cross_divergence[i].overall)
        return max_idx + 1  # cycles are 1-indexed

    def summary(self) -> dict:
        return {
            "cycles_compared": len(self.cross_divergence),
            "mean_divergence": f"{self.mean_cross_divergence:.3f}",
            "divergence_trend": self.divergence_trend,
            "max_divergence_cycle": self.max_divergence_cycle,
            "mean_content_similarity": (
                f"{sum(self.cross_content_similarity) / len(self.cross_content_similarity):.3f}"
                if self.cross_content_similarity else "n/a"
            ),
            "stats_a": self.stats_a.summary(),
            "stats_b": self.stats_b.summary(),
        }


def compare_trajectories(
    a: Sequence[Tensor],
    b: Sequence[Tensor],
) -> TrajectoryComparison:
    """Compare two tensor trajectories cycle-by-cycle.

    Tensors are matched by cycle number. If one trajectory has cycles
    the other doesn't, those cycles are skipped.
    """
    stats_a = trajectory_stats(a)
    stats_b = trajectory_stats(b)

    # Match by cycle number
    b_by_cycle = {t.cycle: t for t in b}
    cross_div = []
    cross_sim = []

    for t_a in a:
        t_b = b_by_cycle.get(t_a.cycle)
        if t_b is None:
            continue
        cross_div.append(component_divergence(t_a, t_b))
        cross_sim.append(content_similarity(t_a, t_b))

    return TrajectoryComparison(
        stats_a=stats_a,
        stats_b=stats_b,
        cross_divergence=cross_div,
        cross_content_similarity=cross_sim,
    )
