"""Run the pending disposition simulated-time scheduler experiment."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, default_event_log_path, summarize_event_log

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.event_loop.bounded_autonomy_des_20260605 import (
    run_bounded_autonomy_des as bounded,
)

EXP_DIR = Path(__file__).resolve().parent

SCENARIOS = {
    "stasis_cutoff": {
        "expected_classification": "stasis",
        "expected_suppressed": 1,
        "reason": "stasis cutoff",
    },
    "recursive_drift": {
        "expected_classification": "drift",
        "expected_suppressed": 2,
        "reason": "recursive scheduling drift",
    },
}


def copy_bounded_artifacts(scenario: str) -> tuple[Path, Path]:
    scratch_dir = EXP_DIR / "_bounded_scratch"
    scratch_dir.mkdir(exist_ok=True)
    original_exp_dir = bounded.EXP_DIR
    bounded.EXP_DIR = scratch_dir
    try:
        bounded.run_scenario(scenario)
    finally:
        bounded.EXP_DIR = original_exp_dir
    source_log = scratch_dir / f"{scenario}.jsonl"
    source_events = default_event_log_path(source_log)
    log_path = EXP_DIR / f"{scenario}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    shutil.move(source_log, log_path)
    shutil.move(source_events, event_path)
    for lock in scratch_dir.glob("*.lock"):
        lock.unlink()
    if not any(scratch_dir.iterdir()):
        scratch_dir.rmdir()
    return log_path, event_path


def latest_pending_ids(summary: dict[str, Any]) -> set[str]:
    return {
        str(event["event_id"])
        for event in summary.get("events", [])
        if event.get("status") == "pending"
    }


def run_scenario(scenario: str, config: dict[str, Any]) -> dict[str, Any]:
    log_path, event_path = copy_bounded_artifacts(scenario)
    store = EventStore(event_path)
    before = summarize_event_log(store.read_records())
    pending_before = latest_pending_ids(before)
    suppressed = store.suppress_pending(
        policy="bounded_autonomy",
        reason=config["reason"],
    )
    after = summarize_event_log(store.read_records())
    pending_after = latest_pending_ids(after)
    suppressed_events = [
        event for event in after.get("events", [])
        if event.get("status") == "suppressed"
    ]
    return {
        "scenario": scenario,
        "classification": config["expected_classification"],
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "pending_before_suppression": len(pending_before),
        "suppressed_count": len(suppressed),
        "pending_after_suppression": len(pending_after),
        "status_counts": after.get("status_counts", {}),
        "suppression_reasons": sorted(
            set(
                str(event.get("suppression_reason"))
                for event in suppressed_events
            )
        ),
        "suppressed_events_have_policy_fields": all(
            event.get("suppressed_at")
            and event.get("suppressed_by_policy") == "bounded_autonomy"
            and event.get("suppression_reason") == config["reason"]
            for event in suppressed_events
        ),
        "lifecycle_anomaly_count": len(after.get("lifecycle_anomalies", [])),
        "expected_suppressed": config["expected_suppressed"],
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario = {result["scenario"]: result for result in results}
    stasis = by_scenario["stasis_cutoff"]
    drift = by_scenario["recursive_drift"]
    return {
        "hypothesis_results": {
            "H81_policy_suppression_distinct_terminal_status": all(
                "suppressed" in result["status_counts"]
                and result["pending_after_suppression"] == 0
                for result in results
            ),
            "H82_stasis_suppression_drains_pending": (
                stasis["suppressed_count"] == stasis["expected_suppressed"]
                and stasis["pending_after_suppression"] == 0
                and stasis["suppressed_events_have_policy_fields"]
            ),
            "H83_drift_suppression_drains_branches": (
                drift["suppressed_count"] == drift["expected_suppressed"]
                and drift["pending_after_suppression"] == 0
                and drift["suppressed_events_have_policy_fields"]
            ),
            "H84_suppression_lifecycle_clean": all(
                result["lifecycle_anomaly_count"] == 0 for result in results
            ),
        },
        "summary": {
            "scenario_count": len(results),
            "suppressed_total": sum(
                int(result["suppressed_count"]) for result in results
            ),
            "pending_after_total": sum(
                int(result["pending_after_suppression"]) for result in results
            ),
        },
    }


def main() -> None:
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")
    results = [
        run_scenario(scenario, config)
        for scenario, config in SCENARIOS.items()
    ]
    payload = {"results": results, **aggregate(results)}
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
