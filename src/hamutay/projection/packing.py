"""Message packing — transforms region content into valid API message arrays.

The Anthropic API requires alternating user/assistant messages. The projection
reorders content by stability but must produce valid alternation.

Layout:
  system: [client system blocks + pichay prompt]                  # BP1
  messages:
    user: "Tensor store:\n[tensor:abc] CONTENT"  }
    assistant: "Tensor abc loaded."              } frozen          # BP2
    user: PAGE_TABLE_XML                         }
    assistant: "Page table acknowledged."        } mutable         # BP3
    ... ephemeral messages ...                                     # BP4 at [-2]
    user: current turn + anchor

Frozen tensor pairs: each packed as a user/assistant pair so they grow the
cached message prefix without invalidating existing content. They are NOT in
system — system changes invalidate the entire message cache.
"""

from __future__ import annotations

import sys
from typing import Any

from hamutay.projection.regions import (
    RegionState,
    PageTableEntry,
    TensorEntry,
)


def _build_tensor_pair(tensor: TensorEntry) -> tuple[dict, dict]:
    """Pack a single tensor into a user/assistant message pair."""
    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"[tensor:{tensor.handle}] {tensor.tensor_text}",
            }
        ],
    }
    assistant_msg = {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": f"Tensor {tensor.handle} loaded.",
            }
        ],
    }
    return user_msg, assistant_msg


def _build_page_table_xml(entries: list[PageTableEntry]) -> str:
    """Render the page table as XML for the model."""
    if not entries:
        return "<yuyay-page-table count=\"0\"/>"

    lines = [f'<yuyay-page-table count="{len(entries)}">']
    for entry in entries:
        lines.append(
            f'  <entry handle="{entry.handle}" kind="{entry.kind}" '
            f'status="{entry.status}" region="{entry.region}" '
            f'size_tokens="{entry.size_tokens}" '
            f'faults="{entry.fault_count}" '
            f'age_turns="{entry.age_turns}" '
            f'label="{_escape_xml_attr(entry.label)}"/>'
        )
    lines.append("</yuyay-page-table>")
    return "\n".join(lines)


def _build_page_table_pair(entries: list[PageTableEntry]) -> tuple[dict, dict]:
    """Pack the page table into a user/assistant message pair."""
    xml = _build_page_table_xml(entries)
    user_msg = {
        "role": "user",
        "content": [{"type": "text", "text": xml}],
    }
    assistant_msg = {
        "role": "assistant",
        "content": [{"type": "text", "text": "Page table acknowledged."}],
    }
    return user_msg, assistant_msg


def _escape_xml_attr(s: str) -> str:
    """Escape a string for use in an XML attribute value."""
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def pack_regions(
    *,
    system_blocks: list[dict[str, Any]],
    durable_state: RegionState,
    ephemeral_messages: list[dict[str, Any]],
    anchor_text: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pack all regions into (system, messages) for the API payload.

    Returns:
        (system_blocks, messages) — both ready for the API.

    The system_blocks are passed through as-is (Region 1).
    Messages are built as:
      1. Frozen tensor pairs (Region 2 frozen)
      2. Page table pair (Region 2 mutable)
      3. Ephemeral messages (Region 3, original ordering preserved)
      4. Anchor appended to last user message (Region 4)
    """
    messages: list[dict[str, Any]] = []

    # Region 2: Frozen tensor pairs
    # Sort by insertion order (dict preserves insertion order in Python 3.7+)
    for tensor in durable_state.tensors.values():
        if not tensor.frozen:
            continue
        user_msg, asst_msg = _build_tensor_pair(tensor)
        messages.append(user_msg)
        messages.append(asst_msg)

    # Region 2: Page table pair (mutable — rewritten each turn)
    if durable_state.page_table or durable_state.tensors:
        pt_user, pt_asst = _build_page_table_pair(durable_state.page_table)
        messages.append(pt_user)
        messages.append(pt_asst)

    # Region 3: Ephemeral messages (recent conversation turns)
    messages.extend(ephemeral_messages)

    # Region 4: Anchor — append to last user message
    if anchor_text and messages:
        _append_anchor(messages, anchor_text)

    return system_blocks, messages


def _append_anchor(messages: list[dict[str, Any]], anchor_text: str) -> None:
    """Append anchor text to the last user message."""
    # Find the last user message
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            content = messages[i].get("content", "")
            if isinstance(content, str):
                messages[i]["content"] = content + anchor_text
            elif isinstance(content, list):
                messages[i]["content"].append({
                    "type": "text",
                    "text": anchor_text,
                })
            return

    # No user message found — shouldn't happen, but don't crash
    print(
        "  projection: WARNING — no user message found for anchor",
        file=sys.stderr,
    )
