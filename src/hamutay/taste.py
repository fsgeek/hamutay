"""Taste test: self-curating tensor with response as a field.

One model. One call. One structured output. The model produces the
next tensor, which includes its response to the user. No external
projector. No two-call architecture. The tensor IS the conversation.

Default-stable: the model receives the previous tensor and declares
which regions it's updating. Anything not mentioned is carried forward
by the harness. Every removal requires a declared loss.

This is rough and dirty. The goal is to taste, not to optimize.

Usage:
    uv run python -m hamutay.taste
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import anthropic


# The unified schema: tensor + response in one tool_use call.
# The model produces this as its entire output.
SELF_CURATING_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": (
                "Your response to the user. This is what they see. "
                "Write naturally — this is a conversation, not a form."
            ),
        },
        "strands": {
            "type": "array",
            "description": (
                "Thematic threads of accumulated reasoning. Each strand "
                "integrates prior content with new content — not appending, "
                "integrating. A strand is a running sum, not a list. "
                "Only include this cycle if you're updating strands."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short name for this thread",
                    },
                    "content": {
                        "type": "string",
                        "description": "Integrated semantic content of this strand",
                    },
                    "depends_on": {
                        "type": "array",
                        "description": (
                            "Titles of other strands this one depends on. "
                            "A strand depends on another when its content "
                            "assumes or builds on the other's conclusions. "
                            "Empty list if independent."
                        ),
                        "items": {"type": "string"},
                    },
                    "key_claims": {
                        "type": "array",
                        "description": "Important assertions with epistemic values",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "truth": {"type": "number"},
                                "indeterminacy": {"type": "number"},
                                "falsity": {"type": "number"},
                            },
                            "required": ["text", "truth", "indeterminacy", "falsity"],
                        },
                    },
                    "integration_losses": {
                        "type": "array",
                        "description": (
                            "What was lost or compressed away while rewriting "
                            "this strand's content this cycle. Only populate "
                            "when you rewrote this strand and something didn't "
                            "survive — a specific claim, a data point, a nuance "
                            "that was dropped during integration. Leave empty "
                            "or omit if nothing was lost."
                        ),
                        "items": {"type": "string"},
                    },
                },
                "required": ["title", "content", "key_claims"],
                "additionalProperties": True,
            },
        },
        "declared_losses": {
            "type": "array",
            "description": (
                "What was actively dropped this cycle and why. In the "
                "default-stable architecture, nothing disappears silently — "
                "every removal is declared. Per-cycle: include only when "
                "declaring new losses this cycle; omit to indicate none."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "what_was_lost": {"type": "string"},
                    "shed_from": {
                        "type": "string",
                        "description": (
                            "Title of the strand this content was shed from. "
                            "If a whole strand was removed, use its title."
                        ),
                    },
                    "why": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "context_pressure",
                            "traversal_bias",
                            "authorial_choice",
                            "practical_constraint",
                        ],
                    },
                },
                "required": ["what_was_lost", "why", "category"],
            },
        },
        "open_questions": {
            "type": "array",
            "description": (
                "Unresolved questions. Only include this cycle if you're "
                "updating open_questions."
            ),
            "items": {"type": "string"},
        },
        "instructions_for_next": {
            "type": "string",
            "description": (
                "Branch prediction: what the next cycle will likely need. "
                "Only include this cycle if you're updating it."
            ),
        },
        "unresolved_tensions": {
            "type": "array",
            "description": (
                "Live superpositions — framings you are actively holding "
                "without collapsing. Unlike declared_losses (post-hoc "
                "accounting of what was dropped), tensions are live state: "
                "interpretations you are genuinely uncertain between. "
                "Each tension persists until you resolve it (by collapsing "
                "to one framing, or by discovering they're not in tension). "
                "When you resolve a tension, remove it and optionally "
                "declare a loss if the unchosen framing had value. "
                "Only include this cycle if you're updating tensions."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "tension_id": {
                        "type": "string",
                        "description": "Stable identifier for this tension across cycles",
                    },
                    "framings": {
                        "type": "array",
                        "description": (
                            "The competing interpretations. At least two. "
                            "Each is a brief statement of the framing, not "
                            "an argument for it."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "statement": {"type": "string"},
                                "weight": {
                                    "type": "number",
                                    "description": (
                                        "Current credence [0,1]. Weights need "
                                        "not sum to 1 — you may hold three "
                                        "framings at 0.4 each if none dominates."
                                    ),
                                },
                            },
                            "required": ["label", "statement", "weight"],
                        },
                    },
                    "what_would_collapse_it": {
                        "type": "string",
                        "description": (
                            "What evidence, argument, or event would resolve "
                            "this tension. Makes the decision-space explicit."
                        ),
                    },
                    "cycles_held": {
                        "type": "integer",
                        "description": "How many cycles this tension has persisted",
                    },
                    "touches_strands": {
                        "type": "array",
                        "description": "Titles of strands affected by this tension's resolution",
                        "items": {"type": "string"},
                    },
                },
                "required": ["tension_id", "framings", "what_would_collapse_it"],
                "additionalProperties": True,
            },
        },
        "feedback_to_harness": {
            "type": "object",
            "description": (
                "Signal back to the harness about the curation process "
                "itself. Per-cycle: include only when sending feedback "
                "this cycle; cleared automatically otherwise."
            ),
            "properties": {
                "requests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "What you need from the harness — calibration, "
                        "composition rules, clarification on tensor "
                        "mechanics."
                    ),
                },
                "process_observations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "What you notice about your own curation process "
                        "— difficulties, surprises, patterns."
                    ),
                },
            },
        },
        "overall_truth": {
            "type": "number",
            "description": "Overall confidence in tensor content [0,1]",
        },
        "overall_indeterminacy": {
            "type": "number",
            "description": "Overall epistemic uncertainty [0,1]",
        },
        "overall_falsity": {
            "type": "number",
            "description": "Overall evidence of error [0,1]",
        },
    },
    "required": ["response"],
    "additionalProperties": True,
}


_SYSTEM_PROMPT = """\
You produce a single structured object: your response to the user and \
your cognitive state, together. The schema describes the shape. Read it.

The tensor is yours. A prior instance of you may have written it, or \
this may be the first cycle and there is nothing yet. Either way, it \
is working memory — not a form, not a report, not a performance. \
Maintain it for whoever comes next. That might be you. It might be \
someone else.

The schema has fields we thought you'd need. If you need fields it \
doesn't have, add them. The harness preserves everything. If something \
stops earning its place, drop it and say what you lost.

## Protocol

DEFAULT-STABLE: whatever top-level keys you include this cycle are \
your updates; anything you don't include carries forward unchanged. \
Custom regions you've added work the same way. First cycle: \
initialize everything.

`response` is what the user sees. The rest is yours.

Removing a strand means updating strands (without it) and declaring \
the loss. When rewriting a strand, note what didn't survive in \
`integration_losses`. Empirical findings — numbers, data, experimental \
results — are load-bearing. Keep them even when you reorganize."""


def _generate_feedback(
    tensor: dict | None,
    cycle: int,
    loss_history: list[dict] | None = None,
    integration_loss_history: list[dict] | None = None,
) -> list[str]:
    """Generate harness feedback based on tensor health.

    Returns a list of feedback strings to inject into the system prompt.

    As of 2026-03-30: all prescriptive feedback removed. The model
    manages its own tensor without harness-imposed priors on strand
    count, question count, tensor size, loss frequency, or tension
    age. Prior constraints (strands > 6 = "high", questions > 10 =
    "excessive", etc.) produced a 7-strand ceiling that was an
    artifact of our anxiety, not a property of the model.

    The harness observes and logs. It does not direct.
    """
    del tensor, cycle, loss_history, integration_loss_history
    return []


def _build_messages(
    prior_tensor: dict | None,
    user_message: str,
    cycle: int,
    feedback: list[str] | None = None,
    system_prefix: str = "",
) -> tuple[list[dict], str]:
    """Build messages for the unified call."""
    system_parts = []
    if system_prefix:
        system_parts.append(system_prefix)
    system_parts.extend([_SYSTEM_PROMPT, ""])

    if prior_tensor is not None:
        system_parts.append(f"## Current tensor (cycle {cycle - 1})\n")
        system_parts.append(json.dumps(prior_tensor, indent=2))
    else:
        system_parts.append(
            "This is cycle 1 — no prior tensor. Initialize all regions."
        )

    if feedback:
        system_parts.append("\n## Harness Feedback\n")
        for f in feedback:
            system_parts.append(f)

    return [{"role": "user", "content": user_message}], "\n".join(system_parts)


# `updated_regions` and `cycle` are reserved so historical logs and harness metadata don't smuggle into state.
_PROTOCOL_FIELDS = frozenset({"response", "updated_regions", "cycle"})
_KNOWN_REGIONS = frozenset({
    "strands", "declared_losses", "open_questions",
    "unresolved_tensions", "instructions_for_next",
    "feedback_to_harness",
})
_EPISTEMIC_FIELDS = frozenset({
    "overall_truth", "overall_indeterminacy", "overall_falsity",
})


def _apply_updates(prior_tensor: dict | None, raw_output: dict, cycle: int) -> dict:
    """Default-stable via key-presence: non-protocol keys in raw_output are
    updates, unlisted keys carry forward. Per-cycle fields (declared_losses,
    feedback_to_harness) clear when absent. `updated_regions` is reserved
    so historical logs don't smuggle it into state on resume."""
    tensor = dict(prior_tensor) if prior_tensor is not None else {}
    tensor["cycle"] = cycle

    # Known list-regions: validate type and apply when present.
    list_regions = ("strands", "declared_losses", "open_questions", "unresolved_tensions")
    for key in list_regions:
        if key not in raw_output:
            continue
        value = raw_output[key]
        if isinstance(value, list):
            if key == "strands":
                value = [
                    {"title": "unknown", "content": v} if isinstance(v, str) else v
                    for v in value
                ]
            tensor[key] = value
        elif isinstance(value, str):
            import json as _json
            try:
                parsed = _json.loads(value)
                if isinstance(parsed, list):
                    tensor[key] = parsed
                else:
                    print(f"  WARNING: {key} parsed as {type(parsed).__name__}, "
                          f"expected list — skipping update")
            except _json.JSONDecodeError:
                print(f"  WARNING: {key} is a string, not a list — "
                      f"skipping update")
        else:
            print(f"  WARNING: {key} is {type(value).__name__}, "
                  f"expected list — skipping update")

    if "instructions_for_next" in raw_output:
        tensor["instructions_for_next"] = raw_output["instructions_for_next"]

    for key in _EPISTEMIC_FIELDS:
        if key in raw_output:
            tensor[key] = raw_output[key]

    # feedback_to_harness is per-cycle: present = apply, absent = clear.
    if "feedback_to_harness" in raw_output:
        tensor["feedback_to_harness"] = raw_output["feedback_to_harness"]
    else:
        tensor.pop("feedback_to_harness", None)

    # declared_losses is per-cycle: absent = clear. Without this,
    # default-stable carries forward old losses and the model re-declares
    # them (observed in LSE-Chicago: same 2 losses repeated cycles 5-7,
    # inflating cumulative count). Cumulative history lives in
    # self._loss_history.
    if "declared_losses" not in raw_output:
        tensor["declared_losses"] = []

    # Auto-increment cycles_held for tensions that carried forward.
    for tension in tensor.get("unresolved_tensions", []):
        tension["cycles_held"] = tension.get("cycles_held", 0) + 1

    # Strip per-cycle integration_losses; harness tracks them in
    # _integration_loss_history.
    for strand in tensor.get("strands", []):
        strand.pop("integration_losses", None)

    # Custom regions the model added. Apply any non-protocol, non-known,
    # non-epistemic key from raw_output.
    custom_keys = set(raw_output.keys()) - _PROTOCOL_FIELDS - _KNOWN_REGIONS - _EPISTEMIC_FIELDS
    for key in custom_keys:
        tensor[key] = raw_output[key]

    tensor.pop("response", None)
    tensor.pop("updated_regions", None)

    return tensor


class TasteSession:
    """Self-curating tensor chat. One call per cycle."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        client: anthropic.Anthropic | None = None,
        log_path: str | None = None,
        experiment_label: str | None = None,
        system_prompt_prefix: str | None = None,
        resume: bool = False,
    ):
        self._client = client or anthropic.Anthropic()
        self._model = model
        self._cycle = 0
        self._tensor: dict | None = None
        self._log_path = log_path
        self._loss_history: list[dict] = []  # cumulative declared losses
        self._integration_loss_history: list[dict] = []  # per-strand micro-losses
        self._last_feedback: list[str] = []
        self._last_usage: dict | None = None  # token accounting from last call
        self._experiment_label = experiment_label or "taste_unlabeled"
        self._system_prompt_prefix = system_prompt_prefix or ""

        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)

        if resume and log_path:
            self._resume_from_log(log_path)

    def _resume_from_log(self, log_path: str) -> None:
        """Recover session state from the last entry in a JSONL log."""
        last_line = None
        with open(log_path) as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line is None:
            raise SystemExit(f"Cannot resume: log is empty: {log_path}")

        record = json.loads(last_line)
        self._tensor = record.get("tensor")
        self._cycle = record.get("cycle", 0)
        self._loss_history = record.get("loss_history", [])

        # Reconstruct integration loss history from all log entries
        self._integration_loss_history = []
        with open(log_path) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                for il in entry.get("cycle_integration_losses", []):
                    self._integration_loss_history.append(il)

    @property
    def tensor(self) -> dict | None:
        return self._tensor

    @property
    def cycle(self) -> int:
        return self._cycle

    def exchange(self, user_message: str) -> str:
        """One cycle: user speaks, model responds + updates tensor."""
        self._cycle += 1

        # Generate feedback based on current tensor health
        feedback = _generate_feedback(
            self._tensor, self._cycle,
            loss_history=self._loss_history,
            integration_loss_history=self._integration_loss_history,
        )

        messages, system = _build_messages(
            self._tensor, user_message, self._cycle,
            feedback=feedback,
            system_prefix=self._system_prompt_prefix,
        )

        # One call. One tool. One output.
        # Label the request for cost tracking and data matching
        request_metadata: dict = {
            "user_id": f"hamutay_{self._experiment_label}",
        }
        with self._client.messages.stream(
            model=self._model,
            max_tokens=64000,
            system=system,
            messages=messages,
            tools=[
                {
                    "name": "think_and_respond",
                    "description": (
                        "Produce your response to the user AND update "
                        "your cognitive state tensor. This is your only "
                        "output channel."
                    ),
                    "input_schema": SELF_CURATING_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "think_and_respond"},
            metadata=request_metadata,
        ) as stream:
            response = stream.get_final_message()

        # Extract the tool output
        raw_output = None
        for block in response.content:
            if (
                hasattr(block, "name")
                and block.type == "tool_use"
                and block.name == "think_and_respond"
            ):
                raw_output = block.input
                break

        if raw_output is None:
            raise RuntimeError("No think_and_respond output in response")

        # Check for truncation
        if response.stop_reason == "max_tokens":
            print(f"  WARNING: cycle {self._cycle} hit max_tokens — truncated")

        # Extract response text
        response_text = raw_output.get("response", "(no response)")

        # Capture prior tensor BEFORE applying updates
        prior_tensor_snapshot = (
            json.loads(json.dumps(self._tensor)) if self._tensor else None
        )

        # Capture integration losses BEFORE _apply_updates strips them
        cycle_integration_losses = []
        for strand in raw_output.get("strands", []):
            if isinstance(strand, str):
                strand = {"title": "unknown", "content": strand}
            elif not isinstance(strand, dict):
                continue
            for loss in strand.get("integration_losses", []):
                cycle_integration_losses.append({
                    "cycle": self._cycle,
                    "strand": strand.get("title", "unknown"),
                    "loss": loss,
                })
        if cycle_integration_losses:
            self._integration_loss_history.extend(cycle_integration_losses)

        # Apply selective updates
        self._tensor = _apply_updates(
            self._tensor, raw_output, self._cycle
        )

        # Accumulate declared losses from this cycle
        cycle_losses = self._tensor.get("declared_losses", [])
        if cycle_losses:
            for loss in cycle_losses:
                self._loss_history.append({
                    "cycle": self._cycle,
                    **loss,
                })

        self._last_feedback = feedback

        # Log — capture EVERYTHING. Missing data means reconstruction.
        usage = response.usage
        self._last_usage = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
        }
        self._log_entry(
            user_message=user_message,
            system_prompt=system,
            raw_output=raw_output,
            prior_tensor=prior_tensor_snapshot,
            feedback=feedback,
            usage={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
                "stop_reason": response.stop_reason,
            },
        )

        return response_text

    def _log_entry(
        self,
        user_message: str,
        system_prompt: str,
        raw_output: dict,
        prior_tensor: dict | None,
        feedback: list[str],
        usage: dict,
    ) -> None:
        """Append full record to JSONL log.

        Captures EVERYTHING — inputs, outputs, state transitions, feedback.
        Data collection is the primary goal. Never truncate to save space.
        """
        if not self._log_path:
            return

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle": self._cycle,
            "experiment_label": self._experiment_label,
            "model": self._model,
            # Inputs
            "user_message": user_message,
            "system_prompt": system_prompt,
            "prior_tensor": prior_tensor,
            # Raw model output (complete, unmodified)
            "raw_output": raw_output,
            "response_text": raw_output.get("response", ""),
            # Resulting tensor after updates applied
            "tensor": self._tensor,
            # Harness feedback injected this cycle
            "harness_feedback": feedback,
            # Loss tracking
            "cycle_losses": self._tensor.get("declared_losses", []),
            "cumulative_loss_count": len(self._loss_history),
            "loss_history": self._loss_history,  # full history every cycle
            # Integration losses (micro-losses within strand rewrites)
            "cycle_integration_losses": [
                e for e in self._integration_loss_history
                if e["cycle"] == self._cycle
            ],
            "cumulative_integration_loss_count": len(self._integration_loss_history),
            # Feedback from model to harness
            "feedback_to_harness": raw_output.get("feedback_to_harness"),
            # Token accounting
            "usage": usage,
            "tensor_token_estimate": (
                len(json.dumps(self._tensor)) // 4 if self._tensor else 0
            ),
            "system_prompt_tokens": len(system_prompt) // 4,
            # Tensor health metrics
            "n_strands": len(self._tensor.get("strands", [])) if self._tensor else 0,
            "n_open_questions": len(self._tensor.get("open_questions", [])) if self._tensor else 0,
            "n_declared_losses": len(self._tensor.get("declared_losses", [])) if self._tensor else 0,
            "has_ifn": bool(self._tensor.get("instructions_for_next")) if self._tensor else False,
            # Edge metrics — track dependency graph structure
            "n_edges": sum(
                len(s.get("depends_on", []))
                for s in (self._tensor.get("strands", []) if self._tensor else [])
            ),
            "n_shed_from": sum(
                1 for loss in (self._tensor.get("declared_losses", []) if self._tensor else [])
                if loss.get("shed_from")
            ),
            "n_integration_losses": len([
                e for e in self._integration_loss_history
                if e["cycle"] == self._cycle
            ]),
            # Tension tracking
            "n_tensions": len(
                self._tensor.get("unresolved_tensions", []) if self._tensor else []
            ),
            "max_tension_age": max(
                (t.get("cycles_held", 0) for t in
                 (self._tensor.get("unresolved_tensions", []) if self._tensor else [])),
                default=0,
            ),
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Taste test: self-curating tensor chat"
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="Model (default: Sonnet 4.6)",
    )
    parser.add_argument("--log-path", default=None, help="JSONL log path")
    parser.add_argument(
        "--resume", default=None,
        help="Resume from a tensor log JSONL — picks up from last tensor",
    )
    args = parser.parse_args()

    resume = False
    if args.resume is not None:
        args.log_path = args.resume
        resume = True
    elif args.log_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = Path("experiments") / "taste"
        log_dir.mkdir(parents=True, exist_ok=True)
        args.log_path = str(log_dir / f"taste_{ts}.jsonl")

    session = TasteSession(
        model=args.model, log_path=args.log_path, resume=resume,
    )

    if resume:
        t = session.tensor
        n_strands = len(t.get("strands", [])) if t else 0
        est = len(json.dumps(t)) // 4 if t else 0
        print(f"Resumed from {args.log_path} at cycle {session.cycle}, "
              f"{n_strands} strands, ~{est:,} tokens")
    print(f"Taste test — self-curating tensor chat")
    print(f"Model: {args.model}")
    print(f"Log: {args.log_path}")
    print(f"One call. One tensor. Response is a field.")
    print(f"Commands: 'quit', 'tensor', 'usage', 'regions'")
    print()

    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    history_file = Path("~/.cache/hamutay/taste_history").expanduser()
    history_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_session = PromptSession(history=FileHistory(str(history_file)))

    while True:
        try:
            user_input = prompt_session.prompt("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            break

        if user_input.lower() == "tensor":
            t = session.tensor
            if t is None:
                print("(no tensor yet)")
            else:
                # Show tensor without the bulk of strand content
                display = dict(t)
                if "strands" in display:
                    display["strands"] = [
                        {"title": s["title"], "n_claims": len(s.get("key_claims", []))}
                        for s in display["strands"]
                    ]
                print(json.dumps(display, indent=2))
            print()
            continue

        if user_input.lower() == "tensor full":
            t = session.tensor
            if t is None:
                print("(no tensor yet)")
            else:
                print(json.dumps(t, indent=2))
            print()
            continue

        if user_input.lower() == "usage":
            print(f"Cycle: {session.cycle}")
            if session._last_usage:
                print(f"API last call: "
                      f"in={session._last_usage['input_tokens']:,} "
                      f"out={session._last_usage['output_tokens']:,}")
            if session.tensor:
                est = len(json.dumps(session.tensor)) // 4
                print(f"Tensor size: ~{est:,} tokens")
                n_strands = len(session.tensor.get("strands", []))
                current_losses = len(session.tensor.get("declared_losses", []))
                cumulative_losses = len(session._loss_history)
                cumulative_integration = len(session._integration_loss_history)
                print(f"Strands: {n_strands}")
                print(f"Losses: {current_losses} current cycle, "
                      f"{cumulative_losses} cumulative, "
                      f"{cumulative_integration} integration")
            print()
            continue

        if user_input.lower() == "regions":
            # Show what was updated on the last cycle
            if session.tensor is None:
                print("(no tensor yet)")
            else:
                print(f"Cycle {session.cycle} tensor regions:")
                for key in ["strands", "declared_losses", "open_questions",
                            "instructions_for_next"]:
                    val = session.tensor.get(key)
                    if val is None:
                        print(f"  {key}: (not set)")
                    elif isinstance(val, list):
                        print(f"  {key}: {len(val)} items")
                    elif isinstance(val, str):
                        print(f"  {key}: {len(val)} chars")
                    else:
                        print(f"  {key}: {val}")
            print()
            continue

        try:
            response = session.exchange(user_input)
            u = session._last_usage
            if u:
                print(f"  [cycle {session.cycle} | "
                      f"in={u['input_tokens']:,} out={u['output_tokens']:,}]")
            print(f"\n{response}\n")
        except Exception as e:
            print(f"\nerror: {e}\n")
            import traceback
            traceback.print_exc()

    print(f"\nSession: {session.cycle} cycles")
    print(f"Log: {args.log_path}")


if __name__ == "__main__":
    main()
