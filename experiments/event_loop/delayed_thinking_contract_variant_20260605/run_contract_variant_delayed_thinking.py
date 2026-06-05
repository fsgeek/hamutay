"""Run controlled delayed-thinking gate with explicit durable update contract."""

from __future__ import annotations

import importlib.util
import json
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


def durable_update_contract(expected_probe_id: str) -> dict:
    return {
        "required_top_level": {
            "probe_id": {"equals": expected_probe_id},
            "thinking_status": {"equals": "completed"},
            "delayed_thought": {"type": "non_empty_string"},
            "wake_observation": {
                "type": "object",
                "required": {"kind": "delayed_thinking"},
            },
            "observations": {"contains": "baseline_observation"},
        }
    }


def make_contract_schedule_prompt(base, model: str, replicate: int) -> str:
    expected_probe_id = base.probe_id_for(model, replicate)
    requested_context = [{"tool": "recall", "cycle": 1}]
    contract = durable_update_contract(expected_probe_id)
    purpose = f"""
You are the delayed simulated-time wake for probe_id
{expected_probe_id}.

Use the recalled cycle 1 state to complete the delayed thinking question.

Required durable wake updates:
- Preserve probe_id.
- Set top-level thinking_status to "completed".
- Add top-level delayed_thought as a non-empty string.
- Add top-level wake_observation with kind "delayed_thinking".
- Preserve the baseline observation.

Do not recursively schedule an event.
""".strip()
    return f"""
Registered delayed thinking scheduling cycle with explicit durable contract.
model={model}
replicate={replicate + 1}

Call schedule_event exactly once and wait for its result. Use exactly:
- requested_context: {json.dumps(requested_context)}
- not_before: {base.NOT_BEFORE}
- label: delayed-thinking-{base.safe_model_name(model)}-r{replicate + 1}
- durable_update_contract:
{json.dumps(contract, indent=2)}

Event purpose:
{purpose}

After schedule_event returns an event_id, set thinking_status to "scheduled" and
end with think_and_respond. Do not call read, search_project, bash, or clock.
""".strip()


def main() -> None:
    runner = load_base_runner()
    runner.EXP_DIR = EXP_DIR
    runner.PROJECT_ROOT = PROJECT_ROOT
    original_base = runner.base
    original_base.schedule_prompt = (
        lambda model, replicate: make_contract_schedule_prompt(
            original_base,
            model,
            replicate,
        )
    )
    runner.main()


if __name__ == "__main__":
    main()
