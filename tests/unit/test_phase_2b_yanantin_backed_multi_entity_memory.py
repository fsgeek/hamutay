from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_2b_yanantin_backed_multi_entity_memory_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_2b_yanantin_backed_multi_entity_memory",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_yanantin_backed_memory_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["recall_required_yanantin_context"] is True
    assert checks["recall_codes_correct"] is True
    assert checks["retrieval_context_has_yanantin_provenance"] is True
    assert checks["final_provenance_includes_source_records"] is True
    assert result["failure_attribution"] == []
    assert len(result["success"]["yanantin_context_observations"]) == 3
    assert result["yanantin"]["open_record_count"] >= 8


def test_preregistration_artifacts_capture_yanantin_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["memory_substrate"] == "yanantin_apacheta_bridge_in_memory"
    assert matrix["yanantin_enabled"] is True
    assert matrix["expected_event_type_sequence"] == [
        "yanantin_commitment",
        "yanantin_commitment",
        "yanantin_commitment",
        "yanantin_recall",
        "yanantin_recall",
        "yanantin_recall",
        "yanantin_memory_housekeeping",
        "yanantin_memory_final",
    ]
    assert budget["max_live_calls"] == 9
    assert "yanantin_retrieval" in taxonomy["layers"]
    assert "provenance" in taxonomy["layers"]
