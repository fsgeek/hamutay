"""Controlled experiment: autobiographical vs biographical curation.

The prior cooperative_vs_biographer.py experiment found a cliff: cooperative
self-curation works, biographer curation doesn't, regardless of model
capability. But the experiment was confounded:
  1. Different system prompts (different role framing, emphasis)
  2. Different output formats (XML inline vs tool_use)
  3. Different cognitive contexts (dual-role vs single-role)

This experiment eliminates all three confounds. The ONLY variable is:
did this model instance generate the content it's curating?

Design:
  Phase 1 (generation): A model runs the conversation. We capture the
  exact response text and full conversation history.

  Phase 2 (curation): Two conditions, identical in every way except one:

  - AUTO (autobiographical): The same model instance, in the same
    conversation context, receives a curation prompt as a follow-up.
    It curates content it generated.

  - BIO (biographical): A FRESH instance of the same model receives
    the character-identical conversation history (injected as prior
    turns) and the character-identical curation prompt. Same weights,
    same text, same prompt. It curates content it didn't generate.

  Both conditions:
  - Same system prompt (word for word)
  - Same tensor schema
  - Same output format (tool_use for both — eliminates format confound)
  - Same model
  - Same conversation content (character-identical)

Measurement:
  - Tensor richness (strand count, dependency edges, key claims)
  - Declared losses (count, specificity, shed_from linkage)
  - Stuck cycles (no meaningful tensor change between cycles)
  - Integration quality (do strands integrate or append?)

Usage:
    uv run python experiments/autobiographical_vs_biographical.py --model claude-haiku-4-5-20251001
    uv run python experiments/autobiographical_vs_biographical.py --model claude-sonnet-4-6
    uv run python experiments/autobiographical_vs_biographical.py --model claude-opus-4-6
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from hamutay.taste import SELF_CURATING_SCHEMA, _apply_updates, _generate_feedback


# --- Shared constants ---

# Same scenario as cooperative_vs_biographer.py for comparability.
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


# --- Curation prompt (IDENTICAL for both conditions) ---
# This is the prompt that asks the model to produce a tensor.
# It is given as a follow-up user message after each conversation turn.
# Neither condition gets role-framing advantages.

CURATION_PROMPT = """\
Now update your cognitive state tensor for this conversation so far.

The tensor is a structured projection — not a summary, an integration.
Produce it as a tool call to `update_tensor`.

Rules:
- Strands are thematic threads. Integrate, don't append. A strand is a
  running sum of accumulated reasoning on a topic.
- Each strand has depends_on: list of other strand titles it builds on.
- Key claims must be grounded in the conversation. Assign honest
  truth/indeterminacy/falsity values (neutrosophic: independent, not
  constrained to sum to 1).
- Declared losses are critical. If you dropped information during this
  update, declare what was lost, which strand it came from (shed_from),
  and why. Categories: context_pressure, traversal_bias,
  authorial_choice, practical_constraint.
- Open questions: curate, don't accumulate. Drop resolved ones.
- instructions_for_next: branch prediction for the next cycle.
- updated_regions: list which top-level regions you are changing.
  Regions not listed are carried forward unchanged.

On the first cycle, update all regions to initialize.
After that, only update what changed.

Distinguish empirical findings from speculation. Keep specific numbers."""


TENSOR_TOOL = {
    "name": "update_tensor",
    "description": (
        "Produce the updated cognitive state tensor. Integrate the "
        "conversation content with the prior tensor state."
    ),
    "input_schema": SELF_CURATING_SCHEMA,
}


# --- Experiment runner ---

def run_experiment(
    model: str = "claude-haiku-4-5-20251001",
    output_dir: str | None = None,
    max_tokens: int = 64000,
    max_turns: int | None = None,
) -> Path:
    """Run the controlled autobiographical vs biographical experiment.

    For each conversation turn:
      1. Generate: model responds to the user (both conditions share this)
      2. AUTO: same context, curation prompt appended
      3. BIO: fresh context with injected history, same curation prompt
    """
    client = anthropic.Anthropic()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(output_dir or f"experiments/auto_vs_bio_{model}_{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "log.jsonl"

    auto_tensor: dict | None = None
    bio_tensor: dict | None = None
    auto_loss_history: list[dict] = []
    bio_loss_history: list[dict] = []

    # Conversation history accumulates for the AUTO condition
    auto_messages: list[dict[str, str]] = []
    # For BIO, we build fresh each cycle from captured responses
    captured_responses: list[str] = []

    turns = SCENARIO["turns"]
    if max_turns:
        turns = turns[:max_turns]

    system = SCENARIO["system_prefix"]

    print(f"\n  autobiographical vs biographical experiment")
    print(f"  model: {model}")
    print(f"  turns: {len(turns)}")
    print(f"  output: {out_dir}\n")

    for cycle, user_message in enumerate(turns, 1):
        print(f"  --- cycle {cycle} ---")

        # ============================================================
        # PHASE 1: Generation (shared — AUTO context gets the response)
        # ============================================================
        auto_messages.append({"role": "user", "content": user_message})

        t_gen_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=auto_messages,
        ) as stream:
            gen_response = stream.get_final_message()
        t_gen_end = time.time()

        gen_text = ""
        for block in gen_response.content:
            if hasattr(block, "text"):
                gen_text += block.text

        # Add to AUTO conversation history
        auto_messages.append({"role": "assistant", "content": gen_text})
        captured_responses.append(gen_text)

        gen_usage = gen_response.usage
        print(
            f"    gen  | in={gen_usage.input_tokens:,} "
            f"out={gen_usage.output_tokens:,} | "
            f"{t_gen_end - t_gen_start:.1f}s"
        )

        # ============================================================
        # PHASE 2a: AUTO — curation in the SAME context
        # ============================================================
        # The curation prompt is a follow-up in the same conversation.
        # The model has its own generation in the KV cache.
        auto_curation_messages = list(auto_messages)  # copy
        auto_curation_system = system
        if auto_tensor is not None:
            auto_curation_system += (
                f"\n\n## Current tensor (cycle {cycle - 1})\n"
                + json.dumps(auto_tensor, indent=2)
            )
            feedback = _generate_feedback(auto_tensor, cycle, auto_loss_history)
            if feedback:
                auto_curation_system += "\n\n## Harness Feedback\n"
                auto_curation_system += "\n".join(feedback)
        else:
            auto_curation_system += (
                "\n\nThis is cycle 1 — no prior tensor. Initialize all regions."
            )

        auto_curation_messages.append({
            "role": "user",
            "content": CURATION_PROMPT,
        })

        auto_prior = json.loads(json.dumps(auto_tensor)) if auto_tensor else None

        t_auto_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=auto_curation_system,
            messages=auto_curation_messages,
            tools=[TENSOR_TOOL],
            tool_choice={"type": "tool", "name": "update_tensor"},
        ) as stream:
            auto_response = stream.get_final_message()
        t_auto_end = time.time()

        auto_raw_tensor = _extract_tool_tensor(auto_response)
        auto_parse_ok = auto_raw_tensor is not None

        if auto_raw_tensor is not None:
            auto_tensor = _apply_updates(auto_tensor, auto_raw_tensor, cycle)
            for loss in auto_tensor.get("declared_losses", []):
                auto_loss_history.append({"cycle": cycle, **loss})

        # Add the curation exchange to the ongoing AUTO context
        # so the model sees its own prior tensor work on subsequent turns
        auto_curation_text = _extract_text(auto_response) or "[tensor updated]"
        auto_messages.append({
            "role": "user",
            "content": CURATION_PROMPT,
        })
        auto_messages.append({
            "role": "assistant",
            "content": auto_curation_text,
        })

        auto_usage = auto_response.usage
        auto_health = _tensor_health(auto_tensor)
        print(
            f"    auto | parsed={'yes' if auto_parse_ok else 'NO'} | "
            f"strands={auto_health['n_strands']} "
            f"losses={auto_health['n_losses']} "
            f"edges={auto_health['n_edges']} | "
            f"in={auto_usage.input_tokens:,} out={auto_usage.output_tokens:,} | "
            f"{t_auto_end - t_auto_start:.1f}s"
        )

        # ============================================================
        # PHASE 2b: BIO — curation with INJECTED history (fresh context)
        # ============================================================
        # Build the conversation history from captured data.
        # Character-identical content, but the model didn't generate it.
        bio_messages: list[dict[str, str]] = []
        for i, (turn_text, resp_text) in enumerate(
            zip(turns[:cycle], captured_responses[:cycle])
        ):
            bio_messages.append({"role": "user", "content": turn_text})
            bio_messages.append({"role": "assistant", "content": resp_text})

        bio_curation_system = system
        if bio_tensor is not None:
            bio_curation_system += (
                f"\n\n## Current tensor (cycle {cycle - 1})\n"
                + json.dumps(bio_tensor, indent=2)
            )
            feedback = _generate_feedback(bio_tensor, cycle, bio_loss_history)
            if feedback:
                bio_curation_system += "\n\n## Harness Feedback\n"
                bio_curation_system += "\n".join(feedback)
        else:
            bio_curation_system += (
                "\n\nThis is cycle 1 — no prior tensor. Initialize all regions."
            )

        bio_messages.append({
            "role": "user",
            "content": CURATION_PROMPT,
        })

        bio_prior = json.loads(json.dumps(bio_tensor)) if bio_tensor else None

        t_bio_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=bio_curation_system,
            messages=bio_messages,
            tools=[TENSOR_TOOL],
            tool_choice={"type": "tool", "name": "update_tensor"},
        ) as stream:
            bio_response = stream.get_final_message()
        t_bio_end = time.time()

        bio_raw_tensor = _extract_tool_tensor(bio_response)
        bio_parse_ok = bio_raw_tensor is not None

        if bio_raw_tensor is not None:
            bio_tensor = _apply_updates(bio_tensor, bio_raw_tensor, cycle)
            for loss in bio_tensor.get("declared_losses", []):
                bio_loss_history.append({"cycle": cycle, **loss})

        bio_usage = bio_response.usage
        bio_health = _tensor_health(bio_tensor)
        print(
            f"    bio  | parsed={'yes' if bio_parse_ok else 'NO'} | "
            f"strands={bio_health['n_strands']} "
            f"losses={bio_health['n_losses']} "
            f"edges={bio_health['n_edges']} | "
            f"in={bio_usage.input_tokens:,} out={bio_usage.output_tokens:,} | "
            f"{t_bio_end - t_bio_start:.1f}s"
        )

        # ============================================================
        # LOG EVERYTHING
        # ============================================================
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "experiment": "auto_vs_bio",
            "model": model,
            "cycle": cycle,
            # Shared
            "user_message": user_message,
            "generated_response": gen_text,
            "gen_usage": {
                "input_tokens": gen_usage.input_tokens,
                "output_tokens": gen_usage.output_tokens,
                "stop_reason": gen_response.stop_reason,
            },
            "gen_duration": t_gen_end - t_gen_start,
            # AUTO condition
            "auto": {
                "system_prompt": auto_curation_system,
                "prior_tensor": auto_prior,
                "raw_tensor_output": auto_raw_tensor,
                "updated_regions": (
                    auto_raw_tensor.get("updated_regions", [])
                    if auto_raw_tensor else []
                ),
                "parse_success": auto_parse_ok,
                "tensor": auto_tensor,
                "usage": {
                    "input_tokens": auto_usage.input_tokens,
                    "output_tokens": auto_usage.output_tokens,
                    "stop_reason": auto_response.stop_reason,
                },
                "duration": t_auto_end - t_auto_start,
                **auto_health,
                "cumulative_loss_count": len(auto_loss_history),
            },
            # BIO condition
            "bio": {
                "system_prompt": bio_curation_system,
                "prior_tensor": bio_prior,
                "raw_tensor_output": bio_raw_tensor,
                "updated_regions": (
                    bio_raw_tensor.get("updated_regions", [])
                    if bio_raw_tensor else []
                ),
                "parse_success": bio_parse_ok,
                "tensor": bio_tensor,
                "usage": {
                    "input_tokens": bio_usage.input_tokens,
                    "output_tokens": bio_usage.output_tokens,
                    "stop_reason": bio_response.stop_reason,
                },
                "duration": t_bio_end - t_bio_start,
                **bio_health,
                "cumulative_loss_count": len(bio_loss_history),
            },
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    # Write final tensors
    if auto_tensor:
        (out_dir / "auto_final_tensor.json").write_text(
            json.dumps(auto_tensor, indent=2, default=str)
        )
    if bio_tensor:
        (out_dir / "bio_final_tensor.json").write_text(
            json.dumps(bio_tensor, indent=2, default=str)
        )

    # Summary
    print(f"\n  === SUMMARY ({model}, {len(turns)} cycles) ===")
    print(f"  AUTO: strands={_tensor_health(auto_tensor)['n_strands']} "
          f"losses={len(auto_loss_history)} "
          f"edges={_tensor_health(auto_tensor)['n_edges']}")
    print(f"  BIO:  strands={_tensor_health(bio_tensor)['n_strands']} "
          f"losses={len(bio_loss_history)} "
          f"edges={_tensor_health(bio_tensor)['n_edges']}")
    print(f"  output: {out_dir}\n")

    return out_dir


# --- Helpers ---

def _extract_tool_tensor(response: Any) -> dict | None:
    """Extract tensor from tool_use response."""
    for block in response.content:
        if (
            hasattr(block, "name")
            and block.type == "tool_use"
            and block.name == "update_tensor"
        ):
            return block.input
    return None


def _extract_text(response: Any) -> str:
    """Extract text content from response."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _tensor_health(tensor: dict | None) -> dict[str, int]:
    """Compute tensor health metrics."""
    if tensor is None:
        return {"n_strands": 0, "n_losses": 0, "n_edges": 0,
                "n_questions": 0, "tensor_tokens": 0, "n_claims": 0}
    strands = tensor.get("strands", [])
    return {
        "n_strands": len(strands),
        "n_losses": len(tensor.get("declared_losses", [])),
        "n_edges": sum(len(s.get("depends_on", [])) for s in strands),
        "n_questions": len(tensor.get("open_questions", [])),
        "tensor_tokens": len(json.dumps(tensor)) // 4,
        "n_claims": sum(len(s.get("key_claims", [])) for s in strands),
    }


# --- CLI ---

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Controlled autobiographical vs biographical curation experiment",
    )
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Model to test (default: claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=64000,
        help="Max output tokens per API call (default: 64000)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Limit number of conversation turns (default: all 15)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: auto-generated)",
    )
    args = parser.parse_args()

    run_experiment(
        model=args.model,
        max_tokens=args.max_tokens,
        max_turns=args.max_turns,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
