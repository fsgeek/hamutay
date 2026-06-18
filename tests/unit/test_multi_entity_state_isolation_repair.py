from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "multi_entity_state_isolation_repair_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "multi_entity_state_isolation_repair",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_state_isolation_repair_preserves_identity_and_attribution(tmp_path):
    module = load_module()

    results = module.run_probe(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "passed"
    checks = results["success"]["checks"]
    assert checks["completed_six_events"] is True
    assert checks["entity_prior_state_isolated"] is True
    assert checks["entity_event_identity_preserved"] is True
    assert checks["audit_no_contamination"] is True
    assert checks["audit_no_attribution_errors"] is True
    assert checks["final_no_contamination"] is True
    assert checks["final_no_attribution_errors"] is True
    assert checks["multiple_frontier_updates"] is True
    assert results["success"]["observed_entity_pairs"] == [
        ["entity_red", "red_stream"],
        ["entity_red", "red_stream"],
        ["entity_blue", "blue_stream"],
        ["entity_blue", "blue_stream"],
    ]
    assert results["success"]["entity_prior_state_leaks"] == []
    observations = results["success"]["entity_prior_state_observations"]
    assert len(observations) == 4
    assert observations[0]["entity_id"] == "entity_red"
    assert observations[2]["entity_id"] == "entity_blue"
    assert observations[2]["foreign_entity_mentions"] == []


def test_preregistration_artifacts_capture_state_isolation_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["expected_completed_event_count"] == 6
    assert matrix["expected_event_type_sequence"][-1] == "multi_entity_artifact"
    assert "entity-scoped wake state" in matrix["repair_contract"]
    assert matrix["entities"] == [
        {"entity_id": "entity_red", "workstream_id": "red_stream"},
        {"entity_id": "entity_blue", "workstream_id": "blue_stream"},
    ]
    assert "entity_state_isolation" in taxonomy["layers"]
    assert budget["max_live_calls"] == 7
