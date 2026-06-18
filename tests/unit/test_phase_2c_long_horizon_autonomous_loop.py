from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2c_long_horizon_autonomous_loop_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2c_long_horizon_autonomous_loop",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_autonomous_loop_pilot_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_nine_events"] is True
    assert checks["event_type_sequence"] is True
    assert checks["terminal_surface_sequence"] is True
    assert checks["two_workstreams"] is True
    assert checks["two_periodic_reports"] is True
    assert checks["interrupted_event_recovered_and_completed"] is True
    assert checks["recovered_one_interrupted_event"] is True
    assert checks["multiple_frontier_updates"] is True
    assert result["success"]["interrupted_event_history"] == [
        "pending",
        "running",
        "pending",
        "running",
        "completed",
    ]
    assert result["failure_attribution"] == []


def test_preregistration_artifacts_capture_autonomous_loop_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["expected_completed_event_count"] == 9
    assert matrix["expected_event_type_sequence"] == module.EXPECTED_EVENT_TYPES
    assert matrix["interruption"]["task_label"] == "beta"
    assert budget["max_live_calls"] == 10
    assert "restart_frontier" in taxonomy["layers"]
    assert "periodic_reporting" in taxonomy["layers"]
