"""Repair rerun for the production terminal-surface substrate smoke."""

from __future__ import annotations

import importlib.util
from pathlib import Path


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/terminal_surface_substrate_smoke_20260605/"
    / "run_terminal_surface_substrate_smoke.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "terminal_surface_substrate_smoke_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load smoke runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base_runner = load_base_runner()
base_runner.EXP_DIR = EXP_DIR
base_runner.RESULTS_PATH = RESULTS_PATH
base_runner.CONDITION = "terminal_surface_substrate_smoke_repair"
base_runner.base.EXP_DIR = EXP_DIR
base_runner.sb.EXP_DIR = EXP_DIR


if __name__ == "__main__":
    base_runner.main()
