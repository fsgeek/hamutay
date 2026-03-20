"""Run divergence analysis on Q2 declared losses experiment data.

Q2 has two conditions run on identical input:
  - control: sees prior declared_losses each cycle
  - no_prior_losses: never sees prior declared_losses

The original analysis reported 0.000 Jaccard overlap across all 104 cycles.
This analysis replaces that single number with a divergence profile that
shows *how* and *where* the two conditions diverge, not just *that* they do.

Usage:
    uv run python -m hamutay.eval.run_q2_divergence
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hamutay.tensor import (
    Tensor,
    Strand,
    KeyClaim,
    DeclaredLoss,
    EpistemicState,
    LossCategory,
)
from hamutay.eval.divergence import (
    divergence_profile,
    capacity_allocation,
    loss_distribution,
    DivergenceProfile,
)
from hamutay.eval.trajectory import (
    trajectory_stats,
    compare_trajectories,
    TrajectoryComparison,
)
from hamutay.eval.concepts import (
    concept_trajectory,
    concept_overlap,
)
from hamutay.eval.strand_analysis import (
    strand_separation,
    strand_separation_trajectory,
)


EXPERIMENT_DIR = Path(__file__).resolve().parents[3] / "experiments" / "q2_declared_losses"


def _load_tensor(path: Path) -> Tensor:
    """Load a tensor from JSON, handling the raw dict format."""
    raw = json.loads(path.read_text())

    strands = []
    for s in raw.get("strands", []):
        claims = []
        for c in s.get("key_claims", []):
            ep = c.get("epistemic", {})
            claims.append(KeyClaim(
                text=c.get("text", ""),
                epistemic=EpistemicState(
                    truth=ep.get("truth", 0.0),
                    indeterminacy=ep.get("indeterminacy", 0.0),
                    falsity=ep.get("falsity", 0.0),
                ),
            ))
        strands.append(Strand(
            title=s.get("title", ""),
            content=s.get("content", ""),
            key_claims=tuple(claims),
        ))

    losses = []
    for d in raw.get("declared_losses", []):
        cat_str = d.get("category", "practical_constraint")
        try:
            cat = LossCategory(cat_str)
        except ValueError:
            cat = LossCategory.PRACTICAL_CONSTRAINT
        losses.append(DeclaredLoss(
            what_was_lost=d.get("what_was_lost", ""),
            why=d.get("why", ""),
            category=cat,
        ))

    ep = raw.get("epistemic", {})
    ifn = raw.get("instructions_for_next", "")
    if isinstance(ifn, list):
        ifn = "\n".join(str(i) for i in ifn)

    return Tensor(
        cycle=raw.get("cycle", 0),
        strands=tuple(strands),
        declared_losses=tuple(losses),
        open_questions=tuple(str(q) for q in raw.get("open_questions", [])),
        instructions_for_next=str(ifn),
        epistemic=EpistemicState(
            truth=ep.get("truth", 0.0),
            indeterminacy=ep.get("indeterminacy", 0.0),
            falsity=ep.get("falsity", 0.0),
        ),
    )


def _load_condition(name: str) -> list[Tensor]:
    """Load all tensors for a condition, sorted by cycle."""
    tensor_dir = EXPERIMENT_DIR / name / "tensors"
    if not tensor_dir.exists():
        print(f"ERROR: {tensor_dir} not found", file=sys.stderr)
        sys.exit(1)

    tensors = []
    for path in sorted(tensor_dir.glob("tensor_cycle_*.json")):
        tensors.append(_load_tensor(path))

    tensors.sort(key=lambda t: t.cycle)
    return tensors


def _print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def _print_trajectory_summary(name: str, stats) -> None:
    print(f"  {name}:")
    s = stats.summary()
    for k, v in s.items():
        print(f"    {k}: {v}")


def _print_divergence_at_cycles(
    control: list[Tensor],
    treatment: list[Tensor],
    cycles: list[int],
) -> None:
    """Print detailed divergence profiles at specific cycles."""
    treat_by_cycle = {t.cycle: t for t in treatment}

    for cycle in cycles:
        ctrl = next((t for t in control if t.cycle == cycle), None)
        treat = treat_by_cycle.get(cycle)
        if ctrl is None or treat is None:
            continue

        profile = divergence_profile(ctrl, treat)
        print(f"  Cycle {cycle}:")
        for k, v in profile.summary().items():
            if k.startswith("cycle_"):
                continue
            print(f"    {k}: {v}")
        print()


def _print_capacity_evolution(comparison: TrajectoryComparison) -> None:
    """Show how content vs meta allocation evolves in both conditions."""
    print("  Cycle | Control content/meta | Treatment content/meta | Divergence")
    print("  " + "-" * 68)

    # Sample every 10 cycles
    cap_a = comparison.stats_a.capacity_series
    cap_b = comparison.stats_b.capacity_series
    divs = comparison.cross_divergence

    n = min(len(cap_a), len(cap_b), len(divs))
    for i in range(0, n, 10):
        cycle = i + 1
        print(
            f"  {cycle:5d} | "
            f"{cap_a[i].content_frac:.2f} / {cap_a[i].meta_frac:.2f}         | "
            f"{cap_b[i].content_frac:.2f} / {cap_b[i].meta_frac:.2f}           | "
            f"{divs[i].overall:.3f}"
        )
    # Always show last
    if n > 0:
        i = n - 1
        cycle = i + 1
        print(
            f"  {cycle:5d} | "
            f"{cap_a[i].content_frac:.2f} / {cap_a[i].meta_frac:.2f}         | "
            f"{cap_b[i].content_frac:.2f} / {cap_b[i].meta_frac:.2f}           | "
            f"{divs[i].overall:.3f}"
        )


def _print_loss_evolution(comparison: TrajectoryComparison) -> None:
    """Show how loss distributions evolve."""
    print("  Cycle | Control losses (cat distribution) | Treatment losses")
    print("  " + "-" * 64)

    ld_a = comparison.stats_a.loss_distributions
    ld_b = comparison.stats_b.loss_distributions

    n = min(len(ld_a), len(ld_b))
    for i in range(0, n, 20):
        cycle = i + 1
        a_cats = ", ".join(f"{k[:4]}={v}" for k, v in ld_a[i].by_category.items() if v > 0)
        b_cats = ", ".join(f"{k[:4]}={v}" for k, v in ld_b[i].by_category.items() if v > 0)
        print(f"  {cycle:5d} | {ld_a[i].total_losses:2d} ({a_cats or 'none'})")
        print(f"        | {ld_b[i].total_losses:2d} ({b_cats or 'none'})")
    # Last cycle
    if n > 0:
        i = n - 1
        cycle = i + 1
        a_cats = ", ".join(f"{k[:4]}={v}" for k, v in ld_a[i].by_category.items() if v > 0)
        b_cats = ", ".join(f"{k[:4]}={v}" for k, v in ld_b[i].by_category.items() if v > 0)
        print(f"  {cycle:5d} | {ld_a[i].total_losses:2d} ({a_cats or 'none'})")
        print(f"        | {ld_b[i].total_losses:2d} ({b_cats or 'none'})")


def main() -> None:
    print("Loading Q2 experiment data...")
    control = _load_condition("control")
    treatment = _load_condition("no_prior_losses")
    print(f"  Control: {len(control)} tensors, Treatment: {len(treatment)} tensors")

    # ── Individual trajectory analysis ──
    _print_section("TRAJECTORY ANALYSIS")

    ctrl_stats = trajectory_stats(control)
    treat_stats = trajectory_stats(treatment)

    _print_trajectory_summary("Control (sees prior losses)", ctrl_stats)
    print()
    _print_trajectory_summary("Treatment (no prior losses)", treat_stats)

    # ── Cross-trajectory comparison ──
    _print_section("CROSS-TRAJECTORY COMPARISON")

    comparison = compare_trajectories(control, treatment)
    print("  Summary:")
    for k, v in comparison.summary().items():
        if k in ("stats_a", "stats_b"):
            continue
        print(f"    {k}: {v}")

    # ── Detailed divergence at key cycles ──
    _print_section("DIVERGENCE PROFILES AT KEY CYCLES")
    _print_divergence_at_cycles(control, treatment, [1, 10, 25, 50, 75, 104])

    # ── Capacity allocation evolution ──
    _print_section("CAPACITY ALLOCATION EVOLUTION (content/meta ratio)")
    _print_capacity_evolution(comparison)

    # ── Loss distribution evolution ──
    _print_section("LOSS DISTRIBUTION EVOLUTION")
    _print_loss_evolution(comparison)

    # ── The big questions ──
    _print_section("OBSERVATIONS")

    # 1. Where does divergence peak?
    if comparison.max_divergence_cycle is not None:
        print(f"  Peak divergence at cycle {comparison.max_divergence_cycle}")
        print(f"  Divergence trend: {comparison.divergence_trend}")

    # 2. Is the tensor eating itself?
    if ctrl_stats.capacity_series:
        ctrl_final_meta = ctrl_stats.capacity_series[-1].meta_frac
        treat_final_meta = treat_stats.capacity_series[-1].meta_frac
        print(f"\n  Final meta-cognitive fraction:")
        print(f"    Control: {ctrl_final_meta:.2f}")
        print(f"    Treatment: {treat_final_meta:.2f}")
        if ctrl_final_meta > 0.5:
            print("    WARNING: Control tensor spending >50% on meta-cognition")
        if treat_final_meta > 0.5:
            print("    WARNING: Treatment tensor spending >50% on meta-cognition")

    # 3. IFN compensation
    print(f"\n  IFN compensation detected:")
    print(f"    Control: {ctrl_stats.ifn_compensation_detected}")
    print(f"    Treatment: {treat_stats.ifn_compensation_detected}")

    # 4. Strand dynamics
    print(f"\n  Strand dynamics:")
    print(f"    Control: {ctrl_stats.strand_birth_rate:.2f} births/cycle, "
          f"{ctrl_stats.strand_death_rate:.2f} deaths/cycle, "
          f"stability={ctrl_stats.strand_stability:.2f}")
    print(f"    Treatment: {treat_stats.strand_birth_rate:.2f} births/cycle, "
          f"{treat_stats.strand_death_rate:.2f} deaths/cycle, "
          f"stability={treat_stats.strand_stability:.2f}")

    # ── Strand separation analysis ──
    _print_section("STRAND SEPARATION (what does structure buy?)")

    ctrl_sep = strand_separation_trajectory(control)
    treat_sep = strand_separation_trajectory(treatment)

    print("  Cycle | Ctrl strands/jaccard/specialization | Treat strands/jaccard/specialization")
    print("  " + "-" * 76)
    for i in range(0, min(len(ctrl_sep), len(treat_sep)), 10):
        c = ctrl_sep[i]
        t = treat_sep[i]
        print(
            f"  {i+1:5d} | "
            f"{c.n_strands}s jac={c.mean_pairwise_jaccard:.2f} spec={c.vocabulary_specialization:.2f} gini={c.size_gini:.2f} | "
            f"{t.n_strands}s jac={t.mean_pairwise_jaccard:.2f} spec={t.vocabulary_specialization:.2f} gini={t.size_gini:.2f}"
        )
    # Last cycle
    if ctrl_sep and treat_sep:
        c = ctrl_sep[-1]
        t = treat_sep[-1]
        print(
            f"  {len(ctrl_sep):5d} | "
            f"{c.n_strands}s jac={c.mean_pairwise_jaccard:.2f} spec={c.vocabulary_specialization:.2f} gini={c.size_gini:.2f} | "
            f"{t.n_strands}s jac={t.mean_pairwise_jaccard:.2f} spec={t.vocabulary_specialization:.2f} gini={t.size_gini:.2f}"
        )

    # Summary stats
    ctrl_mean_jac = sum(s.mean_pairwise_jaccard for s in ctrl_sep) / len(ctrl_sep)
    ctrl_mean_spec = sum(s.vocabulary_specialization for s in ctrl_sep) / len(ctrl_sep)
    treat_mean_jac = sum(s.mean_pairwise_jaccard for s in treat_sep) / len(treat_sep)
    treat_mean_spec = sum(s.vocabulary_specialization for s in treat_sep) / len(treat_sep)
    print(f"\n  Mean pairwise Jaccard (lower = better separation):")
    print(f"    Control: {ctrl_mean_jac:.3f}")
    print(f"    Treatment: {treat_mean_jac:.3f}")
    print(f"  Mean vocabulary specialization (higher = more distinct strands):")
    print(f"    Control: {ctrl_mean_spec:.3f}")
    print(f"    Treatment: {treat_mean_spec:.3f}")

    # ── Concept persistence analysis ──
    _print_section("CONCEPT PERSISTENCE (what survives strand restructuring?)")

    ctrl_concepts = concept_trajectory(control)
    treat_concepts = concept_trajectory(treatment)

    print("  Control concepts:")
    for k, v in ctrl_concepts.summary().items():
        print(f"    {k}: {v}")

    print(f"\n  Treatment concepts:")
    for k, v in treat_concepts.summary().items():
        print(f"    {k}: {v}")

    # Cross-trajectory concept overlap
    overlap = concept_overlap(ctrl_concepts, treat_concepts)
    print(f"\n  Cross-trajectory concept overlap:")
    print(f"    Shared concepts: {overlap['shared_count']}")
    print(f"    Control-only concepts: {overlap['only_a_count']}")
    print(f"    Treatment-only concepts: {overlap['only_b_count']}")
    print(f"    Concept Jaccard: {overlap['concept_jaccard']:.3f}")
    if overlap['shared_top']:
        print(f"    Most shared concepts: {overlap['shared_top'][:10]}")

    print()


if __name__ == "__main__":
    main()
