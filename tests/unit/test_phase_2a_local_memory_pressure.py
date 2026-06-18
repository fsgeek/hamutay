from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2a_local_memory_pressure_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2a_local_memory_pressure",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_local_memory_pressure_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["recall_required_local_context"] is True
    assert checks["recall_codes_correct"] is True
    assert checks["recall_source_records_present"] is True
    assert checks["housekeeping_checked_recall_records"] is True
    assert checks["housekeeping_clean"] is True
    assert checks["final_codes"] is True
    assert checks["final_provenance_records"] is True
    assert checks["yanantin_gate_remains_closed"] is True
    assert len(result["success"]["recall_states"]) == 3
    assert result["success"]["recall_prior_leaks"] == []


def test_preregistration_artifacts_capture_local_memory_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["memory_substrate"] == "local_requested_context_only"
    assert matrix["yanantin_enabled"] is False
    assert matrix["expected_event_type_sequence"] == [
        "local_commitment",
        "local_commitment",
        "local_commitment",
        "local_recall",
        "local_recall",
        "local_recall",
        "local_memory_housekeeping",
        "local_memory_final",
    ]
    assert budget["max_live_calls"] == 9
    assert "local_recall" in taxonomy["layers"]
    assert "yanantin_gate" in taxonomy["layers"]
