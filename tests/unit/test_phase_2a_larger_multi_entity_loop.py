from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2a_larger_multi_entity_loop_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2a_larger_multi_entity_loop",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_larger_multi_entity_loop_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["interleaved_identity_sequence"] is True
    assert checks["entity_prior_state_isolated"] is True
    assert checks["housekeeping_count"] is True
    assert checks["housekeeping_clean"] is True
    assert checks["final_entity_count"] is True
    assert checks["final_round_count"] is True
    assert checks["final_completed_entity_events"] is True
    assert checks["scheduler_owned_fields_not_model_authored"] is True
    assert checks["local_artifacts_only"] is True
    assert len(result["success"]["completed_event_types"]) == 15
    assert len(result["success"]["observed_identity_sequence"]) == 12
    assert result["success"]["entity_prior_state_leaks"] == []
    assert result["success"]["frontier_line_count"] >= 16


def test_preregistration_artifacts_capture_larger_loop_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["expected_completed_event_count"] == 15
    assert matrix["memory_substrate"] == "local_artifacts_only"
    assert matrix["yanantin_enabled"] is False
    assert matrix["entities"] == [
        {"entity_id": "entity_red", "workstream_id": "red_stream"},
        {"entity_id": "entity_blue", "workstream_id": "blue_stream"},
        {"entity_id": "entity_green", "workstream_id": "green_stream"},
    ]
    assert matrix["expected_event_type_sequence"] == (
        ["entity_inbound"] * 3
        + ["entity_continuation"] * 3
        + ["scale_housekeeping"]
        + ["entity_inbound"] * 3
        + ["entity_continuation"] * 3
        + ["scale_housekeeping", "scale_final_artifact"]
    )
    assert budget["max_live_calls"] == 16
    assert "interleaving" in taxonomy["layers"]
    assert "housekeeping" in taxonomy["layers"]
