"""Model escalation experiment — can a stronger projector prevent collapse?

Du et al. (2025) showed context length alone degrades LLM performance.
The projector (Haiku) is itself an LLM processing growing tensors.
As tensors grow past ~8K tokens, the projector's own context load
enters the degradation zone, causing the precursor → collapse pattern.

Hypothesis: escalating to a more capable model (Sonnet) when the
projector is under load — either from precursor signals or tensor
size — should reduce collapse rate without requiring Sonnet for
every cycle. L1 cache miss falls through to L2.

Experimental conditions:
1. haiku_only       — baseline (NeverEscalate)
2. sonnet_only      — upper bound (AlwaysEscalate)
3. escalate_precur  — escalate on precursor detection
4. escalate_size    — escalate when tensor > 8K tokens
5. escalate_both    — escalate on precursor OR size (defense in depth)
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from hamutay.log_reader import ConversationTurn, read_session_jsonl
from hamutay.projector import (
    AlwaysEscalate,
    EscalateOnPrecursor,
    EscalateOnPrecursorOrSize,
    EscalateOnSize,
    EscalationPolicy,
    NeverEscalate,
    Projector,
)
from hamutay.riemann_experiment import (
    _embed_texts,
    _run_condition,
    compute_dispersion,
    prepare_tensor_context,
)
from hamutay.tensor import Tensor


@dataclass
class GrowthPoint:
    """One cycle's metrics in a growth curve."""

    cycle: int
    tokens: int
    n_strands: int
    n_losses: int
    has_ifn: bool
    model_used: str
    escalated: bool
    precursor: bool
    collapsed: bool


@dataclass
class EscalationResult:
    """Results from one escalation condition."""

    name: str
    description: str
    policy_class: str
    growth_curve: list[GrowthPoint] = field(default_factory=list)
    total_cycles: int = 0
    collapse_count: int = 0
    precursor_count: int = 0
    escalation_count: int = 0
    final_tensor_tokens: int = 0
    final_tensor_json: str = ""
    wall_time_s: float = 0.0
    dispersion: float | None = None
    mean_pairwise_cosine: float | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "policy_class": self.policy_class,
            "total_cycles": self.total_cycles,
            "collapse_count": self.collapse_count,
            "precursor_count": self.precursor_count,
            "escalation_count": self.escalation_count,
            "collapse_rate": self.collapse_count / max(self.total_cycles, 1),
            "escalation_rate": self.escalation_count / max(self.total_cycles, 1),
            "final_tensor_tokens": self.final_tensor_tokens,
            "wall_time_s": self.wall_time_s,
            "dispersion": self.dispersion,
            "mean_pairwise_cosine": self.mean_pairwise_cosine,
            "growth_curve": [
                {
                    "cycle": p.cycle,
                    "tokens": p.tokens,
                    "n_strands": p.n_strands,
                    "n_losses": p.n_losses,
                    "has_ifn": p.has_ifn,
                    "model_used": p.model_used,
                    "escalated": p.escalated,
                    "precursor": p.precursor,
                    "collapsed": p.collapsed,
                }
                for p in self.growth_curve
            ],
        }


def _prepare_batches(
    turns: list[ConversationTurn],
    batch_size: int,
) -> list[str]:
    """Group turns into batched content blocks."""
    batches: list[str] = []
    for i in range(0, len(turns), batch_size):
        batch = turns[i : i + batch_size]
        parts = [f"[{t.role} turn {t.turn_number}] {t.content}" for t in batch]
        batches.append("\n\n---\n\n".join(parts))
    return batches


def run_growth_curve(
    batches: list[str],
    policy: EscalationPolicy,
    client: anthropic.Anthropic,
    label: str,
) -> tuple[Projector, list[GrowthPoint], float]:
    """Run a full growth curve with a given escalation policy."""
    projector = Projector(
        client=client,
        model=policy.base_model,
        escalation_policy=policy,
    )

    points: list[GrowthPoint] = []
    t0 = time.monotonic()

    for i, content in enumerate(batches):
        prior_tokens = projector.current_tensor.token_estimate() if projector.current_tensor else 0
        tensor = projector.project(content)

        # Detect collapse from the log
        log_entry = projector.escalation_log[-1] if projector.escalation_log else {}
        collapsed = (
            prior_tokens > 0
            and tensor.token_estimate() / prior_tokens < 0.3
        ) if prior_tokens > 0 else False

        point = GrowthPoint(
            cycle=tensor.cycle,
            tokens=tensor.token_estimate(),
            n_strands=len(tensor.strands),
            n_losses=len(tensor.declared_losses),
            has_ifn=bool(tensor.instructions_for_next),
            model_used=log_entry.get("model", policy.base_model),
            escalated=log_entry.get("escalated", False),
            precursor=projector._precursor_detected,
            collapsed=collapsed,
        )
        points.append(point)

        status = ""
        if point.escalated:
            status += " [ESCALATED]"
        if point.precursor:
            status += " [PRECURSOR]"
        if point.collapsed:
            status += " [COLLAPSED]"

        print(f"  {label} cycle {point.cycle:>3}: "
              f"{point.tokens:>6} tokens, "
              f"{point.n_strands} strands, "
              f"{point.n_losses} losses, "
              f"ifn={'Y' if point.has_ifn else 'N'}"
              f"{status}")

    elapsed = time.monotonic() - t0
    return projector, points, elapsed


def run_escalation_experiment(
    session_path: Path,
    output_dir: Path,
    batch_size: int = 3,
    max_cycles: int | None = None,
    base_model: str = "claude-haiku-4-5-20251001",
    escalation_model: str = "claude-sonnet-4-6",
    size_threshold: int = 8000,
    n_dispersion_runs: int = 20,
    reasoner_model: str = "claude-sonnet-4-6",
) -> list[EscalationResult]:
    """Run the full escalation experiment."""

    turns = read_session_jsonl(session_path)
    batches = _prepare_batches(turns, batch_size)
    if max_cycles:
        batches = batches[:max_cycles]

    print(f"Session: {session_path}")
    print(f"Turns: {len(turns)}, Batches: {len(batches)} (batch_size={batch_size})")
    print(f"Base model: {base_model}")
    print(f"Escalation model: {escalation_model}")
    print(f"Size threshold: {size_threshold} tokens")
    print()

    conditions: list[tuple[str, str, EscalationPolicy]] = [
        (
            "haiku_only",
            "Haiku-only baseline — no escalation",
            NeverEscalate(base_model, escalation_model),
        ),
        (
            "escalate_precur",
            "Escalate to Sonnet on precursor detection",
            EscalateOnPrecursor(base_model, escalation_model),
        ),
        (
            "escalate_size",
            f"Escalate to Sonnet when tensor > {size_threshold} tokens",
            EscalateOnSize(base_model, escalation_model, size_threshold),
        ),
        (
            "escalate_both",
            f"Escalate on precursor OR tensor > {size_threshold} tokens",
            EscalateOnPrecursorOrSize(base_model, escalation_model, size_threshold),
        ),
        (
            "sonnet_only",
            "Sonnet-only — upper bound on projection quality",
            AlwaysEscalate(base_model, escalation_model),
        ),
    ]

    client = anthropic.Anthropic()
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[EscalationResult] = []

    for name, description, policy in conditions:
        print(f"\n{'=' * 60}")
        print(f"Condition: {name}")
        print(f"  {description}")
        print(f"{'=' * 60}")

        projector, points, elapsed = run_growth_curve(
            batches, policy, client, name
        )

        result = EscalationResult(
            name=name,
            description=description,
            policy_class=type(policy).__name__,
            growth_curve=points,
            total_cycles=len(points),
            collapse_count=sum(1 for p in points if p.collapsed),
            precursor_count=sum(1 for p in points if p.precursor),
            escalation_count=sum(1 for p in points if p.escalated),
            final_tensor_tokens=points[-1].tokens if points else 0,
            final_tensor_json=projector.current_tensor.model_dump_json(indent=2)
            if projector.current_tensor
            else "",
            wall_time_s=elapsed,
        )
        results.append(result)

        print(f"\n  Summary: {result.collapse_count} collapses, "
              f"{result.precursor_count} precursors, "
              f"{result.escalation_count} escalations in "
              f"{result.total_cycles} cycles ({elapsed:.1f}s)")

    # Measure dispersion on final tensors
    if n_dispersion_runs > 0:
        print(f"\n{'=' * 60}")
        print(f"Measuring dispersion (N={n_dispersion_runs} per condition)")
        print(f"{'=' * 60}")

        for result in results:
            if not result.final_tensor_json:
                continue

            print(f"\n  {result.name}: measuring dispersion...")
            condition_result = _run_condition(
                result.name,
                result.description,
                result.final_tensor_json,
                n_dispersion_runs,
                client,
                reasoner_model,
            )
            result.dispersion = condition_result.dispersion
            result.mean_pairwise_cosine = condition_result.mean_pairwise_cosine

    # Save results
    experiment_data = {
        "session_path": str(session_path),
        "n_turns": len(turns),
        "n_batches": len(batches),
        "batch_size": batch_size,
        "base_model": base_model,
        "escalation_model": escalation_model,
        "size_threshold": size_threshold,
        "n_dispersion_runs": n_dispersion_runs,
        "reasoner_model": reasoner_model,
        "conditions": [r.to_dict() for r in results],
    }

    output_path = output_dir / "escalation_results.json"
    output_path.write_text(json.dumps(experiment_data, indent=2))

    # Print summary table
    print(f"\n{'=' * 90}")
    print(f"{'Condition':<20} {'Cycles':>7} {'Collapses':>10} {'Precurs':>8} "
          f"{'Escals':>7} {'Final':>7} {'Disp':>10} {'Time':>7}")
    print(f"{'-' * 90}")
    for r in results:
        disp_str = f"{r.dispersion:.6f}" if r.dispersion is not None else "—"
        print(f"{r.name:<20} {r.total_cycles:>7} {r.collapse_count:>10} "
              f"{r.precursor_count:>8} {r.escalation_count:>7} "
              f"{r.final_tensor_tokens:>7} {disp_str:>10} "
              f"{r.wall_time_s:>6.0f}s")
    print(f"{'=' * 90}")

    # Write growth curves as text for easy inspection
    curve_path = output_dir / "growth_curves.txt"
    with open(curve_path, "w") as f:
        for r in results:
            f.write(f"\n# {r.name}\n")
            for p in r.growth_curve:
                flags = ""
                if p.escalated:
                    flags += "E"
                if p.precursor:
                    flags += "P"
                if p.collapsed:
                    flags += "C"
                f.write(
                    f"cycle {p.cycle:>3}: {p.tokens:>6} tokens, "
                    f"{p.n_strands} strands, {p.n_losses} losses, "
                    f"ifn={'Y' if p.has_ifn else 'N'}"
                    f"{' [' + flags + ']' if flags else ''}\n"
                )

    print(f"\nResults: {output_path}")
    print(f"Growth curves: {curve_path}")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m hamutay.escalation_experiment "
            "<session.jsonl> <output_dir> "
            "[batch_size] [max_cycles] [n_dispersion_runs] [size_threshold]"
        )
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    max_cycles = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None
    n_dispersion_runs = int(sys.argv[5]) if len(sys.argv) > 5 else 20
    size_threshold = int(sys.argv[6]) if len(sys.argv) > 6 else 8000

    run_escalation_experiment(
        session_path,
        output_dir,
        batch_size=batch_size,
        max_cycles=max_cycles,
        size_threshold=size_threshold,
        n_dispersion_runs=n_dispersion_runs,
    )
