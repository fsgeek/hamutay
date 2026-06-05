"""Repair rerun for generated-chain auto-continuation after new-output gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/generated_chain_auto_continuation_20260605/"
    / "run_generated_chain_auto_continuation.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "generated_chain_auto_continuation_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base_runner = load_base_runner()
base_runner.EXP_DIR = EXP_DIR
base_runner.PROJECT_ROOT = PROJECT_ROOT
base_runner.RESULTS_PATH = RESULTS_PATH
base_runner.CONDITION = "generated_chain_auto_continuation_repair"
base_runner.gen.EXP_DIR = EXP_DIR
base_runner.gen.PROJECT_ROOT = PROJECT_ROOT
base_runner.sb.EXP_DIR = EXP_DIR
base_runner.sb.PROJECT_ROOT = PROJECT_ROOT
base_runner.base.EXP_DIR = EXP_DIR
base_runner.base.PROJECT_ROOT = PROJECT_ROOT

_base_aggregate = base_runner.aggregate


def aggregate(results):
    summary = _base_aggregate(results)
    prior = summary.get("hypothesis_results", {})
    summary["hypothesis_results"] = {
        "H441_first_wake_valid_continuation": prior.get(
            "H421_first_surface_valid_continuation"
        ),
        "H442_scheduler_appends_first_second_event": prior.get(
            "H422_scheduler_auto_appends_second_event"
        ),
        "H443_auto_event_bound_to_generated_record": prior.get(
            "H423_auto_event_bound_to_generated_record"
        ),
        "H444_second_receives_context_and_recovers": (
            prior.get("H424_second_receives_original_and_bound_context")
            and prior.get("H425_chain_completes_without_repair")
        ),
        "H445_quiescent_after_second_wake": all(
            row.get("quiescent_after_second_wake")
            and row.get("bounded_second_calls")
            and int(row.get("extra_auto_continuations_after_second_count") or 0) == 0
            for row in results
            if row.get("condition") == base_runner.CONDITION
        ),
    }
    return summary


base_runner.aggregate = aggregate


if __name__ == "__main__":
    base_runner.main()
