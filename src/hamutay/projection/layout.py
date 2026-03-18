"""Layout budget calculation and message classification.

Determines how many tokens each region can consume and which messages
belong in which region. The key constraint: Region 3 (ephemeral) gets
whatever is left after Regions 0-2 and the Region 4 margin.

When ephemeral messages exceed their budget, the oldest drop. No
compaction in the physical store — eviction is purely in the projection.
"""

from __future__ import annotations

import json
from typing import Any


# Conservative bytes-to-tokens ratio (Anthropic tokenizer averages ~3.5-4 bytes/token)
_BYTES_PER_TOKEN = 4


def estimate_tokens(obj: Any) -> int:
    """Estimate token count from a JSON-serializable object."""
    raw = json.dumps(obj, default=str)
    return len(raw.encode("utf-8")) // _BYTES_PER_TOKEN


def estimate_message_tokens(msg: dict) -> int:
    """Estimate tokens for a single message."""
    return estimate_tokens(msg)


def compute_ephemeral_budget(
    *,
    window_size: int,
    system_tokens: int,
    tools_tokens: int,
    durable_tokens: int,
    anchor_margin: int = 2000,
    output_margin: int = 8000,
) -> int:
    """Compute the token budget for the ephemeral region (Region 3).

    The ephemeral region gets everything not claimed by other regions,
    minus margins for the anchor (Region 4) and output tokens.

    Args:
        window_size: Total context window in tokens.
        system_tokens: Estimated tokens in Region 1 (system prompt).
        tools_tokens: Estimated tokens in Region 0 (tool definitions).
        durable_tokens: Estimated tokens in Region 2 (frozen tensors + page table).
        anchor_margin: Reserved tokens for Region 4 (dynamic anchor).
        output_margin: Reserved tokens for model output.

    Returns:
        Maximum tokens available for ephemeral messages.
    """
    used = system_tokens + tools_tokens + durable_tokens + anchor_margin + output_margin
    budget = window_size - used
    return max(0, budget)


def trim_ephemeral_to_budget(
    messages: list[dict[str, Any]],
    budget_tokens: int,
) -> list[dict[str, Any]]:
    """Trim ephemeral messages to fit within the token budget.

    Drops oldest messages first (from the front of the list).
    Always preserves at least the last message (the current turn).

    Returns a new list (does not mutate the input).
    """
    if not messages:
        return []

    # Estimate tokens for each message
    msg_tokens = [estimate_message_tokens(m) for m in messages]
    total = sum(msg_tokens)

    if total <= budget_tokens:
        return list(messages)

    # Drop from the front until we fit
    trimmed = list(messages)
    trimmed_tokens = list(msg_tokens)

    while len(trimmed) > 1 and sum(trimmed_tokens) > budget_tokens:
        trimmed.pop(0)
        trimmed_tokens.pop(0)

    return trimmed
