"""Tests for scheduler policy boundaries."""

from __future__ import annotations

from uuid import UUID

from hamutay.event_policies import BranchContextPolicy
from hamutay.events import build_pending_event


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
