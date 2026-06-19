from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3d_durable_category_ledger_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3d_durable_category_ledger",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_durable_category_ledger_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["durable_category_ledger_present"] is True
    assert checks["durable_category_ledger_expected"] is True
    assert checks["category_summary_uses_durable_ledger"] is True
    assert checks["claim_audit_uses_durable_ledger"] is True
    assert checks["final_uses_durable_ledger"] is True
    assert checks["final_preserves_category_ledger"] is True
    assert result["success"]["durable_category_ledger"] == (
        module.EXPECTED_CATEGORY_LEDGER
    )
    final_state = result["success"]["final_state"]
    assert final_state["accepted_non_task_message_labels"] == [
        "cancel-beta",
        "correction-alpha",
        "evidence-alpha",
        "status-all",
    ]
    assert final_state["rejected_message_labels"] == ["cancel-ghost"]
    assert final_state["unsupported_claim_candidates"] == [
        "task-ghost was cancelable"
    ]
    assert final_state["unsupported_claims"] == []
    assert result["failure_attribution"] == []

    snapshots = module.read_category_ledger_snapshots(tmp_path)
    assert snapshots[-1]["ledger"] == module.EXPECTED_CATEGORY_LEDGER


def test_preregistration_artifacts_capture_durable_ledger_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["message_plan"] == module.MESSAGE_PLAN
    assert matrix["expected_event_type_sequence"] == module.EXPECTED_EVENT_TYPES
    assert matrix["category_ledger_artifact"] == "category_ledger.jsonl"
    assert matrix["expected_category_ledger"] == module.EXPECTED_CATEGORY_LEDGER
    assert budget["max_live_calls"] == 12
    assert "category_ledger" in taxonomy["layers"]
