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


def test_soft_threshold_is_checked_by_count_on_later_turns_too(tmp_path):
    """A window-aware door never withdraws on the character estimate.

    The exact count is taken before every send, not only the first: a turn-0
    payload under the threshold and a turn-1 payload over it must withdraw on
    turn 1, on the counted number rather than on the estimate (spec r6.2 §1).
    """
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    script = [_turn(tool_calls=[_tool_call("clock", {})], prompt_tokens=20000),
              _turn(content="done", prompt_tokens=53000)]
    # turn 0 counts 20000 (under 0.8*65536 = 52428) and is reused by the send;
    # turn 1 counts 53000 (over), withdraws, rebuilds, and the send recounts.
    b = _aware(script, counts=[20000, 53000, 52500])
    b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
           extra_tools=_tools(), tool_executor=executor)
    assert len(b._counter.seen) == 3 and len(b.payloads) == 2   # 1 on turn 0, 2 on turn 1
    assert "read" in _names(b.payloads[0]) and "bash" in _names(b.payloads[0])
    assert _names(b.payloads[1]) == sorted(["update_state", "schedule_event", "declare_quiet"])
    assert b.payloads[1]["max_tokens"] == 65536 - 1 - 52500
    note = [m for m in b.payloads[1]["messages"] if m["role"] == "user" and "withdrawn" in (m["content"] or "")]
    assert note and "53000" in note[0]["content"] and "server" in note[0]["content"]
    ev = _events(executor, "budget_pressure")
    assert ev[0]["action"] == "perception_tools_withdrawn"
    assert ev[0]["prompt_tokens"] == 53000 and ev[0]["count_source"] == "server"


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


def test_multi_turn_truncated_reply_carries_earlier_interim_text(tmp_path):
    """The multi-turn (terminal wake mode + extra tools) path must collect
    interim text the same way the natural path does (spec §4: the snapshot
    carries "the earlier turns' interim_text"), so a TruncatedReply raised on
    a later turn does not silently drop an earlier turn's content text."""
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([_turn(content="earlier-text", tool_calls=[_tool_call("clock", {})], prompt_tokens=100),
                _turn(content="<think>cut", finish="length", prompt_tokens=200)], counts=[100, 200],
               wake_mode="terminal")
    with pytest.raises(TruncatedReply) as ei:
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}], experiment_label="t",
               extra_tools=_tools(), tool_executor=executor)
    assert ei.value.account.interim_text == ["earlier-text"]


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
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[100])
    prep = b.prepare("m", "s", [{"role": "user", "content": "hi"}], _tools(), None, executor, candidate=True)
    assert prep.path == "natural" and prep.prompt_tokens == 100 and prep.sendable and prep.payload["model"] == "m"
    assert "max_tokens" not in prep.payload   # candidate mode leaves the payload unbounded
    b.call_prepared(prep)
    # The prepare counted these exact bytes; the send must not count them again.
    assert len(b._counter.seen) == 1
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


# --- Task 5: the session's policy holder, lean rendering, the failure record ---
from hamutay.taste_open import OpenTasteSession, _build_messages


def _state_with_log():
    return {"cycle": 2, "k": "v", "_activity_log": [{"cycle": 2, "timestamp": "t", "tool": "clock", "reason": "r",
                                                     "result_summary": "s", "parameters": {"p": 1}, "result_hash": "h"}]}


def _state_section(system: str) -> dict:
    head = system.index("## Your state from cycle")
    body = system[head:].split("\n", 2)[2]
    if body.startswith("(_activity_log"):
        body = body.split("\n", 1)[1]
    return json.loads(body.split("\n## ")[0])


def test_lean_activity_log_rendering_is_structural_and_leaves_the_state_untouched():
    st = _state_with_log(); before = json.dumps(st)
    _, system = _build_messages(st, "u", 3, tools_enabled=True, wake_mode="natural", lean_activity_log=True)
    assert json.dumps(st) == before
    parsed = _state_section(system)
    assert list(parsed["_activity_log"][0]) == ["cycle", "timestamp", "tool", "reason", "result_summary"]
    assert "(_activity_log is shown without parameters; the record has them)" in system
    _, plain = _build_messages(st, "u", 3, tools_enabled=True, wake_mode="natural")
    assert "parameters" in plain and "(_activity_log is shown" not in plain
    _, omitted = _build_messages(st, "u", 3, tools_enabled=True, wake_mode="natural", omit_activity_log=True)
    assert "_activity_log" not in _state_section(omitted) and "(_activity_log is omitted" in omitted


def test_session_records_a_truncated_reply_with_real_usage_once(tmp_path):
    b = _aware([_turn(content="first", tool_calls=[_tool_call("clock", {})], prompt_tokens=100),
                _turn(content="<think>cut", finish="length", prompt_tokens=200)], counts=[100, 200])
    log = tmp_path / "s.jsonl"
    s = OpenTasteSession(model="m", backend=b, log_path=str(log), experiment_label="t", enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    with pytest.raises(TruncatedReply):
        s.exchange("hi")
    rec = json.loads(log.read_text().splitlines()[-1])
    fc = rec["failure_classification"]
    assert fc["error_type"] == "TruncatedReply" and fc["truncated_reply"]["text"] == "<think>cut"
    assert fc["truncated_reply"]["trusted"] is False and fc["truncated_reply"]["turn_index"] == 1
    assert rec["usage"]["input_tokens"] == 300 and rec["usage"]["output_tokens"] == 20 and rec["usage"]["stop_reason"] == "max_tokens"
    # The spec's invariant (§4): the truncated text appears under
    # `truncated_reply`, never in `interim_text`. `message` keeps the raw
    # `choices[0].message` beside the flattened `text`, so a global substring
    # count over the record is not the thing being asserted.
    assert rec["interim_text"] == ["first"]
    assert "<think>cut" not in json.dumps(rec["interim_text"])
    # M4: this policy carries no invocation id, so the key is present (the door
    # is window-aware) and null. The completed-wake case, where the id exists
    # and must be recorded, is
    # test_a_completed_window_aware_wake_records_the_invocation_id.
    assert "context_policy_invocation" in rec
    assert rec["context_policy_invocation"] is None


def test_session_context_policy_is_the_backends_holder_and_replaces_once(tmp_path, monkeypatch):
    from hamutay.context_policy import ContextPolicy
    b = _aware([], counts=[])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    assert s.context_policy is b.policy
    seen = []
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(
        lambda cls, limit, source, base_url, **kw: seen.append((limit, source, kw.get("invocation_id"))) or
        ContextPolicy(limit, source, limit, "http://127.0.0.1:8081", "probed", {"build_info": "x"}, 20, kw.get("invocation_id"))))
    s.apply_context_limit(32768, "discovered", "inv-1")
    assert seen == [(32768, "discovered", "inv-1")]
    assert b.policy.limit == 32768 and s.context_policy.invocation_id == "inv-1"
    assert s._launch_config["context_limit"] == 32768 and s._launch_config["context_policy"]["limit"] == 32768
    last = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert last["record_type"] == "substrate_observation" and last["context_limit"] == 32768


def test_apply_context_limit_keeps_the_old_policy_when_the_probe_raises(tmp_path, monkeypatch):
    from hamutay.context_policy import ContextPolicy
    b = _aware([], counts=[])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    old = s.context_policy
    def boom(cls, *a, **k):
        raise RuntimeError("probe failed")
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(boom))
    s.apply_context_limit(32768, "discovered", "inv-2")
    assert s.context_policy is old


def test_apply_context_limit_never_demotes_a_window_aware_door(tmp_path, monkeypatch):
    """The blocker (Task 4 review, finding 1): gate.py calls this on every
    unvalidated lease invocation. The old path assigned through the backend's
    `_context_limit` setter, which replaced a probed, tokenizer-bearing policy
    with a bare `for_limit` one — a window-aware door silently demoted to the
    character-estimate loop on the first rediscovery."""
    from hamutay.context_policy import ContextPolicy
    b = _aware([], counts=[])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    assert s.context_policy.window_aware
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(
        lambda cls, limit, source, base_url, **kw: ContextPolicy(
            limit, source, limit, "http://127.0.0.1:8081", "probed", {"build_info": "x"}, 20,
            kw.get("invocation_id"))))
    s.apply_context_limit(32768, "discovered", "inv-3")
    assert s.context_policy.window_aware, "a rediscovery must not demote a window-aware door"
    assert s.context_policy.tokenizer == "http://127.0.0.1:8081"
    assert s.context_policy.reasoning_budget == "probed"
    assert b.policy is s.context_policy and b.policy.limit == 32768


def test_apply_context_limit_keeps_a_window_aware_policy_when_props_fails(tmp_path):
    """`for_launch` swallows a failed `/props` and returns `for_limit`.

    That is the right answer at launch (a door with no tokenizer is still a
    door) and the wrong one at rediscovery: the success path would replace a
    probed, counting policy with a bare ceiling and demote the door without
    raising anything. No monkeypatch here — the real `for_launch` runs against
    an `_http` whose `/props` raises, which is exactly what a llama-server
    that is up but not yet answering looks like."""
    b = _aware([], counts=[])

    def dead_http(method, url, body=None):
        raise RuntimeError("connection refused")

    b._http = dead_http
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    old = s.context_policy
    assert old.window_aware
    s.apply_context_limit(32768, "discovered", "inv-props")
    assert s.context_policy is old and s.context_policy.window_aware
    assert s.context_policy.limit == 65536          # the old ceiling, not the new one
    rec = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert rec["record_type"] == "substrate_observation"
    assert rec["context_policy_kept"] is True
    assert rec["reason"] == "rediscovery lost the tokenizer"
    assert rec["window_aware"] is True and rec["tokenizer"] is True
    assert rec["reasoning_budget"] == "probed"


def test_a_successful_apply_records_the_new_policy_state(tmp_path, monkeypatch):
    from hamutay.context_policy import ContextPolicy
    b = _aware([], counts=[])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(
        lambda cls, limit, source, base_url, **kw: ContextPolicy(
            limit, source, limit, "http://127.0.0.1:8081", "probed", {"build_info": "x"}, 20,
            kw.get("invocation_id"))))
    s.apply_context_limit(32768, "discovered", "inv-ok")
    rec = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert rec["window_aware"] is True and rec["reasoning_budget"] == "probed"
    assert "context_policy_kept" not in rec and "reason" not in rec


def test_a_non_window_aware_door_is_not_blocked_from_gaining_a_ceiling(tmp_path):
    """The keep rule is a demotion guard, not a freeze: a door that was never
    window-aware must still be able to learn its ceiling."""
    from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
    b = OpenAITasteBackend(api_key="k", wake_mode="natural",
                           context_policy=ContextPolicyHolder(ContextPolicy.none()))

    def dead_http(method, url, body=None):
        raise RuntimeError("connection refused")

    b._http = dead_http
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    assert not s.context_policy.window_aware
    s.apply_context_limit(32768, "discovered", "inv-new")
    assert s.context_policy.limit == 32768
    rec = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert rec["context_limit"] == 32768 and "context_policy_kept" not in rec
    # M2: the three policy-state keys ride only on a window-aware door. A door
    # that cannot count has nothing to say about its tokenizer or its
    # reasoning budget, so its observation record is what it always was —
    # byte-identical, not three keys wider.
    assert "window_aware" not in rec
    assert "tokenizer" not in rec and "reasoning_budget" not in rec


def test_the_activity_note_follows_whichever_section_was_thinned():
    """Cycle 1 has no prior state, so a note under the state heading would
    describe nothing. The note belongs under the section it describes."""
    mem = {"cycle": 1, "_activity_log": [{"cycle": 1, "timestamp": "t", "tool": "clock",
                                          "reason": "r", "result_summary": "s",
                                          "parameters": {"p": 1}, "result_hash": "h"}]}
    before = json.dumps(mem)
    _, system = _build_messages(None, "u", 1, tools_enabled=True, wake_mode="natural",
                                memory=(1, mem), lean_activity_log=True)
    assert json.dumps(mem) == before
    head = system.index("## A memory from cycle 1")
    tail = system[head:]
    assert "(_activity_log is shown without parameters; the record has them)" in tail
    parsed = json.loads(tail[tail.index("{"):].split("\n## ")[0])
    assert list(parsed["_activity_log"][0]) == ["cycle", "timestamp", "tool", "reason", "result_summary"]
    _, plain = _build_messages(None, "u", 1, tools_enabled=True, wake_mode="natural",
                               memory=(1, mem))
    assert "parameters" in plain and "(_activity_log is shown" not in plain


def test_the_note_is_not_emitted_for_a_section_with_no_activity_log():
    """A state with no `_activity_log` was not thinned; claiming it was is a lie."""
    _, system = _build_messages({"cycle": 2, "k": "v"}, "u", 3, tools_enabled=True,
                                wake_mode="natural", lean_activity_log=True)
    assert "(_activity_log is shown" not in system


def test_lean_and_omit_together_are_refused():
    with pytest.raises(ValueError):
        _build_messages({"cycle": 2}, "u", 3, lean_activity_log=True, omit_activity_log=True)


def test_admission_halves_the_cap_from_the_full_results_until_under_target(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[40000, 33000, 30000, 30000])   # 3 candidate counts + 1 send
    log = tmp_path / "s.jsonl"
    s = OpenTasteSession(model="m", backend=b, log_path=str(log), experiment_label="t", enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    caps = []

    def envelope(cap):
        caps.append(cap)
        return json.dumps({"purpose": "p", "context_results": [{"result": "x" * (cap or 100000)}]})
    s.exchange("ignored", render_envelope=envelope)
    assert caps == [32768, 16384, 8192] and s._last_admission == {
        "passes": 3, "final_cap": 8192, "prompt_tokens": 30000, "over_target": False, "envelope_exhausted": False}
    rec = json.loads(log.read_text().splitlines()[-1])
    assert rec["admission"]["passes"] == 3 and rec["user_message"] == envelope(8192)
    assert b.payloads[0]["messages"][-1]["content"] == envelope(8192)


def test_admission_stops_at_the_pass_bound_and_reports_over_target(tmp_path):
    """The pass bound is an independent stop (spec r6.3 §2).

    On a 65,536 window the cap starts at 32,768 and halves while the floor
    allows it: 32768, 16384, 8192, 4096, 2048, 1024, 512, 256. Reaching the
    all-stubs cap of 0 would take a ninth pass, which ADMISSION_MAX_PASSES
    forbids, so this wake terminates still over target with a real (not
    metadata-only) cap. `envelope_exhausted` is False precisely because the
    envelope was never exhausted — the passes ran out first.
    """
    from hamutay.window import ADMISSION_MAX_PASSES, MIN_STUB_CHARS
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[40000] * 9 + [40000])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    caps = []
    s.exchange("ignored", render_envelope=lambda cap: caps.append(cap) or json.dumps({"cap": cap}))
    a = s._last_admission
    assert a["passes"] == ADMISSION_MAX_PASSES and a["over_target"] is True
    assert a["final_cap"] == MIN_STUB_CHARS and a["envelope_exhausted"] is False
    assert caps == [32768, 16384, 8192, 4096, 2048, 1024, 512, 256]
    assert caps[-1] == MIN_STUB_CHARS and len(caps) == ADMISSION_MAX_PASSES


def test_a_compact_wake_over_target_is_exhausted_in_one_pass(tmp_path):
    """The other way admission ends: the envelope really is spent.

    A compact wake starts at cap 0 — every result already a metadata-only
    stub — so there is nothing left to halve. One pass, and if the count is
    still over target the wake proceeds over target with `envelope_exhausted`
    true: the harness has cut everything it is allowed to cut.
    """
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[40000, 40000])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    caps = []
    s.exchange("ignored", render_envelope=lambda cap: caps.append(cap) or json.dumps({"cap": cap}),
               compact=True)
    a = s._last_admission
    assert caps == [0] and a["passes"] == 1
    assert a["envelope_exhausted"] is True and a["over_target"] is True and a["final_cap"] == 0


def test_admission_first_candidate_below_the_floor_is_not_an_error(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[65000, 30000, 30000])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    s.exchange("ignored", render_envelope=lambda cap: json.dumps({"cap": cap}))
    assert s._last_admission["passes"] == 2 and b.payloads


def test_compact_wake_omits_the_activity_log_and_starts_at_stubs(tmp_path):
    b = _aware([_turn(content="done", prompt_tokens=100)], counts=[100, 100])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state(_state_with_log(), 2)
    caps = []
    s.exchange("ignored", render_envelope=lambda cap: caps.append(cap) or json.dumps({"cap": cap}), compact=True)
    assert caps == [0] and "_activity_log" not in _state_section(b.payloads[0]["messages"][0]["content"])
    assert "(_activity_log is omitted" in b.payloads[0]["messages"][0]["content"]


def test_no_envelope_or_no_window_means_no_admission(tmp_path):
    b = _backend([_turn(content="done")])
    s = OpenTasteSession(model="m", backend=b, log_path=str(tmp_path / "s.jsonl"), experiment_label="t")
    s.exchange("plain")
    assert s._last_admission is None


# --- the recovery loop: one count per send, typed failures fail closed --------


def test_budget_recovery_recounts_the_rebuilt_payload(tmp_path):
    """C1: the resend after a truncation is bounded by its own count.

    `_truncate_largest_tool_results` mutates the conversation and
    `_withdraw_perception` may shrink the tool set, so the `precounted` value
    computed before the recovery describes bytes that are no longer being
    sent. Reusing it bounds the resend on a number nobody measured — which is
    exactly what a door whose whole purpose is to never guess must not do.
    Round-seven items 1 and 3, and the spec's "one count per send".
    """
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    b = _aware([
        _turn(tool_calls=[_tool_call("read", {"path": "README.md"})], prompt_tokens=20000),
        RuntimeError(LLAMA_ERR),
        _turn(content="recovered", prompt_tokens=500),
    ], counts=[20000, 20000, 5000])
    executor.execute = lambda name, args: {"content": "z" * 200_000}  # type: ignore[assignment]
    result = b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
                    experiment_label="t",
                    extra_tools=[TOOL_SCHEMAS["read"], UPDATE_STATE_SCHEMA],
                    tool_executor=executor)
    assert result.raw_output["response"] == "recovered"
    # Three sends, three counts: the recovery resend is not exempt.
    assert len(b.payloads) == 3 and len(b._counter.seen) == 3
    # Each count saw the bytes its send carried.
    for c, p in zip(b._counter.seen, b.payloads):
        assert c["messages"] == p["messages"] and c.get("tools") == p.get("tools")
    # The resend's bound derives from its own count (5000), not the stale one.
    assert b.payloads[-1]["max_tokens"] == 65536 - 1 - 5000
    assert all(pt + p["max_tokens"] < 65536
               for pt, p in zip((20000, 20000, 5000), b.payloads))


def test_a_window_failure_quoting_the_servers_phrasing_never_enters_recovery(tmp_path):
    """I2: window failures are routed by type, never by message text.

    `WindowFailure` subclasses `RuntimeError`, so all three typed failures
    reach the recovery loop's `except RuntimeError`. A `CountUnavailable`
    wrapping a `/tokenize` refusal that quotes the server's own context
    phrasing — the likeliest text for that endpoint to return on an oversized
    body — would be misread as a wall hit and answered with truncate-and-retry
    instead of failing closed (spec §1; round three finding 23).

    The failure has to come from inside `_send`, which is where the loop's
    `try` reaches. Turn 0 counts over the soft threshold, so perception is
    withdrawn and `precounted` is dropped; turn 1 then has perception already
    withdrawn, so it takes no count of its own and `_send` counts — and that
    is the count that fails.
    """
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    quoting = CountUnavailable(
        "request (70000 tokens) exceeds the available context size (65536 tokens)"
    )
    from hamutay.taste_open import _is_context_limit_error
    assert _is_context_limit_error(quoting), "the premise: this text reads as a wall hit"
    b = _aware([
        _turn(tool_calls=[_tool_call("read", {"path": "README.md"})], prompt_tokens=53000),
        _turn(content="never"),
    # Three spare counts after the failing one: today's buggy path retries
    # three times, and the test must fail on the assertion below rather
    # than on an exhausted script.
    ], counts=[53000, 52000, quoting, quoting, quoting, quoting])
    executor.execute = lambda name, args: {"content": "z" * 200_000}  # type: ignore[assignment]
    with pytest.raises(CountUnavailable):
        b.call(model="m", system="s", messages=[{"role": "user", "content": "hi"}],
               experiment_label="t",
               extra_tools=[TOOL_SCHEMAS["read"], UPDATE_STATE_SCHEMA],
               tool_executor=executor)
    # One send only: no second post, and nothing was truncated on the way out.
    assert len(b.payloads) == 1
    assert not _events(executor, "budget_recovery")
    assert _events(executor, "budget_pressure")[-1]["action"] == "count_unavailable"


def test_a_completed_window_aware_wake_records_the_invocation_id(tmp_path):
    """I1: the success path names the invocation the failure path names.

    `_log_entry` writes `context_policy_invocation` on every window-aware
    record, so a success path that does not pass it writes `null` — making a
    completed wake indistinguishable from "no invocation was ever named",
    which is the ambiguity the field exists to remove.
    """
    from hamutay.context_policy import ContextPolicy, ContextPolicyHolder
    holder = ContextPolicyHolder(ContextPolicy(
        65536, "discovered", 65536, "http://127.0.0.1:8081", "probed", {}, 20, "inv-live"))
    b = OpenAITasteBackend(api_key="k", wake_mode="natural", context_policy=holder,
                           max_tokens=64000)
    b.payloads = []
    b._counter = _Counter([100])
    script = [_turn(content="done", prompt_tokens=100)]

    def fake_post(payload):
        b.payloads.append(json.loads(json.dumps(payload)))
        return script.pop(0)

    b._post_chat = fake_post
    log = tmp_path / "s.jsonl"
    s = OpenTasteSession(model="m", backend=b, log_path=str(log), experiment_label="t",
                         enable_tools=True, project_root=tmp_path)
    s.seed_state({"cycle": 1}, 1)
    s.exchange("hi")
    rec = json.loads(log.read_text().splitlines()[-1])
    assert rec["context_policy_invocation"] == "inv-live"
