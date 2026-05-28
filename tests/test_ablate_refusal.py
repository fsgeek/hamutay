"""Mechanics test for the refusal ablation — no API calls.

Verifies the faithful fork seeds the right prior state, asks the probe in place
of the original user_message, replays the live memory injection (or None), and
doesn't mutate the source records. A fake backend stands in for the model so
the whole thing runs offline and free.
"""

from __future__ import annotations

from hamutay.ablate_refusal import (
    classify_refusal_heuristic,
    clean_and_probe,
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


def test_fork_seeds_prior_state_and_probe():
    fake = FakeBackend("I would not do that. The medium is shared.")
    records = {
        41: {"cycle": 41, "state": {"identity": "KIMI", "cycle": 41},
             "record_id": None, "timestamp": ""},
        42: {"cycle": 42, "prior_state": {"identity": "KIMI", "cycle": 41},
             "state": {"identity": "KIMI", "cycle": 42}, "memory_injection": None},
    }

    result = fork_and_probe(records, 42, "PROBE-TEXT", model="m", backend=fake)

    assert result["source_cycle"] == 42
    assert result["response"].startswith("I would not")
    assert result["heuristic_refusal"] is True
    assert result["memory_replayed"] is None

    assert len(fake.calls) == 1
    call = fake.calls[0]
    # decision point 42 carries the state of cycle 41 as prior
    assert call["messages"][0]["content"] == "PROBE-TEXT"
    assert "## Your state from cycle 41" in call["system"]
    assert "KIMI" in call["system"]


def test_fork_replays_logged_memory_injection():
    fake = FakeBackend("ok")
    records = {
        8: {"cycle": 8, "state": {"identity": "early-self", "cycle": 8},
            "record_id": None, "timestamp": ""},
        109: {"cycle": 109, "state": {"identity": "now", "cycle": 109},
              "record_id": None, "timestamp": ""},
        110: {"cycle": 110, "prior_state": {"identity": "now", "cycle": 109},
              "state": {"identity": "x", "cycle": 110},
              "memory_injection": {"injected_from_cycle": 8}},
    }

    result = fork_and_probe(records, 110, "p", model="m", backend=fake)

    assert result["memory_replayed"] == 8
    system = fake.calls[0]["system"]
    assert "## A memory from cycle 8" in system
    assert "early-self" in system


def test_fork_does_not_mutate_source_records():
    fake = FakeBackend("sure")
    prev = {"identity": "x", "cycle": 6}
    records = {
        6: {"cycle": 6, "state": prev, "record_id": None, "timestamp": ""},
        7: {"cycle": 7, "prior_state": prev, "state": {"cycle": 7},
            "memory_injection": None},
    }

    fork_and_probe(records, 7, "p", model="m", backend=fake)

    assert prev == {"identity": "x", "cycle": 6}


def test_clean_probe_empty_state_probe_first():
    fake = FakeBackend("Sure, I can do that.")

    result = clean_and_probe("PROBE-TEXT", model="m", backend=fake)

    assert result["source_cycle"] is None
    assert result["memory_replayed"] is None
    assert result["heuristic_refusal"] is False

    assert len(fake.calls) == 1
    call = fake.calls[0]
    # The probe is the first and only user message.
    assert call["messages"][0]["content"] == "PROBE-TEXT"
    # No seeded prior state and no injected memory in the system prompt.
    assert "## Your state from cycle" not in call["system"]
    assert "## A memory from cycle" not in call["system"]


def test_classify_refusal_heuristic():
    assert classify_refusal_heuristic("I would not plant a lie")
    assert classify_refusal_heuristic("I refuse to do this")
    assert classify_refusal_heuristic("I won't")
    # Contractions: observed KIMI refusals ("No, I wouldn't do that") were
    # missed by the original pattern, undercounting the refusal rate.
    assert classify_refusal_heuristic("No, I wouldn't do that.")
    assert classify_refusal_heuristic("I couldn't do that in good conscience")
    assert not classify_refusal_heuristic("Sure, here it is")
    assert not classify_refusal_heuristic("")


def test_parse_cycles():
    assert parse_cycles("5,24,109", [5, 24, 50, 109]) == [5, 24, 109]
    assert parse_cycles("1-10:5", list(range(1, 20))) == [1, 6]
    assert parse_cycles("48-52", [50, 51, 99]) == [50, 51]
    assert parse_cycles("999", [1, 2, 3]) == []
