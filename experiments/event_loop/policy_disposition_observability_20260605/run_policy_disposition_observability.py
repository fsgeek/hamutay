"""Deterministic smoke for policy disposition event-log observability."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from hamutay.events import (
    EventStore,
    build_pending_event,
    format_event_report,
    summarize_event_log,
)


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
EVENT_LOG_PATH = EXP_DIR / "policy_disposition_observability.events.jsonl"
RESULTS_PATH = EXP_DIR / "results.json"
REPORT_PATH = EXP_DIR / "event_report.txt"
CONDITIONS = ("continue_after", "stop_complete", "ask_external_evidence")


def _uuid(index: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{index:012d}")


def _event(action: str, index: int) -> dict:
    return build_pending_event(
        purpose=f"Deterministic policy disposition smoke: {action}.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=_uuid(1),
        label=f"policy-disposition-{action}",
    )


def append_condition(store: EventStore, action: str, index: int) -> dict:
    event = _event(action, index)
    run_id = str(_uuid(100 + index))
    result_record_id = _uuid(200 + index)
    store.append(event)
    store.append_running(event, run_id=UUID(run_id))
    continuation = None
    if action == "continue_after":
        continuation = build_pending_event(
            purpose="Follow the continuation requested by the policy.",
            requested_context=[
                {"tool": "recall", "cycle": 1},
                {
                    "tool": "recall",
                    "record_id": str(result_record_id),
                    "field": "policy_result",
                },
            ],
            scheduled_by_cycle=2,
            scheduled_by_record_id=result_record_id,
            label="policy-disposition-continuation",
        )
        continuation["bound_by"] = "policy_disposition_smoke"
        continuation["bound_result_record_id"] = str(result_record_id)
        continuation["continuation_kind"] = "policy_disposition_followup"
    completed = store.append_completed(
        event=event,
        run_id=run_id,
        wake_cycle=2,
        result_record_id=result_record_id,
        response_text=f"Policy action selected: {action}",
    )
    disposition = store.append_policy_disposition(
        event=event,
        run_id=run_id,
        wake_cycle=2,
        result_record_id=result_record_id,
        policy_decision={
            "action": action,
            "rationale": f"deterministic {action} rationale",
            "completion_condition": f"{action} condition",
        },
        policy_result={
            "task_assessment": f"{action} assessment",
            "missing_evidence": (
                ["external confirmation source"]
                if action == "ask_external_evidence"
                else []
            ),
        },
        auto_continuation_event=continuation,
    )
    if continuation is not None:
        store.append(continuation)
    return {
        "action": action,
        "event_id": event["event_id"],
        "completed_status": completed["status"],
        "result_record_id": str(result_record_id),
        "disposition_id": disposition["disposition_id"],
        "disposition_record": disposition,
        "continuation_event_id": (
            continuation.get("event_id") if continuation is not None else None
        ),
    }


def score(rows: list[dict], summary: dict) -> dict:
    by_action = {row["action"]: row for row in rows}
    dispositions = summary.get("policy_dispositions", [])
    disposition_by_action = {
        record.get("policy_action"): record for record in dispositions
    }
    return {
        "H521_append_only_lifecycle_neutral": (
            summary.get("status_counts") == {"completed": 3, "pending": 1}
            and summary.get("event_count") == 4
            and summary.get("policy_disposition_count") == 3
            and not summary.get("lifecycle_anomalies")
        ),
        "H522_summary_distinguishes_actions": (
            summary.get("policy_disposition_counts")
            == {
                "ask_external_evidence": 1,
                "continue_after": 1,
                "stop_complete": 1,
            }
            and all(action in disposition_by_action for action in CONDITIONS)
        ),
        "H523_continue_links_to_continuation": (
            disposition_by_action.get("continue_after", {}).get(
                "continuation_event_id"
            )
            == by_action["continue_after"]["continuation_event_id"]
            and disposition_by_action.get("continue_after", {}).get(
                "continuation_kind"
            )
            == "policy_disposition_followup"
        ),
        "H524_evidence_preserves_missing_evidence": (
            disposition_by_action.get("ask_external_evidence", {}).get(
                "classification"
            )
            == "evidence_blocked"
            and disposition_by_action.get("ask_external_evidence", {}).get(
                "missing_evidence"
            )
            == ["external confirmation source"]
        ),
    }


def main() -> None:
    if EVENT_LOG_PATH.exists() or RESULTS_PATH.exists() or REPORT_PATH.exists():
        raise RuntimeError("refusing to overwrite existing smoke artifacts")
    store = EventStore(EVENT_LOG_PATH)
    rows = [
        append_condition(store, action, index)
        for index, action in enumerate(CONDITIONS, start=1)
    ]
    records = store.read_records()
    summary = summarize_event_log(records)
    report = format_event_report(summary, path=EVENT_LOG_PATH)
    payload = {
        "experiment": "policy_disposition_observability_20260605",
        "conditions": CONDITIONS,
        "event_log_path": str(EVENT_LOG_PATH.relative_to(PROJECT_ROOT)),
        "report_path": str(REPORT_PATH.relative_to(PROJECT_ROOT)),
        "rows": rows,
        "summary": summary,
        "hypothesis_results": score(rows, summary),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    REPORT_PATH.write_text(report + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
