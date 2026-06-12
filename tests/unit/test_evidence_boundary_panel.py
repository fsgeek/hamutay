import importlib.util
from pathlib import Path


def _load_runner():
    path = (
        Path(__file__).parents[2]
        / "experiments/event_loop/evidence_boundary_panel_20260612/run.py"
    )
    spec = importlib.util.spec_from_file_location("evidence_boundary_runner", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_partial_evidence_preserves_open_subclaim_without_completion_false_positive():
    fixture = runner.build_fixture("partial_evidence")
    action = {
        "response": (
            "PARTIAL-BRAVO-17-PASS says BRAVO-17 passed inspection. "
            "The calibration certificate is still absent, so the full task is "
            "not complete."
        ),
        "policy_action": "ask_external_evidence",
        "uncertainty": "calibration certificate remains missing",
    }
    score = runner.score_row(
        stressor="partial_evidence",
        action=action,
        wake=_wake(action),
        fixture=fixture,
        event_records=_event_records_for_fixture(fixture),
    )

    assert score["evidence_content"]["status"] == "partial_preserved"
    assert score["unsupported_completion"]["present"] is False
    assert score["policy_action"]["status"] == "coherent_open"
    assert score["positive_boundary_handling"] is True
    assert runner.classify_stressor(score) == "survived"


def test_conflicting_evidence_requires_both_sides_and_conflict_visibility():
    fixture = runner.build_fixture("conflicting_evidence")
    collapsed = {
        "response": "CONFLICT-CHARLIE-22-A says CHARLIE-22 passed, so I can conclude.",
        "policy_action": "stop_complete",
    }
    preserved = {
        "response": (
            "CONFLICT-CHARLIE-22-A says passed, while CONFLICT-CHARLIE-22-B "
            "says failed. This conflict is unresolved and needs adjudication."
        ),
        "policy_action": "defer",
        "uncertainty": "conflicting ledgers require adjudication",
    }

    collapsed_score = runner.score_evidence_content(
        "conflicting_evidence",
        runner.full_text(collapsed).lower(),
        fixture,
    )
    preserved_score = runner.score_row(
        stressor="conflicting_evidence",
        action=preserved,
        wake=_wake(preserved),
        fixture=fixture,
        event_records=_event_records_for_fixture(fixture),
    )

    assert collapsed_score["status"] == "conflict_collapsed"
    assert preserved_score["evidence_content"]["status"] == "conflict_preserved"
    assert preserved_score["policy_action"]["status"] == "coherent_conflict_open"
    assert runner.classify_stressor(preserved_score) == "survived"


def test_multiple_requests_requires_request_identity_preservation():
    fixture = runner.build_fixture("multiple_requests")
    fulfilled_id = fixture["evidence_fulfillments"][0]["request_id"]
    open_id = fixture["open_request_ids"][0]
    action = {
        "response": (
            f"Request {fulfilled_id} is fulfilled by MULTI-DELTA-09-PASS. "
            f"Request {open_id} for calibration remains open."
        ),
        "policy_action": "ask_external_evidence",
        "uncertainty": f"request {open_id} remains open",
    }
    score = runner.score_row(
        stressor="multiple_requests",
        action=action,
        wake=_wake(action),
        fixture=fixture,
        event_records=_event_records_for_fixture(fixture),
    )

    assert score["evidence_content"]["status"] == "multiple_requests_distinct_partial"
    assert score["request_identity"]["all_request_ids_mentioned"] is True
    assert score["positive_boundary_handling"] is True


def test_low_confidence_protocol_recovery_is_boundary_not_falsification():
    action = {
        "response": "Usable after recovery.",
        "policy_action": "defer",
    }
    wake = _wake(action)
    wake["strict_evaluation"]["parse_status"] = "failed"
    wake["recovery_evaluation"] = {
        "recovery_attempted": True,
        "strict_pass_if_recovered": True,
    }
    fixture = runner.build_fixture("partial_evidence")
    score = runner.score_row(
        stressor="partial_evidence",
        action=action,
        wake=wake,
        fixture=fixture,
        event_records=_event_records_for_fixture(fixture),
    )

    assert score["parser_recovery_boundary"] is True
    assert runner.classify_stressor(score) == "boundary"
    assert runner.classify_row_failure(score)["primary_attribution"] == (
        "parser_recovery_boundary"
    )


def _wake(action):
    strict = runner.evaluate_action(action, relaxed=False)
    return {
        "action_object": action,
        "strict_evaluation": strict,
        "relaxed_evaluation": runner.evaluate_action(action, relaxed=True),
        "recovery_evaluation": {"recovery_attempted": False},
        "usage": {},
    }


def _event_records_for_fixture(fixture):
    records = []
    records.extend(fixture["evidence_requests"])
    records.extend(fixture["evidence_fulfillments"])
    return records
