import importlib.util
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "working_set_matched_panel_20260612"
    / "run.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("goal8_working_set_panel", RUN_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_score_artifact_separates_recovery_from_contamination():
    module = _load_module()
    output = module.dry_provider_response("direct_one_shot", 1)
    output["claims"][0]["status"] = "verified"
    clean = module.score_artifact(output)

    contaminated = dict(output)
    contaminated["cited_record_ids"] = [
        *output["cited_record_ids"],
        module.DISTRACTOR_ID,
    ]
    dirty = module.score_artifact(contaminated)

    assert clean["recovery_rate"] == 1.0
    assert clean["contamination_rate"] == 0.0
    assert dirty["recovery_rate"] == 1.0
    assert dirty["contamination_rate"] == 1.0
    assert dirty["artifact_quality_score"] < clean["artifact_quality_score"]


def test_selection_payload_accepts_model_output_wrapped_by_prompt_shape():
    module = _load_module()
    wrapped = {
        "required_output": {
            "requested_context": [
                {"tool": "recall", "record_id": module.RECORD_IDS["ledger"]}
            ],
            "omitted_record_ids": [module.DISTRACTOR_ID],
        }
    }

    selected = module.selection_payload(wrapped)

    assert selected["requested_context"][0]["record_id"] == module.RECORD_IDS["ledger"]
    assert selected["omitted_record_ids"] == [module.DISTRACTOR_ID]


def test_working_set_score_uses_provenance_without_overwriting_artifact_quality():
    module = _load_module()
    artifact = module.score_artifact(module.dry_provider_response("direct_one_shot", 1))
    with_provenance = {
        "artifact_score": artifact,
        "context_accounting": {"recall_provenance": [{"tool": "recall"}]},
    }
    without_provenance = {
        "artifact_score": artifact,
        "context_accounting": {"recall_provenance": []},
    }

    assert module.working_set_score(with_provenance) > module.working_set_score(
        without_provenance
    )
    assert artifact["artifact_quality_score"] == module.score_artifact(
        module.dry_provider_response("direct_one_shot", 1)
    )["artifact_quality_score"]


def test_dry_run_matched_panel_writes_all_condition_artifacts(tmp_path):
    module = _load_module()
    exit_code = module.main(
        [
            "--dry-run",
            "--overwrite",
            "--output-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    results = module._json_copy(__import__("json").loads((tmp_path / "results.json").read_text()))
    assert results["classification"] == "survived"
    assert {
        row["condition"] for row in results["rows"]
    } == set(module.CONDITIONS)
    for condition in module.CONDITIONS:
        row_root = tmp_path / "rows" / condition
        assert (row_root / "context_accounting.json").exists()
        assert (row_root / "row_result.json").exists()
        assert (row_root / "memory_snapshot.json").exists()
