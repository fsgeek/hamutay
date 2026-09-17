import json

import pytest

from hamutay.context_policy import ContextPolicy
from hamutay.window import (
    ADMISSION_MAX_PASSES, MIN_STUB_CHARS, REPLY_RESERVE_TOKENS, THINK_FLOOR_TOKENS,
    THINK_UNRESTRICTED_ROOM_TOKENS, Bound, CountUnavailable, ExhaustedBeforeRequest, TokenCounter,
    TruncatedReply, WakeAccount, WindowFailure, bound_payload, budget_message, lean_activity_logs,
    project_context_results,
)


class ScriptedCounter:
    def __init__(self, counts):
        self.counts = list(counts)
        self.payloads = []

    def count(self, payload):
        self.payloads.append(json.loads(json.dumps(payload)))
        n = self.counts.pop(0)
        if isinstance(n, Exception):
            raise n
        return n


def _policy(limit=65536, *, budget="probed", forced=20):
    return ContextPolicy(limit, "discovered", limit, "http://127.0.0.1:8081", budget, {}, forced)


def test_failures_are_typed_and_carry_numbers():
    assert issubclass(CountUnavailable, WindowFailure) and issubclass(TruncatedReply, WindowFailure)
    e = ExhaustedBeforeRequest(prompt_tokens=64000, limit=65536, room=1535, max_tokens=1535)
    assert (e.prompt_tokens, e.limit, e.room, e.max_tokens) == (64000, 65536, 1535, 1535)
    assert "64000 of 65536" in str(e)


def test_token_counter_renders_then_tokenizes_with_special_tokens():
    calls = []

    def http(method, url, body):
        calls.append((url, body))
        if url.endswith("/apply-template"):
            return {"prompt": "RENDERED"}
        return {"tokens": [1, 2, 3]}
    c = TokenCounter("http://127.0.0.1:8081", http)
    assert c.count({"model": "m", "messages": []}) == 3
    assert calls[0][0].endswith("/apply-template") and calls[0][1] == {"model": "m", "messages": []}
    assert calls[1][1] == {"content": "RENDERED", "add_special": True, "parse_special": True}


def test_token_counter_failure_is_count_unavailable():
    def http(method, url, body):
        raise OSError("down")
    with pytest.raises(CountUnavailable):
        TokenCounter("http://127.0.0.1:8081", http).count({"model": "m"})


def test_bound_payload_ample_room_sets_only_max_tokens():
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(), ScriptedCounter([20000]), configured_max_tokens=64000, tool_choice_none=False)
    assert b.prompt_tokens == 20000 and b.room == 65536 - 1 - 20000 == 45535
    assert p["max_tokens"] == 45535 and b.max_tokens == 45535 and b.sendable
    assert "reasoning_budget_tokens" not in p and b.budget_fields == {}
    assert b.prompt_tokens + p["max_tokens"] < 65536


def test_bound_payload_budget_only_on_grammar_free_turns_near_the_wall():
    counter = ScriptedCounter([40000, 40000])
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(forced=20), counter, configured_max_tokens=64000, tool_choice_none=False)
    assert b.room == 25535 < THINK_UNRESTRICTED_ROOM_TOKENS and "reasoning_budget_tokens" not in p
    p2 = {"model": "m", "messages": [], "tool_choice": "none"}
    b2 = bound_payload(p2, _policy(forced=20), counter, configured_max_tokens=64000, tool_choice_none=True)
    assert p2["reasoning_budget_tokens"] == 25535 - REPLY_RESERVE_TOKENS - 20
    assert p2["reasoning_budget_message"] == budget_message()
    assert b2.budget_fields["reasoning_budget_tokens"] == p2["reasoning_budget_tokens"]


def test_bound_payload_no_budget_when_not_probed():
    for kind in ("unsupported", "inconclusive", "not_probed"):
        p = {"model": "m", "messages": [], "tool_choice": "none"}
        bound_payload(p, _policy(budget=kind), ScriptedCounter([40000]), configured_max_tokens=64000, tool_choice_none=True)
        assert "reasoning_budget_tokens" not in p and p["max_tokens"] == 25535


def test_bound_payload_floor_is_checked_on_max_tokens_not_room():
    floor = REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + 20
    p = {"model": "m", "messages": [], "tool_choice": "none"}
    with pytest.raises(ExhaustedBeforeRequest) as ei:
        bound_payload(p, _policy(forced=20), ScriptedCounter([65536 - 1 - (floor - 1)]),
                      configured_max_tokens=64000, tool_choice_none=True)
    assert ei.value.max_tokens == floor - 1 and "max_tokens" not in p
    p = {"model": "m", "messages": [], "tool_choice": "none"}
    with pytest.raises(ExhaustedBeforeRequest):   # configured --max-tokens below the floor, room ample
        bound_payload(p, _policy(forced=20), ScriptedCounter([1000]), configured_max_tokens=floor - 1, tool_choice_none=True)
    p = {"model": "m", "messages": [], "tool_choice": "none"}
    b = bound_payload(p, _policy(forced=20), ScriptedCounter([1000]), configured_max_tokens=floor, tool_choice_none=True)
    assert p["max_tokens"] == floor and p["reasoning_budget_tokens"] == THINK_FLOOR_TOKENS


def test_bound_payload_candidate_mode_reports_instead_of_raising_the_floor():
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(), ScriptedCounter([65000]), configured_max_tokens=64000, tool_choice_none=False,
                      candidate=True)
    assert b.sendable is False and b.reason == "exhausted_before_request" and "max_tokens" not in p
    with pytest.raises(CountUnavailable):
        bound_payload(p, _policy(), ScriptedCounter([CountUnavailable("x")]), configured_max_tokens=64000,
                      tool_choice_none=False, candidate=True)


def test_bound_payload_strict_boundary():
    p = {"model": "m", "messages": [], "tool_choice": "auto"}
    b = bound_payload(p, _policy(), ScriptedCounter([10]), configured_max_tokens=1_000_000, tool_choice_none=False)
    assert b.prompt_tokens + p["max_tokens"] == 65536 - 1


def test_lean_activity_logs_is_recursive_and_copies():
    src = {"a": {"_activity_log": [{"cycle": 1, "timestamp": "t", "tool": "x", "reason": "r",
                                    "result_summary": "s", "parameters": {"big": "x" * 100},
                                    "result_hash": "h", "duration_ms": 3, "exit_code": 0}]},
           "b": [{"content": {"_activity_log": [{"tool": "y", "parameters": {}}]}}]}
    before = json.dumps(src)
    out = lean_activity_logs(src)
    assert json.dumps(src) == before
    assert out["a"]["_activity_log"] == [{"cycle": 1, "timestamp": "t", "tool": "x", "reason": "r", "result_summary": "s"}]
    assert out["b"][0]["content"]["_activity_log"] == [{"tool": "y"}]


def test_project_context_results_types_and_caps():
    big = {"request": {"tool": "recall", "cycle": 11},
           "result": {"cycle": 11, "content": {"k": "v" * 5000, "_activity_log": [{"tool": "t", "parameters": {"p": 1}}]}}}
    small = {"request": {"tool": "recall", "cycle": 1, "field": "k"}, "result": {"content": "short"}}
    out = project_context_results([big, small], cap_chars=1000)
    assert out[1]["result"] == {"content": "short"} and out[1]["result"] is not small["result"]
    r = out[0]["result"]
    assert r["truncated"] is True and r["chars_kept"] == 1000 and len(r["head"]) == 1000 and r["why"] == "context result cap"
    assert "parameters" not in json.dumps(r["head"]) or r["chars"] > 0   # lean applied before sizing
    assert "parameters" in json.dumps(big)                                # argument untouched
    out2 = project_context_results([big], cap_chars=MIN_STUB_CHARS - 1)
    assert "head" not in out2[0]["result"] and out2[0]["result"]["chars_kept"] == 0
    assert project_context_results([big, small], cap_chars=None) == [big, small]


def test_wake_account_and_truncated_reply_snapshot():
    acct = WakeAccount()
    acct.input_tokens += 5
    acct.interim_text.append("earlier")
    e = TruncatedReply(text="cut", message={"content": "cut"}, turn_index=2, prompt_tokens=100,
                       completion_tokens=7, account=acct)
    assert e.account.input_tokens == 5 and e.account.interim_text == ["earlier"] and e.turn_index == 2
    assert "finish_reason=length" in str(e)
