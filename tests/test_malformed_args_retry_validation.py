"""Independent adversarial validation of malformed OpenAI tool arguments."""

from __future__ import annotations

import copy
import json
from datetime import datetime

import pytest

from hamutay.taste_open import CapabilityProfile, OpenAITasteBackend
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import UPDATE_STATE_SCHEMA


BROKEN = '{"updates":{"should_not_survive":true}'

PROBE_TOOL = {
    "name": "probe",
    "description": "Record a probe.",
    "input_schema": {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
    },
}


def _call(name: str, arguments: str | dict, call_id: str | None = "call-1") -> dict:
    tool_call = {
        "type": "function",
        "function": {
            "name": name,
            "arguments": (
                json.dumps(arguments) if isinstance(arguments, dict) else arguments
            ),
        },
    }
    if call_id is not None:
        tool_call["id"] = call_id
    return tool_call


def _reply(
    *,
    content: str | None = None,
    calls: list[dict] | None = None,
    finish_reason: str | None = None,
    usage: dict | None = None,
) -> dict:
    if finish_reason is None:
        finish_reason = "tool_calls" if calls else "stop"
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content, "tool_calls": calls},
            }
        ],
        "usage": usage
        if usage is not None
        else {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _scripted_backend(script: list[dict], **kwargs) -> OpenAITasteBackend:
    backend = OpenAITasteBackend(api_key="unused", provider_name="openai", **kwargs)
    backend.payloads = []
    responses = list(script)

    def post(payload: dict) -> dict:
        backend.payloads.append(copy.deepcopy(payload))
        if not responses:
            raise AssertionError("script exhausted")
        return responses.pop(0)

    backend._post_chat = post
    return backend


class RecordingExecutor:
    def __init__(self, cycle: int = 41):
        self._cycle = cycle
        self.activity_log: list[dict] = []
        self.calls: list[tuple[str, dict]] = []

    @property
    def pending_state_updates(self) -> dict:
        return {"updates": {}, "deleted_regions": []}

    def execute(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        event = {"tool": name, "parameters": arguments, "result": {"ok": True}}
        self.activity_log.append(event)
        return event["result"]

    def log_event(self, event: dict) -> None:
        self.activity_log.append(event)


class ExecutorWithoutLogEvent:
    """Smallest natural-wake executor that deliberately has no log_event."""

    def __init__(self):
        self.activity_log: list[dict] = []
        self.calls: list[tuple[str, dict]] = []

    @property
    def pending_state_updates(self) -> dict:
        return {"updates": {}, "deleted_regions": []}

    def execute(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        return {"ok": True}


def _invoke_shape(
    backend: OpenAITasteBackend,
    shape: str,
    tmp_path,
):
    kwargs = {
        "model": "validator-model",
        "system": "system-marker",
        "messages": [{"role": "user", "content": "validate"}],
        "experiment_label": "independent-validation",
    }
    if shape == "single":
        return backend.call(**kwargs)
    executor = ToolExecutor(project_root=tmp_path, cycle=9)
    if shape == "multi":
        return backend.call(
            **kwargs, extra_tools=[PROBE_TOOL], tool_executor=executor
        )
    return backend.call(
        **kwargs, extra_tools=[UPDATE_STATE_SCHEMA], tool_executor=executor
    )


def _malformed_then_recovery_script(shape: str, malformed_count: int) -> list[dict]:
    malformed_name = {
        "single": "think_and_respond",
        "multi": "think_and_respond",
        "natural": "update_state",
    }[shape]
    script = [
        _reply(calls=[_call(malformed_name, BROKEN, f"bad-{index}")])
        for index in range(malformed_count)
    ]
    if shape == "natural":
        script.append(_reply(content="recovered"))
    else:
        script.append(
            _reply(
                calls=[
                    _call(
                        "think_and_respond",
                        {"response": "recovered"},
                        "terminal",
                    )
                ]
            )
        )
    return script


@pytest.mark.parametrize("shape", ["single", "multi", "natural"])
def test_three_malformed_calls_are_allowed_before_recovery(shape, tmp_path):
    backend = _scripted_backend(
        _malformed_then_recovery_script(shape, 3),
        wake_mode="natural" if shape == "natural" else "terminal",
    )

    result = _invoke_shape(backend, shape, tmp_path)

    assert result.raw_output["response"] == "recovered"
    assert len(backend.payloads) == 4


@pytest.mark.parametrize("shape", ["single", "multi", "natural"])
def test_fourth_malformed_call_exceeds_the_cap(shape, tmp_path):
    backend = _scripted_backend(
        _malformed_then_recovery_script(shape, 4),
        wake_mode="natural" if shape == "natural" else "terminal",
    )

    with pytest.raises(RuntimeError, match=r"malformed tool arguments 3 times"):
        _invoke_shape(backend, shape, tmp_path)
    assert len(backend.payloads) == 4


def test_malformed_counter_resets_for_each_call_on_one_backend_instance():
    one_wake = _malformed_then_recovery_script("single", 3)
    backend = _scripted_backend(one_wake + copy.deepcopy(one_wake))
    kwargs = {
        "model": "m",
        "system": "s",
        "messages": [{"role": "user", "content": "u"}],
        "experiment_label": "reset",
    }

    first = backend.call(**kwargs)
    second = backend.call(**kwargs)

    assert first.raw_output == second.raw_output == {"response": "recovered"}
    assert len(backend.payloads) == 8


def test_multi_turn_cap_is_shared_by_terminal_and_peripheral_tools():
    names = ["think_and_respond", "probe", "unknown_tool", "think_and_respond"]
    backend = _scripted_backend(
        [
            _reply(calls=[_call(name, BROKEN, f"mixed-{index}")])
            for index, name in enumerate(names)
        ]
    )
    executor = RecordingExecutor()

    with pytest.raises(RuntimeError, match=r"malformed tool arguments 3 times"):
        backend.call(
            model="m",
            system="s",
            messages=[{"role": "user", "content": "u"}],
            experiment_label="shared-cap",
            extra_tools=[PROBE_TOOL],
            tool_executor=executor,
        )

    assert executor.calls == []
    assert len([e for e in executor.activity_log if e["malformed_arguments"]]) == 3


def test_malformed_terminal_bundled_with_valid_peripheral_executes_peripheral():
    backend = _scripted_backend(
        [
            _reply(
                calls=[
                    _call("think_and_respond", BROKEN, "bad-terminal"),
                    _call("probe", {"value": 7}, "good-probe"),
                ]
            ),
            _reply(
                calls=[
                    _call(
                        "think_and_respond", {"response": "after probe"}, "terminal"
                    )
                ]
            ),
        ]
    )
    executor = RecordingExecutor()

    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "u"}],
        experiment_label="bundle",
        extra_tools=[PROBE_TOOL],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "after probe"}
    assert executor.calls == [("probe", {"value": 7})]
    retry_messages = backend.payloads[1]["messages"]
    assert [tc["id"] for tc in retry_messages[-3]["tool_calls"]] == [
        "bad-terminal",
        "good-probe",
    ]
    assert [message["tool_call_id"] for message in retry_messages[-2:]] == [
        "bad-terminal",
        "good-probe",
    ]


def test_valid_terminal_bundled_with_malformed_peripheral_is_not_returned_early():
    backend = _scripted_backend(
        [
            _reply(
                calls=[
                    _call("probe", BROKEN, "bad-probe"),
                    _call(
                        "think_and_respond",
                        {"response": "premature"},
                        "premature-terminal",
                    ),
                ]
            ),
            _reply(
                calls=[
                    _call(
                        "think_and_respond", {"response": "retried"}, "terminal"
                    )
                ]
            ),
        ]
    )
    executor = RecordingExecutor()

    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "u"}],
        experiment_label="terminal-plus-malformed",
        extra_tools=[PROBE_TOOL],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "retried"}
    assert len(backend.payloads) == 2
    echoed = backend.payloads[1]["messages"][-2]
    assert [tc["id"] for tc in echoed["tool_calls"]] == ["bad-probe"]
    assert backend.payloads[1]["messages"][-1]["tool_call_id"] == "bad-probe"


@pytest.mark.parametrize("shape", ["single", "multi"])
def test_synthetic_id_is_used_in_both_assistant_echo_and_tool_result(shape):
    backend = _scripted_backend(
        [
            _reply(calls=[_call("think_and_respond", BROKEN, None)]),
            _reply(
                calls=[
                    _call("think_and_respond", {"response": "ok"}, "terminal")
                ]
            ),
        ]
    )
    kwargs = {
        "model": "m",
        "system": "s",
        "messages": [{"role": "user", "content": "u"}],
        "experiment_label": "synthetic-id",
    }
    if shape == "multi":
        kwargs.update(extra_tools=[PROBE_TOOL], tool_executor=RecordingExecutor())

    result = backend.call(**kwargs)

    assert result.raw_output == {"response": "ok"}
    retry_messages = backend.payloads[1]["messages"]
    assistant_echo = retry_messages[-2]
    tool_result = retry_messages[-1]
    assert assistant_echo["tool_calls"][0].get("id") == "malformed-1"
    assert tool_result["tool_call_id"] == "malformed-1"


def test_natural_unknown_malformed_call_works_without_log_event_method():
    backend = _scripted_backend(
        [
            _reply(calls=[_call("not_in_the_schema", "{", "mystery")]),
            _reply(content="continued"),
        ],
        wake_mode="natural",
    )
    executor = ExecutorWithoutLogEvent()

    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "u"}],
        experiment_label="unknown-no-logger",
        extra_tools=[PROBE_TOOL],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "continued"}
    assert executor.calls == []
    error = json.loads(backend.payloads[1]["messages"][-1]["content"])["error"]
    assert "malformed JSON arguments for not_in_the_schema" in error


def test_natural_retry_preserves_only_valid_state_and_accounts_for_all_turns(tmp_path):
    usage = [
        {
            "prompt_tokens": 101,
            "completion_tokens": 11,
            "prompt_tokens_details": {"cached_tokens": 20, "cache_write_tokens": 3},
        },
        {
            "prompt_tokens": 202,
            "completion_tokens": 22,
            "prompt_tokens_details": {"cached_tokens": 40, "cache_write_tokens": 5},
        },
        {
            "prompt_tokens": 303,
            "completion_tokens": 33,
            "prompt_tokens_details": {"cached_tokens": 60, "cache_write_tokens": 7},
        },
    ]
    backend = _scripted_backend(
        [
            _reply(
                content="malformed draft",
                calls=[_call("update_state", BROKEN, "bad-state")],
                usage=usage[0],
            ),
            _reply(
                content="valid draft",
                calls=[
                    _call(
                        "update_state",
                        {"updates": {"kept": "valid"}},
                        "good-state",
                    )
                ],
                usage=usage[1],
            ),
            _reply(content="final reply", usage=usage[2]),
        ],
        wake_mode="natural",
    )
    executor = ToolExecutor(project_root=tmp_path, cycle=17)

    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "u"}],
        experiment_label="natural-accounting",
        extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "final reply", "kept": "valid"}
    assert "should_not_survive" not in result.raw_output
    assert result.interim_text == ["malformed draft", "valid draft"]
    assert (result.input_tokens, result.output_tokens) == (606, 66)
    assert (result.cache_read_tokens, result.cache_creation_tokens) == (120, 15)

    malformed_entries = [
        event for event in result.tool_activity if event.get("malformed_arguments")
    ]
    assert len(malformed_entries) == 1
    malformed = malformed_entries[0]
    assert set(malformed) == {
        "cycle",
        "timestamp",
        "tool",
        "malformed_arguments",
        "error",
        "raw_length",
    }
    assert malformed["cycle"] == 17
    assert malformed["tool"] == "update_state"
    assert malformed["malformed_arguments"] is True
    assert malformed["raw_length"] == len(BROKEN)
    assert malformed["error"] and "\n" not in malformed["error"]
    assert datetime.fromisoformat(malformed["timestamp"]).tzinfo is not None

    normally_executed = [
        event for event in result.tool_activity if not event.get("malformed_arguments")
    ]
    assert len(normally_executed) == 1
    assert normally_executed[0]["tool"] == "update_state"
    assert normally_executed[0]["parameters"] == {"updates": {"kept": "valid"}}


def test_single_tool_retries_grow_messages_once_and_keep_resolved_tool_choice():
    resolved_choice = {
        "type": "function",
        "function": {"name": "think_and_respond"},
    }
    backend = _scripted_backend(
        [
            _reply(calls=[_call("think_and_respond", BROKEN, "bad-1")]),
            _reply(calls=[_call("think_and_respond", "{", "bad-2")]),
            _reply(
                calls=[
                    _call(
                        "think_and_respond",
                        {"response": "tool recovery"},
                        "terminal",
                    )
                ]
            ),
        ],
        capability=CapabilityProfile(tool_choice_mode="function_object"),
    )

    result = backend.call(
        model="m",
        system="unique-system",
        messages=[{"role": "user", "content": "u"}],
        experiment_label="single-payload",
    )

    assert result.raw_output == {"response": "tool recovery"}
    assert [len(payload["messages"]) for payload in backend.payloads] == [2, 4, 6]
    for payload in backend.payloads:
        system_messages = [
            message for message in payload["messages"] if message["role"] == "system"
        ]
        assert system_messages == [{"role": "system", "content": "unique-system"}]
        assert payload["tool_choice"] == resolved_choice

    second_request = backend.payloads[1]["messages"]
    assert second_request[-2]["role"] == "assistant"
    assert second_request[-2]["tool_calls"] == [_call("think_and_respond", BROKEN, "bad-1")]
    assert second_request[-1]["tool_call_id"] == "bad-1"
    third_request = backend.payloads[2]["messages"]
    assert [message["tool_call_id"] for message in third_request if message["role"] == "tool"] == [
        "bad-1",
        "bad-2",
    ]


def test_single_tool_content_json_fallback_after_malformed_accepts_null_tool_calls():
    backend = _scripted_backend(
        [
            _reply(calls=[_call("think_and_respond", BROKEN, "bad")]),
            # OpenAI-compatible responses may serialize an unused optional
            # tool_calls field as null rather than omitting it.
            _reply(content='{"response":"content fallback"}', calls=None),
        ]
    )

    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "u"}],
        experiment_label="fallback-after-malformed",
    )

    assert result.raw_output == {"response": "content fallback"}
    assert len(backend.payloads) == 2
