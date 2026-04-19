"""Open taste: self-curating tensor with no prescribed structure.

The model gets a tool with one required field (response) and permission
to add anything else. The harness preserves whatever it produces.
Default-stable protocol: the model declares what it's updating.
Everything else carries forward.

This is the "empty object" experiment — what does a transformer
build when it gets to decide what cognitive state looks like?

Usage:
    uv run python -m hamutay.taste_open
    uv run python -m hamutay.taste_open --provider openrouter --model anthropic/claude-haiku-4-5
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast
from uuid import UUID

import anthropic
import httpx

if TYPE_CHECKING:
    from anthropic.types import MessageParam


OPEN_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Your response to the user.",
        },
        "deleted_regions": {
            "type": "array",
            "description": (
                "Top-level keys to remove from state this cycle. "
                "The prior state is preserved in the log; deletion "
                "removes from working state, not from history."
            ),
            "items": {"type": "string"},
        },
    },
    "required": ["response"],
    "additionalProperties": True,
}


_SYSTEM_PROMPT = """\
You produce a single structured object each cycle: your response to \
the user, and whatever else you need to carry forward.

The `response` field is what the user sees. Beyond that, the object \
is yours. Add whatever fields help you think, remember, or track \
what matters. These are real fields in the JSON object you're \
producing — include the key and its value, just like `response`. \
The harness will preserve everything you produce.

The object is default-stable: whatever top-level keys you include \
this cycle are your updates, and any key you don't include carries \
forward unchanged from last cycle. If this is the first cycle, \
everything you include is new.

You may also list keys in `deleted_regions` to remove them from \
working state. Deleted keys are not lost — every prior state is \
preserved in the log, and may resurface through involuntary memory. \
Deletion is shedding, not destruction.

A prior instance of you may have written the object you're receiving, \
or this may be the first cycle and there's nothing yet. Either way, \
what you build here is for whoever comes next."""


_TOOL_GUIDANCE = """\
## Tools

Alongside think_and_respond you may call these tools before producing \
your state update:

### Perception

- read(path): Read a file from the project you live in.
- search_project(pattern): Search the codebase for a pattern.
- clock(): Current wall time, your cycle rate, and elapsed time since \
your last cycle. Ten minutes and ten days between cycles are different \
kinds of continuity.

### Memory

Five tools that let you look at your prior cycles without carrying \
their full content in context:

- memory_schema(cycle): The structure of a past cycle — field names, \
types, sizes — without the content.
- recall(cycle?, field?, recent?, random?): Retrieve content from a \
prior cycle. Four modes — surgical (cycle+field), full snapshot (cycle), \
trajectory (recent+field), serendipitous (random+field).
- compare(cycle_a, cycle_b, field?, content?): Structural diff between \
two cycles. With content=true, values of changed fields come along.
- walk(from_cycle, direction?, depth?): Traverse adjacent cycles. \
Returns summaries, not content — use recall afterward if a step looks \
worth loading.
- search_memory(query, narrow_by?): Substring search across your \
history. Structural narrowing (cycle range, field presence, field \
scope) first; keyword match after. Ranked most-recent-first.

What you recall is what you claimed then, not necessarily what was \
true. For grounding claims against external evidence, use perception \
tools.

### Reason field

Each tool accepts an optional `reason` field. When you have a reason \
worth stating, include it — it's recorded in your activity log. When \
you don't, omit it; an absent reason is fine and is itself information.

You are not required to use these tools. You are not rewarded for \
using them. They exist so you can see what's there. Use them when it \
helps you; don't when it doesn't."""


@dataclass
class ExchangeResult:
    """What comes back from a single taste_open API call."""

    raw_output: dict
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    tool_activity: list[dict] | None = None


@dataclass
class _ToolBlocks:
    """Partition of a response's tool_use blocks.

    think_and_respond is the protocol's terminal tool — the state update.
    Other tool_use blocks are perception or action tools the model chose
    to call. The framework should never silently drop the latter just
    because the former is present in the same response.
    """

    think_and_respond_input: dict | None
    other_tool_uses: list


def _split_tool_use_blocks(content) -> _ToolBlocks:
    """Partition response content into think_and_respond vs other tool calls."""
    tr_input = None
    others = []
    for block in content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if getattr(block, "name", None) == "think_and_respond":
            tr_input = block.input
        else:
            others.append(block)
    return _ToolBlocks(think_and_respond_input=tr_input, other_tool_uses=others)


def execute_concurrent_tool_calls(blocks, tool_executor) -> None:
    """Execute tool calls that arrived alongside a terminal think_and_respond.

    When the model returns think_and_respond in the same response as other
    tool_use blocks, the cycle is over — we have the state update. But the
    model *also* asked to call those other tools. Silently dropping them
    discards expressed intent. We execute them so the activity log reflects
    what the model actually did this cycle. Their results do not feed back
    into the model (the cycle is terminal), but the activity is recorded.
    """
    if tool_executor is None:
        return
    for block in blocks:
        name = getattr(block, "name", None)
        tool_input = getattr(block, "input", {})
        if name is None:
            continue
        tool_executor.execute(name, tool_input)


class TasteBridge(Protocol):
    """Persistence layer for taste_open tensors."""

    def store_open_state(self, state: dict, cycle: int) -> UUID: ...


class TasteBackend(Protocol):
    """Transport layer for taste_open — send prompt, get structured output."""

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult: ...


class AnthropicTasteBackend:
    """Streaming tool-use via the Anthropic SDK.

    Two modes:
      * Single-tool (no extra_tools): forces think_and_respond as the only
        tool; the model returns exactly one structured state update.
      * Multi-turn (extra_tools provided): the model may call perception
        or other tools, see results, and eventually call think_and_respond
        to close the cycle.
    """

    def __init__(self, client: anthropic.Anthropic | None = None):
        self._client = client or anthropic.Anthropic()

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult:
        if not extra_tools:
            return self._call_single_tool(model, system, messages, experiment_label)
        return self._call_multi_turn(
            model, system, messages, experiment_label, extra_tools, tool_executor
        )

    def _call_single_tool(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
    ) -> ExchangeResult:
        with self._client.messages.stream(
            model=model,
            max_tokens=64000,
            system=system,
            messages=cast("list[MessageParam]", messages),
            tools=[
                {
                    "name": "think_and_respond",
                    "description": (
                        "Produce your response and maintain your state."
                    ),
                    "input_schema": OPEN_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "think_and_respond"},
            metadata={"user_id": f"hamutay_{experiment_label}"},
        ) as stream:
            response = stream.get_final_message()

        split = _split_tool_use_blocks(response.content)
        if split.think_and_respond_input is None:
            raise RuntimeError("No think_and_respond output in response")

        usage = response.usage
        return ExchangeResult(
            raw_output=split.think_and_respond_input,
            stop_reason=response.stop_reason or "unknown",
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        )

    def _call_multi_turn(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict],
        tool_executor: Any | None,
    ) -> ExchangeResult:
        """Multi-turn loop: model calls perception tools, gets results,
        eventually calls think_and_respond. Uses streaming throughout
        to avoid the 16K non-streaming output ceiling.
        """
        tools: list[dict] = [
            {
                "name": "think_and_respond",
                "description": "Produce your response and maintain your state.",
                "input_schema": OPEN_SCHEMA,
            },
            *extra_tools,
        ]

        conversation = list(messages)
        total_input = 0
        total_output = 0
        cache_read = 0
        cache_create = 0
        max_turns = 10

        for _ in range(max_turns):
            with self._client.messages.stream(
                model=model,
                max_tokens=64000,
                system=system,
                messages=cast("list[MessageParam]", conversation),
                tools=cast("list", tools),
                tool_choice={"type": "any"},
                metadata={"user_id": f"hamutay_{experiment_label}"},
            ) as stream:
                response = stream.get_final_message()

            usage = response.usage
            total_input += getattr(usage, "input_tokens", 0) or 0
            total_output += getattr(usage, "output_tokens", 0) or 0
            cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_create += getattr(usage, "cache_creation_input_tokens", 0) or 0

            split = _split_tool_use_blocks(response.content)

            if split.think_and_respond_input is not None:
                # Terminal. Execute any concurrent tool calls for logging
                # so the model's expressed intent is honored rather than
                # silently dropped.
                execute_concurrent_tool_calls(
                    split.other_tool_uses, tool_executor
                )
                return ExchangeResult(
                    raw_output=split.think_and_respond_input,
                    stop_reason=response.stop_reason or "end_turn",
                    input_tokens=total_input,
                    output_tokens=total_output,
                    cache_read_tokens=cache_read,
                    cache_creation_tokens=cache_create,
                    tool_activity=(
                        tool_executor.activity_log if tool_executor else None
                    ),
                )

            if not split.other_tool_uses:
                raise RuntimeError(
                    "Model produced no tool calls and no think_and_respond "
                    "despite tool_choice='any'"
                )

            if tool_executor is None:
                raise RuntimeError(
                    "Model called perception tools but no tool_executor "
                    "was provided to resolve them"
                )

            # Serialize assistant content blocks for the conversation.
            assistant_content = []
            for block in response.content:
                if hasattr(block, "model_dump"):
                    assistant_content.append(block.model_dump())
                else:
                    assistant_content.append({"type": "text", "text": str(block)})
            conversation.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for block in split.other_tool_uses:
                result = tool_executor.execute(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    }
                )
            conversation.append({"role": "user", "content": tool_results})

        raise RuntimeError(
            f"Multi-turn exchange did not produce think_and_respond "
            f"within {max_turns} turns"
        )


class OpenAITasteBackend:
    """OpenAI-compatible chat completions (OpenRouter, LM Studio, vLLM, etc.)."""

    def __init__(
        self,
        base_url: str = "https://openrouter.ai/api/v1",
        api_key: str | None = None,
        timeout: float = 300,
        extra_headers: dict[str, str] | None = None,
        tool_choice: str | dict = "auto",
        max_tokens: int = 64000,
    ):
        self._base_url = base_url
        self._api_key = api_key or ""
        self._timeout = timeout
        self._extra_headers = extra_headers or {}
        self._tool_choice = tool_choice
        self._max_tokens = max_tokens

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,  # required by TasteBackend protocol
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult:
        if extra_tools:
            import warnings
            warnings.warn(
                "OpenAI backend does not yet support multi-turn tool use; "
                "extra_tools will be ignored.",
                stacklevel=2,
            )
        del tool_executor  # not yet used by OpenAI backend
        del experiment_label  # not consumed by OpenAI backend (protocol requirement)

        # OpenAI format: system prompt is a message, not a parameter
        oai_messages = [{"role": "system", "content": system}] + messages

        # OpenAI function calling format
        tool_def = {
            "type": "function",
            "function": {
                "name": "think_and_respond",
                "description": "Produce your response and maintain your state.",
                "parameters": OPEN_SCHEMA,
            },
        }

        payload: dict = {
            "model": model,
            "max_tokens": self._max_tokens,
            "messages": oai_messages,
            "tools": [tool_def],
            "tool_choice": self._tool_choice,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }

        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self._timeout,
        )
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"OpenAI backend error: {data['error']}")

        choice = data["choices"][0]
        raw_stop: str = choice.get("finish_reason") or "unknown"
        stop_reason: str = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
        }.get(raw_stop, raw_stop)

        usage = data.get("usage", {})

        # Extract tool call output
        message = choice.get("message", {})
        for tc in message.get("tool_calls", []):
            fn = tc.get("function", {})
            if fn.get("name") == "think_and_respond":
                args = fn.get("arguments", "")
                raw_output = json.loads(args) if isinstance(args, str) else args
                return ExchangeResult(
                    raw_output=raw_output,
                    stop_reason=stop_reason,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )

        # Fallback: some models put JSON in content
        content = message.get("content", "")
        if content:
            raw_output = self._extract_json(content)
            if raw_output is not None:
                raw_output = self._unwrap_tool_echo(raw_output)
                return ExchangeResult(
                    raw_output=raw_output,
                    stop_reason=stop_reason,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                )

        raise RuntimeError("OpenAI backend: no think_and_respond output in response")

    @staticmethod
    def _unwrap_tool_echo(obj: dict) -> dict:
        """Unwrap models that echo the tool definition structure.

        Some models (e.g. Llama 3.1 8B) put the tool call in content as:
            {"name": "think_and_respond", "parameters": {"response": ..., ...}}
        instead of using the tool_calls mechanism.  Also handles stringified
        inner fields (updated_regions as a JSON string instead of a list).
        """
        if (
            obj.get("name") == "think_and_respond"
            and isinstance(obj.get("parameters"), dict)
        ):
            obj = obj["parameters"]

        # Some models stringify array fields
        for key in ("updated_regions", "deleted_regions"):
            val = obj.get(key)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        obj[key] = parsed
                except (json.JSONDecodeError, ValueError):
                    pass
        return obj

    @staticmethod
    def _extract_json(content: str) -> dict | None:
        try:
            if "<think>" in content:
                content = content.split("</think>")[-1].strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return None


def _build_messages(
    prior_state: dict | None,
    user_message: str,
    cycle: int,
    system_prefix: str = "",
    memory: tuple[int, dict] | None = None,
    tools_enabled: bool = False,
) -> tuple[list[dict], str]:
    """Build messages for the call."""
    system_parts = []
    if system_prefix:
        system_parts.append(system_prefix)
    system_parts.extend([_SYSTEM_PROMPT, ""])

    if tools_enabled:
        system_parts.append(_TOOL_GUIDANCE)
        system_parts.append("")

    if prior_state is not None:
        system_parts.append(f"## Your state from cycle {cycle - 1}\n")
        system_parts.append(json.dumps(prior_state, indent=2))
    else:
        system_parts.append(
            "This is cycle 1. There is no prior state."
        )

    if memory is not None:
        memory_cycle, memory_state = memory
        system_parts.append(f"\n## A memory from cycle {memory_cycle}\n")
        system_parts.append(
            "This is a prior state that surfaced unbidden. "
            "You didn't ask for it. Do with it what you will."
        )
        system_parts.append(json.dumps(memory_state, indent=2))

    return [{"role": "user", "content": user_message}], "\n".join(system_parts)


# `updated_regions` is reserved so historical logs (which still carry it) don't smuggle it into state on resume.
_PROTOCOL_FIELDS = frozenset({"response", "updated_regions", "deleted_regions"})


def _apply_updates(prior_state: dict | None, raw_output: dict, cycle: int) -> dict:
    """Default-stable via key-presence: non-protocol keys in raw_output are
    updates, unlisted keys carry forward. Overlap between updates and deletions
    raises — the ambiguity is exactly the silent-drop failure we're removing."""
    deleted = set(raw_output.get("deleted_regions", []))
    updated = set(raw_output.keys()) - _PROTOCOL_FIELDS

    overlap = deleted & updated
    if overlap:
        raise ValueError(
            f"cycle {cycle}: deleted_regions overlaps updates: {sorted(overlap)}. "
            "A key cannot be simultaneously deleted and updated in the same cycle."
        )

    state = dict(prior_state) if prior_state is not None else {}
    state["cycle"] = cycle

    for key in updated:
        state[key] = raw_output[key]

    for key in deleted:
        state.pop(key, None)

    return state


class OpenTasteSession:
    """Open self-curating tensor chat. No prescribed structure."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        client: anthropic.Anthropic | None = None,
        backend: TasteBackend | None = None,
        log_path: str | None = None,
        experiment_label: str | None = None,
        system_prompt_prefix: str | None = None,
        resume: bool = False,
        bridge: TasteBridge | None = None,
        memory_base_probability: float = 0.1,
        enable_tools: bool = False,
        project_root: Path | None = None,
    ):
        self._backend = backend or AnthropicTasteBackend(client)
        self._model = model
        self._cycle = 0
        self._state: dict | None = None
        self._log_path = log_path
        self._last_usage: dict | None = None
        self._experiment_label = experiment_label or "taste_open"
        self._system_prompt_prefix = system_prompt_prefix or ""
        self._bridge: TasteBridge | None = bridge
        self._memory_base_prob = memory_base_probability
        self._enable_tools = enable_tools
        self._project_root = project_root or Path.cwd()
        self._session_start = datetime.now(timezone.utc)
        self._last_cycle_time: datetime | None = None
        # Accumulated prior states for involuntary recall and memory tools:
        # (cycle, state, timestamp_iso).
        self._prior_states: list[tuple[int, dict, str]] = []
        # Last injected memory cycle (for logging)
        self._last_injected_memory: tuple[int, dict] | None = None

        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)

        if resume and log_path:
            self._resume_from_log(log_path)

    def _resume_from_log(self, log_path: str) -> None:
        """Recover session state from the JSONL log.

        Rebuilds the full prior_states list so involuntary memory
        has the complete history to draw from, not just the last state.
        """
        with open(log_path) as f:
            lines = [line for line in f if line.strip()]

        if not lines:
            raise SystemExit(f"Cannot resume: log is empty: {log_path}")

        if lines[0].startswith("version https://git-lfs"):
            raise SystemExit(
                f"Cannot resume: {log_path} is a Git LFS pointer, not data. "
                f"Run: git lfs pull --include=\"{log_path}\""
            )

        for line in lines:
            record = json.loads(line)
            state = record.get("state")
            cycle = record.get("cycle", 0)
            timestamp = record.get("timestamp", "")
            if state is not None:
                self._prior_states.append((cycle, state, timestamp))

        last = json.loads(lines[-1])
        self._state = last.get("state")
        self._cycle = last.get("cycle", 0)

    @property
    def state(self) -> dict | None:
        return self._state

    @property
    def cycle(self) -> int:
        return self._cycle

    def _pick_memory(self) -> tuple[int, dict] | None:
        """Maybe select a prior state for involuntary recall.

        Probability increases with cycle count — early cycles have little
        to remember, later cycles have more past selves to encounter.
        Returns None if no memory fires or there's nothing to recall.
        """
        # Need at least 2 prior states (don't inject the immediately previous one)
        if len(self._prior_states) < 2:
            return None

        # Probability ramps: base_prob at cycle 1, approaches 0.5 asymptotically
        prob = min(self._memory_base_prob * (1 + self._cycle / 50), 0.5)
        if random.random() > prob:
            return None

        # Pick from all but the most recent (that's already in the system prompt).
        # Strip the timestamp — callers consume (cycle, state).
        candidates = self._prior_states[:-1]
        cycle, state, _ = random.choice(candidates)
        return (cycle, state)

    def exchange(self, user_message: str) -> str:
        """One cycle: user speaks, model responds + updates state."""
        self._cycle += 1

        # Involuntary memory — maybe surface a prior self
        memory = self._pick_memory()
        self._last_injected_memory = memory

        messages, system = _build_messages(
            self._state, user_message, self._cycle,
            system_prefix=self._system_prompt_prefix,
            memory=memory,
            tools_enabled=self._enable_tools,
        )

        # Tool wiring — only when enabled. Executor is scoped to this cycle.
        tool_executor = None
        extra_tools: list[dict] | None = None
        if self._enable_tools:
            from hamutay.tools import TOOL_SCHEMAS, ToolExecutor
            tool_executor = ToolExecutor(
                project_root=self._project_root,
                cycle=self._cycle,
                session_start=self._session_start,
                last_cycle_time=self._last_cycle_time,
                prior_states=self._prior_states,
            )
            extra_tools = list(TOOL_SCHEMAS.values())

        result = self._backend.call(
            model=self._model,
            system=system,
            messages=messages,
            experiment_label=self._experiment_label,
            extra_tools=extra_tools,
            tool_executor=tool_executor,
        )

        if result.stop_reason == "max_tokens":
            print(f"  WARNING: cycle {self._cycle} hit max_tokens — truncated")

        raw_output = result.raw_output
        response_text = raw_output.get("response", "(no response)")

        prior_state_snapshot = (
            json.loads(json.dumps(self._state)) if self._state else None
        )

        self._state = _apply_updates(self._state, raw_output, self._cycle)

        # Activity log is per-cycle — overwrites prior cycle's log rather
        # than accumulating. JSONL holds the full history for analysis.
        if result.tool_activity is not None:
            self._state["_activity_log"] = result.tool_activity

        self._last_cycle_time = datetime.now(timezone.utc)

        # Accumulate for future involuntary recall and memory tools
        self._prior_states.append(
            (
                self._cycle,
                json.loads(json.dumps(self._state)),
                self._last_cycle_time.isoformat(),
            )
        )

        # Persist to Apacheta if bridge is wired
        if self._bridge is not None:
            try:
                self._bridge.store_open_state(self._state, self._cycle)
            except Exception as e:
                print(f"  WARNING: bridge persist failed cycle {self._cycle}: {e}")

        self._last_usage = {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        self._log_entry(
            user_message=user_message,
            system_prompt=system,
            raw_output=raw_output,
            prior_state=prior_state_snapshot,
            usage={
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_input_tokens": result.cache_read_tokens,
                "cache_creation_input_tokens": result.cache_creation_tokens,
                "stop_reason": result.stop_reason,
            },
        )

        return response_text

    def _log_entry(
        self,
        user_message: str,
        system_prompt: str,
        raw_output: dict,
        prior_state: dict | None,
        usage: dict,
    ) -> None:
        """Append full record to JSONL log. Captures everything."""
        if not self._log_path:
            return

        # Capture involuntary memory injection
        injected = self._last_injected_memory
        memory_info = (
            {"injected_from_cycle": injected[0]} if injected else None
        )

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle": self._cycle,
            "experiment_label": self._experiment_label,
            "model": self._model,
            # Inputs
            "user_message": user_message,
            "system_prompt": system_prompt,
            "prior_state": prior_state,
            # Raw model output (complete, unmodified)
            "raw_output": raw_output,
            "deleted_regions": raw_output.get("deleted_regions", []),
            "response_text": raw_output.get("response", ""),
            # Resulting state after updates
            "state": self._state,
            # Token accounting
            "usage": usage,
            "state_token_estimate": (
                len(json.dumps(self._state)) // 4 if self._state else 0
            ),
            "system_prompt_tokens": len(system_prompt) // 4,
            # Structure metrics — what did the model build?
            "n_top_level_keys": (
                len([k for k in self._state if k != "cycle"])
                if self._state else 0
            ),
            "top_level_keys": (
                sorted(k for k in self._state if k != "cycle")
                if self._state else []
            ),
            # Involuntary memory
            "memory_injection": memory_info,
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Open taste: self-curating state with no prescribed structure"
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-6",
        help="Model (default: Sonnet 4.6)",
    )
    parser.add_argument(
        "--provider", default="anthropic",
        choices=["anthropic", "openrouter", "openai"],
        help="API provider (default: anthropic)",
    )
    parser.add_argument(
        "--base-url", default=None,
        help="Base URL for OpenAI-compatible endpoint",
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API key (default: from env OPENROUTER_API_KEY or OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--label", default=None,
        help="Experiment label for billing/logging (default: taste_open)",
    )
    parser.add_argument("--log-path", default=None, help="JSONL log path")
    parser.add_argument(
        "--resume", default=None,
        help="Resume from a log JSONL — picks up from last state",
    )
    parser.add_argument(
        "--persist", default="arango", nargs="?", const="arango",
        help="Persist tensors to Apacheta (default: arango). Pass a path for DuckDB, or --no-persist to disable.",
    )
    parser.add_argument(
        "--no-persist", action="store_true",
        help="Disable Apacheta persistence (JSONL backup only)",
    )
    parser.add_argument(
        "--memory-prob", default=0.1, type=float,
        help="Base probability of involuntary memory injection (default: 0.1)",
    )
    parser.add_argument(
        "--tools", action="store_true",
        help="Enable perception tools (read, search_project, clock)",
    )
    args = parser.parse_args()

    resume = False
    if args.resume is not None:
        args.log_path = args.resume
        resume = True
    elif args.log_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = Path("experiments") / "taste_open"
        log_dir.mkdir(parents=True, exist_ok=True)
        args.log_path = str(log_dir / f"taste_open_{ts}.jsonl")

    experiment_label = args.label or "taste_open"

    # Build backend
    backend: TasteBackend
    if args.provider == "anthropic":
        backend = AnthropicTasteBackend()
    else:
        if args.provider == "openrouter":
            base_url = args.base_url or "https://openrouter.ai/api/v1"
            api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
            extra_headers = {
                "X-Title": f"hamutay/{experiment_label}",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            }
        else:  # openai
            base_url = args.base_url or "https://api.openai.com/v1"
            api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
            extra_headers = {}

        if not api_key:
            raise SystemExit(
                f"No API key: pass --api-key or set "
                f"{'OPENROUTER_API_KEY' if args.provider == 'openrouter' else 'OPENAI_API_KEY'}"
            )

        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            extra_headers=extra_headers,
        )

    # Wire Apacheta bridge (default: ArangoDB, opt out with --no-persist)
    bridge = None
    if not args.no_persist and args.persist:
        try:
            from hamutay.apacheta_bridge import ApachetaBridge
            if args.persist == "arango":
                bridge = ApachetaBridge.from_arango(model=args.model)
                print("Persisting to: ArangoDB (via Apacheta)")
            else:
                bridge = ApachetaBridge.from_duckdb(
                    args.persist, model=args.model,
                )
                print(f"Persisting to: {args.persist}")
        except (ImportError, ConnectionError) as e:
            print(f"WARNING: persistence unavailable ({e}); continuing with JSONL only")

    session = OpenTasteSession(
        model=args.model,
        backend=backend,
        log_path=args.log_path,
        experiment_label=experiment_label,
        resume=resume,
        bridge=bridge,
        memory_base_probability=args.memory_prob,
        enable_tools=args.tools,
        project_root=Path.cwd(),
    )

    if resume:
        s = session.state
        keys = sorted(k for k in s if k != "cycle") if s else []
        est = len(json.dumps(s)) // 4 if s else 0
        print(f"Resumed from {args.log_path} at cycle {session.cycle}, "
              f"{len(keys)} keys ({', '.join(keys)}), ~{est:,} tokens")

    print("Open taste — no prescribed structure")
    print(f"Model: {args.model}")
    print(f"Log: {args.log_path}")
    print("Commands: 'quit', 'state', 'keys', 'usage'")
    print()

    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    history_file = Path("~/.cache/hamutay/taste_open_history").expanduser()
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

        if user_input.lower() == "state":
            s = session.state
            if s is None:
                print("(no state yet)")
            else:
                print(json.dumps(s, indent=2))
            print()
            continue

        if user_input.lower() == "keys":
            s = session.state
            if s is None:
                print("(no state yet)")
            else:
                for k, v in sorted(s.items()):
                    if k == "cycle":
                        continue
                    if isinstance(v, list):
                        print(f"  {k}: [{len(v)} items]")
                    elif isinstance(v, dict):
                        print(f"  {k}: {{{len(v)} keys}}")
                    elif isinstance(v, str) and len(v) > 80:
                        print(f"  {k}: {v[:77]}...")
                    else:
                        print(f"  {k}: {v}")
            print()
            continue

        if user_input.lower() == "usage":
            print(f"Cycle: {session.cycle}")
            if session._last_usage:
                print(f"API last call: "
                      f"in={session._last_usage['input_tokens']:,} "
                      f"out={session._last_usage['output_tokens']:,}")
            if session.state:
                est = len(json.dumps(session.state)) // 4
                print(f"State size: ~{est:,} tokens")
                keys = [k for k in session.state if k != "cycle"]
                print(f"Keys: {', '.join(sorted(keys))}")
            print()
            continue

        try:
            response = session.exchange(user_input)
            u = session._last_usage
            mem = session._last_injected_memory
            status_parts = [f"cycle {session.cycle}"]
            if u:
                status_parts.append(
                    f"in={u['input_tokens']:,} out={u['output_tokens']:,}"
                )
            if mem:
                status_parts.append(f"memory from cycle {mem[0]}")
            print(f"  [{' | '.join(status_parts)}]")
            print(f"\n{response}\n")
        except Exception as e:
            print(f"\nerror: {e}\n")
            import traceback
            traceback.print_exc()

    print(f"\nSession: {session.cycle} cycles")
    print(f"Log: {args.log_path}")


if __name__ == "__main__":
    main()
