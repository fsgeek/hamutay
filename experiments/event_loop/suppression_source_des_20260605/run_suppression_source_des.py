"""Run the suppression-source simulated-time diagnostic."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, default_event_log_path, summarize_event_log

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.event_loop.bounded_autonomy_des_20260605 import (  # noqa: E402
    run_bounded_autonomy_des as bounded,
)

EXP_DIR = Path(__file__).resolve().parent

SCENARIOS = {
    "stasis_cutoff": {
        "classification": "stasis",
        "reason": "stasis cutoff",
    },
    "recursive_drift": {
        "classification": "drift",
        "reason": "recursive scheduling drift",
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def wake_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if "self_scheduled_reflection" in str(record.get("user_message", ""))
    ]


def run_bounded_in_scratch(scenario: str) -> tuple[Path, Path]:
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


def run_scenario(scenario: str, config: dict[str, str]) -> dict[str, Any]:
    log_path, event_path = run_bounded_in_scratch(scenario)
    records = load_jsonl(log_path)
    last_wake = wake_records(records)[-1]
    source_record_id = str(last_wake["record_id"])
    source_cycle = int(last_wake["cycle"])
    store = EventStore(event_path)
    before = summarize_event_log(store.read_records())
    pending_before = latest_pending_ids(before)
    store.suppress_pending(
        policy="bounded_autonomy",
        reason=config["reason"],
        suppressed_by_record_id=source_record_id,
        suppressed_by_cycle=source_cycle,
        suppressed_by_classification=config["classification"],
    )
    after = summarize_event_log(store.read_records())
    suppressed = [
        event for event in after.get("events", [])
        if event.get("status") == "suppressed"
    ]
    source_ids = {str(record.get("record_id")) for record in records}
    return {
        "scenario": scenario,
        "classification": config["classification"],
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "pending_before_suppression": len(pending_before),
        "pending_after_suppression": len(latest_pending_ids(after)),
        "suppressed_count": len(suppressed),
        "suppressed_with_source_count": sum(
            bool(
                event.get("suppressed_by_cycle") == source_cycle
                and event.get("suppressed_by_record_id") == source_record_id
                and event.get("suppressed_by_classification")
                == config["classification"]
            )
            for event in suppressed
        ),
        "source_records_resolved": all(
            str(event.get("suppressed_by_record_id")) in source_ids
            for event in suppressed
        ),
        "suppressed_by_classifications": sorted(
            set(
                str(event.get("suppressed_by_classification"))
                for event in suppressed
            )
        ),
        "lifecycle_anomaly_count": len(after.get("lifecycle_anomalies", [])),
        "status_counts": after.get("status_counts", {}),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "hypothesis_results": {
            "H85_suppressed_events_carry_policy_source": all(
                result["suppressed_count"] > 0
                and result["suppressed_with_source_count"]
                == result["suppressed_count"]
                for result in results
            ),
            "H86_suppression_source_record_resolvable": all(
                result["source_records_resolved"] for result in results
            ),
            "H87_source_linked_suppression_lifecycle_clean": all(
                result["pending_after_suppression"] == 0
                and result["lifecycle_anomaly_count"] == 0
                for result in results
            ),
        },
        "summary": {
            "scenario_count": len(results),
            "suppressed_total": sum(
                int(result["suppressed_count"]) for result in results
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
