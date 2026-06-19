from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3b_degraded_memory_attribution_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3b_degraded_memory_attribution",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_degraded_memory_attribution_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["write_failure_injected"] is True
    assert checks["read_failure_injected"] is True
    assert checks["partial_retrieval_injected"] is True
    assert checks["delayed_retrieval_latency_captured"] is True
    assert checks["expected_context_errors_observed"] is True
    assert checks["failure_cases_declared_losses"] is True
    assert checks["partial_not_scored_as_success"] is True
    assert checks["delayed_retrieval_succeeded"] is True
    assert checks["final_declared_loss_cases"] is True
    assert checks["final_successful_retrieval_cases"] is True
    assert result["failure_attribution"] == []


def test_preregistration_artifacts_capture_degraded_memory_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["degradation_cases"] == module.CASE_IDS
    assert matrix["expected_event_type_sequence"] == module.EXPECTED_EVENT_TYPES
    assert budget["max_live_calls"] == 10
    assert "fallback_masking" in taxonomy["layers"]
    assert "partial_retrieval" in taxonomy["layers"]
