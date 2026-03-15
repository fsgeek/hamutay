"""Observational experiment — full-fidelity data collection.

No interventions, no escalation, no ablation. Just Haiku projecting
against untruncated conversation data, saving everything.

This is Phase 1: collect clean data, map the collapse landscape,
find the real crossover point. Design interventions later.

Output: JSONL with one record per cycle containing the full tensor,
full batch content, and all metrics. Disk is cheap. Research data is not.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import anthropic

from hamutay.log_reader import ConversationTurn, read_session_jsonl
from hamutay.projector import Projector


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
    """Build cumulative raw text from all turns so far."""
    parts = [f"[{t.role} turn {t.turn_number}] {t.content}" for t in turns]
    return "\n\n---\n\n".join(parts)


def run_observation(
    session_path: Path,
    output_dir: Path,
    batch_size: int = 3,
    max_cycles: int | None = None,
    projector_model: str = "claude-haiku-4-5-20251001",
    crossover_checkpoint_every: int = 5,
) -> None:
    """Run the observational experiment.

    Saves one JSONL record per cycle with:
    - Full batch content
    - Full tensor JSON
    - Token counts (batch, tensor, cumulative raw via API)
    - Structural metrics (strands, losses, ifn)
    - Collapse/precursor events
    - API stop_reason
    - Wall clock time

    Crossover data (cumulative raw token count and optional constructed
    tensor) is measured at checkpoints to avoid excessive API calls for
    token counting.
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
    print(f"Model: {projector_model}")
    print(f"Crossover checkpoints every {crossover_checkpoint_every} cycles")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "observations.jsonl"

    projector = Projector(client=client, model=projector_model)

    all_turns_so_far: list[ConversationTurn] = []

    with open(output_path, "w") as out:
        for cycle_idx, batch in enumerate(batches):
            cycle = cycle_idx + 1
            all_turns_so_far.extend(batch)

            # Build batch content
            batch_content = "\n\n---\n\n".join(
                f"[{t.role} turn {t.turn_number}] {t.content}" for t in batch
            )

            # Token count the batch
            batch_tokens = _count_tokens(client, batch_content)

            # Project
            t0 = time.monotonic()
            tensor = projector.project(batch_content)
            t1 = time.monotonic()
            projection_time = t1 - t0

            # Get the tensor as JSON
            tensor_json = tensor.model_dump_json(indent=2)
            tensor_tokens = _count_tokens(client, tensor_json)

            # Detect events from projector state
            # The projector already printed collapse/precursor/recovery info.
            # We capture the escalation log entry for this cycle.
            esc_entry = projector.escalation_log[-1] if projector.escalation_log else {}
            collapsed = esc_entry.get("collapsed", False)
            precursor = esc_entry.get("precursor_prior", False)

            # Actually, collapsed isn't in the log — we need to check.
            # The projector prints COLLAPSE but doesn't flag it in the log.
            # We can detect it: if the log has more entries than cycles,
            # retries happened. Or we check the tensor size ratio.
            prior_tensor_tokens = None
            if cycle > 1 and len(projector.escalation_log) >= 2:
                prior_entry = projector.escalation_log[-2]
                prior_tensor_tokens = prior_entry.get("tensor_tokens")

            # Build crossover data at checkpoints
            crossover_data = None
            is_checkpoint = (
                cycle % crossover_checkpoint_every == 0
            ) or cycle == len(batches)
            if is_checkpoint:
                raw_text = _build_cumulative_text(all_turns_so_far)
                raw_tokens = _count_tokens(client, raw_text)
                crossover_data = {
                    "cumulative_raw_tokens": raw_tokens,
                    "tensor_tokens": tensor_tokens,
                    "ratio": tensor_tokens / raw_tokens if raw_tokens > 0 else 0,
                    "crossed_over": tensor_tokens < raw_tokens,
                }
                print(
                    f"  cycle {cycle:>3} [checkpoint]: "
                    f"tensor={tensor_tokens:>6} tokens, "
                    f"raw={raw_tokens:>6} tokens, "
                    f"ratio={crossover_data['ratio']:.3f}, "
                    f"crossed={'YES' if crossover_data['crossed_over'] else 'no'}"
                )
            else:
                print(
                    f"  cycle {cycle:>3}: "
                    f"tensor={tensor_tokens:>6} tokens, "
                    f"{len(tensor.strands)} strands, "
                    f"{len(tensor.declared_losses)} losses, "
                    f"ifn={'Y' if tensor.instructions_for_next else 'N'}, "
                    f"{projection_time:.1f}s"
                )

            # Build the full record
            record = {
                "cycle": cycle,
                "turn_start": batch[0].turn_number,
                "turn_end": batch[-1].turn_number,
                "batch_content": batch_content,
                "batch_tokens": batch_tokens,
                "tensor": json.loads(tensor_json),
                "tensor_tokens": tensor_tokens,
                "tensor_token_estimate": tensor.token_estimate(),
                "n_strands": len(tensor.strands),
                "n_losses": len(tensor.declared_losses),
                "has_ifn": bool(tensor.instructions_for_next),
                "precursor_prior_cycle": precursor,
                "stop_reason": projector.last_stop_reason,
                "model": projector_model,
                "projection_time_s": round(projection_time, 2),
                "crossover": crossover_data,
            }

            out.write(json.dumps(record) + "\n")
            out.flush()

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"Observation complete: {cycle} cycles")
    print(f"Data saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m hamutay.observation_experiment "
            "<session.jsonl> <output_dir> "
            "[batch_size] [max_cycles]"
        )
        sys.exit(1)

    session_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    max_cycles = (
        int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None
    )

    run_observation(
        session_path,
        output_dir,
        batch_size=batch_size,
        max_cycles=max_cycles,
    )
