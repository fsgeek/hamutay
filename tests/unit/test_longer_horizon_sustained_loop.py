from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "longer_horizon_sustained_loop_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "longer_horizon_sustained_loop",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_dry_longer_horizon_loop_completes_two_tasks_and_final_artifact(tmp_path):
    module = load_module()

    results = module.run_probe(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "passed"
    assert results["success"]["checks"]["completed_seven_events"] is True
    assert results["success"]["checks"]["two_inbound_events"] is True
    assert results["success"]["checks"]["two_continuation_events"] is True
    assert results["success"]["checks"]["two_housekeeping_events"] is True
    assert results["success"]["checks"]["one_final_artifact"] is True
    assert results["success"]["checks"]["final_task_count"] is True
    assert results["success"]["checks"]["final_labels"] is True
    assert results["success"]["checks"]["multiple_frontier_updates"] is True
    assert results["success"]["completed_event_types"] == [
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
        "final_artifact_synthesis",
    ]
    assert results["success"]["completed_terminal_surface_tools"][-1] == (
        "write_long_horizon_artifact"
    )

    events = read_jsonl(tmp_path / "events.jsonl")
    assert sum(1 for event in events if event.get("status") == "completed") == 7
    assert (tmp_path / "restart_frontier.jsonl").exists()


def test_preregistration_artifacts_capture_long_horizon_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    assert matrix["expected_completed_event_count"] == 7
    assert matrix["expected_event_type_sequence"][-1] == "final_artifact_synthesis"
    assert budget["max_live_calls"] == 8
