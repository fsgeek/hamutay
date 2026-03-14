"""Run the projector with batched turns — group N turns into one projection cycle.

This lets us compare per-turn projection vs batched projection
and see how batch size affects tensor stability and content quality.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hamutay.log_reader import ConversationTurn, read_session_jsonl
from hamutay.projector import Projector
from hamutay.tensor import Tensor


def run_batched_projection(
    session_path: Path,
    output_dir: Path | None = None,
    batch_size: int = 3,
    max_cycles: int | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> list[Tensor]:
    """Run the projector with turns grouped into batches.

    Instead of projecting every turn individually, accumulate
    batch_size turns and project them as a single content block.
    """
    turns = read_session_jsonl(session_path)
    if not turns:
        print("No turns found in session file.")
        return []

    # Group turns into batches
    batches: list[list[ConversationTurn]] = []
    for i in range(0, len(turns), batch_size):
        batches.append(turns[i : i + batch_size])

    if max_cycles:
        batches = batches[:max_cycles]

    projector = Projector(model=model)
    tensors: list[Tensor] = []

    for batch in batches:
        # Combine batch turns into a single content block
        parts = []
        for turn in batch:
            parts.append(f"[{turn.role} turn {turn.turn_number}] {turn.content}")
        content = "\n\n---\n\n".join(parts)

        turn_range = f"{batch[0].turn_number}-{batch[-1].turn_number}"
        total_chars = sum(len(t.content) for t in batch)
        print(f"  cycle {projector.cycle + 1}: projecting turns {turn_range} "
              f"({len(batch)} turns, {total_chars} chars)...")

        tensor = projector.project(content)
        tensors.append(tensor)

        n_strands = len(tensor.strands)
        n_claims = sum(len(s.key_claims) for s in tensor.strands)
        n_losses = len(tensor.declared_losses)
        tokens = tensor.token_estimate()

        print(f"    -> {n_strands} strands, {n_claims} claims, "
              f"{n_losses} losses, ~{tokens} tokens")
        print(f"    -> T={tensor.epistemic.truth:.2f} "
              f"I={tensor.epistemic.indeterminacy:.2f} "
              f"F={tensor.epistemic.falsity:.2f}")

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        for t in tensors:
            path = output_dir / f"tensor_cycle_{t.cycle:03d}.json"
            path.write_text(t.model_dump_json(indent=2))
        print(f"\nWrote {len(tensors)} tensors to {output_dir}")

    # Print strand stability
    if len(tensors) > 1:
        print("\n=== Strand Stability ===\n")
        for i in range(1, len(tensors)):
            prev = {s.title for s in tensors[i - 1].strands}
            curr = {s.title for s in tensors[i].strands}
            added = curr - prev
            removed = prev - curr
            stable = curr & prev
            print(f"Cycle {i} -> {i + 1}: "
                  f"+{len(added)} -{len(removed)} ={len(stable)}")

    return tensors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m hamutay.run_projection_batched <session.jsonl> "
              "[output_dir] [batch_size] [max_cycles]")
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    max_cycles = int(sys.argv[4]) if len(sys.argv) > 4 else None

    run_batched_projection(session_path, output_dir, batch_size, max_cycles)
