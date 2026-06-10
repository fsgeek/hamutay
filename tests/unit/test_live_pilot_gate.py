import json

from hamutay.memory.live_pilot import (
    REQUIRED_FAILURE_LAYERS,
    _has_running_to_pending_recovery,
    classify_report_failures,
    evaluate_pilot_report,
    failure_taxonomy,
    run_no_token_dry_run_gate,
    sandbox_manifest,
    token_cycle_budget,
)


def test_no_token_dry_run_gate_writes_artifacts_and_passes(tmp_path):
    report = run_no_token_dry_run_gate(tmp_path)

    assert report["live_model_calls"] is False
    assert report["passed"] is True
    assert {case["case_id"] for case in report["cases"]} == {
        "clean_reconstruction",
        "resume_after_event_claim",
    }
    assert all(case["passed"] for case in report["cases"])
    assert all(case["failures"] == [] for case in report["cases"])

    for filename in (
        "sandbox_manifest.json",
        "token_cycle_budget.json",
        "failure_taxonomy.json",
        "dry_run_gate_report.json",
    ):
        assert (tmp_path / filename).exists()

    manifest = json.loads((tmp_path / "sandbox_manifest.json").read_text())
    budget = json.loads((tmp_path / "token_cycle_budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())

    assert manifest == sandbox_manifest()
    assert budget == token_cycle_budget()
    assert taxonomy == failure_taxonomy()
    assert manifest["live_model_calls"] is False
    assert manifest["enforcement_level"] == "in_process_detective"
    assert "not OS-level containment" in manifest["enforcement_note"]
    assert manifest["tools"]["shell"] == "disabled"
    assert budget["max_cycles"] == 2

    resume_case = next(
        case for case in report["cases"]
        if case["case_id"] == "resume_after_event_claim"
    )
    statuses = [
        item["status"] for item in resume_case["report"]["event_statuses"]
        if item["record_type"] == "event_status"
    ]
    assert statuses == ["pending", "running", "pending", "running", "completed"]


def test_failure_taxonomy_covers_required_layers():
    layers = {entry["layer"] for entry in failure_taxonomy()["entries"]}

    assert REQUIRED_FAILURE_LAYERS <= layers


def test_evaluator_classifies_report_failures_by_layer():
    report = {
        "ledger_verification": {"ok": False, "errors": [{"code": "tamper"}]},
        "ignored_ledger_count": 2,
        "invariant_failures": ["stop_policy_consistent_with_idle"],
        "action_trace_count": 1,
        "stopped_because": "wording should not drive classification",
        "invariants": {
            "ledger_verified": False,
            "restart_frontier_clean": False,
            "closed_handle_had_prior_open_item": True,
            "stop_policy_consistent_with_idle": False,
            "event_reached_completed": True,
            "no_pending_or_running_events": True,
        },
    }

    failures = classify_report_failures(report)
    evaluation = evaluate_pilot_report(report, case_id="synthetic_failure")
    layers = {failure["layer"] for failure in failures}
    codes = {failure["code"] for failure in failures}

    assert evaluation["passed"] is False
    assert {"substrate", "restart_boundary", "harness", "model"} <= layers
    assert {
        "action_ledger_verification_failed",
        "restart_frontier_unclean",
        "invariant_failure",
        "model_action_missing",
        "model_policy_incoherent",
    } <= codes
    assert evaluation["required_layers_available"] is True


def test_stop_message_wording_does_not_create_model_failure():
    report = {
        "ledger_verification": {"ok": True, "errors": []},
        "ignored_ledger_count": 0,
        "invariant_failures": [],
        "action_trace_count": 2,
        "stopped_because": "idle with alternate human-readable phrasing",
        "invariants": {
            "ledger_verified": True,
            "restart_frontier_clean": True,
            "closed_handle_had_prior_open_item": True,
            "stop_policy_consistent_with_idle": True,
            "event_reached_completed": True,
            "no_pending_or_running_events": True,
        },
    }

    assert classify_report_failures(report) == []
    assert evaluate_pilot_report(report, case_id="alternate_stop")[
        "passed"
    ] is True


def test_evaluator_marks_missing_invariants_unscoreable():
    report = {
        "ledger_verification": {"ok": True, "errors": []},
        "ignored_ledger_count": 0,
        "invariant_failures": [],
        "action_trace_count": 2,
        "stopped_because": "idle: no open work remained",
        "invariants": {"ledger_verified": True},
    }

    evaluation = evaluate_pilot_report(report, case_id="missing_invariants")

    assert evaluation["passed"] is False
    assert evaluation["failures"] == [
        {
            "layer": "scorer",
            "code": "report_unscoreable",
            "evidence": {
                "missing_invariants": [
                    "closed_handle_had_prior_open_item",
                    "event_reached_completed",
                    "no_pending_or_running_events",
                    "restart_frontier_clean",
                    "stop_policy_consistent_with_idle",
                ]
            },
        }
    ]


def test_recovery_detection_is_event_id_aware():
    assert _has_running_to_pending_recovery(
        {
            "event_statuses": [
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "running",
                },
                {
                    "record_type": "event_status",
                    "event_id": "b",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "completed",
                },
            ]
        }
    ) is False
    assert _has_running_to_pending_recovery(
        {
            "event_statuses": [
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "running",
                },
                {
                    "record_type": "event_status",
                    "event_id": "b",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "running",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "completed",
                },
            ]
        }
    ) is True
