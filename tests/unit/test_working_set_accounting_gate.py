import importlib.util
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "working_set_accounting_gate_20260612"
    / "run.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("goal7_working_set_gate", RUN_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_request_classification_exercises_all_preregistered_categories():
    module = _load_module()
    substrate = module.build_bounded_corpus()

    rows = [
        module.classify_evidence_request(request, substrate=substrate)
        for request in module.model_authored_requests()
    ]

    assert {row["classification"] for row in rows} == {
        "answerable_by_substrate",
        "unavailable_but_well_formed",
        "structurally_impossible",
        "malformed_or_underspecified",
    }
    assert any(row.get("truncated") for row in rows)
    assert any(row["layer"] == "memory_substrate_coverage" for row in rows)
    assert any(row["layer"] == "recall_protocol" for row in rows)
    assert any(row["layer"] == "prompt_schema" for row in rows)


def test_accounting_distinguishes_context_layers_and_metrics():
    module = _load_module()

    accounting = module.build_working_set_accounting()
    results = module.score_accounting(accounting)

    assert results["classification"] == "survived"
    for section in module.REQUIRED_SECTIONS:
        assert section in accounting
    assert accounting["live_context"]
    assert accounting["carried_state"]
    assert accounting["recalled_context"]
    assert accounting["omitted_context"]
    assert accounting["declared_losses"]
    assert accounting["token_counts"]["total_accounted"] > 0
    assert accounting["recovery_metrics"]["recovery_rate"] == 2 / 3
    assert accounting["contamination_metrics"]["contamination_rate"] == 0.0
    assert accounting["truncation_metadata"]


def test_gate_writes_readiness_artifacts(tmp_path):
    module = _load_module()

    exit_code = module.main(["--output-root", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "working_set_accounting.json").exists()
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "analysis.md").exists()
    results = json_load(tmp_path / "results.json")
    assert results["summary"]["ready_for_goal_8"] is True


def json_load(path: Path):
    import json

    return json.loads(path.read_text())
