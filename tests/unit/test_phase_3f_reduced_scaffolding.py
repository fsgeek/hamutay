from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3f_reduced_scaffolding_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3f_reduced_scaffolding",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_reduced_scaffolding_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["all_memory_records_seeded"] is True
    assert checks["maintenance_actions_non_destructive"] is True
    assert checks["final_obsolete_report_records"] is True
    assert checks["final_disorder_reduced"] is True
    assert result["failure_attribution"] == []


def test_preregistration_artifacts_capture_reduced_scaffolding_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    profile = matrix["reduced_scaffolding_profile"]
    assert profile["exact_value_enums_removed"] is True
    assert profile["terminal_field_names_required"] is True
    assert profile["scoring_contract_unchanged_from_phase_3e"] is True
    assert budget["max_live_calls"] == 11
    assert "reduced_scaffolding" in taxonomy["layers"]
