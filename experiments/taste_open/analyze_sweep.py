"""Analyze taste_open sweep results.

Reads JSONL logs from a sweep directory and produces per-model analysis
across five dimensions: protocol compliance, data integrity, structure
building, curation behavior, and truncation.

Usage:
    uv run python experiments/taste_open/analyze_sweep.py experiments/taste_open/sweep_20260411/
    uv run python experiments/taste_open/analyze_sweep.py experiments/taste_open/sweep_20260411/ --json
    uv run python experiments/taste_open/analyze_sweep.py experiments/taste_open/sweep_20260411/ --tier A
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


PROTOCOL_KEYS = {"response", "updated_regions", "deleted_regions"}


@dataclass
class CycleMetrics:
    cycle: int
    tool_used: bool
    has_response: bool
    has_updated_regions: bool
    declared_regions: list[str]
    actual_custom_keys: list[str]
    declared_but_missing: list[str]
    undeclared_but_present: list[str]
    n_custom_keys: int
    state_tokens: int
    stop_reason: str
    truncated: bool


@dataclass
class ModelAnalysis:
    model_id: str
    status: str
    cycles_completed: int

    # Protocol compliance
    tool_use_rate: float = 0.0
    updated_regions_rate: float = 0.0
    data_integrity_rate: float = 0.0

    # Structure building
    max_custom_keys: int = 0
    final_custom_keys: int = 0
    key_trajectory: list[int] = field(default_factory=list)
    keys_ever_created: list[str] = field(default_factory=list)
    key_growth_pattern: str = "unknown"

    # Curation behavior
    state_token_trajectory: list[int] = field(default_factory=list)
    curation_events: int = 0
    max_state_tokens: int = 0
    final_state_tokens: int = 0
    state_pattern: str = "unknown"

    # Truncation
    truncation_count: int = 0
    truncation_cycles: list[int] = field(default_factory=list)

    # Content quality
    declared_vs_actual_mismatches: int = 0
    empty_response_count: int = 0

    # Scoring
    composite_score: float = 0.0
    tier: str = "F"


def _classify_trajectory(values: list[int]) -> str:
    """Classify a numeric trajectory as growing/plateau/oscillating/declining."""
    if len(values) < 3:
        return "insufficient_data"

    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    if not deltas:
        return "insufficient_data"

    positive = sum(1 for d in deltas if d > 0)
    negative = sum(1 for d in deltas if d < 0)
    zero = sum(1 for d in deltas if d == 0)
    total = len(deltas)

    if positive / total > 0.6:
        return "growing"
    if zero / total > 0.6:
        return "plateau"
    if negative / total > 0.4:
        return "declining"
    return "oscillating"


def analyze_model_log(log_path: Path) -> ModelAnalysis:
    """Read a model's JSONL log and compute all metrics."""
    records = []
    with open(log_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        model_id = log_path.stem.replace("__", "/")
        return ModelAnalysis(model_id=model_id, status="empty", cycles_completed=0)

    model_id = records[0].get("model", log_path.stem.replace("__", "/"))
    cycles: list[CycleMetrics] = []
    all_keys: set[str] = set()

    for rec in records:
        raw = rec.get("raw_output", {})
        state = rec.get("state", {})
        usage = rec.get("usage", {})

        # Did the model produce output via tool?
        tool_used = bool(raw) and "response" in raw
        has_response = bool(raw.get("response"))
        has_updated = "updated_regions" in raw

        declared = set(raw.get("updated_regions", []))
        # Keys in raw_output beyond protocol keys
        actual_custom = set(raw.keys()) - PROTOCOL_KEYS
        declared_but_missing = sorted(declared - set(raw.keys()))
        undeclared_but_present = sorted(actual_custom - declared)

        # State-level custom keys (what persisted)
        state_keys = [k for k in state if k != "cycle"] if state else []
        n_custom = len(state_keys)
        all_keys.update(state_keys)

        state_tokens = rec.get("state_token_estimate", 0)
        stop = usage.get("stop_reason", "unknown")

        cycles.append(CycleMetrics(
            cycle=rec.get("cycle", 0),
            tool_used=tool_used,
            has_response=has_response,
            has_updated_regions=has_updated,
            declared_regions=sorted(declared),
            actual_custom_keys=sorted(actual_custom),
            declared_but_missing=declared_but_missing,
            undeclared_but_present=undeclared_but_present,
            n_custom_keys=n_custom,
            state_tokens=state_tokens,
            stop_reason=stop,
            truncated=(stop == "max_tokens"),
        ))

    n = len(cycles)
    analysis = ModelAnalysis(
        model_id=model_id,
        status="complete" if n >= 10 else ("partial" if n > 0 else "empty"),
        cycles_completed=n,
    )

    if n == 0:
        return analysis

    # Protocol compliance
    analysis.tool_use_rate = sum(c.tool_used for c in cycles) / n
    analysis.updated_regions_rate = sum(c.has_updated_regions for c in cycles) / n

    # Data integrity: cycles where declared regions were all present in output
    integrity_ok = sum(
        1 for c in cycles if not c.declared_but_missing
    )
    analysis.data_integrity_rate = integrity_ok / n

    # Structure building
    key_traj = [c.n_custom_keys for c in cycles]
    analysis.key_trajectory = key_traj
    analysis.max_custom_keys = max(key_traj) if key_traj else 0
    analysis.final_custom_keys = key_traj[-1] if key_traj else 0
    analysis.keys_ever_created = sorted(all_keys)
    analysis.key_growth_pattern = _classify_trajectory(key_traj)

    # Curation behavior
    tok_traj = [c.state_tokens for c in cycles]
    analysis.state_token_trajectory = tok_traj
    analysis.max_state_tokens = max(tok_traj) if tok_traj else 0
    analysis.final_state_tokens = tok_traj[-1] if tok_traj else 0
    analysis.curation_events = sum(
        1 for i in range(1, len(tok_traj)) if tok_traj[i] < tok_traj[i - 1]
    )
    analysis.state_pattern = _classify_trajectory(tok_traj)

    # Truncation
    analysis.truncation_count = sum(c.truncated for c in cycles)
    analysis.truncation_cycles = [c.cycle for c in cycles if c.truncated]

    # Content quality
    analysis.declared_vs_actual_mismatches = sum(
        1 for c in cycles if c.declared_but_missing
    )
    analysis.empty_response_count = sum(
        1 for c in cycles if not c.has_response
    )

    # Scoring
    analysis.composite_score = _compute_score(analysis)
    analysis.tier = _assign_tier(analysis)

    return analysis


def _compute_score(a: ModelAnalysis) -> float:
    """Composite score 0-1."""
    if a.cycles_completed == 0:
        return 0.0

    protocol = a.tool_use_rate * 0.3
    integrity = a.data_integrity_rate * 0.2

    # Structure: normalize key count (10 custom keys = full marks)
    structure = min(a.max_custom_keys / 10, 1.0) * 0.2

    # Curation: any evidence of curation is good
    curation = (min(a.curation_events / 3, 1.0) * 0.2) if a.cycles_completed > 3 else 0.1

    # No truncation
    trunc_rate = a.truncation_count / a.cycles_completed if a.cycles_completed else 0
    no_trunc = (1 - trunc_rate) * 0.1

    return round(protocol + integrity + structure + curation + no_trunc, 3)


def _assign_tier(a: ModelAnalysis) -> str:
    s = a.composite_score

    if s >= 0.8 and a.curation_events > 0 and a.key_growth_pattern != "accumulating":
        return "A"
    if s >= 0.6 and a.max_custom_keys >= 3:
        return "B"
    if s >= 0.4 and a.tool_use_rate >= 0.8:
        return "C"
    if a.cycles_completed >= 3 and a.tool_use_rate > 0.3:
        return "D"
    return "F"


def analyze_sweep(sweep_dir: Path) -> dict:
    """Analyze all model logs in a sweep directory."""
    manifest_path = sweep_dir / "sweep_manifest.json"
    metadata = {}
    if manifest_path.exists():
        metadata = json.loads(manifest_path.read_text())

    analyses = []
    for log_path in sorted(sweep_dir.glob("*.jsonl")):
        analyses.append(analyze_model_log(log_path))

    # Sort by composite score descending
    analyses.sort(key=lambda a: -a.composite_score)

    tiers: dict[str, list[str]] = {}
    for a in analyses:
        tiers.setdefault(a.tier, []).append(a.model_id)

    return {
        "metadata": {
            "sweep_dir": str(sweep_dir),
            "n_models": len(analyses),
            "start_time": metadata.get("start_time"),
            "config": metadata.get("config"),
        },
        "models": [asdict(a) for a in analyses],
        "tiers": tiers,
    }


def print_summary(result: dict, tier_filter: str | None = None) -> None:
    """Print human-readable summary."""
    models = result["models"]
    if tier_filter:
        models = [m for m in models if m["tier"] == tier_filter.upper()]

    print(f"Sweep: {result['metadata']['sweep_dir']}")
    print(f"Models analyzed: {result['metadata']['n_models']}")
    print()

    # Tier summary
    tiers = result["tiers"]
    for t in ["A", "B", "C", "D", "F"]:
        if t in tiers:
            print(f"  Tier {t}: {len(tiers[t])} models")
    print()

    # Detail table
    header = (
        f"{'Tier':>4}  {'Model':<50} {'Cyc':>4} {'Keys':>5} "
        f"{'Tok':>6} {'Cur':>4} {'Trnc':>4} {'Score':>6}"
    )
    print(header)
    print("-" * len(header))

    for m in models:
        print(
            f"  {m['tier']:>2}  {m['model_id']:<50} "
            f"{m['cycles_completed']:>4} {m['final_custom_keys']:>5} "
            f"{m['final_state_tokens']:>6} {m['curation_events']:>4} "
            f"{m['truncation_count']:>4} {m['composite_score']:>6.3f}"
        )

    print()
    print("Columns: Cyc=cycles completed, Keys=final custom keys, "
          "Tok=final state tokens, Cur=curation events, Trnc=truncations")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze taste_open sweep results"
    )
    parser.add_argument("sweep_dir", type=Path)
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--tier", default=None, help="Filter to tier (A/B/C/D/F)")
    parser.add_argument(
        "--detail", default=None,
        help="Show detailed analysis for a specific model ID",
    )
    args = parser.parse_args()

    if not args.sweep_dir.is_dir():
        raise SystemExit(f"Not a directory: {args.sweep_dir}")

    result = analyze_sweep(args.sweep_dir)

    if args.detail:
        for m in result["models"]:
            if m["model_id"] == args.detail or args.detail in m["model_id"]:
                print(json.dumps(m, indent=2))
                return
        raise SystemExit(f"Model not found: {args.detail}")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_summary(result, tier_filter=args.tier)


if __name__ == "__main__":
    main()
