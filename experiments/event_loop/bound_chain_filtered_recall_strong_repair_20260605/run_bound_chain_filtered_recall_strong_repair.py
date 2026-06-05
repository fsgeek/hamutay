"""Filtered bound-record recall with strong first-wake repair."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
FILTERED_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bound_chain_filtered_recall_20260605/"
    / "run_bound_chain_filtered_recall.py"
)
STABILITY_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/first_wake_continuation_stability_20260605/"
    / "run_first_wake_continuation_stability.py"
)


def load_runner(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runner from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


filtered = load_runner(FILTERED_RUNNER_PATH, "filtered_bound_recall_base")
stability = load_runner(STABILITY_RUNNER_PATH, "first_wake_stability_base")

filtered.EXP_DIR = EXP_DIR
filtered.PROJECT_ROOT = PROJECT_ROOT
filtered.RESULTS_PATH = RESULTS_PATH
filtered.base_runner.EXP_DIR = EXP_DIR
filtered.base_runner.PROJECT_ROOT = PROJECT_ROOT
filtered.base_runner.RESULTS_PATH = RESULTS_PATH
filtered.base_runner.base.EXP_DIR = EXP_DIR
filtered.base_runner.base.PROJECT_ROOT = PROJECT_ROOT
filtered.sb.EXP_DIR = EXP_DIR
filtered.sb.PROJECT_ROOT = PROJECT_ROOT

MODEL = filtered.MODEL
N_REPLICATES = filtered.N_REPLICATES
BOUND_FIELD = filtered.BOUND_FIELD


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    original_builder = filtered.sb.FirstWakeRepairBuilder
    try:
        filtered.sb.FirstWakeRepairBuilder = stability.StrongFirstWakeRepairBuilder
        row = filtered.run_replicate(replicate, api_key)
    finally:
        filtered.sb.FirstWakeRepairBuilder = original_builder
    row["first_wake_repair_builder"] = "StrongFirstWakeRepairBuilder"
    return row


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "bound_chain_filtered_recall_strong_repair_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "filtered_bound_field": BOUND_FIELD,
        "first_wake_repair_builder": "StrongFirstWakeRepairBuilder",
        "results": results,
        "summary": filtered.aggregate(results),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def completed_replicates(results: list[dict[str, Any]]) -> set[int]:
    return {int(row.get("replicate", 0)) for row in results}


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict[str, Any]] = []
    if RESULTS_PATH.exists():
        prior = json.loads(RESULTS_PATH.read_text()).get("results", [])
        if isinstance(prior, list):
            results = [
                filtered.enrich_filtered_context(row)
                for row in prior
                if isinstance(row, dict)
            ]
    done = completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(
                f"bound_chain_filtered_recall_strong_repair r{replicate + 1} already recorded",
                flush=True,
            )
            continue
        print(f"bound_chain_filtered_recall_strong_repair r{replicate + 1}", flush=True)
        results.append(run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(filtered.aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
