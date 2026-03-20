"""Pairwise interaction ablation using covering arrays.

The N=20 ablation tested single-component removal. It found flat_strands
and no_instructions hurt, while no_losses, no_epistemic, and no_questions
don't. But it didn't test INTERACTIONS — does removing losses AND instructions
produce a worse-than-additive effect (the coupled channel hypothesis)?

This experiment uses covering array design to test all pairwise interactions
with ~10-12 configurations instead of 2^5 = 32 exhaustive.

Five binary factors:
  A: declared_losses   (present / absent)
  B: epistemic values   (present / zeroed)
  C: instructions_for_next (present / absent)
  D: open_questions     (present / absent)
  E: strand_structure   (separated / flat)

A covering array CA(N; 2, 5, 2) guarantees every pair of factors appears
in all 4 states (00, 01, 10, 11) across the configuration set.

Usage:
    uv run python -m hamutay.eval.pairwise_ablation [--dry-run]
"""

from __future__ import annotations

import copy
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import numpy as np

from hamutay.ablation import ablate_tensor
from hamutay.riemann_experiment import (
    _embed_texts,
    _run_condition,
    compute_dispersion,
)


EXPERIMENT_DIR = Path(__file__).resolve().parents[3] / "experiments"
OUTPUT_DIR = EXPERIMENT_DIR / "pairwise_ablation"


# ── Covering Array Generation ────────────────────────────────────────

# For CA(N; 2, 5, 2): pairwise coverage of 5 binary factors
# Minimum N is 4 (for t=2, v=2); in practice ~6-8 for k=5
# We use a known optimal CA(6; 2, 5, 2) from the literature,
# plus the full and empty configurations for interpretability.

# Each row: (losses, epistemic, ifn, questions, strands_separated)
# 0 = absent/zeroed/flat, 1 = present/normal
COVERING_ARRAY = [
    # Optimal CA(6; 2, 5, 2) — covers all pairwise combinations
    (1, 1, 1, 1, 1),  # full tensor (baseline)
    (0, 0, 0, 0, 0),  # everything removed
    (1, 0, 0, 1, 0),
    (0, 1, 0, 0, 1),
    (0, 0, 1, 1, 1),
    (1, 1, 1, 0, 0),
    # Additional configs for interpretability
    (0, 0, 0, 0, 1),  # strands only (strands_only from N=20)
    (1, 1, 0, 1, 1),  # no_instructions (single removal, replication)
]

FACTOR_NAMES = ["losses", "epistemic", "ifn", "questions", "strands_sep"]


def _verify_pairwise_coverage() -> bool:
    """Verify the covering array has complete pairwise coverage."""
    n_factors = len(FACTOR_NAMES)
    for i in range(n_factors):
        for j in range(i + 1, n_factors):
            pairs_seen = set()
            for config in COVERING_ARRAY:
                pairs_seen.add((config[i], config[j]))
            if len(pairs_seen) < 4:  # need all of (0,0), (0,1), (1,0), (1,1)
                print(f"  COVERAGE GAP: factors {FACTOR_NAMES[i]}, {FACTOR_NAMES[j]} "
                      f"missing {4 - len(pairs_seen)} pairs")
                return False
    return True


def _config_name(config: tuple[int, ...]) -> str:
    """Human-readable name for a configuration."""
    parts = []
    for i, (val, name) in enumerate(zip(config, FACTOR_NAMES)):
        if val == 0:
            parts.append(f"no_{name}")
    if not parts:
        return "full"
    return "+".join(parts)


def _apply_config(tensor_json: str, config: tuple[int, ...]) -> str:
    """Apply a configuration to a tensor JSON string.

    Each factor maps to a specific ablation:
      losses=0    → remove declared_losses
      epistemic=0 → zero all T/I/F
      ifn=0       → remove instructions_for_next
      questions=0 → remove open_questions
      strands=0   → flatten strands
    """
    data = json.loads(tensor_json)

    if config[0] == 0:  # losses
        data["declared_losses"] = []

    if config[1] == 0:  # epistemic
        data["overall_truth"] = 0.0
        data["overall_indeterminacy"] = 0.0
        data["overall_falsity"] = 0.0
        if "epistemic" in data:
            data["epistemic"] = {"truth": 0.0, "indeterminacy": 0.0, "falsity": 0.0}
        for strand in data.get("strands", []):
            for claim in strand.get("key_claims", []):
                claim["truth"] = 0.0
                claim["indeterminacy"] = 0.0
                claim["falsity"] = 0.0
            if "epistemic" in strand:
                strand["epistemic"] = {"truth": 0.0, "indeterminacy": 0.0, "falsity": 0.0}

    if config[2] == 0:  # ifn
        data["instructions_for_next"] = ""

    if config[3] == 0:  # questions
        data["open_questions"] = []

    if config[4] == 0:  # strands (flatten)
        all_content = "\n\n".join(s.get("content", "") for s in data.get("strands", []))
        all_claims = []
        for s in data.get("strands", []):
            all_claims.extend(s.get("key_claims", []))
        data["strands"] = [{"title": "Merged content", "content": all_content,
                            "key_claims": all_claims}]

    return json.dumps(data, indent=2)


# ── Interaction Analysis ─────────────────────────────────────────────

@dataclass
class InteractionEffect:
    """Pairwise interaction between two factors."""
    factor_a: str
    factor_b: str
    # Main effects
    delta_a: float  # effect of removing A alone
    delta_b: float  # effect of removing B alone
    # Interaction
    delta_both: float      # effect of removing both
    expected_additive: float  # delta_a + delta_b
    interaction: float     # delta_both - expected_additive
    # Interpretation
    synergistic: bool  # interaction > 0: worse together than sum
    compensatory: bool  # interaction < 0: less bad together (compensation)


def compute_interactions(
    results: dict[str, float],
    baseline_key: str = "full",
) -> list[InteractionEffect]:
    """Compute pairwise interactions from the covering array results.

    Uses the standard interaction formula:
      interaction(A,B) = delta(A+B) - delta(A) - delta(B)
    where delta(X) = dispersion(no_X) - dispersion(full)

    Positive interaction = synergistic (worse together than expected)
    Negative interaction = compensatory (less bad together than expected)
    """
    baseline = results.get(baseline_key, 0.0)
    interactions = []

    for i in range(len(FACTOR_NAMES)):
        for j in range(i + 1, len(FACTOR_NAMES)):
            # Find configs where only factor i is removed
            a_only_configs = [c for c in COVERING_ARRAY
                              if c[i] == 0 and c[j] == 1
                              and all(c[k] == 1 for k in range(len(FACTOR_NAMES)) if k not in (i, j))]
            # Find configs where only factor j is removed
            b_only_configs = [c for c in COVERING_ARRAY
                              if c[i] == 1 and c[j] == 0
                              and all(c[k] == 1 for k in range(len(FACTOR_NAMES)) if k not in (i, j))]
            # Find configs where both are removed
            both_configs = [c for c in COVERING_ARRAY
                            if c[i] == 0 and c[j] == 0
                            and all(c[k] == 1 for k in range(len(FACTOR_NAMES)) if k not in (i, j))]

            # Average over matching configs (may be >1 due to covering array)
            def _mean_disp(configs):
                vals = [results.get(_config_name(c), baseline) for c in configs]
                return sum(vals) / len(vals) if vals else baseline

            disp_a = _mean_disp(a_only_configs)
            disp_b = _mean_disp(b_only_configs)
            disp_both = _mean_disp(both_configs)

            delta_a = disp_a - baseline
            delta_b = disp_b - baseline
            delta_both = disp_both - baseline
            expected = delta_a + delta_b
            interaction = delta_both - expected

            interactions.append(InteractionEffect(
                factor_a=FACTOR_NAMES[i],
                factor_b=FACTOR_NAMES[j],
                delta_a=delta_a,
                delta_b=delta_b,
                delta_both=delta_both,
                expected_additive=expected,
                interaction=interaction,
                synergistic=interaction > 0.001,
                compensatory=interaction < -0.001,
            ))

    return interactions


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    dry_run = "--dry-run" in sys.argv
    n_runs = 10  # same as N=20 ablation but we have more conditions

    print("=" * 60)
    print("  Pairwise Interaction Ablation")
    print("  Covering Array CA(8; 2, 5, 2)")
    print("=" * 60)

    # Verify coverage
    print("\n  Verifying pairwise coverage...")
    if _verify_pairwise_coverage():
        print("  Complete pairwise coverage confirmed.")
    else:
        print("  WARNING: incomplete coverage!")

    print(f"\n  {len(COVERING_ARRAY)} configurations × N={n_runs}:")
    for config in COVERING_ARRAY:
        name = _config_name(config)
        factors = ", ".join(
            f"{FACTOR_NAMES[i]}={'on' if v else 'OFF'}"
            for i, v in enumerate(config)
        )
        print(f"    {name:40s} [{factors}]")

    total_calls = len(COVERING_ARRAY) * n_runs
    print(f"\n  Total Sonnet calls: {total_calls}")
    print(f"  Estimated cost: ${total_calls * 0.05:.2f}")

    if dry_run:
        print("\n  [DRY RUN] Would run the above experiment.")
        return

    # Load the tensor used in N=20 ablation
    # The ablation used the observation_full tensor — need to find it
    print("\n  Loading tensor...")

    # Use the Q2 control cycle 50 tensor — rich, mid-conversation
    tensor_path = EXPERIMENT_DIR / "q2_declared_losses" / "control" / "tensors" / "tensor_cycle_050.json"
    tensor_json = tensor_path.read_text()
    print(f"  Tensor: cycle 50, ~{len(tensor_json) // 4} tokens")

    client = anthropic.Anthropic()
    all_results: dict[str, float] = {}

    for config in COVERING_ARRAY:
        name = _config_name(config)
        context = _apply_config(tensor_json, config)
        tokens = len(context) // 4

        print(f"\n  Condition: {name} (~{tokens} tokens)")

        result = _run_condition(
            name, f"config {''.join(str(v) for v in config)}",
            context, n_runs, client, "claude-sonnet-4-6"
        )

        if result.dispersion is not None:
            all_results[name] = result.dispersion
            print(f"    dispersion={result.dispersion:.4f}, "
                  f"cosine={result.mean_pairwise_cosine:.4f}")

    # Compute interactions
    print("\n" + "=" * 60)
    print("  INTERACTION EFFECTS")
    print("=" * 60)

    interactions = compute_interactions(all_results)

    print(f"\n  {'Factor A':12s} × {'Factor B':12s} | δA      δB      δA+B    expected  interaction")
    print("  " + "-" * 80)
    for ix in sorted(interactions, key=lambda x: abs(x.interaction), reverse=True):
        label = ""
        if ix.synergistic:
            label = " SYNERGISTIC"
        elif ix.compensatory:
            label = " COMPENSATORY"
        print(f"  {ix.factor_a:12s} × {ix.factor_b:12s} | "
              f"{ix.delta_a:+.4f}  {ix.delta_b:+.4f}  {ix.delta_both:+.4f}  "
              f"{ix.expected_additive:+.4f}    {ix.interaction:+.4f}{label}")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_data = {
        "experiment": "pairwise_ablation",
        "covering_array": [list(c) for c in COVERING_ARRAY],
        "factor_names": FACTOR_NAMES,
        "n_runs": n_runs,
        "dispersions": all_results,
        "interactions": [
            {
                "factor_a": ix.factor_a, "factor_b": ix.factor_b,
                "delta_a": ix.delta_a, "delta_b": ix.delta_b,
                "delta_both": ix.delta_both, "expected": ix.expected_additive,
                "interaction": ix.interaction,
                "synergistic": ix.synergistic, "compensatory": ix.compensatory,
            }
            for ix in interactions
        ],
    }
    (OUTPUT_DIR / "results.json").write_text(json.dumps(save_data, indent=2))
    print(f"\n  Saved to {OUTPUT_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
