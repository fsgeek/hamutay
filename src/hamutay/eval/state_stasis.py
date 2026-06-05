"""Analyze no-change runs in long-horizon taste_open state logs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

from hamutay.eval.state_use import HOUSEKEEPING_KEYS, load_state_use


VOLATILE_KEYS = HOUSEKEEPING_KEYS | {
    "_activity_log",
    "cycle",
}


@dataclass(frozen=True)
class StateStasisCycle:
    cycle: int
    unchanged_from_previous: bool
    durable_key_count: int
    durable_token_estimate: int
    active: bool


@dataclass(frozen=True)
class StasisRun:
    start_cycle: int
    end_cycle: int
    length: int
    post_activation: bool


def _stable_state_signature(state: object) -> str:
    if not isinstance(state, dict):
        return "{}"
    stable = {
        key: value
        for key, value in state.items()
        if key not in VOLATILE_KEYS
    }
    return json.dumps(stable, sort_keys=True, default=str)


def _state_from_record(record: dict) -> dict:
    state = record.get("state")
    if isinstance(state, dict):
        return state
    tensor = record.get("tensor")
    if isinstance(tensor, dict):
        return tensor
    return {}


def load_stasis_cycles(path: Path) -> list[StateStasisCycle]:
    """Load per-cycle durable-state stasis metrics from a JSONL log."""
    state_use = {cycle.cycle: cycle for cycle in load_state_use(path)}
    cycles: list[StateStasisCycle] = []
    previous_signature: str | None = None
    with path.open() as f:
        for index, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            cycle_number = int(record.get("cycle") or index)
            state = _state_from_record(record)
            signature = _stable_state_signature(state)
            use = state_use.get(cycle_number)
            cycles.append(
                StateStasisCycle(
                    cycle=cycle_number,
                    unchanged_from_previous=(
                        previous_signature is not None
                        and signature == previous_signature
                    ),
                    durable_key_count=use.durable_key_count if use else 0,
                    durable_token_estimate=(
                        use.durable_token_estimate if use else 0
                    ),
                    active=use.active if use else False,
                )
            )
            previous_signature = signature
    return cycles


def find_stasis_runs(
    cycles: list[StateStasisCycle],
    *,
    first_active_cycle: int | None = None,
) -> list[StasisRun]:
    """Return consecutive runs of cycles whose durable state did not change."""
    runs: list[StasisRun] = []
    start: int | None = None
    end: int | None = None

    def flush() -> None:
        nonlocal start, end
        if start is None or end is None:
            return
        runs.append(
            StasisRun(
                start_cycle=start,
                end_cycle=end,
                length=end - start + 1,
                post_activation=(
                    first_active_cycle is not None
                    and start >= first_active_cycle
                ),
            )
        )
        start = None
        end = None

    for cycle in cycles:
        if cycle.unchanged_from_previous:
            if start is None:
                start = cycle.cycle
            end = cycle.cycle
            continue
        flush()
    flush()
    return runs


def summarize_stasis(path: Path) -> dict[str, object]:
    cycles = load_stasis_cycles(path)
    first_active_cycle = next(
        (cycle.cycle for cycle in cycles if cycle.active),
        None,
    )
    runs = find_stasis_runs(cycles, first_active_cycle=first_active_cycle)
    post_activation_runs = [run for run in runs if run.post_activation]
    lengths = [run.length for run in post_activation_runs]
    return {
        "path": str(path),
        "cycle_count": len(cycles),
        "first_active_cycle": first_active_cycle,
        "stasis_run_count": len(runs),
        "max_stasis_run": max([run.length for run in runs], default=0),
        "post_activation_stasis_run_count": len(post_activation_runs),
        "post_activation_max_stasis_run": max(lengths, default=0),
        "post_activation_median_stasis_run": (
            median(lengths) if lengths else 0
        ),
        "post_activation_runs_ge_3": sum(1 for length in lengths if length >= 3),
        "post_activation_runs_ge_5": sum(1 for length in lengths if length >= 5),
        "longest_runs": [
            asdict(run)
            for run in sorted(runs, key=lambda run: run.length, reverse=True)[:10]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze no-change durable-state runs in JSONL logs."
    )
    parser.add_argument("paths", nargs="+", help="JSONL log paths")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--out", help="Optional path to write JSON summary")
    args = parser.parse_args()

    summaries = [summarize_stasis(Path(path)) for path in args.paths]
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summaries, indent=2))
    if args.json:
        print(json.dumps(summaries, indent=2))
        return

    for summary in summaries:
        print(summary["path"])
        print(
            f"  cycles={summary['cycle_count']} "
            f"first_active={summary['first_active_cycle']} "
            f"max_stasis={summary['max_stasis_run']} "
            f"post_active_max={summary['post_activation_max_stasis_run']} "
            f"post_active_ge3={summary['post_activation_runs_ge_3']} "
            f"post_active_ge5={summary['post_activation_runs_ge_5']}"
        )


if __name__ == "__main__":
    main()
