"""Projection backends — API-specific transport for the Projector.

The Projector is backend-agnostic. It builds prompts, parses tensors,
detects collapses, and manages escalation. The backend handles the
single concern of sending a projection request and getting a response.

Two backends:
  - AnthropicBackend: streaming via the Anthropic SDK (current behavior)
  - OpenAIBackend: OpenAI-compatible endpoints (LM Studio, vLLM, etc.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import anthropic
import httpx

from hamutay.projector import PROJECTION_SCHEMA


@dataclass
class ProjectionResult:
    """What comes back from a single projection call."""

    tensor: dict
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ProjectionBackend(Protocol):
    """Minimal interface a Projector needs from its transport layer."""

    def call_projection(
        self,
        model: str,
        max_tokens: int,
        prompt: str,
    ) -> ProjectionResult:
        """Send a projection prompt, return a ProjectionResult.

        Stop reasons are normalized:
          - "end_turn" or "tool_use": normal completion
          - "max_tokens": output was truncated (the guillotine)
          - "unknown": couldn't determine

        Raises RuntimeError if no tensor could be extracted from the response.
        """
        ...


class AnthropicBackend:
    """Streaming projection via the Anthropic SDK.

    This is the existing behavior extracted from Projector._do_projection
    and Projector._raw_stream_fallback.
    """

    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()

    def call_projection(
        self,
        model: str,
        max_tokens: int,
        prompt: str,
    ) -> ProjectionResult:
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "name": "emit_tensor",
                        "description": "Emit the updated tensor projection",
                        "input_schema": PROJECTION_SCHEMA,
                    }
                ],
                tool_choice={"type": "tool", "name": "emit_tensor"},
            ) as stream:
                response = stream.get_final_message()
        except (ValueError, json.JSONDecodeError) as e:
            print(f"    SDK stream accumulator failed: {type(e).__name__}: {e}")
            print(f"      model={model}, retrying with raw event collection")
            response = self._raw_stream_fallback(model, max_tokens, prompt)

        stop_reason = response.stop_reason or "unknown"

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) if usage else 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) if usage else 0

        for block in response.content:
            if hasattr(block, "name") and block.type == "tool_use" and block.name == "emit_tensor":
                return ProjectionResult(
                    tensor=block.input,  # type: ignore[union-attr]
                    stop_reason=stop_reason,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read,
                    cache_creation_tokens=cache_create,
                )

        raise RuntimeError("Anthropic backend: no emit_tensor in response")

    def _raw_stream_fallback(self, model: str, max_tokens: int, prompt: str):
        """Collect raw SSE events when the SDK accumulator chokes."""
        from types import SimpleNamespace

        json_parts: list[str] = []
        stop_reason = "unknown"
        tool_use_id = ""
        tool_name = ""

        with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": "emit_tensor",
                    "description": "Emit the updated tensor projection",
                    "input_schema": PROJECTION_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "emit_tensor"},
        ) as stream:
            for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block"):
                            block = event.content_block
                            if hasattr(block, "id"):
                                tool_use_id = block.id
                            if hasattr(block, "name"):
                                tool_name = block.name
                    elif event.type == "content_block_delta":
                        if hasattr(event, "delta") and hasattr(event.delta, "partial_json"):
                            json_parts.append(event.delta.partial_json)
                    elif event.type == "message_delta":
                        if hasattr(event, "delta") and hasattr(event.delta, "stop_reason"):
                            stop_reason = event.delta.stop_reason or stop_reason

        raw_json = "".join(json_parts)
        tool_input = json.loads(raw_json)

        tool_block = SimpleNamespace(
            type="tool_use", name=tool_name, id=tool_use_id, input=tool_input,
        )
        return SimpleNamespace(stop_reason=stop_reason, content=[tool_block])


class OpenAIBackend:
    """Projection via OpenAI-compatible endpoints.

    Works with LM Studio, vLLM, OpenAI API, or anything that speaks
    the /v1/chat/completions protocol with function calling.
    """

    def __init__(
        self,
        base_url: str = "http://192.168.111.125:1234/v1",
        api_key: str = "lm-studio",
        timeout: float = 300,
        tool_choice: str | dict = "required",
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        # Most OpenAI-compatible endpoints only support string values
        # ("required", "auto", "none"). The OpenAI API itself supports
        # {"type": "function", "function": {"name": "..."}} for forcing
        # a specific function, but LM Studio / vLLM / etc. typically don't.
        self._tool_choice = tool_choice

    def call_projection(
        self,
        model: str,
        max_tokens: int,
        prompt: str,
    ) -> ProjectionResult:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "emit_tensor",
                        "description": "Emit the updated tensor projection",
                        "parameters": PROJECTION_SCHEMA,
                    },
                }
            ],
            "tool_choice": self._tool_choice,
        }

        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"OpenAI backend error: {data['error']}")

        choice = data["choices"][0]
        raw_stop = choice.get("finish_reason", "unknown")

        # Normalize stop reasons to Anthropic conventions
        stop_reason = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
        }.get(raw_stop, raw_stop)

        # Extract usage if provided
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        message = choice.get("message", {})

        def _result(tensor: dict) -> ProjectionResult:
            return ProjectionResult(
                tensor=tensor,
                stop_reason=stop_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        # Primary path: tool_calls in the response
        for tc in message.get("tool_calls", []):
            fn = tc.get("function", {})
            if fn.get("name") == "emit_tensor":
                args = fn.get("arguments", "")
                raw_tensor = json.loads(args) if isinstance(args, str) else args
                return _result(raw_tensor)

        # Fallback: some models put JSON in content instead of tool_calls
        content = message.get("content", "")
        if content:
            raw_tensor = self._extract_json_from_content(content)
            if raw_tensor is not None:
                return _result(raw_tensor)

        raise RuntimeError("OpenAI backend: no emit_tensor in response")

    @staticmethod
    def _extract_json_from_content(content: str) -> dict | None:
        """Try to extract a tensor dict from raw content.

        Some models (especially with thinking enabled) put the JSON
        in content rather than using tool_calls properly.
        """
        try:
            # Strip thinking tags if present
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return None
