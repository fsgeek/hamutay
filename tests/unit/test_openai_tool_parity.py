"""OpenAI-compatible multi-turn tool-loop parity tests."""

from __future__ import annotations

import copy
import json

import pytest

from hamutay.taste_open import OpenAITasteBackend


READ_TOOL = {
    "name": "read",
    "description": "Read a file.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

CLOCK_TOOL = {
    "name": "clock",
    "description": "Get time.",
    "input_schema": {"type": "object", "properties": {}},
}


def _tool_call(call_id: str, name: str, arguments: dict | str) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": (
                json.dumps(arguments) if isinstance(arguments, dict) else arguments
            ),
        },
    }


def _response(tool_calls: list[dict], *, finish_reason: str = "tool_calls") -> dict:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": None, "tool_calls": tool_calls},
            }
        ],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }


class ScriptedOpenAIBackend(OpenAITasteBackend):
    def __init__(self, script: list[dict]):
        super().__init__(
            base_url="https://example.invalid/v1",
            api_key="test",
            max_retries=0,
        )
        self._script = list(script)
        self.payloads: list[dict] = []

    def _post_with_retry(self, url: str, payload: dict, headers: dict) -> dict:
        del url, headers
        self.payloads.append(copy.deepcopy(payload))
        if not self._script:
            raise AssertionError("script exhausted")
        return self._script.pop(0)


class FakeToolExecutor:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.activity_log: list[dict] = []

    def execute(self, name: str, tool_input: dict) -> dict:
        self.calls.append((name, tool_input))
        result = {"ok": True, "tool": name, "input": tool_input}
        self.activity_log.append(
            {
                "tool": name,
                "parameters": tool_input,
                "result_summary": f"{name} ok",
                "result": result,
            }
        )
        return result


class FailingToolExecutor(FakeToolExecutor):
    def execute(self, name: str, tool_input: dict) -> dict:
        self.calls.append((name, tool_input))
        result = {"error": "tool rejected request"}
        self.activity_log.append(
            {
                "tool": name,
                "parameters": tool_input,
                "result_summary": "error: tool rejected request",
                "result": result,
            }
        )
        return result


def test_single_tool_compatibility_uses_think_and_respond_only():
    backend = ScriptedOpenAIBackend(
        [_response([_tool_call("tr_1", "think_and_respond", {"response": "ok"})])]
    )

    result = backend.call(
        model="test-model",
        system="system",
        messages=[{"role": "user", "content": "hello"}],
        experiment_label="test",
    )

    assert result.raw_output == {"response": "ok"}
    tools = backend.payloads[0]["tools"]
    assert [tool["function"]["name"] for tool in tools] == ["think_and_respond"]


def test_openai_backend_sends_extra_tools_and_resolves_serial_tool_call():
    backend = ScriptedOpenAIBackend(
        [
            _response([_tool_call("read_1", "read", {"path": "README.md"})]),
            _response(
                [_tool_call("tr_1", "think_and_respond", {"response": "saw it"})]
            ),
        ]
    )
    executor = FakeToolExecutor()

    result = backend.call(
        model="test-model",
        system="system",
        messages=[{"role": "user", "content": "read"}],
        experiment_label="test",
        extra_tools=[READ_TOOL],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "saw it"}
    assert result.tool_activity == executor.activity_log
    assert executor.calls == [("read", {"path": "README.md"})]
    sent_tools = [tool["function"]["name"] for tool in backend.payloads[0]["tools"]]
    assert sent_tools == ["think_and_respond", "read"]
    second_messages = backend.payloads[1]["messages"]
    assert second_messages[-2]["role"] == "assistant"
    assert second_messages[-2]["tool_calls"][0]["id"] == "read_1"
    assert second_messages[-1]["role"] == "tool"
    assert second_messages[-1]["tool_call_id"] == "read_1"


def test_openai_backend_resolves_parallel_tool_calls():
    backend = ScriptedOpenAIBackend(
        [
            _response(
                [
                    _tool_call("read_1", "read", {"path": "a.txt"}),
                    _tool_call("clock_1", "clock", {}),
                ]
            ),
            _response(
                [_tool_call("tr_1", "think_and_respond", {"response": "done"})]
            ),
        ]
    )
    executor = FakeToolExecutor()

    backend.call(
        model="test-model",
        system="system",
        messages=[{"role": "user", "content": "inspect"}],
        experiment_label="test",
        extra_tools=[READ_TOOL, CLOCK_TOOL],
        tool_executor=executor,
    )

    assert executor.calls == [("read", {"path": "a.txt"}), ("clock", {})]
    tool_messages = [
        message
        for message in backend.payloads[1]["messages"]
        if message["role"] == "tool"
    ]
    assert [message["tool_call_id"] for message in tool_messages] == [
        "read_1",
        "clock_1",
    ]


def test_openai_backend_routes_unknown_tool_calls_through_executor():
    backend = ScriptedOpenAIBackend(
        [
            _response([_tool_call("mystery_1", "mystery", {"x": 1})]),
            _response(
                [_tool_call("tr_1", "think_and_respond", {"response": "done"})]
            ),
        ]
    )
    executor = FakeToolExecutor()

    backend.call(
        model="test-model",
        system="system",
        messages=[{"role": "user", "content": "inspect"}],
        experiment_label="test",
        extra_tools=[READ_TOOL],
        tool_executor=executor,
    )

    assert executor.calls == [("mystery", {"x": 1})]


def test_openai_backend_executes_nonterminal_tools_alongside_terminal_call():
    backend = ScriptedOpenAIBackend(
        [
            _response(
                [
                    _tool_call("read_1", "read", {"path": "a.txt"}),
                    _tool_call("tr_1", "think_and_respond", {"response": "done"}),
                ]
            ),
        ]
    )
    executor = FakeToolExecutor()

    result = backend.call(
        model="test-model",
        system="system",
        messages=[{"role": "user", "content": "inspect"}],
        experiment_label="test",
        extra_tools=[READ_TOOL],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "done"}
    assert executor.calls == [("read", {"path": "a.txt"})]


def test_openai_backend_rejects_failed_terminal_batch_tool_call():
    backend = ScriptedOpenAIBackend(
        [
            _response(
                [
                    _tool_call("read_1", "read", {"path": "missing.txt"}),
                    _tool_call("tr_1", "think_and_respond", {"response": "done"}),
                ]
            ),
        ]
    )
    executor = FailingToolExecutor()

    with pytest.raises(RuntimeError, match="Terminal-batch tool call failed"):
        backend.call(
            model="test-model",
            system="system",
            messages=[{"role": "user", "content": "inspect"}],
            experiment_label="test",
            extra_tools=[READ_TOOL],
            tool_executor=executor,
        )

    assert executor.calls == [("read", {"path": "missing.txt"})]


def test_openai_backend_length_finish_reason_raises():
    backend = ScriptedOpenAIBackend(
        [
            _response(
                [_tool_call("tr_1", "think_and_respond", {"response": "partial"})],
                finish_reason="length",
            )
        ]
    )

    with pytest.raises(RuntimeError, match="finish_reason=length"):
        backend.call(
            model="test-model",
            system="system",
            messages=[{"role": "user", "content": "hello"}],
            experiment_label="test",
        )


def test_openai_backend_malformed_tool_arguments_raise_clear_error():
    backend = ScriptedOpenAIBackend(
        [_response([_tool_call("read_1", "read", '{"path":')])]
    )

    with pytest.raises(RuntimeError, match="malformed JSON arguments for read"):
        backend.call(
            model="test-model",
            system="system",
            messages=[{"role": "user", "content": "read"}],
            experiment_label="test",
            extra_tools=[READ_TOOL],
            tool_executor=FakeToolExecutor(),
        )


def test_openai_backend_provider_error_payload_propagates():
    payload = {
        "error": {
            "message": "No provider satisfies provider.require_parameters",
            "code": 400,
        }
    }
    backend = ScriptedOpenAIBackend([payload])

    with pytest.raises(RuntimeError, match="require_parameters"):
        backend.call(
            model="test-model",
            system="system",
            messages=[{"role": "user", "content": "hello"}],
            experiment_label="test",
            extra_tools=[READ_TOOL],
            tool_executor=FakeToolExecutor(),
        )
