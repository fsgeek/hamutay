"""Independent §1a validation: literal spec oracles, fake transport, no live server.

The r6.5 design and accepted review-8 were read from the parent checkout
(this worktree still contains r6.4). No production completions are used.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from hamutay.context_policy import ContextPolicy, probe_think_switch
from hamutay.heartbeat import window_clause
from hamutay.window import (
    CountUnavailable, THINK_GATE_KWARGS, THINK_GATE_SENTENCE, think_gate_applies,
)

from .conftest import aware_policy, natural_tools, records, scripted_backend, tool_call, turn

SENTENCE = (
    "The harness also closes your think block for the rest of this wake "
    "(this server cannot bound a think); reason in your reply if you need to."
)
KWARGS = {"enable_thinking": False}


def gate_policy(**changes):
    return replace(aware_policy(reasoning_budget="unsupported"),
                   **({"think_switch": "template"} | changes))


class Executor:
    def __init__(self):
        self.activity_log = []
        self.pending_state_updates = {"updates": {}, "deleted_regions": []}

    def execute(self, name, arguments):
        return {"accepted": True, "tool": name, "input": arguments}

    def log_event(self, event):
        self.activity_log.append(copy.deepcopy(event))


def run_wake(backend, executor=None):
    executor = executor if executor is not None else Executor()
    backend.call(model="validation-model", system="system",
                 messages=[{"role": "user", "content": "work until done"}],
                 experiment_label="window-validation", extra_tools=natural_tools(),
                 tool_executor=executor)
    return executor


def four_turns():
    return [
        turn(tool_calls=[tool_call("clock", {}, "read-0")], prompt_tokens=20_000),
        turn(tool_calls=[tool_call("update_state", {"updates": {"phase": 1}}, "state-1")],
             prompt_tokens=52_500),
        turn(tool_calls=[tool_call("update_state", {"updates": {"phase": 2}}, "state-2")],
             prompt_tokens=53_500),
        turn("finished", prompt_tokens=54_000),
    ]


def closed_events(executor):
    return [e for e in executor.activity_log if e.get("action") == "think_closed"]


def expected_event(index, count):
    return {"tool": "_framework", "event": "budget_pressure", "action": "think_closed",
            "turn_index": index, "prompt_tokens": count, "max_tokens": 65_535 - count}


def assert_gate(payload, enabled):
    if enabled:
        assert payload["chat_template_kwargs"] == KWARGS
    else:
        assert "chat_template_kwargs" not in payload


def assert_same_prompt(counted, sent):
    # Generation bounds may change after counting; everything that renders the
    # prompt (including tools, choice, and template kwargs) must already match.
    ignored = {"max_tokens", "reasoning_budget_tokens", "reasoning_budget_message"}
    assert {k: v for k, v in counted.items() if k not in ignored} == {
        k: v for k, v in sent.items() if k not in ignored
    }


@pytest.mark.parametrize("mode,expected", [
    ("effective", "template"), ("identical-open", "none"),
    ("identical-closed", "none"), ("missing-string", "none"),
    ("plain-error", "none"), ("closed-error", "none"),
    ("different-but-open", "none"),
])
def test_switch_requires_two_successful_effective_renders(mode, expected):
    """Only a switch that changes an open suffix into a closed block qualifies."""
    calls = []

    def http(method, url, body):
        assert method == "POST" and url == "http://render.invalid/apply-template"
        calls.append(copy.deepcopy(body))
        gated = "chat_template_kwargs" in body
        if mode == ("closed-error" if gated else "plain-error"):
            raise OSError("render failed")
        if mode == "identical-closed":
            return {"prompt": "assistant <think>\n\n</think>\n\n"}
        if mode == "identical-open" or not gated:
            return {"prompt": "assistant <think>\n"}
        if mode == "different-but-open":
            return {"prompt": "different assistant <think>\n"}
        return {"prompt": "assistant <think>\n\n</think>\n\n"}

    template = "no switch here" if mode == "missing-string" else "enable_thinking"
    assert probe_think_switch("http://render.invalid", "m", http, template=template) == expected
    if mode == "missing-string":
        assert calls == []
    else:
        assert_gate(calls[0], False)
        if mode != "plain-error":
            assert len(calls) == 2
            assert_gate(calls[1], True)
            assert {k: v for k, v in calls[1].items() if k != "chat_template_kwargs"} == calls[0]


@pytest.mark.parametrize("effective", [True, False])
def test_cached_budget_probe_does_not_skip_switch_renders(effective):
    """A budget cache hit still independently renders and classifies the switch."""
    calls = []

    def http(method, url, body):
        calls.append((method, url, copy.deepcopy(body)))
        if url.endswith("/props"):
            return {"build_info": "validator-build", "model_alias": "m",
                    "chat_template": "<think></think> enable_thinking"}
        if url.endswith("/tokenize"):
            return {"tokens": [1, 2, 3]}
        if url.endswith("/apply-template"):
            suffix = "\n\n</think>\n\n" if effective and body.get("chat_template_kwargs") == KWARGS else "\n"
            return {"prompt": "assistant <think>" + suffix}
        assert url.endswith("/v1/chat/completions")
        return turn("<think>unchanged reasoning</think>ready")

    first = ContextPolicy.for_launch(65_536, "discovered", "http://render.invalid/v1", http=http, model="m")
    assert len([c for c in calls if c[1].endswith("/chat/completions")]) == 2
    calls.clear()
    cached = ContextPolicy.for_launch(65_536, "discovered", "http://render.invalid/v1", http=http, model="m", cached=first.probe)
    assert cached.think_switch == first.think_switch == ("template" if effective else "none")
    assert len([c for c in calls if c[1].endswith("/apply-template")]) == 2
    assert not any(c[1].endswith("/chat/completions") for c in calls)


@pytest.mark.parametrize("limit,tokenizer", [(65_536, "http://render.invalid"), (None, None), (65_536, None), (None, "http://render.invalid")])
def test_policy_dict_only_adds_switch_for_window_aware_policy(limit, tokenizer):
    """No-window launch serialization retains its old keys."""
    policy = gate_policy(limit=limit, tokenizer=tokenizer)
    data = policy.as_dict()
    assert data["window_aware"] is (limit is not None and tokenizer is not None)
    if data["window_aware"]:
        assert data["think_switch"] == "template"
    else:
        assert "think_switch" not in data


@pytest.mark.parametrize("budget", ["unsupported", "inconclusive", "not_probed"])
def test_four_send_gate_counts_note_and_exact_events(budget):
    """Open turn, withdrawn turn, subsequent state turn, and tools-none turn have exact gates."""
    backend = scripted_backend(four_turns(), counts=[20_000, 53_000, 52_500, 53_500, 54_000],
                               policy=gate_policy(reasoning_budget=budget))
    executor = run_wake(backend)
    assert THINK_GATE_KWARGS == KWARGS
    assert THINK_GATE_SENTENCE == SENTENCE
    assert [p["tool_choice"] for p in backend.payloads] == ["auto", "auto", "auto", "none"]
    assert len(backend._counter.payloads) == 5
    for payload, gate in zip(backend.payloads, [False, True, True, True], strict=True):
        assert_gate(payload, gate)
    for payload, gate in zip(backend._counter.payloads, [False, False, True, True, True], strict=True):
        assert_gate(payload, gate)
    for index, (count_index, count) in enumerate([(0, 20_000), (2, 52_500), (3, 53_500), (4, 54_000)]):
        sent = backend.payloads[index]
        assert_same_prompt(backend._counter.payloads[count_index], sent)
        assert sent["max_tokens"] == 65_535 - count
        assert count + sent["max_tokens"] < 65_536
        notes = [m for m in sent["messages"] if SENTENCE in (m.get("content") or "")]
        assert len(notes) == (1 if index else 0)
        if notes:
            assert notes[0]["role"] == "user"
            assert notes[0]["content"].count(SENTENCE) == 1
            assert " remain. " + SENTENCE + " Your reply" in notes[0]["content"]
        assert "reasoning_budget_tokens" not in sent
    for sent in backend.payloads[1:3]:
        names = {t["function"]["name"] for t in sent["tools"]}
        assert "update_state" in names
        assert names.isdisjoint({"read", "clock", "bash"})
    assert "tools" not in backend.payloads[3]
    assert closed_events(executor) == [expected_event(1, 52_500), expected_event(2, 53_500), expected_event(3, 54_000)]
    assert backend._counter.counts == []


@pytest.mark.parametrize("case", ["probed", "no-switch", "no-window", "no-tokenizer"])
def test_gate_negatives_and_probed_tools_none_budget(case):
    """The three gate preconditions are necessary; probed tools-none retains its budget."""
    changes = {"probed": {"reasoning_budget": "probed"}, "no-switch": {"think_switch": "none"},
               "no-window": {"limit": None, "tokenizer": None}, "no-tokenizer": {"tokenizer": None}}[case]
    policy = gate_policy(**changes)
    assert not think_gate_applies(policy)
    backend = scripted_backend(four_turns(), counts=[20_000, 53_000, 52_500, 53_500, 54_000] if policy.window_aware else None,
                               policy=policy)
    executor = run_wake(backend)
    payloads = backend.payloads + (backend._counter.payloads if backend._counter else [])
    for payload in payloads:
        assert_gate(payload, False)
        assert SENTENCE not in json.dumps(payload)
    assert closed_events(executor) == []
    if case == "probed":
        assert backend.payloads[-1]["tool_choice"] == "none"
        assert backend.payloads[-1]["reasoning_budget_tokens"] == 11_535 - 2048 - 23
        assert backend.payloads[-1]["reasoning_budget_message"] == (
            "[harness: thinking budget reached; about 2048 tokens remain for this "
            "turn. Do not open another think block. Finish the turn.]"
        )
        assert all("reasoning_budget_tokens" not in p for p in backend.payloads[:-1])


def test_gate_is_sticky_after_rebuild_restores_ample_room():
    """A 53,000 candidate rebuilt to 20,500 stays gated on this and later turns."""
    backend = scripted_backend(four_turns(), counts=[20_000, 53_000, 20_500, 21_000, 21_500], policy=gate_policy())
    executor = run_wake(backend)
    for index, count in enumerate([20_000, 20_500, 21_000, 21_500]):
        assert_gate(backend.payloads[index], index > 0)
        assert backend.payloads[index]["max_tokens"] == 65_535 - count
    assert closed_events(executor) == [expected_event(1, 20_500), expected_event(2, 21_000), expected_event(3, 21_500)]


def test_failed_gated_recount_never_sends_or_claims_a_closed_turn():
    """Withdrawal must count its changed template successfully before any send/event."""
    backend = scripted_backend([turn("not sent")], counts=[53_000, CountUnavailable("closed template failed")], policy=gate_policy())
    executor = Executor()
    with pytest.raises(CountUnavailable):
        run_wake(backend, executor)
    assert backend.payloads == []
    assert closed_events(executor) == []
    assert_gate(backend._counter.payloads[0], False)
    assert_gate(backend._counter.payloads[1], True)


@pytest.mark.parametrize("budget,switch,gate", [("unsupported", "template", "template after withdrawal"),
                                              ("probed", "template", "budget"), ("unsupported", "none", "none")])
def test_launch_clause_three_forms(budget, switch, gate):
    """The complete launch clause declares which closing-turn mechanism applies."""
    assert window_clause(gate_policy(reasoning_budget=budget, think_switch=switch)) == (
        "; window: limit 65536 (discovered), count server, reserve reply 2048 floor 512, "
        "think unrestricted above 32768 of room, "
        f"reasoning budget {budget}, think gate {gate}, compact retry once"
    )


def test_completed_no_window_wake_matches_frozen_golden(tmp_path, monkeypatch):
    """Completed no-ceiling payloads, system prompt, and record retain pre-change bytes."""
    from _window_golden_helpers import _backend, _session, _tool_call, _turn, frozen_clock

    golden = json.loads((Path(__file__).parents[1] / "fixtures/window_golden/no_ceiling_two_turn.json").read_text())
    backend = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")])
    # Duration is runtime metadata; freeze the timer rather than deleting record fields.
    monkeypatch.setattr("hamutay.tools.executor.time.monotonic", lambda: 100.0)
    with frozen_clock():
        session, path = _session(tmp_path, backend)
        assert session.exchange("hello") == "done"
    completed = records(path)[-1]
    completed.pop("timestamp")
    completed.pop("record_id")
    assert {"payloads": backend.payloads, "system_prompt": completed["system_prompt"], "record": completed} == golden


# Additional spec-derived edge cases, added after the initial 26-case run.
@pytest.mark.parametrize("bad_side", ["plain", "closed"])
def test_invalid_render_output_classifies_none_instead_of_aborting_launch(bad_side):
    """An unusable render is a probe failure: §1a says any failure yields none."""
    def http(method, url, body):
        gated = "chat_template_kwargs" in body
        if gated == (bad_side == "closed"):
            return {"prompt": None}
        return {"prompt": "assistant <think>\n\n</think>\n\n" if gated else "assistant <think>\n"}

    assert probe_think_switch("http://render.invalid", "m", http, template="enable_thinking") == "none"


@pytest.mark.parametrize("server", ["absent", "effective-without-limit"])
def test_launch_without_window_classifies_switch_none(server):
    """Item 18 requires window awareness as well as an effective template switch."""
    def http(method, url, body):
        if url.endswith("/props"):
            if server == "absent":
                raise OSError("no llama-server")
            return {"build_info": "validation-build", "model_alias": "m",
                    "chat_template": "<think></think> enable_thinking"}
        if url.endswith("/tokenize"):
            return {"tokens": [1, 2, 3]}
        if url.endswith("/apply-template"):
            return {"prompt": "assistant <think>\n\n</think>\n\n" if body.get("chat_template_kwargs") == KWARGS else "assistant <think>\n"}
        assert url.endswith("/v1/chat/completions")
        return turn("<think>same</think>ready")

    policy = ContextPolicy.for_launch(None if server == "effective-without-limit" else 65_536,
                                      "explicit", "http://render.invalid/v1", http=http, model="m")
    assert not policy.window_aware
    assert policy.think_switch == "none"
    assert "think_switch" not in policy.as_dict()
