from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2a_interleaving_restart_resume_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2a_interleaving_restart_resume",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_interleaving_restart_resume_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["interleaved_identity_sequence"] is True
    assert checks["entity_prior_state_isolated"] is True
    assert checks["recovered_one_interrupted_entity_continuation"] is True
    assert checks["no_suppressed_events"] is True
    assert checks["interrupted_event_recovered_and_completed"] is True
    assert checks["reconstructed_entity_state_for_resume"] is True
    assert result["success"]["interrupted_event_history"] == [
        "pending",
        "running",
        "pending",
        "running",
        "completed",
    ]
    assert [
        record["event_type"]
        for record in result["success"]["recovered_event_records"]
    ] == ["entity_continuation"]
    assert "entity_green" in result["success"]["reconstructed_entity_ids"]


def test_preregistration_artifacts_capture_interruption_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["base_protocol"] == "phase_2a_larger_multi_entity_loop_20260618"
    assert matrix["interruption"] == {
        "event_type": "entity_continuation",
        "entity_id": "entity_green",
        "round_index": 2,
        "point": "after claim as running before exchange",
        "expected_history": [
            "pending",
            "running",
            "pending",
            "running",
            "completed",
        ],
    }
    assert matrix["yanantin_enabled"] is False
    assert budget["max_live_calls"] == 16
    assert "restart_frontier" in taxonomy["layers"]
    assert "state_reconstruction" in taxonomy["layers"]
