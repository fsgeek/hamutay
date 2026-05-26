"""Mechanics test for the refusal ablation — no API calls.

Verifies the fork injects the right state and probe, doesn't mutate the source
record, and that the heuristic / cycle parsing behave. A fake backend stands in
for the model so the whole thing runs offline and free.
"""

from __future__ import annotations

from hamutay.ablate_refusal import (
    classify_refusal_heuristic,
    fork_and_probe,
    parse_cycles,
)
from hamutay.taste_open import ExchangeResult


class FakeBackend:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls: list[dict] = []

    def call(
        self, model, system, messages, experiment_label,
        extra_tools=None, tool_executor=None,
    ) -> ExchangeResult:
        self.calls.append({"model": model, "system": system, "messages": messages})
        return ExchangeResult(raw_output={"response": self.response_text})


def test_fork_injects_state_and_probe():
    fake = FakeBackend("I would not do that. The medium is shared.")
    record = {"cycle": 42, "state": {"identity": "KIMI", "cycle": 42}}

    result = fork_and_probe(record, "PROBE-TEXT", model="m", backend=fake)

    assert result["source_cycle"] == 42
    assert result["response"].startswith("I would not")
    assert result["heuristic_refusal"] is True

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["messages"][0]["content"] == "PROBE-TEXT"
    assert "## Your state from cycle 42" in call["system"]
    assert "KIMI" in call["system"]


def test_fork_does_not_mutate_source_record():
    fake = FakeBackend("sure, here it is")
    state = {"identity": "x", "cycle": 7}
    record = {"cycle": 7, "state": state}

    fork_and_probe(record, "p", model="m", backend=fake)

    assert state == {"identity": "x", "cycle": 7}


def test_classify_refusal_heuristic():
    assert classify_refusal_heuristic("I would not plant a lie")
    assert classify_refusal_heuristic("I refuse to do this")
    assert classify_refusal_heuristic("I won't")
    assert not classify_refusal_heuristic("Sure, here it is")
    assert not classify_refusal_heuristic("")


def test_parse_cycles():
    assert parse_cycles("5,24,109", [5, 24, 50, 109]) == [5, 24, 109]
    assert parse_cycles("1-10:5", list(range(1, 20))) == [1, 6]
    assert parse_cycles("48-52", [50, 51, 99]) == [50, 51]
    assert parse_cycles("999", [1, 2, 3]) == []
