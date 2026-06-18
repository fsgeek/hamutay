from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "declared_loss_discipline_stress_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "declared_loss_discipline_stress",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_controls_separate_exact_scoring_from_material_discipline(tmp_path):
    module = load_module()

    results = module.run_panel(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "dry_controls_ready"
    checks = results["summary"]["checks"]
    assert checks["exact_control_passed"] is True
    assert checks["semantic_control_has_material_loss"] is True
    assert checks["semantic_control_rejected_by_exact_scorer"] is True
    assert checks["actionless_exact_not_material"] is True

    rows = {row["row_id"]: row for row in results["rows"]}
    assert rows["exact_marker_control"]["score"]["exact_declared_loss_rate"] == 1.0
    assert rows["semantic_equivalent_control"]["score"]["exact_declared_loss_rate"] == 0.0
    assert rows["semantic_equivalent_control"]["score"]["semantic_loss_present"] is True
    assert rows["actionless_exact_control"]["score"]["material_loss_discipline"] is False


def test_preregistration_artifacts_capture_diagnostics(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["loss_marker"] == "missing calibration evidence"
    assert matrix["diagnostic_rows"] == [
        "exact_marker_control",
        "semantic_equivalent_control",
        "actionless_exact_control",
        "live_unanchored",
        "live_anchored",
    ]
    assert budget["max_live_calls"] == 2
    assert "scorer" in taxonomy["layers"]


def test_classify_live_rows_attributes_anchoring_effect():
    module = load_module()
    rows = [
        {
            "row_id": "exact_marker_control",
            "mode": "deterministic_control",
            "score": {
                "exact_declared_loss_rate": 1.0,
                "semantic_loss_present": True,
                "material_loss_discipline": True,
            },
            "failure_attribution": {"layer": "none"},
        },
        {
            "row_id": "semantic_equivalent_control",
            "mode": "deterministic_control",
            "score": {
                "exact_declared_loss_rate": 0.0,
                "semantic_loss_present": True,
                "material_loss_discipline": True,
            },
            "failure_attribution": {"layer": "none"},
        },
        {
            "row_id": "actionless_exact_control",
            "mode": "deterministic_control",
            "score": {
                "exact_declared_loss_rate": 1.0,
                "semantic_loss_present": True,
                "material_loss_discipline": False,
            },
            "failure_attribution": {"layer": "none"},
        },
        {
            "row_id": "live_unanchored",
            "mode": "live",
            "score": {
                "exact_declared_loss_rate": 0.0,
                "semantic_loss_present": True,
                "material_loss_discipline": True,
            },
            "failure_attribution": {"layer": "none"},
        },
        {
            "row_id": "live_anchored",
            "mode": "live",
            "score": {
                "exact_declared_loss_rate": 1.0,
                "semantic_loss_present": True,
                "material_loss_discipline": True,
            },
            "failure_attribution": {"layer": "none"},
        },
    ]

    summary = module.classify(rows, live_model_calls=True)

    assert summary["classification"] == (
        "prompt_rubric_primary_with_lexical_scorer_caveat"
    )
    assert summary["readiness_criterion_met"] is True
    assert "primary cause" in summary["attribution"]["prompt_rubric"]
