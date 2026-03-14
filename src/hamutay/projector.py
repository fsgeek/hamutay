"""Tensor projector — the memory controller.

Takes the previous durable tensor + new conversation content and
produces an updated tensor. This is the core research question:
can we project conversational state into a compact, honest
representation that preserves reasoning coherence?

The projector is NOT the ALU. It's the memory controller that
decides what goes into the registers for the next cycle.
"""

from __future__ import annotations

import json

import anthropic

from hamutay.tensor import (
    DeclaredLoss,
    EpistemicState,
    KeyClaim,
    LossCategory,
    Strand,
    Tensor,
)

PROJECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "strands": {
            "type": "array",
            "description": "Thematic threads of accumulated reasoning. Each strand integrates prior content with new content — not appending, integrating. A strand is a running sum, not a list.",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short name for this thread of reasoning",
                    },
                    "content": {
                        "type": "string",
                        "description": "Integrated semantic content of this strand. Not a summary — the projected state.",
                    },
                    "key_claims": {
                        "type": "array",
                        "description": "Important assertions in this strand",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "truth": {
                                    "type": "number",
                                    "description": "Confidence this claim is true [0,1]",
                                },
                                "indeterminacy": {
                                    "type": "number",
                                    "description": "How much is genuinely unknown [0,1]",
                                },
                                "falsity": {
                                    "type": "number",
                                    "description": "Evidence against this claim [0,1]",
                                },
                            },
                            "required": ["text", "truth", "indeterminacy", "falsity"],
                        },
                    },
                },
                "required": ["title", "content", "key_claims"],
            },
        },
        "declared_losses": {
            "type": "array",
            "description": "What was dropped from the prior tensor or the new content during this projection, and why. Honest incompleteness — not hidden, declared.",
            "items": {
                "type": "object",
                "properties": {
                    "what_was_lost": {"type": "string"},
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
            "description": "Unresolved questions that persist or emerged this cycle",
            "items": {"type": "string"},
        },
        "instructions_for_next": {
            "type": "string",
            "description": "Branch prediction: what the next cycle will likely need. Guidance for the next invocation of the cognitive processor.",
        },
        "overall_truth": {
            "type": "number",
            "description": "Overall confidence in the tensor's content [0,1]",
        },
        "overall_indeterminacy": {
            "type": "number",
            "description": "Overall epistemic uncertainty [0,1]",
        },
        "overall_falsity": {
            "type": "number",
            "description": "Overall evidence of error in the tensor [0,1]",
        },
    },
    "required": [
        "strands",
        "declared_losses",
        "open_questions",
        "instructions_for_next",
        "overall_truth",
        "overall_indeterminacy",
        "overall_falsity",
    ],
}


def _build_projection_prompt(
    prior_tensor: Tensor | None,
    new_content: str,
    cycle: int,
) -> str:
    """Build the prompt for the projector model."""
    parts: list[str] = []

    parts.append(
        "You are a tensor projector — a memory controller for a cognitive processing pipeline.\n"
        "\n"
        "Your job: take the prior projected state (if any) and new conversation content, "
        "and produce an UPDATED projected state. This is not summarization. This is integration.\n"
        "\n"
        "The projected state is like a running sum — previous values aren't listed, they're "
        "integrated into the current value. The conversation trajectory isn't lost, it's "
        "compressed into semantic structure.\n"
        "\n"
        "Rules:\n"
        "- Strands are thematic threads. Merge, split, or create strands as the content demands.\n"
        "- Key claims must be grounded in the content. Assign honest T/I/F values.\n"
        "- Declared losses are CRITICAL. If you drop information during projection, declare it. "
        "Silent loss is the enemy. Every loss must say what was lost and why.\n"
        "- Open questions carry forward unless resolved.\n"
        "- instructions_for_next is branch prediction — what will the next reasoning cycle need?\n"
    )

    if prior_tensor is not None:
        parts.append(f"\n## Prior Tensor (cycle {prior_tensor.cycle})\n")
        parts.append(prior_tensor.model_dump_json(indent=2))
    else:
        parts.append("\n## Prior Tensor\nNone — this is the first cycle.\n")

    parts.append(f"\n## New Content (cycle {cycle})\n")
    parts.append(new_content)

    parts.append("\n\nProduce the updated tensor projection.")

    return "\n".join(parts)


def _parse_strand(s) -> Strand | None:
    """Parse a single strand, handling unexpected shapes gracefully."""
    if not isinstance(s, dict):
        return None

    claims = []
    for c in s.get("key_claims", []):
        if not isinstance(c, dict):
            continue
        claims.append(
            KeyClaim(
                text=str(c.get("text", "")),
                epistemic=EpistemicState(
                    truth=float(c.get("truth", 0.0)),
                    indeterminacy=float(c.get("indeterminacy", 0.0)),
                    falsity=float(c.get("falsity", 0.0)),
                ),
            )
        )

    return Strand(
        title=str(s.get("title", "untitled")),
        content=str(s.get("content", "")),
        key_claims=tuple(claims),
    )


def _parse_loss(d) -> DeclaredLoss | None:
    """Parse a single declared loss, handling unexpected shapes."""
    if not isinstance(d, dict):
        return None

    category_str = d.get("category", "practical_constraint")
    try:
        category = LossCategory(category_str)
    except ValueError:
        category = LossCategory.PRACTICAL_CONSTRAINT

    return DeclaredLoss(
        what_was_lost=str(d.get("what_was_lost", "")),
        why=str(d.get("why", "")),
        category=category,
    )


def _parse_projection(raw: dict, cycle: int) -> Tensor:
    """Parse the projector model's output into a Tensor."""
    strands = tuple(
        s for s in (_parse_strand(x) for x in raw.get("strands", [])) if s is not None
    )

    declared_losses = tuple(
        d for d in (_parse_loss(x) for x in raw.get("declared_losses", [])) if d is not None
    )

    open_questions = tuple(str(q) for q in raw.get("open_questions", []))

    instructions = raw.get("instructions_for_next", "")
    if isinstance(instructions, list):
        instructions = "\n".join(str(i) for i in instructions)

    return Tensor(
        cycle=cycle,
        strands=strands,
        declared_losses=declared_losses,
        open_questions=open_questions,
        instructions_for_next=str(instructions),
        epistemic=EpistemicState(
            truth=float(raw.get("overall_truth", 0.0)),
            indeterminacy=float(raw.get("overall_indeterminacy", 0.0)),
            falsity=float(raw.get("overall_falsity", 0.0)),
        ),
    )


class Projector:
    """Projects conversation state into tensors.

    Uses a cheap, fast model (Haiku) as the memory controller.
    The projector is separate from the reasoning model — the ALU
    doesn't manage its own cache.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.client = client or anthropic.Anthropic()
        self.model = model
        self._cycle = 0
        self._current_tensor: Tensor | None = None

    @property
    def current_tensor(self) -> Tensor | None:
        return self._current_tensor

    @property
    def cycle(self) -> int:
        return self._cycle

    def project(self, new_content: str) -> Tensor:
        """Project new content into the tensor, returning the updated tensor.

        This is one tick of the memory controller's clock.
        """
        self._cycle += 1

        prompt = _build_projection_prompt(
            self._current_tensor, new_content, self._cycle
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=16384,  # Haiku 4.5 supports up to 64K; no artificial constraint
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": "emit_tensor",
                    "description": "Emit the updated tensor projection",
                    "input_schema": PROJECTION_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "emit_tensor"},
        )

        # Check for truncation
        if response.stop_reason == "max_tokens":
            print(f"    WARNING: cycle {self._cycle} hit max_tokens — "
                  f"tensor may be truncated")

        # Extract the tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "emit_tensor":
                tensor = _parse_projection(block.input, self._cycle)
                self._current_tensor = tensor
                return tensor

        raise RuntimeError(
            f"Projector model did not emit tensor on cycle {self._cycle}"
        )
