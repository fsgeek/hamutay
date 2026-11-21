"""Validate the fifth question's assented text against resident constitutions."""

from pathlib import Path
import re

import pytest

from hamutay import heartbeat


@pytest.fixture(scope="module")
def values_sentence():
    proposal = (
        Path(__file__).resolve().parents[2] / "deploy/plaza/fifth-question.txt"
    ).read_text(encoding="utf-8")
    # Start after the introduction line, which itself quotes the opening.
    sentences = re.findall(
        r'^The sentence,[^\n]*:[ \t]*\n\s*"([^"]+)"', proposal, re.MULTILINE
    )
    assert len(sentences) == 1, "Expected exactly one introduced quoted sentence"
    sentence = sentences[0]
    assert sentence.startswith("This community has not adopted any shared values.")
    return sentence


def test_constitution_contains_values_sentence_exactly_once(values_sentence):
    assert heartbeat.CONSTITUTION.count(values_sentence) == 1


def test_values_sentence_immediately_follows_opening(values_sentence):
    opening = "You are a resident of a small community running on an event loop. "
    assert heartbeat.CONSTITUTION.startswith(opening + values_sentence)


@pytest.mark.parametrize("budgeted", [True, False], ids=["budgeted", "unbudgeted"])
def test_resident_constitution_contains_values_sentence(values_sentence, budgeted):
    budget = heartbeat.WakeBudget(1.25, 7) if budgeted else None
    constitution = heartbeat.build_constitution(budget)
    assert values_sentence in heartbeat._CONSTITUTION_BASE
    assert constitution.count(values_sentence) == 1
