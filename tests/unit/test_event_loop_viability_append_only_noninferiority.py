import importlib.util
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "event_loop_viability_append_only_noninferiority_20260614"
    / "run.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("event_loop_append_only_panel", RUN_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_matrix_separates_scheduler_viability_from_artifact_quality():
    module = _load_module()

    matrix = module.matrix()

    assert matrix["claim_separation"]["shared_surface_noninferiority"] == (
        "fair head-to-head comparison on common artifact and trace axes"
    )
    assert matrix["claim_separation"]["scheduler_added_value"] == (
        "event-loop-only reconstruction evidence, not an append_only penalty"
    )
    assert matrix["conditions"] == list(module.CONDITIONS)


def test_score_artifact_penalizes_distractor_without_hiding_recovery():
    module = _load_module()
    task_id = "scheduler_boundary_note"
    clean = module.dry_artifact_cycle(
        task_id=task_id,
        condition="append_only",
        corpus=module.TASKS[task_id]["records"],
        carried_state=None,
    )["parsed"]
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


def test_scheduler_viability_gate_is_independent_of_artifact_score(tmp_path):
    module = _load_module()
    result = module.run_panel(output_root=tmp_path, overwrite=True)

    rows = result["rows"]
    assert result["scheduler_viability"]["passed"] is True
    assert result["artifact_noninferiority"]["passed"] is True

    broken = module._read_json(
        tmp_path
        / "rows"
        / "scheduler_boundary_note"
        / "event_loop_scheduled"
        / "row_result.json"
    )
    broken["scheduler_checks"]["passed"] = False
    broken["scheduler_checks"]["checks"]["status_sequence_valid"] = False
    rescored = module.score_scheduler_viability(
        [
            broken if row["task_id"] == broken["task_id"]
            and row["condition"] == broken["condition"] else row
            for row in rows
        ]
    )

    assert rescored["passed"] is False
    assert broken["artifact_score"]["artifact_quality_score"] == 1.0


def test_append_only_is_not_penalized_on_scheduler_specific_observability(tmp_path):
    module = _load_module()
    result = module.run_panel(output_root=tmp_path, overwrite=True)

    assert result["shared_surface_observability"]["passed"] is True
    assert (
        result["shared_surface_observability"][
            "event_loop_mean_shared_surface_observability"
        ]
        == result["shared_surface_observability"][
            "append_only_mean_shared_surface_observability"
        ]
    )
    assert result["scheduler_added_value"]["passed"] is True
    assert result["scheduler_added_value"]["append_only"] == "not_applicable"

    append_rows = [
        row for row in result["rows"] if row["condition"] == "append_only"
    ]
    for row in append_rows:
        scheduler_obs = row["observability_score"]["scheduler_reconstruction"]
        assert scheduler_obs["score"] is None
        assert scheduler_obs["not_applicable"] is True


def test_live_mode_requires_api_key_before_writing_outputs(tmp_path):
    module = _load_module()

    try:
        module.run_panel(
            output_root=tmp_path,
            overwrite=True,
            live_model_calls=True,
            api_key=None,
        )
    except ValueError as exc:
        assert "api_key" in str(exc)
    else:
        raise AssertionError("live mode accepted a missing api_key")

    assert not (tmp_path / "results.json").exists()
    assert not (tmp_path / "rows").exists()


def test_terminal_surfaces_preserve_required_scored_fields():
    module = _load_module()

    selection = module.selection_terminal_surface()
    artifact = module.artifact_terminal_surface()

    assert selection["tool_choice"] == "force"
    assert "requested_context" in selection["input_schema"]["required"]
    assert selection["state_update"]["copy"]["declared_losses"] == "declared_losses"
    assert artifact["tool_choice"] == "force"
    for field in (
        "artifact_title",
        "task_id",
        "conclusion",
        "recommended_action",
        "claims",
        "declared_losses",
        "cited_record_ids",
    ):
        assert field in artifact["input_schema"]["required"]
        assert artifact["state_update"]["copy"][field] == field


def test_direct_deepseek_defaults_terminal_tool_choice_to_auto():
    module = _load_module()

    assert module.default_terminal_tool_choice("https://api.deepseek.com") == "auto"
    assert (
        module.default_terminal_tool_choice("https://openrouter.ai/api/v1")
        == "force"
    )
    assert module.selection_terminal_surface(tool_choice="auto")["tool_choice"] == "auto"
    assert module.artifact_terminal_surface(tool_choice="auto")["tool_choice"] == "auto"


def test_dry_harness_writes_matched_rows_and_separate_summaries(tmp_path):
    module = _load_module()

    exit_code = module.main(
        ["--dry-run", "--overwrite", "--output-root", str(tmp_path)]
    )

    assert exit_code == 0
    results = module._read_json(tmp_path / "results.json")
    assert results["classification"] == "survived"
    assert results["summary"]["scheduler_viability_passed"] is True
    assert results["summary"]["artifact_noninferiority_passed"] is True
    assert results["summary"]["shared_surface_observability_noninferior"] is True
    assert results["summary"]["scheduler_added_value_passed"] is True
    assert len(results["rows"]) == len(module.TASKS) * len(module.CONDITIONS)

    for task_id in module.TASKS:
        event_root = tmp_path / "rows" / task_id / "event_loop_scheduled"
        append_root = tmp_path / "rows" / task_id / "append_only"
        assert (event_root / "cycle_01.json").exists()
        assert (event_root / "cycle_02.json").exists()
        assert (event_root / "scheduler_events.json").exists()
        assert (event_root / "restart_frontier.json").exists()
        assert (event_root / "row_result.json").exists()
        assert (append_root / "cycle_01.json").exists()
        assert not (append_root / "scheduler_events.json").exists()
        assert (append_root / "row_result.json").exists()


def test_overwrite_preserves_protocol_files(tmp_path):
    module = _load_module()
    (tmp_path / "PRE_REGISTRATION.md").write_text("locked protocol\n")
    (tmp_path / "run.py").write_text("runner\n")
    (tmp_path / "rows").mkdir()
    (tmp_path / "rows" / "stale.json").write_text("{}\n")

    module.run_panel(output_root=tmp_path, overwrite=True)

    assert (tmp_path / "PRE_REGISTRATION.md").read_text() == "locked protocol\n"
    assert (tmp_path / "run.py").read_text() == "runner\n"
    assert not (tmp_path / "rows" / "stale.json").exists()
