"""Cache breakpoint placement and waste tracking.

The Anthropic API allows up to 4 cache_control markers. The projection
places them at region boundaries to maximize cache reuse:

  BP1: End of tools (Region 0) — tools are stable for session lifetime,
       but tool cache is a separate level from system/message cache.
       Actually: tools use the `cache_control` in the tool definition
       array, not in messages. We place BP1 on the last system block.

  BP1: End of system prompt (Region 1) — stable for session lifetime
  BP2: End of last frozen tensor pair (Region 2 frozen)
  BP3: End of page table acknowledgment (Region 2 mutable)
  BP4: Second-to-last ephemeral message (Region 3)

Note: The Anthropic cache hierarchy is tools → system → messages.
Tools get their own implicit cache level. We use our 4 markers for
system and messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheState:
    """Tracks cache waste for restructure decisions."""
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cumulative_waste_tokens: int = 0
    last_breakpoint_count: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.cache_read_tokens + self.cache_creation_tokens
        if total == 0:
            return 0.0
        return self.cache_read_tokens / total

    def update_from_usage(self, usage: dict[str, Any]) -> None:
        """Update cache state from an API response's usage dict."""
        self.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
        self.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)


def _add_cache_control_to_block(block: dict) -> None:
    """Add cache_control marker to a content block."""
    block["cache_control"] = {"type": "ephemeral"}


def _add_cache_control_to_message(msg: dict) -> None:
    """Add cache_control marker to the last content block of a message."""
    content = msg.get("content")
    if isinstance(content, str):
        msg["content"] = [
            {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
        ]
    elif isinstance(content, list) and content:
        last = content[-1]
        if isinstance(last, dict):
            last["cache_control"] = {"type": "ephemeral"}


def strip_all_cache_controls(payload: dict) -> None:
    """Remove all existing cache_control markers from the payload.

    Must run before place_breakpoints to prevent exceeding the 4-block
    API limit. Claude Code places its own markers on the system prompt;
    without stripping first we can end up with 5+.
    """
    # Strip from tools
    tools = payload.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict):
                tool.pop("cache_control", None)

    # Strip from system
    system = payload.get("system")
    if isinstance(system, list):
        for block in system:
            if isinstance(block, dict):
                block.pop("cache_control", None)

    # Strip from messages
    for msg in payload.get("messages", []):
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block.pop("cache_control", None)


def place_breakpoints(
    payload: dict,
    *,
    frozen_tensor_count: int = 0,
    has_page_table: bool = False,
) -> int:
    """Place up to 4 cache_control breakpoints at region boundaries.

    Mutates payload in place. Returns the number of breakpoints placed.

    Strategy:
      BP1: Last system block (Region 1 boundary)
      BP2: Last frozen tensor pair's assistant message (Region 2 frozen boundary)
      BP3: Page table ack (Region 2 mutable boundary)
      BP4: Second-to-last message (Region 3 boundary)

    With no frozen tensors: BP1 (system) + BP4 (second-to-last) = 2 breakpoints.
    This alone should improve cache hits from 7-8% to ~40%.
    """
    placed = 0

    # BP1: End of system prompt
    system = payload.get("system")
    if isinstance(system, list) and system:
        last_block = system[-1]
        if isinstance(last_block, dict):
            _add_cache_control_to_block(last_block)
            placed += 1

    messages = payload.get("messages", [])
    if not messages:
        return placed

    # Calculate message indices for region boundaries
    # Frozen tensor pairs: 2 messages each (user + assistant)
    # Page table: 2 messages (user + assistant)
    frozen_msg_count = frozen_tensor_count * 2
    page_table_msg_count = 2 if has_page_table else 0
    durable_msg_count = frozen_msg_count + page_table_msg_count

    # BP2: End of frozen tensor region (last assistant of frozen pairs)
    if frozen_msg_count > 0 and frozen_msg_count <= len(messages):
        bp2_idx = frozen_msg_count - 1  # last assistant msg of frozen tensors
        _add_cache_control_to_message(messages[bp2_idx])
        placed += 1

    # BP3: End of page table (page table ack assistant message)
    if has_page_table and durable_msg_count <= len(messages):
        bp3_idx = durable_msg_count - 1  # page table ack assistant msg
        _add_cache_control_to_message(messages[bp3_idx])
        placed += 1

    # BP4: Second-to-last message (previous turn cached for next call)
    if len(messages) >= 2:
        bp4_idx = len(messages) - 2
        # Don't place BP4 if it would collide with BP2 or BP3
        if bp4_idx > durable_msg_count - 1:
            _add_cache_control_to_message(messages[bp4_idx])
            placed += 1

    return placed
