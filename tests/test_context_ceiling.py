"""The natural-shape loop must know its substrate's context ceiling.

Spec: docs/superpowers/specs/2026-09-06-local-substrate-door-design.md §5.
Found live 2026-09-06: the local Qwen door's first probe wake grew to
68,025 tokens of context in one wake and died on llama-server's
exceed_context_size_error at 65,536. The Anthropic backend already closes a
cycle at 80% of a known limit and recovers from over-limit errors; the
OpenAI natural loop did neither.
"""

import json

import pytest

from hamutay.taste_open import OpenAITasteBackend
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import (
    DECLARE_QUIET_SCHEMA,
    TOOL_SCHEMAS,
    UPDATE_STATE_SCHEMA,
)

LLAMA_ERR = (
    "OpenAI backend error: {'code': 400, 'message': 'request (68025 tokens) "
    "exceeds the available context size (65536 tokens), try increasing it', "
    "'type': 'exceed_context_size_error', 'n_prompt_tokens': 68025, 'n_ctx': 65536}"
)


# --- helpers -----------------------------------------------------------------


def _backend(script, *, context_limit=None, capability=None):
    backend = OpenAITasteBackend(
        api_key="k", capability=capability, wake_mode="natural",
        context_limit=context_limit,
    )
    backend.payloads = []

    def fake_post(payload):
        backend.payloads.append(payload)
        nxt = script.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    backend._post_chat = fake_post
    return backend


def _tool_call(name, args, call_id="c1"):
    return {
        "id": call_id, "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _turn(content=None, tool_calls=None, finish="stop", prompt_tokens=100):
    return {
        "choices": [{
            "finish_reason": finish,
            "message": {"role": "assistant", "content": content, "tool_calls": tool_calls},
        }],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": 10},
    }


def _tools():
    return [TOOL_SCHEMAS["read"], TOOL_SCHEMAS["clock"], TOOL_SCHEMAS["bash"],
            TOOL_SCHEMAS["schedule_event"], UPDATE_STATE_SCHEMA, DECLARE_QUIET_SCHEMA]


def _names(payload):
    return sorted(t["function"]["name"] for t in payload.get("tools", []))


def _events(executor, event):
    return [e for e in executor.activity_log if e.get("event") == event]


# --- recognising the wall ------------------------------------------------------


def test_llama_server_context_error_is_recognised():
    from hamutay.taste_open import _is_context_limit_error

    assert _is_context_limit_error(RuntimeError(LLAMA_ERR))


def test_truncation_handles_openai_tool_messages():
    from hamutay.taste_open import _truncate_largest_tool_results

    conversation = [
        {"role": "system", "content": "s"},
        {"role": "tool", "tool_call_id": "c1", "name": "read", "content": "x" * 100_000},
        {"role": "tool", "tool_call_id": "c2", "name": "clock", "content": "small"},
    ]
    dropped = _truncate_largest_tool_results(conversation, target_drop_tokens=10_000)
    assert dropped > 0
    assert len(conversation[1]["content"]) < 100_000
    assert conversation[2]["content"] == "small"


# --- the soft threshold: perception withdrawn, state kept --------------------


def test_soft_threshold_withdraws_perception_tools_and_says_so(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    backend = _backend([
        _turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=850),  # 850 ≥ 80% of 1000
        _turn(content="closing", prompt_tokens=870),
    ], context_limit=1000)
    result = backend.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                          experiment_label="t", extra_tools=_tools(), tool_executor=executor)
    assert result.raw_output["response"] == "closing"
    first, second = backend.payloads
    assert "read" in _names(first) and "bash" in _names(first)
    assert _names(second) == sorted(["update_state", "schedule_event", "declare_quiet"])
    # The resident is told, once, in a USER message appended to the conversation.
    # Found live 2026-09-16 (community/qwen c8, the first wake to reach 80%):
    # Qwen's chat template raises "System message must be at the beginning"
    # on any system-role message after the first, so a mid-conversation
    # harness note must never carry the system role.
    notes = [m for m in second["messages"] if m["role"] == "user"
             and "context" in m["content"].lower() and "withdrawn" in m["content"].lower()]
    assert len(notes) == 1
    assert "850" in notes[0]["content"] and "1000" in notes[0]["content"]
    assert [i for i, m in enumerate(second["messages"]) if m["role"] == "system"] == [0]
    pressure = _events(executor, "budget_pressure")
    assert pressure and pressure[0]["action"] == "perception_tools_withdrawn"
    assert pressure[0]["context_limit"] == 1000


def test_after_withdrawal_the_wake_is_forced_to_text_within_three_turns(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    script = [_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=850)]
    # The model keeps calling state tools after withdrawal.
    for i in range(3):
        script.append(_turn(tool_calls=[_tool_call("update_state", {"updates": {"n": i}}, f"u{i}")],
                            prompt_tokens=860 + i))
    script.append(_turn(content="done", prompt_tokens=870))
    backend = _backend(script, context_limit=1000)
    result = backend.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                          experiment_label="t", extra_tools=_tools(), tool_executor=executor)
    assert result.raw_output["response"] == "done"
    last = backend.payloads[-1]
    assert "tools" not in last and last["tool_choice"] == "none"
    assert any(e["action"] == "all_tools_withdrawn" for e in _events(executor, "budget_pressure"))


def test_no_limit_means_no_withdrawal(tmp_path):
    """Regression guard: OpenRouter's million-token substrates keep today's loop."""
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    backend = _backend([
        _turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=200_000),
        _turn(content="ok", prompt_tokens=200_100),
    ])
    backend.call(model="anthropic/claude-fable-5", system="s",
                 messages=[{"role": "user", "content": "hi"}],
                 experiment_label="t", extra_tools=_tools(), tool_executor=executor)
    assert "read" in _names(backend.payloads[1])
    assert not _events(executor, "budget_pressure")


# --- hitting the wall anyway: truncate, withdraw, retry ----------------------


def test_context_limit_error_truncates_withdraws_and_retries(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    big = TOOL_SCHEMAS["read"]
    backend = _backend([
        _turn(tool_calls=[_tool_call("read", {"path": "README.md"})], prompt_tokens=100),
        RuntimeError(LLAMA_ERR),
        _turn(content="recovered", prompt_tokens=500),
    ], context_limit=65536)
    # Make the executor return a large result so there is something to drop.
    executor.execute = lambda name, args: {"content": "z" * 200_000}  # type: ignore[assignment]
    result = backend.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                          experiment_label="t", extra_tools=[big, UPDATE_STATE_SCHEMA],
                          tool_executor=executor)
    assert result.raw_output["response"] == "recovered"
    retry = backend.payloads[-1]
    tool_msgs = [m for m in retry["messages"] if m["role"] == "tool"]
    assert len(tool_msgs[0]["content"]) < 200_000
    assert _names(retry) == ["update_state"]
    recovery = _events(executor, "budget_recovery")
    assert recovery and recovery[0]["action"] == "truncate_and_retry_tools_withdrawn"
    # The note names the size the server actually refused (68,025), not the
    # last request that succeeded (100). Codex's frozen validation caught
    # the wrong number on 2026-09-16.
    notes = [m for m in retry["messages"] if m["role"] == "user" and "withdrawn" in m["content"].lower()]
    assert len(notes) == 1 and "68025" in notes[0]["content"] and "65536" in notes[0]["content"]
    assert [i for i, m in enumerate(retry["messages"]) if m["role"] == "system"] == [0]


def test_context_limit_error_on_the_first_turn_still_raises(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    backend = _backend([RuntimeError(LLAMA_ERR)], context_limit=65536)
    import pytest
    with pytest.raises(RuntimeError, match="context size"):
        backend.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                     experiment_label="t", extra_tools=_tools(), tool_executor=executor)


# --- a single result cannot eat the window ------------------------------------


def test_tool_result_cap_scales_with_the_ceiling(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    executor.execute = lambda name, args: {"content": "q" * 150_000}  # type: ignore[assignment]
    backend = _backend([
        _turn(tool_calls=[_tool_call("read", {"path": "x"})], prompt_tokens=100),
        _turn(content="ok", prompt_tokens=200),
    ], context_limit=64_000)
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                 experiment_label="t", extra_tools=_tools(), tool_executor=executor)
    tool_msg = [m for m in backend.payloads[1]["messages"] if m["role"] == "tool"][0]
    # 25% of the window, in chars (4 chars/token): 64_000 * 4 * 0.25 = 64_000
    assert len(tool_msg["content"]) <= 64_000 + 2_000  # head + declared-loss stub
    assert "elided" in tool_msg["content"].lower() or "truncated" in tool_msg["content"].lower()


def test_tool_result_cap_without_a_ceiling_is_the_old_cap(tmp_path):
    from hamutay.taste_open import _MAX_TOOL_RESULT_CHARS, _bound_tool_result_for_context

    assert len(_bound_tool_result_for_context("a" * 10)) == 10
    bounded = _bound_tool_result_for_context("a" * (_MAX_TOOL_RESULT_CHARS + 50_000))
    assert len(bounded) < _MAX_TOOL_RESULT_CHARS + 50_000


# --- learning the ceiling ------------------------------------------------------


def test_discovery_reads_n_ctx_from_a_llama_server():
    from hamutay.taste_open import discover_llama_server_context

    def fetch(url):
        assert url == "http://127.0.0.1:8081/props"
        return {"default_generation_settings": {"n_ctx": 65536}, "total_slots": 4}

    assert discover_llama_server_context("http://127.0.0.1:8081/v1", fetch=fetch) == 65536


def test_discovery_returns_none_when_the_server_is_not_llama():
    from hamutay.taste_open import discover_llama_server_context

    def fetch(url):
        raise OSError("connection refused")

    assert discover_llama_server_context("https://api.openai.com/v1", fetch=fetch) is None
    assert discover_llama_server_context("http://x/v1", fetch=lambda u: {"foo": 1}) is None


def test_heartbeat_context_limit_explicit_beats_discovered_beats_table(tmp_path):
    from hamutay.heartbeat import build_parser, resolve_context_limit

    args = build_parser().parse_args([
        "--log-path", str(tmp_path / "q.jsonl"), "--provider", "openai",
        "--base-url", "http://127.0.0.1:8081/v1", "--model", "qwen3.8-27b-q4km",
        "--context-limit", "40000",
    ])
    assert resolve_context_limit(args, discover=lambda url: 65536) == (40000, "explicit")
    args = build_parser().parse_args([
        "--log-path", str(tmp_path / "q.jsonl"), "--provider", "openai",
        "--base-url", "http://127.0.0.1:8081/v1", "--model", "qwen3.8-27b-q4km",
    ])
    assert resolve_context_limit(args, discover=lambda url: 65536) == (65536, "discovered")
    assert resolve_context_limit(args, discover=lambda url: None) == (None, "provider default")
    args = build_parser().parse_args([
        "--log-path", str(tmp_path / "h.jsonl"), "--provider", "openrouter",
        "--model", "anthropic/claude-haiku-4-5",
    ])
    assert resolve_context_limit(args, discover=lambda url: 65536) == (None, "provider default")


# --- window-aware: exact count, bound, budget, capture ----------------------
from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
from hamutay.window import (REPLY_RESERVE_TOKENS, THINK_FLOOR_TOKENS, CountUnavailable,
                            ExhaustedBeforeRequest, TruncatedReply)


class _Counter:
    def __init__(self, counts):
        self.counts = list(counts); self.seen = []

    def count(self, payload):
        self.seen.append(json.loads(json.dumps(payload)))
        n = self.counts.pop(0)
        if isinstance(n, Exception):
            raise n
        return n


def _aware(script, counts, *, budget="probed", forced=20, limit=65536, max_tokens=64000, wake_mode="natural"):
    holder = ContextPolicyHolder(ContextPolicy(limit, "discovered", limit, "http://127.0.0.1:8081", budget, {}, forced))
    backend = OpenAITasteBackend(api_key="k", wake_mode=wake_mode, context_policy=holder, max_tokens=max_tokens)
    backend.payloads = []
    backend._counter = _Counter(counts)

    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        nxt = script.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt
    backend._post_chat = fake_post
    return backend


def test_every_send_is_counted_and_bounded_on_the_natural_path(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=20000), _turn(content="done", prompt_tokens=21000)],
               counts=[20000, 21000])
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert len(b._counter.seen) == 2 == len(b.payloads)
    for c, p in zip(b._counter.seen, b.payloads):
        assert c["messages"] == p["messages"] and c["tools"] == p["tools"]
    assert b.payloads[0]["max_tokens"] == 65536 - 1 - 20000 and "reasoning_budget_tokens" not in b.payloads[0]
    assert all(pt + p["max_tokens"] < 65536 for pt, p in zip((20000, 21000), b.payloads))


def test_turn_zero_soft_threshold_withdraws_rebuilds_and_recounts(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="done", prompt_tokens=53000)], counts=[53000, 52000])   # 53000 >= 0.8*65536
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert len(b._counter.seen) == 2 and len(b.payloads) == 1
    assert _names(b.payloads[0]) == sorted(["update_state", "schedule_event", "declare_quiet"])
    assert b.payloads[0]["max_tokens"] == 65536 - 1 - 52000
    note = [m for m in b.payloads[0]["messages"] if m["role"] == "user" and "withdrawn" in (m["content"] or "")]
    assert note and "53000" in note[0]["content"] and "server" in note[0]["content"]
    ev = _events(executor, "budget_pressure")
    assert ev[0]["action"] == "perception_tools_withdrawn" and ev[0]["prompt_tokens"] == 53000


def test_near_the_wall_all_tools_go_after_one_turn_and_the_budget_arrives(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    script = [_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=53000),
              _turn(tool_calls=[_tool_call("update_state", {"updates": {"n": 1}}, "u1")], prompt_tokens=54000),
              _turn(content="done", prompt_tokens=55000)]
    b = _aware(script, counts=[53000, 53000, 54000, 55000])
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    last = b.payloads[-1]
    assert last["tool_choice"] == "none" and "tools" not in last
    room = 65536 - 1 - 55000
    assert last["max_tokens"] == room and last["reasoning_budget_tokens"] == room - REPLY_RESERVE_TOKENS - 20
    assert "reasoning_budget_tokens" not in b.payloads[-2]
    assert [e["action"] for e in _events(executor, "budget_pressure")][-1] == "generation_budgeted"


def test_three_turn_rule_holds_above_the_unrestricted_room(tmp_path):
    # On a 65,536 window the soft threshold (52,428) always leaves room below
    # 32,768, so the near-wall one-turn rule always applies there: the
    # three-turn rule can only be observed on a window big enough that 80% of
    # it still leaves an unrestricted think's worth of room. At 200,000 the
    # threshold is 160,000 and the room is 39,999 >= 32,768.
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    script = [_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=160_000)]
    for i in range(3):
        script.append(_turn(tool_calls=[_tool_call("update_state", {"updates": {"n": i}}, f"u{i}")],
                            prompt_tokens=160_000))
    script.append(_turn(content="done", prompt_tokens=160_000))
    # Six counts for five sends: one per send, plus turn 0's candidate count,
    # which is not reused because the withdrawal rebuilds the payload.
    b = _aware(script, counts=[160_000] * 6, limit=200_000)
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert len(b._counter.seen) == 6 and len(b.payloads) == 5   # every send was counted
    # The turn-0 count is at the threshold, so perception goes before the first send.
    state_tools = sorted(["update_state", "schedule_event", "declare_quiet"])
    assert _names(b.payloads[0]) == state_tools
    # Three tool turns keep the state tools; only then do all tools go.
    for p in b.payloads[:4]:
        assert p["tool_choice"] == "auto" and _names(p) == state_tools
    assert b.payloads[-1]["tool_choice"] == "none" and "tools" not in b.payloads[-1]
    # Room >= 32,768 throughout: the think is never budgeted.
    assert all("reasoning_budget_tokens" not in p for p in b.payloads)


def test_count_unavailable_fails_closed_with_no_request(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="never")], counts=[CountUnavailable("down")])
    with pytest.raises(CountUnavailable):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    assert b.payloads == [] and _events(executor, "budget_pressure")[-1]["action"] == "count_unavailable"


def test_exhausted_before_request_sends_nothing(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="never")], counts=[65536 - 1 - 100])
    with pytest.raises(ExhaustedBeforeRequest) as ei:
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    assert b.payloads == [] and ei.value.max_tokens == 100
    assert _events(executor, "budget_pressure")[-1]["action"] == "exhausted_before_request"


def test_truncated_reply_carries_the_snapshot_after_accounting(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="first", tool_calls=[_tool_call("clock", {})], prompt_tokens=100),
                _turn(content="<think>cut", finish="length", prompt_tokens=200)], counts=[100, 200])
    with pytest.raises(TruncatedReply) as ei:
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    e = ei.value
    assert e.text == "<think>cut" and e.message["content"] == "<think>cut" and e.turn_index == 1
    assert e.prompt_tokens == 200 and e.completion_tokens == 10
    assert e.account.input_tokens == 300 and e.account.output_tokens == 20 and len(e.account.responses) == 2
    assert e.account.interim_text == ["first"]


def test_truncation_is_typed_on_all_four_paths(tmp_path):
    cut = _turn(content="cut", finish="length")
    # single tool (terminal wake mode, no extra tools)
    b = _backend([json.loads(json.dumps(cut))]); b.wake_mode = "terminal"
    with pytest.raises(TruncatedReply):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t")
    # multi-turn
    b = _backend([json.loads(json.dumps(cut))]); b.wake_mode = "terminal"
    with pytest.raises(TruncatedReply):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=ToolExecutor(project_root=tmp_path, cycle=1))
    # terminal surface
    b = _backend([json.loads(json.dumps(cut))])
    with pytest.raises(TruncatedReply):
        b.call_terminal_surface(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                                experiment_label="t", terminal_surface=_terminal_surface_for_test())
    # natural: covered above


def test_single_tool_malformed_resend_is_recounted(tmp_path):
    bad = _turn(tool_calls=[{"id": "x", "type": "function", "function": {"name": "think_and_respond", "arguments": "{not json"}}],
                finish="tool_calls")
    good = _turn(tool_calls=[_tool_call("think_and_respond", {"response": "ok"})], finish="tool_calls")
    b = _aware([bad, good], counts=[100, 150], wake_mode="terminal")
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t")
    assert len(b._counter.seen) == 2 and b.payloads[1]["max_tokens"] == min(64000, 65536 - 1 - 150)
    assert b._counter.seen[1]["messages"] == b.payloads[1]["messages"]


def test_prepare_returns_the_exact_first_payload_and_call_prepared_sends_it(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[100, 100])
    prep = b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)
    assert prep.path == "natural" and prep.prompt_tokens == 100 and prep.sendable and prep.payload["model"] == "m"
    assert "max_tokens" not in prep.payload   # candidate mode leaves the payload unbounded
    b.call_prepared(prep)
    assert b.payloads[0]["messages"] == prep.payload["messages"] and b.payloads[0]["tools"] == prep.payload["tools"]
    assert b.payloads[0]["max_tokens"] == min(64000, 65536 - 1 - 100)


def test_prepare_candidate_reports_exhaustion_but_count_failure_raises(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([], counts=[65530])
    prep = b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)
    assert prep.sendable is False and prep.reason == "exhausted_before_request"
    b = _aware([], counts=[CountUnavailable("down")])
    with pytest.raises(CountUnavailable):
        b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)


def test_prepare_covers_the_terminal_surface_and_single_tool_paths(tmp_path):
    b = _aware([], counts=[10, 11], wake_mode="terminal")
    p = b.prepare("m", "s", [{"role": "user", "content": "hi"}], None, _terminal_surface_for_test(), None, candidate=True)
    assert p.path == "terminal_surface" and p.payload["tools"][0]["function"]["name"] == _terminal_surface_for_test()["tool_name"]
    p = b.prepare("m", "s", [{"role": "user", "content": "hi"}], None, None, None, candidate=True)
    assert p.path == "single_tool" and p.payload["tools"][0]["function"]["name"] == "think_and_respond"


def _terminal_surface_for_test():
    # `state_update` is required by terminal_tool_schema (it predates this
    # task); the brief's helper omitted it.
    return {"tool_name": "complete_task", "description": "Complete the bounded scheduled task.",
            "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
            "state_update": {"response_field": "summary"},
            "tool_choice": "force"}
