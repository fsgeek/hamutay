"""Independent validation of budget-note roles in OpenAI natural wakes."""

import copy
import json

from hamutay.taste_open import OpenAITasteBackend
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import (
    DECLARE_QUIET_SCHEMA,
    TOOL_SCHEMAS,
    UPDATE_STATE_SCHEMA,
)


CONTEXT_LIMIT_ERROR = (
    "OpenAI backend error: {'code': 400, 'message': 'request (68025 tokens) "
    "exceeds the available context size (65536 tokens), try increasing it', "
    "'type': 'exceed_context_size_error', 'n_prompt_tokens': 68025, "
    "'n_ctx': 65536}"
)


def _backend(script, *, context_limit):
    backend = OpenAITasteBackend(
        api_key="validation-key",
        wake_mode="natural",
        context_limit=context_limit,
    )
    backend.payloads = []
    remaining = list(script)

    def fake_post(payload):
        backend.payloads.append(copy.deepcopy(payload))
        response = remaining.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    backend._post_chat = fake_post
    return backend


def _tool_call(name, arguments, call_id="validation-call"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _turn(*, content=None, tool_calls=None, prompt_tokens):
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                },
            }
        ],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": 10},
    }


def _tools():
    return [
        TOOL_SCHEMAS["read"],
        TOOL_SCHEMAS["clock"],
        TOOL_SCHEMAS["bash"],
        TOOL_SCHEMAS["schedule_event"],
        UPDATE_STATE_SCHEMA,
        DECLARE_QUIET_SCHEMA,
    ]


def _assert_leading_system_message_only(payloads):
    for payload in payloads:
        system_positions = [
            index
            for index, message in enumerate(payload["messages"])
            if message["role"] == "system"
        ]
        assert system_positions == [0]


def _assert_single_user_budget_note(payloads, *, measured_tokens, ceiling):
    notes = [
        message
        for payload in payloads
        for message in payload["messages"]
        if "Operational note from the harness:" in str(message.get("content", ""))
    ]
    assert len(notes) == 1
    assert notes[0]["role"] == "user"
    assert "withdrawn" in notes[0]["content"].lower()
    assert str(measured_tokens) in notes[0]["content"]
    assert str(ceiling) in notes[0]["content"]


def test_soft_threshold_keeps_system_role_first_and_delivers_one_budget_note(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    backend = _backend(
        [
            _turn(
                tool_calls=[_tool_call("clock", {})],
                prompt_tokens=850,
            ),
            _turn(content="closing", prompt_tokens=870),
        ],
        context_limit=1000,
    )

    result = backend.call(
        model="validation-model",
        system="validation system prompt",
        messages=[{"role": "user", "content": "begin"}],
        experiment_label="budget-note-role-validation",
        extra_tools=_tools(),
        tool_executor=executor,
    )

    assert result.raw_output["response"] == "closing"
    assert len(backend.payloads) == 2
    _assert_leading_system_message_only(backend.payloads)
    _assert_single_user_budget_note(
        backend.payloads,
        measured_tokens=850,
        ceiling=1000,
    )


def test_over_limit_retry_keeps_system_role_first_and_delivers_one_budget_note(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    executor.execute = lambda name, arguments: {"content": "z" * 200_000}
    backend = _backend(
        [
            _turn(
                tool_calls=[_tool_call("read", {"path": "README.md"})],
                prompt_tokens=100,
            ),
            RuntimeError(CONTEXT_LIMIT_ERROR),
            _turn(content="recovered", prompt_tokens=500),
        ],
        context_limit=65536,
    )

    result = backend.call(
        model="validation-model",
        system="validation system prompt",
        messages=[{"role": "user", "content": "begin"}],
        experiment_label="budget-note-role-validation",
        extra_tools=_tools(),
        tool_executor=executor,
    )

    assert result.raw_output["response"] == "recovered"
    assert len(backend.payloads) == 3
    retry = backend.payloads[-1]
    tool_messages = [message for message in retry["messages"] if message["role"] == "tool"]
    assert len(tool_messages) == 1
    assert len(tool_messages[0]["content"]) < 200_000
    assert sorted(tool["function"]["name"] for tool in retry["tools"]) == [
        "declare_quiet",
        "schedule_event",
        "update_state",
    ]
    _assert_leading_system_message_only(backend.payloads)
    _assert_single_user_budget_note(
        backend.payloads,
        measured_tokens=68025,
        ceiling=65536,
    )
