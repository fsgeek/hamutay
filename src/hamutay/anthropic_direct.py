"""Anthropic's own API behind the OpenAI-format loops (2026-10-19).

The natural wake, the window rules, the malformed-argument recovery and the
cost fields all live in `OpenAITasteBackend`, written against chat-completions
payloads. A resident moved from OpenRouter to Anthropic's API must keep that
behaviour exactly, so this backend replaces only the transport: each
chat-completions payload is translated to a Messages API request, streamed,
and the reply translated back into the chat-completions shape the loops read.

What the translation adds:

- Credentials from HAMUTAY_ANTHROPIC_API_KEY and the workspace id from
  HAMUTAY_ANTHROPIC_WORKSPACE_ID, never from ANTHROPIC_API_KEY: an exported
  ANTHROPIC_API_KEY makes Claude Code bill the API instead of the
  subscription (the $500 incident), so the name stays out of every
  environment.
- Prompt caching the way OpenRouter's top-level cache_control gave it to the
  resident: tools, system, and a breakpoint on the last block of the growing
  conversation, which advances every round trip of a wake (3 of the 4
  breakpoints the API allows).
- Cost from tokens. Anthropic reports tokens, not dollars, so usage.cost is
  priced here from ANTHROPIC_PRICES_PER_MTOK and marked
  cost_source="anthropic_token_estimate". A model missing from the table
  reports no cost: UNMEASURED, never free, and said loudly.
- Thinking blocks travel back to the API unchanged. The loops keep only
  content and tool_calls of an assistant turn, so the full Anthropic content
  of a turn that called tools is held here, keyed by its tool_use ids, and
  replayed in place of the reconstruction.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import anthropic

from hamutay.taste_open import CapabilityProfile, OpenAITasteBackend

KEY_ENV = "HAMUTAY_ANTHROPIC_API_KEY"
WORKSPACE_ENV = "HAMUTAY_ANTHROPIC_WORKSPACE_ID"
COST_SOURCE = "anthropic_token_estimate"

# USD per million tokens: (input, 5-minute cache write, cache read, output).
# Source: the claude-api skill's model tables (cached 2026-10-06), read
# 2026-10-19. A 1-hour cache write is 2x input. Claude Haiku 5.5 is left out
# on purpose: its price doubles above a 100K-token prompt, and a flat row
# would be wrong for long wakes.
ANTHROPIC_PRICES_PER_MTOK: dict[str, tuple[float, float, float, float]] = {
    "claude-fable-5": (10.0, 12.5, 1.00, 50.0),
    "claude-fable-5-1": (10.0, 12.5, 0.25, 50.0),
    "claude-opus-5-5": (4.0, 5.0, 0.20, 20.0),
    "claude-sonnet-5-5": (2.0, 2.5, 0.20, 10.0),
    "claude-haiku-4-5": (1.0, 1.25, 0.10, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 1.25, 0.10, 5.0),
}

# Output ceilings (max_tokens) per model; a request above one is a 400, and
# below one is the guillotine CLAUDE.md warns about.
ANTHROPIC_MAX_OUTPUT: dict[str, int] = {
    "claude-fable-5": 128_000,
    "claude-fable-5-1": 128_000,
    "claude-opus-5-5": 128_000,
    "claude-sonnet-5-5": 128_000,
    "claude-haiku-4-5": 64_000,
    "claude-haiku-4-5-20251001": 64_000,
}

_FINISH = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
    "max_tokens": "length",
    "refusal": "content_filter",
}


def anthropic_client_from_env(timeout: float = 600.0) -> anthropic.Anthropic:
    """The one way this house builds an Anthropic client: named key, named
    workspace, nothing read from ANTHROPIC_API_KEY. Missing either is fatal."""
    key = os.environ.get(KEY_ENV, "").strip()
    workspace = os.environ.get(WORKSPACE_ENV, "").strip()
    missing = [n for n, v in ((KEY_ENV, key), (WORKSPACE_ENV, workspace)) if not v]
    if missing:
        raise SystemExit(
            "anthropic-direct: " + " and ".join(missing) + " not set (load "
            "~/.config/hamutay/anthropic.env as the unit's EnvironmentFile; "
            "ANTHROPIC_API_KEY is never read)"
        )
    return anthropic.Anthropic(
        api_key=key,
        default_headers={"anthropic-workspace-id": workspace},
        timeout=timeout,
    )


def price_usage(model: str, usage: dict) -> float | None:
    """USD for one response's usage, or None when the model has no price."""
    row = ANTHROPIC_PRICES_PER_MTOK.get(model)
    if row is None:
        return None
    p_in, p_write5, p_read, p_out = row
    creation = usage.get("cache_creation") or {}
    write_1h = int(creation.get("ephemeral_1h_input_tokens") or 0)
    write_total = int(usage.get("cache_creation_input_tokens") or 0)
    write_5m = max(write_total - write_1h, 0)
    cost = (
        int(usage.get("input_tokens") or 0) * p_in
        + write_5m * p_write5
        + write_1h * p_in * 2
        + int(usage.get("cache_read_input_tokens") or 0) * p_read
        + int(usage.get("output_tokens") or 0) * p_out
    )
    return cost / 1_000_000


def _text_blocks(content: Any) -> list[dict]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content else []
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict) and part.get("type", "text") == "text":
                if part.get("text"):
                    out.append({"type": "text", "text": part["text"]})
        return out
    return []


class AnthropicDirectBackend(OpenAITasteBackend):
    """`OpenAITasteBackend` with Anthropic's Messages API as its transport."""

    def __init__(self, client: anthropic.Anthropic | None = None, *, max_tokens: int | None = None,
                 model_hint: str | None = None, **kwargs):
        if max_tokens is None:
            max_tokens = ANTHROPIC_MAX_OUTPUT.get(model_hint or "", 64_000)
        kwargs.setdefault("capability", CapabilityProfile(
            supports_parallel_tool_calls=False, tool_choice_mode="function_object"))
        super().__init__(
            base_url="https://api.anthropic.com",
            api_key="",
            max_tokens=max_tokens,
            provider_name="anthropic",
            openrouter_cache=False,
            **kwargs,
        )
        # Built at the first request, not here: a session can be constructed
        # (and tested) without credentials, and a door missing them fails its
        # first wake with the reason instead of crashing at import.
        self._client = client
        # Full Anthropic content of assistant turns that called tools, keyed by
        # each tool_use id, so thinking blocks are replayed unchanged.
        self._turn_blocks: dict[str, list[dict]] = {}

    # --- request: chat-completions -> Messages ------------------------------

    # Names prefixed _messages_: the parent sets instance attributes such as
    # self._tool_choice in __init__, which would shadow a method of that name.
    @staticmethod
    def _messages_tool(tool: dict) -> dict:
        fn = tool.get("function", tool)
        return {
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or fn.get("input_schema") or {"type": "object"},
        }

    @staticmethod
    def _messages_tool_choice(choice: Any) -> dict | None:
        if choice in (None, "auto"):
            return {"type": "auto"}
        if choice == "none":
            return {"type": "none"}
        if choice == "required":
            return {"type": "any"}
        if isinstance(choice, dict):
            name = (choice.get("function") or {}).get("name")
            if name:
                return {"type": "tool", "name": name}
        raise RuntimeError(f"anthropic-direct: untranslatable tool_choice {choice!r}")

    def _assistant_blocks(self, msg: dict) -> list[dict]:
        tool_calls = msg.get("tool_calls") or []
        for tc in tool_calls:
            held = self._turn_blocks.get(tc.get("id"))
            if held is not None:
                return held
        blocks = _text_blocks(msg.get("content"))
        for tc in tool_calls:
            fn = tc.get("function") or {}
            raw = fn.get("arguments", "")
            try:
                args = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except json.JSONDecodeError:
                args = {"_unparsed_arguments": raw}
            if not isinstance(args, dict):
                args = {"_arguments": args}
            blocks.append({"type": "tool_use", "id": tc["id"], "name": fn.get("name", ""),
                           "input": args})
        return blocks

    def _translate(self, payload: dict) -> dict:
        system_parts: list[dict] = []
        messages: list[dict] = []

        def add(role: str, blocks: list[dict]) -> None:
            if not blocks:
                return
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"].extend(blocks)
            else:
                messages.append({"role": role, "content": list(blocks)})

        for msg in payload["messages"]:
            role = msg.get("role")
            if role == "system" and not messages:
                system_parts.extend(_text_blocks(msg.get("content")))
            elif role in ("user", "system"):
                add("user", _text_blocks(msg.get("content")))
            elif role == "assistant":
                add("assistant", self._assistant_blocks(msg))
            elif role == "tool":
                content = msg.get("content")
                add("user", [{"type": "tool_result", "tool_use_id": msg["tool_call_id"],
                              "content": content if isinstance(content, str) else json.dumps(content)}])
            else:
                raise RuntimeError(f"anthropic-direct: untranslatable role {role!r}")

        cache = {"type": "ephemeral"}
        if system_parts:
            system_parts[-1] = {**system_parts[-1], "cache_control": cache}
        if messages and messages[-1]["content"]:
            # The advancing breakpoint: the end of this request's prefix, which
            # the next round trip of the wake reads back.
            last = messages[-1]["content"]
            last[-1] = {**last[-1], "cache_control": cache}

        max_tokens = payload.get("max_tokens") or self._max_tokens
        ceiling = ANTHROPIC_MAX_OUTPUT.get(payload["model"])
        request: dict = {
            "model": payload["model"],
            # Never above the model's ceiling (a 400); never lowered otherwise.
            "max_tokens": min(max_tokens, ceiling) if ceiling else max_tokens,
            "messages": messages,
        }
        if system_parts:
            request["system"] = system_parts
        tools = [self._messages_tool(t) for t in payload.get("tools") or []]
        if tools:
            tools[-1] = {**tools[-1], "cache_control": cache}
            request["tools"] = tools
            request["tool_choice"] = self._messages_tool_choice(payload.get("tool_choice"))
        return request

    # --- response: Messages -> chat-completions -----------------------------

    def _untranslate(self, model: str, response: Any) -> dict:
        raw_blocks = [b.model_dump(exclude_none=True) for b in response.content]
        text = "\n".join(b.get("text", "") for b in raw_blocks if b.get("type") == "text")
        tool_calls = [
            {"id": b["id"], "type": "function",
             "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
            for b in raw_blocks if b.get("type") == "tool_use"
        ]
        if tool_calls:
            for tc in tool_calls:
                self._turn_blocks[tc["id"]] = raw_blocks
        else:
            self._turn_blocks.clear()  # a text reply ends the wake's tool turns

        usage = response.usage.model_dump(exclude_none=True) if response.usage else {}
        read = int(usage.get("cache_read_input_tokens") or 0)
        write = int(usage.get("cache_creation_input_tokens") or 0)
        uncached = int(usage.get("input_tokens") or 0)
        cost = price_usage(model, usage)
        if cost is None:
            print(f"!!! anthropic-direct: no price for model {model!r}; this turn's cost "
                  "is UNMEASURED (not free)", file=sys.stderr)
        oa_usage: dict = {
            "prompt_tokens": uncached + read + write,
            "completion_tokens": int(usage.get("output_tokens") or 0),
            "prompt_tokens_details": {"cached_tokens": read, "cache_write_tokens": write},
            "anthropic_usage": usage,
        }
        if cost is not None:
            oa_usage["cost"] = cost
            oa_usage["cost_source"] = COST_SOURCE
        stop = response.stop_reason or "unknown"
        return {
            "id": response.id,
            "model": response.model,
            "choices": [{
                "index": 0,
                "finish_reason": _FINISH.get(stop, stop),
                "message": {"role": "assistant", "content": text,
                            **({"tool_calls": tool_calls} if tool_calls else {})},
            }],
            "usage": oa_usage,
            "anthropic_stop_reason": stop,
        }

    def _post_chat(self, payload: dict) -> dict:
        request = self._translate(payload)
        if self._client is None:
            try:
                self._client = anthropic_client_from_env(timeout=max(self._timeout, 600.0))
            except SystemExit as e:
                raise RuntimeError(str(e)) from None
        try:
            with self._client.messages.stream(**request) as stream:
                response = stream.get_final_message()
        except anthropic.APIStatusError as e:
            # RuntimeError so the loops' recovery (context-limit truncation)
            # and their refusal to treat errors as replies both apply.
            raise RuntimeError(f"anthropic-direct error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise RuntimeError(f"anthropic-direct transport failed: {e}") from e
        return self._untranslate(request["model"], response)
