"""Run controlled-seed delayed-thinking gate with revised event envelope."""

from __future__ import annotations

import importlib.util
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
BASE_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/delayed_thinking_controlled_seed_20260605/"
    / "run_controlled_seed_delayed_thinking.py"
)


def load_base_runner():
    spec = importlib.util.spec_from_file_location(
        "controlled_seed_delayed_thinking_base",
        BASE_RUNNER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base runner from {BASE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    base = load_base_runner()
    base.EXP_DIR = EXP_DIR
    base.PROJECT_ROOT = PROJECT_ROOT
    base.main()


if __name__ == "__main__":
    main()
