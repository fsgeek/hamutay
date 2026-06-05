"""Deterministic smoke for evidence-block fulfillment and resume events."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from hamutay.events import (
    EventStore,
    build_evidence_resume_event,
    build_event_envelope,
    build_pending_event,
    format_event_report,
    summarize_event_log,
)


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
EVENT_LOG_PATH = EXP_DIR / "evidence_block_resume.events.jsonl"
RESULTS_PATH = EXP_DIR / "results.json"
REPORT_PATH = EXP_DIR / "event_report.txt"


def stable_uuid(index: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{index:012d}")


def append_blocked_wake(store: EventStore) -> dict:
    event = build_pending_event(
        purpose="Evaluate an evidence-dependent claim.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=stable_uuid(1),
        label="evidence-block-source",
    )
    run_id = str(stable_uuid(100))
    result_record_id = stable_uuid(200)
    store.append(event)
    store.append_running(event, run_id=UUID(run_id))
    completed = store.append_completed(
        event=event,
        run_id=run_id,
        wake_cycle=2,
        result_record_id=result_record_id,
        response_text="Cannot evaluate without the external source.",
    )
    disposition = store.append_policy_disposition(
        event=event,
        run_id=run_id,
        wake_cycle=2,
        result_record_id=result_record_id,
        policy_decision={
            "action": "ask_external_evidence",
            "rationale": "external confirmation is absent",
        },
        policy_result={
            "task_assessment": "evidence-blocked",
            "missing_evidence": ["external completion confirmation"],
        },
    )
    return {
        "event": event,
        "completed": completed,
        "disposition": disposition,
        "result_record_id": str(result_record_id),
    }


def score(
    *,
    blocked: dict,
    request: dict,
    fulfillment: dict,
    resume_event: dict,
    before_summary: dict,
    after_summary: dict,
    envelope: str,
) -> dict:
    return {
        "H541_request_append_only_and_linked": (
            request.get("record_type") == "evidence_request"
            and request.get("source_event_id") == blocked["event"]["event_id"]
            and request.get("source_disposition_id")
            == blocked["disposition"]["disposition_id"]
            and request.get("result_record_id") == blocked["result_record_id"]
            and request.get("missing_evidence")
            == ["external completion confirmation"]
            and before_summary.get("status_counts") == {"completed": 1}
        ),
        "H542_fulfillment_append_only_satisfies_request": (
            fulfillment.get("record_type") == "evidence_fulfillment"
            and fulfillment.get("request_id") == request.get("request_id")
            and fulfillment.get("evidence", {}).get("finding")
            == "scheduled task completed successfully"
            and after_summary.get("fulfilled_evidence_request_count") == 1
        ),
        "H543_fulfilled_evidence_creates_resume_event": (
            resume_event.get("status") == "pending"
            and resume_event.get("resumes_evidence_request_id")
            == request.get("request_id")
            and resume_event.get("resumes_evidence_fulfillment_id")
            == fulfillment.get("fulfillment_id")
            and resume_event.get("requested_context") == [{
                "tool": "recall",
                "record_id": blocked["result_record_id"],
            }]
            and fulfillment.get("fulfillment_id") in envelope
        ),
        "H544_summaries_distinguish_open_and_fulfilled": (
            before_summary.get("open_evidence_request_count") == 1
            and before_summary.get("fulfilled_evidence_request_count") == 0
            and after_summary.get("open_evidence_request_count") == 0
            and after_summary.get("fulfilled_evidence_request_count") == 1
            and after_summary.get("status_counts") == {
                "completed": 1,
                "pending": 1,
            }
            and not after_summary.get("lifecycle_anomalies")
        ),
    }


def main() -> None:
    for path in (EVENT_LOG_PATH, RESULTS_PATH, REPORT_PATH):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite {path}")
    store = EventStore(EVENT_LOG_PATH)
    blocked = append_blocked_wake(store)
    request = store.append_evidence_request(
        policy_disposition=blocked["disposition"],
    )
    before_summary = summarize_event_log(store.read_records())
    fulfillment = store.append_evidence_fulfillment(
        evidence_request=request,
        evidence={
            "source_name": "external completion ledger",
            "finding": "scheduled task completed successfully",
            "source_record": "ledger://completion/17",
        },
        source="deterministic-smoke",
    )
    resume_event = build_evidence_resume_event(
        evidence_request=request,
        evidence_fulfillment=fulfillment,
        purpose=(
            "Resume the evidence-blocked task using the supplied external "
            "completion evidence."
        ),
        label="resume-evidence-blocked-work",
    )
    store.append(resume_event)
    records = store.read_records()
    after_summary = summarize_event_log(records)
    envelope = build_event_envelope(resume_event, [], "resume-run")
    report = format_event_report(after_summary, path=EVENT_LOG_PATH)
    payload = {
        "experiment": "evidence_block_resume_20260605",
        "event_log_path": str(EVENT_LOG_PATH.relative_to(PROJECT_ROOT)),
        "report_path": str(REPORT_PATH.relative_to(PROJECT_ROOT)),
        "blocked": blocked,
        "evidence_request": request,
        "evidence_fulfillment": fulfillment,
        "resume_event": resume_event,
        "resume_event_envelope": json.loads(envelope),
        "before_summary": before_summary,
        "after_summary": after_summary,
        "hypothesis_results": score(
            blocked=blocked,
            request=request,
            fulfillment=fulfillment,
            resume_event=resume_event,
            before_summary=before_summary,
            after_summary=after_summary,
            envelope=envelope,
        ),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    REPORT_PATH.write_text(report + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
