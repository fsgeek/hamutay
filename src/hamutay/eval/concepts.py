"""Concept persistence tracking across tensor sequences.

Strands are ephemeral — 9% stability in Q2 data. But content persists
(0.711-0.887 similarity across conditions). This means the *concepts*
persist while the *organization* is rebuilt each cycle.

This module tracks concepts rather than strands. A concept is a
cluster of semantically related content that may move between strands,
split, merge, or transform across cycles.

Approach: extract key phrases from each tensor, track which phrases
persist, appear, or disappear across cycles. This is cheaper than
embedding-based tracking and transparent — you can see exactly what
persisted and what didn't.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from hamutay.tensor import Tensor


def _extract_phrases(text: str, min_len: int = 2, max_len: int = 4) -> list[tuple[str, ...]]:
    """Extract n-gram phrases from text.

    Uses word-level n-grams (bigrams through 4-grams) as concept proxies.
    Filters out purely functional phrases.
    """
    # Simple stopwords — enough to filter function words without a dependency
    stops = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "and", "but", "or",
        "nor", "not", "so", "yet", "both", "either", "neither", "each",
        "every", "all", "any", "few", "more", "most", "other", "some",
        "such", "no", "only", "own", "same", "than", "too", "very",
        "this", "that", "these", "those", "it", "its", "if", "when",
        "what", "which", "who", "whom", "how", "where", "why",
    }

    words = re.findall(r"[a-z][a-z0-9_]+", text.lower())
    # Filter stopwords but keep at least one content word per n-gram
    content_words = [w for w in words if w not in stops and len(w) > 2]

    phrases = []
    for n in range(min_len, max_len + 1):
        for i in range(len(content_words) - n + 1):
            phrase = tuple(content_words[i:i + n])
            phrases.append(phrase)

    return phrases


def _phrase_key(phrase: tuple[str, ...]) -> str:
    """Convert phrase tuple to comparable string."""
    return " ".join(phrase)


@dataclass(frozen=True)
class ConceptSnapshot:
    """Concepts present in a single tensor."""
    cycle: int
    phrases: frozenset[str]  # set of phrase keys
    phrase_counts: dict[str, int]  # how often each phrase appears


@dataclass
class ConceptLifespan:
    """Track a concept's presence across cycles."""
    phrase: str
    first_seen: int
    last_seen: int
    present_cycles: list[int]
    absent_cycles: list[int] = field(default_factory=list)

    @property
    def total_cycles_present(self) -> int:
        return len(self.present_cycles)

    @property
    def persistence_ratio(self) -> float:
        """Fraction of cycles (from first to last seen) where concept was present."""
        span = self.last_seen - self.first_seen + 1
        if span <= 0:
            return 1.0
        return self.total_cycles_present / span

    @property
    def is_transient(self) -> bool:
        """Present for only 1 cycle."""
        return self.total_cycles_present == 1

    @property
    def is_persistent(self) -> bool:
        """Present for >50% of its lifespan and at least 5 cycles."""
        return self.persistence_ratio > 0.5 and self.total_cycles_present >= 5

    @property
    def is_intermittent(self) -> bool:
        """Appears, disappears, reappears."""
        return len(self.absent_cycles) > 0 and self.total_cycles_present > 1


@dataclass
class ConceptTrajectory:
    """Concept dynamics across a tensor sequence."""
    total_cycles: int
    total_unique_concepts: int
    lifespans: dict[str, ConceptLifespan]

    @property
    def persistent_concepts(self) -> list[ConceptLifespan]:
        return sorted(
            [l for l in self.lifespans.values() if l.is_persistent],
            key=lambda l: l.total_cycles_present,
            reverse=True,
        )

    @property
    def transient_concepts(self) -> list[ConceptLifespan]:
        return [l for l in self.lifespans.values() if l.is_transient]

    @property
    def intermittent_concepts(self) -> list[ConceptLifespan]:
        return sorted(
            [l for l in self.lifespans.values() if l.is_intermittent],
            key=lambda l: l.total_cycles_present,
            reverse=True,
        )

    @property
    def persistence_ratio(self) -> float:
        """Fraction of concepts that are persistent."""
        if self.total_unique_concepts == 0:
            return 0.0
        return len(self.persistent_concepts) / self.total_unique_concepts

    @property
    def transience_ratio(self) -> float:
        """Fraction of concepts that appear only once."""
        if self.total_unique_concepts == 0:
            return 0.0
        return len(self.transient_concepts) / self.total_unique_concepts

    def summary(self) -> dict:
        return {
            "total_cycles": self.total_cycles,
            "unique_concepts": self.total_unique_concepts,
            "persistent": len(self.persistent_concepts),
            "transient": len(self.transient_concepts),
            "intermittent": len(self.intermittent_concepts),
            "persistence_ratio": f"{self.persistence_ratio:.3f}",
            "transience_ratio": f"{self.transience_ratio:.3f}",
            "top_persistent": [
                f"{l.phrase} ({l.total_cycles_present} cycles, {l.persistence_ratio:.0%})"
                for l in self.persistent_concepts[:10]
            ],
        }


def _extract_tensor_concepts(t: Tensor) -> ConceptSnapshot:
    """Extract concepts from a single tensor."""
    all_text = []
    for s in t.strands:
        all_text.append(s.title)
        all_text.append(s.content)
        for c in s.key_claims:
            all_text.append(c.text)
    # Include declared losses — they carry conceptual content
    for d in t.declared_losses:
        all_text.append(d.what_was_lost)
    # IFN carries concept references too
    all_text.append(t.instructions_for_next)

    combined = " ".join(all_text)
    raw_phrases = _extract_phrases(combined)
    phrase_keys = [_phrase_key(p) for p in raw_phrases]

    counts = Counter(phrase_keys)

    return ConceptSnapshot(
        cycle=t.cycle,
        phrases=frozenset(counts.keys()),
        phrase_counts=dict(counts),
    )


def concept_trajectory(tensors: list[Tensor]) -> ConceptTrajectory:
    """Track concept persistence across a tensor sequence."""
    snapshots = [_extract_tensor_concepts(t) for t in tensors]

    # Build lifespans
    lifespans: dict[str, ConceptLifespan] = {}
    all_cycles = [s.cycle for s in snapshots]

    for snapshot in snapshots:
        for phrase in snapshot.phrases:
            if phrase not in lifespans:
                lifespans[phrase] = ConceptLifespan(
                    phrase=phrase,
                    first_seen=snapshot.cycle,
                    last_seen=snapshot.cycle,
                    present_cycles=[snapshot.cycle],
                )
            else:
                ls = lifespans[phrase]
                ls.last_seen = snapshot.cycle
                ls.present_cycles.append(snapshot.cycle)

    # Fill in absent cycles
    for phrase, ls in lifespans.items():
        present_set = set(ls.present_cycles)
        for cycle in all_cycles:
            if ls.first_seen <= cycle <= ls.last_seen and cycle not in present_set:
                ls.absent_cycles.append(cycle)

    return ConceptTrajectory(
        total_cycles=len(tensors),
        total_unique_concepts=len(lifespans),
        lifespans=lifespans,
    )


def concept_overlap(a: ConceptTrajectory, b: ConceptTrajectory) -> dict:
    """Compare concept vocabularies between two trajectories.

    Returns metrics about shared vs unique concepts.
    """
    a_concepts = set(a.lifespans.keys())
    b_concepts = set(b.lifespans.keys())

    shared = a_concepts & b_concepts
    only_a = a_concepts - b_concepts
    only_b = b_concepts - a_concepts

    # Among shared concepts, how do their lifespans compare?
    shared_persistence_corr = []
    for phrase in shared:
        a_ratio = a.lifespans[phrase].persistence_ratio
        b_ratio = b.lifespans[phrase].persistence_ratio
        shared_persistence_corr.append((a_ratio, b_ratio))

    jaccard = len(shared) / len(a_concepts | b_concepts) if (a_concepts | b_concepts) else 1.0

    return {
        "shared_count": len(shared),
        "only_a_count": len(only_a),
        "only_b_count": len(only_b),
        "concept_jaccard": jaccard,
        "shared_top": sorted(
            shared,
            key=lambda p: a.lifespans[p].total_cycles_present + b.lifespans[p].total_cycles_present,
            reverse=True,
        )[:20],
    }
