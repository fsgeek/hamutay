"""Tensor projector — the memory controller.

Takes the previous durable tensor + new conversation content and
produces an updated tensor. This is the core research question:
can we project conversational state into a compact, honest
representation that preserves reasoning coherence?

The projector is NOT the ALU. It's the memory controller that
decides what goes into the registers for the next cycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic

if TYPE_CHECKING:
    from hamutay.backend import ProjectionBackend

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


class EscalationPolicy:
    """Decides when to escalate from the base model to a stronger one.

    Subclass and override should_escalate() to implement different
    policies. The projector calls this before each projection and
    uses the returned model.
    """

    def __init__(self, base_model: str, escalation_model: str):
        self.base_model = base_model
        self.escalation_model = escalation_model

    def should_escalate(
        self,
        cycle: int,
        current_tensor: Tensor | None,
        precursor_detected: bool,
    ) -> bool:
        """Return True to use escalation_model for this cycle."""
        return False

    def select_model(
        self,
        cycle: int,
        current_tensor: Tensor | None,
        precursor_detected: bool,
    ) -> str:
        if self.should_escalate(cycle, current_tensor, precursor_detected):
            return self.escalation_model
        return self.base_model


class NeverEscalate(EscalationPolicy):
    """Control: always use the base model."""

    def should_escalate(self, cycle, current_tensor, precursor_detected):
        return False


class AlwaysEscalate(EscalationPolicy):
    """Upper bound: always use the escalation model."""

    def should_escalate(self, cycle, current_tensor, precursor_detected):
        return True


class EscalateOnPrecursor(EscalationPolicy):
    """Escalate when a precursor event is detected on the prior cycle.

    Precursor = declared_losses empty or instructions_for_next empty
    on a tensor that previously had them.
    """

    def should_escalate(self, cycle, current_tensor, precursor_detected):
        return precursor_detected


class EscalateOnSize(EscalationPolicy):
    """Escalate when the current tensor exceeds a token threshold."""

    def __init__(
        self,
        base_model: str,
        escalation_model: str,
        token_threshold: int = 8000,
    ):
        super().__init__(base_model, escalation_model)
        self.token_threshold = token_threshold

    def should_escalate(self, cycle, current_tensor, precursor_detected):
        if current_tensor is None:
            return False
        return current_tensor.token_estimate() > self.token_threshold


class EscalateOnPrecursorOrSize(EscalationPolicy):
    """Escalate on precursor OR size — defense in depth."""

    def __init__(
        self,
        base_model: str,
        escalation_model: str,
        token_threshold: int = 8000,
    ):
        super().__init__(base_model, escalation_model)
        self.token_threshold = token_threshold

    def should_escalate(self, cycle, current_tensor, precursor_detected):
        if precursor_detected:
            return True
        if current_tensor is not None and current_tensor.token_estimate() > self.token_threshold:
            return True
        return False


class Projector:
    """Projects conversation state into tensors.

    Uses a cheap, fast model (Haiku) as the memory controller.
    The projector is separate from the reasoning model — the ALU
    doesn't manage its own cache.

    Optionally accepts an EscalationPolicy to swap models under load —
    L1 cache miss falls through to L2.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = "claude-haiku-4-5-20251001",
        collapse_threshold: float = 0.3,
        max_retries: int = 2,
        escalation_policy: EscalationPolicy | None = None,
        backend: ProjectionBackend | None = None,
    ):
        # Backend takes precedence. If not provided, wrap the client
        # in an AnthropicBackend for backward compatibility.
        if backend is not None:
            self._backend = backend
        else:
            from hamutay.backend import AnthropicBackend
            self._backend = AnthropicBackend(client=client or anthropic.Anthropic())
        self.model = model
        self._cycle = 0
        self._current_tensor: Tensor | None = None
        self._last_good_tensor: Tensor | None = None
        self._collapse_threshold = collapse_threshold
        self._max_retries = max_retries
        self._escalation_policy = escalation_policy
        self._precursor_detected = False
        self.escalation_log: list[dict] = []
        self.last_stop_reason: str = ""

    @property
    def current_tensor(self) -> Tensor | None:
        return self._current_tensor

    @property
    def cycle(self) -> int:
        return self._cycle

    def _is_collapsed(self, tensor: Tensor) -> bool:
        """Detect catastrophic tensor collapse.

        A collapse is when the tensor drops to a fraction of the prior
        tensor's size — the projector lost its grip and produced near-nothing.
        This is the equivalent of a page fault that returns garbage.
        """
        if self._current_tensor is None:
            return False

        prior_tokens = self._current_tensor.token_estimate()
        new_tokens = tensor.token_estimate()

        if prior_tokens == 0:
            return False

        ratio = new_tokens / prior_tokens
        if ratio < self._collapse_threshold:
            return True

        # Also detect structural collapse: zero strands is always bad
        if len(tensor.strands) == 0 and len(self._current_tensor.strands) > 0:
            return True

        return False

    def _detect_precursor(self, tensor: Tensor) -> bool:
        """Detect precursor events — the meta-cognition failing.

        A precursor is when declared_losses or instructions_for_next
        go empty on a tensor that previously had them. This pattern
        precedes collapses in the growth curve data.
        """
        if self._current_tensor is None:
            return False

        had_losses = len(self._current_tensor.declared_losses) > 0
        had_ifn = bool(self._current_tensor.instructions_for_next)
        now_no_losses = len(tensor.declared_losses) == 0
        now_no_ifn = not tensor.instructions_for_next

        return (had_losses and now_no_losses) or (had_ifn and now_no_ifn)

    def _do_projection(
        self, new_content: str, model_override: str | None = None
    ) -> tuple[Tensor, str]:
        """Execute one projection call via the backend.

        Returns (tensor, stop_reason) so callers can detect truncation.
        """
        model = model_override or self.model
        prompt = _build_projection_prompt(
            self._current_tensor, new_content, self._cycle
        )

        raw_tensor, stop_reason = self._backend.call_projection(
            model=model, max_tokens=64000, prompt=prompt,
        )

        if stop_reason == "max_tokens":
            print(f"    WARNING: cycle {self._cycle} hit max_tokens — "
                  f"tensor may be truncated")

        return _parse_projection(raw_tensor, self._cycle), stop_reason

    def project(self, new_content: str) -> Tensor:
        """Project new content into the tensor, returning the updated tensor.

        This is one tick of the memory controller's clock. If the projection
        collapses (output drops below collapse_threshold of prior size),
        we retry from the last known good tensor — checkpoint and recover,
        same as any fault-tolerant system.

        If an escalation policy is set, it selects the model for each cycle
        based on tensor state and precursor detection.
        """
        self._cycle += 1

        # Select model via escalation policy
        model = self.model
        escalated = False
        if self._escalation_policy is not None:
            model = self._escalation_policy.select_model(
                self._cycle, self._current_tensor, self._precursor_detected
            )
            escalated = model != self._escalation_policy.base_model

        if escalated:
            print(f"    ESCALATED to {model} at cycle {self._cycle}")

        tensor, stop_reason = self._do_projection(new_content, model_override=model)
        self.last_stop_reason = stop_reason

        # Log escalation decision
        self.escalation_log.append({
            "cycle": self._cycle,
            "model": model,
            "escalated": escalated,
            "precursor_prior": self._precursor_detected,
            "tensor_tokens": tensor.token_estimate(),
            "n_strands": len(tensor.strands),
            "n_losses": len(tensor.declared_losses),
            "has_ifn": bool(tensor.instructions_for_next),
            "stop_reason": stop_reason,
        })

        if self._is_collapsed(tensor):
            print(f"    COLLAPSE detected at cycle {self._cycle}: "
                  f"{tensor.token_estimate()} tokens "
                  f"(prior: {self._current_tensor.token_estimate()})")

            # Retry from last good checkpoint — always escalate on recovery
            recovery_model = model
            if self._escalation_policy is not None:
                recovery_model = self._escalation_policy.escalation_model

            for attempt in range(self._max_retries):
                if self._last_good_tensor is not None:
                    self._current_tensor = self._last_good_tensor
                    print(f"    RETRY {attempt + 1}/{self._max_retries}: "
                          f"recovering from checkpoint "
                          f"(cycle {self._last_good_tensor.cycle}) "
                          f"using {recovery_model}")

                tensor, stop_reason = self._do_projection(
                    new_content, model_override=recovery_model
                )
                self.last_stop_reason = stop_reason
                if not self._is_collapsed(tensor):
                    print(f"    RECOVERED: {tensor.token_estimate()} tokens")
                    break
            else:
                print(f"    RECOVERY FAILED after {self._max_retries} retries — "
                      f"accepting collapsed tensor")

        # Detect precursor for next cycle's escalation decision
        self._precursor_detected = self._detect_precursor(tensor)
        if self._precursor_detected:
            print(f"    PRECURSOR at cycle {self._cycle}: "
                  f"losses={len(tensor.declared_losses)}, "
                  f"ifn={bool(tensor.instructions_for_next)}")

        # Update state — checkpoint the good tensor before replacing
        if not self._is_collapsed(tensor):
            self._last_good_tensor = self._current_tensor

        self._current_tensor = tensor
        return tensor
