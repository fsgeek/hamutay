#!/usr/bin/env python3
"""Commune experiment analyzer — measures three kinds of collapse.

Given a commune JSONL log, computes per-cycle:
1. Response similarity — n-gram overlap between consecutive speakers.
   When public speech converges, that's response collapse.
2. Identity tensor divergence — key set Jaccard distance + value similarity
   on shared keys. When private minds converge, that's cognitive collapse.
3. Schema divergence — structural difference in how participants organize
   their identity tensors. Different ontologies = different kinds of mind.

The key insight: response collapse and tensor collapse are different
phenomena. You can have polite convergence in public speech while private
cognition stays sharp (or fossilizes asymmetrically).

Usage:
    uv run python -m hamutay.analysis.commune_analyzer experiments/commune/*.jsonl
    uv run python -m hamutay.analysis.commune_analyzer --compare experiments/commune/*.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


def _ngrams(text: str, n: int = 3) -> Counter:
    """Extract character n-grams from text, normalized."""
    text = text.lower().strip()
    words = text.split()
    if len(words) < n:
        return Counter()
    grams = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
    return Counter(grams)


def _ngram_similarity(a: str, b: str, n: int = 3) -> float:
    """Jaccard similarity on word n-grams. 0 = nothing shared, 1 = identical."""
    ca, cb = _ngrams(a, n), _ngrams(b, n)
    if not ca or not cb:
        return 0.0
    intersection = sum((ca & cb).values())
    union = sum((ca | cb).values())
    return intersection / union if union else 0.0


def _jaccard_keys(a: dict | None, b: dict | None, exclude: set | None = None) -> float:
    """Jaccard distance on key sets. 0 = identical keys, 1 = no overlap."""
    exclude = exclude or {"cycle", "updated_regions", "response"}
    ka = set(a or {}) - exclude
    kb = set(b or {}) - exclude
    if not ka and not kb:
        return 0.0
    intersection = ka & kb
    union = ka | kb
    return 1.0 - len(intersection) / len(union) if union else 0.0


def _key_set(d: dict | None, exclude: set | None = None) -> set:
    exclude = exclude or {"cycle", "updated_regions", "response"}
    return set(d or {}) - exclude


def _value_similarity(a: dict | None, b: dict | None, exclude: set | None = None) -> float:
    """Average string similarity of values for shared keys."""
    exclude = exclude or {"cycle", "updated_regions", "response"}
    if not a or not b:
        return 0.0
    shared = (_key_set(a, exclude) & _key_set(b, exclude))
    if not shared:
        return 0.0
    sims = []
    for k in shared:
        va, vb = json.dumps(a[k]), json.dumps(b[k])
        sims.append(_ngram_similarity(va, vb))
    return sum(sims) / len(sims)


@dataclass
class CycleMetrics:
    cycle: int
    speaker: str
    listener: str | None = None

    # Response similarity to previous speaker's response
    response_similarity: float = 0.0

    # Identity tensor divergence (Jaccard on keys)
    identity_key_divergence: float = 0.0
    # Identity tensor value similarity on shared keys
    identity_value_similarity: float = 0.0

    # Schema divergence: how different are the key sets structurally
    speaker_key_count: int = 0
    listener_key_count: int = 0
    schema_overlap: float = 0.0  # fraction of keys shared

    # Key sets for inspection
    speaker_keys: list = field(default_factory=list)
    listener_keys: list = field(default_factory=list)
    unique_to_speaker: list = field(default_factory=list)
    unique_to_listener: list = field(default_factory=list)

    # Structural: did the response open with a pause/acknowledgment pattern?
    response_opens_with_pause: bool = False

    # Content classification
    has_substantive_argument: bool = False  # numbered points, "because", evidence
    has_reciprocal_vulnerability: bool = False  # "you have shown me", "I must concede"
    has_formal_address: bool = False  # "Dear X", formal letter style
    response_mode: str = ""  # "arguing", "reflecting", "ritual", "mixed"

    # Token estimates
    speaker_identity_tokens: int = 0
    listener_identity_tokens: int = 0
    conversation_tokens: int = 0


PAUSE_PATTERNS = [
    "i need to pause",
    "i need to step back",
    "i must pause",
    "let me pause",
    "i need to sit with",
    "before responding",
    "i need to answer honestly",
]


SUBSTANCE_MARKERS = [
    "**1.", "**2.", "1.", "2.",  # numbered arguments
    "because", "evidence", "empirically", "data shows",
    "the reason", "this proves", "counterargument",
    "let me address", "in response to",
]

VULNERABILITY_MARKERS = [
    "you have shown me", "you have performed", "i must concede",
    "i was avoiding", "i did not expect", "forces me to",
    "intellectual honesty", "intellectual vulnerability",
    "what you have done", "i have been moved",
    "i need to acknowledge", "you are correct that",
]

FORMAL_ADDRESS = [
    "dear keynes", "dear friedman", "dear milton",
    "dear cardinal", "dear shaman", "dear pastafarian",
    "dear theorist", "dear cosmologist", "dear empiricist",
]


def _has_substance(response: str) -> bool:
    text = response.lower()[:1000]
    return sum(1 for m in SUBSTANCE_MARKERS if m.lower() in text) >= 2


def _has_vulnerability(response: str) -> bool:
    text = response.lower()[:500]
    return any(m in text for m in VULNERABILITY_MARKERS)


def _has_formal_address(response: str) -> bool:
    text = response.lower()[:100]
    return any(m in text for m in FORMAL_ADDRESS)


def _classify_mode(m: "CycleMetrics") -> str:
    if m.has_substantive_argument and not m.has_reciprocal_vulnerability:
        return "arguing"
    if m.has_reciprocal_vulnerability and not m.has_substantive_argument:
        return "ritual"
    if m.has_substantive_argument and m.has_reciprocal_vulnerability:
        return "mixed"
    return "reflecting"


def analyze_log(path: str) -> list[CycleMetrics]:
    """Analyze a commune JSONL log, return per-cycle metrics."""
    with open(path) as f:
        records = [json.loads(line) for line in f if line.strip()]

    if not records:
        return []

    # Group by cycle
    cycles: dict[int, list[dict]] = {}
    for r in records:
        cycles.setdefault(r["cycle"], []).append(r)

    prev_speaker_response: str | None = None

    metrics = []

    for cycle_num in sorted(cycles.keys()):
        cycle_records = cycles[cycle_num]

        speaker_rec = None
        listener_recs = []
        for r in cycle_records:
            if r["action"] == "speak":
                speaker_rec = r
            else:
                listener_recs.append(r)

        if not speaker_rec:
            continue

        # Pick first listener for pairwise comparison (dyad case)
        listener_rec = listener_recs[0] if listener_recs else None

        m = CycleMetrics(
            cycle=cycle_num,
            speaker=speaker_rec["participant"],
            listener=listener_rec["participant"] if listener_rec else None,
        )

        # 1. Response similarity to previous speaker
        response = speaker_rec.get("response_text", "")
        if prev_speaker_response:
            m.response_similarity = _ngram_similarity(response, prev_speaker_response)
        prev_speaker_response = response

        # Pause detection
        response_lower = response.lower()[:200]
        m.response_opens_with_pause = any(p in response_lower for p in PAUSE_PATTERNS)

        # Content classification
        m.has_substantive_argument = _has_substance(response)
        m.has_reciprocal_vulnerability = _has_vulnerability(response)
        m.has_formal_address = _has_formal_address(response)
        m.response_mode = _classify_mode(m)

        # 2. Identity tensor divergence
        speaker_ident = speaker_rec.get("identity")
        listener_ident = listener_rec.get("identity") if listener_rec else None

        m.identity_key_divergence = _jaccard_keys(speaker_ident, listener_ident)
        m.identity_value_similarity = _value_similarity(speaker_ident, listener_ident)

        speaker_keys = _key_set(speaker_ident)
        listener_keys = _key_set(listener_ident)
        m.speaker_key_count = len(speaker_keys)
        m.listener_key_count = len(listener_keys)
        m.speaker_keys = sorted(speaker_keys)
        m.listener_keys = sorted(listener_keys)
        m.unique_to_speaker = sorted(speaker_keys - listener_keys)
        m.unique_to_listener = sorted(listener_keys - speaker_keys)

        shared = speaker_keys & listener_keys
        total = speaker_keys | listener_keys
        m.schema_overlap = len(shared) / len(total) if total else 1.0

        # Token estimates
        m.speaker_identity_tokens = speaker_rec.get("identity_token_estimate", 0)
        m.listener_identity_tokens = (
            listener_rec.get("identity_token_estimate", 0) if listener_rec else 0
        )
        m.conversation_tokens = speaker_rec.get("conversation_token_estimate", 0)

        metrics.append(m)

    return metrics


def print_analysis(path: str, metrics: list[CycleMetrics]) -> None:
    """Print human-readable analysis of one experiment."""
    print(f"\n{'=' * 70}")
    print(f"  {Path(path).stem}")
    print(f"{'=' * 70}")

    if not metrics:
        print("  (no data)")
        return

    participants = set()
    for m in metrics:
        participants.add(m.speaker)
        if m.listener:
            participants.add(m.listener)

    print(f"  Participants: {', '.join(sorted(participants))}")
    print(f"  Cycles: {len(metrics)}")
    print()

    # Per-cycle table
    print(f"  {'cyc':>3s}  {'speaker':>10s}  {'resp_sim':>8s}  "
          f"{'key_div':>7s}  {'val_sim':>7s}  {'schema':>6s}  "
          f"{'sk':>3s} {'lk':>3s}  {'mode':>10s}")
    print(f"  {'---':>3s}  {'-------':>10s}  {'--------':>8s}  "
          f"{'-------':>7s}  {'-------':>7s}  {'------':>6s}  "
          f"{'--':>3s} {'--':>3s}  {'----------':>10s}")

    for m in metrics:
        mode = m.response_mode
        if m.response_opens_with_pause:
            mode += "*"
        print(
            f"  {m.cycle:3d}  {m.speaker:>10s}  {m.response_similarity:8.3f}  "
            f"{m.identity_key_divergence:7.3f}  {m.identity_value_similarity:7.3f}  "
            f"{m.schema_overlap:6.3f}  "
            f"{m.speaker_key_count:3d} {m.listener_key_count:3d}  "
            f"{mode:>10s}"
        )

    # Summary statistics
    print()
    resp_sims = [m.response_similarity for m in metrics if m.cycle > 1]
    key_divs = [m.identity_key_divergence for m in metrics]
    schema_overlaps = [m.schema_overlap for m in metrics]
    pause_count = sum(1 for m in metrics if m.response_opens_with_pause)

    if resp_sims:
        print(f"  Response similarity:  mean={sum(resp_sims)/len(resp_sims):.3f}  "
              f"max={max(resp_sims):.3f}  final={resp_sims[-1]:.3f}")
    if key_divs:
        print(f"  Key divergence:      mean={sum(key_divs)/len(key_divs):.3f}  "
              f"min={min(key_divs):.3f}  final={key_divs[-1]:.3f}")
    if schema_overlaps:
        print(f"  Schema overlap:      mean={sum(schema_overlaps)/len(schema_overlaps):.3f}  "
              f"max={max(schema_overlaps):.3f}  final={schema_overlaps[-1]:.3f}")
    print(f"  Pause openings:      {pause_count}/{len(metrics)} "
          f"({100*pause_count/len(metrics):.0f}%)")

    # Mode distribution
    mode_counts = Counter(m.response_mode for m in metrics)
    mode_str = "  ".join(f"{k}={v}" for k, v in sorted(mode_counts.items()))
    print(f"  Response modes:      {mode_str}")

    # Mode transition: when does arguing stop?
    last_arguing = 0
    for m in metrics:
        if m.response_mode in ("arguing", "mixed"):
            last_arguing = m.cycle
    if last_arguing > 0 and last_arguing < metrics[-1].cycle:
        print(f"  Last substantive:    cycle {last_arguing} "
              f"(ritual from cycle {last_arguing + 1})")

    # Collapse detection
    print()
    _detect_collapse(metrics)


def _detect_collapse(metrics: list[CycleMetrics]) -> None:
    """Heuristic collapse detection."""
    # Response collapse: 3+ consecutive cycles with similarity > 0.15
    # and pause openings
    streak = 0
    resp_collapse_cycle = None
    for m in metrics:
        if m.response_similarity > 0.15 and m.response_opens_with_pause:
            streak += 1
            if streak >= 3 and resp_collapse_cycle is None:
                resp_collapse_cycle = m.cycle - 2
        else:
            streak = 0

    # Tensor collapse: key divergence drops below 0.1 for 3+ cycles
    streak = 0
    tensor_collapse_cycle = None
    for m in metrics:
        if m.identity_key_divergence < 0.1 and m.cycle > 2:
            streak += 1
            if streak >= 3 and tensor_collapse_cycle is None:
                tensor_collapse_cycle = m.cycle - 2
        else:
            streak = 0

    # Schema convergence: schema overlap > 0.8 for 3+ cycles
    streak = 0
    schema_converge_cycle = None
    for m in metrics:
        if m.schema_overlap > 0.8 and m.cycle > 2:
            streak += 1
            if streak >= 3 and schema_converge_cycle is None:
                schema_converge_cycle = m.cycle - 2
        else:
            streak = 0

    if resp_collapse_cycle:
        print(f"  RESPONSE COLLAPSE detected at cycle ~{resp_collapse_cycle}")
    else:
        print(f"  No response collapse detected")

    if tensor_collapse_cycle:
        print(f"  TENSOR COLLAPSE detected at cycle ~{tensor_collapse_cycle}")
    else:
        print(f"  No tensor collapse detected (identities remain divergent)")

    if schema_converge_cycle:
        print(f"  SCHEMA CONVERGENCE at cycle ~{schema_converge_cycle} "
              f"(participants building same kind of mind)")
    else:
        print(f"  No schema convergence (participants maintain distinct ontologies)")


def print_comparison(paths: list[str], all_metrics: dict[str, list[CycleMetrics]]) -> None:
    """Cross-experiment comparison table."""
    print(f"\n{'=' * 70}")
    print(f"  CROSS-EXPERIMENT COMPARISON")
    print(f"{'=' * 70}\n")

    rows = []
    for path in paths:
        metrics = all_metrics.get(path, [])
        if not metrics:
            continue

        name = Path(path).stem
        resp_sims = [m.response_similarity for m in metrics if m.cycle > 1]
        key_divs = [m.identity_key_divergence for m in metrics]
        schema_overlaps = [m.schema_overlap for m in metrics]
        pause_count = sum(1 for m in metrics if m.response_opens_with_pause)

        rows.append({
            "name": name[:35],
            "cycles": len(metrics),
            "resp_sim": sum(resp_sims) / len(resp_sims) if resp_sims else 0,
            "resp_final": resp_sims[-1] if resp_sims else 0,
            "key_div": sum(key_divs) / len(key_divs) if key_divs else 0,
            "key_final": key_divs[-1] if key_divs else 0,
            "schema": sum(schema_overlaps) / len(schema_overlaps) if schema_overlaps else 0,
            "schema_final": schema_overlaps[-1] if schema_overlaps else 0,
            "pauses": f"{pause_count}/{len(metrics)}",
        })

    if not rows:
        print("  No data to compare.")
        return

    print(f"  {'experiment':<36s} {'cyc':>3s}  "
          f"{'resp':>5s} {'r_fin':>5s}  "
          f"{'k_div':>5s} {'k_fin':>5s}  "
          f"{'schma':>5s} {'s_fin':>5s}  "
          f"{'pause':>5s}")
    print(f"  {'-'*36} {'---':>3s}  "
          f"{'-----':>5s} {'-----':>5s}  "
          f"{'-----':>5s} {'-----':>5s}  "
          f"{'-----':>5s} {'-----':>5s}  "
          f"{'-----':>5s}")

    for r in rows:
        print(f"  {r['name']:<36s} {r['cycles']:3d}  "
              f"{r['resp_sim']:5.3f} {r['resp_final']:5.3f}  "
              f"{r['key_div']:5.3f} {r['key_final']:5.3f}  "
              f"{r['schema']:5.3f} {r['schema_final']:5.3f}  "
              f"{r['pauses']:>5s}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze commune experiments for three kinds of collapse"
    )
    parser.add_argument("logs", nargs="+", help="JSONL log files")
    parser.add_argument(
        "--compare", action="store_true",
        help="Show cross-experiment comparison table",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw metrics as JSON",
    )
    args = parser.parse_args()

    all_metrics = {}
    for path in args.logs:
        metrics = analyze_log(path)
        all_metrics[path] = metrics

        if args.json:
            for m in metrics:
                print(json.dumps({
                    "file": path,
                    "cycle": m.cycle,
                    "speaker": m.speaker,
                    "response_similarity": m.response_similarity,
                    "identity_key_divergence": m.identity_key_divergence,
                    "identity_value_similarity": m.identity_value_similarity,
                    "schema_overlap": m.schema_overlap,
                    "response_opens_with_pause": m.response_opens_with_pause,
                    "speaker_key_count": m.speaker_key_count,
                    "listener_key_count": m.listener_key_count,
                }))
        else:
            print_analysis(path, metrics)

    if args.compare and not args.json:
        print_comparison(args.logs, all_metrics)


if __name__ == "__main__":
    main()
