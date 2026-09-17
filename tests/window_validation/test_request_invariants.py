from __future__ import annotations

import json

import pytest

from hamutay.context_policy import ContextPolicy
from hamutay.tools import ToolExecutor
from hamutay.window import (
    REPLY_RESERVE_TOKENS,
    THINK_FLOOR_TOKENS,
    THINK_UNRESTRICTED_ROOM_TOKENS,
    CountUnavailable,
    ExhaustedBeforeRequest,
    bound_payload,
)

from .conftest import (
    FakeHTTP,
    ScriptedCounter,
    aware_policy,
    natural_tools,
    records,
    scripted_backend,
    seeded_session,
    tool_call,
    turn,
)


def test_every_natural_payload_is_strictly_inside_the_window_after_each_tool_withdrawal(tmp_path):
    limit = 65_536
    sent_counts = [52_000, 54_000, 55_000]
    backend = scripted_backend(
        [
            turn(tool_calls=[tool_call("clock", {})], prompt_tokens=52_000),
            turn(
                tool_calls=[tool_call("update_state", {"updates": {"phase": "closing"}}, "update-1")],
                prompt_tokens=54_000,
            ),
            turn("finished", prompt_tokens=55_000),
        ],
        counts=[53_000, *sent_counts],
        policy=aware_policy(limit),
    )
    executor = ToolExecutor(project_root=tmp_path, cycle=1)

    backend.call(
        model="validation-model",
        system="system",
        messages=[{"role": "user", "content": "work until done"}],
        experiment_label="window-validation",
        extra_tools=natural_tools(),
        tool_executor=executor,
    )

    assert len(backend.payloads) == 3
    assert len(backend._counter.payloads) == 4
    for counted, sent, prompt_tokens in zip(
        backend._counter.payloads[-3:], backend.payloads, sent_counts, strict=True
    ):
        assert counted["messages"] == sent["messages"]
        assert counted.get("tools") == sent.get("tools")
        assert counted.get("tool_choice") == sent.get("tool_choice")
        assert prompt_tokens + sent["max_tokens"] < limit

    first_names = {tool["function"]["name"] for tool in backend.payloads[0].get("tools", [])}
    assert {"read", "clock", "bash"}.isdisjoint(first_names)
    assert backend.payloads[-1]["tool_choice"] == "none"
    assert "tools" not in backend.payloads[-1]


@pytest.mark.parametrize(
    ("reasoning_budget", "tool_choice_none", "prompt_tokens", "expect_budget"),
    [
        ("probed", True, 40_000, True),
        ("probed", False, 40_000, False),
        ("unsupported", True, 40_000, False),
        ("inconclusive", True, 40_000, False),
        ("not_probed", True, 40_000, False),
        ("probed", True, 1_000, False),
    ],
)
def test_budget_fields_obey_the_probed_grammar_free_near_wall_gate(
    reasoning_budget, tool_choice_none, prompt_tokens, expect_budget
):
    forced = 37
    policy = aware_policy(
        reasoning_budget=reasoning_budget,
        forced_sequence_tokens=forced,
    )
    payload = {
        "model": "validation-model",
        "messages": [],
        "tool_choice": "none" if tool_choice_none else "auto",
    }
    bound = bound_payload(
        payload,
        policy,
        ScriptedCounter([prompt_tokens]),
        configured_max_tokens=64_000,
        tool_choice_none=tool_choice_none,
    )

    assert prompt_tokens + payload["max_tokens"] < policy.limit
    assert ("reasoning_budget_tokens" in payload) is expect_budget
    assert ("reasoning_budget_message" in payload) is expect_budget
    if expect_budget:
        assert bound.room < THINK_UNRESTRICTED_ROOM_TOKENS
        assert payload["max_tokens"] < THINK_UNRESTRICTED_ROOM_TOKENS
        assert payload["reasoning_budget_tokens"] == (
            payload["max_tokens"] - 2_048 - forced
        )
        assert REPLY_RESERVE_TOKENS == 2_048


def test_an_unavailable_server_count_sends_no_completion_payload(tmp_path):
    http = FakeHTTP(fail_at="/apply-template")
    backend = scripted_backend(
        [turn("must not be sent")],
        policy=aware_policy(),
        http=http,
    )
    executor = ToolExecutor(project_root=tmp_path, cycle=1)

    with pytest.raises(CountUnavailable):
        backend.call(
            model="validation-model",
            system="system",
            messages=[{"role": "user", "content": "hello"}],
            experiment_label="window-validation",
            extra_tools=natural_tools(),
            tool_executor=executor,
        )

    assert backend.payloads == []
    assert [url.rsplit("/", 1)[-1] for _, url, _ in http.calls] == ["apply-template"]


def test_a_generation_limit_below_the_reply_floor_sends_nothing(tmp_path):
    forced = 19
    floor = REPLY_RESERVE_TOKENS + THINK_FLOOR_TOKENS + forced
    backend = scripted_backend(
        [turn("must not be sent")],
        counts=[100],
        policy=aware_policy(forced_sequence_tokens=forced),
        wake_mode="terminal",
        max_tokens=floor - 1,
    )

    with pytest.raises(ExhaustedBeforeRequest) as raised:
        backend.call(
            model="validation-model",
            system="system",
            messages=[{"role": "user", "content": "hello"}],
            experiment_label="window-validation",
        )

    assert raised.value.max_tokens == floor - 1
    assert backend.payloads == []


def test_no_ceiling_payloads_match_a_baseline_backend_without_a_policy(tmp_path):
    script = [
        turn(tool_calls=[tool_call("update_state", {"updates": {"stable": True}})]),
        turn("done"),
    ]
    baseline = scripted_backend(json.loads(json.dumps(script)), wake_mode="natural")
    explicit_none = scripted_backend(
        json.loads(json.dumps(script)),
        policy=ContextPolicy.none(),
        wake_mode="natural",
    )

    class DeterministicExecutor:
        def __init__(self):
            self.activity_log = []

        def execute(self, tool_name, tool_input):
            return {"accepted": True, "tool": tool_name, "input": tool_input}

        def log_event(self, event):
            self.activity_log.append(event)

    for backend in (baseline, explicit_none):
        backend.call(
            model="validation-model",
            system="same-system",
            messages=[{"role": "user", "content": "same-wake"}],
            experiment_label="window-validation",
            extra_tools=natural_tools(),
            tool_executor=DeterministicExecutor(),
        )

    assert explicit_none.payloads == baseline.payloads


def test_no_ceiling_completed_record_has_no_window_admission_provenance(tmp_path):
    backend = scripted_backend([turn("complete")])
    session, log_path = seeded_session(tmp_path, backend, name="no-ceiling")

    assert session.exchange("hello") == "complete"

    completed = records(log_path)[-1]
    assert "admission" not in completed
    assert "context_policy_invocation" not in completed
