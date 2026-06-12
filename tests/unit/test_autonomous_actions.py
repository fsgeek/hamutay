from uuid import UUID

from hamutay.memory.actions import (
    AUTONOMOUS_ACTION_SCHEMA_VERSION,
    parse_autonomous_action,
)


RID = UUID("30000000-0000-0000-0000-000000000001")


def _handle() -> dict:
    return {"record_id": str(RID), "source": "open_items", "index": 0}


def test_valid_autonomous_action_accepts_model_authored_control_surface():
    trace = parse_autonomous_action(
        {
            "response": "I will continue this after the evidence wake.",
            "open_items": [{"kind": "todo", "text": "inspect the new evidence"}],
            "closures": [
                {
                    "target_handle": _handle(),
                    "status": "resolved",
                    "basis": "the evidence was inspected",
                }
            ],
            "schedule_requests": [
                {
                    "purpose": "resume after evidence arrives",
                    "requested_context": [
                        {"tool": "recall", "record_id": str(RID), "field": "claim"}
                    ],
                    "not_before": "2026-06-09T12:00:00+00:00",
                }
            ],
            "policy_action": "continue_after",
            "declared_losses": [{"what": "source freshness", "why": "not provided"}],
            "uncertainty": [{"claim": "external evidence remains partial"}],
        }
    )

    row = trace.to_dict()

    assert row["schema_version"] == AUTONOMOUS_ACTION_SCHEMA_VERSION
    assert row["parse_status"] == "parsed"
    assert row["validation_status"] == "accepted"
    assert row["rejected_actions"] == []
    assert {action["action_type"] for action in row["accepted_actions"]} == {
        "response",
        "open_item",
        "closure",
        "schedule_request",
        "policy_action",
        "declared_loss",
        "uncertainty",
    }
    schedule = next(
        action for action in row["accepted_actions"]
        if action["action_type"] == "schedule_request"
    )
    assert schedule["parameters"]["requested_context"] == [
        {"tool": "recall", "record_id": str(RID), "field": "claim"}
    ]


def test_missing_response_rejects_whole_action_without_hiding_valid_subactions():
    trace = parse_autonomous_action(
        {
            "open_items": [{"kind": "todo", "text": "still visible"}],
        }
    ).to_dict()

    assert trace["parse_status"] == "parsed"
    assert trace["validation_status"] == "rejected"
    assert any(
        rejection["code"] == "required_response_missing"
        for rejection in trace["rejected_actions"]
    )
    assert any(
        action["action_type"] == "open_item"
        for action in trace["accepted_actions"]
    )


def test_malformed_closure_target_is_rejected_but_logged():
    trace = parse_autonomous_action(
        {
            "response": "I think I closed it.",
            "closures": [
                {
                    "target_handle": {"record_id": str(RID), "source": "open_items"},
                    "status": "resolved",
                }
            ],
        }
    ).to_dict()

    assert trace["validation_status"] == "accepted_with_rejections"
    assert trace["accepted_actions"][0]["action_type"] == "response"
    assert trace["rejected_actions"] == [
        {
            "action_type": "closure",
            "source_path": "$.closures[0].target_handle",
            "code": "malformed_target_handle",
            "message": (
                "closure target_handle must include valid record_id, source, "
                "and non-negative index"
            ),
            "value": {"record_id": str(RID), "source": "open_items"},
        }
    ]


def test_invalid_schedule_request_is_rejected_but_not_inferred():
    trace = parse_autonomous_action(
        {
            "response": "Call me later.",
            "schedule_requests": [
                {
                    "purpose": "later",
                    "requested_context": [
                        {"tool": "recall", "record_id": str(RID), "extra": "nope"}
                    ],
                }
            ],
        }
    ).to_dict()

    assert trace["validation_status"] == "accepted_with_rejections"
    assert any(
        rejection["action_type"] == "schedule_request"
        and rejection["code"] == "invalid_schedule_request"
        and "unsupported keys" in rejection["message"]
        for rejection in trace["rejected_actions"]
    )
    assert not any(
        action["action_type"] == "schedule_request"
        for action in trace["accepted_actions"]
    )


def test_continue_after_without_schedule_request_rejects_policy_action():
    trace = parse_autonomous_action(
        {
            "response": "I should continue after this.",
            "policy_action": "continue_after",
        }
    ).to_dict()

    assert trace["validation_status"] == "accepted_with_rejections"
    assert trace["parsed_action"] == {"response": "I should continue after this."}
    assert any(
        action["action_type"] == "response"
        for action in trace["accepted_actions"]
    )
    assert not any(
        action["action_type"] == "policy_action"
        for action in trace["accepted_actions"]
    )
    assert trace["rejected_actions"] == [
        {
            "action_type": "policy_action",
            "source_path": "$.policy_action",
            "code": "continue_after_without_continuation_request",
            "message": (
                "continue_after requires at least one valid schedule_request "
                "continuation request"
            ),
            "value": "continue_after",
        }
    ]


def test_continue_after_with_malformed_schedule_request_rejects_policy_action_too():
    trace = parse_autonomous_action(
        {
            "response": "I should continue after this.",
            "schedule_requests": [
                {
                    "purpose": "resume the work",
                    "requested_context": {
                        "tool": "recall",
                        "record_id": str(RID),
                    },
                }
            ],
            "policy_action": "continue_after",
        }
    ).to_dict()

    assert trace["validation_status"] == "accepted_with_rejections"
    assert trace["parsed_action"] == {
        "response": "I should continue after this.",
        "schedule_requests": [],
    }
    assert [
        rejection["code"] for rejection in trace["rejected_actions"]
    ] == [
        "invalid_schedule_request",
        "continue_after_without_continuation_request",
    ]
    assert not any(
        action["action_type"] == "policy_action"
        for action in trace["accepted_actions"]
    )


def test_continue_after_with_valid_schedule_request_accepts_policy_action():
    trace = parse_autonomous_action(
        {
            "response": "I should continue after this.",
            "schedule_requests": [
                {
                    "purpose": "resume the work",
                    "requested_context": [
                        {
                            "tool": "recall",
                            "record_id": str(RID),
                        }
                    ],
                }
            ],
            "policy_action": "continue_after",
        }
    ).to_dict()

    assert trace["validation_status"] == "accepted"
    assert trace["rejected_actions"] == []
    assert any(
        action["action_type"] == "schedule_request"
        for action in trace["accepted_actions"]
    )
    assert any(
        action["action_type"] == "policy_action"
        for action in trace["accepted_actions"]
    )


def test_unknown_action_field_is_rejected_without_interpretation():
    trace = parse_autonomous_action(
        {
            "response": "Visible response remains valid.",
            "teleport_repo": {"path": "/tmp/outside"},
        }
    ).to_dict()

    assert trace["validation_status"] == "accepted_with_rejections"
    assert trace["accepted_actions"] == [
        {
            "action_type": "response",
            "parameters": {"response": "Visible response remains valid."},
            "source_path": "$.response",
        }
    ]
    assert trace["rejected_actions"][0]["action_type"] == "unknown_action"
    assert trace["rejected_actions"][0]["code"] == "unknown_field"


def test_non_object_output_fails_parse_and_preserves_raw_value():
    trace = parse_autonomous_action("not an action").to_dict()

    assert trace["parse_status"] == "failed"
    assert trace["validation_status"] == "rejected"
    assert trace["raw_output"] == "not an action"
    assert trace["parsed_action"] is None
