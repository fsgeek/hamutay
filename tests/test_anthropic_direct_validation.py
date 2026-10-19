"""Codex-authored, offline validation of the 2026-10-19 direct-wake spec.

The provider boundary is fake; translation, natural wakes, sessions, ledger,
and budget are real. No test may open the credential file or a socket.
"""

from copy import deepcopy
from datetime import datetime, timezone
import builtins
import io
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from hamutay import anthropic_direct as direct
from hamutay import heartbeat
from hamutay.taste_open import OpenAITasteBackend, resolve_launch
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS
from hamutay.window import TruncatedReply, WakeAccount


MODEL = "claude-haiku-4-5"
KEY = "HAMUTAY_ANTHROPIC_API_KEY"
WORKSPACE = "HAMUTAY_ANTHROPIC_WORKSPACE_ID"
TOOL = {"type": "function", "function": {
    "name": "clock", "description": "Read the clock",
    "parameters": {"type": "object", "properties": {}},
}}
USAGE = {
    "input_tokens": 101, "output_tokens": 29,
    "cache_read_input_tokens": 307, "cache_creation_input_tokens": 211,
    "cache_creation": {"ephemeral_5m_input_tokens": 138, "ephemeral_1h_input_tokens": 73},
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv(KEY, raising=False)
    monkeypatch.delenv(WORKSPACE, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "bogus-general-key-must-not-be-used")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")

    def forbidden(*args, **kwargs):
        pytest.fail("provider construction or network access escaped a fake")

    monkeypatch.setattr(direct.anthropic, "Anthropic", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    for module in (builtins, io):
        original = module.open

        def guarded_open(file, *args, _open=original, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                assert Path(os.fsdecode(file)).name != "anthropic.env", "credential file read"
            return _open(file, *args, **kwargs)

        monkeypatch.setattr(module, "open", guarded_open)


class Dump:
    """Only the SDK's serialization boundary is needed for canned replies."""

    def __init__(self, value):
        self.value = deepcopy(value)

    def model_dump(self, *, exclude_none):
        assert exclude_none is True
        return deepcopy(self.value)


def response(blocks=None, *, stop="end_turn", usage=USAGE):
    return SimpleNamespace(
        id="msg-offline", model=MODEL, stop_reason=stop,
        content=[Dump(b) for b in (blocks if blocks is not None else [{"type": "text", "text": "awake"}])],
        usage=Dump(usage) if usage is not None else None,
    )


class ScriptedClient:
    def __init__(self, *script):
        self.script = iter(script)
        self.requests = []
        self.final_reads = 0
        self.exits = 0
        self.messages = self

    def stream(self, **request):
        self.requests.append(deepcopy(request))
        item = next(self.script)
        if isinstance(item, Exception):
            raise item
        client = self

        class Stream:
            def __enter__(self):
                return self

            def get_final_message(self):
                client.final_reads += 1
                return item

            def __exit__(self, *exc):
                client.exits += 1

        return Stream()


def payload(messages=None, **extra):
    return {
        "model": MODEL, "max_tokens": 48_000,
        "messages": messages if messages is not None else [
            {"role": "system", "content": "constitution"},
            {"role": "user", "content": "hello"},
        ],
        "tools": [deepcopy(TOOL)], "tool_choice": "auto", **extra,
    }


def call(backend, *, model=MODEL, executor=None, tools=None):
    return backend.call(
        model=model, system="constitution", messages=[{"role": "user", "content": "hello"}],
        experiment_label="offline-validation", extra_tools=tools, tool_executor=executor,
    )


def tool_call(identifier, arguments="{}"):
    return {"id": identifier, "type": "function", "function": {"name": "clock", "arguments": arguments}}


def breakpoints(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "cache_control":
                yield path
            else:
                yield from breakpoints(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from breakpoints(child, path + (index,))


# Credentials and launch (spec 1-3).
def test_client_uses_only_house_key_and_workspace(monkeypatch):
    monkeypatch.setenv(KEY, "  fake-house-key  ")
    monkeypatch.setenv(WORKSPACE, "  fake-workspace  ")
    reads = []
    original_get = os._Environ.__getitem__

    def get(env, name):
        reads.append(name)
        return original_get(env, name)

    monkeypatch.setattr(os._Environ, "__getitem__", get)
    captured = []
    sentinel = object()
    monkeypatch.setattr(direct.anthropic, "Anthropic", lambda **kw: captured.append(kw) or sentinel)
    assert direct.anthropic_client_from_env(timeout=731) is sentinel
    assert captured == [{"api_key": "fake-house-key", "default_headers": {
        "anthropic-workspace-id": "fake-workspace"}, "timeout": 731}]
    assert "ANTHROPIC_API_KEY" not in reads


@pytest.mark.parametrize("key,workspace,missing", [
    (None, "fake-workspace", [KEY]), ("fake-key", None, [WORKSPACE]),
    (None, None, [KEY, WORKSPACE]), (" \t", "\n", [KEY, WORKSPACE]),
])
def test_missing_credentials_refuse_even_with_general_key(monkeypatch, key, workspace, missing):
    for name, value in ((KEY, key), (WORKSPACE, workspace)):
        if value is not None:
            monkeypatch.setenv(name, value)
    with pytest.raises(SystemExit) as exc:
        direct.anthropic_client_from_env()
    assert all(name in str(exc.value) for name in missing)
    assert "not set" in str(exc.value)
    backend = direct.AnthropicDirectBackend(wake_mode="natural")
    with pytest.raises(RuntimeError) as wake_error:
        call(backend)
    assert str(wake_error.value) == str(exc.value)


def test_client_is_lazy_and_reused_for_streamed_requests(monkeypatch):
    backend = direct.AnthropicDirectBackend(timeout=7)
    client = ScriptedClient(response(), response())
    constructions = []
    monkeypatch.setattr(direct, "anthropic_client_from_env", lambda **kw: constructions.append(kw) or client)
    for _ in range(2):
        assert backend._post_chat(payload())["choices"][0]["message"]["content"] == "awake"
    assert constructions == [{"timeout": 600.0}]
    assert client.final_reads == client.exits == 2


def heartbeat_args(tmp_path, provider="anthropic", mode="natural"):
    return heartbeat.build_parser().parse_args([
        "--log-path", str(tmp_path / "session.jsonl"), "--project-root", str(tmp_path),
        "--provider", provider, "--model", MODEL, "--wake-mode", mode, "--no-persist",
    ])


@pytest.mark.parametrize("provider", ["anthropic", "openai", "openrouter"])
def test_offline_session_build_marks_every_provider_metered(tmp_path, monkeypatch, capsys, provider):
    monkeypatch.setattr(heartbeat, "source_note", lambda root: "source: offline")
    # Hosted discovery has no llama-server props; keep this boundary offline.
    monkeypatch.setattr("hamutay.taste_open._default_http", lambda *a, **kw: {})
    args = heartbeat_args(tmp_path, provider)
    args.context_limit = 8192
    session, backend, launch = heartbeat.build_session(args)
    assert launch["metered"] is True
    if provider == "anthropic":
        assert isinstance(backend, direct.AnthropicDirectBackend)
        assert backend.wake_mode == "natural"
        assert "!!! anthropic-direct:" in capsys.readouterr().out
        assert backend._client is None


@pytest.mark.parametrize("missing", [(KEY,), (WORKSPACE,), (KEY, WORKSPACE)])
def test_main_refuses_missing_credentials_before_loop(tmp_path, monkeypatch, capsys, missing):
    for name in (KEY, WORKSPACE):
        if name not in missing:
            monkeypatch.setenv(name, "fake-value")
    args = heartbeat_args(tmp_path)
    monkeypatch.setattr(sys, "argv", ["heartbeat"])
    monkeypatch.setattr(heartbeat, "build_parser", lambda: SimpleNamespace(parse_args=lambda: args))
    monkeypatch.setattr(heartbeat.HeartbeatLoop, "run_forever", lambda self: pytest.fail("loop started"))
    monkeypatch.setattr(heartbeat, "source_note", lambda root: "source: offline")
    with pytest.raises(SystemExit) as exc:
        heartbeat.main()
    assert all(name in str(exc.value) for name in missing)
    output = capsys.readouterr().out
    assert "!!! anthropic-direct:" in output and "not set" in output


def test_main_with_credentials_starts_natural_loop_and_names_house_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(KEY, "fake-key")
    monkeypatch.setenv(WORKSPACE, "fake-workspace")
    captured = []
    monkeypatch.setattr(direct.anthropic, "Anthropic", lambda **kw: captured.append(kw) or ScriptedClient())
    args = heartbeat_args(tmp_path)
    monkeypatch.setattr(heartbeat, "build_parser", lambda: SimpleNamespace(parse_args=lambda: args))
    monkeypatch.setattr(heartbeat, "source_note", lambda root: "source: offline")
    loops = []
    monkeypatch.setattr(heartbeat.HeartbeatLoop, "run_forever", lambda self: loops.append(self))
    heartbeat.main()
    assert len(loops) == 1
    assert loops[0]._session._wake_mode == "natural"
    assert captured[0]["api_key"] == "fake-key"
    assert f"anthropic-direct: key {KEY}" in capsys.readouterr().out


# Request translation (spec 4-9).
def test_system_user_and_consecutive_assistant_messages_translate_without_loss():
    request = direct.AnthropicDirectBackend()._translate(payload([
        {"role": "system", "content": [{"type": "text", "text": "first"}, {"type": "text", "text": "second"}]},
        {"role": "user", "content": "u1"}, {"role": "system", "content": "later system"},
        {"role": "user", "content": "u2"}, {"role": "assistant", "content": "a1"},
        {"role": "assistant", "content": "a2"}, {"role": "user", "content": "u3"},
    ]))
    assert [b["text"] for b in request["system"]] == ["first", "second"]
    assert [m["role"] for m in request["messages"]] == ["user", "assistant", "user"]
    assert [[b["text"] for b in m["content"]] for m in request["messages"]] == [
        ["u1", "later system", "u2"], ["a1", "a2"], ["u3"],
    ]


def test_only_first_system_message_is_promoted():
    request = direct.AnthropicDirectBackend()._translate(payload([
        {"role": "system", "content": "constitution"},
        {"role": "system", "content": "later operational note"},
        {"role": "user", "content": "hello"},
    ]))
    assert [b["text"] for b in request["system"]] == ["constitution"]
    assert [b["text"] for b in request["messages"][0]["content"]] == ["later operational note", "hello"]


@pytest.mark.parametrize("raw,expected", [('{"timezone":"UTC"}', {"timezone": "UTC"}),
                                          ('{"broken":', {"_unparsed_arguments": '{"broken":'})])
def test_parallel_tool_calls_and_results_preserve_ids_and_arguments(raw, expected):
    request = direct.AnthropicDirectBackend()._translate(payload([
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "checking", "tool_calls": [tool_call("one", raw), tool_call("two")]},
        {"role": "tool", "tool_call_id": "one", "content": "result one"},
        {"role": "tool", "tool_call_id": "two", "content": "result two"},
    ]))
    assert request["messages"][1]["content"] == [
        {"type": "text", "text": "checking"},
        {"type": "tool_use", "id": "one", "name": "clock", "input": expected},
        {"type": "tool_use", "id": "two", "name": "clock", "input": {}},
    ]
    results = request["messages"][2]
    assert results["role"] == "user"
    assert [(b["tool_use_id"], b["content"]) for b in results["content"]] == [("one", "result one"), ("two", "result two")]


@pytest.mark.parametrize("choice,expected", [
    ("auto", {"type": "auto"}), ("none", {"type": "none"}), ("required", {"type": "any"}),
    ({"type": "function", "function": {"name": "clock"}}, {"type": "tool", "name": "clock"}),
])
def test_tool_choice_mapping_and_schema(choice, expected):
    request = direct.AnthropicDirectBackend()._translate(payload(tool_choice=choice))
    assert request["tool_choice"] == expected
    assert request["tools"] == [{"name": "clock", "description": "Read the clock",
                                  "input_schema": TOOL["function"]["parameters"],
                                  "cache_control": {"type": "ephemeral"}}]


@pytest.mark.parametrize("choice", [
    pytest.param("invalid", id="unknown-string"),
    pytest.param({}, id="empty-object"),
    pytest.param({"type": "tool", "name": "clock"}, id="wrong-shape"),
    pytest.param({"type": "invalid", "function": {"name": "clock"}}, id="invalid-function-type"),
])
def test_invalid_tool_choice_is_rejected(choice):
    with pytest.raises(RuntimeError, match="tool_choice"):
        direct.AnthropicDirectBackend()._translate(payload(tool_choice=choice))


@pytest.mark.parametrize("tools", [None, []])
def test_no_tools_omits_tools_and_choice_even_if_choice_untranslatable(tools):
    request = direct.AnthropicDirectBackend()._translate(payload(tools=tools, tool_choice="invalid"))
    assert "tools" not in request and "tool_choice" not in request


def test_cache_breakpoint_advances_without_accumulating_or_mutating_payload():
    backend = direct.AnthropicDirectBackend()
    source = payload(tools=[deepcopy(TOOL), deepcopy(TOOL)])
    source["tools"][1]["function"]["name"] = "other_clock"
    for turn in range(7):
        before = deepcopy(source)
        request = backend._translate(source)
        assert set(breakpoints(request)) == {
            ("messages", len(request["messages"]) - 1, "content", len(request["messages"][-1]["content"]) - 1),
            ("system", 0), ("tools", 1),
        }
        assert source == before
        assert request["messages"][-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
        source["messages"].extend([
            {"role": "assistant", "content": None, "tool_calls": [tool_call(f"c{turn}")]},
            {"role": "tool", "tool_call_id": f"c{turn}", "content": f"result {turn}"},
        ])


@pytest.mark.parametrize("model,requested,expected", [(MODEL, 47_123, 47_123), (MODEL, 100_000, 64_000),
    ("claude-fable-5", 120_000, 120_000), ("claude-fable-5", 200_000, 128_000),
    ("unpriced-future-model", 177_777, 177_777)])
def test_max_tokens_is_only_clamped_at_model_ceiling(model, requested, expected):
    request = direct.AnthropicDirectBackend()._translate(payload(
        model=model, max_tokens=requested, parallel_tool_calls=True, chat_template_kwargs={"enable_thinking": True},
    ))
    assert request["max_tokens"] == expected
    assert "parallel_tool_calls" not in request and "chat_template_kwargs" not in request


# Thinking replay and response translation (spec 10-14).
def thinking_turn(prefix):
    return [
        {"type": "thinking", "thinking": f"private {prefix}\n\u2603", "signature": f"signed-{prefix}"},
        {"type": "redacted_thinking", "data": f"opaque-{prefix}"},
        {"type": "text", "text": f"checking {prefix}"},
        {"type": "tool_use", "id": f"{prefix}-one", "name": "clock", "input": {}},
        {"type": "tool_use", "id": f"{prefix}-two", "name": "clock", "input": {}},
    ]


def test_natural_wake_replays_full_thinking_across_multiple_round_trips(tmp_path):
    first, second = thinking_turn("first"), thinking_turn("second")
    client = ScriptedClient(response(first, stop="tool_use"), response(second, stop="tool_use"), response())
    backend = direct.AnthropicDirectBackend(client=client, wake_mode="natural")
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    result = call(backend, executor=executor, tools=[TOOL_SCHEMAS["clock"]])
    assert result.raw_output["response"] == "awake"
    for index, expected in [(1, [first]), (2, [first, second])]:
        actual = [m["content"] for m in client.requests[index]["messages"] if m["role"] == "assistant"]
        assert actual == expected
        assert len(list(breakpoints(client.requests[index]))) == 3
    assert result.input_tokens == 3 * (101 + 307 + 211)
    assert result.cache_read_tokens == 3 * 307
    assert result.cache_creation_tokens == 3 * 211
    assert result.cost_turns_unreported == 0
    assert result.cost_usd == pytest.approx(3 * 0.0005952)
    assert backend._turn_blocks == {}


def test_parallel_thinking_turn_is_replayable_by_either_tool_id_then_cleared():
    backend = direct.AnthropicDirectBackend()
    blocks = thinking_turn("held")
    translated = backend._untranslate(MODEL, response(blocks, stop="tool_use"))
    for tc in translated["choices"][0]["message"]["tool_calls"]:
        request = backend._translate(payload([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "lossy reconstruction", "tool_calls": [tc]},
            {"role": "tool", "tool_call_id": tc["id"], "content": "ok"},
        ]))
        assert request["messages"][1]["content"] == blocks
    backend._untranslate(MODEL, response())
    assert backend._turn_blocks == {}


@pytest.mark.parametrize("stop,expected", [("end_turn", "stop"), ("stop_sequence", "stop"),
    ("tool_use", "tool_calls"), ("max_tokens", "length"), ("refusal", "content_filter"), ("future_stop", "future_stop")])
def test_stop_reason_mapping(stop, expected):
    result = direct.AnthropicDirectBackend()._untranslate(MODEL, response(stop=stop))
    assert result["choices"][0]["finish_reason"] == expected
    assert result["anthropic_stop_reason"] == stop


def test_truncation_is_accounted_then_raised():
    backend = direct.AnthropicDirectBackend()
    data = backend._untranslate(MODEL, response(stop="max_tokens"))
    account = WakeAccount()
    with pytest.raises(TruncatedReply) as exc:
        backend._take_response(data, account, turn_index=2)
    assert exc.value.account is account
    assert account.responses == [data]
    assert account.input_tokens == 619
    assert account.output_tokens == 29


def test_refusal_cannot_end_a_natural_wake():
    client = ScriptedClient(response(stop="refusal"))
    with pytest.raises(RuntimeError, match="content_filter"):
        call(direct.AnthropicDirectBackend(client=client, wake_mode="natural"))


def test_usage_counts_all_input_kinds_and_retains_raw_usage_and_text():
    result = direct.AnthropicDirectBackend()._untranslate(MODEL, response([
        {"type": "text", "text": "one"}, {"type": "text", "text": "two"},
    ]))
    assert result["choices"][0]["message"]["content"] == "one\ntwo"
    assert result["usage"]["prompt_tokens"] == 619
    assert result["usage"]["completion_tokens"] == 29
    assert result["usage"]["prompt_tokens_details"] == {"cached_tokens": 307, "cache_write_tokens": 211}
    assert result["usage"]["anthropic_usage"] == USAGE
    assert result["usage"]["cost_source"] == "anthropic_token_estimate"


@pytest.mark.parametrize("usage,expected", [
    (USAGE, (101 + 138 * 1.25 + 73 * 2 + 307 * .1 + 29 * 5) / 1e6),
    ({"cache_creation_input_tokens": 100}, 125 / 1e6),
    ({"cache_creation_input_tokens": 100, "cache_creation": {"ephemeral_1h_input_tokens": 100}}, 200 / 1e6),
    ({}, 0.0),
])
def test_price_usage_charges_each_token_kind_once(usage, expected):
    assert direct.price_usage(MODEL, usage) == pytest.approx(expected)


def test_unpriced_model_is_unmeasured_never_free_through_natural_wake(capsys):
    assert direct.price_usage("unpriced-model", USAGE) is None
    backend = direct.AnthropicDirectBackend(client=ScriptedClient(response()), wake_mode="natural")
    result = call(backend, model="unpriced-model")
    assert result.cost_usd is None
    assert result.cost_turns_unreported == 1
    warning = capsys.readouterr().err
    assert "!!!" in warning and "unpriced-model" in warning and "UNMEASURED" in warning
    data = backend._untranslate("unpriced-model", response())
    assert "cost" not in data["usage"]
    assert OpenAITasteBackend._cost_kwargs([data])["cost_usd"] is None


def status_error():
    request = httpx.Request("POST", "https://offline.invalid/v1/messages")
    return anthropic.BadRequestError("prompt is too long", response=httpx.Response(400, request=request), body=None)


@pytest.mark.parametrize("error,match", [
    (status_error(), "400: prompt is too long"),
    (anthropic.APIConnectionError(request=httpx.Request("POST", "https://offline.invalid")), "transport failed"),
])
def test_api_errors_become_runtime_errors(error, match):
    backend = direct.AnthropicDirectBackend(client=ScriptedClient(error))
    with pytest.raises(RuntimeError, match=match):
        backend._post_chat(payload())


def test_context_error_triggers_natural_loop_truncation_and_retry(tmp_path, monkeypatch):
    blocks = [{"type": "tool_use", "id": "large", "name": "clock", "input": {}}]
    client = ScriptedClient(response(blocks, stop="tool_use"), status_error(), response())
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    monkeypatch.setattr(executor, "execute", lambda *args: {"content": "large result " * 100_000})
    backend = direct.AnthropicDirectBackend(client=client, wake_mode="natural")
    result = call(backend, executor=executor, tools=[TOOL_SCHEMAS["clock"]])
    assert result.raw_output["response"] == "awake"
    assert len(client.requests) == 3
    def tool_result(request):
        return next(b["content"] for m in request["messages"] for b in m["content"] if b["type"] == "tool_result")
    assert len(tool_result(client.requests[2])) < len(tool_result(client.requests[1]))
    assert "tools" not in client.requests[2]


# Durable metering and restart compatibility (spec 15-16).
@pytest.mark.parametrize("model,expected_cost,unmeasured", [(MODEL, .0005952, 0), ("unpriced-model", None, 1)])
def test_direct_wake_cost_reaches_session_ledger_and_wake_budget(tmp_path, monkeypatch, model, expected_cost, unmeasured):
    args = heartbeat_args(tmp_path)
    args.model = model
    monkeypatch.setattr(heartbeat, "source_note", lambda root: "source: offline")
    session, backend, launch = heartbeat.build_session(args)
    backend._client = ScriptedClient(response())
    session.exchange("hello")
    record = json.loads(Path(args.log_path).read_text().splitlines()[-1])
    assert record["launch"]["metered"] is True
    if expected_cost is None:
        assert record["usage"]["cost_usd"] is None
    else:
        assert record["usage"]["cost_usd"] == pytest.approx(expected_cost)
    now = datetime.fromisoformat(record["timestamp"])
    day = heartbeat.DailyLedger(args.log_path).day(now)
    assert day["wakes"] == 1 and day["unmeasured_wakes"] == unmeasured
    assert day["cost_usd"] == pytest.approx(expected_cost or 0)
    assert heartbeat.WakeBudget(10, 1).exceeded(day) == "wakes"
    assert heartbeat.WakeBudget(.0005, 10).exceeded(day) == ("cost" if expected_cost else None)


@pytest.mark.parametrize("flag", [None, False, 1, "true"])
def test_legacy_anthropic_records_stay_unmetered_without_boolean_true(tmp_path, flag):
    launch = {"provider": "anthropic"}
    if flag is not None:
        launch["metered"] = flag
    records = [{"timestamp": "2026-10-19T01:00:00Z", "cycle": i, "launch": launch, "usage": usage}
               for i, usage in enumerate([{"cost_usd": 999}, {"cost_usd": None, "cost_turns_unreported": 3}], 1)]
    log = tmp_path / "legacy.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in records))
    day = heartbeat.DailyLedger(str(log)).day(datetime(2026, 10, 19, tzinfo=timezone.utc))
    assert day == {"day": "2026-10-19", "wakes": 2, "cost_usd": 0.0,
                   "unmeasured_wakes": 0, "cost_turns_unreported": 0}


def test_metered_flag_does_not_create_substrate_change_but_compared_fields_do():
    old = {"model": MODEL, "provider": "anthropic", "tools": True, "wake_mode": "natural", "base_url": None,
           "source_cycle": 3}
    resolved, notes = resolve_launch({**old, "metered": True}, old)
    assert "metered" not in resolved
    assert not any("CHANGE" in note for note in notes)
    for field, value in {"model": "new-model", "provider": "openai", "tools": False,
                         "wake_mode": "terminal", "base_url": "https://offline.invalid"}.items():
        _, changed = resolve_launch({**old, "metered": True, field: value}, old)
        assert sum("CHANGE:" in note for note in changed) == 1
