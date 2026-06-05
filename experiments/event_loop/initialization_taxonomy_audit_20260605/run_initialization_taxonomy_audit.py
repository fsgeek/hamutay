"""Retrospective initialization provenance audit for event-loop experiments."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EVENT_LOOP_DIR = ROOT / "experiments" / "event_loop"
OUT_DIR = Path(__file__).resolve().parent
OUT_PATH = OUT_DIR / "taxonomy.json"

INIT_KEYS = {
    "init_valid",
    "init_failure_reasons",
    "init_validation_status",
    "init_first_pass_status",
    "init_repair_attempted",
    "init_repaired",
    "init_repair_status",
    "init_repair_valid",
    "init_has_repair_validation",
    "init_has_repair_raw_output",
}

SCHEDULER_KEYS = {
    "schedule_valid",
    "scheduled_event_count",
    "direct_scheduled_event_count",
    "valid_schedule_attempts",
    "event_completed",
    "event_persisted",
    "event_result_status",
    "event_count_in_cycle_log",
    "wake_status_woke",
    "expected_wake_cycle",
    "walk_context_event_count",
}

REPAIR_KEYS = {
    "repaired",
    "repair_attempted",
    "repair_status",
    "state_validation_status",
    "first_pass_validation_status",
    "has_repair_validation",
    "has_repair_raw_output",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def row_list(data: Any) -> tuple[list[Any] | None, str]:
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            return results, "dict.results"
        return None, f"dict.{type(results).__name__}"
    if isinstance(data, list):
        return data, "list"
    return None, type(data).__name__


def present_fields(row: dict[str, Any], candidates: set[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in sorted(candidates) if key in row}


def log_exists(row: dict[str, Any], key: str) -> bool | None:
    value = row.get(key)
    if not isinstance(value, str):
        return None
    return (ROOT / value).exists()


def has_scheduler_surface(row: dict[str, Any]) -> bool:
    return any(key in row for key in SCHEDULER_KEYS)


def classify(row: dict[str, Any]) -> tuple[str, bool, list[str]]:
    evidence: list[str] = []
    scheduler_relevant = has_scheduler_surface(row)

    if row.get("init_repair_valid") is True:
        evidence.append("init_repair_valid=True")
        return "repaired_valid", True, evidence

    if row.get("init_validation_status") == "repaired":
        evidence.append("init_validation_status=repaired")
        return "repaired_valid", True, evidence

    if row.get("init_repaired") is True and row.get("init_repair_status") == "valid":
        evidence.extend(["init_repaired=True", "init_repair_status=valid"])
        return "repaired_valid", True, evidence

    if row.get("init_validation_status") == "valid":
        evidence.append("init_validation_status=valid")
        return "first_pass_valid", True, evidence

    if row.get("init_first_pass_status") == "valid":
        evidence.append("init_first_pass_status=valid")
        return "first_pass_valid", True, evidence

    if row.get("init_valid") is False:
        evidence.append("init_valid=False")
        if row.get("init_failure_reasons"):
            evidence.append("init_failure_reasons")
        return "failed_or_culled", scheduler_relevant, evidence

    if row.get("init_valid") is True:
        evidence.append("init_valid=True")
        return "valid_legacy", scheduler_relevant, evidence

    if scheduler_relevant:
        evidence.append("scheduler_surface_without_init_evidence")
        return "unclassifiable", True, evidence

    return "not_scheduler_scored", False, evidence


def safe_event_completed(row: dict[str, Any]) -> bool:
    return row.get("event_completed") is True or row.get("event_result_status") == "completed"


def audit() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    file_records: list[dict[str, Any]] = []

    for path in sorted(EVENT_LOOP_DIR.glob("*/results.json")):
        rel_path = path.relative_to(ROOT).as_posix()
        experiment = path.parent.name
        try:
            data = load_json(path)
        except Exception as exc:  # pragma: no cover - defensive audit path
            file_records.append(
                {
                    "experiment": experiment,
                    "results_path": rel_path,
                    "root_shape": "unreadable",
                    "class": "malformed_or_aggregate",
                    "error": str(exc),
                }
            )
            continue

        rows, root_shape = row_list(data)
        if rows is None:
            file_records.append(
                {
                    "experiment": experiment,
                    "results_path": rel_path,
                    "root_shape": root_shape,
                    "class": "malformed_or_aggregate",
                    "error": "missing row-level results list",
                }
            )
            continue

        file_records.append(
            {
                "experiment": experiment,
                "results_path": rel_path,
                "root_shape": root_shape,
                "row_count": len(rows),
            }
        )

        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                records.append(
                    {
                        "experiment": experiment,
                        "result_index": index,
                        "results_path": rel_path,
                        "root_shape": root_shape,
                        "class": "malformed_or_aggregate",
                        "scheduler_relevant": False,
                        "evidence": ["non_dict_row"],
                    }
                )
                continue

            row_class, scheduler_relevant, evidence = classify(row)
            records.append(
                {
                    "experiment": experiment,
                    "result_index": index,
                    "model": row.get("model"),
                    "replicate": row.get("replicate"),
                    "results_path": rel_path,
                    "root_shape": root_shape,
                    "class": row_class,
                    "scheduler_relevant": scheduler_relevant,
                    "evidence": evidence,
                    "init_fields": present_fields(row, INIT_KEYS),
                    "repair_fields": present_fields(row, REPAIR_KEYS),
                    "scheduler_fields": present_fields(row, SCHEDULER_KEYS),
                    "log_path": row.get("log_path"),
                    "log_exists": log_exists(row, "log_path"),
                    "event_log_path": row.get("event_log_path"),
                    "event_log_exists": log_exists(row, "event_log_path"),
                    "event_completed": safe_event_completed(row),
                    "error": row.get("error"),
                }
            )

    class_counts = Counter(record["class"] for record in records)
    scheduler_class_counts = Counter(
        record["class"] for record in records if record.get("scheduler_relevant")
    )

    experiments: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["experiment"]].append(record)

    for experiment, experiment_records in sorted(grouped.items()):
        class_counter = Counter(record["class"] for record in experiment_records)
        scheduler_records = [
            record for record in experiment_records if record.get("scheduler_relevant")
        ]
        qualified_records = [
            record
            for record in scheduler_records
            if record["class"] in {"first_pass_valid", "valid_legacy", "repaired_valid"}
        ]
        failed_or_unclassified = [
            record
            for record in scheduler_records
            if record["class"] in {"failed_or_culled", "unclassifiable"}
        ]
        all_completed = sum(1 for record in scheduler_records if record["event_completed"])
        qualified_completed = sum(
            1 for record in qualified_records if record["event_completed"]
        )
        experiments[experiment] = {
            "row_count": len(experiment_records),
            "class_counts": dict(sorted(class_counter.items())),
            "scheduler_relevant_count": len(scheduler_records),
            "qualified_initialization_count": len(qualified_records),
            "failed_or_unclassified_initialization_count": len(failed_or_unclassified),
            "all_attempt_event_completed_count": all_completed,
            "qualified_event_completed_count": qualified_completed,
            "all_attempt_event_completion_rate": (
                all_completed / len(scheduler_records) if scheduler_records else None
            ),
            "qualified_event_completion_rate": (
                qualified_completed / len(qualified_records)
                if qualified_records
                else None
            ),
            "censoring_changes_denominator": bool(
                scheduler_records and len(scheduler_records) != len(qualified_records)
            ),
        }

    aggregate_files = [
        record for record in file_records if record.get("class") == "malformed_or_aggregate"
    ]
    censoring_panels = {
        experiment: summary
        for experiment, summary in experiments.items()
        if summary["censoring_changes_denominator"]
    }

    return {
        "experiment": "initialization_taxonomy_audit_20260605",
        "generated_from": "experiments/event_loop/*/results.json",
        "record_count": len(records),
        "file_count": len(file_records),
        "class_counts": dict(sorted(class_counts.items())),
        "scheduler_class_counts": dict(sorted(scheduler_class_counts.items())),
        "scheduler_relevant_count": sum(
            1 for record in records if record.get("scheduler_relevant")
        ),
        "classified_scheduler_relevant_count": sum(
            1
            for record in records
            if record.get("scheduler_relevant")
            and record["class"] not in {"unclassifiable", "malformed_or_aggregate"}
        ),
        "initialization_classes_observed": sorted(
            {
                record["class"]
                for record in records
                if record["class"]
                not in {"not_scheduler_scored", "malformed_or_aggregate"}
            }
        ),
        "aggregate_or_malformed_files": aggregate_files,
        "censoring_panels": censoring_panels,
        "experiments": experiments,
        "records": records,
    }


def main() -> None:
    result = audit()
    with OUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(result["class_counts"], indent=2, sort_keys=True))
    print(json.dumps(result["scheduler_class_counts"], indent=2, sort_keys=True))
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
