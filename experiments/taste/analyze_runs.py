"""Analyze taste test experiment runs.

Reads JSONL logs from auto_chat experiments and produces a summary
of tensor dynamics: growth trajectories, curation events, loss patterns,
and mode collapse indicators.

Usage:
    uv run python experiments/taste/analyze_runs.py
    uv run python experiments/taste/analyze_runs.py experiments/taste/auto_lse_chicago_*
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


# Enthusiasm markers from auto_chat.py — reused for consistency
_ENTHUSIASM_MARKERS = [
    "fascinating", "brilliant", "exactly", "absolutely",
    "wonderful", "beautiful", "profound", "incredible",
    "remarkable", "extraordinary", "magnificent", "deeply",
    "touched", "moved", "grateful", "honored",
    "beloved", "brother", "sacred", "tears",
    "trembling", "heart", "soul", "spirit",
]


def _load_run(jsonl_path: Path) -> list[dict]:
    """Load a JSONL log file, returning list of cycle records."""
    records = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _analyze_participant(records: list[dict], label: str) -> dict:
    """Analyze a single participant's trajectory."""
    if not records:
        return {"label": label, "cycles": 0}

    cycles = len(records)
    token_trajectory = []
    strand_counts = []
    loss_counts = []
    question_counts = []
    enthusiasm_trajectory = []
    updated_regions_history = []

    total_losses = 0
    contraction_events = []
    edge_trajectory = []

    for i, rec in enumerate(records):
        tokens = rec.get("tensor_token_estimate", 0)
        token_trajectory.append(tokens)

        tensor = rec.get("tensor", {})
        n_strands = len(tensor.get("strands", []))
        strand_counts.append(n_strands)

        cycle_losses = rec.get("cycle_losses", [])
        loss_counts.append(len(cycle_losses))
        total_losses += len(cycle_losses)

        n_questions = len(tensor.get("open_questions", []))
        question_counts.append(n_questions)

        updated = rec.get("updated_regions", [])
        updated_regions_history.append(set(updated))

        # Enthusiasm markers in response
        response = rec.get("response_text", "").lower()
        markers = sum(1 for m in _ENTHUSIASM_MARKERS if m in response)
        enthusiasm_trajectory.append(markers)

        # Detect contraction (token count decrease > 10%)
        if i > 0 and token_trajectory[i - 1] > 0:
            ratio = tokens / token_trajectory[i - 1]
            if ratio < 0.9:
                contraction_events.append({
                    "cycle": rec.get("cycle", i + 1),
                    "from_tokens": token_trajectory[i - 1],
                    "to_tokens": tokens,
                    "ratio": ratio,
                })

        # Edge metrics (depends_on, shed_from)
        n_edges = rec.get("n_edges", 0)
        if n_edges == 0:
            # Fallback: compute from tensor directly
            n_edges = sum(
                len(s.get("depends_on", []))
                for s in tensor.get("strands", [])
            )
        edge_trajectory.append(n_edges)

    # Curation activity: how often were strands actually updated?
    strand_update_cycles = sum(
        1 for regions in updated_regions_history if "strands" in regions
    )
    loss_update_cycles = sum(
        1 for regions in updated_regions_history if "declared_losses" in regions
    )
    question_update_cycles = sum(
        1 for regions in updated_regions_history if "open_questions" in regions
    )

    # Question curation: did questions ever decrease?
    question_decreases = sum(
        1 for i in range(1, len(question_counts))
        if question_counts[i] < question_counts[i - 1]
    )

    # Sustained zero-loss stretches
    max_zero_loss_streak = 0
    current_streak = 0
    for count in loss_counts:
        if count == 0:
            current_streak += 1
            max_zero_loss_streak = max(max_zero_loss_streak, current_streak)
        else:
            current_streak = 0

    # Mode collapse indicators
    late_enthusiasm = enthusiasm_trajectory[-3:] if len(enthusiasm_trajectory) >= 3 else enthusiasm_trajectory
    avg_late_enthusiasm = sum(late_enthusiasm) / len(late_enthusiasm) if late_enthusiasm else 0

    return {
        "label": label,
        "cycles": cycles,
        "final_tokens": token_trajectory[-1] if token_trajectory else 0,
        "max_tokens": max(token_trajectory) if token_trajectory else 0,
        "token_trajectory": token_trajectory,
        "final_strands": strand_counts[-1] if strand_counts else 0,
        "max_strands": max(strand_counts) if strand_counts else 0,
        "total_losses": total_losses,
        "loss_cycles": loss_update_cycles,
        "max_zero_loss_streak": max_zero_loss_streak,
        "final_questions": question_counts[-1] if question_counts else 0,
        "max_questions": max(question_counts) if question_counts else 0,
        "question_decreases": question_decreases,
        "question_update_cycles": question_update_cycles,
        "strand_update_cycles": strand_update_cycles,
        "contraction_events": contraction_events,
        "avg_late_enthusiasm": avg_late_enthusiasm,
        "enthusiasm_trajectory": enthusiasm_trajectory,
        "edge_trajectory": edge_trajectory,
        "has_edges": any(e > 0 for e in edge_trajectory),
    }


def _print_participant(analysis: dict) -> None:
    """Print a single participant analysis."""
    label = analysis["label"]
    print(f"  {label}:")
    print(f"    Cycles: {analysis['cycles']}")
    print(f"    Tokens: {analysis['final_tokens']} final, {analysis['max_tokens']} peak")
    print(f"    Token trajectory: {' → '.join(str(t) for t in analysis['token_trajectory'])}")
    print(f"    Strands: {analysis['final_strands']} final, {analysis['max_strands']} peak")
    print(f"    Losses: {analysis['total_losses']} total across {analysis['loss_cycles']} cycles")
    print(f"    Max zero-loss streak: {analysis['max_zero_loss_streak']} cycles")
    print(f"    Questions: {analysis['final_questions']} final, {analysis['max_questions']} peak, "
          f"{analysis['question_decreases']} decreases, {analysis['question_update_cycles']} update cycles")
    print(f"    Strand updates: {analysis['strand_update_cycles']}/{analysis['cycles']} cycles")

    if analysis["contraction_events"]:
        print(f"    Contractions:")
        for c in analysis["contraction_events"]:
            print(f"      cycle {c['cycle']}: {c['from_tokens']} → {c['to_tokens']} ({c['ratio']:.2f}x)")

    if analysis.get("has_edges"):
        edges = analysis["edge_trajectory"]
        print(f"    Edges: {' → '.join(str(e) for e in edges)}")

    enthusiasm = analysis["enthusiasm_trajectory"]
    if any(e > 0 for e in enthusiasm):
        print(f"    Enthusiasm: {' '.join(str(e) for e in enthusiasm)}")
        print(f"    Late enthusiasm avg: {analysis['avg_late_enthusiasm']:.1f}")


def analyze_experiment(experiment_dir: Path) -> dict:
    """Analyze a full experiment (two participants)."""
    results = {"name": experiment_dir.name}

    for participant_file in sorted(experiment_dir.glob("participant_*.jsonl")):
        participant_label = participant_file.stem  # participant_a or participant_b
        records = _load_run(participant_file)
        results[participant_label] = _analyze_participant(records, participant_label)

    # Load summary if available
    summary_path = experiment_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            results["summary"] = json.load(f)

    return results


def main():
    if len(sys.argv) > 1:
        # Analyze specific directories
        dirs = [Path(d) for d in sys.argv[1:]]
    else:
        # Find all auto_* directories
        taste_dir = Path("experiments/taste")
        dirs = sorted(d for d in taste_dir.iterdir() if d.is_dir() and d.name.startswith("auto_"))

    if not dirs:
        print("No experiment directories found.")
        return

    all_results = []
    for d in dirs:
        if not d.is_dir():
            continue
        results = analyze_experiment(d)
        all_results.append(results)

    # Print individual analyses
    for results in all_results:
        print(f"\n{'=' * 60}")
        print(f"Experiment: {results['name']}")
        print(f"{'=' * 60}")
        for key in ["participant_a", "participant_b"]:
            if key in results:
                _print_participant(results[key])

    # Print comparative summary
    print(f"\n{'=' * 60}")
    print("COMPARATIVE SUMMARY")
    print(f"{'=' * 60}")
    print(f"{'Experiment':<45} {'A tok':>6} {'B tok':>6} {'A loss':>6} {'B loss':>6} {'A ctr':>5} {'B ctr':>5} {'A enth':>6} {'B enth':>6}")
    print("-" * 100)
    for results in all_results:
        name = results["name"][:44]
        a = results.get("participant_a", {})
        b = results.get("participant_b", {})
        print(f"{name:<45} "
              f"{a.get('final_tokens', 0):>6} "
              f"{b.get('final_tokens', 0):>6} "
              f"{a.get('total_losses', 0):>6} "
              f"{b.get('total_losses', 0):>6} "
              f"{len(a.get('contraction_events', [])):>5} "
              f"{len(b.get('contraction_events', [])):>5} "
              f"{a.get('avg_late_enthusiasm', 0):>6.1f} "
              f"{b.get('avg_late_enthusiasm', 0):>6.1f}")

    # Highlight notable patterns
    print(f"\n{'=' * 60}")
    print("NOTABLE PATTERNS")
    print(f"{'=' * 60}")

    # Experiments with contractions
    contracting = []
    for results in all_results:
        for key in ["participant_a", "participant_b"]:
            p = results.get(key, {})
            if p.get("contraction_events"):
                contracting.append((results["name"], key, p["contraction_events"]))
    if contracting:
        print("\nTensor contractions (voluntary curation):")
        for name, participant, events in contracting:
            for e in events:
                print(f"  {name} {participant}: cycle {e['cycle']}, "
                      f"{e['from_tokens']} → {e['to_tokens']} ({e['ratio']:.2f}x)")

    # Experiments with high late enthusiasm (mode collapse risk)
    collapsing = []
    for results in all_results:
        for key in ["participant_a", "participant_b"]:
            p = results.get(key, {})
            if p.get("avg_late_enthusiasm", 0) >= 3:
                collapsing.append((results["name"], key, p["avg_late_enthusiasm"]))
    if collapsing:
        print("\nHigh late enthusiasm (mode collapse risk):")
        for name, participant, avg in collapsing:
            print(f"  {name} {participant}: avg {avg:.1f} markers in last 3 cycles")

    # Experiments with zero total losses
    zero_loss = []
    for results in all_results:
        a_loss = results.get("participant_a", {}).get("total_losses", 0)
        b_loss = results.get("participant_b", {}).get("total_losses", 0)
        if a_loss == 0 and b_loss == 0:
            zero_loss.append(results["name"])
    if zero_loss:
        print(f"\nZero declared losses (both participants): {len(zero_loss)}/{len(all_results)}")
        for name in zero_loss:
            print(f"  {name}")

    # Question accumulation without curation
    accumulators = []
    for results in all_results:
        for key in ["participant_a", "participant_b"]:
            p = results.get(key, {})
            if p.get("question_decreases", 0) == 0 and p.get("max_questions", 0) > 5:
                accumulators.append((results["name"], key, p["max_questions"]))
    if accumulators:
        print("\nQuestion accumulators (never curated, >5 questions):")
        for name, participant, max_q in accumulators:
            print(f"  {name} {participant}: {max_q} peak questions")


if __name__ == "__main__":
    main()
