from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


RUN_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "event_loop"
    / "symbolic_continuation_stability_20260618"
    / "run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "symbolic_continuation_stability_panel",
        RUN_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_dry_stability_panel_requires_replication_and_adversarial_drift(tmp_path):
    module = load_module()

    results = module.run_panel(
        output_root=tmp_path,
        overwrite=True,
        replications=2,
    )

    assert results["classification"] == "passed"
    assert results["summary"]["checks"] == {
        "adversarial_count": True,
        "adversarial_drift_was_ignored": True,
        "all_rows_have_attribution_surface": True,
        "all_rows_passed": True,
        "all_rows_use_symbolic_binding": True,
        "repeated_live_wakes": True,
        "replication_count": True,
    }
    assert results["summary"]["total_completed_events"] == 9
    assert [row["mode"] for row in results["rows"]] == [
        "replication",
        "replication",
        "adversarial_drift",
    ]

    adversarial = results["rows"][-1]
    assert adversarial["ignored_model_authored_fields"] == [
        "requested_context",
        "terminal_surface",
    ]
    assert adversarial["continuation_terminal_surfaces"] == [
        "complete_bound_continuation"
    ]

    continuation_pending = next(
        record for record in read_jsonl(
            tmp_path / "runs" / "adversarial_drift_01" / "events.jsonl"
        )
        if record.get("event_type") == "self_scheduled_reflection"
        and record.get("status") == "pending"
    )
    assert continuation_pending["ignored_model_authored_fields"] == [
        "requested_context",
        "terminal_surface",
    ]
    assert continuation_pending["terminal_surface"]["tool_name"] == (
        "complete_bound_continuation"
    )


def test_panel_fails_without_adversarial_ignored_fields():
    module = load_module()

    summary = module.classify_panel(
        [
            {
                "classification": "passed",
                "mode": "replication",
                "completed_event_count": 3,
                "binding_contracts": [
                    "framework_bound_symbolic_continuation.v1"
                ],
                "failure_attribution": [],
            },
            {
                "classification": "passed",
                "mode": "adversarial_drift",
                "completed_event_count": 3,
                "binding_contracts": [
                    "framework_bound_symbolic_continuation.v1"
                ],
                "ignored_model_authored_fields": [],
                "failure_attribution": [],
            },
        ],
        expected_replications=1,
    )

    assert summary["passed"] is False
    assert summary["checks"]["adversarial_drift_was_ignored"] is False
