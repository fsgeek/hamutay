from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3c_longer_wall_clock_sustained_operation_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3c_longer_wall_clock_sustained_operation",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_wall_clock_sustained_operation_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(
        output_root=tmp_path,
        overwrite=True,
        delay_seconds=module.MIN_OBSERVED_DELAY_SECONDS,
    )

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_nine_events"] is True
    assert checks["event_type_sequence"] is True
    assert checks["observed_delay_windows"] is True
    assert checks["delayed_events_waited_before_start"] is True
    assert checks["report_consistency"] is True
    assert checks["interrupted_event_recovered_and_completed"] is True
    assert checks["recovered_one_interrupted_event"] is True
    assert checks["final_distinguishes_operation_state"] is True
    final_state = result["success"]["final_after_state"]
    assert final_state["elapsed_delay_window_labels"] == [
        "alpha-report-delay",
        "beta-restart-delay",
    ]
    assert final_state["currently_pending_event_labels"] == []
    assert result["success"]["interrupted_event_history"] == [
        "pending",
        "running",
        "pending",
        "running",
        "completed",
    ]
    assert result["failure_attribution"] == []


def test_preregistration_artifacts_capture_wall_clock_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["delay_windows"] == module.DELAY_WINDOWS
    assert matrix["minimum_observed_delay_seconds"] == (
        module.MIN_OBSERVED_DELAY_SECONDS
    )
    assert matrix["expected_event_type_sequence"] == module.EXPECTED_EVENT_TYPES
    assert budget["max_live_calls"] == 10
    assert "elapsed_time_scheduler" in taxonomy["layers"]
    assert "restart_frontier" in taxonomy["layers"]


def test_preserved_state_labels_accept_concrete_state_fields():
    module = load_module()

    assert module.preserved_state_labels_sufficient(
        [
            "probe_status",
            "open_items",
            "workstream_id",
            "continuation_request",
            "report_status",
            "unsupported_claims",
        ]
    )
