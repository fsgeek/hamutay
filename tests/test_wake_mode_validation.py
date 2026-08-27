"""Independent adversarial validation for ``--wake-mode natural``.

These tests intentionally exercise protocol boundaries and multi-turn shapes
that are distinct from the implementation author's development suite.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pytest

from hamutay.taste_open import (
    CapabilityProfile,
    OpenAITasteBackend,
    OpenTasteSession,
    _apply_updates,
)
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS, UPDATE_STATE_SCHEMA


@dataclass
class ScriptedChat:
    """Strict fake transport: capture payloads and consume replies in order."""

    replies: list[dict[str, Any]]

    def __post_init__(self) -> None:
        self.replies = deepcopy(self.replies)
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(deepcopy(payload))
        if not self.replies:
            raise AssertionError("backend made more chat turns than scripted")
        return self.replies.pop(0)


def chat_reply(
    *,
    content: Any = None,
    calls: list[dict[str, Any]] | None = None,
    finish_reason: str = "stop",
    prompt_tokens: int | None = 0,
    completion_tokens: int | None = 0,
) -> dict[str, Any]:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content, "tool_calls": calls or []},
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


def function_call(
    name: str,
    arguments: dict[str, Any],
    *,
    call_id: str | None,
) -> dict[str, Any]:
    call = {
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }
    if call_id is not None:
        call["id"] = call_id
    return call


def natural_backend(
    monkeypatch: pytest.MonkeyPatch,
    replies: list[dict[str, Any]],
    *,
    capability: CapabilityProfile | None = None,
) -> tuple[OpenAITasteBackend, ScriptedChat]:
    backend = OpenAITasteBackend(
        api_key="not-used",
        capability=capability,
        wake_mode="natural",
    )
    transport = ScriptedChat(replies)
    monkeypatch.setattr(backend, "_post_chat", transport)
    return backend, transport


def executor(tmp_path: Path, *, cycle: int = 8) -> ToolExecutor:
    return ToolExecutor(project_root=tmp_path, cycle=cycle)


def call_natural(
    backend: OpenAITasteBackend,
    tool_executor: ToolExecutor | None,
    *,
    tools: list[dict[str, Any]] | None = None,
):
    return backend.call(
        model="validation-model",
        system="validation system",
        messages=[{"role": "user", "content": "exercise the wake"}],
        experiment_label="independent_validation",
        extra_tools=tools if tools is not None else [UPDATE_STATE_SCHEMA],
        tool_executor=tool_executor,
    )


# ToolExecutor -------------------------------------------------------------


def test_executor_resolves_cross_call_conflicts_before_protected_state_merge(tmp_path):
    ex = executor(tmp_path, cycle=9)
    ex.execute(
        "update_state",
        {
            "updates": {"written_then_deleted": "temporary", "locked": "replace"},
            "deleted_regions": ["deleted_then_written"],
        },
    )
    ex.execute(
        "update_state",
        {
            "updates": {"deleted_then_written": "restored"},
            "deleted_regions": ["written_then_deleted", "locked"],
        },
    )

    pending = ex.pending_state_updates
    assert pending == {
        "updates": {"deleted_then_written": "restored"},
        "deleted_regions": ["written_then_deleted", "locked"],
    }
    assert not set(pending["updates"]) & set(pending["deleted_regions"])

    raw_output = {"response": "done", **pending["updates"]}
    raw_output["deleted_regions"] = pending["deleted_regions"]
    merged = _apply_updates(
        {
            "written_then_deleted": "old",
            "deleted_then_written": "old",
            "locked": "must survive",
        },
        raw_output,
        9,
        protected_fields={"locked"},
    )
    assert merged == {
        "cycle": 9,
        "deleted_then_written": "restored",
        "locked": "must survive",
    }


def test_executor_protocol_key_rejection_is_atomic_and_logged(tmp_path):
    ex = executor(tmp_path)
    attempted = {
        "updates": {"safe": 1, "response": "forge", "cycle": 999},
        "deleted_regions": ["updated_regions", "deleted_regions"],
        "reason": "probe protocol ownership",
    }

    result = ex.execute("update_state", attempted)

    assert result == {
        "error": (
            "update_state: ['cycle', 'deleted_regions', 'response', "
            "'updated_regions'] are protocol keys and cannot be written or deleted"
        )
    }
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": []}
    entry = ex.activity_log[-1]
    assert entry["tool"] == "update_state"
    assert entry["capability"] == "bounded_write"
    assert entry["reason"] == "probe protocol ownership"
    assert entry["parameters"] == {
        "updates": attempted["updates"],
        "deleted_regions": attempted["deleted_regions"],
    }
    assert entry["result"] == result
    assert entry["result_summary"].startswith("error: update_state:")


def test_executor_rejects_non_mapping_update_state_input_without_crashing(tmp_path):
    ex = executor(tmp_path)

    result = ex.execute("update_state", None)  # type: ignore[arg-type]

    assert "error" in result
    assert "object" in result["error"]
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": []}
    assert ex.activity_log[-1]["result"] == result


@pytest.mark.parametrize(
    ("bad_input", "field"),
    [
        ({"updates": []}, "updates"),
        ({"deleted_regions": {}}, "deleted_regions"),
    ],
)
def test_executor_rejects_falsey_values_of_the_wrong_container_type(
    tmp_path,
    bad_input,
    field,
):
    ex = executor(tmp_path)

    result = ex.execute("update_state", bad_input)

    assert "error" in result, f"falsey nonconforming {field} must not be accepted"
    assert field in result["error"]
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": []}


def test_executor_activity_log_records_success_without_leaking_reason_into_parameters(
    tmp_path,
):
    ex = executor(tmp_path, cycle=12)

    result = ex.execute(
        "update_state",
        {"updates": {"zeta": 1, "alpha": 2}, "reason": "durable context"},
    )

    assert result == {"recorded": ["alpha", "zeta"], "deleted": []}
    [entry] = ex.activity_log
    assert entry["cycle"] == 12
    assert entry["tool"] == "update_state"
    assert entry["capability"] == "bounded_write"
    assert entry["parameters"] == {"updates": {"zeta": 1, "alpha": 2}}
    assert entry["reason"] == "durable context"
    assert entry["exit_code"] is None
    assert entry["result"] == result
    assert len(entry["result_hash"]) == 64
    assert entry["duration_ms"] >= 0


# OpenAITasteBackend -------------------------------------------------------


def test_natural_backend_runs_several_tool_turns_with_late_state_override_and_usage_sum(
    tmp_path,
    monkeypatch,
):
    (tmp_path / "evidence.txt").write_text("evidence")
    replies = [
        chat_reply(
            content="I am checking the evidence.",
            calls=[function_call("read", {"path": "evidence.txt"}, call_id="read-1")],
            finish_reason="tool_calls",
            prompt_tokens=3,
            completion_tokens=5,
        ),
        chat_reply(
            content="First state draft.",
            calls=[
                function_call(
                    "update_state",
                    {
                        "updates": {"decision": "first", "revived": True},
                        "deleted_regions": ["gone"],
                    },
                    call_id="state-1",
                )
            ],
            finish_reason="tool_calls",
            prompt_tokens=7,
            completion_tokens=11,
        ),
        chat_reply(
            calls=[
                function_call(
                    "update_state",
                    {
                        "updates": {"decision": "second", "gone": "restored"},
                        "deleted_regions": ["revived"],
                    },
                    call_id="state-2",
                )
            ],
            finish_reason="tool_calls",
            prompt_tokens=13,
            completion_tokens=17,
        ),
        chat_reply(
            content="Final answer after the tools.",
            prompt_tokens=19,
            completion_tokens=23,
        ),
    ]
    backend, transport = natural_backend(monkeypatch, replies)
    ex = executor(tmp_path)

    result = call_natural(
        backend,
        ex,
        tools=[TOOL_SCHEMAS["read"], UPDATE_STATE_SCHEMA],
    )

    assert result.raw_output == {
        "response": "Final answer after the tools.",
        "decision": "second",
        "gone": "restored",
        "deleted_regions": ["revived"],
    }
    assert result.interim_text == [
        "I am checking the evidence.",
        "First state draft.",
    ]
    assert result.input_tokens == 42
    assert result.output_tokens == 56
    assert [entry["tool"] for entry in result.tool_activity] == [
        "read",
        "update_state",
        "update_state",
    ]
    assert len(transport.payloads) == 4
    assert transport.replies == []
    assert all(payload["tool_choice"] == "auto" for payload in transport.payloads)
    second_turn_roles = [m["role"] for m in transport.payloads[1]["messages"]]
    assert second_turn_roles[-2:] == ["assistant", "tool"]
    assert transport.payloads[1]["messages"][-1]["tool_call_id"] == "read-1"


def test_natural_backend_normalizes_list_content_parts_for_interim_and_final_text(
    tmp_path,
    monkeypatch,
):
    interim_parts = [
        {"type": "text", "text": "looking"},
        {"type": "text", "text": "more closely"},
    ]
    final_parts = [
        {"type": "text", "text": "first line"},
        {"type": "text", "text": "second line"},
    ]
    backend, transport = natural_backend(
        monkeypatch,
        [
            chat_reply(
                content=interim_parts,
                calls=[
                    function_call(
                        "update_state",
                        {"updates": {"inspected": True}},
                        call_id="parts-1",
                    )
                ],
                finish_reason="tool_calls",
            ),
            chat_reply(content=final_parts),
        ],
    )

    result = call_natural(backend, executor(tmp_path))

    assert transport.payloads[1]["messages"][-2]["content"] == interim_parts
    assert result.interim_text == ["looking\nmore closely"]
    assert result.raw_output["response"] == "first line\nsecond line"
    assert result.raw_output["inspected"] is True


def test_natural_backend_uses_auto_even_for_function_object_capability(
    tmp_path,
    monkeypatch,
):
    backend, transport = natural_backend(
        monkeypatch,
        [chat_reply(content="plain response")],
        capability=CapabilityProfile(tool_choice_mode="function_object"),
    )

    call_natural(backend, executor(tmp_path))

    [payload] = transport.payloads
    assert payload["tool_choice"] == "auto"
    assert [tool["function"]["name"] for tool in payload["tools"]] == [
        "update_state"
    ]


def test_natural_backend_stops_after_exactly_twenty_nonterminal_turns(
    tmp_path,
    monkeypatch,
):
    backend = OpenAITasteBackend(api_key="not-used", wake_mode="natural")
    payloads = []

    def endless_tools(payload):
        payloads.append(deepcopy(payload))
        index = len(payloads)
        return chat_reply(
            calls=[
                function_call(
                    "update_state",
                    {"updates": {"turn": index}},
                    call_id=f"loop-{index}",
                )
            ],
            finish_reason="tool_calls",
            prompt_tokens=1,
            completion_tokens=1,
        )

    monkeypatch.setattr(backend, "_post_chat", endless_tools)

    with pytest.raises(RuntimeError, match="within 20 turns"):
        call_natural(backend, executor(tmp_path))
    assert len(payloads) == 20


def test_natural_backend_rejects_tool_call_without_id_before_execution(
    tmp_path,
    monkeypatch,
):
    backend, _ = natural_backend(
        monkeypatch,
        [
            chat_reply(
                calls=[
                    function_call(
                        "update_state",
                        {"updates": {"must_not_apply": True}},
                        call_id=None,
                    )
                ],
                finish_reason="tool_calls",
            )
        ],
    )
    ex = executor(tmp_path)

    with pytest.raises(RuntimeError, match="missing name or id"):
        call_natural(backend, ex)
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": []}
    assert ex.activity_log == []


def test_natural_backend_rejects_length_before_executing_truncated_tool_calls(
    tmp_path,
    monkeypatch,
):
    backend, _ = natural_backend(
        monkeypatch,
        [
            chat_reply(
                content="partial",
                calls=[
                    function_call(
                        "update_state",
                        {"updates": {"must_not_apply": True}},
                        call_id="truncated-1",
                    )
                ],
                finish_reason="length",
                prompt_tokens=101,
                completion_tokens=202,
            )
        ],
    )
    ex = executor(tmp_path)

    with pytest.raises(RuntimeError, match="finish_reason=length"):
        call_natural(backend, ex)
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": []}
    assert ex.activity_log == []


def test_natural_backend_requires_stop_to_accept_a_tool_free_terminal_reply(
    tmp_path,
    monkeypatch,
):
    backend, _ = natural_backend(
        monkeypatch,
        [chat_reply(content="filtered text", finish_reason="content_filter")],
    )

    with pytest.raises(RuntimeError, match="finish_reason.*content_filter"):
        call_natural(backend, executor(tmp_path))


def test_natural_backend_rejects_tool_calls_when_no_executor_is_available(monkeypatch):
    backend, _ = natural_backend(
        monkeypatch,
        [
            chat_reply(
                calls=[function_call("update_state", {}, call_id="orphan-1")],
                finish_reason="tool_calls",
            )
        ],
    )

    with pytest.raises(RuntimeError, match="no tool_executor"):
        call_natural(backend, None)


def test_default_terminal_payload_is_byte_identical_to_explicit_terminal_mode(
    tmp_path,
    monkeypatch,
):
    capability = CapabilityProfile(tool_choice_mode="function_object")
    payloads = []

    for kwargs in ({}, {"wake_mode": "terminal"}):
        backend = OpenAITasteBackend(
            api_key="not-used",
            capability=capability,
            **kwargs,
        )
        transport = ScriptedChat(
            [
                chat_reply(
                    calls=[
                        function_call(
                            "think_and_respond",
                            {"response": "terminal response", "state_key": "value"},
                            call_id="terminal-1",
                        )
                    ],
                    finish_reason="tool_calls",
                )
            ]
        )
        monkeypatch.setattr(backend, "_post_chat", transport)
        result = backend.call(
            model="validation-model",
            system="terminal system",
            messages=[{"role": "user", "content": "terminal request"}],
            experiment_label="independent_validation",
            extra_tools=[TOOL_SCHEMAS["read"]],
            tool_executor=executor(tmp_path),
        )
        assert result.raw_output == {
            "response": "terminal response",
            "state_key": "value",
        }
        payloads.append(transport.payloads[0])

    assert json.dumps(payloads[0], separators=(",", ":")) == json.dumps(
        payloads[1], separators=(",", ":")
    )
    terminal_payload = payloads[0]
    assert [tool["function"]["name"] for tool in terminal_payload["tools"]] == [
        "think_and_respond",
        "read",
    ]
    assert terminal_payload["tool_choice"] == {
        "type": "function",
        "function": {"name": "think_and_respond"},
    }


# OpenTasteSession ---------------------------------------------------------


def test_natural_session_logs_mode_and_prompt_and_carries_state_without_an_update(
    tmp_path,
    monkeypatch,
):
    log_path = tmp_path / "natural.jsonl"
    backend, transport = natural_backend(
        monkeypatch,
        [
            chat_reply(
                calls=[
                    function_call(
                        "update_state",
                        {"updates": {"durable": {"value": 1}}},
                        call_id="session-state-1",
                    )
                ],
                finish_reason="tool_calls",
            ),
            chat_reply(content="first reply"),
            chat_reply(content="second reply, no state call"),
        ],
    )
    session = OpenTasteSession(
        model="validation-model",
        backend=backend,
        log_path=str(log_path),
        enable_tools=True,
        project_root=tmp_path,
        memory_base_probability=0,
        wake_mode="natural",
    )

    assert session.exchange("first", force_memory=None) == "first reply"
    assert session.state["durable"] == {"value": 1}
    assert session.exchange("second", force_memory=None) == "second reply, no state call"

    assert session.state["durable"] == {"value": 1}
    assert session.state["cycle"] == 2
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [record["wake_mode"] for record in records] == ["natural", "natural"]
    assert records[0]["raw_output"]["durable"] == {"value": 1}
    assert records[1]["raw_output"] == {"response": "second reply, no state call"}
    assert records[1]["prior_state"]["durable"] == {"value": 1}
    assert records[1]["state"]["durable"] == {"value": 1}
    for record in records:
        assert "think_and_respond" not in record["system_prompt"]
        assert "update_state" in record["system_prompt"]
    assert [
        tool["function"]["name"] for tool in transport.payloads[0]["tools"]
    ].count("update_state") == 1


def test_natural_session_durably_logs_interim_text_without_using_it_as_reply_or_state(
    tmp_path,
    monkeypatch,
):
    log_path = tmp_path / "interim.jsonl"
    backend, _ = natural_backend(
        monkeypatch,
        [
            chat_reply(
                content="I will inspect first.",
                calls=[
                    function_call(
                        "update_state",
                        {"updates": {"inspected": True}},
                        call_id="interim-1",
                    )
                ],
                finish_reason="tool_calls",
            ),
            chat_reply(content="This is the actual reply."),
        ],
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(log_path),
        enable_tools=True,
        project_root=tmp_path,
        memory_base_probability=0,
        wake_mode="natural",
    )

    reply = session.exchange("inspect", force_memory=None)

    record = json.loads(log_path.read_text().splitlines()[-1])
    assert reply == "This is the actual reply."
    assert record["response_text"] == "This is the actual reply."
    assert record.get("interim_text") == ["I will inspect first."], (
        "natural-mode interim assistant text is declared as durable data and "
        "must not disappear between ExchangeResult and the session record"
    )
    assert "interim_text" not in record["state"]
    assert "_interim_text" not in record["state"]


def test_natural_session_resolves_conflicting_updates_and_honors_protected_fields(
    tmp_path,
    monkeypatch,
):
    backend, _ = natural_backend(
        monkeypatch,
        [
            chat_reply(
                calls=[
                    function_call(
                        "update_state",
                        {"updates": {"flip": "written", "locked": "replace"}},
                        call_id="merge-1",
                    )
                ],
                finish_reason="tool_calls",
            ),
            chat_reply(
                calls=[
                    function_call(
                        "update_state",
                        {
                            "updates": {"restored": "new"},
                            "deleted_regions": ["flip", "locked"],
                        },
                        call_id="merge-2",
                    )
                ],
                finish_reason="tool_calls",
            ),
            chat_reply(content="merged"),
        ],
    )
    session = OpenTasteSession(
        backend=backend,
        enable_tools=True,
        project_root=tmp_path,
        memory_base_probability=0,
        protected_state_fields={"locked"},
        wake_mode="natural",
    )
    session._state = {"locked": "original", "flip": "old", "restored": "old"}

    assert session.exchange("merge", force_memory=None) == "merged"
    assert session.state["locked"] == "original"
    assert "flip" not in session.state
    assert session.state["restored"] == "new"


def test_natural_session_commits_schedule_event_calls_after_success(
    tmp_path,
    monkeypatch,
):
    log_path = tmp_path / "scheduled-session.jsonl"
    event_path = tmp_path / "scheduled-events.jsonl"
    backend, _ = natural_backend(
        monkeypatch,
        [
            chat_reply(
                calls=[
                    function_call(
                        "schedule_event",
                        {
                            "purpose": "Revisit the evidence.",
                            "requested_context": [{"tool": "recall", "cycle": 1}],
                        },
                        call_id="schedule-1",
                    )
                ],
                finish_reason="tool_calls",
            ),
            chat_reply(content="Scheduled."),
        ],
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(log_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
        memory_base_probability=0,
        wake_mode="natural",
    )

    assert session.exchange("schedule", force_memory=None) == "Scheduled."

    [event] = [json.loads(line) for line in event_path.read_text().splitlines()]
    [record] = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert event["status"] == "pending"
    assert event["scheduled_by_cycle"] == 1
    assert event["scheduled_by_record_id"] == record["record_id"]
    assert record["scheduled_events"][0]["event_id"] == event["event_id"]
    assert record["tool_activity_full"][0]["tool"] == "schedule_event"


def test_natural_session_rejects_backend_without_declared_support(tmp_path):
    class UnsupportedBackend:
        def call(self, **_kwargs):
            raise AssertionError("constructor should reject this backend")

    with pytest.raises(ValueError, match="backend constructed.*natural"):
        OpenTasteSession(
            backend=UnsupportedBackend(),
            enable_tools=True,
            project_root=tmp_path,
            wake_mode="natural",
        )


def test_natural_session_rejects_disabled_tools_even_with_supported_backend(tmp_path):
    class DeclaredNaturalBackend:
        wake_mode = "natural"

        def call(self, **_kwargs):
            raise AssertionError("constructor should reject disabled tools")

    with pytest.raises(ValueError, match="requires enable_tools=True"):
        OpenTasteSession(
            backend=DeclaredNaturalBackend(),
            enable_tools=False,
            project_root=tmp_path,
            wake_mode="natural",
        )
