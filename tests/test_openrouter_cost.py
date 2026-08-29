"""OpenRouter cost accounting: the log knows what it spent.

Why: on 2026-08-29 the first natural-shape wake of the Fable resident cost
509K input tokens and the only place the dollar figure lived was Tony's
OpenRouter receipt. The record carried tokens and no cost, and dropped the
generation id the response carries on every call — the key that
OpenRouter's /generation endpoint needs to give the authoritative billing
record after the fact. Implementer's TDD tests.

Honesty rule: a call that reports no cost is UNMEASURED, never free. cost_usd
is None when nothing reported; when some turns of a wake report and others
do not, the sum of the reported turns is carried with the number of
unreported turns beside it.
"""
import json

import pytest

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


def _turn(content=None, tool_calls=None, finish="stop", usage=None, gen_id=None):
    data = {
        "choices": [{"finish_reason": finish,
                     "message": {"content": content, "tool_calls": tool_calls}}],
        "usage": usage or {"prompt_tokens": 10, "completion_tokens": 5},
    }
    if gen_id is not None:
        data["id"] = gen_id
    return data


def _tool_call(name, args, call_id):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def _think(cid="t1"):
    return _tool_call("think_and_respond", {"response": "r"}, cid)


def _usage(prompt=10, completion=5, cost=None):
    usage = {"prompt_tokens": prompt, "completion_tokens": completion}
    if cost is not None:
        usage["cost"] = cost
    return usage


# --- the request asks OpenRouter for usage accounting, always ---------------


def test_openrouter_payload_requests_usage_accounting():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openrouter")
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t")
    assert backend.payloads[0]["usage"] == {"include": True}


def test_non_openrouter_provider_sends_no_usage_directive():
    backend = _backend([_turn(tool_calls=[_think()], finish="tool_calls")],
                       provider_name="openai")
    backend.call(model="m", system="s", messages=[{"role": "user", "content": "u"}],
                 experiment_label="t")
    assert "usage" not in backend.payloads[0]


# --- cost and generation id reach ExchangeResult ----------------------------


def test_single_call_reports_cost_and_generation_id():
    backend = _backend(
        [_turn(tool_calls=[_think()], finish="tool_calls",
               usage=_usage(cost=0.0123), gen_id="gen-abc")],
        provider_name="openrouter",
    )
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t")
    assert result.cost_usd == pytest.approx(0.0123)
    assert result.cost_turns_unreported == 0
    assert result.generation_ids == ["gen-abc"]


def test_missing_cost_is_unmeasured_not_zero():
    backend = _backend(
        [_turn(tool_calls=[_think()], finish="tool_calls", gen_id="gen-1")],
        provider_name="openrouter",
    )
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t")
    assert result.cost_usd is None
    assert result.cost_turns_unreported == 1
    assert result.generation_ids == ["gen-1"]


def test_natural_wake_sums_cost_and_collects_every_generation_id(tmp_path):
    script = [
        _turn(tool_calls=[_tool_call("update_state", {"updates": {"a": 1}}, "c1")],
              finish="tool_calls", usage=_usage(cost=0.10), gen_id="gen-1"),
        _turn(content="done", usage=_usage(cost=0.25), gen_id="gen-2"),
    ]
    backend = _backend(script, provider_name="openrouter", wake_mode="natural")
    result = backend.call(
        model="m", system="s", messages=[{"role": "user", "content": "u"}],
        experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )
    assert result.cost_usd == pytest.approx(0.35)
    assert result.cost_turns_unreported == 0
    assert result.generation_ids == ["gen-1", "gen-2"]


def test_natural_wake_partial_cost_carries_sum_and_unreported_count(tmp_path):
    script = [
        _turn(tool_calls=[_tool_call("update_state", {"updates": {"a": 1}}, "c1")],
              finish="tool_calls", usage=_usage(cost=0.10), gen_id="gen-1"),
        _turn(content="done", usage=_usage(), gen_id="gen-2"),
    ]
    backend = _backend(script, provider_name="openrouter", wake_mode="natural")
    result = backend.call(
        model="m", system="s", messages=[{"role": "user", "content": "u"}],
        experiment_label="t", extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )
    assert result.cost_usd == pytest.approx(0.10)
    assert result.cost_turns_unreported == 1
    assert result.generation_ids == ["gen-1", "gen-2"]


def test_terminal_multi_turn_sums_cost(tmp_path):
    (tmp_path / "f.txt").write_text("x")
    script = [
        _turn(tool_calls=[_tool_call("read", {"path": "f.txt"}, "c1")],
              finish="tool_calls", usage=_usage(cost=0.05), gen_id="gen-1"),
        _turn(tool_calls=[_think()], finish="tool_calls",
              usage=_usage(cost=0.07), gen_id="gen-2"),
    ]
    backend = _backend(script, provider_name="openrouter")
    result = backend.call(
        model="m", system="s", messages=[{"role": "user", "content": "u"}],
        experiment_label="t", extra_tools=[TOOL_SCHEMAS["read"]],
        tool_executor=ToolExecutor(project_root=tmp_path, cycle=1),
    )
    assert result.cost_usd == pytest.approx(0.12)
    assert result.generation_ids == ["gen-1", "gen-2"]


def test_response_without_id_records_no_generation_id():
    backend = _backend(
        [_turn(tool_calls=[_think()], finish="tool_calls", usage=_usage(cost=0.01))],
        provider_name="openrouter",
    )
    result = backend.call(model="m", system="s",
                          messages=[{"role": "user", "content": "u"}],
                          experiment_label="t")
    assert result.generation_ids == []


# --- the cycle record carries it; a silent backend leaves the record alone --


class _SequenceBackend:
    def __init__(self, results):
        self._results = list(results)

    def call(self, model, system, messages, experiment_label,
             extra_tools=None, tool_executor=None):
        del model, system, messages, experiment_label, extra_tools, tool_executor
        return self._results.pop(0)


def _last_record(path):
    with open(path) as f:
        return json.loads([line for line in f if line.strip()][-1])


def test_cycle_record_usage_carries_cost_and_generation_ids(tmp_path):
    from hamutay.taste_open import ExchangeResult, OpenTasteSession

    log = tmp_path / "session.jsonl"
    backend = _SequenceBackend([
        ExchangeResult(raw_output={"response": "r", "status": "done"},
                       cost_usd=0.35, cost_turns_unreported=1,
                       generation_ids=["gen-1", "gen-2"]),
    ])
    OpenTasteSession(backend=backend, log_path=str(log)).exchange("hi")
    usage = _last_record(log)["usage"]
    assert usage["cost_usd"] == pytest.approx(0.35)
    assert usage["cost_turns_unreported"] == 1
    assert usage["generation_ids"] == ["gen-1", "gen-2"]


def test_cycle_record_usage_unchanged_when_backend_reports_no_cost(tmp_path):
    from hamutay.taste_open import ExchangeResult, OpenTasteSession

    log = tmp_path / "session.jsonl"
    backend = _SequenceBackend([
        ExchangeResult(raw_output={"response": "r", "status": "done"}),
    ])
    OpenTasteSession(backend=backend, log_path=str(log)).exchange("hi")
    usage = _last_record(log)["usage"]
    assert "cost_usd" not in usage
    assert "cost_turns_unreported" not in usage
    assert "generation_ids" not in usage
