"""OpenRouter prompt caching for the OpenAI-compatible backend.

Why: the wake-mode spike (docs/wake-mode-preregistration-20260827.md) showed
cache_read=0 on all 64 wakes and a natural wake re-sending its growing
context once per tool round-trip. OpenRouter's automatic mode (top-level
cache_control, breakpoint advanced as the conversation grows) targets
exactly that intra-wake repetition. Implementer's TDD tests.
"""
import json

from hamutay.taste_open import OpenAITasteBackend
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS, UPDATE_STATE_SCHEMA


def _backend(script, **kw):
    backend = OpenAITasteBackend(api_key="k", **kw)
    backend.payloads = []

    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        return script.pop(0)

    backend._post_chat = fake_post
    return backend


def _turn(content=None, tool_calls=None, finish="stop", usage=None):
    return {
        "choices": [{"finish_reason": finish,
                     "message": {"content": content, "tool_calls": tool_calls}}],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _tool_call(name, args, call_id):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def _think(cid="t1"):
    return _tool_call("think_and_respond", {"response": "r"}, cid)


# --- the request carries the caching directive ------------------------------


def test_openrouter_payload_requests_automatic_caching_by_default():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openrouter")
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t")
    assert backend.payloads[0]["cache_control"] == {"type": "ephemeral"}


def test_openrouter_caching_ttl_is_configurable():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openrouter", openrouter_cache_ttl="1h")
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t")
    assert backend.payloads[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_openrouter_caching_can_be_disabled():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openrouter", openrouter_cache=False)
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t")
    assert "cache_control" not in backend.payloads[0]


def test_non_openrouter_provider_sends_no_cache_control():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openai")
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t")
    assert "cache_control" not in backend.payloads[0]


def test_natural_wake_sends_cache_control_on_every_round_trip(tmp_path):
    script = [
        _turn(tool_calls=[_tool_call("update_state", {"updates": {"a": 1}}, "c1")],
              finish="tool_calls"),
        _turn(content="done"),
    ]
    backend = _backend(script, provider_name="openrouter", wake_mode="natural")
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
                 tool_executor=ToolExecutor(project_root=tmp_path, cycle=1))
    assert [p.get("cache_control") for p in backend.payloads] == [
        {"type": "ephemeral"}, {"type": "ephemeral"},
    ]


# --- the response's cache accounting reaches ExchangeResult -----------------


def _usage(prompt, completion, cached=0, written=0):
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "prompt_tokens_details": {
            "cached_tokens": cached,
            "cache_write_tokens": written,
        },
    }


def test_natural_wake_sums_cache_reads_and_writes_across_turns(tmp_path):
    script = [
        _turn(tool_calls=[_tool_call("update_state", {"updates": {"a": 1}}, "c1")],
              finish="tool_calls", usage=_usage(1000, 20, cached=0, written=900)),
        _turn(content="done", usage=_usage(1200, 30, cached=900, written=100)),
    ]
    backend = _backend(script, provider_name="openrouter", wake_mode="natural")
    result = backend.call(
        model="m", system="s", messages=[{"role": "user", "content": "u"}],
        experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )
    assert result.input_tokens == 2200
    assert result.cache_read_tokens == 900
    assert result.cache_creation_tokens == 1000


def test_terminal_multi_turn_sums_cache_reads_and_writes(tmp_path):
    (tmp_path / "f.txt").write_text("x")
    script = [
        _turn(tool_calls=[_tool_call("read", {"path": "f.txt"}, "c1")],
              finish="tool_calls", usage=_usage(500, 10, written=400)),
        _turn(tool_calls=[_think()], finish="tool_calls",
              usage=_usage(600, 40, cached=400)),
    ]
    backend = _backend(script, provider_name="openrouter")
    result = backend.call(
        model="m", system="s", messages=[{"role": "user", "content": "u"}],
        experiment_label="t", extra_tools=[TOOL_SCHEMAS["read"]],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )
    assert result.cache_read_tokens == 400
    assert result.cache_creation_tokens == 400


def test_single_tool_call_reports_cache_reads():
    backend = _backend(
        [_turn(tool_calls=[_think()], finish="tool_calls",
               usage=_usage(300, 5, cached=250))],
        provider_name="openrouter",
    )
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t")
    assert result.cache_read_tokens == 250


def test_missing_cache_details_read_as_zero():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openrouter")
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t")
    assert result.cache_read_tokens == 0
    assert result.cache_creation_tokens == 0


# --- heartbeat exposes it, on by default ------------------------------------


def test_heartbeat_parser_cache_flags_default_on():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x.jsonl"])
    assert args.no_openrouter_cache is False
    assert args.openrouter_cache_ttl == "5m"
