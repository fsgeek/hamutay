"""Independent validation of OpenRouter per-wake cost accounting."""

import json

import pytest

from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS, UPDATE_STATE_SCHEMA


_MISSING = object()


def _backend(script, **kwargs):
    backend = OpenAITasteBackend(api_key="validation-key", **kwargs)
    backend.payloads = []
    responses = list(script)

    def fake_post(payload):
        backend.payloads.append(json.loads(json.dumps(payload)))
        return responses.pop(0)

    backend._post_chat = fake_post
    return backend


def _response(*, content=None, tool_calls=None, finish="stop", usage=_MISSING, gen_id=_MISSING):
    response = {
        "choices": [
            {
                "finish_reason": finish,
                "message": {"content": content, "tool_calls": tool_calls},
            }
        ]
    }
    if usage is _MISSING:
        response["usage"] = {"prompt_tokens": 3, "completion_tokens": 2}
    else:
        response["usage"] = usage
    if gen_id is not _MISSING:
        response["id"] = gen_id
    return response


def _usage(cost=_MISSING):
    usage = {"prompt_tokens": 3, "completion_tokens": 2}
    if cost is not _MISSING:
        usage["cost"] = cost
    return usage


def _tool_call(name, arguments, call_id):
    encoded = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": encoded},
    }


def _think(arguments=None, call_id="think-1"):
    return _tool_call(
        "think_and_respond",
        {"response": "done"} if arguments is None else arguments,
        call_id,
    )


def _call(backend, **kwargs):
    return backend.call(
        model="validation-model",
        system="system",
        messages=[{"role": "user", "content": "hello"}],
        experiment_label="validation",
        **kwargs,
    )


def _terminal_surface():
    return {
        "tool_name": "complete_task",
        "description": "Complete the task.",
        "input_schema": {
            "type": "object",
            "properties": {"response": {"type": "string"}},
            "required": ["response"],
        },
        "tool_choice": "auto",
        "state_update": {"response_field": "response", "copy": {}, "set": {}},
    }


def test_single_tool_malformed_retry_counts_both_http_responses():
    backend = _backend(
        [
            _response(
                tool_calls=[_think("{", "bad-call")],
                finish="tool_calls",
                usage=_usage(0.11),
                gen_id="gen-malformed",
            ),
            _response(
                tool_calls=[_think(call_id="good-call")],
                finish="tool_calls",
                usage=_usage(0.23),
                gen_id="gen-retry",
            ),
        ],
        provider_name="openrouter",
    )

    result = _call(backend)

    assert result.cost_usd == pytest.approx(0.34)
    assert result.cost_turns_unreported == 0
    assert result.generation_ids == ["gen-malformed", "gen-retry"]
    assert [payload["usage"] for payload in backend.payloads] == [
        {"include": True},
        {"include": True},
    ]


def test_terminal_multi_turn_malformed_retry_counts_both_http_responses(tmp_path):
    backend = _backend(
        [
            _response(
                tool_calls=[_tool_call("read", "{", "bad-read")],
                finish="tool_calls",
                usage=_usage(0.07),
                gen_id="gen-bad-read",
            ),
            _response(
                tool_calls=[_think()],
                finish="tool_calls",
                usage=_usage(0.13),
                gen_id="gen-terminal",
            ),
        ],
        provider_name="openrouter",
    )

    result = _call(
        backend,
        extra_tools=[TOOL_SCHEMAS["read"]],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )

    assert result.cost_usd == pytest.approx(0.20)
    assert result.generation_ids == ["gen-bad-read", "gen-terminal"]
    assert all(payload["usage"] == {"include": True} for payload in backend.payloads)


def test_natural_malformed_retry_counts_both_and_reapplies_usage(tmp_path):
    backend = _backend(
        [
            _response(
                tool_calls=[_tool_call("update_state", "{", "bad-update")],
                finish="tool_calls",
                usage=_usage(0.03),
                gen_id="gen-bad-update",
            ),
            _response(
                content="finished",
                usage=_usage(0.05),
                gen_id="gen-natural-final",
            ),
        ],
        provider_name="openrouter",
        wake_mode="natural",
        openrouter_require_parameters=True,
        openrouter_transforms=[],
    )

    result = _call(
        backend,
        extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )

    assert result.cost_usd == pytest.approx(0.08)
    assert result.generation_ids == ["gen-bad-update", "gen-natural-final"]
    assert all(payload["usage"] == {"include": True} for payload in backend.payloads)
    assert all(payload["provider"] == {"require_parameters": True} for payload in backend.payloads)
    assert all(payload["transforms"] == [] for payload in backend.payloads)


def test_single_tool_json_content_fallback_preserves_cost_metadata():
    backend = _backend(
        [
            _response(
                content='prefix {"response": "fallback"} suffix',
                usage=_usage(0.19),
                gen_id="gen-content",
            )
        ],
        provider_name="openrouter",
    )

    result = _call(backend)

    assert result.raw_output == {"response": "fallback"}
    assert result.cost_usd == pytest.approx(0.19)
    assert result.cost_turns_unreported == 0
    assert result.generation_ids == ["gen-content"]


def test_terminal_surface_json_content_fallback_preserves_cost_metadata():
    backend = _backend(
        [
            _response(
                content='{"name":"complete_task","parameters":{"response":"ok"}}',
                usage=_usage(0.17),
                gen_id="gen-terminal-content",
            )
        ],
        provider_name="openrouter",
    )

    result = backend.call_terminal_surface(
        model="validation-model",
        system="system",
        messages=[{"role": "user", "content": "hello"}],
        experiment_label="validation",
        terminal_surface=_terminal_surface(),
    )

    assert result.raw_output == {"response": "ok"}
    assert result.cost_usd == pytest.approx(0.17)
    assert result.generation_ids == ["gen-terminal-content"]
    assert backend.payloads[0]["usage"] == {"include": True}


def test_bool_and_string_costs_are_unreported_and_non_string_ids_are_ignored(tmp_path):
    backend = _backend(
        [
            _response(
                tool_calls=[
                    _tool_call("update_state", {"updates": {"mood": "steady"}}, "update-1")
                ],
                finish="tool_calls",
                usage=_usage(True),
                gen_id=123,
            ),
            _response(
                content="finished",
                usage=_usage("0.50"),
                gen_id="gen-valid",
            ),
        ],
        provider_name="openrouter",
        wake_mode="natural",
    )

    result = _call(
        backend,
        extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )

    assert result.cost_usd is None
    assert result.cost_turns_unreported == 2
    assert result.generation_ids == ["gen-valid"]


def test_usage_null_is_an_unreported_turn_not_an_exception():
    backend = _backend(
        [
            _response(
                tool_calls=[_think()],
                finish="tool_calls",
                usage=None,
                gen_id="gen-null-usage",
            )
        ],
        provider_name="openrouter",
    )

    result = _call(backend)

    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.cost_usd is None
    assert result.cost_turns_unreported == 1
    assert result.generation_ids == ["gen-null-usage"]


@pytest.mark.parametrize("wake_path", ["single", "natural", "terminal_surface"])
def test_non_openrouter_never_sends_usage_key(wake_path, tmp_path):
    if wake_path == "natural":
        backend = _backend(
            [_response(content="done")],
            provider_name="openai",
            wake_mode="natural",
        )
        _call(
            backend,
            extra_tools=[UPDATE_STATE_SCHEMA],
            tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
        )
    elif wake_path == "terminal_surface":
        backend = _backend(
            [_response(content='{"response":"done"}')],
            provider_name="openai",
        )
        backend.call_terminal_surface(
            model="validation-model",
            system="system",
            messages=[{"role": "user", "content": "hello"}],
            experiment_label="validation",
            terminal_surface=_terminal_surface(),
        )
    else:
        backend = _backend(
            [_response(tool_calls=[_think()], finish="tool_calls")],
            provider_name="openai",
        )
        _call(backend)

    assert backend.payloads
    assert all("usage" not in payload for payload in backend.payloads)


class _SequenceBackend:
    def __init__(self, results):
        self.results = list(results)

    def call(self, **kwargs):
        del kwargs
        return self.results.pop(0)


class _RequiredStateValidator:
    def validate(self, *, state, **kwargs):
        del kwargs
        valid = state.get("task_status") == "done"
        return {"valid": valid, "status": "valid" if valid else "invalid"}


class _RepairBuilder:
    def build_repair_prompt(self, **kwargs):
        del kwargs
        return "Repair state."


def _last_record(path):
    return json.loads(path.read_text().splitlines()[-1])


def test_session_record_conditionally_includes_main_result_cost_fields(tmp_path):
    measured = ExchangeResult(
        raw_output={"response": "measured"},
        cost_usd=0.41,
        cost_turns_unreported=1,
        generation_ids=["gen-main"],
    )
    unmeasured = ExchangeResult(raw_output={"response": "plain"})

    measured_log = tmp_path / "measured.jsonl"
    plain_log = tmp_path / "plain.jsonl"
    OpenTasteSession(backend=_SequenceBackend([measured]), log_path=str(measured_log)).exchange("hi")
    OpenTasteSession(backend=_SequenceBackend([unmeasured]), log_path=str(plain_log)).exchange("hi")

    measured_usage = _last_record(measured_log)["usage"]
    plain_usage = _last_record(plain_log)["usage"]
    assert measured_usage["cost_usd"] == pytest.approx(0.41)
    assert measured_usage["cost_turns_unreported"] == 1
    assert measured_usage["generation_ids"] == ["gen-main"]
    assert {"cost_usd", "cost_turns_unreported", "generation_ids"}.isdisjoint(plain_usage)


def test_state_repair_record_has_its_own_cost_metadata(tmp_path):
    initial = ExchangeResult(
        raw_output={"response": "needs repair"},
        cost_usd=0.10,
        generation_ids=["gen-main"],
    )
    repaired = ExchangeResult(
        raw_output={"response": "repaired", "task_status": "done"},
        cost_usd=0.06,
        cost_turns_unreported=2,
        generation_ids=["gen-repair-1", "gen-repair-2", "gen-repair-3"],
    )
    log_path = tmp_path / "repair.jsonl"
    session = OpenTasteSession(
        backend=_SequenceBackend([initial, repaired]),
        log_path=str(log_path),
        state_validator=_RequiredStateValidator(),
        state_repair_builder=_RepairBuilder(),
    )

    assert session.exchange("hi") == "repaired"

    record = _last_record(log_path)
    assert record["usage"]["cost_usd"] == pytest.approx(0.10)
    assert record["usage"]["generation_ids"] == ["gen-main"]
    repair_usage = record["state_validation"]["repair"]["usage"]
    assert repair_usage["cost_usd"] == pytest.approx(0.06)
    assert repair_usage["cost_turns_unreported"] == 2
    assert repair_usage["generation_ids"] == [
        "gen-repair-1",
        "gen-repair-2",
        "gen-repair-3",
    ]


def test_last_usage_accumulator_retains_cycle_cost_metadata(tmp_path):
    result = ExchangeResult(
        raw_output={"response": "done"},
        input_tokens=12,
        output_tokens=4,
        cost_usd=0.09,
        cost_turns_unreported=1,
        generation_ids=["gen-last"],
    )
    session = OpenTasteSession(
        backend=_SequenceBackend([result]),
        log_path=str(tmp_path / "last-usage.jsonl"),
    )

    session.exchange("hi")

    assert session._last_usage == {
        "input_tokens": 12,
        "output_tokens": 4,
        "cost_usd": pytest.approx(0.09),
        "cost_turns_unreported": 1,
        "generation_ids": ["gen-last"],
    }
