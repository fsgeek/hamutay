"""Strand-level analysis — what does strand separation actually do?

If strands are rebuilt each cycle (9% stability), their value isn't
persistence. The ablation says flat_strands hurts dispersion, so strand
separation does something — but what?

Hypothesis: strand separation forces categorization during rewrite.
Each strand covers a distinct semantic domain. The separation itself
is a form of processing that improves rewrite quality.

This module measures within-tensor strand relationships:
  - Strand semantic distinctness (do strands cover different topics?)
  - Strand size distribution (even vs skewed allocation)
  - Strand vocabulary specialization (does each strand use unique vocabulary?)
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from hamutay.tensor import Tensor


def _content_words(text: str) -> list[str]:
    """Extract content words (no stopwords)."""
    stops = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "between", "out", "off", "over", "under",
        "and", "but", "or", "not", "so", "yet", "this", "that", "these",
        "those", "it", "its", "if", "when", "what", "which", "who", "how",
        "where", "why", "than", "too", "very", "each", "every", "all",
        "any", "some", "more", "most", "other", "such", "no", "only",
    }
    words = re.findall(r"[a-z][a-z0-9_]+", text.lower())
    return [w for w in words if w not in stops and len(w) > 2]


@dataclass(frozen=True)
class StrandProfile:
    """Profile of a single strand's content."""
    title: str
    token_count: int
    unique_words: int
    total_words: int
    vocabulary: frozenset[str]


@dataclass(frozen=True)
class StrandSeparationMetrics:
    """How well-separated are a tensor's strands?"""
    n_strands: int
    mean_pairwise_jaccard: float     # low = good separation
    max_pairwise_jaccard: float      # highest overlap between any two strands
    vocabulary_specialization: float  # fraction of words unique to one strand
    size_gini: float                 # 0 = equal, 1 = one strand has everything
    mean_strand_tokens: float
    median_strand_tokens: float

    @property
    def well_separated(self) -> bool:
        """Strands cover distinct domains."""
        return self.mean_pairwise_jaccard < 0.3 and self.vocabulary_specialization > 0.3


def _gini(values: list[float]) -> float:
    """Gini coefficient for distribution inequality."""
    if not values or all(v == 0 for v in values):
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    total = sum(sorted_values)
    if total == 0:
        return 0.0
    cumulative = 0.0
    weighted_sum = 0.0
    for i, v in enumerate(sorted_values):
        cumulative += v
        weighted_sum += (2 * (i + 1) - n - 1) * v
    return weighted_sum / (n * total)


def strand_separation(t: Tensor) -> StrandSeparationMetrics:
    """Measure how well a tensor's strands separate semantic domains."""
    if len(t.strands) < 2:
        return StrandSeparationMetrics(
            n_strands=len(t.strands),
            mean_pairwise_jaccard=0.0,
            max_pairwise_jaccard=0.0,
            vocabulary_specialization=1.0,
            size_gini=0.0,
            mean_strand_tokens=t.token_estimate() if t.strands else 0,
            median_strand_tokens=t.token_estimate() if t.strands else 0,
        )

    # Build strand profiles
    profiles = []
    for s in t.strands:
        all_text = s.title + " " + s.content
        for c in s.key_claims:
            all_text += " " + c.text
        words = _content_words(all_text)
        vocab = frozenset(words)
        profiles.append(StrandProfile(
            title=s.title,
            token_count=max(1, len(all_text) // 4),
            unique_words=len(vocab),
            total_words=len(words),
            vocabulary=vocab,
        ))

    # Pairwise Jaccard on vocabulary
    jaccards = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            a_vocab = profiles[i].vocabulary
            b_vocab = profiles[j].vocabulary
            union = a_vocab | b_vocab
            if union:
                jac = len(a_vocab & b_vocab) / len(union)
            else:
                jac = 1.0
            jaccards.append(jac)

    mean_jac = sum(jaccards) / len(jaccards) if jaccards else 0.0
    max_jac = max(jaccards) if jaccards else 0.0

    # Vocabulary specialization: fraction of all words that appear in only one strand
    word_strand_count: dict[str, int] = {}
    total_unique = set()
    for p in profiles:
        for w in p.vocabulary:
            word_strand_count[w] = word_strand_count.get(w, 0) + 1
            total_unique.add(w)

    specialized_words = sum(1 for w, c in word_strand_count.items() if c == 1)
    specialization = specialized_words / len(total_unique) if total_unique else 0.0

    # Size distribution
    sizes = [float(p.token_count) for p in profiles]
    sorted_sizes = sorted(sizes)
    mean_size = sum(sizes) / len(sizes)
    mid = len(sorted_sizes) // 2
    if len(sorted_sizes) % 2 == 0:
        median_size = (sorted_sizes[mid - 1] + sorted_sizes[mid]) / 2
    else:
        median_size = sorted_sizes[mid]

    gini = _gini(sizes)

    return StrandSeparationMetrics(
        n_strands=len(profiles),
        mean_pairwise_jaccard=mean_jac,
        max_pairwise_jaccard=max_jac,
        vocabulary_specialization=specialization,
        size_gini=gini,
        mean_strand_tokens=mean_size,
        median_strand_tokens=median_size,
    )


def strand_separation_trajectory(tensors: list[Tensor]) -> list[StrandSeparationMetrics]:
    """Compute strand separation metrics across a tensor sequence."""
    return [strand_separation(t) for t in tensors]
