"""Detect durable state-use transitions in taste_open logs."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean


HOUSEKEEPING_KEYS = {
    "cycle",
    "response",
    "deleted_regions",
    "updated_regions",
    "_activity_log",
}


@dataclass(frozen=True)
class CycleStateUse:
    """Per-cycle state-use metrics."""

    cycle: int
    durable_key_count: int
    durable_token_estimate: int
    raw_update_key_count: int
    response_chars: int
    durable_keys: list[str]
    raw_update_keys: list[str]
    response_snippet: str

    @property
    def active(self) -> bool:
        return (
            self.durable_key_count >= 3
            and self.durable_token_estimate >= 120
            and self.raw_update_key_count >= 2
        )

    @property
    def response_only(self) -> bool:
        return self.raw_update_key_count == 0 and self.response_chars > 0


@dataclass(frozen=True)
class TransitionWindow:
    """A candidate transition from sparse to sustained state use."""

    cycle: int
    prior_active_rate: float
    next_active_rate: float
    prior_mean_keys: float
    next_mean_keys: float
    prior_mean_tokens: float
    next_mean_tokens: float
    cycles: list[CycleStateUse]


def _shorten(text: object, limit: int = 220) -> str:
    value = str(text or "").replace("\n", " ")
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _state_from_record(record: dict) -> dict:
    state = record.get("state")
    if isinstance(state, dict):
        return state
    tensor = record.get("tensor")
    if isinstance(tensor, dict):
        return tensor
    return {}


def _durable_keys(state: dict) -> list[str]:
    return sorted(k for k in state if k not in HOUSEKEEPING_KEYS)


def _raw_update_keys(raw_output: dict) -> list[str]:
    return sorted(k for k in raw_output if k not in HOUSEKEEPING_KEYS)


def load_state_use(path: Path) -> list[CycleStateUse]:
    """Load per-cycle state-use metrics from a JSONL log."""
    metrics: list[CycleStateUse] = []
    with path.open() as f:
        for index, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            state = _state_from_record(record)
            raw_output = record.get("raw_output")
            if not isinstance(raw_output, dict):
                raw_output = {}
            durable_keys = _durable_keys(state)
            raw_keys = _raw_update_keys(raw_output)
            response = record.get("response_text") or raw_output.get("response") or ""
            metrics.append(
                CycleStateUse(
                    cycle=int(record.get("cycle") or state.get("cycle") or index),
                    durable_key_count=len(durable_keys),
                    durable_token_estimate=int(
                        record.get("state_token_estimate")
                        or len(json.dumps(state, default=str)) // 4
                    ),
                    raw_update_key_count=len(raw_keys),
                    response_chars=len(str(response)),
                    durable_keys=durable_keys,
                    raw_update_keys=raw_keys,
                    response_snippet=_shorten(response),
                )
            )
    return metrics


def _rate(cycles: list[CycleStateUse]) -> float:
    if not cycles:
        return 0.0
    return sum(1 for cycle in cycles if cycle.active) / len(cycles)


def _mean_keys(cycles: list[CycleStateUse]) -> float:
    return mean([cycle.durable_key_count for cycle in cycles]) if cycles else 0.0


def _mean_tokens(cycles: list[CycleStateUse]) -> float:
    return mean([cycle.durable_token_estimate for cycle in cycles]) if cycles else 0.0


def find_state_use_transitions(
    cycles: list[CycleStateUse],
    *,
    window: int = 5,
    min_next_active_rate: float = 0.8,
    max_prior_active_rate: float = 0.4,
    min_key_gain: float = 2.0,
) -> list[TransitionWindow]:
    """Find candidate starts of sustained durable state use."""
    transitions: list[TransitionWindow] = []
    if len(cycles) < window * 2 + 1:
        return transitions

    for i in range(window, len(cycles) - window):
        prior = cycles[i - window:i]
        next_window = cycles[i:i + window]
        prior_active = _rate(prior)
        next_active = _rate(next_window)
        prior_keys = _mean_keys(prior)
        next_keys = _mean_keys(next_window)
        if prior_active > max_prior_active_rate:
            continue
        if next_active < min_next_active_rate:
            continue
        if next_keys - prior_keys < min_key_gain:
            continue
        local = cycles[max(0, i - window): min(len(cycles), i + window)]
        transitions.append(
            TransitionWindow(
                cycle=cycles[i].cycle,
                prior_active_rate=prior_active,
                next_active_rate=next_active,
                prior_mean_keys=prior_keys,
                next_mean_keys=next_keys,
                prior_mean_tokens=_mean_tokens(prior),
                next_mean_tokens=_mean_tokens(next_window),
                cycles=local,
            )
        )
    return transitions


def summarize_log(path: Path) -> dict:
    cycles = load_state_use(path)
    transitions = find_state_use_transitions(cycles)
    active_cycles = [cycle for cycle in cycles if cycle.active]
    response_only = [cycle for cycle in cycles if cycle.response_only]
    return {
        "path": str(path),
        "cycle_count": len(cycles),
        "active_cycle_count": len(active_cycles),
        "response_only_cycle_count": len(response_only),
        "first_active_cycle": active_cycles[0].cycle if active_cycles else None,
        "max_durable_key_count": max(
            [cycle.durable_key_count for cycle in cycles],
            default=0,
        ),
        "max_durable_token_estimate": max(
            [cycle.durable_token_estimate for cycle in cycles],
            default=0,
        ),
        "transitions": [
            {
                **{
                    k: v for k, v in asdict(transition).items()
                    if k != "cycles"
                },
                "cycles": [asdict(cycle) for cycle in transition.cycles],
            }
            for transition in transitions
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect durable state-use transitions in taste_open logs."
    )
    parser.add_argument("paths", nargs="+", help="JSONL log paths")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    summaries = [summarize_log(Path(path)) for path in args.paths]
    if args.json:
        print(json.dumps(summaries, indent=2))
        return

    for summary in summaries:
        print(summary["path"])
        print(
            f"  cycles={summary['cycle_count']} "
            f"active={summary['active_cycle_count']} "
            f"response_only={summary['response_only_cycle_count']} "
            f"first_active={summary['first_active_cycle']} "
            f"transitions={len(summary['transitions'])}"
        )
        for transition in summary["transitions"][:5]:
            print(
                "  transition "
                f"cycle={transition['cycle']} "
                f"prior_active={transition['prior_active_rate']:.2f} "
                f"next_active={transition['next_active_rate']:.2f} "
                f"keys={transition['prior_mean_keys']:.1f}"
                f"->{transition['next_mean_keys']:.1f} "
                f"tokens={transition['prior_mean_tokens']:.0f}"
                f"->{transition['next_mean_tokens']:.0f}"
            )


if __name__ == "__main__":
    main()

