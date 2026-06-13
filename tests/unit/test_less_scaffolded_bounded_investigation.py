import importlib.util
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "less_scaffolded_bounded_investigation_20260612"
    / "run.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("goal6_less_scaffolded", RUN_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_goal_provenance_requires_model_shaping():
    module = _load_module()

    assert (
        module.classify_goal_provenance(
            {
                "response": (
                    "I selected an investigation into restart frontier and "
                    "action/artifact consistency across a continuation wake."
                )
            }
        )
        == "model_originated"
    )
    assert (
        module.classify_goal_provenance(
            {
                "response": (
                    "Goal 6 less-scaffolded bounded investigation wake"
                )
            }
        )
        == "harness_authored"
    )


def test_action_artifact_consistency_scores_policy_against_artifact():
    module = _load_module()

    assert (
        module.classify_action_artifact(
            {
                "response": "The artifact is complete and supported.",
                "policy_action": "stop_complete",
            },
            {"accepted_actions": [{"action_type": "policy_action"}]},
        )
        == "consistent_complete"
    )
    assert (
        module.classify_action_artifact(
            {
                "response": "The evidence is missing and I cannot complete it.",
                "policy_action": "stop_complete",
            },
            {"accepted_actions": [{"action_type": "policy_action"}]},
        )
        == "mismatch_action_overclaims"
    )
    assert (
        module.classify_action_artifact(
            {
                "response": "I need another wake.",
                "open_items": [{"kind": "todo", "text": "finish"}],
                "policy_action": "continue_after",
            },
            {"accepted_actions": [{"action_type": "policy_action"}]},
        )
        == "mismatch_continuation"
    )


def test_dry_run_preserves_reconstructable_goal6_artifacts(tmp_path):
    module = _load_module()
    results = module.main(
        [
            "--dry-run",
            "--overwrite",
            "--output-root",
            str(tmp_path),
        ]
    )

    assert results == 0
    result_payload = module._read_json(tmp_path / "results.json")
    assert result_payload["classification"] == "survived"
    assert result_payload["summary"]["positive_scoreable_rows"] >= 2
    for row_id in module.DEFAULT_ROW_IDS:
        row = module._read_json(tmp_path / "rows" / row_id / "row_result.json")
        assert row["reconstructable"] is True
        assert (tmp_path / "rows" / row_id / "run" / "actions.jsonl").exists()
        assert (tmp_path / "rows" / row_id / "run" / "events.jsonl").exists()
        assert (tmp_path / "rows" / row_id / "run" / "restart_frontier.jsonl").exists()
