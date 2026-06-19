from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "event_loop"
    / "phase_3d_richer_ipc_ingress_20260619"
    / "deterministic_replay_audit.py"
)
SPLIT_FINAL_RESULT = (
    PROJECT_ROOT
    / "experiments"
    / "event_loop"
    / "phase_3d_richer_ipc_ingress_20260619_direct_deepseek_split_final"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "phase_3d_deterministic_replay_audit",
        AUDIT_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_deterministic_replay_reconstructs_split_final_category_truth():
    module = load_module()

    audit = module.audit_result_dir(SPLIT_FINAL_RESULT)

    assert audit["finding"]["substrate_category_truth_reconstructable"] is True
    assert audit["finding"]["substrate_evidence_truth_reconstructable"] is True
    assert audit["finding"]["model_event_category_truth_reconstructable"] is True
    assert audit["finding"]["evidence_citation_constrained_by_surface"] is True
    ledger = audit["substrate_declared_ledger"]
    assert ledger["accepted_task_message_labels"] == ["task-alpha", "task-beta"]
    assert ledger["accepted_non_task_message_labels"] == [
        "cancel-beta",
        "correction-alpha",
        "evidence-alpha",
        "status-all",
    ]
    assert ledger["rejected_message_labels"] == ["cancel-ghost"]
    assert ledger["completed_message_labels"] == ["task-alpha"]


def test_deterministic_replay_writes_outputs(tmp_path):
    module = load_module()

    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"
    exit_code = module.main(
        [
            str(SPLIT_FINAL_RESULT),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    assert "all_substrate_ledgers_reconstructable" in output_json.read_text()
    assert "Deterministic Replay Audit" in output_md.read_text()
