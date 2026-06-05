"""Repair rerun for the budgeted three-wake chain."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/budgeted_three_wake_chain_20260605/"
    / "run_budgeted_three_wake_chain.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "budgeted_three_wake_chain_base",
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
base_runner.CONDITION = "budgeted_three_wake_chain_repair"
base_runner.gen.EXP_DIR = EXP_DIR
base_runner.gen.PROJECT_ROOT = PROJECT_ROOT
base_runner.sb.EXP_DIR = EXP_DIR
base_runner.sb.PROJECT_ROOT = PROJECT_ROOT
base_runner.base.EXP_DIR = EXP_DIR
base_runner.base.PROJECT_ROOT = PROJECT_ROOT

_base_first_surface = base_runner.first_surface
_base_bridge_surface = base_runner.bridge_surface
_base_aggregate = base_runner.aggregate


def first_surface(replicate: int):
    surface = copy.deepcopy(_base_first_surface(replicate))
    intermediate = (
        surface["input_schema"]["properties"]["chain_intermediate"]
    )
    intermediate["additionalProperties"] = False
    return surface


def bridge_surface(replicate: int, bound_record_id: str):
    surface = copy.deepcopy(_base_bridge_surface(replicate, bound_record_id))
    surface["input_schema"]["properties"]["chain_bridge"] = {
        "type": "object",
        "properties": {
            "source_cycle": {"type": "integer"},
            "first_record_id": {"type": "string"},
            "phrase_shape": {"type": "string"},
            "part_count": {"type": "integer"},
            "exact_phrase_retained": {"type": "boolean"},
        },
        "required": [
            "source_cycle",
            "first_record_id",
            "phrase_shape",
            "part_count",
            "exact_phrase_retained",
        ],
        "additionalProperties": False,
    }
    return surface


def aggregate(results):
    summary = _base_aggregate(results)
    prior = summary.get("hypothesis_results", {})
    summary["hypothesis_results"] = {
        "H481_step1_budget_stop": prior.get("H461_step1_budget_stop"),
        "H482_step2_budget_stop": prior.get("H462_step2_budget_stop"),
        "H483_final_receives_bridge_record_context": prior.get(
            "H464_generated_context_delivered"
        ),
        "H484_final_recovers_and_uses_bridge": prior.get(
            "H463_final_quiesces"
        ),
        "H485_all_wakes_valid_no_repair": prior.get(
            "H465_first_pass_no_repair"
        ),
    }
    return summary


base_runner.first_surface = first_surface
base_runner.bridge_surface = bridge_surface
base_runner.aggregate = aggregate


if __name__ == "__main__":
    base_runner.main()
