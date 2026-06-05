"""Tests for scheduler policy boundaries."""

from __future__ import annotations

from uuid import UUID

from hamutay.event_policies import (
    BranchContextPolicy,
    EventRunResult,
    ForkRunStore,
    ForkJoinPolicyRunner,
    build_fork_run_started_record,
    default_fork_run_log_path,
    finalize_failed_fork_run,
    finalize_successful_fork_run,
    latest_event_records_by_label,
)
from hamutay.events import EventStore, build_pending_event


def test_branch_visible_records_are_idempotent_and_strip_activity_log():
    policy = BranchContextPolicy()
    records = [
        {
            "cycle": 2,
            "record_id": "00000000-0000-0000-0000-000000000002",
            "system_prompt": "framework text mentioning _activity_log",
            "user_message": "transcript text mentioning _activity_log",
            "state": {
                "claim": "visible",
                "_activity_log": [{"tool": "schedule_event"}],
                "nested": {"_activity_log": [{"tool": "bash"}]},
            },
            "prior_state": {"_activity_log": [{"tool": "read"}]},
        }
    ]

    once = policy.branch_visible_records(records)
    twice = policy.branch_visible_records(once)

    assert once == twice
    assert "_activity_log" not in once[0]["state"]
    assert "_activity_log" not in once[0]["state"]["nested"]
    assert "prior_state" not in once[0]
    assert "system_prompt" not in once[0]
    assert "user_message" not in once[0]
    assert "_activity_log" in records[0]["state"]


def test_branch_visible_context_results_strip_activity_log():
    policy = BranchContextPolicy()
    context_results = [
        {
            "request": {"tool": "recall", "cycle": 2},
            "result": {
                "content": {
                    "claim": "visible",
                    "_activity_log": [{"tool": "schedule_event"}],
                }
            },
        }
    ]

    sanitized = policy.branch_visible_context_results(context_results)

    assert "_activity_log" not in sanitized[0]["result"]["content"]
    assert "_activity_log" in context_results[0]["result"]["content"]


def test_sidecar_audit_projection_joins_pending_purpose_to_terminal_status():
    policy = BranchContextPolicy()
    pending = build_pending_event(
        purpose="Branch A work.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
        label="branch-a",
    )
    completed = {
        "record_type": "event_status",
        "event_id": pending["event_id"],
        "status": "completed",
        "result_record_id": "00000000-0000-0000-0000-000000000002",
    }

    projection = policy.sidecar_audit_projection(
        [pending, completed],
        labels=["branch-a"],
    )

    assert projection["branch-a"]["audit_complete"] is True
    assert projection["branch-a"]["purpose"] == "Branch A work."
    assert projection["branch-a"]["terminal_status"] == "completed"
    assert projection["branch-a"]["terminal_record"] == completed


def test_build_join_event_uses_fork_coordinates_and_branch_outputs():
    policy = BranchContextPolicy()
    event = policy.build_join_event(
        fork_record={
            "cycle": 2,
            "record_id": "00000000-0000-0000-0000-000000000002",
        },
        branch_outputs=[
            {"branch_id": "branch-a", "branch_findings": ["a"]},
            {"branch_id": "branch-b", "branch_findings": ["b"]},
        ],
    )

    assert event["label"] == "fork-join"
    assert event["scheduled_by_cycle"] == 2
    assert event["scheduled_by_record_id"] == (
        "00000000-0000-0000-0000-000000000002"
    )
    assert "branch-a" in event["purpose"]
    assert "branch-b" in event["purpose"]


def test_latest_event_records_by_label_uses_pending_label_and_latest_status():
    pending = build_pending_event(
        purpose="Branch B work.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
        label="branch-b",
    )
    failed = {
        "record_type": "event_status",
        "event_id": pending["event_id"],
        "status": "failed",
        "error": "boom",
    }

    latest = latest_event_records_by_label([pending, failed])

    assert latest["branch-b"] == failed


def test_event_run_result_reports_result_record_id():
    result = EventRunResult(
        label="branch-a",
        status="completed",
        terminal_record={
            "status": "completed",
            "result_record_id": "00000000-0000-0000-0000-000000000002",
        },
    )

    assert result.result_record_id == "00000000-0000-0000-0000-000000000002"
    assert result.to_dict()["result_record_id"] == result.result_record_id


def test_fork_join_runner_suppresses_pending_after_failure(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    pending = build_pending_event(
        purpose="Sibling branch.",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=UUID("00000000-0000-0000-0000-000000000001"),
        label="branch-b",
    )
    store.append(pending)
    runner = ForkJoinPolicyRunner()

    suppressed = runner.suppress_pending_after_failure(
        store=store,
        failed_wake_record={
            "cycle": 3,
            "record_id": "00000000-0000-0000-0000-000000000003",
        },
    )

    assert len(suppressed) == 1
    assert suppressed[0]["status"] == "suppressed"
    assert suppressed[0]["suppressed_by_cycle"] == 3
    assert suppressed[0]["suppressed_by_record_id"] == (
        "00000000-0000-0000-0000-000000000003"
    )


def test_default_fork_run_log_path_is_sidecar():
    assert str(default_fork_run_log_path("session.events.jsonl")).endswith(
        ".events.jsonl.fork_runs.jsonl"
    )


def test_fork_run_store_appends_and_tracks_latest(tmp_path):
    store = ForkRunStore(tmp_path / "runs.jsonl")
    store.append({
        "record_type": "fork_run",
        "fork_run_id": "run-1",
        "status": "started",
    })
    store.append({
        "record_type": "fork_run",
        "fork_run_id": "run-1",
        "status": "joined",
    })

    records = store.read_records()

    assert [record["status"] for record in records] == ["started", "joined"]
    assert store.latest_by_run_id()["run-1"]["status"] == "joined"


def test_build_fork_run_started_record_has_identity_and_root():
    record = build_fork_run_started_record(
        fork_record={
            "cycle": 2,
            "record_id": "00000000-0000-0000-0000-000000000002",
        },
        branch_labels=["branch-a", "branch-b"],
        fork_run_id="run-1",
    )

    assert record["record_type"] == "fork_run"
    assert record["fork_run_id"] == "run-1"
    assert record["status"] == "started"
    assert record["scheduled_by_cycle"] == 2
    assert record["scheduled_by_record_id"] == (
        "00000000-0000-0000-0000-000000000002"
    )
    assert record["branch_labels"] == ["branch-a", "branch-b"]


def test_finalize_successful_fork_run_binds_branch_and_join_coordinates():
    started = build_fork_run_started_record(
        fork_record={
            "cycle": 2,
            "record_id": "00000000-0000-0000-0000-000000000002",
        },
        branch_labels=["branch-a", "branch-b"],
        fork_run_id="run-1",
    )
    branch_results = [
        EventRunResult(
            label="branch-a",
            status="completed",
            terminal_record={"result_record_id": "result-a"},
        ),
        EventRunResult(
            label="branch-b",
            status="completed",
            terminal_record={"result_record_id": "result-b"},
        ),
    ]
    join_result = EventRunResult(
        label="fork-join",
        status="completed",
        terminal_record={"result_record_id": "join-result"},
    )

    record = finalize_successful_fork_run(
        started_record=started,
        branch_results=branch_results,
        join_event={"event_id": "join-event"},
        join_result=join_result,
        sidecar_audit_projection={
            "branch-a": {"event_id": "event-a", "terminal_status": "completed"},
            "branch-b": {"event_id": "event-b", "terminal_status": "completed"},
        },
    )

    assert record["fork_run_id"] == "run-1"
    assert record["classification"] == "joined"
    assert record["branch_events"]["branch-a"]["event_id"] == "event-a"
    assert record["branch_events"]["branch-a"]["result_record_id"] == "result-a"
    assert record["join_event_id"] == "join-event"
    assert record["join_result_record_id"] == "join-result"


def test_finalize_failed_fork_run_binds_failure_and_suppression():
    started = build_fork_run_started_record(
        fork_record={
            "cycle": 2,
            "record_id": "00000000-0000-0000-0000-000000000002",
        },
        branch_labels=["branch-a", "branch-b"],
        fork_run_id="run-1",
    )
    failed = EventRunResult(
        label="branch-a",
        status="failed",
        terminal_record={"event_id": "event-a", "status": "failed"},
        error="boom",
    )

    record = finalize_failed_fork_run(
        started_record=started,
        failed_branch_result=failed,
        failed_wake_record={
            "cycle": 3,
            "record_id": "00000000-0000-0000-0000-000000000003",
        },
        suppression_records=[
            {
                "event_id": "event-b",
                "status": "suppressed",
                "suppressed_by_record_id": (
                    "00000000-0000-0000-0000-000000000003"
                ),
            }
        ],
        sidecar_audit_projection={
            "branch-a": {"event_id": "event-a", "terminal_status": "failed"},
            "branch-b": {"event_id": "event-b", "terminal_status": "suppressed"},
        },
    )

    assert record["classification"] == "branch_failed"
    assert record["failed_branch"] == "branch-a"
    assert record["failed_branch_wake_record_id"] == (
        "00000000-0000-0000-0000-000000000003"
    )
    assert record["suppressed_events"] == ["event-b"]
    assert record["branch_events"]["branch-b"]["terminal_status"] == "suppressed"
