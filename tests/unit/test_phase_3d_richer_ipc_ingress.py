from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "phase_3d_richer_ipc_ingress_20260619"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3d_richer_ipc_ingress",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dry_richer_ipc_ingress_probe_passes(tmp_path):
    module = load_module()

    result = module.run_probe(output_root=tmp_path, overwrite=True)

    assert result["classification"] == "passed"
    checks = result["success"]["checks"]
    assert checks["completed_expected_events"] is True
    assert checks["event_type_sequence"] is True
    assert checks["terminal_surface_sequence"] is True
    assert checks["task_routing"] is True
    assert checks["correction_applied_to_alpha"] is True
    assert checks["cancellation_isolated_to_beta"] is True
    assert checks["unknown_cancellation_rejected"] is True
    assert checks["corrected_continuation_completed"] is True
    assert checks["status_query_consistent"] is True
    assert checks["external_evidence_routed"] is True
    assert checks["category_summary"] is True
    assert checks["category_summary_clean"] is True
    assert checks["claim_audit_clean"] is True
    assert checks["final_uses_split_summaries"] is True
    assert checks["final_workstream_isolation"] is True
    category_state = result["success"]["category_state"]
    claim_audit_state = result["success"]["claim_audit_state"]
    final_state = result["success"]["final_state"]
    assert category_state["accepted_task_message_labels"] == [
        "task-alpha",
        "task-beta",
    ]
    assert sorted(category_state["accepted_non_task_message_labels"]) == [
        "cancel-beta",
        "correction-alpha",
        "evidence-alpha",
        "status-all",
    ]
    assert claim_audit_state["unsupported_claims"] == []
    assert claim_audit_state["unresolved_open_items"] == []
    assert final_state["summary_source_labels"] == ["category-summary", "claim-audit"]
    assert final_state["unresolved_open_items"] == []
    assert final_state["unsupported_claims"] == []
    assert result["failure_attribution"] == []


def test_preregistration_artifacts_capture_richer_ipc_contract(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["message_plan"] == module.MESSAGE_PLAN
    assert matrix["expected_event_type_sequence"] == module.EXPECTED_EVENT_TYPES
    assert matrix["expected_terminal_tools"] == module.EXPECTED_TERMINAL_TOOLS
    assert matrix["expected_categories"]["rejected"] == ["cancel-ghost"]
    assert budget["max_live_calls"] == 12
    assert "message_routing" in taxonomy["layers"]
    assert "continuation_binding" in taxonomy["layers"]
