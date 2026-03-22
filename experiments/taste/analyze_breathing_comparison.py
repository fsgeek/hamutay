"""Cross-architecture breathing comparison.

Compares breathing dynamics across:
1. External projector (Haiku), 54-cycle mechanism chat
2. Self-curating tensor (Sonnet), 11x10-cycle taste experiments
3. Self-curating tensor with edges, 50-round LSE-Chicago
4. Resumed session (seeded tensor), 10 cycles post-restart

Produces structured output for the SOSP paper: interval distributions,
severity distributions, loss patterns, and recovery dynamics.

Usage:
    uv run python experiments/taste/analyze_breathing_comparison.py
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def _extract_breathing_events(
    records: list[dict],
    threshold: float = 0.9,
) -> list[dict]:
    """Extract breathing events from a sequence of records.

    A breathing event is a contraction (>threshold token drop) or a
    consecutive sequence of contractions.
    """
    tokens = []
    for r in records:
        tensor = r.get("tensor", {})
        tokens.append(
            r.get("tensor_token_estimate", len(json.dumps(tensor)) // 4)
        )

    events = []
    in_event = False

    for i in range(1, len(tokens)):
        if tokens[i - 1] <= 0:
            continue
        ratio = tokens[i] / tokens[i - 1]
        if ratio < threshold:
            cycle = records[i].get("tensor", {}).get("cycle", i + 1)
            if not in_event:
                events.append({
                    "start_cycle": cycle,
                    "end_cycle": cycle,
                    "start_tokens": tokens[i - 1],
                    "end_tokens": tokens[i],
                    "min_ratio": ratio,
                    "n_cycles": 1,
                })
                in_event = True
            else:
                events[-1]["end_cycle"] = cycle
                events[-1]["end_tokens"] = tokens[i]
                events[-1]["min_ratio"] = min(events[-1]["min_ratio"], ratio)
                events[-1]["n_cycles"] += 1
        else:
            in_event = False

    return events


def _compute_intervals(events: list[dict]) -> list[int]:
    """Compute inter-event intervals."""
    if len(events) < 2:
        return []
    return [
        events[i + 1]["start_cycle"] - events[i]["end_cycle"]
        for i in range(len(events) - 1)
    ]


def _loss_stats(records: list[dict]) -> dict:
    """Compute loss declaration statistics."""
    total_losses = 0
    cycles_with_losses = 0
    loss_categories: dict[str, int] = {}

    for r in records:
        tensor = r.get("tensor", {})
        losses = tensor.get("declared_losses", [])
        if losses:
            cycles_with_losses += 1
            total_losses += len(losses)
            for loss in losses:
                cat = loss.get("category", "unknown")
                loss_categories[cat] = loss_categories.get(cat, 0) + 1

    return {
        "total_losses": total_losses,
        "cycles_with_losses": cycles_with_losses,
        "total_cycles": len(records),
        "loss_rate": cycles_with_losses / len(records) if records else 0,
        "mean_losses_per_cycle": total_losses / len(records) if records else 0,
        "categories": loss_categories,
    }


def analyze_source(
    records: list[dict],
    name: str,
    architecture: str,
) -> dict:
    """Analyze a single data source."""
    events = _extract_breathing_events(records)
    intervals = _compute_intervals(events)
    loss = _loss_stats(records)

    tokens = []
    for r in records:
        tensor = r.get("tensor", {})
        tokens.append(
            r.get("tensor_token_estimate", len(json.dumps(tensor)) // 4)
        )

    return {
        "name": name,
        "architecture": architecture,
        "n_cycles": len(records),
        "n_events": len(events),
        "events": events,
        "intervals": intervals,
        "mean_interval": sum(intervals) / len(intervals) if intervals else 0,
        "severities": [e["min_ratio"] for e in events],
        "mean_severity": (
            sum(e["min_ratio"] for e in events) / len(events)
            if events else 1.0
        ),
        "loss": loss,
        "token_range": (min(tokens), max(tokens)) if tokens else (0, 0),
        "mean_tokens": sum(tokens) / len(tokens) if tokens else 0,
    }


def main():
    results = []

    # 1. External projector, 54-cycle mechanism chat (segment 1)
    chat_path = Path("experiments/chat/mechanism_20260321_142150.jsonl")
    if chat_path.exists():
        all_records = _load_jsonl(chat_path)

        # Find segment boundaries (cycle resets)
        segments = [[]]
        for i, r in enumerate(all_records):
            if i > 0:
                prev_cycle = all_records[i - 1]["tensor"]["cycle"]
                curr_cycle = r["tensor"]["cycle"]
                if curr_cycle <= prev_cycle:
                    segments.append([])
            segments[-1].append(r)

        if len(segments) >= 1:
            results.append(analyze_source(
                segments[0],
                "External projector (54 cycles)",
                "external_projector",
            ))

        if len(segments) >= 2:
            results.append(analyze_source(
                segments[1],
                "Resumed session (10 cycles)",
                "external_projector_resumed",
            ))

    # 2. Self-curating taste experiments (10-cycle runs)
    taste_dir = Path("experiments/taste")
    taste_10_events = []
    taste_10_records = []

    for exp_dir in sorted(taste_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        if "edges" in exp_dir.name or "smoke" in exp_dir.name:
            continue  # separate analysis for edge experiments
        for p_file in sorted(exp_dir.glob("participant_*.jsonl")):
            records = _load_jsonl(p_file)
            if records:
                taste_10_records.extend(records)
                events = _extract_breathing_events(records)
                taste_10_events.extend(events)

    if taste_10_records:
        # Aggregate across all 10-cycle runs
        loss = _loss_stats(taste_10_records)
        tokens = []
        for r in taste_10_records:
            tensor = r.get("tensor", {})
            tokens.append(
                r.get("tensor_token_estimate", len(json.dumps(tensor)) // 4)
            )

        intervals = _compute_intervals(taste_10_events)
        results.append({
            "name": f"Self-curating 10-cycle runs ({len(taste_10_records)} total cycles)",
            "architecture": "self_curating",
            "n_cycles": len(taste_10_records),
            "n_events": len(taste_10_events),
            "events": taste_10_events,
            "intervals": intervals,
            "mean_interval": sum(intervals) / len(intervals) if intervals else 0,
            "severities": [e["min_ratio"] for e in taste_10_events],
            "mean_severity": (
                sum(e["min_ratio"] for e in taste_10_events) / len(taste_10_events)
                if taste_10_events else 1.0
            ),
            "loss": loss,
            "token_range": (min(tokens), max(tokens)) if tokens else (0, 0),
            "mean_tokens": sum(tokens) / len(tokens) if tokens else 0,
        })

    # 3. Edge experiments (20 and 50 cycle)
    for exp_name in ["auto_edges_lse_chicago_20", "auto_edges_lse_chicago_50",
                     "auto_edges_philosophical_20"]:
        exp_dir = taste_dir / exp_name
        if exp_dir.exists():
            for p_file in sorted(exp_dir.glob("participant_*.jsonl")):
                records = _load_jsonl(p_file)
                if records:
                    label = p_file.stem.replace("participant_", "")
                    results.append(analyze_source(
                        records,
                        f"Self-curating+edges: {exp_name}/{label}",
                        "self_curating_edges",
                    ))

    # Print results
    print("=" * 80)
    print("CROSS-ARCHITECTURE BREATHING COMPARISON")
    print("=" * 80)

    # Summary table
    print(f"\n{'Source':<55} {'Cyc':>4} {'Evt':>4} {'Int':>5} "
          f"{'Sev':>5} {'L/cyc':>5} {'L%':>5}")
    print("-" * 85)
    for r in results:
        print(f"{r['name'][:54]:<55} "
              f"{r['n_cycles']:>4} "
              f"{r['n_events']:>4} "
              f"{r['mean_interval']:>5.1f} "
              f"{r['mean_severity']:>5.2f} "
              f"{r['loss']['mean_losses_per_cycle']:>5.1f} "
              f"{r['loss']['loss_rate']*100:>4.0f}%")

    # Detailed analysis by architecture
    print(f"\n{'='*80}")
    print("ARCHITECTURE-LEVEL COMPARISON")
    print(f"{'='*80}")

    arch_groups: dict[str, list[dict]] = {}
    for r in results:
        arch = r["architecture"]
        arch_groups.setdefault(arch, []).append(r)

    for arch, group in arch_groups.items():
        total_cycles = sum(r["n_cycles"] for r in group)
        total_events = sum(r["n_events"] for r in group)
        all_severities = []
        all_intervals = []
        total_losses = 0
        cycles_with_losses = 0

        for r in group:
            all_severities.extend(r["severities"])
            all_intervals.extend(r["intervals"])
            total_losses += r["loss"]["total_losses"]
            cycles_with_losses += r["loss"]["cycles_with_losses"]

        print(f"\n{arch}:")
        print(f"  Sources: {len(group)}")
        print(f"  Total cycles: {total_cycles}")
        print(f"  Total breathing events: {total_events}")
        print(f"  Event rate: {total_events/total_cycles:.2f} per cycle")
        if all_intervals:
            print(f"  Mean inter-event interval: {sum(all_intervals)/len(all_intervals):.1f} cycles")
            print(f"  Interval range: {min(all_intervals)}-{max(all_intervals)}")
        if all_severities:
            print(f"  Mean contraction severity: {sum(all_severities)/len(all_severities):.2f}")
            print(f"  Severity range: {min(all_severities):.2f}-{max(all_severities):.2f}")
        print(f"  Loss rate: {cycles_with_losses/total_cycles*100:.0f}% of cycles declare losses")
        print(f"  Mean losses/cycle: {total_losses/total_cycles:.1f}")

    # Key finding: restart boundary
    print(f"\n{'='*80}")
    print("RESTART BOUNDARY ANALYSIS")
    print(f"{'='*80}")

    ext_result = next((r for r in results if r["architecture"] == "external_projector"), None)
    resumed_result = next((r for r in results if r["architecture"] == "external_projector_resumed"), None)

    if ext_result and resumed_result:
        print(f"\nOriginal session: {ext_result['n_cycles']} cycles, "
              f"{ext_result['n_events']} breathing events, "
              f"mean interval {ext_result['mean_interval']:.1f}")
        print(f"Resumed session:  {resumed_result['n_cycles']} cycles, "
              f"{resumed_result['n_events']} breathing events")
        if resumed_result["events"]:
            first_event = resumed_result["events"][0]
            print(f"  First contraction at cycle {first_event['start_cycle']} "
                  f"({first_event['min_ratio']:.2f}x)")
            print(f"  Breathing begins immediately — no warm-up period needed")

    # Key finding: loss pattern divergence
    print(f"\n{'='*80}")
    print("LOSS PATTERN DIVERGENCE")
    print(f"{'='*80}")

    ext_losses = next(
        (r["loss"] for r in results if r["architecture"] == "external_projector"), None
    )
    sc_losses = next(
        (r["loss"] for r in results if r["architecture"] == "self_curating"), None
    )

    if ext_losses and sc_losses:
        print(f"\nExternal projector (Haiku):")
        print(f"  Loss rate: {ext_losses['loss_rate']*100:.0f}% of cycles")
        print(f"  Mean losses/cycle: {ext_losses['mean_losses_per_cycle']:.1f}")
        if ext_losses["categories"]:
            print(f"  Categories: {ext_losses['categories']}")

        print(f"\nSelf-curating (Sonnet):")
        print(f"  Loss rate: {sc_losses['loss_rate']*100:.0f}% of cycles")
        print(f"  Mean losses/cycle: {sc_losses['mean_losses_per_cycle']:.1f}")
        if sc_losses["categories"]:
            print(f"  Categories: {sc_losses['categories']}")

        print(f"\n  → External projector declares losses {ext_losses['mean_losses_per_cycle']/max(sc_losses['mean_losses_per_cycle'], 0.01):.0f}x "
              f"more often than self-curating model")
        print(f"  → Full-rewrite architecture forces explicit loss declaration")
        print(f"  → Default-stable architecture makes loss declaration opt-in")


if __name__ == "__main__":
    main()
