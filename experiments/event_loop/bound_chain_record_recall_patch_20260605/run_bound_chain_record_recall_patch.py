"""Rerun bound-chain contract probe after in-session record-id recall patch."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BOUND_CHAIN_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bound_chain_contract_20260605/"
    / "run_bound_chain_contract.py"
)


def load_bound_chain_runner():
    spec = importlib.util.spec_from_file_location(
        "bound_chain_contract_base",
        BOUND_CHAIN_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bound-chain runner from {BOUND_CHAIN_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base_runner = load_bound_chain_runner()
base_runner.EXP_DIR = EXP_DIR
base_runner.PROJECT_ROOT = PROJECT_ROOT
base_runner.RESULTS_PATH = RESULTS_PATH
base_runner.base.EXP_DIR = EXP_DIR
base_runner.base.PROJECT_ROOT = PROJECT_ROOT

MODEL = base_runner.MODEL
N_REPLICATES = base_runner.N_REPLICATES


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "experiment": "bound_chain_record_recall_patch_20260605",
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "substrate_patch": "in_session_record_id_recall",
        "results": results,
        "summary": base_runner.aggregate(results),
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
            results = [row for row in prior if isinstance(row, dict)]
    done = completed_replicates(results)
    for replicate in range(N_REPLICATES):
        if replicate + 1 in done:
            print(f"bound_chain_record_recall_patch r{replicate + 1} already recorded", flush=True)
            continue
        print(f"bound_chain_record_recall_patch r{replicate + 1}", flush=True)
        results.append(base_runner.run_replicate(replicate, api_key))
        done.add(replicate + 1)
        write_results(results)
    write_results(results)
    print(json.dumps(base_runner.aggregate(results), indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
