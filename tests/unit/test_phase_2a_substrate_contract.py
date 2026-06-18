from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2a_substrate_contract_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2a_substrate_contract",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_substrate_contract_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["underlying_protocol_passed"] is True
    assert checks["private_entity_prior_state_isolated"] is True
    assert checks["entity_identity_preserved"] is True
    assert checks["authorized_shared_context_explicit"] is True
    assert checks["audit_and_final_clean"] is True
    assert checks["scheduler_owned_fields_not_model_authored"] is True
    assert checks["failure_attribution_surface_present"] is True
    assert result["failure_attribution"] == []
    assert result["success"]["scheduler_owned_field_violations"] == []
    assert len(result["success"]["private_entity_prior_state_observations"]) == 4


def test_preregistration_artifacts_capture_contract_checks(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["contract"] == "CONTRACT.md"
    assert matrix["underlying_protocol"] == "multi_entity_state_isolation_repair_20260618"
    assert matrix["required_checks"] == [
        "private_entity_prior_state_isolated",
        "entity_identity_preserved",
        "authorized_shared_context_explicit",
        "audit_and_final_clean",
        "scheduler_owned_fields_not_model_authored",
        "failure_attribution_surface_present",
    ]
    assert budget["max_live_calls"] == 7
    assert "state_isolation" in taxonomy["layers"]
    assert "scheduler_field_ownership" in taxonomy["layers"]
