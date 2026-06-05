"""Audit continuity-measurement surfaces in the live normalized scheduler panel."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parent
SOURCE_RESULTS = (
    ROOT
    / "experiments/event_loop/live_normalized_scheduler_panel_20260605/results.json"
)
OUT_PATH = EXP_DIR / "measurement_audit.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def rel_path(value: str | None) -> Path | None:
    if not value:
        return None
    return ROOT / value


def status_sequence(events: list[dict[str, Any]]) -> list[str]:
    return [
        str(event.get("status"))
        for event in events
        if event.get("record_type") == "event_status" and event.get("status")
    ]


def completed_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("record_type") == "event_status"
        and event.get("status") == "completed"
    ]


def context_paths(completed: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    paths: list[list[dict[str, Any]]] = []
    for event in completed:
        for item in event.get("context_results") or []:
            result = item.get("result") if isinstance(item, dict) else None
            if isinstance(result, dict) and isinstance(result.get("path"), list):
                paths.append(result["path"])
    return paths


def event_requested_tools(events: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for event in events:
        if event.get("record_type") != "event_status":
            continue
        for item in event.get("requested_context") or []:
            if isinstance(item, dict) and item.get("tool"):
                tools.append(str(item["tool"]))
    return tools


def session_requested_tools(records: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for record in records:
        for item in record.get("tool_activity_full") or []:
            if isinstance(item, dict) and item.get("tool"):
                tools.append(str(item["tool"]))
        for item in record.get("_activity_log") or []:
            if isinstance(item, dict) and item.get("tool"):
                tools.append(str(item["tool"]))
    return tools


def state_growth(records: list[dict[str, Any]]) -> dict[str, Any]:
    estimates = [
        record.get("state_token_estimate")
        for record in records
        if isinstance(record.get("state_token_estimate"), int)
    ]
    key_counts = [
        record.get("n_top_level_keys")
        for record in records
        if isinstance(record.get("n_top_level_keys"), int)
    ]
    return {
        "state_token_estimates": estimates,
        "state_token_delta": (
            estimates[-1] - estimates[0] if len(estimates) >= 2 else None
        ),
        "top_level_key_counts": key_counts,
        "top_level_key_delta": (
            key_counts[-1] - key_counts[0] if len(key_counts) >= 2 else None
        ),
    }


def validation_surfaces(raw: dict[str, Any], completed: list[dict[str, Any]]) -> dict[str, Any]:
    wake_validations = [
        event.get("wake_validation")
        for event in completed
        if isinstance(event.get("wake_validation"), dict)
    ]
    first_pass_statuses = [
        validation.get("first_pass_status")
        for validation in wake_validations
        if validation.get("first_pass_status") is not None
    ]
    repair_statuses = [
        validation.get("repair_status")
        for validation in wake_validations
        if validation.get("repair_attempted")
    ]
    return {
        "wake_validation_present": bool(wake_validations),
        "wake_validation_statuses": [
            validation.get("status") for validation in wake_validations
        ],
        "first_pass_statuses": first_pass_statuses,
        "repair_statuses": repair_statuses,
        "raw_state_validation_status": raw.get("state_validation_status"),
        "raw_first_pass_validation_status": raw.get("first_pass_validation_status"),
        "raw_repair_status": raw.get("repair_status"),
    }


def continuity_fields(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "continuity_valid": raw.get("continuity_valid"),
        "continuity_failures": raw.get("continuity_failures"),
        "probe_id_preserved": raw.get("probe_id_preserved"),
        "baseline_preserved": raw.get("baseline_preserved"),
        "cycle_preserved": raw.get("cycle_preserved"),
        "evidence_valid": raw.get("evidence_valid"),
        "response_state_mismatch": raw.get("response_state_mismatch"),
    }


def has_delayed_task_goal(row: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    text_parts: list[str] = [str(row.get("condition", ""))]
    for event in events:
        text_parts.append(str(event.get("purpose", "")))
    text = "\n".join(text_parts).lower()
    delayed_markers = [
        "tomorrow",
        "later",
        "after",
        "long-horizon",
        "multi-step",
        "delayed task",
        "resume",
    ]
    return any(marker in text for marker in delayed_markers)


def audit_row(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw_result") if isinstance(row.get("raw_result"), dict) else {}
    envelope = (
        row.get("result_envelope")
        if isinstance(row.get("result_envelope"), dict)
        else {}
    )
    log_path = rel_path(raw.get("log_path"))
    event_path = rel_path(raw.get("event_log_path"))
    session_records = load_jsonl(log_path)
    event_records = load_jsonl(event_path)
    statuses = status_sequence(event_records)
    completed = completed_events(event_records)
    paths = context_paths(completed)
    requested_tools = event_requested_tools(event_records)
    all_tools = requested_tools + session_requested_tools(session_records)
    validation = validation_surfaces(raw, completed)
    growth = state_growth(session_records)

    surfaces = {
        "event_lifecycle": all(
            status in statuses for status in ["pending", "running", "completed"]
        ),
        "context_delivery": any(event.get("context_results") for event in completed),
        "context_grounding": any(paths),
        "state_transition": any(
            isinstance(event.get("outcome_observation"), dict) for event in completed
        ),
        "wake_validation": validation["wake_validation_present"],
        "first_pass_validation": bool(validation["first_pass_statuses"]),
        "repair_validation": bool(validation["repair_statuses"]),
        "continuity_fields": all(
            key in raw
            for key in [
                "continuity_valid",
                "probe_id_preserved",
                "baseline_preserved",
                "cycle_preserved",
            ]
        ),
        "state_growth": bool(growth["state_token_estimates"])
        and bool(growth["top_level_key_counts"]),
        "task_goal": has_delayed_task_goal(row, event_records),
        "delayed_recall": any(tool in {"recall", "memory_schema", "compare"} for tool in all_tools),
    }
    missing = sorted(key for key, present in surfaces.items() if not present)
    return {
        "condition": row.get("condition"),
        "replicate": row.get("replicate"),
        "initialization_class": envelope.get("initialization", {}).get("class"),
        "scheduler_score_eligible": envelope.get("initialization", {}).get(
            "scheduler_score_eligible"
        ),
        "log_path": raw.get("log_path"),
        "event_log_path": raw.get("event_log_path"),
        "session_record_count": len(session_records),
        "event_record_count": len(event_records),
        "event_status_sequence": statuses,
        "context_path_counts": [len(path) for path in paths],
        "context_edge_types": sorted(
            {
                str(step.get("edge_type"))
                for path in paths
                for step in path
                if step.get("edge_type")
            }
        ),
        "requested_context_tools": requested_tools,
        "all_observed_tools": sorted(set(all_tools)),
        "surfaces": surfaces,
        "missing_surfaces": missing,
        "validation": validation,
        "continuity": continuity_fields(raw),
        "state_growth": growth,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if row.get("scheduler_score_eligible")]
    by_condition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_condition[str(row.get("condition"))].append(row)

    surface_names = sorted(rows[0]["surfaces"]) if rows else []

    def coverage(group: list[dict[str, Any]]) -> dict[str, int]:
        return {
            surface: sum(bool(row["surfaces"].get(surface)) for row in group)
            for surface in surface_names
        }

    condition_coverage = {
        condition: {
            "n": len(group),
            "coverage": coverage(group),
            "missing": dict(
                sorted(Counter(surface for row in group for surface in row["missing_surfaces"]).items())
            ),
        }
        for condition, group in sorted(by_condition.items())
    }
    eligible_coverage = coverage(eligible)
    return {
        "n": len(rows),
        "eligible_n": len(eligible),
        "surface_coverage_all": coverage(rows),
        "surface_coverage_eligible": eligible_coverage,
        "condition_coverage": condition_coverage,
        "continuity_valid_eligible": sum(
            row["continuity"].get("continuity_valid") is True for row in eligible
        ),
        "evidence_valid_eligible": sum(
            row["continuity"].get("evidence_valid") is True for row in eligible
        ),
        "repair_dependent_eligible": sum(
            bool(row["validation"]["repair_statuses"]) for row in eligible
        ),
        "context_grounded_eligible": sum(
            bool(row["surfaces"]["context_grounding"]) for row in eligible
        ),
        "hypothesis_results": {
            "H261_full_event_lifecycle": all(
                row["surfaces"]["event_lifecycle"] for row in eligible
            ) if eligible else False,
            "H262_context_separate_from_state": all(
                row["surfaces"]["context_delivery"]
                and row["surfaces"]["context_grounding"]
                for row in eligible
            ) if eligible else False,
            "H263_first_pass_and_repair_validation": all(
                row["surfaces"]["first_pass_validation"]
                and row["surfaces"]["repair_validation"]
                for row in eligible
            ) if eligible else False,
            "H264_local_continuity_measurable": all(
                row["surfaces"]["continuity_fields"]
                and row["surfaces"]["state_transition"]
                and row["surfaces"]["state_growth"]
                for row in eligible
            ) if eligible else False,
            "H265_long_horizon_benefit_not_yet_measurable": not any(
                row["surfaces"]["task_goal"] and row["surfaces"]["delayed_recall"]
                for row in eligible
            ),
        },
    }


def main() -> None:
    payload = load_json(SOURCE_RESULTS)
    source_rows = payload.get("results")
    if not isinstance(source_rows, list):
        raise SystemExit("source results missing results list")
    rows = [audit_row(row) for row in source_rows if isinstance(row, dict)]
    result = {
        "experiment": "continuity_substrate_measurement_audit_20260605",
        "source_results": str(SOURCE_RESULTS.relative_to(ROOT)),
        "rows": rows,
        "summary": aggregate(rows),
    }
    OUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
