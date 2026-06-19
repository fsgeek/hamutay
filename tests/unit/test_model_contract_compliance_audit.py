from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "model_contract_compliance_audit_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "model_contract_compliance_audit",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_model_contract_compliance_audit_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["terminal_surface_sequence"] is True
    assert checks["vocabulary_exact"] is True
    assert checks["provenance_uses_record_labels"] is True
    assert checks["provenance_avoids_record_ids"] is True
    assert checks["kind_source_exact"] is True
    assert checks["count_semantics_exact"] is True
    assert result["failure_attribution"] == []


def test_preregistration_artifacts_capture_contract_dimensions(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert (tmp_path / "CONTRACT.md").exists()
    assert (tmp_path / "PRE_REGISTRATION.md").exists()
    assert matrix["expected_action_labels"] == module.EXPECTED_ACTION_LABELS
    assert matrix["expected_provenance_link"] == module.EXPECTED_PROVENANCE_LINK
    assert matrix["expected_kind_source"] == module.EXPECTED_KIND_SOURCE
    assert matrix["expected_counts"] == module.EXPECTED_COUNTS
    assert matrix["schema_profile"]["exact_value_enums_removed"] is True
    assert matrix["schema_profile"]["probes_are_isolated"] is True
    assert budget["max_live_calls"] == 5
    assert "count_semantics_compliance" in taxonomy["layers"]
