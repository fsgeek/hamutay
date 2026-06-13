import importlib.util
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "artifact_noninferiority_20260612"
    / "run.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("goal10_artifact_panel", RUN_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_artifact_score_penalizes_contamination_without_hiding_recovery():
    module = _load_module()
    task_id = "memory_boundary_note"
    clean = module.dry_provider_response(task_id, "direct_one_shot", 1)
    clean_score = module.score_artifact(task_id, clean)

    contaminated = dict(clean)
    contaminated["cited_record_ids"] = [
        *clean["cited_record_ids"],
        module.TASKS[task_id]["distractor_id"],
    ]
    dirty_score = module.score_artifact(task_id, contaminated)

    assert clean_score["recovery_rate"] == 1.0
    assert dirty_score["recovery_rate"] == 1.0
    assert clean_score["contamination_rate"] == 0.0
    assert dirty_score["contamination_rate"] == 1.0
    assert dirty_score["artifact_quality_score"] < clean_score["artifact_quality_score"]
    assert dirty_score["catastrophic_failure"] is True


def test_noninferiority_summary_separates_quality_from_observability(tmp_path):
    module = _load_module()
    result = module.run_panel(
        output_root=tmp_path,
        dry_run=True,
        overwrite=True,
        api_key=None,
        endpoint=module.DEFAULT_ENDPOINT,
        model=module.DEFAULT_MODEL,
    )

    assert result["classification"] == "survived"
    assert result["summary"]["artifact_non_inferior"] is True
    assert result["summary"]["observability_stronger"] is True
    assert result["summary"]["observability_delta_event_minus_direct"] > 0


def test_dry_run_preserves_traces_scores_and_review_packet(tmp_path):
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
    results = module._read_json(tmp_path / "results.json")
    assert len(results["rows"]) == len(module.TASKS) * 2
    assert (tmp_path / "review_packet" / "manifest.json").exists()
    for task_id in module.TASKS:
        for condition in module.CONDITIONS:
            row_root = tmp_path / "rows" / task_id / condition
            assert (row_root / "row_result.json").exists()
            assert (row_root / "score.json").exists()
            assert (row_root / "observability_score.json").exists()
            assert (row_root / "context_accounting.json").exists()
            assert (row_root / "cycle_01.json").exists()
        assert (
            tmp_path / "rows" / task_id / "event_loop_bounded" / "cycle_02.json"
        ).exists()
