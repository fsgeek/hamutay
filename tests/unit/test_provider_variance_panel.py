from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "provider_variance_panel_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("provider_variance_panel", RUN_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_row(path: Path, *, endpoint: str, model: str, classification: str = "passed"):
    path.mkdir(parents=True)
    (path / "results.json").write_text(
        json.dumps(
            {
                "experiment_id": "restart_resume_interruption_20260618",
                "classification": classification,
                "endpoint": endpoint,
                "model": model,
                "terminal_tool_choice": "auto",
                "success": {
                    "completed_event_types": [
                        "inbound_message",
                        "self_scheduled_reflection",
                        "housekeeping",
                    ],
                    "interrupted_event_history": [
                        "pending",
                        "running",
                        "pending",
                        "running",
                        "completed",
                    ],
                    "checks": {"completed_expected_events": True},
                },
                "failure_attribution": [],
            },
            sort_keys=True,
        )
    )


def test_collect_panel_passes_with_two_provider_rows(tmp_path):
    module = load_module()
    anchor = tmp_path / "anchor"
    alternate = tmp_path / "alternate"
    write_row(anchor, endpoint="https://api.deepseek.com", model="deepseek-v4-pro")
    write_row(
        alternate,
        endpoint="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-v4-pro",
    )

    result = module.collect_panel(
        output_root=tmp_path / "panel",
        anchor_dir=anchor,
        openrouter_dir=alternate,
    )

    assert result["classification"] == "passed"
    assert result["panel_conclusion"] == "no_provider_variance_detected_on_panel"
    assert result["checks"]["at_least_two_provider_rows"] is True
    assert result["checks"]["no_framework_failures"] is True
    assert [row["row_id"] for row in result["rows"]] == [
        "direct_deepseek_anchor",
        "openrouter_deepseek",
    ]


def test_preregistration_artifacts_capture_provider_rows(tmp_path):
    module = load_module()

    module.write_preregistration_artifacts(tmp_path, live_model_calls=True)

    matrix = json.loads((tmp_path / "matrix.json").read_text())
    budget = json.loads((tmp_path / "budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())
    assert matrix["protocol"] == "restart_resume_interruption_20260618"
    assert [row["row_id"] for row in matrix["rows"]] == [
        "direct_deepseek_anchor",
        "openrouter_deepseek",
    ]
    assert budget["anchor_row_reuses_committed_result"] is True
    assert budget["max_new_live_calls"] == 4
    assert "provider" in taxonomy["layers"]
    assert "terminal_surface" in taxonomy["layers"]
