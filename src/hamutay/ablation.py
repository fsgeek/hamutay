"""Ablation study: which tensor components are load-bearing?

Take the full tensor, surgically remove one component at a time,
measure dispersion. If dispersion increases when you remove a
component, that component contributes to coherence.

Single ablations first (screen), interactions later (probe).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import anthropic

from hamutay.riemann_experiment import (
    ConditionResult,
    _embed_texts,
    _generate_blinded_grading,
    _run_condition,
    compute_dispersion,
)


def ablate_tensor(tensor_json: str, ablation: str) -> str:
    """Remove a specific component from a tensor JSON string.

    Ablations:
    - no_losses: remove declared_losses
    - no_epistemic: zero out all T/I/F values
    - no_instructions: remove instructions_for_next
    - no_questions: remove open_questions
    - flat_strands: collapse all strands into one blob
    - strands_only: keep only strand titles and content
    - content_only: unstructured blob of all strand content (no JSON structure)
    """
    data = json.loads(tensor_json)

    if ablation == "no_losses":
        data["declared_losses"] = []

    elif ablation == "no_epistemic":
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

    elif ablation == "no_instructions":
        data["instructions_for_next"] = ""

    elif ablation == "no_questions":
        data["open_questions"] = []

    elif ablation == "flat_strands":
        # Merge all strand content into one strand
        all_content = "\n\n".join(
            s.get("content", "") for s in data.get("strands", [])
        )
        all_claims = []
        for s in data.get("strands", []):
            all_claims.extend(s.get("key_claims", []))
        data["strands"] = [{
            "title": "Merged content",
            "content": all_content,
            "key_claims": all_claims,
        }]

    elif ablation == "strands_only":
        # Keep strand titles and content, strip everything else
        data["strands"] = [
            {"title": s["title"], "content": s["content"], "key_claims": []}
            for s in data.get("strands", [])
        ]
        data["declared_losses"] = []
        data["open_questions"] = []
        data["instructions_for_next"] = ""
        # Zero epistemic
        data["overall_truth"] = 0.0
        data["overall_indeterminacy"] = 0.0
        data["overall_falsity"] = 0.0
        if "epistemic" in data:
            data["epistemic"] = {"truth": 0.0, "indeterminacy": 0.0, "falsity": 0.0}

    elif ablation == "content_only":
        # Flatten to unstructured prose — no JSON at all
        parts = []
        for s in data.get("strands", []):
            parts.append(f"{s.get('title', '')}: {s.get('content', '')}")
        if data.get("open_questions"):
            parts.append("Open questions: " + "; ".join(data["open_questions"]))
        if data.get("instructions_for_next"):
            parts.append("Next steps: " + data["instructions_for_next"])
        return "\n\n".join(parts)

    else:
        raise ValueError(f"Unknown ablation: {ablation}")

    return json.dumps(data, indent=2)


ABLATIONS = [
    ("full_tensor", "Complete tensor — control condition", None),
    ("no_losses", "Declared losses removed", "no_losses"),
    ("no_epistemic", "All T/I/F values zeroed", "no_epistemic"),
    ("no_instructions", "instructions_for_next removed", "no_instructions"),
    ("no_questions", "open_questions removed", "no_questions"),
    ("flat_strands", "All strands merged into one", "flat_strands"),
    ("strands_only", "Only strand titles and content — minimal structure", "strands_only"),
    ("content_only", "Unstructured prose extracted from tensor — no JSON", "content_only"),
]


def run_ablation_study(
    tensor_json: str,
    output_dir: Path,
    n_runs: int = 20,
    reasoner_model: str = "claude-sonnet-4-6",
) -> list[ConditionResult]:
    """Run the ablation study: full tensor vs each single ablation."""

    output_dir.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()
    results = []

    print(f"Running ablation study: {len(ABLATIONS)} conditions, N={n_runs}")
    print(f"Full tensor: ~{len(tensor_json) // 4} tokens\n")

    for name, description, ablation in ABLATIONS:
        if ablation is None:
            context = tensor_json
        else:
            context = ablate_tensor(tensor_json, ablation)

        tokens = len(context) // 4
        print(f"  {name}: ~{tokens} tokens ({description})")

        result = _run_condition(
            name, description, context, n_runs, client, reasoner_model
        )
        results.append(result)

    # Save results
    experiment_data = {
        "n_runs": n_runs,
        "reasoner_model": reasoner_model,
        "full_tensor_tokens": len(tensor_json) // 4,
        "conditions": [r.to_dict() for r in results],
        "summary": {
            r.name: {
                "tokens": r.representation_tokens,
                "dispersion": r.dispersion,
                "mean_pairwise": r.mean_pairwise_cosine,
            }
            for r in results
        },
    }

    output_path = output_dir / "ablation_results.json"
    output_path.write_text(json.dumps(experiment_data, indent=2))

    # Generate blinded grading sheet
    _generate_blinded_grading(results, output_dir)

    # Print summary
    print("\n" + "=" * 75)
    print(f"{'Ablation':<20} {'Tokens':>8} {'Dispersion':>12} {'Pairwise':>12} {'Delta':>8}")
    print("-" * 75)

    control_disp = results[0].dispersion
    for r in results:
        delta = r.dispersion - control_disp if control_disp else 0
        sign = "+" if delta > 0 else ""
        print(
            f"{r.name:<20} {r.representation_tokens:>8} "
            f"{r.dispersion:>12.6f} {r.mean_pairwise_cosine:>12.6f} "
            f"{sign}{delta:>7.6f}"
        )
    print("=" * 75)

    print(f"\nResults written to {output_path}")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m hamutay.ablation <prepared_contexts.json> <output_dir> "
            "[n_runs]"
        )
        sys.exit(1)

    contexts_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    n_runs = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    cached = json.loads(contexts_path.read_text())
    tensor_json = cached["tensor"]

    run_ablation_study(tensor_json, output_dir, n_runs)
