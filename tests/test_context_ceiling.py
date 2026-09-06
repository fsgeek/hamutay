"""The natural-shape loop must know its substrate's context ceiling.

Spec: docs/superpowers/specs/2026-09-06-local-substrate-door-design.md §5.
Found live 2026-09-06: the local Qwen door's first probe wake grew to
68,025 tokens of context in one wake and died on llama-server's
exceed_context_size_error at 65,536. The Anthropic backend already closes a
cycle at 80% of a known limit and recovers from over-limit errors; the
OpenAI natural loop did neither.
"""

import json

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
    # The resident is told, once, in a system message appended to the conversation.
    notes = [m for m in second["messages"] if m["role"] == "system"
             and "context" in m["content"].lower() and "withdrawn" in m["content"].lower()]
    assert len(notes) == 1
    assert "850" in notes[0]["content"] and "1000" in notes[0]["content"]
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
