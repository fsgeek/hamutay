from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2b_yanantin_memory_contract_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2b_yanantin_memory_contract",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_contract_validator_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    assert result["failure_attribution"] == []
    checks = result["success"]["checks"]
    assert all(checks.values())
    assert result["success"]["missing_provenance_fields"] == []
    assert result["success"]["missing_retrieval_envelope_fields"] == []
    assert result["success"]["surface"]["missing_memory_port_methods"] == []
    assert result["success"]["surface"]["missing_apacheta_bridge_methods"] == []
    assert (tmp_path / "results.json").exists()


def test_matrix_preserves_substrate_distinctions():
    matrix_path = RUN_PATH.parent / "matrix.json"
    budget_path = RUN_PATH.parent / "budget.json"

    matrix = json.loads(matrix_path.read_text())
    budget = json.loads(budget_path.read_text())

    assert matrix["recall_substrates"] == [
        "in_session_state",
        "local_artifact_recall",
        "yanantin_backed_recall",
    ]
    assert "entity_scoped" in matrix["memory_scopes"]
    assert "shared" in matrix["memory_scopes"]
    assert matrix["record_classes"]["yanantin_writes"]
    assert matrix["record_classes"]["local_only"]
    assert budget["live_model_calls"] is False
    assert budget["max_live_calls"] == 0
