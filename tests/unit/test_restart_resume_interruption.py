from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "restart_resume_interruption_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "restart_resume_interruption",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_restart_resume_recovers_interrupted_running_event(tmp_path):
    module = load_module()

    results = module.run_probe(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "passed"
    checks = results["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["recovered_one_housekeeping_event"] is True
    assert checks["no_suppressed_events"] is True
    assert checks["interrupted_event_recovered_and_completed"] is True
    assert checks["completed_records_in_session_log"] is True
    assert checks["multiple_frontier_updates"] is True
    assert results["success"]["completed_event_types"] == [
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
    ]
    assert results["success"]["interrupted_event_history"] == [
        "pending",
        "running",
        "pending",
        "running",
        "completed",
    ]


def test_preregistration_artifacts_capture_interruption_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["interruption_point"] == (
        "after housekeeping pending event is claimed running"
    )
    assert matrix["expected_recovered_event_type"] == "housekeeping"
    assert matrix["expected_completed_event_types"] == [
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
    ]
    assert "restart_frontier" in taxonomy["layers"]
    assert "event_lifecycle" in taxonomy["layers"]
    assert budget["max_live_calls"] == 4
