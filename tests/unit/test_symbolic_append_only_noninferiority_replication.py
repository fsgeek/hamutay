from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "event_loop_symbolic_append_only_noninferiority_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "symbolic_append_only_noninferiority_replication",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preregistration_artifacts_declare_symbolic_contract(tmp_path):
    module = load_module()

    manifest = module.write_preregistration_artifacts(
        tmp_path,
        live_model_calls=True,
    )

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert manifest["experiment_id"] == module.EXPERIMENT_ID
    assert matrix["symbolic_contract"] == module.SYMBOLIC_CONTRACT
    assert len(matrix["tasks"]) == 5
    assert budget["max_live_calls"] == 15
    assert "model_output" in taxonomy["layers"]


def test_dry_panel_uses_symbolic_bound_event_loop_rows(tmp_path):
    module = load_module()

    results = module.run_panel(output_root=tmp_path, overwrite=True)

    assert results["classification"] == "survived"
    assert results["symbolic_contract"] == module.SYMBOLIC_CONTRACT
    assert len(results["rows"]) == 10
    event_rows = [
        row for row in results["rows"]
        if row["condition"] == "event_loop_scheduled"
    ]
    assert len(event_rows) == 5
    assert all(row["symbolic_contract"] == module.SYMBOLIC_CONTRACT for row in event_rows)
    assert all(
        row["scheduler_checks"]["checks"]["symbolic_binding_contract"]
        for row in event_rows
    )
    assert all(
        row["context_accounting"]["symbolic_binding_contract"]
        == module.SYMBOLIC_CONTRACT
        for row in event_rows
    )

    first_row_root = (
        tmp_path
        / "rows"
        / event_rows[0]["task_id"]
        / "event_loop_scheduled"
    )
    restart_frontier = json.loads((first_row_root / "restart_frontier.json").read_text())
    assert restart_frontier["binding_contract"] == module.SYMBOLIC_CONTRACT
    assert restart_frontier["bound_continuation"]["terminal_surface"]["tool_name"] == (
        "write_matched_artifact"
    )


def test_symbolic_binding_rejects_concrete_model_authored_context():
    module = load_module()

    bound = module.bind_symbolic_continuation_request(
        {
            "requested": True,
            "purpose": "continue",
            "symbolic_context": [
                {"source": "completed_wake_state", "field": "declared_losses"}
            ],
            "requested_context": [
                {
                    "tool": "recall",
                    "record_id": "wrong-record",
                    "field": "declared_losses",
                }
            ],
            "terminal_surface": {"tool_name": "wrong_surface"},
            "record_id": "wrong-record",
            "label": "artifact-wake",
        },
        result_record_id="framework-record",
        terminal_tool_choice="auto",
    )

    assert bound["binding_contract"] == module.SYMBOLIC_CONTRACT
    assert bound["requested_context"] == [
        {
            "tool": "recall",
            "record_id": "framework-record",
            "field": "declared_losses",
        }
    ]
    assert bound["terminal_surface"]["tool_name"] == "write_matched_artifact"
    assert bound["ignored_model_authored_fields"] == [
        "record_id",
        "requested_context",
        "terminal_surface",
    ]
