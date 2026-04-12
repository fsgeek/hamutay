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
from typing import Protocol

import anthropic
import httpx


OPEN_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string",
            "description": "Your response to the user.",
        },
        "updated_regions": {
            "type": "array",
            "description": (
                "Which top-level keys you changed this cycle. "
                "Keys not listed here carry forward from last cycle."
            ),
            "items": {"type": "string"},
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
    "required": ["response", "updated_regions"],
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

The object is default-stable: list the keys you're changing in \
`updated_regions`, and include those keys with their data in the \
object. Anything not listed carries forward unchanged from last \
cycle. If this is the first cycle, everything you include is new.

You may also list keys in `deleted_regions` to remove them from \
working state. Deleted keys are not lost — every prior state is \
preserved in the log, and may resurface through involuntary memory. \
Deletion is shedding, not destruction.

A prior instance of you may have written the object you're receiving, \
or this may be the first cycle and there's nothing yet. Either way, \
what you build here is for whoever comes next."""


@dataclass
class ExchangeResult:
    """What comes back from a single taste_open API call."""

    raw_output: dict
    stop_reason: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class TasteBackend(Protocol):
    """Transport layer for taste_open — send prompt, get structured output."""

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
    ) -> ExchangeResult: ...


class AnthropicTasteBackend:
    """Streaming tool-use via the Anthropic SDK."""

    def __init__(self, client: anthropic.Anthropic | None = None):
        self._client = client or anthropic.Anthropic()

    def call(
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
            messages=messages,
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

        raw_output = None
        for block in response.content:
            if (
                hasattr(block, "name")
                and block.type == "tool_use"
                and block.name == "think_and_respond"
            ):
                raw_output = block.input
                break

        if raw_output is None:
            raise RuntimeError("No think_and_respond output in response")

        usage = response.usage
        return ExchangeResult(
            raw_output=raw_output,
            stop_reason=response.stop_reason or "unknown",
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0),
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
        experiment_label: str,
    ) -> ExchangeResult:
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
        raw_stop = choice.get("finish_reason", "unknown")
        stop_reason = {
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
) -> tuple[list[dict], str]:
    """Build messages for the call."""
    system_parts = []
    if system_prefix:
        system_parts.append(system_prefix)
    system_parts.extend([_SYSTEM_PROMPT, ""])

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


def _apply_updates(prior_state: dict | None, raw_output: dict, cycle: int) -> dict:
    """Apply selective updates. Entirely generic — no hardcoded field names."""
    updated_regions = set(raw_output.get("updated_regions", []))

    # Start from prior state or empty
    state = dict(prior_state) if prior_state is not None else {}

    state["cycle"] = cycle

    # Apply everything the model declared as updated
    for key in updated_regions:
        if key in raw_output:
            state[key] = raw_output[key]

    # Remove anything the model declared as deleted
    deleted_regions = set(raw_output.get("deleted_regions", []))
    for key in deleted_regions:
        state.pop(key, None)

    # Don't carry protocol fields in the state
    state.pop("response", None)
    state.pop("updated_regions", None)
    state.pop("deleted_regions", None)

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
        bridge: object | None = None,
        memory_base_probability: float = 0.1,
    ):
        self._backend = backend or AnthropicTasteBackend(client)
        self._model = model
        self._cycle = 0
        self._state: dict | None = None
        self._log_path = log_path
        self._last_usage: dict | None = None
        self._experiment_label = experiment_label or "taste_open"
        self._system_prompt_prefix = system_prompt_prefix or ""
        self._bridge = bridge
        self._memory_base_prob = memory_base_probability
        # Accumulated prior states for involuntary recall: (cycle, state)
        self._prior_states: list[tuple[int, dict]] = []
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

        for line in lines:
            record = json.loads(line)
            state = record.get("state")
            cycle = record.get("cycle", 0)
            if state is not None:
                self._prior_states.append((cycle, state))

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

        # Pick from all but the most recent (that's already in the system prompt)
        candidates = self._prior_states[:-1]
        return random.choice(candidates)

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
        )

        result = self._backend.call(
            model=self._model,
            system=system,
            messages=messages,
            experiment_label=self._experiment_label,
        )

        if result.stop_reason == "max_tokens":
            print(f"  WARNING: cycle {self._cycle} hit max_tokens — truncated")

        raw_output = result.raw_output
        response_text = raw_output.get("response", "(no response)")

        prior_state_snapshot = (
            json.loads(json.dumps(self._state)) if self._state else None
        )

        self._state = _apply_updates(self._state, raw_output, self._cycle)

        # Accumulate for future involuntary recall
        self._prior_states.append((self._cycle, json.loads(json.dumps(self._state))))

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
            # What the model declared as changed
            "updated_regions": raw_output.get("updated_regions", []),
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
                print("Persisting to: ArangoDB (via YANANTIN_ARANGO_* env vars)")
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
