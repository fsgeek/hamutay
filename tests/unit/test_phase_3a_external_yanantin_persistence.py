from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3a_external_yanantin_persistence_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3a_external_yanantin_persistence",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_persistent_yanantin_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["retrieval_context_has_yanantin_provenance"] is True
    assert checks["persistent_db_file_exists"] is True
    assert checks["backend_counts_include_records"] is True
    assert checks["reopened_source_records_retrievable"] is True
    assert checks["reopened_source_identity_preserved"] is True
    assert checks["operation_latencies_captured"] is True
    assert checks["open_record_query_limitations_explicit"] is True
    assert result["failure_attribution"] == []
    persistent = result["success"]["persistent_backend"]
    assert persistent["record_counts_before_reopen"]["records"] >= 8
    assert persistent["open_record_query_limitations"]
    assert (tmp_path / module.DB_FILENAME).exists()


def test_preregistration_artifacts_capture_persistent_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["backend"] == "ApachetaBridge.from_duckdb"
    assert matrix["persistent_artifact"] == module.DB_FILENAME
    assert matrix["base_protocol"] == "phase_2b_yanantin_backed_multi_entity_memory_20260618"
    assert budget["max_live_calls"] == 9
    assert "backend_persistence" in taxonomy["layers"]
    assert "backend_query_limitation" in taxonomy["layers"]
