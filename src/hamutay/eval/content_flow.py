"""Content flow analysis — tracking what survives the rewrite.

The tensor rewrites almost everything each cycle (9% strand stability)
but preserves 71-89% of semantic content. This module investigates
that gap: what specific content persists, what gets dropped, and
what determines survival.

Operates on a sequence of full tensors (as dicts with strands,
declared_losses, instructions_for_next, etc.).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field


def _extract_ngrams(text: str, n: int = 3) -> set[str]:
    """Extract word n-grams from text, lowercased."""
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    if len(words) < n:
        return set(words)
    return {" ".join(words[i:i+n]) for i in range(len(words) - n + 1)}


def _extract_content(tensor: dict) -> str:
    """Extract all semantic content from a tensor."""
    parts = []
    for strand in tensor.get("strands", []):
        parts.append(strand.get("title", ""))
        parts.append(strand.get("content", ""))
        for claim in strand.get("key_claims", []):
            parts.append(claim.get("text", ""))
    return " ".join(parts)


def _extract_meta(tensor: dict) -> str:
    """Extract metacognitive content from a tensor."""
    parts = []
    for loss in tensor.get("declared_losses", []):
        parts.append(loss.get("what_was_lost", ""))
        parts.append(loss.get("why", ""))
    parts.append(tensor.get("instructions_for_next", ""))
    for q in tensor.get("open_questions", []):
        parts.append(q)
    return " ".join(parts)


@dataclass
class ContentFlowRecord:
    """What happened to content between two consecutive cycles."""
    cycle: int
    prior_cycle: int

    # n-gram overlap between consecutive tensors
    content_ngrams_prior: int = 0
    content_ngrams_current: int = 0
    content_ngrams_shared: int = 0
    content_survival_rate: float = 0.0  # shared / prior

    # n-gram overlap in meta fields
    meta_ngrams_prior: int = 0
    meta_ngrams_current: int = 0
    meta_ngrams_shared: int = 0
    meta_survival_rate: float = 0.0

    # What the tensor itself reports losing
    n_declared_losses: int = 0
    loss_categories: dict[str, int] = field(default_factory=dict)

    # Structural changes
    strands_prior: int = 0
    strands_current: int = 0
    titles_shared: int = 0  # exact title matches


@dataclass
class ContentLifespan:
    """Tracks how long specific n-grams persist across cycles."""
    ngram: str
    first_seen: int  # cycle number
    last_seen: int
    total_appearances: int
    consecutive_runs: list[tuple[int, int]] = field(default_factory=list)  # (start, end) of unbroken runs

    @property
    def lifespan(self) -> int:
        return self.last_seen - self.first_seen + 1

    @property
    def longest_run(self) -> int:
        if not self.consecutive_runs:
            return 0
        return max(end - start + 1 for start, end in self.consecutive_runs)


def analyze_consecutive_flow(tensors: list[dict]) -> list[ContentFlowRecord]:
    """Analyze content flow between each pair of consecutive tensors."""
    records = []

    for i in range(1, len(tensors)):
        prior = tensors[i - 1]
        current = tensors[i]

        prior_content = _extract_ngrams(_extract_content(prior))
        current_content = _extract_ngrams(_extract_content(current))
        shared_content = prior_content & current_content

        prior_meta = _extract_ngrams(_extract_meta(prior))
        current_meta = _extract_ngrams(_extract_meta(current))
        shared_meta = prior_meta & current_meta

        prior_titles = {s.get("title", "") for s in prior.get("strands", [])}
        current_titles = {s.get("title", "") for s in current.get("strands", [])}

        losses = current.get("declared_losses", [])
        categories: dict[str, int] = {}
        for loss in losses:
            cat = loss.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        records.append(ContentFlowRecord(
            cycle=current.get("cycle", i),
            prior_cycle=prior.get("cycle", i - 1),
            content_ngrams_prior=len(prior_content),
            content_ngrams_current=len(current_content),
            content_ngrams_shared=len(shared_content),
            content_survival_rate=len(shared_content) / len(prior_content) if prior_content else 0.0,
            meta_ngrams_prior=len(prior_meta),
            meta_ngrams_current=len(current_meta),
            meta_ngrams_shared=len(shared_meta),
            meta_survival_rate=len(shared_meta) / len(prior_meta) if prior_meta else 0.0,
            n_declared_losses=len(losses),
            loss_categories=categories,
            strands_prior=len(prior.get("strands", [])),
            strands_current=len(current.get("strands", [])),
            titles_shared=len(prior_titles & current_titles),
        ))

    return records


def track_ngram_lifespans(
    tensors: list[dict],
    n: int = 3,
    min_appearances: int = 3,
) -> list[ContentLifespan]:
    """Track how long specific n-grams survive across cycles.

    Returns lifespans for n-grams that appear in at least min_appearances cycles.
    """
    # Build cycle -> ngram set mapping
    cycle_ngrams: list[tuple[int, set[str]]] = []
    for tensor in tensors:
        cycle = tensor.get("cycle", len(cycle_ngrams))
        text = _extract_content(tensor) + " " + _extract_meta(tensor)
        ngrams = _extract_ngrams(text, n)
        cycle_ngrams.append((cycle, ngrams))

    # Count appearances per ngram
    ngram_cycles: dict[str, list[int]] = {}
    for cycle, ngrams in cycle_ngrams:
        for ng in ngrams:
            if ng not in ngram_cycles:
                ngram_cycles[ng] = []
            ngram_cycles[ng].append(cycle)

    # Build lifespans for persistent ngrams
    lifespans = []
    for ng, cycles in ngram_cycles.items():
        if len(cycles) < min_appearances:
            continue

        # Find consecutive runs
        sorted_cycles = sorted(cycles)
        runs: list[tuple[int, int]] = []
        run_start = sorted_cycles[0]
        prev = sorted_cycles[0]
        for c in sorted_cycles[1:]:
            if c == prev + 1:
                prev = c
            else:
                runs.append((run_start, prev))
                run_start = c
                prev = c
        runs.append((run_start, prev))

        lifespans.append(ContentLifespan(
            ngram=ng,
            first_seen=sorted_cycles[0],
            last_seen=sorted_cycles[-1],
            total_appearances=len(cycles),
            consecutive_runs=runs,
        ))

    # Sort by lifespan descending
    lifespans.sort(key=lambda x: x.lifespan, reverse=True)
    return lifespans


def summarize_flow(records: list[ContentFlowRecord]) -> dict:
    """Summarize content flow across all consecutive pairs."""
    if not records:
        return {}

    content_survival = [r.content_survival_rate for r in records]
    meta_survival = [r.meta_survival_rate for r in records]
    title_persistence = [
        r.titles_shared / r.strands_prior if r.strands_prior > 0 else 0.0
        for r in records
    ]

    all_categories: Counter[str] = Counter()
    for r in records:
        all_categories.update(r.loss_categories)

    return {
        "n_transitions": len(records),
        "content_survival": {
            "mean": sum(content_survival) / len(content_survival),
            "min": min(content_survival),
            "max": max(content_survival),
            "std": _std(content_survival),
        },
        "meta_survival": {
            "mean": sum(meta_survival) / len(meta_survival),
            "min": min(meta_survival),
            "max": max(meta_survival),
            "std": _std(meta_survival),
        },
        "title_persistence": {
            "mean": sum(title_persistence) / len(title_persistence),
            "min": min(title_persistence),
            "max": max(title_persistence),
        },
        "loss_categories": dict(all_categories.most_common()),
        "total_declared_losses": sum(r.n_declared_losses for r in records),
    }


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5
