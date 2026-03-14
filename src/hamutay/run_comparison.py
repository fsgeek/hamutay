"""Head-to-head comparison: tensor projection vs compaction.

Same conversation, same compressing model (Haiku), same reasoning model
(Sonnet). Two representations. Which one produces better reasoning?

This is the experiment that turns an argument into evidence.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic

from hamutay.compactor import Compactor
from hamutay.log_reader import ConversationTurn, read_session_jsonl
from hamutay.projector import Projector
from hamutay.tensor import Tensor


@dataclass
class ComparisonResult:
    """Results from one comparison run."""

    session_path: str
    num_turns: int
    batch_size: int

    # Tensor path
    tensor_json: str
    tensor_tokens: int
    tensor_cycles: int
    tensor_projection_time_s: float

    # Compaction path
    compaction_text: str
    compaction_tokens: int
    compaction_cycles: int
    compaction_time_s: float

    # Reasoning outputs
    tensor_reasoning: str
    compaction_reasoning: str
    reasoning_prompt: str

    def to_dict(self) -> dict:
        return {
            "session_path": self.session_path,
            "num_turns": self.num_turns,
            "batch_size": self.batch_size,
            "tensor": {
                "tokens": self.tensor_tokens,
                "cycles": self.tensor_cycles,
                "projection_time_s": self.tensor_projection_time_s,
                "json": self.tensor_json,
            },
            "compaction": {
                "tokens": self.compaction_tokens,
                "cycles": self.compaction_cycles,
                "compaction_time_s": self.compaction_time_s,
                "text": self.compaction_text,
            },
            "reasoning": {
                "prompt": self.reasoning_prompt,
                "from_tensor": self.tensor_reasoning,
                "from_compaction": self.compaction_reasoning,
            },
        }


# The reasoning prompt — what we ask Sonnet to do with each representation.
# This should be domain-agnostic enough to work with any conversation content.
REASONING_PROMPT = """\
You are given a compressed representation of a prior conversation. Your task is to \
reason about what was discussed and demonstrate your understanding.

Based on the representation below, answer the following:

1. **What is this conversation about?** Identify the core topic, project, or problem.
2. **What are the key technical decisions or findings?** List the most important ones.
3. **What is uncertain or unresolved?** What questions remain open?
4. **What should happen next?** Based on the state of the work, what are the logical \
next steps?
5. **What is missing from this representation?** What can you tell is NOT captured \
here that might matter? Be honest about the gaps you can perceive.

Be specific. Use details from the representation, not general knowledge.

## The Representation

{representation}
"""


def _prepare_batches(
    turns: list[ConversationTurn],
    batch_size: int,
) -> list[str]:
    """Group turns into batched content blocks."""
    batches: list[str] = []
    for i in range(0, len(turns), batch_size):
        batch = turns[i : i + batch_size]
        parts = []
        for turn in batch:
            parts.append(f"[{turn.role} turn {turn.turn_number}] {turn.content}")
        batches.append("\n\n---\n\n".join(parts))
    return batches


def _run_tensor_path(
    batches: list[str],
    model: str,
) -> tuple[Tensor, float]:
    """Run the tensor projection path."""
    projector = Projector(model=model)
    t0 = time.monotonic()
    for content in batches:
        tensor = projector.project(content)
        n_strands = len(tensor.strands)
        tokens = tensor.token_estimate()
        print(f"    tensor cycle {tensor.cycle}: {n_strands} strands, ~{tokens} tokens")
    elapsed = time.monotonic() - t0
    assert projector.current_tensor is not None
    return projector.current_tensor, elapsed


def _run_compaction_path(
    batches: list[str],
    model: str,
) -> tuple[str, float]:
    """Run the compaction path."""
    compactor = Compactor(model=model)
    t0 = time.monotonic()
    for content in batches:
        summary = compactor.compact(content)
        tokens = len(summary) // 4  # rough estimate
        print(f"    compaction cycle {compactor.cycle}: ~{tokens} tokens")
    elapsed = time.monotonic() - t0
    assert compactor.current_summary is not None
    return compactor.current_summary, elapsed


def _run_reasoning(
    representation: str,
    label: str,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> str:
    """Have the reasoning model work from a representation."""
    prompt = REASONING_PROMPT.format(representation=representation)

    print(f"  reasoning from {label}...")
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def run_comparison(
    session_path: Path,
    output_dir: Path,
    batch_size: int = 3,
    max_turns: int | None = None,
    compressor_model: str = "claude-haiku-4-5-20251001",
    reasoner_model: str = "claude-sonnet-4-6",
) -> ComparisonResult:
    """Run the full comparison: tensor vs compaction on the same conversation."""
    turns = read_session_jsonl(session_path)
    if max_turns:
        turns = turns[:max_turns]

    total_input_chars = sum(len(t.content) for t in turns)
    print(f"Loaded {len(turns)} turns ({total_input_chars:,} chars) from {session_path}")

    batches = _prepare_batches(turns, batch_size)
    print(f"Grouped into {len(batches)} batches (batch_size={batch_size})")

    # Run both paths
    print("\n--- Tensor Projection ---")
    tensor, tensor_time = _run_tensor_path(batches, compressor_model)

    print("\n--- Compaction ---")
    summary, compaction_time = _run_compaction_path(batches, compressor_model)

    # Prepare representations for reasoning
    tensor_repr = tensor.model_dump_json(indent=2)
    tensor_tokens = tensor.token_estimate()
    compaction_tokens = len(summary) // 4

    print(f"\nTensor: ~{tensor_tokens} tokens in {tensor_time:.1f}s")
    print(f"Compaction: ~{compaction_tokens} tokens in {compaction_time:.1f}s")

    # Run reasoning from each
    client = anthropic.Anthropic()
    print("\n--- Reasoning ---")
    tensor_reasoning = _run_reasoning(tensor_repr, "tensor", client, reasoner_model)
    compaction_reasoning = _run_reasoning(summary, "compaction", client, reasoner_model)

    # Build result
    result = ComparisonResult(
        session_path=str(session_path),
        num_turns=len(turns),
        batch_size=batch_size,
        tensor_json=tensor_repr,
        tensor_tokens=tensor_tokens,
        tensor_cycles=tensor.cycle,
        tensor_projection_time_s=tensor_time,
        compaction_text=summary,
        compaction_tokens=compaction_tokens,
        compaction_cycles=len(batches),
        compaction_time_s=compaction_time,
        tensor_reasoning=tensor_reasoning,
        compaction_reasoning=compaction_reasoning,
        reasoning_prompt=REASONING_PROMPT,
    )

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "comparison_result.json"
    output_path.write_text(json.dumps(result.to_dict(), indent=2))
    print(f"\nResults written to {output_path}")

    # Print side-by-side summary
    print("\n" + "=" * 60)
    print("TENSOR REASONING")
    print("=" * 60)
    print(tensor_reasoning)
    print("\n" + "=" * 60)
    print("COMPACTION REASONING")
    print("=" * 60)
    print(compaction_reasoning)

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m hamutay.run_comparison <session.jsonl> <output_dir> "
            "[batch_size] [max_turns]"
        )
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    max_turns = int(sys.argv[4]) if len(sys.argv) > 4 else None

    run_comparison(session_path, output_dir, batch_size, max_turns)
