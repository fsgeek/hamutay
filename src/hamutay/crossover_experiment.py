"""Crossover experiment — when does tensor projection earn its overhead?

Three representations tracked across a conversation:
1. cumulative_content_only — the raw append-only log, growing linearly
2. composed_tensor — iterative projection (tensor_{n-1} + batch → tensor_n)
3. constructed_tensor — fresh projection from cumulative text at each checkpoint

At each checkpoint, measure:
- Token count (via count_tokens API, not chars//4)
- Riemann dispersion (optional, expensive)

The crossover point is where the tensor's token count drops below the
cumulative raw text's token count. Below that point, raw text wins.
Above it, the tensor earns its compression overhead.

This is the experiment that asks: "when should you start compressing?"
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from hamutay.log_reader import ConversationTurn, read_session_jsonl
from hamutay.projector import Projector
from hamutay.riemann_experiment import (
    _run_condition,
    compute_dispersion,
)
from hamutay.tensor import Tensor


@dataclass
class Checkpoint:
    """Measurements at one point in the conversation."""

    cycle: int
    turn_end: int

    # Token counts (from count_tokens API)
    raw_tokens: int = 0
    composed_tensor_tokens: int = 0
    constructed_tensor_tokens: int = 0

    # The representations themselves (for dispersion measurement)
    raw_text: str = ""
    composed_tensor_json: str = ""
    constructed_tensor_json: str = ""

    # Dispersion (filled in later if measured)
    raw_dispersion: float | None = None
    composed_dispersion: float | None = None
    constructed_dispersion: float | None = None

    # Metadata
    composed_n_strands: int = 0
    composed_n_losses: int = 0
    composed_has_ifn: bool = False
    constructed_n_strands: int = 0
    constructed_n_losses: int = 0
    constructed_has_ifn: bool = False

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "turn_end": self.turn_end,
            "raw_tokens": self.raw_tokens,
            "composed_tensor_tokens": self.composed_tensor_tokens,
            "constructed_tensor_tokens": self.constructed_tensor_tokens,
            "raw_dispersion": self.raw_dispersion,
            "composed_dispersion": self.composed_dispersion,
            "constructed_dispersion": self.constructed_dispersion,
            "composed_n_strands": self.composed_n_strands,
            "composed_n_losses": self.composed_n_losses,
            "composed_has_ifn": self.composed_has_ifn,
            "constructed_n_strands": self.constructed_n_strands,
            "constructed_n_losses": self.constructed_n_losses,
            "constructed_has_ifn": self.constructed_has_ifn,
        }


def _count_tokens(
    client: anthropic.Anthropic,
    text: str,
    model: str = "claude-haiku-4-5-20251001",
) -> int:
    """Count tokens using the API — no estimation, real tokenizer."""
    result = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    return result.input_tokens


def _build_cumulative_text(turns: list[ConversationTurn]) -> str:
    """Build the cumulative raw text up to this point."""
    parts = [f"[{t.role} turn {t.turn_number}] {t.content}" for t in turns]
    return "\n\n---\n\n".join(parts)


def _construct_tensor(
    cumulative_text: str,
    client: anthropic.Anthropic,
    model: str,
) -> Tensor:
    """Project a tensor from scratch given all accumulated text.

    This is NOT iterative — it's a single projection from the full
    cumulative text. Asks: what if the projector saw everything at once?
    """
    projector = Projector(client=client, model=model)
    return projector.project(cumulative_text)


def run_crossover_experiment(
    session_path: Path,
    output_dir: Path,
    batch_size: int = 3,
    checkpoint_every: int = 5,
    max_cycles: int | None = None,
    projector_model: str = "claude-haiku-4-5-20251001",
    n_dispersion_runs: int = 0,
    dispersion_at_cycles: list[int] | None = None,
    reasoner_model: str = "claude-sonnet-4-6",
) -> list[Checkpoint]:
    """Run the crossover experiment.

    Args:
        checkpoint_every: measure all three representations every N cycles
        dispersion_at_cycles: specific cycles where to run Riemann dispersion
                              (expensive, so only at selected points)
    """
    client = anthropic.Anthropic()
    turns = read_session_jsonl(session_path)

    # Build batches
    batches: list[list[ConversationTurn]] = []
    for i in range(0, len(turns), batch_size):
        batches.append(turns[i : i + batch_size])
    if max_cycles:
        batches = batches[:max_cycles]

    print(f"Session: {session_path}")
    print(f"Turns: {len(turns)}, Batches: {len(batches)} (batch_size={batch_size})")
    print(f"Checkpoints every {checkpoint_every} cycles")
    print(f"Projector model: {projector_model}")
    if dispersion_at_cycles:
        print(f"Dispersion measurement at cycles: {dispersion_at_cycles}")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)

    # The composed projector runs iteratively
    composed_projector = Projector(client=client, model=projector_model)

    checkpoints: list[Checkpoint] = []
    all_turns_so_far: list[ConversationTurn] = []

    for cycle_idx, batch in enumerate(batches):
        cycle = cycle_idx + 1
        all_turns_so_far.extend(batch)

        # Build batch content for the composed projector
        batch_content = "\n\n---\n\n".join(
            f"[{t.role} turn {t.turn_number}] {t.content}" for t in batch
        )

        # Run composed projection (iterative)
        composed_tensor = composed_projector.project(batch_content)

        # Checkpoint?
        is_checkpoint = (cycle % checkpoint_every == 0) or (cycle == len(batches))
        if not is_checkpoint:
            # Still print progress
            print(f"  cycle {cycle:>3}: composed={composed_tensor.token_estimate():>6} est tokens, "
                  f"{len(composed_tensor.strands)} strands")
            continue

        print(f"\n  === Checkpoint at cycle {cycle} (turn {all_turns_so_far[-1].turn_number}) ===")

        # 1. Cumulative raw text
        raw_text = _build_cumulative_text(all_turns_so_far)
        raw_tokens = _count_tokens(client, raw_text)
        print(f"  Raw cumulative: {raw_tokens} tokens")

        # 2. Composed tensor (already computed)
        composed_json = composed_tensor.model_dump_json(indent=2)
        composed_tokens = _count_tokens(client, composed_json)
        print(f"  Composed tensor: {composed_tokens} tokens "
              f"({len(composed_tensor.strands)} strands, "
              f"{len(composed_tensor.declared_losses)} losses, "
              f"ifn={'Y' if composed_tensor.instructions_for_next else 'N'})")

        # 3. Constructed tensor (fresh projection from cumulative text)
        print(f"  Constructing tensor from scratch ({raw_tokens} tokens input)...")
        t0 = time.monotonic()
        constructed_tensor = _construct_tensor(raw_text, client, projector_model)
        t1 = time.monotonic()
        constructed_json = constructed_tensor.model_dump_json(indent=2)
        constructed_tokens = _count_tokens(client, constructed_json)
        print(f"  Constructed tensor: {constructed_tokens} tokens "
              f"({len(constructed_tensor.strands)} strands, "
              f"{len(constructed_tensor.declared_losses)} losses, "
              f"ifn={'Y' if constructed_tensor.instructions_for_next else 'N'}) "
              f"[{t1-t0:.1f}s]")

        # Ratios
        composed_ratio = composed_tokens / raw_tokens if raw_tokens > 0 else 0
        constructed_ratio = constructed_tokens / raw_tokens if raw_tokens > 0 else 0
        print(f"  Ratios: composed={composed_ratio:.2f}x, constructed={constructed_ratio:.2f}x")

        crossover_composed = "YES" if composed_tokens < raw_tokens else "no"
        crossover_constructed = "YES" if constructed_tokens < raw_tokens else "no"
        print(f"  Crossover: composed={crossover_composed}, constructed={crossover_constructed}")

        cp = Checkpoint(
            cycle=cycle,
            turn_end=all_turns_so_far[-1].turn_number,
            raw_tokens=raw_tokens,
            composed_tensor_tokens=composed_tokens,
            constructed_tensor_tokens=constructed_tokens,
            raw_text=raw_text,
            composed_tensor_json=composed_json,
            constructed_tensor_json=constructed_json,
            composed_n_strands=len(composed_tensor.strands),
            composed_n_losses=len(composed_tensor.declared_losses),
            composed_has_ifn=bool(composed_tensor.instructions_for_next),
            constructed_n_strands=len(constructed_tensor.strands),
            constructed_n_losses=len(constructed_tensor.declared_losses),
            constructed_has_ifn=bool(constructed_tensor.instructions_for_next),
        )
        checkpoints.append(cp)

    # Dispersion measurement at selected checkpoints
    if n_dispersion_runs > 0 and dispersion_at_cycles:
        print(f"\n{'=' * 60}")
        print(f"Measuring dispersion (N={n_dispersion_runs})")
        print(f"{'=' * 60}")

        for cp in checkpoints:
            if cp.cycle not in dispersion_at_cycles:
                continue

            print(f"\n  Cycle {cp.cycle} (turn {cp.turn_end}):")

            # Raw
            print(f"    raw ({cp.raw_tokens} tokens)...")
            raw_result = _run_condition(
                f"raw_c{cp.cycle}", "Cumulative raw text",
                cp.raw_text, n_dispersion_runs, client, reasoner_model,
            )
            cp.raw_dispersion = raw_result.dispersion

            # Composed tensor
            print(f"    composed ({cp.composed_tensor_tokens} tokens)...")
            composed_result = _run_condition(
                f"composed_c{cp.cycle}", "Composed tensor",
                cp.composed_tensor_json, n_dispersion_runs, client, reasoner_model,
            )
            cp.composed_dispersion = composed_result.dispersion

            # Constructed tensor
            print(f"    constructed ({cp.constructed_tensor_tokens} tokens)...")
            constructed_result = _run_condition(
                f"constructed_c{cp.cycle}", "Constructed tensor",
                cp.constructed_tensor_json, n_dispersion_runs, client, reasoner_model,
            )
            cp.constructed_dispersion = constructed_result.dispersion

            print(f"    Dispersion: raw={cp.raw_dispersion:.6f}, "
                  f"composed={cp.composed_dispersion:.6f}, "
                  f"constructed={cp.constructed_dispersion:.6f}")

    # Save results (without the full text representations to keep file size sane)
    experiment_data = {
        "session_path": str(session_path),
        "n_turns": len(turns),
        "n_batches": len(batches),
        "batch_size": batch_size,
        "checkpoint_every": checkpoint_every,
        "projector_model": projector_model,
        "n_dispersion_runs": n_dispersion_runs,
        "dispersion_at_cycles": dispersion_at_cycles,
        "reasoner_model": reasoner_model,
        "checkpoints": [cp.to_dict() for cp in checkpoints],
    }

    output_path = output_dir / "crossover_results.json"
    output_path.write_text(json.dumps(experiment_data, indent=2))

    # Print summary table
    print(f"\n{'=' * 85}")
    print(f"{'Cycle':>5} {'Turn':>5} {'Raw':>8} {'Composed':>9} {'Constructed':>12} "
          f"{'C/R':>6} {'X/R':>6} {'Cross?':>7}")
    print(f"{'-' * 85}")
    for cp in checkpoints:
        c_ratio = cp.composed_tensor_tokens / cp.raw_tokens if cp.raw_tokens > 0 else 0
        x_ratio = cp.constructed_tensor_tokens / cp.raw_tokens if cp.raw_tokens > 0 else 0
        cross = "YES" if cp.composed_tensor_tokens < cp.raw_tokens else ""
        print(f"{cp.cycle:>5} {cp.turn_end:>5} {cp.raw_tokens:>8} "
              f"{cp.composed_tensor_tokens:>9} {cp.constructed_tensor_tokens:>12} "
              f"{c_ratio:>6.2f} {x_ratio:>6.2f} {cross:>7}")
    print(f"{'=' * 85}")

    if any(cp.composed_dispersion is not None for cp in checkpoints):
        print(f"\n{'=' * 75}")
        print(f"{'Cycle':>5} {'Raw disp':>10} {'Comp disp':>10} {'Const disp':>11} {'Winner':>10}")
        print(f"{'-' * 75}")
        for cp in checkpoints:
            if cp.raw_dispersion is None:
                continue
            vals = {
                "raw": cp.raw_dispersion,
                "composed": cp.composed_dispersion,
                "constructed": cp.constructed_dispersion,
            }
            winner = min(vals, key=lambda k: vals[k] if vals[k] is not None else float('inf'))
            print(f"{cp.cycle:>5} {cp.raw_dispersion:>10.6f} "
                  f"{cp.composed_dispersion:>10.6f} "
                  f"{cp.constructed_dispersion:>11.6f} {winner:>10}")
        print(f"{'=' * 75}")

    print(f"\nResults: {output_path}")
    return checkpoints


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m hamutay.crossover_experiment "
            "<session.jsonl> <output_dir> "
            "[batch_size] [checkpoint_every] [max_cycles]"
        )
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    checkpoint_every = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    max_cycles = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] else None

    run_crossover_experiment(
        session_path,
        output_dir,
        batch_size=batch_size,
        checkpoint_every=checkpoint_every,
        max_cycles=max_cycles,
    )
