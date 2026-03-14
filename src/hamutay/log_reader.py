"""Read Pichay proxy logs and extract conversation turns.

The proxy logs are JSONL with alternating request/response_stream entries.
We extract the conversation content that the projector needs — the delta
of each turn, not the accumulated context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Turn:
    """A single conversation turn extracted from proxy logs."""

    turn_number: int
    timestamp: str
    role_counts: dict[str, int]
    message_count: int
    total_request_bytes: int
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int

    # The content we can extract — proxy logs have summaries, not full text.
    # For full content we'd need the session JSONL.
    system_prompt_preview: str


@dataclass(frozen=True)
class ConversationTurn:
    """A turn with actual message content, from session JSONL files."""

    turn_number: int
    role: str
    content: str


def read_proxy_log(path: Path) -> list[Turn]:
    """Read a proxy log and extract turn metadata.

    Proxy logs contain request/response pairs with metadata about
    message sizes, token counts, and cache behavior — but not full
    message content (by design, for privacy).
    """
    turns: list[Turn] = []
    turn_num = 0

    with open(path) as f:
        for line in f:
            entry = json.loads(line.strip())

            if entry["type"] == "request":
                turn_num += 1
                request = entry
            elif entry["type"] == "response_stream":
                usage = entry.get("usage", {})
                turns.append(
                    Turn(
                        turn_number=turn_num,
                        timestamp=request["timestamp"],
                        role_counts=request["messages"]["role_counts"],
                        message_count=request["messages"]["message_count"],
                        total_request_bytes=request["total_request_bytes"],
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_creation_tokens=usage.get(
                            "cache_creation_input_tokens", 0
                        ),
                        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                        system_prompt_preview=request["system"].get(
                            "system_prompt_preview", ""
                        ),
                    )
                )

    return turns


def _extract_text(content) -> str:
    """Extract text from message content, which may be a string or block list."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    text_parts.append(
                        f"[tool_use: {block.get('name', 'unknown')}]"
                    )
                elif block.get("type") == "tool_result":
                    text_parts.append(
                        f"[tool_result: {str(block.get('content', ''))[:200]}]"
                    )
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts)
    return str(content)


def read_session_jsonl(path: Path) -> list[ConversationTurn]:
    """Read a session JSONL file and extract conversation turns.

    Session files from Claude Code contain entries with a "type" field
    ("user" or "assistant") and a "message" field with role and content.
    Also handles queue-operation entries and other metadata.
    """
    turns: list[ConversationTurn] = []
    turn_num = 0

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)

            # Claude Code session format: {"type": "user"|"assistant", "message": {...}}
            entry_type = entry.get("type")
            if entry_type in ("user", "assistant"):
                msg = entry.get("message", {})
                role = msg.get("role", entry_type)
                content = _extract_text(msg.get("content", ""))

                if content:
                    turn_num += 1
                    turns.append(
                        ConversationTurn(
                            turn_number=turn_num,
                            role=role,
                            content=content,
                        )
                    )

    return turns
