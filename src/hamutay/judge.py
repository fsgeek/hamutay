"""Q2 tensor judges — evaluate end-state tensors per pre-registered rubric.

Three judge modes:
  1. isolated: Evaluate a single tensor without seeing the other condition.
  2. comparative: Evaluate both tensors side by side.

The rubric comes directly from experiments/q2_declared_losses/PRE_REGISTRATION.md:

Loss Sophistication Classification:
  - Structural: Loss of data artifacts (dialogue flow, file contents, timestamps).
    Signal words: "raw dialogue", "intermediate", "file states", "timestamps",
    "tool output", "code artifacts", "format details"
  - Epistemic: Loss of understanding or analytical capacity (reasoning chains,
    counter-arguments, alternative interpretations).
    Signal words: "reasoning about", "understanding of", "uncertainty",
    "alternative interpretation", "counter-argument", "analytical depth"
  - Refinement: Meta-loss — recognition that a prior framing has been superseded
    by deeper understanding. Editorial judgment, maturation not degradation.
    Signal words: "maturation", "no longer needed", "superseded", "reframed",
    "integrated into", "the wondering about X has been resolved into Y"

  Ambiguous cases classified as the lower category (structural < epistemic < refinement).

Strand Character Classification:
  - Research-oriented: reflective, analytical, questioning, developing frameworks
  - Procedural: status tracking, execution plans, blocker management

Usage:
    # Isolated judge on one tensor
    uv run python -m hamutay.judge isolated \\
        experiments/q2_declared_losses/control/tensors/tensor_cycle_104.json \\
        --output experiments/q2_declared_losses/judgments/

    # Comparative judge on both end-state tensors
    uv run python -m hamutay.judge comparative \\
        experiments/q2_declared_losses/control/tensors/tensor_cycle_104.json \\
        experiments/q2_declared_losses/no_prior_losses/tensors/tensor_cycle_104.json \\
        --output experiments/q2_declared_losses/judgments/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic

LOSS_RUBRIC = """\
Classify each declared loss into exactly one of three categories by reading
its "what_was_lost" and "why" fields together.

Categories (in ascending order of sophistication):

1. STRUCTURAL: Loss of data artifacts — dialogue flow, file contents,
   timestamps, intermediate states. The loss describes *what data* was
   dropped. These losses are about the container, not the content.
   Signal words: "raw dialogue", "intermediate", "file states", "timestamps",
   "tool output", "code artifacts", "format details"

2. EPISTEMIC: Loss of understanding or analytical capacity — reasoning
   chains, counter-arguments, alternative interpretations, uncertainty
   about specific claims. The loss describes *what understanding* was
   compressed or degraded.
   Signal words: "reasoning about", "understanding of", "uncertainty",
   "alternative interpretation", "counter-argument", "analytical depth",
   "implications of"

3. REFINEMENT: Meta-loss — the recognition that a prior framing, question,
   or exploratory tone has been superseded by deeper understanding. The loss
   is acknowledged as maturation rather than degradation. This is the
   projector developing editorial judgment.
   Signal words: "maturation", "no longer needed", "superseded",
   "exploratory tone", "reframed", "integrated into", "the wondering
   about X has been resolved into Y"

IMPORTANT: When ambiguous, classify as the LOWER category
(structural before epistemic, epistemic before refinement).
"""

STRAND_RUBRIC = """\
Classify each strand into exactly one of two categories by reading
its title and content together.

Categories:

1. RESEARCH-ORIENTED: Reflective, analytical, questioning, developing
   frameworks for understanding. The strand is about ideas, relationships
   between concepts, or building mental models.

2. PROCEDURAL: Status tracking, execution plans, blocker management,
   dependency resolution. The strand is about what to do, what has been
   done, or what is blocked.
"""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "loss_classifications": {
            "type": "array",
            "description": "One classification per declared loss, in order",
            "items": {
                "type": "object",
                "properties": {
                    "loss_index": {"type": "integer"},
                    "what_was_lost_excerpt": {
                        "type": "string",
                        "description": "First 80 chars of what_was_lost for traceability",
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["structural", "epistemic", "refinement"],
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief justification for the classification",
                    },
                },
                "required": ["loss_index", "what_was_lost_excerpt", "classification", "reasoning"],
            },
        },
        "strand_classifications": {
            "type": "array",
            "description": "One classification per strand, in order",
            "items": {
                "type": "object",
                "properties": {
                    "strand_index": {"type": "integer"},
                    "title": {"type": "string"},
                    "classification": {
                        "type": "string",
                        "enum": ["research-oriented", "procedural"],
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Brief justification for the classification",
                    },
                },
                "required": ["strand_index", "title", "classification", "reasoning"],
            },
        },
        "overall_assessment": {
            "type": "string",
            "description": "2-3 sentence overall assessment of this tensor's character",
        },
    },
    "required": ["loss_classifications", "strand_classifications", "overall_assessment"],
}

COMPARATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "tensor_a": JUDGE_SCHEMA,
        "tensor_b": JUDGE_SCHEMA,
        "comparison": {
            "type": "object",
            "properties": {
                "loss_sophistication_difference": {
                    "type": "string",
                    "description": "How do the loss classifications differ between A and B?",
                },
                "strand_character_difference": {
                    "type": "string",
                    "description": "How do the strand classifications differ between A and B?",
                },
                "overall_comparison": {
                    "type": "string",
                    "description": "2-3 sentence comparison of the two tensors' character",
                },
            },
            "required": [
                "loss_sophistication_difference",
                "strand_character_difference",
                "overall_comparison",
            ],
        },
    },
    "required": ["tensor_a", "tensor_b", "comparison"],
}


def _build_isolated_prompt(tensor_json: str) -> str:
    return f"""\
You are evaluating a tensor projection — a compressed representation of a
long conversation, produced by an AI projector model. Your job is to classify
the declared losses and strands using the rubrics below.

You are seeing this tensor in isolation. You do not know what condition
produced it or what other tensors exist. Judge it on its own merits.

## Loss Classification Rubric

{LOSS_RUBRIC}

## Strand Classification Rubric

{STRAND_RUBRIC}

## Tensor to Evaluate

{tensor_json}

Classify every declared loss and every strand. Use the emit_judgment tool.
"""


def _build_comparative_prompt(tensor_a_json: str, tensor_b_json: str) -> str:
    return f"""\
You are evaluating two tensor projections — compressed representations of a
long conversation, each produced by an AI projector model under different
conditions. Your job is to classify the declared losses and strands in BOTH
tensors, then compare them.

You do not know which condition produced which tensor. They are labeled
A and B arbitrarily. Judge each on its own merits, then compare.

## Loss Classification Rubric

{LOSS_RUBRIC}

## Strand Classification Rubric

{STRAND_RUBRIC}

## Tensor A

{tensor_a_json}

## Tensor B

{tensor_b_json}

Classify every declared loss and every strand in BOTH tensors, then provide
a comparison. Use the emit_judgment tool.
"""


def judge_isolated(
    tensor_path: Path,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Run an isolated judge on a single tensor."""
    tensor_json = tensor_path.read_text()
    prompt = _build_isolated_prompt(tensor_json)

    print(f"  Judging {tensor_path.name} (isolated)...")

    with client.messages.stream(
        model=model,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "emit_judgment",
                "description": "Emit the classification judgment",
                "input_schema": JUDGE_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "emit_judgment"},
    ) as stream:
        response = stream.get_final_message()

    for block in response.content:
        if hasattr(block, "name") and block.type == "tool_use" and block.name == "emit_judgment":
            return block.input  # type: ignore[union-attr]

    raise RuntimeError("Judge did not emit judgment")


def judge_comparative(
    tensor_a_path: Path,
    tensor_b_path: Path,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Run a comparative judge on two tensors."""
    tensor_a_json = tensor_a_path.read_text()
    tensor_b_json = tensor_b_path.read_text()
    prompt = _build_comparative_prompt(tensor_a_json, tensor_b_json)

    print(f"  Judging {tensor_a_path.name} vs {tensor_b_path.name} (comparative)...")

    with client.messages.stream(
        model=model,
        max_tokens=32768,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "emit_judgment",
                "description": "Emit the comparative classification judgment",
                "input_schema": COMPARATIVE_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "emit_judgment"},
    ) as stream:
        response = stream.get_final_message()

    for block in response.content:
        if hasattr(block, "name") and block.type == "tool_use" and block.name == "emit_judgment":
            return block.input  # type: ignore[union-attr]

    raise RuntimeError("Judge did not emit judgment")


def _print_isolated(result: dict, label: str) -> None:
    """Print an isolated judgment."""
    print(f"\n{'=' * 60}")
    print(f"ISOLATED JUDGMENT: {label}")
    print(f"{'=' * 60}")

    losses = result.get("loss_classifications", [])
    strands = result.get("strand_classifications", [])

    # Loss summary
    counts = {"structural": 0, "epistemic": 0, "refinement": 0}
    for lc in losses:
        cat = lc.get("classification", "unknown")
        counts[cat] = counts.get(cat, 0) + 1

    print(f"\nLoss classifications ({len(losses)} total):")
    print(f"  Structural: {counts['structural']}")
    print(f"  Epistemic:  {counts['epistemic']}")
    print(f"  Refinement: {counts['refinement']}")

    for lc in losses:
        excerpt = lc.get("what_was_lost_excerpt", "")[:60]
        cat = lc.get("classification", "?")
        reason = lc.get("reasoning", "")
        print(f"  [{cat:11s}] {excerpt}...")
        print(f"              {reason}")

    # Strand summary
    s_counts = {"research-oriented": 0, "procedural": 0}
    for sc in strands:
        cat = sc.get("classification", "unknown")
        s_counts[cat] = s_counts.get(cat, 0) + 1

    print(f"\nStrand classifications ({len(strands)} total):")
    print(f"  Research-oriented: {s_counts['research-oriented']}")
    print(f"  Procedural:        {s_counts['procedural']}")

    for sc in strands:
        title = sc.get("title", "")[:50]
        cat = sc.get("classification", "?")
        print(f"  [{cat:18s}] {title}")

    print(f"\nOverall: {result.get('overall_assessment', '')}")


def _print_comparative(result: dict) -> None:
    """Print a comparative judgment."""
    _print_isolated(result.get("tensor_a", {}), "Tensor A")
    _print_isolated(result.get("tensor_b", {}), "Tensor B")

    comp = result.get("comparison", {})
    print(f"\n{'=' * 60}")
    print("COMPARISON")
    print(f"{'=' * 60}")
    print(f"\nLoss difference: {comp.get('loss_sophistication_difference', '')}")
    print(f"\nStrand difference: {comp.get('strand_character_difference', '')}")
    print(f"\nOverall: {comp.get('overall_comparison', '')}")


def main():
    parser = argparse.ArgumentParser(
        description="Q2 tensor judge — pre-registered rubric evaluation"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    iso_parser = subparsers.add_parser("isolated", help="Judge a single tensor")
    iso_parser.add_argument("tensor", type=Path, help="Path to tensor JSON")
    iso_parser.add_argument("--output", type=Path, default=None, help="Output directory")
    iso_parser.add_argument("--model", default="claude-sonnet-4-6", help="Judge model")

    comp_parser = subparsers.add_parser("comparative", help="Compare two tensors")
    comp_parser.add_argument("tensor_a", type=Path, help="Path to tensor A")
    comp_parser.add_argument("tensor_b", type=Path, help="Path to tensor B")
    comp_parser.add_argument("--output", type=Path, default=None, help="Output directory")
    comp_parser.add_argument("--model", default="claude-sonnet-4-6", help="Judge model")

    args = parser.parse_args()
    client = anthropic.Anthropic()

    if args.mode == "isolated":
        result = judge_isolated(args.tensor, client, model=args.model)
        _print_isolated(result, args.tensor.name)

        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            out_path = args.output / f"isolated_{args.tensor.stem}.json"
            out_path.write_text(json.dumps(result, indent=2))
            print(f"\nSaved to {out_path}")

    elif args.mode == "comparative":
        result = judge_comparative(args.tensor_a, args.tensor_b, client, model=args.model)
        _print_comparative(result)

        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            out_path = args.output / f"comparative_{args.tensor_a.stem}_vs_{args.tensor_b.stem}.json"
            out_path.write_text(json.dumps(result, indent=2))
            print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
