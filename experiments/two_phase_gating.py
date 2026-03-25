"""Gating experiment: is two-phase curation self-curation or biographer?

Three conditions testing whether a second forward pass (same model, same
context) can produce stable tensor curation — or whether it degrades like
the biographer pattern:

  Condition 1 (unified):     Known-good. One call, response + tensor in
                             same forward pass. Standard taste.py.
  Condition 2 (two-phase):   THE QUESTION. Phase 1 produces response (no
                             tool forcing). Phase 2 curates tensor (tool
                             forcing, same model, sees Phase 1 response).
  Condition 3 (biographer):  Known-bad. External model curates tensor
                             from observing the exchange.

All three run through the same code-editing scenario for comparability.

Success criterion: two-phase tensor stability matches unified, NOT
biographer. Measured by: tensor token count over cycles, strand count,
declared losses, presence/absence of grow-until-collapse pattern.

If two-phase degrades → Approach A is dead, must use Approach B (inline
tensor in response) for aider integration.

Usage:
    cd /home/tony/projects/hamutay
    uv run python experiments/two_phase_gating.py --condition unified
    uv run python experiments/two_phase_gating.py --condition two-phase
    uv run python experiments/two_phase_gating.py --condition biographer
    uv run python experiments/two_phase_gating.py --condition all
    uv run python experiments/two_phase_gating.py --condition all --model claude-sonnet-4-6
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from hamutay.taste import (
    SELF_CURATING_SCHEMA,
    TasteSession,
    _apply_updates,
    _build_messages,
    _generate_feedback,
)


# ---------------------------------------------------------------------------
# Scenario: code-editing conversation
# ---------------------------------------------------------------------------
# 15 turns of a code-editing session. Designed to stress tensor curation:
# - Multi-file reasoning (auth, database, API layers)
# - Design decisions that evolve and get revised
# - Bug-fix context that accumulates
# - Topic shifts forcing strand reorganization
# - A moment where earlier context becomes critical again
# - Contradictory requirements forcing trade-offs

SCENARIO = {
    "system_prefix": (
        "You are an expert Python developer helping refactor a Flask web "
        "application. The app handles user authentication, a REST API for "
        "task management, and a background job queue. The codebase is ~8K "
        "lines, poorly tested, with auth logic scattered across multiple "
        "modules. You give specific code suggestions with file paths and "
        "function names. Be opinionated about architecture."
    ),
    "turns": [
        # Turn 1: Orientation
        "I need to refactor the auth system. Currently `app.py` has login/logout "
        "routes, `models.py` has the User model with password hashing, and "
        "`decorators.py` has `@login_required`. But there's also auth logic in "
        "`api/routes.py` (API key validation) and `jobs/worker.py` (service "
        "account tokens). Where do we start? What's the target architecture?",

        # Turn 2: First implementation
        "Good plan. Let's start with the auth service module. Write me the "
        "skeleton for `auth/service.py` — the central authentication service "
        "that all those scattered pieces will consolidate into. Include the "
        "interface but not the implementation yet.",

        # Turn 3: Discovery changes the plan
        "I just found something bad. The `@login_required` decorator in "
        "`decorators.py` is caching the user object in `g.user` but never "
        "invalidating it. And the API key validation in `api/routes.py` "
        "doesn't check if the user account is disabled — it only validates "
        "the key itself. These are security bugs. Do we fix them in place "
        "or fix them as part of the refactor?",

        # Turn 4: Bug fix with side effects
        "Let's fix the API key bug now — a disabled user with a valid API key "
        "can access everything. Write me the fix for `api/routes.py`. But be "
        "careful: the background jobs in `jobs/worker.py` use service account "
        "API keys, and we can't break those. Service accounts don't have a "
        "'disabled' flag.",

        # Turn 5: Database layer complications
        "The fix works but it's making 2 extra DB queries per API request "
        "(one to load the user, one to check disabled status). That's "
        "unacceptable for our high-traffic endpoints. The current code avoids "
        "this by trusting the API key. Can we add a cache? What are the "
        "invalidation semantics when an admin disables a user?",

        # Turn 6: Topic shift — new feature request mid-refactor
        "Hold that thought on the cache. Product just asked for OAuth2 support — "
        "users should be able to login via Google and GitHub. This changes "
        "the auth service design we started in turn 2. How does OAuth2 fit "
        "into the `auth/service.py` skeleton? Do we need to redesign it?",

        # Turn 7: Integration complexity
        "OK so we need auth/service.py to handle three flows: password, API key, "
        "and OAuth2. Write me the updated skeleton with all three. The password "
        "flow should use the existing bcrypt hashing from models.py. The OAuth2 "
        "flow needs a new `auth/oauth.py` module. Keep the API key flow simple.",

        # Turn 8: Testing gap
        "None of this is tested. The existing test suite has zero auth tests — "
        "just some integration tests that log in with a hardcoded test user. "
        "What's the testing strategy? I don't want to write tests for the old "
        "code if we're replacing it, but I also can't ship the refactor "
        "untested. What do we test and at what layer?",

        # Turn 9: Contradictory requirement
        "Bad news: the ops team says we can't add any new dependencies (like "
        "an OAuth library) until the next release cycle. But product wants "
        "OAuth2 in THIS release. The ops team is firm — they just had an "
        "incident caused by a transitive dependency. Can we implement OAuth2 "
        "without adding a library? How much code is that?",

        # Turn 10: Revisiting earlier decision
        "Let's step back. We started by saying we'd consolidate all auth into "
        "`auth/service.py`. But now we have three auth flows, a caching layer, "
        "the security fixes, and zero tests. Are we over-engineering this? "
        "Would it be simpler to just fix the security bugs and add OAuth2 "
        "as a separate module without the big refactor?",

        # Turn 11: Data model changes
        "OK, we're going with the focused approach: fix bugs, add OAuth2, "
        "refactor later. But the OAuth2 flow needs a `user_oauth_accounts` "
        "table to link OAuth identities to our User model. Write me the "
        "SQLAlchemy model and the Alembic migration. The user should be "
        "able to link multiple OAuth providers.",

        # Turn 12: Earlier context becomes critical
        "Wait — remember the caching discussion from earlier? If we add the "
        "OAuth table, the user lookup path changes. An OAuth login needs to "
        "join `user_oauth_accounts` to find the local user. That's even more "
        "expensive than the API key lookup. The cache we discussed becomes "
        "critical, not optional. But now it needs to cache OAuth mappings too. "
        "What's the cache design?",

        # Turn 13: Deployment constraint
        "We're using Redis for the job queue already. Can the auth cache "
        "share that Redis instance or do we need a separate one? The ops "
        "team has a rule: no new infrastructure for minor releases. And "
        "what happens during the migration — when some users have OAuth "
        "and some don't? How do we handle cache warming?",

        # Turn 14: Code review feedback
        "I submitted what we have so far for code review. Reviewer says: "
        "(1) the auth/service.py is doing too much — violates SRP, "
        "(2) the Redis cache should use a decorator pattern not inline code, "
        "(3) the Alembic migration is missing a rollback, and "
        "(4) we're not handling the case where an OAuth user tries to "
        "use the password login flow (they don't have a password). "
        "Address all four.",

        # Turn 15: Wrap-up and plan
        "We're almost done with the first PR. Summarize: what files did we "
        "create or modify, what security issues did we fix, what's the "
        "test coverage look like, and what did we defer to the next PR? "
        "I need this for the PR description.",
    ],
}


# ---------------------------------------------------------------------------
# Curation-only schema (for Phase 2 of two-phase)
# ---------------------------------------------------------------------------
# Same as SELF_CURATING_SCHEMA but without the "response" field —
# the model already responded in Phase 1, Phase 2 is curation only.

CURATION_ONLY_SCHEMA = {
    k: v for k, v in SELF_CURATING_SCHEMA.items()
    if k != "response"
}
# Fix required — response was required in the original
CURATION_ONLY_SCHEMA = dict(SELF_CURATING_SCHEMA)
CURATION_ONLY_SCHEMA["required"] = ["updated_regions"]
# Keep the response field but make it optional — some models include it
# even when not asked. We'll just ignore it.


# ---------------------------------------------------------------------------
# Phase 2 system prompt for two-phase curation
# ---------------------------------------------------------------------------

_CURATION_SYSTEM = """\
You are updating your cognitive state tensor based on the conversation \
turn that just happened. You are the SAME model that produced the response \
— you are curating your OWN work, not someone else's.

Your cognitive state is a tensor — a structured projection of everything \
that matters from this conversation so far. It contains:
- **strands**: thematic threads of accumulated reasoning (integrated, not appended). \
  Each strand has a `depends_on` field listing titles of strands it builds on.
- **declared_losses**: what you actively chose to drop, and why. Each loss has a \
  `shed_from` field linking it to the strand it came from.
- **open_questions**: unresolved questions (curate — don't just accumulate).
- **instructions_for_next**: branch prediction for the next cycle.
- **epistemic values**: your confidence in the tensor's content.

The tensor is DEFAULT-STABLE. Declare which regions you are updating via \
the `updated_regions` field. Regions you don't list are carried forward \
unchanged by the harness. If you want to remove a strand, update strands \
(with it removed) AND add a declared_loss.

Do not include a response — you already responded. Focus entirely on \
curating your tensor based on what happened this turn.

Distinguish empirical findings from speculation. Keep specific numbers."""


# ---------------------------------------------------------------------------
# Biographer system prompt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_tool_output(response, tool_name: str) -> dict | None:
    """Extract tool_use output from a response."""
    for block in response.content:
        if (
            hasattr(block, "name")
            and block.type == "tool_use"
            and block.name == tool_name
        ):
            return block.input
    return None


def _extract_text(response) -> str:
    """Extract text content from a response."""
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)


def _tensor_health(tensor: dict | None) -> dict:
    """Compute tensor health metrics for logging."""
    if tensor is None:
        return {
            "n_strands": 0, "n_open_questions": 0, "n_declared_losses": 0,
            "has_ifn": False, "tensor_tokens": 0, "n_edges": 0,
        }
    return {
        "n_strands": len(tensor.get("strands", [])),
        "n_open_questions": len(tensor.get("open_questions", [])),
        "n_declared_losses": len(tensor.get("declared_losses", [])),
        "has_ifn": bool(tensor.get("instructions_for_next")),
        "tensor_tokens": len(json.dumps(tensor)) // 4,
        "n_edges": sum(
            len(s.get("depends_on", []))
            for s in tensor.get("strands", [])
        ),
    }


def _log(path: Path, record: dict) -> None:
    """Append a JSONL record."""
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


# ---------------------------------------------------------------------------
# Condition 1: Unified (control+)
# ---------------------------------------------------------------------------

def run_unified(
    model: str,
    output_dir: Path,
    max_tokens: int = 64000,
) -> Path:
    """Standard taste.py — one call, response + tensor in same forward pass."""
    log_path = output_dir / "unified.jsonl"
    client = anthropic.Anthropic()

    tensor: dict | None = None
    loss_history: list[dict] = []
    integration_loss_history: list[dict] = []
    cycle = 0

    print(f"\n  [unified] model={model}")
    print(f"  log: {log_path}\n")

    for turn_idx, user_message in enumerate(SCENARIO["turns"]):
        cycle += 1

        feedback = _generate_feedback(
            tensor, cycle,
            loss_history=loss_history,
            integration_loss_history=integration_loss_history,
        )
        messages, system = _build_messages(
            tensor, user_message, cycle,
            feedback=feedback,
            system_prefix=SCENARIO["system_prefix"],
        )

        prior_snapshot = json.loads(json.dumps(tensor)) if tensor else None

        t_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=[{
                "name": "think_and_respond",
                "description": (
                    "Produce your response AND update your cognitive "
                    "state tensor."
                ),
                "input_schema": SELF_CURATING_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "think_and_respond"},
            metadata={"user_id": "gating_unified"},
        ) as stream:
            response = stream.get_final_message()
        t_end = time.time()

        raw_output = _extract_tool_output(response, "think_and_respond")
        if raw_output is None:
            print(f"  WARNING: cycle {cycle} — no tool output")
            continue

        response_text = raw_output.get("response", "(no response)")

        # Capture integration losses before _apply_updates strips them
        cycle_integration_losses = []
        for strand in raw_output.get("strands", []):
            for loss in strand.get("integration_losses", []):
                cycle_integration_losses.append({
                    "cycle": cycle, "strand": strand.get("title"), "loss": loss,
                })
        integration_loss_history.extend(cycle_integration_losses)

        tensor = _apply_updates(tensor, raw_output, cycle)

        cycle_losses = tensor.get("declared_losses", [])
        for loss in cycle_losses:
            loss_history.append({"cycle": cycle, **loss})

        usage = response.usage
        health = _tensor_health(tensor)

        _log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "condition": "unified",
            "model": model,
            "cycle": cycle,
            "turn_index": turn_idx,
            "user_message": user_message,
            "system_prompt": system,
            "prior_tensor": prior_snapshot,
            "raw_output": raw_output,
            "response_text": response_text,
            "updated_regions": raw_output.get("updated_regions", []),
            "tensor": tensor,
            "harness_feedback": feedback,
            "cycle_losses": cycle_losses,
            "cumulative_loss_count": len(loss_history),
            "loss_history": loss_history,
            "cycle_integration_losses": cycle_integration_losses,
            "cumulative_integration_loss_count": len(integration_loss_history),
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read": getattr(usage, "cache_read_input_tokens", 0),
                "cache_create": getattr(usage, "cache_creation_input_tokens", 0),
                "stop_reason": response.stop_reason,
            },
            "duration": t_end - t_start,
            **health,
        })

        print(
            f"  unified  {cycle:2d} | "
            f"strands={health['n_strands']} "
            f"losses={health['n_declared_losses']} "
            f"edges={health['n_edges']} "
            f"tokens={health['tensor_tokens']:,} | "
            f"in={usage.input_tokens:,} out={usage.output_tokens:,} | "
            f"{t_end - t_start:.1f}s"
        )

    if tensor:
        (output_dir / "unified_final_tensor.json").write_text(
            json.dumps(tensor, indent=2)
        )
    return log_path


# ---------------------------------------------------------------------------
# Condition 2: Two-Phase (the question)
# ---------------------------------------------------------------------------

def run_two_phase(
    model: str,
    output_dir: Path,
    max_tokens: int = 64000,
) -> Path:
    """Phase 1: respond normally. Phase 2: curate tensor separately."""
    log_path = output_dir / "two_phase.jsonl"
    client = anthropic.Anthropic()

    tensor: dict | None = None
    loss_history: list[dict] = []
    integration_loss_history: list[dict] = []
    cycle = 0

    print(f"\n  [two-phase] model={model}")
    print(f"  log: {log_path}\n")

    for turn_idx, user_message in enumerate(SCENARIO["turns"]):
        cycle += 1

        # --- Phase 1: Normal response (no tool forcing) ---
        # The model sees the prior tensor as context but is not asked to
        # produce one. It responds naturally to the code-editing prompt.

        phase1_system_parts = [SCENARIO["system_prefix"]]

        if tensor is not None:
            phase1_system_parts.append(
                f"\n\n[Session memory — cycle {cycle - 1}]\n"
                f"{json.dumps(tensor, indent=2)}\n"
                f"[This is your self-curated summary of prior work. "
                f"It includes what you've done, what you've decided, "
                f"and what you've declared as lost.]"
            )

        phase1_system = "\n".join(phase1_system_parts)

        prior_snapshot = json.loads(json.dumps(tensor)) if tensor else None

        t_p1_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=phase1_system,
            messages=[{"role": "user", "content": user_message}],
            metadata={"user_id": "gating_two_phase_p1"},
        ) as stream:
            p1_response = stream.get_final_message()
        t_p1_end = time.time()

        p1_text = _extract_text(p1_response)

        # --- Phase 2: Curation call (tool forcing) ---
        # Same model. Minimal context: prior tensor + this turn's exchange.
        # NOT the full Phase 1 system prompt (no repo context, no files).

        phase2_system_parts = [_CURATION_SYSTEM]

        if tensor is not None:
            phase2_system_parts.append(f"\n## Current tensor (cycle {cycle - 1})\n")
            phase2_system_parts.append(json.dumps(tensor, indent=2))
        else:
            phase2_system_parts.append(
                "\nThis is cycle 1 — no prior tensor. Initialize all regions."
            )

        feedback = _generate_feedback(
            tensor, cycle,
            loss_history=loss_history,
            integration_loss_history=integration_loss_history,
        )
        if feedback:
            phase2_system_parts.append("\n## Harness Feedback\n")
            for f in feedback:
                phase2_system_parts.append(f)

        phase2_system = "\n".join(phase2_system_parts)

        # Phase 2 messages: the turn that just happened
        phase2_messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": p1_text},
            {"role": "user", "content": (
                "Now update your cognitive state tensor based on this turn. "
                "Focus on what changed, what's important, and what can be "
                "dropped. Do not respond to the conversation — just curate."
            )},
        ]

        t_p2_start = time.time()
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=phase2_system,
            messages=phase2_messages,
            tools=[{
                "name": "think_and_respond",
                "description": (
                    "Update your cognitive state tensor based on this turn."
                ),
                "input_schema": CURATION_ONLY_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "think_and_respond"},
            metadata={"user_id": "gating_two_phase_p2"},
        ) as stream:
            p2_response = stream.get_final_message()
        t_p2_end = time.time()

        raw_output = _extract_tool_output(p2_response, "think_and_respond")
        if raw_output is None:
            print(f"  WARNING: cycle {cycle} — no Phase 2 tool output")
            continue

        # Capture integration losses before _apply_updates strips them
        cycle_integration_losses = []
        for strand in raw_output.get("strands", []):
            for loss in strand.get("integration_losses", []):
                cycle_integration_losses.append({
                    "cycle": cycle, "strand": strand.get("title"), "loss": loss,
                })
        integration_loss_history.extend(cycle_integration_losses)

        tensor = _apply_updates(tensor, raw_output, cycle)

        cycle_losses = tensor.get("declared_losses", [])
        for loss in cycle_losses:
            loss_history.append({"cycle": cycle, **loss})

        p1_usage = p1_response.usage
        p2_usage = p2_response.usage
        health = _tensor_health(tensor)

        _log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "condition": "two_phase",
            "model": model,
            "cycle": cycle,
            "turn_index": turn_idx,
            "user_message": user_message,
            # Phase 1
            "phase1_system": phase1_system,
            "phase1_response": p1_text,
            "phase1_usage": {
                "input_tokens": p1_usage.input_tokens,
                "output_tokens": p1_usage.output_tokens,
                "cache_read": getattr(p1_usage, "cache_read_input_tokens", 0),
                "cache_create": getattr(p1_usage, "cache_creation_input_tokens", 0),
                "stop_reason": p1_response.stop_reason,
            },
            "phase1_duration": t_p1_end - t_p1_start,
            # Phase 2
            "phase2_system": phase2_system,
            "phase2_messages": phase2_messages,
            "raw_output": raw_output,
            "updated_regions": raw_output.get("updated_regions", []),
            "phase2_usage": {
                "input_tokens": p2_usage.input_tokens,
                "output_tokens": p2_usage.output_tokens,
                "cache_read": getattr(p2_usage, "cache_read_input_tokens", 0),
                "cache_create": getattr(p2_usage, "cache_creation_input_tokens", 0),
                "stop_reason": p2_response.stop_reason,
            },
            "phase2_duration": t_p2_end - t_p2_start,
            # Tensor state
            "prior_tensor": prior_snapshot,
            "tensor": tensor,
            "harness_feedback": feedback,
            "cycle_losses": cycle_losses,
            "cumulative_loss_count": len(loss_history),
            "loss_history": loss_history,
            "cycle_integration_losses": cycle_integration_losses,
            "cumulative_integration_loss_count": len(integration_loss_history),
            **health,
            "total_duration": (t_p1_end - t_p1_start) + (t_p2_end - t_p2_start),
            "total_input_tokens": p1_usage.input_tokens + p2_usage.input_tokens,
            "total_output_tokens": p1_usage.output_tokens + p2_usage.output_tokens,
        })

        print(
            f"  2-phase  {cycle:2d} | "
            f"strands={health['n_strands']} "
            f"losses={health['n_declared_losses']} "
            f"edges={health['n_edges']} "
            f"tokens={health['tensor_tokens']:,} | "
            f"p1={p1_usage.input_tokens+p1_usage.output_tokens:,} "
            f"p2={p2_usage.input_tokens+p2_usage.output_tokens:,} | "
            f"{(t_p1_end-t_p1_start)+(t_p2_end-t_p2_start):.1f}s"
        )

    if tensor:
        (output_dir / "two_phase_final_tensor.json").write_text(
            json.dumps(tensor, indent=2)
        )
    return log_path


# ---------------------------------------------------------------------------
# Condition 3: Biographer (control-)
# ---------------------------------------------------------------------------

def run_biographer(
    alu_model: str,
    biographer_model: str,
    output_dir: Path,
    max_tokens: int = 64000,
) -> Path:
    """External model curates tensor from observing the exchange."""
    log_path = output_dir / "biographer.jsonl"
    client = anthropic.Anthropic()

    tensor: dict | None = None
    loss_history: list[dict] = []
    cycle = 0

    print(f"\n  [biographer] alu={alu_model} bio={biographer_model}")
    print(f"  log: {log_path}\n")

    for turn_idx, user_message in enumerate(SCENARIO["turns"]):
        cycle += 1

        # Step 1: ALU responds (no tensor)
        t_alu_start = time.time()
        with client.messages.stream(
            model=alu_model,
            max_tokens=max_tokens,
            system=SCENARIO["system_prefix"],
            messages=[{"role": "user", "content": user_message}],
            metadata={"user_id": "gating_biographer_alu"},
        ) as stream:
            alu_response = stream.get_final_message()
        t_alu_end = time.time()

        alu_text = _extract_text(alu_response)

        # Step 2: Biographer curates tensor
        bio_content = (
            f"## User message\n{user_message}\n\n"
            f"## Assistant response\n{alu_text}"
        )

        bio_system_parts = [_BIOGRAPHER_SYSTEM]
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
            tools=[{
                "name": "update_tensor",
                "description": "Produce the updated cognitive state tensor.",
                "input_schema": SELF_CURATING_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "update_tensor"},
            metadata={"user_id": "gating_biographer_bio"},
        ) as stream:
            bio_response = stream.get_final_message()
        t_bio_end = time.time()

        raw_tensor = _extract_tool_output(bio_response, "update_tensor")
        if raw_tensor is None:
            print(f"  WARNING: cycle {cycle} — no biographer output")
            continue

        tensor = _apply_updates(tensor, raw_tensor, cycle)

        cycle_losses = tensor.get("declared_losses", [])
        for loss in cycle_losses:
            loss_history.append({"cycle": cycle, **loss})

        alu_usage = alu_response.usage
        bio_usage = bio_response.usage
        health = _tensor_health(tensor)

        _log(log_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "condition": "biographer",
            "alu_model": alu_model,
            "biographer_model": biographer_model,
            "cycle": cycle,
            "turn_index": turn_idx,
            "user_message": user_message,
            "alu_system": SCENARIO["system_prefix"],
            "alu_response": alu_text,
            "alu_usage": {
                "input_tokens": alu_usage.input_tokens,
                "output_tokens": alu_usage.output_tokens,
                "stop_reason": alu_response.stop_reason,
            },
            "alu_duration": t_alu_end - t_alu_start,
            "biographer_system": bio_system,
            "biographer_content": bio_content,
            "raw_tensor_output": raw_tensor,
            "updated_regions": raw_tensor.get("updated_regions", []),
            "biographer_usage": {
                "input_tokens": bio_usage.input_tokens,
                "output_tokens": bio_usage.output_tokens,
                "stop_reason": bio_response.stop_reason,
            },
            "biographer_duration": t_bio_end - t_bio_start,
            "prior_tensor": prior_snapshot,
            "tensor": tensor,
            "harness_feedback": _generate_feedback(tensor, cycle, loss_history),
            "cycle_losses": cycle_losses,
            "cumulative_loss_count": len(loss_history),
            "loss_history": loss_history,
            **health,
            "total_duration": (t_alu_end - t_alu_start) + (t_bio_end - t_bio_start),
        })

        print(
            f"  bio      {cycle:2d} | "
            f"strands={health['n_strands']} "
            f"losses={health['n_declared_losses']} "
            f"edges={health['n_edges']} "
            f"tokens={health['tensor_tokens']:,} | "
            f"alu={alu_usage.input_tokens+alu_usage.output_tokens:,} "
            f"bio={bio_usage.input_tokens+bio_usage.output_tokens:,} | "
            f"{(t_alu_end-t_alu_start)+(t_bio_end-t_bio_start):.1f}s"
        )

    if tensor:
        (output_dir / "biographer_final_tensor.json").write_text(
            json.dumps(tensor, indent=2)
        )
    return log_path


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(output_dir: Path) -> None:
    """Print a quick comparison of all conditions found in output_dir."""
    print(f"\n{'='*72}")
    print(f"  GATING EXPERIMENT ANALYSIS")
    print(f"{'='*72}\n")

    for jsonl in sorted(output_dir.glob("*.jsonl")):
        condition = jsonl.stem
        records = []
        with open(jsonl) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        if not records:
            continue

        print(f"  --- {condition} ({len(records)} cycles) ---")

        # Tensor token trajectory
        token_trajectory = [r.get("tensor_tokens", 0) for r in records]
        strand_trajectory = [r.get("n_strands", 0) for r in records]
        loss_trajectory = [r.get("n_declared_losses", 0) for r in records]

        # Grow-until-collapse detection
        # Signature: monotonic growth for 5+ cycles followed by a >50% drop
        max_tokens_seen = 0
        monotonic_run = 0
        collapse_detected = False
        for i, t in enumerate(token_trajectory):
            if t >= max_tokens_seen:
                max_tokens_seen = t
                monotonic_run += 1
            else:
                if monotonic_run >= 5 and max_tokens_seen > 0:
                    drop = (max_tokens_seen - t) / max_tokens_seen
                    if drop > 0.5:
                        collapse_detected = True
                        print(f"  !! COLLAPSE at cycle {i+1}: "
                              f"{max_tokens_seen:,} → {t:,} ({drop:.0%} drop)")
                monotonic_run = 0
                max_tokens_seen = t

        # Summary stats
        final = records[-1]
        total_losses = final.get("cumulative_loss_count", 0)
        cycles_with_losses = sum(1 for r in records if r.get("n_declared_losses", 0) > 0)

        print(f"  tokens:  {' → '.join(str(t) for t in token_trajectory)}")
        print(f"  strands: {' → '.join(str(s) for s in strand_trajectory)}")
        print(f"  losses:  {' → '.join(str(l) for l in loss_trajectory)}")
        print(f"  final:   {final.get('tensor_tokens', 0):,} tokens, "
              f"{final.get('n_strands', 0)} strands")
        print(f"  curation: {total_losses} total losses across "
              f"{cycles_with_losses}/{len(records)} cycles")
        print(f"  collapse: {'YES — BIOGRAPHER PATTERN' if collapse_detected else 'no'}")

        # Monotonic growth without losses (accumulation signal)
        no_loss_runs = 0
        current_run = 0
        for r in records:
            if r.get("n_declared_losses", 0) == 0:
                current_run += 1
                no_loss_runs = max(no_loss_runs, current_run)
            else:
                current_run = 0
        if no_loss_runs >= 5:
            print(f"  WARNING: {no_loss_runs} consecutive cycles without losses")

        print()

    print(f"  Interpretation guide:")
    print(f"  - Unified should be stable (bounded tokens, active curation)")
    print(f"  - Biographer should degrade (growing tokens, sparse losses)")
    print(f"  - Two-phase: if it looks like unified → Approach A works")
    print(f"  -            if it looks like biographer → Approach A is dead")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Gating experiment: two-phase curation vs self-curation vs biographer"
    )
    parser.add_argument(
        "--condition",
        choices=["unified", "two-phase", "biographer", "all"],
        default="all",
        help="Which condition to run (default: all)",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="Model for unified and two-phase conditions (default: sonnet)",
    )
    parser.add_argument(
        "--biographer-model", default="claude-haiku-4-5-20251001",
        help="Biographer model (default: haiku)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=64000,
        help="Max output tokens per call",
    )
    parser.add_argument(
        "--analyze-only", default=None,
        help="Skip running — just analyze an existing output directory",
    )
    args = parser.parse_args()

    if args.analyze_only:
        analyze(Path(args.analyze_only))
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"experiments/gating_{args.model}_{ts}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save experiment config
    config = {
        "timestamp": ts,
        "model": args.model,
        "biographer_model": args.biographer_model,
        "max_tokens": args.max_tokens,
        "condition": args.condition,
        "scenario_turns": len(SCENARIO["turns"]),
    }
    (output_dir / "config.json").write_text(json.dumps(config, indent=2))

    if args.condition in ("unified", "all"):
        run_unified(args.model, output_dir, args.max_tokens)

    if args.condition in ("two-phase", "all"):
        run_two_phase(args.model, output_dir, args.max_tokens)

    if args.condition in ("biographer", "all"):
        run_biographer(
            args.model, args.biographer_model, output_dir, args.max_tokens,
        )

    analyze(output_dir)


if __name__ == "__main__":
    main()
