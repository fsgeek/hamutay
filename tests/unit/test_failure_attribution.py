from hamutay.memory.failure_attribution import classify_action_row_failure


def _row(**overrides):
    row = {
        "row_id": "row-1",
        "prompt_condition": "test",
        "provider_failure": None,
        "raw_content": '{"response":"ok"}',
        "strict_evaluation": {
            "parse_status": "parsed",
            "strict_required_actions_valid": False,
            "relaxed_required_actions_valid": False,
            "rejection_paths": [],
            "trace": {"rejected_actions": []},
        },
        "relaxed_evaluation": {
            "relaxed_required_actions_valid": False,
        },
    }
    row.update(overrides)
    return row


def test_passed_primary_strict_is_not_reclassified():
    row = _row(
        strict_evaluation={
            "strict_required_actions_valid": True,
            "rejection_paths": [],
        }
    )

    result = classify_action_row_failure(row)

    assert result["primary_attribution"] == "passed_primary_strict"


def test_provider_failure_is_provider_substrate():
    row = _row(provider_failure={"layer": "provider", "code": "provider_api_error"})

    result = classify_action_row_failure(row)

    assert result["primary_attribution"] == "provider_substrate_failure"


def test_blank_protocol_failure_is_transport_contract():
    row = _row(
        provider_failure={"layer": "protocol", "code": "invalid_action_schema"},
        raw_content="     ",
        recovery_evaluation={"recovery_attempted": True, "recovered": False},
    )

    result = classify_action_row_failure(row)

    assert result["primary_attribution"] == "prompt_transport_contract"


def test_recovered_strict_valid_protocol_failure_is_parser_boundary():
    row = _row(
        provider_failure={"layer": "protocol", "code": "invalid_action_schema"},
        recovery_evaluation={
            "recovery_attempted": True,
            "recovered": True,
            "strict_pass_if_recovered": True,
        },
    )

    result = classify_action_row_failure(row)

    assert result["primary_attribution"] == "parser_recovery_boundary"


def test_schedule_request_shape_failure_is_model_contract_boundary():
    row = _row(
        strict_evaluation={
            "parse_status": "parsed",
            "strict_required_actions_valid": False,
            "rejection_paths": ["$.schedule_requests[0]"],
            "trace": {
                "rejected_actions": [
                    {
                        "action_type": "schedule_request",
                        "code": "invalid_schedule_request",
                    }
                ]
            },
        }
    )

    result = classify_action_row_failure(row)

    assert result["primary_attribution"] == "model_contract_boundary"


def test_relaxed_pass_with_open_item_shape_failure_is_prompt_schema_contract():
    row = _row(
        strict_evaluation={
            "parse_status": "parsed",
            "strict_required_actions_valid": False,
            "rejection_paths": ["$.open_items[0].kind"],
            "trace": {"rejected_actions": []},
        },
        relaxed_evaluation={"relaxed_required_actions_valid": True},
    )

    result = classify_action_row_failure(row)

    assert result["primary_attribution"] == "prompt_schema_contract"
