"""Malformed tool-call arguments are fed back to the model as a tool error and
retried within the wake, instead of failing the wake.

Why: docs/model-sweep-20260827.md — three families in one day failed at the
JSON-argument layer (Haiku: Claude-style XML inside JSON; DeepSeek-flash:
arguments truncated; Qwen-max: the same XML leak). The behavior above was
fine; the wake died below it. Implementer's TDD tests.
"""
import json

import pytest

from hamutay.taste_open import OpenAITasteBackend
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS, UPDATE_STATE_SCHEMA


def _backend(script, **kw):
    backend = OpenAITasteBackend(api_key="k", provider_name="openrouter", **kw)
    backend.payloads = []

    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        return script.pop(0)

    backend._post_chat = fake_post
    return backend


def _turn(content=None, tool_calls=None, finish="stop"):
    return {
        "choices": [{"finish_reason": finish,
                     "message": {"content": content, "tool_calls": tool_calls}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _call(name, raw_arguments, call_id):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": raw_arguments}}


BROKEN = '{"updates": {"a": 1}, "deleted_regions": ["x"]}\n<parameter name="deleted_regions">'
TRUNCATED = '{"updates": {"a": "I hold it as accounts, not gos'


def _tool_messages(payload):
    return [m for m in payload["messages"] if m.get("role") == "tool"]


# --- natural wake ----------------------------------------------------------


def test_natural_wake_feeds_malformed_args_back_and_continues(tmp_path):
    script = [
        _turn(tool_calls=[_call("update_state", BROKEN, "c1")], finish="tool_calls"),
        _turn(tool_calls=[_call("update_state", json.dumps({"updates": {"a": 1}}), "c2")],
              finish="tool_calls"),
        _turn(content="done"),
    ]
    backend = _backend(script, wake_mode="natural")
    ex = ToolExecutor(project_root=tmp_path, cycle=1)
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
                          tool_executor=ex)
    assert result.raw_output == {"response": "done", "a": 1}
    fed_back = _tool_messages(backend.payloads[1])
    assert len(fed_back) == 1
    assert fed_back[0]["tool_call_id"] == "c1"
    assert "malformed" in fed_back[0]["content"].lower()
    malformed = [e for e in ex.activity_log if e.get("malformed_arguments")]
    assert len(malformed) == 1 and malformed[0]["tool"] == "update_state"


def test_natural_wake_truncated_args_are_retried(tmp_path):
    script = [
        _turn(tool_calls=[_call("update_state", TRUNCATED, "c1")], finish="tool_calls"),
        _turn(content="ok without state"),
    ]
    backend = _backend(script, wake_mode="natural")
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
                          tool_executor=ToolExecutor(project_root=tmp_path, cycle=1))
    assert result.raw_output == {"response": "ok without state"}


def test_natural_wake_gives_up_after_three_malformed_calls(tmp_path):
    script = [_turn(tool_calls=[_call("update_state", BROKEN, f"c{i}")],
                    finish="tool_calls") for i in range(4)]
    backend = _backend(script, wake_mode="natural")
    with pytest.raises(RuntimeError, match="malformed.*3"):
        backend.call(model="m", system="s",
                     messages=[{"role": "user", "content": "u"}],
                     experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
                     tool_executor=ToolExecutor(project_root=tmp_path, cycle=1))


# --- terminal wake, multi-turn (residents with tools) ------------------------


def test_terminal_multi_turn_retries_malformed_think_and_respond(tmp_path):
    script = [
        _turn(tool_calls=[_call("think_and_respond", BROKEN, "t1")], finish="tool_calls"),
        _turn(tool_calls=[_call("think_and_respond", json.dumps({"response": "r"}), "t2")],
              finish="tool_calls"),
    ]
    backend = _backend(script)
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t", extra_tools=[TOOL_SCHEMAS["read"]],
                          tool_executor=ToolExecutor(project_root=tmp_path, cycle=1))
    assert result.raw_output == {"response": "r"}
    fed_back = _tool_messages(backend.payloads[1])
    assert fed_back[0]["tool_call_id"] == "t1"
    assert "malformed" in fed_back[0]["content"].lower()


def test_terminal_multi_turn_good_calls_still_run_beside_a_malformed_one(tmp_path):
    (tmp_path / "f.txt").write_text("hello")
    script = [
        _turn(tool_calls=[
            _call("read", json.dumps({"path": "f.txt"}), "r1"),
            _call("update_state", BROKEN, "b1"),
        ], finish="tool_calls"),
        _turn(tool_calls=[_call("think_and_respond", json.dumps({"response": "r"}), "t1")],
              finish="tool_calls"),
    ]
    backend = _backend(script)
    ex = ToolExecutor(project_root=tmp_path, cycle=1)
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t", extra_tools=[TOOL_SCHEMAS["read"]],
                 tool_executor=ex)
    ids = [m["tool_call_id"] for m in _tool_messages(backend.payloads[1])]
    assert ids == ["r1", "b1"]
    assert [e["tool"] for e in ex.activity_log if not e.get("malformed_arguments")] == ["read"]


# --- terminal wake, single tool (no executor: the elder without --tools) -----


def test_single_tool_call_retries_malformed_think_and_respond():
    script = [
        _turn(tool_calls=[_call("think_and_respond", BROKEN, "t1")], finish="tool_calls"),
        _turn(tool_calls=[_call("think_and_respond", json.dumps({"response": "r"}), "t2")],
              finish="tool_calls"),
    ]
    backend = _backend(script)
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t")
    assert result.raw_output == {"response": "r"}
    assert len(backend.payloads) == 2
    assert _tool_messages(backend.payloads[1])[0]["tool_call_id"] == "t1"


def test_single_tool_call_gives_up_after_three_malformed():
    script = [_turn(tool_calls=[_call("think_and_respond", BROKEN, f"t{i}")],
                    finish="tool_calls") for i in range(4)]
    backend = _backend(script)
    with pytest.raises(RuntimeError, match="malformed.*3"):
        backend.call(model="m", system="s",
                     messages=[{"role": "user", "content": "u"}],
                     experiment_label="t")
