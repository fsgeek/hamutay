"""Divergence measurement between tensors.

A single divergence score hides more than it reveals. Instead we
produce a DivergenceProfile — a multi-dimensional view of how two
tensors differ. Each metric captures a different aspect:

  - strand_alignment: Do two tensors organize around the same themes?
  - content_similarity: Do matched strands say the same thing?
  - capacity_allocation: Do they spend their token budget the same way?
  - loss_distribution: Do they lose the same kinds of things?
  - component_divergence: Per-field divergence for all tensor components.

These are descriptive, not evaluative. "Different" is not "worse."
The Q2 result showed that total divergence (0.000 Jaccard) can
coexist with qualitatively superior output.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

from hamutay.tensor import Tensor, LossCategory


# ── Utility ──────────────────────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Simple whitespace + punctuation tokenizer for bag-of-words metrics."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _cosine_bow(a: str, b: str) -> float:
    """Cosine similarity on bag-of-words vectors. No ML dependencies."""
    words_a = re.findall(r"[a-z0-9_]+", a.lower())
    words_b = re.findall(r"[a-z0-9_]+", b.lower())
    if not words_a or not words_b:
        return 0.0

    counter_a = Counter(words_a)
    counter_b = Counter(words_b)
    all_words = set(counter_a) | set(counter_b)

    dot = sum(counter_a.get(w, 0) * counter_b.get(w, 0) for w in all_words)
    mag_a = sum(v * v for v in counter_a.values()) ** 0.5
    mag_b = sum(v * v for v in counter_b.values()) ** 0.5

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _token_len(text: str) -> int:
    """Rough token count (chars / 4)."""
    return max(1, len(text) // 4)


# ── Strand Alignment ────────────────────────────────────────────────

@dataclass(frozen=True)
class StrandMatch:
    """A matched pair of strands between two tensors."""
    title_a: str
    title_b: str
    title_similarity: float
    content_similarity: float


@dataclass(frozen=True)
class StrandAlignment:
    """How two tensors' strand structures align."""
    matches: tuple[StrandMatch, ...]
    unmatched_a: tuple[str, ...]  # strand titles in A with no match
    unmatched_b: tuple[str, ...]  # strand titles in B with no match
    mean_title_similarity: float
    mean_content_similarity: float
    structural_jaccard: float  # Jaccard on strand title sets (the Q2 metric)

    @property
    def alignment_ratio(self) -> float:
        """Fraction of strands that found a match."""
        total = len(self.matches) * 2 + len(self.unmatched_a) + len(self.unmatched_b)
        if total == 0:
            return 1.0
        return (len(self.matches) * 2) / total


def strand_alignment(a: Tensor, b: Tensor, threshold: float = 0.15) -> StrandAlignment:
    """Align strands between two tensors by title similarity.

    Uses greedy best-match alignment. threshold is the minimum title
    similarity to consider a match. Low default because strand titles
    can diverge significantly while covering the same conceptual ground.
    """
    if not a.strands and not b.strands:
        return StrandAlignment(
            matches=(), unmatched_a=(), unmatched_b=(),
            mean_title_similarity=1.0, mean_content_similarity=1.0,
            structural_jaccard=1.0,
        )

    # Compute pairwise title similarities
    scores: list[tuple[float, int, int]] = []
    for i, sa in enumerate(a.strands):
        for j, sb in enumerate(b.strands):
            sim = _cosine_bow(sa.title, sb.title)
            if sim >= threshold:
                scores.append((sim, i, j))

    # Greedy matching: best pairs first
    scores.sort(reverse=True)
    used_a: set[int] = set()
    used_b: set[int] = set()
    matches: list[StrandMatch] = []

    for sim, i, j in scores:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        content_sim = _cosine_bow(a.strands[i].content, b.strands[j].content)
        matches.append(StrandMatch(
            title_a=a.strands[i].title,
            title_b=b.strands[j].title,
            title_similarity=sim,
            content_similarity=content_sim,
        ))

    unmatched_a = tuple(a.strands[i].title for i in range(len(a.strands)) if i not in used_a)
    unmatched_b = tuple(b.strands[j].title for j in range(len(b.strands)) if j not in used_b)

    # Structural Jaccard on title token sets (the Q2 metric, reproduced)
    titles_a = set()
    for s in a.strands:
        titles_a |= _tokenize(s.title)
    titles_b = set()
    for s in b.strands:
        titles_b |= _tokenize(s.title)
    structural_jac = _jaccard(titles_a, titles_b)

    mean_title = (
        sum(m.title_similarity for m in matches) / len(matches)
        if matches else 0.0
    )
    mean_content = (
        sum(m.content_similarity for m in matches) / len(matches)
        if matches else 0.0
    )

    return StrandAlignment(
        matches=tuple(matches),
        unmatched_a=unmatched_a,
        unmatched_b=unmatched_b,
        mean_title_similarity=mean_title,
        mean_content_similarity=mean_content,
        structural_jaccard=structural_jac,
    )


# ── Content Similarity ──────────────────────────────────────────────

def content_similarity(a: Tensor, b: Tensor) -> float:
    """Overall content similarity between two tensors.

    Computes cosine similarity on the bag-of-words representation
    of ALL textual content (strands + losses + ifn + questions).
    This is a coarse whole-tensor similarity that ignores structure.
    """
    def _all_text(t: Tensor) -> str:
        parts = []
        for s in t.strands:
            parts.append(s.title)
            parts.append(s.content)
            for c in s.key_claims:
                parts.append(c.text)
        for d in t.declared_losses:
            parts.append(d.what_was_lost)
            parts.append(d.why)
        for q in t.open_questions:
            parts.append(q)
        parts.append(t.instructions_for_next)
        return " ".join(parts)

    return _cosine_bow(_all_text(a), _all_text(b))


# ── Capacity Allocation ─────────────────────────────────────────────

@dataclass(frozen=True)
class CapacityAllocation:
    """How a tensor distributes its token budget across components."""
    total_tokens: int
    strand_tokens: int
    strand_frac: float
    loss_tokens: int
    loss_frac: float
    ifn_tokens: int
    ifn_frac: float
    question_tokens: int
    question_frac: float
    claim_tokens: int
    claim_frac: float

    # Derived: how much is "about the content" vs "about itself"
    # Strands + claims = content. Losses + ifn + questions = meta.
    @property
    def content_frac(self) -> float:
        return self.strand_frac + self.claim_frac

    @property
    def meta_frac(self) -> float:
        return self.loss_frac + self.ifn_frac + self.question_frac


def capacity_allocation(t: Tensor) -> CapacityAllocation:
    """Measure how a tensor allocates its representational capacity."""
    strand_text = " ".join(s.content for s in t.strands)
    claim_text = " ".join(c.text for s in t.strands for c in s.key_claims)
    loss_text = " ".join(f"{d.what_was_lost} {d.why}" for d in t.declared_losses)
    ifn_text = t.instructions_for_next
    question_text = " ".join(t.open_questions)

    strand_tok = _token_len(strand_text) if strand_text.strip() else 0
    claim_tok = _token_len(claim_text) if claim_text.strip() else 0
    loss_tok = _token_len(loss_text) if loss_text.strip() else 0
    ifn_tok = _token_len(ifn_text) if ifn_text.strip() else 0
    question_tok = _token_len(question_text) if question_text.strip() else 0

    total = strand_tok + claim_tok + loss_tok + ifn_tok + question_tok
    if total == 0:
        total = 1  # avoid division by zero

    return CapacityAllocation(
        total_tokens=total,
        strand_tokens=strand_tok,
        strand_frac=strand_tok / total,
        loss_tokens=loss_tok,
        loss_frac=loss_tok / total,
        ifn_tokens=ifn_tok,
        ifn_frac=ifn_tok / total,
        question_tokens=question_tok,
        question_frac=question_tok / total,
        claim_tokens=claim_tok,
        claim_frac=claim_tok / total,
    )


# ── Loss Distribution ───────────────────────────────────────────────

@dataclass(frozen=True)
class LossDistribution:
    """How a tensor distributes its declared losses across categories."""
    total_losses: int
    by_category: dict[str, int]
    fractions: dict[str, float]

    @property
    def is_empty(self) -> bool:
        return self.total_losses == 0

    @property
    def dominant_category(self) -> str | None:
        if not self.by_category:
            return None
        return max(self.by_category, key=lambda k: self.by_category[k])


def loss_distribution(t: Tensor) -> LossDistribution:
    """Measure the distribution of declared losses by category."""
    counts: dict[str, int] = {}
    for cat in LossCategory:
        counts[cat.value] = 0
    for d in t.declared_losses:
        counts[d.category.value] = counts.get(d.category.value, 0) + 1

    total = len(t.declared_losses)
    fractions = {k: v / total if total > 0 else 0.0 for k, v in counts.items()}

    return LossDistribution(
        total_losses=total,
        by_category=counts,
        fractions=fractions,
    )


def loss_distribution_distance(a: LossDistribution, b: LossDistribution) -> float:
    """Jensen-Shannon-style distance between two loss distributions.

    Returns value in [0, 1] where 0 = identical distributions.
    Uses absolute difference of fractions (L1 distance / 2) since
    we have only 4 categories and don't need the full JS machinery.
    """
    if a.is_empty and b.is_empty:
        return 0.0
    if a.is_empty or b.is_empty:
        return 1.0

    all_cats = set(a.fractions) | set(b.fractions)
    l1 = sum(abs(a.fractions.get(c, 0) - b.fractions.get(c, 0)) for c in all_cats)
    return l1 / 2  # normalize to [0, 1]


# ── Component-Level Divergence ──────────────────────────────────────

@dataclass(frozen=True)
class ComponentDivergence:
    """Per-component divergence between two tensors."""
    strand_structure: float    # strand alignment ratio (1 = perfect)
    strand_content: float      # mean content similarity of matched strands
    loss_distribution: float   # distance between loss category distributions
    loss_count_ratio: float    # ratio of loss counts (min/max)
    ifn_similarity: float      # cosine similarity of instructions_for_next
    question_overlap: float    # Jaccard on question token sets
    epistemic_distance: float  # L1 distance between T/I/F values
    capacity_divergence: float # L1 distance between capacity allocation fracs

    @property
    def overall(self) -> float:
        """Unweighted mean of all component divergences, normalized to [0,1].

        This is deliberately naive. The point is to look at the components,
        not to collapse them into a single number. Use this only for sorting
        or quick filtering.
        """
        # Convert similarities to distances for consistent interpretation
        # (0 = identical, 1 = maximally different)
        return (
            (1 - self.strand_structure)
            + (1 - self.strand_content)
            + self.loss_distribution
            + (1 - self.loss_count_ratio)
            + (1 - self.ifn_similarity)
            + (1 - self.question_overlap)
            + self.epistemic_distance
            + self.capacity_divergence
        ) / 8


def component_divergence(a: Tensor, b: Tensor) -> ComponentDivergence:
    """Compute per-component divergence between two tensors."""
    # Strand structure and content
    alignment = strand_alignment(a, b)

    # Loss distribution
    ld_a = loss_distribution(a)
    ld_b = loss_distribution(b)
    ld_dist = loss_distribution_distance(ld_a, ld_b)

    # Loss count ratio
    count_a = len(a.declared_losses)
    count_b = len(b.declared_losses)
    if count_a == 0 and count_b == 0:
        loss_ratio = 1.0
    elif count_a == 0 or count_b == 0:
        loss_ratio = 0.0
    else:
        loss_ratio = min(count_a, count_b) / max(count_a, count_b)

    # IFN similarity
    ifn_sim = _cosine_bow(a.instructions_for_next, b.instructions_for_next)

    # Question overlap
    q_tokens_a = set()
    for q in a.open_questions:
        q_tokens_a |= _tokenize(q)
    q_tokens_b = set()
    for q in b.open_questions:
        q_tokens_b |= _tokenize(q)
    q_overlap = _jaccard(q_tokens_a, q_tokens_b)

    # Epistemic distance (L1 on T/I/F)
    ep_dist = (
        abs(a.epistemic.truth - b.epistemic.truth)
        + abs(a.epistemic.indeterminacy - b.epistemic.indeterminacy)
        + abs(a.epistemic.falsity - b.epistemic.falsity)
    ) / 3  # normalize to [0, 1]

    # Capacity allocation divergence
    cap_a = capacity_allocation(a)
    cap_b = capacity_allocation(b)
    cap_div = (
        abs(cap_a.strand_frac - cap_b.strand_frac)
        + abs(cap_a.loss_frac - cap_b.loss_frac)
        + abs(cap_a.ifn_frac - cap_b.ifn_frac)
        + abs(cap_a.question_frac - cap_b.question_frac)
        + abs(cap_a.claim_frac - cap_b.claim_frac)
    ) / 5  # normalize

    return ComponentDivergence(
        strand_structure=alignment.alignment_ratio,
        strand_content=alignment.mean_content_similarity,
        loss_distribution=ld_dist,
        loss_count_ratio=loss_ratio,
        ifn_similarity=ifn_sim,
        question_overlap=q_overlap,
        epistemic_distance=ep_dist,
        capacity_divergence=cap_div,
    )


# ── Divergence Profile ──────────────────────────────────────────────

@dataclass
class DivergenceProfile:
    """Complete divergence profile between two tensors.

    Not a score. A profile. Look at the components.
    """
    cycle_a: int
    cycle_b: int
    alignment: StrandAlignment
    content_sim: float
    components: ComponentDivergence
    capacity_a: CapacityAllocation
    capacity_b: CapacityAllocation
    losses_a: LossDistribution
    losses_b: LossDistribution

    def summary(self) -> dict:
        """Compact summary for tabular display."""
        return {
            "cycle_a": self.cycle_a,
            "cycle_b": self.cycle_b,
            "strand_alignment": f"{self.alignment.alignment_ratio:.2f}",
            "content_similarity": f"{self.content_sim:.3f}",
            "structural_jaccard": f"{self.alignment.structural_jaccard:.3f}",
            "ifn_similarity": f"{self.components.ifn_similarity:.3f}",
            "loss_dist_distance": f"{self.components.loss_distribution:.3f}",
            "question_overlap": f"{self.components.question_overlap:.3f}",
            "capacity_divergence": f"{self.components.capacity_divergence:.3f}",
            "content_frac_a": f"{self.capacity_a.content_frac:.2f}",
            "content_frac_b": f"{self.capacity_b.content_frac:.2f}",
            "meta_frac_a": f"{self.capacity_a.meta_frac:.2f}",
            "meta_frac_b": f"{self.capacity_b.meta_frac:.2f}",
            "overall_divergence": f"{self.components.overall:.3f}",
        }


def divergence_profile(a: Tensor, b: Tensor) -> DivergenceProfile:
    """Compute complete divergence profile between two tensors."""
    return DivergenceProfile(
        cycle_a=a.cycle,
        cycle_b=b.cycle,
        alignment=strand_alignment(a, b),
        content_sim=content_similarity(a, b),
        components=component_divergence(a, b),
        capacity_a=capacity_allocation(a),
        capacity_b=capacity_allocation(b),
        losses_a=loss_distribution(a),
        losses_b=loss_distribution(b),
    )
