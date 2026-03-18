"""Data model for the projection engine's four-region layout.

Regions:
  0: Tools — tool definitions (framework + phantom), cached for session lifetime
  1: System — system prompt + Pichay instructions, cached for session lifetime
  2: Durable — frozen tensors + mutable page table, append-only growth
  3: Ephemeral — recent conversation turns, rewritten each turn
  4: Anchor — current turn + live status, never cached
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class RegionID(enum.IntEnum):
    """Region identifiers, ordered front-to-back in the projection."""
    TOOLS = 0
    SYSTEM = 1
    DURABLE = 2
    EPHEMERAL = 3
    ANCHOR = 4


@dataclass
class TensorEntry:
    """A model-produced tensor stored in the durable region."""
    handle: str              # 8-char hex, content-addressed
    tensor_text: str         # model's compressed representation
    source_tool_use_id: str  # original tool_use_id that was evicted
    source_tool_name: str
    source_label: str        # human-readable label
    frozen: bool = True      # frozen entries are never modified


@dataclass
class PageTableEntry:
    """An entry in the page table — the model's map of available memory."""
    handle: str              # 8-char hex
    kind: str                # "file" | "tool_result" | "conversation" | "tensor"
    label: str               # human-readable (~40 chars)
    status: str              # "present" | "available" | "pending_removal"
    region: int              # 2 or 3 — where the content currently lives
    size_tokens: int         # approximate token count
    fault_count: int = 0     # times recalled after eviction
    age_turns: int = 0       # turns since last access


@dataclass
class RegionState:
    """Per-session state for the durable region (Region 2)."""
    tensors: dict[str, TensorEntry] = field(default_factory=dict)
    page_table: list[PageTableEntry] = field(default_factory=list)
    # Waste tracking
    waste_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass
class ProjectedPayload:
    """The output of a projection — a valid API payload with cache breakpoints.

    Fields:
        system: System prompt blocks (list of content blocks)
        messages: Alternating user/assistant messages
        tools: Tool definitions
        region_token_estimates: Approximate token counts per region
        breakpoint_count: Number of cache_control markers placed
    """
    system: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    region_token_estimates: dict[str, int] = field(default_factory=dict)
    breakpoint_count: int = 0
