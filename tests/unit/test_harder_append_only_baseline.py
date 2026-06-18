from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "harder_append_only_baseline_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "harder_append_only_baseline",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_declared_loss_contract_is_added_to_loss_tasks():
    module = load_module()

    request = module.stronger_append_only_request("declared_loss_discipline")

    assert request["declared_loss_contract"]["required_exact_markers"] == [
        "missing calibration evidence"
    ]
    assert "audit_checklist" in request
    assert "missing calibration evidence" in json.dumps(request)


def test_dry_panel_runs_harder_baseline_shape(tmp_path):
    module = load_module()

    results = module.run_panel(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "survived"
    assert len(results["rows"]) == 10
    append_rows = [
        row for row in results["rows"]
        if row["condition"] == "append_only"
    ]
    assert all(
        row["baseline_strength"] == "harder_one_shot_with_audit_checklist"
        for row in append_rows
    )
    assert results["artifact_noninferiority"]["passed"] is True


def test_preregistration_artifacts_capture_harder_baseline(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    assert matrix["append_only_baseline"] == "harder_one_shot_with_audit_checklist"
    assert matrix["declared_loss_policy"] == "exact_marker_contract_required"
    assert budget["max_live_calls"] == 15
