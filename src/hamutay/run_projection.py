"""Run the projector against conversation data and observe tensor evolution.

This is the first experiment: feed real conversation turns through the
projector and measure whether the tensor stabilizes or drifts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hamutay.log_reader import ConversationTurn, read_session_jsonl
from hamutay.projector import Projector
from hamutay.tensor import Tensor


def run_projection(
    session_path: Path,
    output_dir: Path | None = None,
    max_turns: int | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> list[Tensor]:
    """Run the projector against a session file, producing a tensor per turn.

    Returns the sequence of tensors — the trajectory through tensor space.
    """
    turns = read_session_jsonl(session_path)
    if max_turns:
        turns = turns[:max_turns]

    if not turns:
        print("No turns found in session file.")
        return []

    projector = Projector(model=model)
    tensors: list[Tensor] = []

    for turn in turns:
        content = f"[{turn.role}] {turn.content}"
        print(f"  cycle {projector.cycle + 1}: projecting {turn.role} turn "
              f"({len(turn.content)} chars)...")

        tensor = projector.project(content)
        tensors.append(tensor)

        # Report tensor stats
        n_strands = len(tensor.strands)
        n_claims = sum(len(s.key_claims) for s in tensor.strands)
        n_losses = len(tensor.declared_losses)
        n_questions = len(tensor.open_questions)
        tokens = tensor.token_estimate()

        print(f"    -> {n_strands} strands, {n_claims} claims, "
              f"{n_losses} losses, {n_questions} open questions, "
              f"~{tokens} tokens")
        print(f"    -> T={tensor.epistemic.truth:.2f} "
              f"I={tensor.epistemic.indeterminacy:.2f} "
              f"F={tensor.epistemic.falsity:.2f}")

        if tensor.instructions_for_next:
            preview = tensor.instructions_for_next[:100]
            print(f"    -> next: {preview}...")

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        for t in tensors:
            path = output_dir / f"tensor_cycle_{t.cycle:03d}.json"
            path.write_text(t.model_dump_json(indent=2))
        print(f"\nWrote {len(tensors)} tensors to {output_dir}")

    return tensors


def print_tensor_trajectory(tensors: list[Tensor]) -> None:
    """Print a summary of how the tensor evolved across cycles."""
    if not tensors:
        return

    print("\n=== Tensor Trajectory ===\n")

    for t in tensors:
        strand_titles = [s.title for s in t.strands]
        print(f"Cycle {t.cycle}: strands={strand_titles}")

        for loss in t.declared_losses:
            print(f"  LOSS: {loss.what_was_lost} ({loss.category.value})")

        if t.open_questions:
            print(f"  OPEN: {', '.join(t.open_questions[:3])}")

    # Track strand evolution
    print("\n=== Strand Stability ===\n")
    all_titles: list[set[str]] = [
        {s.title for s in t.strands} for t in tensors
    ]
    for i in range(1, len(all_titles)):
        added = all_titles[i] - all_titles[i - 1]
        removed = all_titles[i - 1] - all_titles[i]
        stable = all_titles[i] & all_titles[i - 1]
        print(f"Cycle {i} -> {i + 1}: "
              f"+{len(added)} -{len(removed)} ={len(stable)}")
        if added:
            print(f"  added: {added}")
        if removed:
            print(f"  removed: {removed}")

    # Compression ratio
    print("\n=== Compression ===\n")
    final = tensors[-1]
    print(f"Final tensor: ~{final.token_estimate()} tokens")
    print(f"Cycles processed: {final.cycle}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m hamutay.run_projection <session.jsonl> [output_dir] [max_turns]")
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    max_turns = int(sys.argv[3]) if len(sys.argv) > 3 else None

    tensors = run_projection(session_path, output_dir, max_turns)
    print_tensor_trajectory(tensors)
