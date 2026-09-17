"""Window-aware wakes: the numbers, the failures, the counter, the bound, the projections.

Spec: docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md r6.
Property (asserted in bound_payload): prompt_tokens + max_tokens < limit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

REPLY_RESERVE_TOKENS = 2048
THINK_FLOOR_TOKENS = 512
THINK_UNRESTRICTED_ROOM_TOKENS = 32768
WITHDRAWN_TOOL_TURNS_NEAR_WALL = 1
SOFT_THRESHOLD_FRACTION = 0.8
ADMISSION_TARGET_FRACTION = 0.5
ADMISSION_MAX_PASSES = 8
MIN_STUB_CHARS = 256
BUDGET_MESSAGE = ("[harness: thinking budget reached; about {reserve} tokens remain for this "
                  "turn. Do not open another think block. Finish the turn.]")
LEAN_ACTIVITY_KEYS = ("cycle", "timestamp", "tool", "reason", "result_summary")


def budget_message() -> str:
    return BUDGET_MESSAGE.format(reserve=REPLY_RESERVE_TOKENS)


class WindowFailure(RuntimeError):
    """A wake that could not be sent or finished inside the window."""


class CountUnavailable(WindowFailure):
    def __init__(self, error: str):
        self.error = error
        super().__init__(f"OpenAI backend: the prompt could not be counted: {error}")


class ExhaustedBeforeRequest(WindowFailure):
    def __init__(self, *, prompt_tokens: int, limit: int, room: int, max_tokens: int):
        self.prompt_tokens, self.limit, self.room, self.max_tokens = prompt_tokens, limit, room, max_tokens
        super().__init__(f"OpenAI backend: context exhausted before the request: {prompt_tokens} of "
                         f"{limit} in hand, {room} left, {max_tokens} would be allowed")


@dataclass
class WakeAccount:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    responses: list = field(default_factory=list)
    interim_text: list = field(default_factory=list)


class TruncatedReply(WindowFailure):
    def __init__(self, *, text: str, message: dict, turn_index: int, prompt_tokens: int,
                 completion_tokens: int, account: WakeAccount):
        self.text, self.message, self.turn_index = text, message, turn_index
        self.prompt_tokens, self.completion_tokens, self.account = prompt_tokens, completion_tokens, account
        super().__init__("OpenAI backend: finish_reason=length; the reply was truncated and is not trusted")


class TokenCounter:
    """Exact count of the prompt llama-server will tokenize for a request body."""

    def __init__(self, root: str, http):
        self._root, self._http = root, http

    def count(self, payload: dict) -> int:
        try:
            rendered = self._http("POST", f"{self._root}/apply-template", payload)["prompt"]
            toks = self._http("POST", f"{self._root}/tokenize",
                              {"content": rendered, "add_special": True, "parse_special": True})["tokens"]
        except Exception as e:
            raise CountUnavailable(str(e)[:200]) from e
        return len(toks)


@dataclass
class Bound:
    prompt_tokens: int
    room: int
    max_tokens: int
    budget_fields: dict
    sendable: bool
    reason: str | None
    count_source: str = "server"


def bound_payload(payload: dict, policy, counter, *, configured_max_tokens: int,
                  tool_choice_none: bool, candidate: bool = False) -> Bound:
    """Count, bound, and (unless candidate) mutate `payload`; assert the property.

    Raises CountUnavailable always; ExhaustedBeforeRequest unless candidate."""
    prompt_tokens = counter.count(payload)
    limit = policy.limit
    room = limit - 1 - prompt_tokens
    max_tokens = min(configured_max_tokens, room)
    floor = REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + policy.forced_sequence_tokens
    if max_tokens < floor:
        if candidate:
            return Bound(prompt_tokens, room, max_tokens, {}, False, "exhausted_before_request")
        raise ExhaustedBeforeRequest(prompt_tokens=prompt_tokens, limit=limit, room=room, max_tokens=max_tokens)
    fields: dict = {}
    # Gate on max_tokens (the generation limit actually sent), not room: the think must be
    # bounded whenever this turn's generation is bounded small, including when a configured
    # --max-tokens below the unrestricted threshold clamps max_tokens while room is ample
    # (r6.1). For the default configuration max_tokens == min(configured, room), so the two
    # gates agree whenever room is the binding term.
    if policy.reasoning_budget == "probed" and tool_choice_none and max_tokens < THINK_UNRESTRICTED_ROOM_TOKENS:
        fields = {"reasoning_budget_tokens": max_tokens - REPLY_RESERVE_TOKENS - policy.forced_sequence_tokens,
                  "reasoning_budget_message": budget_message()}
    if not candidate:
        assert prompt_tokens + max_tokens < limit, (prompt_tokens, max_tokens, limit)
        payload["max_tokens"] = max_tokens
        payload.update(fields)
    return Bound(prompt_tokens, room, max_tokens, fields, True, None)


def lean_activity_logs(obj):
    """Deep copy in which every `_activity_log` list's entries keep only the five lean keys."""
    def walk(x):
        if isinstance(x, dict):
            return {k: ([{kk: vv for kk, vv in e.items() if kk in LEAN_ACTIVITY_KEYS} if isinstance(e, dict) else e
                         for e in v] if k == "_activity_log" and isinstance(v, list) else walk(v))
                    for k, v in x.items()}
        if isinstance(x, list):
            return [walk(i) for i in x]
        return x
    return walk(json.loads(json.dumps(obj, default=str)))


def _drop_activity_logs(obj):
    """Deep copy with every `_activity_log` key removed at any depth.

    The compact wake's rendering: the record still carries the log, the prompt
    does not. Same walk as `lean_activity_logs`, deleting the key instead of
    thinning its entries."""
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items() if k != "_activity_log"}
        if isinstance(x, list):
            return [walk(i) for i in x]
        return x
    return walk(json.loads(json.dumps(obj, default=str)))


def project_context_results(results: list, cap_chars: int | None) -> list:
    """A deep-copied, lean, typed projection for the envelope; the argument is untouched."""
    if cap_chars is None:
        return json.loads(json.dumps(results, default=str))
    out = []
    for item in lean_activity_logs(results):
        result = item.get("result") if isinstance(item, dict) else None
        s = json.dumps(result, default=str)
        if len(s) > cap_chars:
            keep = cap_chars if cap_chars >= MIN_STUB_CHARS else 0
            stub = {"truncated": True, "chars": len(s), "chars_kept": keep, "why": "context result cap"}
            if keep:
                stub["head"] = s[:keep]
            item = dict(item, result=stub)
        out.append(item)
    return out
