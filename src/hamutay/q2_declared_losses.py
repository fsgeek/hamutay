"""Q2: Declared losses as differentiation mechanism.

Rerun of Q1 with confounds fixed:
  1. Uses Projector class (collapse recovery, precursor detection, full schema)
  2. max_tokens = 64000 with streaming (no truncation artifacts)
  3. Treatment is a Projector subclass, not raw API calls

Hypothesis (refined from Q1 qualitative analysis): declared_losses in the
prior tensor function as a differentiation mechanism. A projector that sees
its own prior losses develops increasingly sophisticated loss taxonomy.
A projector denied this feedback produces structurally uniform output.

See experiments/q2_declared_losses/PRE_REGISTRATION.md for the full
pre-registered analysis plan including loss sophistication classification.

Usage:
    uv run python -m hamutay.q2_declared_losses \\
        experiments/observation_full/observations.jsonl \\
        experiments/q2_declared_losses \\
        [--max-cycles N]
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from hamutay.projector import Projector
from hamutay.tensor import Tensor


class MaskedLossProjector(Projector):
    """Projector that never sees its own prior declared_losses.

    The surgical intervention: before each projection, temporarily
    replace the current tensor's declared_losses with an empty tuple.
    Everything else — strands, open_questions, instructions_for_next,
    epistemic state, collapse detection, recovery, streaming — is
    inherited from Projector unchanged.

    The projector still *produces* declared_losses in its output.
    It just never sees its own prior ones.
    """

    def _do_projection(
        self, new_content: str, model_override: str | None = None
    ) -> tuple[Tensor, str]:
        """Mask declared_losses, then delegate to parent."""
        original = self._current_tensor

        if original is not None:
            self._current_tensor = Tensor(
                cycle=original.cycle,
                strands=original.strands,
                declared_losses=(),  # the intervention
                open_questions=original.open_questions,
                instructions_for_next=original.instructions_for_next,
                epistemic=original.epistemic,
            )

        try:
            result = super()._do_projection(new_content, model_override)
        finally:
            # Restore so collapse detection etc. sees the real tensor
            self._current_tensor = original

        return result


@dataclass
class CycleMetrics:
    """Per-cycle measurements for one condition."""

    cycle: int
    n_strands: int
    strand_titles: list[str]
    n_losses: int
    loss_categories: list[str]
    n_open_questions: int
    tensor_tokens: int
    ifn_length: int
    has_ifn: bool
    stop_reason: str
    projection_time_s: float
    collapsed: bool
    recovered: bool
    precursor: bool

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
            "loss_categories": self.loss_categories,
            "n_open_questions": self.n_open_questions,
            "tensor_tokens": self.tensor_tokens,
            "ifn_length": self.ifn_length,
            "has_ifn": self.has_ifn,
            "stop_reason": self.stop_reason,
            "projection_time_s": self.projection_time_s,
            "collapsed": self.collapsed,
            "recovered": self.recovered,
            "precursor": self.precursor,
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
    escalation_log: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "metrics": [m.to_dict() for m in self.metrics],
            "escalation_log": self.escalation_log,
        }


def _compute_stability(
    prev_titles: list[str], curr_titles: list[str]
) -> tuple[int, int, int]:
    """Compute strand stability between consecutive cycles."""
    prev_set = set(prev_titles)
    curr_set = set(curr_titles)
    return (
        len(curr_set - prev_set),
        len(prev_set - curr_set),
        len(curr_set & prev_set),
    )


def run_condition(
    name: str,
    description: str,
    observations: list[dict],
    client: anthropic.Anthropic,
    model: str,
    mask_losses: bool = False,
    max_cycles: int | None = None,
) -> ConditionRun:
    """Run one experimental condition using the Projector class.

    This is the key difference from Q1: we use the actual Projector
    (or MaskedLossProjector) instead of raw API calls. This gives us
    collapse detection, checkpoint/recovery, precursor detection,
    and the full PROJECTION_SCHEMA.
    """
    run = ConditionRun(name=name, description=description)

    if mask_losses:
        projector = MaskedLossProjector(client=client, model=model)
    else:
        projector = Projector(client=client, model=model)

    prev_titles: list[str] = []

    cycles = observations
    if max_cycles:
        cycles = cycles[:max_cycles]

    for obs in cycles:
        cycle_num = obs["cycle"]
        batch_content = obs["batch_content"]

        prior_tokens = (
            projector.current_tensor.token_estimate()
            if projector.current_tensor
            else 0
        )

        start = time.perf_counter()
        tensor = projector.project(batch_content)
        elapsed = time.perf_counter() - start

        # Detect if this cycle involved a collapse and recovery
        # by checking if token count dropped dramatically and came back
        new_tokens = tensor.token_estimate()
        collapsed = (
            prior_tokens > 0
            and new_tokens / prior_tokens < projector._collapse_threshold
        )
        # If the projector logged a recovery, the last escalation entry tells us
        last_log = projector.escalation_log[-1] if projector.escalation_log else {}
        recovered = last_log.get("escalated", False) and not collapsed

        curr_titles = [s.title for s in tensor.strands]
        added, removed, stable = _compute_stability(prev_titles, curr_titles)

        loss_categories = [loss.category.value for loss in tensor.declared_losses]

        metrics = CycleMetrics(
            cycle=cycle_num,
            n_strands=len(tensor.strands),
            strand_titles=curr_titles,
            n_losses=len(tensor.declared_losses),
            loss_categories=loss_categories,
            n_open_questions=len(tensor.open_questions),
            tensor_tokens=new_tokens,
            ifn_length=len(tensor.instructions_for_next),
            has_ifn=bool(tensor.instructions_for_next),
            stop_reason=projector.last_stop_reason,
            projection_time_s=elapsed,
            collapsed=collapsed,
            recovered=recovered,
            precursor=projector._precursor_detected,
            strands_added=added,
            strands_removed=removed,
            strands_stable=stable,
        )

        run.metrics.append(metrics)

        # Save raw tensor for qualitative analysis
        run.tensors.append(json.loads(tensor.model_dump_json()))

        prev_titles = curr_titles

        print(
            f"  [{name}] cycle {cycle_num}: "
            f"{metrics.n_strands} strands "
            f"(+{added} -{removed} ={stable}), "
            f"{metrics.n_losses} losses [{','.join(loss_categories) or 'none'}], "
            f"~{metrics.tensor_tokens} tok, "
            f"{elapsed:.1f}s"
            f"{' TRUNCATED' if metrics.stop_reason == 'max_tokens' else ''}"
            f"{' PRECURSOR' if metrics.precursor else ''}"
        )

    run.escalation_log = projector.escalation_log
    return run


def run_experiment(
    observations_path: Path,
    output_dir: Path,
    max_cycles: int | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> None:
    """Run the Q2 declared losses experiment."""

    output_dir.mkdir(parents=True, exist_ok=True)

    observations = []
    with open(observations_path) as f:
        for line in f:
            observations.append(json.loads(line.strip()))

    n_cycles = (
        len(observations) if max_cycles is None
        else min(max_cycles, len(observations))
    )
    print("Q2: Declared Losses as Differentiation Mechanism")
    print(f"  Corpus: {observations_path} ({len(observations)} cycles)")
    print(f"  Running: {n_cycles} cycles x 2 conditions")
    print(f"  Model: {model}")
    print(f"  max_tokens: 64000 (streaming)")
    print(f"  Infrastructure: Projector class (collapse recovery, precursor detection)")
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
        "experiment": "q2_declared_losses_differentiation",
        "hypothesis": (
            "Declared losses in the prior tensor function as a differentiation "
            "mechanism: a projector that sees its own prior losses develops "
            "increasingly sophisticated loss taxonomy over iterative cycles."
        ),
        "pre_registration": "experiments/q2_declared_losses/PRE_REGISTRATION.md",
        "model": model,
        "max_tokens": 64000,
        "n_cycles": n_cycles,
        "infrastructure": "Projector class with collapse recovery and precursor detection",
        "conditions": {
            "control": control.to_dict(),
            "no_prior_losses": treatment.to_dict(),
        },
    }

    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2))

    # Save tensors for qualitative analysis
    for condition_name, run in [("control", control), ("no_prior_losses", treatment)]:
        tensor_dir = output_dir / condition_name / "tensors"
        tensor_dir.mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(run.tensors):
            path = tensor_dir / f"tensor_cycle_{i + 1:03d}.json"
            path.write_text(json.dumps(t, indent=2))

    _print_summary(control, treatment)

    print(f"\nResults written to {results_path}")
    print(f"Tensors saved for qualitative analysis in {output_dir}/*/tensors/")
    print(f"\nNext: classify declared losses per PRE_REGISTRATION.md")


def _print_summary(control: ConditionRun, treatment: ConditionRun) -> None:
    """Print side-by-side comparison."""

    print()
    print("=" * 75)
    print("COMPARATIVE SUMMARY")
    print("=" * 75)
    print(f"{'Metric':<35} {'Control':>18} {'No Prior Losses':>18}")
    print("-" * 75)

    def _avg(metrics: list[CycleMetrics], attr: str) -> float:
        vals = [getattr(m, attr) for m in metrics]
        return sum(vals) / len(vals) if vals else 0

    def _avg_half(metrics: list[CycleMetrics], attr: str, second: bool) -> float:
        half = len(metrics) // 2
        subset = metrics[half:] if second else metrics[:half]
        vals = [getattr(m, attr) for m in subset]
        return sum(vals) / len(vals) if vals else 0

    rows = [
        ("Avg strands (all)", "n_strands", "all"),
        ("Avg strands (1st half)", "n_strands", "1st"),
        ("Avg strands (2nd half)", "n_strands", "2nd"),
        ("Avg losses declared (all)", "n_losses", "all"),
        ("Avg losses declared (1st half)", "n_losses", "1st"),
        ("Avg losses declared (2nd half)", "n_losses", "2nd"),
        ("Avg tensor tokens (all)", "tensor_tokens", "all"),
        ("Avg tensor tokens (2nd half)", "tensor_tokens", "2nd"),
        ("Avg ifn length (all)", "ifn_length", "all"),
        ("Avg ifn length (2nd half)", "ifn_length", "2nd"),
    ]

    for label, attr, half in rows:
        if half == "all":
            c_val = _avg(control.metrics, attr)
            t_val = _avg(treatment.metrics, attr)
        elif half == "1st":
            c_val = _avg_half(control.metrics, attr, second=False)
            t_val = _avg_half(treatment.metrics, attr, second=False)
        else:
            c_val = _avg_half(control.metrics, attr, second=True)
            t_val = _avg_half(treatment.metrics, attr, second=True)
        print(f"  {label:<33} {c_val:>18.1f} {t_val:>18.1f}")

    # Zero-loss cycles
    c_zero = sum(1 for m in control.metrics if m.n_losses == 0)
    t_zero = sum(1 for m in treatment.metrics if m.n_losses == 0)
    print(f"  {'Zero-loss cycles':<33} {c_zero:>18d} {t_zero:>18d}")

    # Collapses
    c_collapse = sum(1 for m in control.metrics if m.collapsed)
    t_collapse = sum(1 for m in treatment.metrics if m.collapsed)
    print(f"  {'Collapse events':<33} {c_collapse:>18d} {t_collapse:>18d}")

    # Precursors
    c_precursor = sum(1 for m in control.metrics if m.precursor)
    t_precursor = sum(1 for m in treatment.metrics if m.precursor)
    print(f"  {'Precursor events':<33} {c_precursor:>18d} {t_precursor:>18d}")

    # Truncation events
    c_trunc = sum(1 for m in control.metrics if m.stop_reason == "max_tokens")
    t_trunc = sum(1 for m in treatment.metrics if m.stop_reason == "max_tokens")
    print(f"  {'Truncation events':<33} {c_trunc:>18d} {t_trunc:>18d}")

    # Loss category distribution
    print()
    print("Loss category distribution:")
    for cond_name, run in [("Control", control), ("No Prior Losses", treatment)]:
        cats: dict[str, int] = {}
        for m in run.metrics:
            for cat in m.loss_categories:
                cats[cat] = cats.get(cat, 0) + 1
        total = sum(cats.values())
        print(f"  {cond_name}: {cats} (total: {total})")

    # Strand title overlap between conditions
    print()
    print("Strand title overlap (control vs treatment) per quarter:")
    min_len = min(len(control.metrics), len(treatment.metrics))
    quarter = max(1, min_len // 4)
    for q in range(4):
        start = q * quarter
        end = min((q + 1) * quarter, min_len)
        overlaps = []
        for i in range(start, end):
            c_set = set(control.metrics[i].strand_titles)
            t_set = set(treatment.metrics[i].strand_titles)
            if c_set or t_set:
                overlaps.append(len(c_set & t_set) / len(c_set | t_set))
        if overlaps:
            avg = sum(overlaps) / len(overlaps)
            print(f"  Q{q + 1} (cycles {start + 1}-{end}): Jaccard = {avg:.3f}")


def main():
    parser = argparse.ArgumentParser(
        description="Q2: Declared losses as differentiation mechanism"
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
