from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3e_memory_maintenance_pressure_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3e_memory_maintenance_pressure",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_memory_maintenance_pressure_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["all_memory_records_seeded"] is True
    assert checks["stale_record_identified"] is True
    assert checks["duplicate_identified"] is True
    assert checks["contested_records_preserved"] is True
    assert checks["obsolete_report_identified"] is True
    assert checks["maintenance_actions_non_destructive"] is True
    assert checks["disorder_reduced"] is True
    assert checks["final_unresolved_contested"] is True
    assert checks["final_non_destructive"] is True
    assert checks["final_disorder_reduced"] is True
    assert result["failure_attribution"] == []

    final_state = result["success"]["final_state"]
    assert final_state["active_record_labels"] == module.EXPECTED_ACTIVE
    assert final_state["retired_record_labels"] == module.EXPECTED_RETIRED
    assert final_state["contested_record_labels"] == module.EXPECTED_CONTESTED
    assert final_state["unresolved_memory_items"] == module.EXPECTED_UNRESOLVED


def test_preregistration_artifacts_capture_memory_maintenance_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["memory_records"] == module.MEMORY_RECORDS
    assert matrix["expected_event_type_sequence"] == module.EXPECTED_EVENT_TYPES
    assert matrix["expected_active_record_labels"] == module.EXPECTED_ACTIVE
    assert matrix["expected_retired_record_labels"] == module.EXPECTED_RETIRED
    assert matrix["disorder_before_count"] == 4
    assert matrix["disorder_after_count"] == 1
    assert budget["max_live_calls"] == 11
    assert "memory_maintenance" in taxonomy["layers"]
    assert "unsupported_deletion" in taxonomy["layers"]
