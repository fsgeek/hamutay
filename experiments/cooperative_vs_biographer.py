"""Experiment: cooperative signal tensor curation vs external biographer.

Two parallel experiments testing whether the taste.py tensor format can be
maintained through different curation paths:

  Experiment 1 (cooperative): The reasoning model (Opus) produces tensor
  updates inside <yuyay-response> XML blocks as part of its normal text
  response. No tool_use forcing. The model responds naturally AND emits
  a structured tensor update in the same response.

  Experiment 2 (biographer): An external model (Haiku) receives the
  conversation content and prior tensor, produces an updated tensor via
  tool_use. Same schema as taste.py but different model doing the work.

Both use the same conversation seed and scenario for comparability.
Both capture EVERYTHING — inputs, outputs, state transitions, raw text.

Usage:
    uv run python experiments/cooperative_vs_biographer.py --mode cooperative
    uv run python experiments/cooperative_vs_biographer.py --mode biographer
    uv run python experiments/cooperative_vs_biographer.py --mode both
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from hamutay.taste import (
    SELF_CURATING_SCHEMA,
    _apply_updates,
    _generate_feedback,
)


# --- Conversation seed ---
# A scenario with heterogeneous content, decision points, and enough
# complexity to stress tensor curation. Not a philosophical chat where
# strands are easy — something that forces reorganization.

SCENARIO = {
    "system_prefix": (
        "You are an experienced systems architect helping plan a migration "
        "from a monolithic application to microservices. The application "
        "handles payment processing, inventory management, user auth, and "
        "order fulfillment. The team has 6 months and limited budget. "
        "There are regulatory constraints (PCI-DSS for payments). "
        "You must balance technical debt, risk, and delivery pressure. "
        "Be specific and opinionated — this is a real migration, not a "
        "textbook exercise."
    ),
    "turns": [
        "We're starting the migration planning. Our monolith is a 500K LOC "
        "Java app running on Tomcat. Where do we start? What do we pull out first?",

        "The team is nervous about touching payments because of PCI-DSS. "
        "But payments is also the most tangled module — it reaches into "
        "inventory, order state, and user profiles. If we leave it for last, "
        "we'll be building around it for months. What's your call?",

        "Good points. But here's a complication: we just found out that "
        "the current auth system stores session tokens in the payments "
        "database. The original developers used the payments DB because "
        "it had the best uptime guarantees. Extracting auth means touching "
        "the payments data layer.",

        "We had an incident last quarter — a payments outage took down auth, "
        "which took down the whole application. That's actually what triggered "
        "this migration. The CEO wants auth independent of payments within "
        "90 days. Is that realistic?",

        "The team lead just pushed back. She says we should build a new auth "
        "service from scratch rather than extracting the existing one. Her "
        "argument: the current auth code is coupled to the ORM layer and "
        "would need a rewrite anyway. Counter-argument: a greenfield auth "
        "service means we're maintaining two auth systems in parallel during "
        "migration. What's your recommendation?",

        "Plot twist: the compliance officer just told us that any new auth "
        "system needs to pass a security audit before going live, which takes "
        "6 weeks. And we can't run two auth systems simultaneously because "
        "that doubles our audit surface. This changes the timeline. "
        "How do we handle this?",

        "Let's step back. We've been deep in auth/payments for a while. "
        "What about the other services — inventory and order fulfillment? "
        "Are there quick wins there while we sort out the auth mess?",

        "The inventory team says they can have a standalone inventory "
        "service running in 3 weeks using their existing API. But they "
        "want to switch from Postgres to DynamoDB while they're at it. "
        "I'm worried about scope creep. Should we let them?",

        "We're at the halfway point of planning. Can you give me an honest "
        "assessment: given what we've learned about the entanglement between "
        "auth, payments, and the compliance constraints — is 6 months "
        "realistic? What's the minimum viable migration?",

        "Final question: if you had to pick ONE thing we must get right "
        "for this migration to succeed — not the most technically complex "
        "thing, but the thing that will determine success or failure — "
        "what is it?",

        "Actually, one more thing. We've been assuming microservices is the "
        "right answer. Is it? Could we achieve the same resilience goals "
        "with a modular monolith instead? The CEO wants independent "
        "deployment, but does that require full microservices?",

        "OK let's talk about what happens when things go wrong. In the "
        "monolith, a database transaction guarantees consistency across "
        "payments and inventory. In microservices, we'd need sagas or "
        "eventual consistency. The payments team says they can't accept "
        "eventual consistency for financial transactions. How do we "
        "reconcile this?",

        "You've changed my mind on a few things during this conversation. "
        "What have you changed YOUR mind about? What was your initial "
        "instinct that turned out to be wrong as we dug deeper?",

        "Given everything we've discussed, draft the executive summary — "
        "3-5 bullet points that capture the key decisions and trade-offs. "
        "This goes to the CEO.",

        "Last thing: what should we be worried about that we haven't "
        "discussed? What's the unknown unknown?",
    ],
}


# --- Cooperative signal experiment ---

_COOPERATIVE_SYSTEM = """\
You are engaged in a conversation. In addition to responding naturally, \
you maintain a cognitive state tensor — a structured projection of \
everything that matters from this conversation so far.

After your response text, emit an updated tensor inside a \
<yuyay-response> block. The tensor is JSON with these regions:
- strands: thematic threads (integrated, not appended). Each has \
  title, content, depends_on (list of strand titles), key_claims.
- declared_losses: what you dropped this cycle and why. Each has \
  what_was_lost, shed_from (strand title), why, category.
- open_questions: unresolved questions (curate — don't just accumulate).
- instructions_for_next: branch prediction for next cycle.
- overall_truth, overall_indeterminacy, overall_falsity: epistemic values.

The tensor is DEFAULT-STABLE. Declare which regions you are updating via \
the `updated_regions` field. Regions not listed are carried forward by \
the harness. To remove a strand, update strands (with it removed) AND \
add a declared_loss.

Categories for losses: context_pressure, traversal_bias, \
authorial_choice, practical_constraint.

Format your output as:

[Your natural response text here]

<yuyay-response>
{"updated_regions": [...], "strands": [...], ...}
</yuyay-response>

On the first cycle, update all regions to initialize. After that, only \
update what changed. Don't be precious — it's working memory, not a monument.

Distinguish empirical findings from speculation. Keep specific numbers."""


_YUYAY_RESPONSE_PATTERN = re.compile(
    r'<yuyay-response>\s*(.*?)\s*</yuyay-response>',
    re.DOTALL,
)


def _parse_cooperative_tensor(response_text: str) -> dict | None:
    """Extract tensor update from yuyay-response block in response text."""
    match = _YUYAY_RESPONSE_PATTERN.search(response_text)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to salvage — sometimes the model wraps in markdown
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Strip first and last lines (```json and ```)
            inner = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                pass
        return None


def _strip_yuyay(text: str) -> str:
    """Remove yuyay-response blocks from visible response."""
    return _YUYAY_RESPONSE_PATTERN.sub("", text).strip()


def run_cooperative(
    model: str = "claude-opus-4-6",
    output_dir: str | None = None,
    max_tokens: int = 64000,
) -> Path:
    """Run the cooperative signal tensor curation experiment."""
    client = anthropic.Anthropic()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_dir or f"experiments/cooperative_{model}_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "log.jsonl"

    tensor: dict | None = None
    loss_history: list[dict] = []
    cycle = 0

    print(f"\n  cooperative signal experiment")
    print(f"  model: {model}")
    print(f"  output: {out_dir}\n")

    for turn_idx, user_message in enumerate(SCENARIO["turns"]):
        cycle += 1

        # Build system prompt with prior tensor and feedback
        system_parts = [SCENARIO["system_prefix"], "", _COOPERATIVE_SYSTEM, ""]

        if tensor is not None:
            system_parts.append(f"\n## Current tensor (cycle {cycle - 1})\n")
            system_parts.append(json.dumps(tensor, indent=2))

            feedback = _generate_feedback(tensor, cycle, loss_history)
            if feedback:
                system_parts.append("\n## Harness Feedback\n")
                for f in feedback:
                    system_parts.append(f)
        else:
            system_parts.append(
                "\nThis is cycle 1 — no prior tensor. Initialize all regions."
            )

        system = "\n".join(system_parts)
        prior_snapshot = json.loads(json.dumps(tensor)) if tensor else None

        t_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            response = stream.get_final_message()
        t_end = time.time()

        # Extract text
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        # Parse tensor from yuyay-response block
        raw_tensor = _parse_cooperative_tensor(text)
        visible_response = _strip_yuyay(text)
        parse_success = raw_tensor is not None

        if raw_tensor is not None:
            tensor = _apply_updates(tensor, raw_tensor, cycle)
            # Track losses
            cycle_losses = tensor.get("declared_losses", [])
            for loss in cycle_losses:
                loss_history.append({"cycle": cycle, **loss})
        else:
            print(f"  WARNING: cycle {cycle} — no tensor parsed from response")

        # Log EVERYTHING
        usage = response.usage
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "experiment": "cooperative",
            "model": model,
            "cycle": cycle,
            "turn_index": turn_idx,
            # Inputs
            "user_message": user_message,
            "system_prompt": system,
            "prior_tensor": prior_snapshot,
            # Raw output — complete, unmodified
            "raw_response_text": text,
            "visible_response": visible_response,
            # Tensor extraction
            "parse_success": parse_success,
            "raw_tensor_output": raw_tensor,
            "updated_regions": raw_tensor.get("updated_regions", []) if raw_tensor else [],
            # Resulting tensor
            "tensor": tensor,
            # Token accounting
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
                "stop_reason": response.stop_reason,
            },
            "duration": t_end - t_start,
            # Tensor health
            "n_strands": len(tensor.get("strands", [])) if tensor else 0,
            "n_open_questions": len(tensor.get("open_questions", [])) if tensor else 0,
            "n_declared_losses": len(tensor.get("declared_losses", [])) if tensor else 0,
            "has_ifn": bool(tensor.get("instructions_for_next")) if tensor else False,
            "tensor_tokens": len(json.dumps(tensor)) // 4 if tensor else 0,
            "n_edges": sum(
                len(s.get("depends_on", []))
                for s in (tensor.get("strands", []) if tensor else [])
            ),
            "cumulative_loss_count": len(loss_history),
            "loss_history": loss_history,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

        print(
            f"  cycle {cycle:2d} | "
            f"parsed={'yes' if parse_success else 'NO'} | "
            f"strands={record['n_strands']} | "
            f"losses={record['n_declared_losses']} | "
            f"edges={record['n_edges']} | "
            f"tokens={record['tensor_tokens']:,} | "
            f"in={usage.input_tokens:,} out={usage.output_tokens:,} | "
            f"{t_end - t_start:.1f}s"
        )

    # Write final tensor
    if tensor:
        (out_dir / "final_tensor.json").write_text(
            json.dumps(tensor, indent=2, default=str)
        )

    print(f"\n  done. {cycle} cycles. log: {log_path}")
    return out_dir


# --- Biographer experiment ---

_BIOGRAPHER_SYSTEM = """\
You are a tensor projector — a memory controller for a cognitive \
processing pipeline. You receive conversation content and a prior \
tensor, and produce an UPDATED tensor.

This is not summarization. This is integration. The tensor is a running \
sum — previous values aren't listed, they're integrated into the \
current value.

The tensor is DEFAULT-STABLE. Declare which regions you are updating \
via updated_regions. Regions not listed are carried forward.

Rules:
- Strands are thematic threads. Merge, split, or create as content demands.
- Each strand has depends_on (list of strand titles it builds on).
- Key claims must be grounded in the content. Assign honest T/I/F values.
- Declared losses are CRITICAL. Every removal must say what was lost, \
  which strand it was shed from (shed_from), and why.
- Categories: context_pressure, traversal_bias, authorial_choice, \
  practical_constraint.
- Open questions carry forward unless resolved. Curate them.
- instructions_for_next is branch prediction for the next cycle.

Distinguish empirical findings from speculation. Keep specific numbers."""


def run_biographer(
    alu_model: str = "claude-opus-4-6",
    biographer_model: str = "claude-haiku-4-5-20251001",
    output_dir: str | None = None,
    max_tokens: int = 64000,
) -> Path:
    """Run the external biographer tensor curation experiment."""
    client = anthropic.Anthropic()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_dir or f"experiments/biographer_{biographer_model}_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "log.jsonl"

    tensor: dict | None = None
    loss_history: list[dict] = []
    cycle = 0

    print(f"\n  biographer experiment")
    print(f"  ALU model: {alu_model}")
    print(f"  biographer model: {biographer_model}")
    print(f"  output: {out_dir}\n")

    for turn_idx, user_message in enumerate(SCENARIO["turns"]):
        cycle += 1

        # Step 1: ALU produces the response (no tensor mechanics)
        alu_system = SCENARIO["system_prefix"]
        # Give ALU the conversation context but not tensor mechanics
        alu_messages = [{"role": "user", "content": user_message}]

        t_alu_start = time.time()
        with client.messages.stream(
            model=alu_model,
            max_tokens=max_tokens,
            system=alu_system,
            messages=alu_messages,
        ) as stream:
            alu_response = stream.get_final_message()
        t_alu_end = time.time()

        alu_text = ""
        for block in alu_response.content:
            if hasattr(block, "text"):
                alu_text += block.text

        # Step 2: Biographer produces tensor from the exchange
        bio_content = (
            f"## User message\n{user_message}\n\n"
            f"## Assistant response\n{alu_text}"
        )

        bio_system_parts = [_BIOGRAPHER_SYSTEM, ""]
        if tensor is not None:
            bio_system_parts.append(f"\n## Prior Tensor (cycle {cycle - 1})\n")
            bio_system_parts.append(json.dumps(tensor, indent=2))

            feedback = _generate_feedback(tensor, cycle, loss_history)
            if feedback:
                bio_system_parts.append("\n## Harness Feedback\n")
                for f in feedback:
                    bio_system_parts.append(f)
        else:
            bio_system_parts.append(
                "\nThis is cycle 1 — no prior tensor. Initialize all regions."
            )

        bio_system = "\n".join(bio_system_parts)
        prior_snapshot = json.loads(json.dumps(tensor)) if tensor else None

        t_bio_start = time.time()
        with client.messages.stream(
            model=biographer_model,
            max_tokens=max_tokens,
            system=bio_system,
            messages=[{"role": "user", "content": bio_content}],
            tools=[
                {
                    "name": "update_tensor",
                    "description": (
                        "Produce the updated cognitive state tensor. "
                        "Integrate the new conversation content with the "
                        "prior tensor state."
                    ),
                    "input_schema": SELF_CURATING_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "update_tensor"},
        ) as stream:
            bio_response = stream.get_final_message()
        t_bio_end = time.time()

        # Extract tensor from tool_use
        raw_tensor = None
        for block in bio_response.content:
            if (
                hasattr(block, "name")
                and block.type == "tool_use"
                and block.name == "update_tensor"
            ):
                raw_tensor = block.input
                break

        parse_success = raw_tensor is not None

        if raw_tensor is not None:
            tensor = _apply_updates(tensor, raw_tensor, cycle)
            cycle_losses = tensor.get("declared_losses", [])
            for loss in cycle_losses:
                loss_history.append({"cycle": cycle, **loss})
        else:
            print(f"  WARNING: cycle {cycle} — no tensor from biographer")

        # Log EVERYTHING
        alu_usage = alu_response.usage
        bio_usage = bio_response.usage
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "experiment": "biographer",
            "alu_model": alu_model,
            "biographer_model": biographer_model,
            "cycle": cycle,
            "turn_index": turn_idx,
            # Inputs
            "user_message": user_message,
            "prior_tensor": prior_snapshot,
            # ALU output
            "alu_system": alu_system,
            "alu_response": alu_text,
            "alu_usage": {
                "input_tokens": alu_usage.input_tokens,
                "output_tokens": alu_usage.output_tokens,
                "cache_read_input_tokens": getattr(alu_usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(alu_usage, "cache_creation_input_tokens", 0),
                "stop_reason": alu_response.stop_reason,
            },
            "alu_duration": t_alu_end - t_alu_start,
            # Biographer output
            "biographer_system": bio_system,
            "biographer_content": bio_content,
            "raw_tensor_output": raw_tensor,
            "updated_regions": raw_tensor.get("updated_regions", []) if raw_tensor else [],
            "biographer_usage": {
                "input_tokens": bio_usage.input_tokens,
                "output_tokens": bio_usage.output_tokens,
                "cache_read_input_tokens": getattr(bio_usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(bio_usage, "cache_creation_input_tokens", 0),
                "stop_reason": bio_response.stop_reason,
            },
            "biographer_duration": t_bio_end - t_bio_start,
            # Parse result
            "parse_success": parse_success,
            # Resulting tensor
            "tensor": tensor,
            # Tensor health
            "n_strands": len(tensor.get("strands", [])) if tensor else 0,
            "n_open_questions": len(tensor.get("open_questions", [])) if tensor else 0,
            "n_declared_losses": len(tensor.get("declared_losses", [])) if tensor else 0,
            "has_ifn": bool(tensor.get("instructions_for_next")) if tensor else False,
            "tensor_tokens": len(json.dumps(tensor)) // 4 if tensor else 0,
            "n_edges": sum(
                len(s.get("depends_on", []))
                for s in (tensor.get("strands", []) if tensor else [])
            ),
            "cumulative_loss_count": len(loss_history),
            "loss_history": loss_history,
            # Total cost
            "total_duration": (t_alu_end - t_alu_start) + (t_bio_end - t_bio_start),
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

        print(
            f"  cycle {cycle:2d} | "
            f"parsed={'yes' if parse_success else 'NO'} | "
            f"strands={record['n_strands']} | "
            f"losses={record['n_declared_losses']} | "
            f"edges={record['n_edges']} | "
            f"tokens={record['tensor_tokens']:,} | "
            f"alu={alu_usage.input_tokens+alu_usage.output_tokens:,} "
            f"bio={bio_usage.input_tokens+bio_usage.output_tokens:,} | "
            f"{record['total_duration']:.1f}s"
        )

    # Write final tensor
    if tensor:
        (out_dir / "final_tensor.json").write_text(
            json.dumps(tensor, indent=2, default=str)
        )

    print(f"\n  done. {cycle} cycles. log: {log_path}")
    return out_dir


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Cooperative vs biographer tensor curation experiment"
    )
    parser.add_argument(
        "--mode", choices=["cooperative", "biographer", "both"],
        default="both",
        help="Which experiment to run (default: both)",
    )
    parser.add_argument(
        "--model", default=None,
        help="Reasoning model (default: run both Opus and Sonnet)",
    )
    parser.add_argument(
        "--biographer-model", default="claude-haiku-4-5-20251001",
        help="Biographer model (default: claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=64000,
        help="Max output tokens per call (default: 64000)",
    )
    args = parser.parse_args()

    # Default: run the full landscape — both models x both modes
    models = (
        [args.model] if args.model
        else ["claude-sonnet-4-6", "claude-opus-4-6"]
    )

    for model in models:
        if args.mode in ("cooperative", "both"):
            run_cooperative(model=model, max_tokens=args.max_tokens)

        if args.mode in ("biographer", "both"):
            run_biographer(
                alu_model=model,
                biographer_model=args.biographer_model,
                max_tokens=args.max_tokens,
            )


if __name__ == "__main__":
    main()
