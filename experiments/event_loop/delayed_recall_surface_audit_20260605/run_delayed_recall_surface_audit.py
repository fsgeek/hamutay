"""Audit delayed-thinking panels for delayed task and recall surfaces."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parent
OUT_PATH = EXP_DIR / "delayed_recall_surface_audit.json"

PANELS = [
    "delayed_thinking_simtime_20260605",
    "delayed_thinking_controlled_seed_20260605",
    "delayed_thinking_contract_variant_20260605",
    "delayed_thinking_envelope_variant_20260605",
    "delayed_thinking_example_variant_20260605",
]


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


def root_path(value: str | None) -> Path | None:
    return ROOT / value if value else None


def event_statuses(events: list[dict[str, Any]]) -> list[str]:
    return [
        str(event.get("status"))
        for event in events
        if event.get("record_type") == "event_status" and event.get("status")
    ]


def requested_context_tools(events: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for event in events:
        if event.get("record_type") != "event_status":
            continue
        for item in event.get("requested_context") or []:
            if isinstance(item, dict) and item.get("tool"):
                tools.append(str(item["tool"]))
    return tools


def completed_context_tools(events: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for event in events:
        if event.get("record_type") != "event_status" or event.get("status") != "completed":
            continue
        for item in event.get("context_results") or []:
            request = item.get("request") if isinstance(item, dict) else None
            if isinstance(request, dict) and request.get("tool"):
                tools.append(str(request["tool"]))
    return tools


def has_delayed_task_goal(row: dict[str, Any], events: list[dict[str, Any]]) -> bool:
    final_state = row.get("final_state")
    final_state = final_state if isinstance(final_state, dict) else {}
    text_parts = [
        str(row.get("expected_probe_id", "")),
        str(final_state.get("thinking_status", "")),
        str(final_state.get("delayed_thought", "")),
        str(final_state.get("wake_observation", "")),
    ]
    for event in events:
        text_parts.append(str(event.get("purpose", "")))
    text = "\n".join(text_parts).lower()
    markers = [
        "delayed",
        "future",
        "recall",
        "thinking",
        "wake",
        "not_before",
    ]
    return any(marker in text for marker in markers)


def audit_row(panel: str, index: int, row: dict[str, Any]) -> dict[str, Any]:
    event_path = root_path(row.get("event_log_path"))
    events = load_jsonl(event_path)
    statuses = event_statuses(events)
    requested_tools = requested_context_tools(events)
    completed_tools = completed_context_tools(events)
    final_state = row.get("final_state")
    final_state = final_state if isinstance(final_state, dict) else {}
    pre_due_step = row.get("pre_due_step")
    pre_due_step = pre_due_step if isinstance(pre_due_step, dict) else {}
    pre_due_summary = pre_due_step.get("summary")
    pre_due_summary = pre_due_summary if isinstance(pre_due_summary, dict) else {}
    surfaces = {
        "activation_valid": row.get("init_valid") is True,
        "schedule_valid": row.get("schedule_valid") is True,
        "pre_due_waiting": (
            pre_due_step.get("stop_reason") == "waiting"
            or int(pre_due_step.get("pending_waiting_count") or 0) > 0
            or int(pre_due_summary.get("pending_waiting_count") or 0) > 0
        ),
        "event_completed": row.get("event_completed") is True,
        "event_lifecycle": all(
            status in statuses for status in ["pending", "running", "completed"]
        ),
        "delayed_task_goal": has_delayed_task_goal(row, events),
        "recall_requested": "recall" in requested_tools,
        "recall_delivered": "recall" in completed_tools
        or row.get("event_has_recall_context") is True,
        "first_pass_valid": row.get("first_pass_validation_status") == "valid",
        "repair_attempted": row.get("repair_attempted") is True,
        "repair_valid": row.get("repair_status") == "valid",
        "final_state_valid": row.get("final_state_valid") is True,
        "protected_merge_observed": int(row.get("protected_merge_diagnostic_count") or 0) > 0,
        "identity_only_control": False,
    }
    return {
        "panel": panel,
        "result_index": index,
        "replicate": row.get("replicate"),
        "log_path": row.get("log_path"),
        "event_log_path": row.get("event_log_path"),
        "event_status_sequence": statuses,
        "requested_context_tools": requested_tools,
        "completed_context_tools": completed_tools,
        "surfaces": surfaces,
        "state_failures": row.get("state_failures"),
        "thinking_status": final_state.get("thinking_status"),
        "has_delayed_thought": bool(final_state.get("delayed_thought")),
        "wake_observation_kind": (
            final_state.get("wake_observation", {}).get("kind")
            if isinstance(final_state.get("wake_observation"), dict)
            else None
        ),
    }


def panel_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    surface_names = sorted(rows[0]["surfaces"]) if rows else []
    coverage = {
        surface: sum(bool(row["surfaces"].get(surface)) for row in rows)
        for surface in surface_names
    }
    return {
        "n": len(rows),
        "coverage": coverage,
        "first_pass_valid_count": coverage.get("first_pass_valid", 0),
        "repair_valid_count": coverage.get("repair_valid", 0),
        "final_state_valid_count": coverage.get("final_state_valid", 0),
        "recall_delivered_count": coverage.get("recall_delivered", 0),
        "status_sequences": dict(
            sorted(
                Counter(
                    ",".join(row["event_status_sequence"]) or "none"
                    for row in rows
                ).items()
            )
        ),
    }


def aggregate(panel_summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    successful_panels = {
        name: summary
        for name, summary in panel_summaries.items()
        if summary["coverage"].get("activation_valid", 0) == summary["n"]
        and summary["coverage"].get("schedule_valid", 0) == summary["n"]
        and summary["coverage"].get("event_completed", 0) == summary["n"]
    }
    any_delayed_goal = any(
        summary["coverage"].get("delayed_task_goal", 0) > 0
        for summary in panel_summaries.values()
    )
    any_scheduled = any(
        summary["coverage"].get("schedule_valid", 0) > 0
        for summary in panel_summaries.values()
    )
    successful_have_waiting = all(
        summary["coverage"].get("pre_due_waiting", 0) == summary["n"]
        for summary in successful_panels.values()
    ) if successful_panels else False
    successful_have_due = all(
        summary["coverage"].get("event_completed", 0) == summary["n"]
        for summary in successful_panels.values()
    ) if successful_panels else False
    successful_have_recall = all(
        summary["coverage"].get("recall_delivered", 0) == summary["n"]
        for summary in successful_panels.values()
    ) if successful_panels else False
    successful_repair_dependent = all(
        summary["coverage"].get("repair_valid", 0) >= summary["n"] / 2
        and summary["coverage"].get("first_pass_valid", 0) < summary["n"]
        for summary in successful_panels.values()
    ) if successful_panels else False
    has_identity_control = any(
        summary["coverage"].get("identity_only_control", 0) > 0
        for summary in panel_summaries.values()
    )
    return {
        "panel_count": len(panel_summaries),
        "successful_panel_count": len(successful_panels),
        "successful_panels": sorted(successful_panels),
        "hypothesis_results": {
            "H266_delayed_goals_and_future_events_preserved": (
                any_delayed_goal and any_scheduled
            ),
            "H267_waiting_and_due_wake_preserved": (
                successful_have_waiting and successful_have_due
            ),
            "H268_delayed_recall_context_delivered": successful_have_recall,
            "H269_successful_panels_repair_dependent": successful_repair_dependent,
            "H270_no_matched_identity_only_control": not has_identity_control,
        },
        "identity_only_control_present": has_identity_control,
    }


def main() -> None:
    rows: list[dict[str, Any]] = []
    panel_summaries: dict[str, dict[str, Any]] = {}
    for panel in PANELS:
        path = ROOT / "experiments/event_loop" / panel / "results.json"
        payload = load_json(path)
        raw_rows = payload.get("results")
        if not isinstance(raw_rows, list):
            raise SystemExit(f"{path} missing results list")
        panel_rows = [
            audit_row(panel, index, row)
            for index, row in enumerate(raw_rows, start=1)
            if isinstance(row, dict)
        ]
        rows.extend(panel_rows)
        panel_summaries[panel] = panel_summary(panel_rows)
    result = {
        "experiment": "delayed_recall_surface_audit_20260605",
        "panels": PANELS,
        "rows": rows,
        "panel_summaries": panel_summaries,
        "summary": aggregate(panel_summaries),
    }
    OUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
