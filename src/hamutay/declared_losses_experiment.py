"""Q1: Are declared losses a projection feedback signal?

Hypothesis: declared_losses in the prior tensor create counter-pressure
to mode collapse during iterative projection. Without them, the projector
progressively narrows its attention across cycles.

Design: replay the 104-cycle observation corpus through the projector
under two conditions:
  - control: normal iterative projection (full prior tensor)
  - treatment: declared_losses zeroed in the prior tensor before each cycle
    (projector still *produces* losses, but never *sees* its own prior ones)

The key insight: the prior ablation study tested whether the *consumer*
needs declared_losses (answer: no). This tests whether the *projector*
needs to see its own prior declared_losses to stay coherent (hypothesis: yes).

Measurements per cycle:
  - strand count and title stability
  - declared_losses count (does the projector stop declaring losses?)
  - tensor token size (collapse or bloat?)
  - instructions_for_next length
  - semantic breadth via embedding dispersion (if available)

What we're looking for: divergence over cycles. Early cycles should be
similar. Later cycles should diverge if the hypothesis holds.

Usage:
    uv run python -m hamutay.declared_losses_experiment \\
        experiments/observation_full/observations.jsonl \\
        experiments/q1_declared_losses \\
        [--max-cycles N]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from hamutay.projector import Projector, _build_projection_prompt, _parse_projection
from hamutay.tensor import Tensor


@dataclass
class CycleMetrics:
    """Per-cycle measurements for one condition."""

    cycle: int
    n_strands: int
    strand_titles: list[str]
    n_losses: int
    n_open_questions: int
    tensor_tokens: int
    ifn_length: int
    has_ifn: bool
    stop_reason: str
    projection_time_s: float

    # Stability metrics (relative to prior cycle)
    strands_added: int = 0
    strands_removed: int = 0
    strands_stable: int = 0

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "n_strands": self.n_strands,
            "strand_titles": self.strand_titles,
            "n_losses": self.n_losses,
            "n_open_questions": self.n_open_questions,
            "tensor_tokens": self.tensor_tokens,
            "ifn_length": self.ifn_length,
            "has_ifn": self.has_ifn,
            "stop_reason": self.stop_reason,
            "projection_time_s": self.projection_time_s,
            "strands_added": self.strands_added,
            "strands_removed": self.strands_removed,
            "strands_stable": self.strands_stable,
        }


@dataclass
class ConditionRun:
    """Results from running one condition across all cycles."""

    name: str
    description: str
    metrics: list[CycleMetrics] = field(default_factory=list)
    tensors: list[dict] = field(default_factory=list)
    total_cost_estimate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "total_cost_estimate": self.total_cost_estimate,
            "metrics": [m.to_dict() for m in self.metrics],
        }


def _mask_declared_losses(tensor: Tensor) -> Tensor:
    """Return a copy of the tensor with declared_losses emptied.

    The projector will see everything else — strands, open_questions,
    instructions_for_next, epistemic state — but not what it previously
    declared it lost. This is the surgical intervention.
    """
    return Tensor(
        cycle=tensor.cycle,
        strands=tensor.strands,
        declared_losses=(),  # the intervention
        open_questions=tensor.open_questions,
        instructions_for_next=tensor.instructions_for_next,
        epistemic=tensor.epistemic,
    )


def _compute_stability(
    prev_titles: list[str], curr_titles: list[str]
) -> tuple[int, int, int]:
    """Compute strand stability between consecutive cycles."""
    prev_set = set(prev_titles)
    curr_set = set(curr_titles)
    added = len(curr_set - prev_set)
    removed = len(prev_set - curr_set)
    stable = len(curr_set & prev_set)
    return added, removed, stable


def run_condition(
    name: str,
    description: str,
    observations: list[dict],
    client: anthropic.Anthropic,
    model: str,
    mask_losses: bool = False,
    max_cycles: int | None = None,
) -> ConditionRun:
    """Run one experimental condition across all observation cycles.

    For each cycle, we feed the projector the same batch_content from
    the original observation run. The only difference between conditions
    is whether the prior tensor's declared_losses are visible.
    """
    run = ConditionRun(name=name, description=description)
    current_tensor: Tensor | None = None
    prev_titles: list[str] = []

    cycles = observations
    if max_cycles:
        cycles = cycles[:max_cycles]

    for obs in cycles:
        cycle_num = obs["cycle"]
        batch_content = obs["batch_content"]

        # The intervention: mask declared_losses from the prior tensor
        prior_for_prompt = current_tensor
        if mask_losses and current_tensor is not None:
            prior_for_prompt = _mask_declared_losses(current_tensor)

        prompt = _build_projection_prompt(prior_for_prompt, batch_content, cycle_num)

        start = time.perf_counter()
        response = client.messages.create(
            model=model,
            max_tokens=16384,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": "emit_tensor",
                    "description": "Emit the updated tensor projection",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "strands": {"type": "array", "items": {"type": "object"}},
                            "declared_losses": {"type": "array", "items": {"type": "object"}},
                            "open_questions": {"type": "array", "items": {"type": "string"}},
                            "instructions_for_next": {"type": "string"},
                            "overall_truth": {"type": "number"},
                            "overall_indeterminacy": {"type": "number"},
                            "overall_falsity": {"type": "number"},
                        },
                        "required": [
                            "strands", "declared_losses", "open_questions",
                            "instructions_for_next", "overall_truth",
                            "overall_indeterminacy", "overall_falsity",
                        ],
                    },
                }
            ],
            tool_choice={"type": "tool", "name": "emit_tensor"},
        )
        elapsed = time.perf_counter() - start
        stop_reason = response.stop_reason or "unknown"

        # Extract tensor
        raw_tensor = None
        for block in response.content:
            if block.type == "tool_use" and block.name == "emit_tensor":
                raw_tensor = block.input
                break

        if raw_tensor is None:
            print(f"    WARNING: cycle {cycle_num} — no tensor emitted, skipping")
            continue

        tensor = _parse_projection(raw_tensor, cycle_num)
        current_tensor = tensor

        # Compute metrics
        curr_titles = [s.title for s in tensor.strands]
        added, removed, stable = _compute_stability(prev_titles, curr_titles)

        metrics = CycleMetrics(
            cycle=cycle_num,
            n_strands=len(tensor.strands),
            strand_titles=curr_titles,
            n_losses=len(tensor.declared_losses),
            n_open_questions=len(tensor.open_questions),
            tensor_tokens=tensor.token_estimate(),
            ifn_length=len(tensor.instructions_for_next),
            has_ifn=bool(tensor.instructions_for_next),
            stop_reason=stop_reason,
            projection_time_s=elapsed,
            strands_added=added,
            strands_removed=removed,
            strands_stable=stable,
        )

        run.metrics.append(metrics)
        run.tensors.append(raw_tensor)

        prev_titles = curr_titles

        # Progress
        print(
            f"  [{name}] cycle {cycle_num}: "
            f"{metrics.n_strands} strands "
            f"(+{added} -{removed} ={stable}), "
            f"{metrics.n_losses} losses, "
            f"~{metrics.tensor_tokens} tok, "
            f"{elapsed:.1f}s"
        )

        if stop_reason == "max_tokens":
            print(f"    WARNING: cycle {cycle_num} hit max_tokens — tensor truncated")

    return run


def run_experiment(
    observations_path: Path,
    output_dir: Path,
    max_cycles: int | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> None:
    """Run the declared losses feedback experiment."""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load observation corpus
    observations = []
    with open(observations_path) as f:
        for line in f:
            observations.append(json.loads(line.strip()))

    n_cycles = len(observations) if max_cycles is None else min(max_cycles, len(observations))
    print(f"Q1: Declared Losses as Projection Feedback")
    print(f"  Corpus: {observations_path} ({len(observations)} cycles)")
    print(f"  Running: {n_cycles} cycles × 2 conditions")
    print(f"  Model: {model}")
    print()

    client = anthropic.Anthropic()

    # Condition 1: Control — full tensor, normal projection
    print("=" * 60)
    print("CONDITION: control (full prior tensor)")
    print("=" * 60)
    control = run_condition(
        name="control",
        description="Normal iterative projection with full prior tensor",
        observations=observations,
        client=client,
        model=model,
        mask_losses=False,
        max_cycles=max_cycles,
    )

    print()

    # Condition 2: Treatment — declared_losses masked from prior tensor
    print("=" * 60)
    print("CONDITION: no_prior_losses (declared_losses masked)")
    print("=" * 60)
    treatment = run_condition(
        name="no_prior_losses",
        description="Prior tensor's declared_losses zeroed before each projection",
        observations=observations,
        client=client,
        model=model,
        mask_losses=True,
        max_cycles=max_cycles,
    )

    # Save raw results
    results = {
        "experiment": "q1_declared_losses_feedback",
        "hypothesis": (
            "Declared losses in the prior tensor create counter-pressure "
            "to mode collapse during iterative projection."
        ),
        "model": model,
        "n_cycles": n_cycles,
        "conditions": {
            "control": control.to_dict(),
            "no_prior_losses": treatment.to_dict(),
        },
    }

    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2))

    # Save tensors for later analysis
    for condition_name, run in [("control", control), ("no_prior_losses", treatment)]:
        tensor_dir = output_dir / condition_name / "tensors"
        tensor_dir.mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(run.tensors):
            path = tensor_dir / f"tensor_cycle_{i + 1:03d}.json"
            path.write_text(json.dumps(t, indent=2))

    # Print comparative summary
    _print_summary(control, treatment)

    print(f"\nResults written to {results_path}")


def _print_summary(control: ConditionRun, treatment: ConditionRun) -> None:
    """Print side-by-side comparison of the two conditions."""

    print()
    print("=" * 75)
    print("COMPARATIVE SUMMARY")
    print("=" * 75)
    print(
        f"{'Metric':<30} {'Control':>20} {'No Prior Losses':>20}"
    )
    print("-" * 75)

    def _avg(metrics: list[CycleMetrics], attr: str) -> float:
        vals = [getattr(m, attr) for m in metrics]
        return sum(vals) / len(vals) if vals else 0

    def _avg_last_half(metrics: list[CycleMetrics], attr: str) -> float:
        """Average over the second half — where divergence should appear."""
        half = len(metrics) // 2
        vals = [getattr(m, attr) for m in metrics[half:]]
        return sum(vals) / len(vals) if vals else 0

    rows = [
        ("Avg strands (all)", "n_strands", False),
        ("Avg strands (2nd half)", "n_strands", True),
        ("Avg losses declared (all)", "n_losses", False),
        ("Avg losses declared (2nd half)", "n_losses", True),
        ("Avg tensor tokens (all)", "tensor_tokens", False),
        ("Avg tensor tokens (2nd half)", "tensor_tokens", True),
        ("Avg ifn length (all)", "ifn_length", False),
        ("Avg ifn length (2nd half)", "ifn_length", True),
        ("Avg strands removed/cycle (all)", "strands_removed", False),
        ("Avg strands removed/cycle (2nd half)", "strands_removed", True),
        ("Avg strands added/cycle (all)", "strands_added", False),
        ("Avg strands stable/cycle (all)", "strands_stable", False),
    ]

    for label, attr, second_half in rows:
        fn = _avg_last_half if second_half else _avg
        c_val = fn(control.metrics, attr)
        t_val = fn(treatment.metrics, attr)
        print(f"  {label:<28} {c_val:>20.1f} {t_val:>20.1f}")

    # Strand title overlap between conditions at each cycle
    print()
    print("Strand title overlap (control ∩ treatment) per cycle:")
    min_len = min(len(control.metrics), len(treatment.metrics))
    overlaps = []
    for i in range(min_len):
        c_titles = set(control.metrics[i].strand_titles)
        t_titles = set(treatment.metrics[i].strand_titles)
        if c_titles or t_titles:
            jaccard = len(c_titles & t_titles) / len(c_titles | t_titles)
            overlaps.append(jaccard)

    if overlaps:
        first_quarter = overlaps[: len(overlaps) // 4] or overlaps[:1]
        last_quarter = overlaps[-(len(overlaps) // 4):] or overlaps[-1:]
        print(
            f"  First quarter avg Jaccard: {sum(first_quarter) / len(first_quarter):.3f}"
        )
        print(
            f"  Last quarter avg Jaccard:  {sum(last_quarter) / len(last_quarter):.3f}"
        )
        print(
            f"  (Divergence = first quarter >> last quarter)"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Q1: Declared losses as projection feedback signal"
    )
    parser.add_argument(
        "observations",
        type=Path,
        help="Path to observations.jsonl from observation experiment",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory for experiment results",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Limit number of cycles (for smoke testing)",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Projector model",
    )
    args = parser.parse_args()

    run_experiment(
        args.observations,
        args.output_dir,
        max_cycles=args.max_cycles,
        model=args.model,
    )


if __name__ == "__main__":
    main()
