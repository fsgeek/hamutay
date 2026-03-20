"""Multi-cycle trajectory ablation: which fields stabilize long-horizon projection?

The N=20 ablation measured downstream quality from a single tensor (snapshot).
But Q2 showed that losses and IFN matter for trajectory dynamics — coupled
channels, metacognitive capacity — effects that only emerge over many cycles.

Hypothesis (multi-timescale): tensor components have different time constants.
  - Strand separation: immediate per-cycle effect (categorization pressure)
  - Losses / IFN: trajectory-scale effect (self-model maintenance, stabilization)

Design:
  - Run the Projector for 50 cycles on the observation_full input
  - Four conditions using Projector subclasses:
    1. full (baseline)
    2. masked_losses (never sees prior losses — replicates Q2 treatment)
    3. masked_ifn (never sees prior instructions_for_next)
    4. masked_both (losses AND ifn masked — the coupled channel test)
  - Measure trajectory health at each cycle using eval instruments:
    strand stability, capacity allocation, consecutive divergence

This tests whether fields that don't matter at snapshot scale (N=20 ablation)
are load-bearing at trajectory scale (50+ cycles).

Cost: 4 conditions × 50 cycles × 1 Haiku call = 200 Haiku calls ≈ $2
(Haiku projection is cheap; the observation data is already prepared)

Usage:
    uv run python -m hamutay.eval.trajectory_ablation [--dry-run] [--max-cycles N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from hamutay.projector import Projector, _parse_projection, _build_projection_prompt
from hamutay.tensor import Tensor
from hamutay.eval.trajectory import trajectory_stats, TrajectoryStats
from hamutay.eval.strand_analysis import strand_separation_trajectory
from hamutay.eval.divergence import capacity_allocation


EXPERIMENT_DIR = Path(__file__).resolve().parents[3] / "experiments"
OUTPUT_DIR = EXPERIMENT_DIR / "trajectory_ablation"
OBSERVATIONS = EXPERIMENT_DIR / "observation_full" / "observations.jsonl"


class MaskedLossProjector(Projector):
    """Never sees prior declared_losses. From Q2 experiment."""

    def _do_projection(self, new_content, model_override=None):
        original = self._current_tensor
        if original is not None:
            self._current_tensor = Tensor(
                cycle=original.cycle, strands=original.strands,
                declared_losses=(),
                open_questions=original.open_questions,
                instructions_for_next=original.instructions_for_next,
                epistemic=original.epistemic,
            )
        try:
            result = super()._do_projection(new_content, model_override)
        finally:
            self._current_tensor = original
        return result


class MaskedIFNProjector(Projector):
    """Never sees prior instructions_for_next."""

    def _do_projection(self, new_content, model_override=None):
        original = self._current_tensor
        if original is not None:
            self._current_tensor = Tensor(
                cycle=original.cycle, strands=original.strands,
                declared_losses=original.declared_losses,
                open_questions=original.open_questions,
                instructions_for_next="",
                epistemic=original.epistemic,
            )
        try:
            result = super()._do_projection(new_content, model_override)
        finally:
            self._current_tensor = original
        return result


class MaskedBothProjector(Projector):
    """Never sees prior losses OR instructions_for_next.

    The coupled channel test: what happens when both feedback
    mechanisms are removed simultaneously?
    """

    def _do_projection(self, new_content, model_override=None):
        original = self._current_tensor
        if original is not None:
            self._current_tensor = Tensor(
                cycle=original.cycle, strands=original.strands,
                declared_losses=(),
                open_questions=original.open_questions,
                instructions_for_next="",
                epistemic=original.epistemic,
            )
        try:
            result = super()._do_projection(new_content, model_override)
        finally:
            self._current_tensor = original
        return result


CONDITIONS = [
    ("full", "Baseline — full tensor feedback", Projector),
    ("no_losses", "Losses masked (Q2 treatment replication)", MaskedLossProjector),
    ("no_ifn", "Instructions_for_next masked", MaskedIFNProjector),
    ("no_both", "Losses AND IFN masked (coupled channel)", MaskedBothProjector),
]


def _load_observations(max_cycles: int) -> list[dict]:
    """Load cycle content from observations.jsonl."""
    cycles = []
    with open(OBSERVATIONS) as f:
        for line in f:
            entry = json.loads(line)
            cycles.append(entry)
            if entry["cycle"] >= max_cycles:
                break
    return cycles


@dataclass
class CycleResult:
    cycle: int
    n_strands: int
    n_losses: int
    has_ifn: bool
    token_count: int
    stop_reason: str
    content_frac: float
    meta_frac: float
    collapsed: bool


@dataclass
class ConditionTrajectory:
    name: str
    description: str
    tensors: list[Tensor]
    cycle_results: list[CycleResult]
    stats: TrajectoryStats | None = None
    collapses: int = 0
    total_time_s: float = 0.0


def _run_condition(
    name: str,
    description: str,
    projector_class: type,
    observations: list[dict],
    client: anthropic.Anthropic,
) -> ConditionTrajectory:
    """Run one condition through all cycles."""
    projector = projector_class(client=client)
    tensors = []
    results = []
    collapses = 0

    t0 = time.monotonic()
    for obs in observations:
        cycle = obs["cycle"]
        content = obs["batch_content"]

        tensor = projector.project(content)
        tensors.append(tensor)

        cap = capacity_allocation(tensor)
        collapsed = projector._is_collapsed(tensor) if projector._current_tensor else False
        if collapsed:
            collapses += 1

        results.append(CycleResult(
            cycle=cycle,
            n_strands=len(tensor.strands),
            n_losses=len(tensor.declared_losses),
            has_ifn=bool(tensor.instructions_for_next),
            token_count=tensor.token_estimate(),
            stop_reason=projector.last_stop_reason,
            content_frac=cap.content_frac,
            meta_frac=cap.meta_frac,
            collapsed=collapsed,
        ))

        # Progress
        if cycle % 10 == 0 or cycle == 1:
            print(f"    cycle {cycle:3d}: {len(tensor.strands)} strands, "
                  f"{tensor.token_estimate():5d} tok, "
                  f"losses={len(tensor.declared_losses)}, "
                  f"ifn={'Y' if tensor.instructions_for_next else 'N'}, "
                  f"content/meta={cap.content_frac:.2f}/{cap.meta_frac:.2f}")

    elapsed = time.monotonic() - t0
    stats = trajectory_stats(tensors)

    return ConditionTrajectory(
        name=name, description=description,
        tensors=tensors, cycle_results=results,
        stats=stats, collapses=collapses,
        total_time_s=elapsed,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=50)
    args = parser.parse_args()

    print("=" * 60)
    print("  Multi-Cycle Trajectory Ablation")
    print("  Which fields stabilize long-horizon projection?")
    print("=" * 60)

    n_cycles = args.max_cycles
    n_calls = len(CONDITIONS) * n_cycles
    print(f"\n  {len(CONDITIONS)} conditions × {n_cycles} cycles = {n_calls} Haiku calls")
    print(f"  Estimated cost: ${n_calls * 0.005:.2f}")

    if args.dry_run:
        print("\n  [DRY RUN]")
        for name, desc, _ in CONDITIONS:
            print(f"    {name}: {desc}")
        return

    observations = _load_observations(n_cycles)
    print(f"\n  Loaded {len(observations)} cycles of observation data")

    client = anthropic.Anthropic()
    trajectories: list[ConditionTrajectory] = []

    for name, desc, projector_class in CONDITIONS:
        print(f"\n  Condition: {name} ({desc})")
        traj = _run_condition(name, desc, projector_class, observations, client)
        trajectories.append(traj)
        print(f"    Done: {traj.collapses} collapses, {traj.total_time_s:.0f}s")

    # Results
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)

    for traj in trajectories:
        s = traj.stats
        print(f"\n  {traj.name}:")
        print(f"    Collapses: {traj.collapses}")
        if s:
            summary = s.summary()
            for k, v in summary.items():
                print(f"    {k}: {v}")

    # Compare trajectory health
    print("\n  TRAJECTORY HEALTH COMPARISON")
    print(f"  {'Condition':12s} | Collapses | StrandStab | LossEvol  | IFN Comp | FinalMeta")
    print("  " + "-" * 72)
    for traj in trajectories:
        s = traj.stats
        if s:
            print(f"  {traj.name:12s} | {traj.collapses:9d} | "
                  f"{s.strand_stability:.3f}      | {s.loss_evolution:9s} | "
                  f"{'Yes' if s.ifn_compensation_detected else 'No':8s} | "
                  f"{s.capacity_series[-1].meta_frac:.3f}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_data = {
        "experiment": "trajectory_ablation",
        "max_cycles": n_cycles,
        "conditions": [],
    }
    for traj in trajectories:
        cond = {
            "name": traj.name,
            "description": traj.description,
            "collapses": traj.collapses,
            "total_time_s": traj.total_time_s,
            "summary": traj.stats.summary() if traj.stats else {},
            "cycles": [
                {
                    "cycle": r.cycle, "n_strands": r.n_strands,
                    "n_losses": r.n_losses, "has_ifn": r.has_ifn,
                    "token_count": r.token_count, "stop_reason": r.stop_reason,
                    "content_frac": r.content_frac, "meta_frac": r.meta_frac,
                    "collapsed": r.collapsed,
                }
                for r in traj.cycle_results
            ],
        }
        save_data["conditions"].append(cond)

    (OUTPUT_DIR / "results.json").write_text(json.dumps(save_data, indent=2))
    print(f"\n  Saved to {OUTPUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
