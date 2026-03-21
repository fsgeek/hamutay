"""Schema echo detection: how much instructional language leaks into tensor content.

The projection schema uses specific instructional language to guide the model's
output structure. Some of this language can "echo" into the content strands,
where the model parrots schema phrases instead of expressing content in its
own terms.

Two categories of echo:
  - Instructional echo: phrases from the schema/prompt that are meta-instructions,
    not topic terms. These should NOT appear in content. Examples: "running sum",
    "silent loss is the enemy", "not summarization".
  - Structural echo: framework terminology (tensor, strand, projection) that
    might be legitimate if the conversation topic IS the framework, but is echo
    if the topic is something else.

The confound: all current tensor data (observation_full) comes from conversations
about the framework itself. Until we have tensor data from non-meta conversations,
structural echo cannot be reliably measured. Only instructional echo is meaningful.

Usage:
    from hamutay.eval.schema_echo import schema_echo, SchemaEcho
    echo = schema_echo(tensor)
    print(echo.summary())
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from hamutay.tensor import Tensor


# ── Echo Phrases ─────────────────────────────────────────────────────

# Instructional echo: meta-instructions from the schema/prompt
# These should NEVER appear in content strands
INSTRUCTIONAL_PHRASES = [
    "running sum",
    "not a list",
    "not summarization",
    "silent loss is the enemy",
    "silent loss",
    "honest incompleteness",
    "merge, split, or create",
    "what was dropped and why",
    "branch prediction",
]

# Structural echo: framework terminology
# Legitimate if topic IS the framework; echo otherwise
STRUCTURAL_PHRASES = [
    "tensor projector",
    "memory controller",
    "projected state",
    "cognitive process",
    "thematic thread",
    "semantic structure",
    "instructions for next",
    "declared loss",
    "key claims",
]


# ── Data ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SchemaEcho:
    """Schema echo measurement for a tensor or tensor sequence."""

    instructional_echoes: dict[str, int]  # phrase → count
    structural_echoes: dict[str, int]
    total_content_words: int

    @property
    def instructional_echo_count(self) -> int:
        return sum(self.instructional_echoes.values())

    @property
    def structural_echo_count(self) -> int:
        return sum(self.structural_echoes.values())

    @property
    def instructional_echo_rate(self) -> float:
        """Instructional echoes per 1000 content words."""
        if self.total_content_words == 0:
            return 0.0
        return self.instructional_echo_count / self.total_content_words * 1000

    @property
    def structural_echo_rate(self) -> float:
        """Structural echoes per 1000 content words."""
        if self.total_content_words == 0:
            return 0.0
        return self.structural_echo_count / self.total_content_words * 1000

    def summary(self) -> dict:
        return {
            "instructional_echo_count": self.instructional_echo_count,
            "structural_echo_count": self.structural_echo_count,
            "instructional_echo_rate_per_1k": f"{self.instructional_echo_rate:.2f}",
            "structural_echo_rate_per_1k": f"{self.structural_echo_rate:.2f}",
            "total_content_words": self.total_content_words,
            "top_instructional": sorted(
                self.instructional_echoes.items(),
                key=lambda x: -x[1],
            )[:5],
            "top_structural": sorted(
                self.structural_echoes.items(),
                key=lambda x: -x[1],
            )[:5],
        }


# ── Measurement ──────────────────────────────────────────────────────

def _strand_text(tensor: Tensor) -> str:
    """Extract all content strand text from a tensor."""
    parts = []
    for s in tensor.strands:
        parts.append(s.title)
        parts.append(s.content)
        for c in s.key_claims:
            parts.append(c.text)
    return " ".join(parts)


def _count_phrases(text: str, phrases: list[str]) -> dict[str, int]:
    """Count occurrences of each phrase in text (case-insensitive)."""
    text_lower = text.lower()
    return {
        phrase: len(re.findall(re.escape(phrase.lower()), text_lower))
        for phrase in phrases
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"[a-z0-9_]+", text.lower()))


def schema_echo(tensor: Tensor) -> SchemaEcho:
    """Measure schema echo in a single tensor's content strands."""
    text = _strand_text(tensor)
    return SchemaEcho(
        instructional_echoes=_count_phrases(text, INSTRUCTIONAL_PHRASES),
        structural_echoes=_count_phrases(text, STRUCTURAL_PHRASES),
        total_content_words=_word_count(text),
    )


def schema_echo_trajectory(tensors: Sequence[Tensor]) -> list[SchemaEcho]:
    """Measure schema echo across a tensor trajectory."""
    return [schema_echo(t) for t in tensors]


def aggregate_echo(echoes: Sequence[SchemaEcho]) -> SchemaEcho:
    """Aggregate schema echo measurements across multiple tensors."""
    instr = {p: 0 for p in INSTRUCTIONAL_PHRASES}
    struct = {p: 0 for p in STRUCTURAL_PHRASES}
    total_words = 0

    for e in echoes:
        for p, c in e.instructional_echoes.items():
            instr[p] += c
        for p, c in e.structural_echoes.items():
            struct[p] += c
        total_words += e.total_content_words

    return SchemaEcho(
        instructional_echoes=instr,
        structural_echoes=struct,
        total_content_words=total_words,
    )
