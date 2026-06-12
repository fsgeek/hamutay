import pytest

from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.rehearsal import (
    RehearsalInterrupted,
    RehearsalPaths,
    RestartableAutonomyRehearsal,
    reconstruct_rehearsal_report,
    run_fake_autonomy_rehearsal,
)


def _operation_statuses(report: dict) -> set[tuple[str, str]]:
    return {
        (item["operation_type"], item["result_status"])
        for item in report["operation_statuses"]
    }


def test_restartable_rehearsal_uses_action_pipeline_and_reconstructs_report(
    tmp_path,
):
    result = run_fake_autonomy_rehearsal(output_dir=tmp_path)
    report = result.to_dict()
    reconstructed = reconstruct_rehearsal_report(result.paths)

    assert report["ledger_verification"]["ok"] is True
    assert reconstructed["ledger_verification"]["ok"] is True
    assert report["frontier"]["cycle_id"] == 2
    assert report["frontier"]["next_cycle_id"] == 3
    assert report["run_manifests"][0]["manifest"]["rehearsal"] == (
        "restartable_no_token"
    )
    assert report["action_trace_count"] == 2
    assert [item["model_input"]["cycle_id"] for item in report["model_inputs"]] == [
        1,
        2,
    ]
    assert [item["raw_output"]["response"] for item in report["model_emissions"]] == [
        "I found one bounded item and scheduled the next wake.",
        "I closed the scheduled rehearsal item and can stop.",
    ]
    assert len(report["action_attempts"]) == 2
    assert any(
        action["action_type"] == "schedule_request"
        for action in report["action_attempts"][0]["accepted_actions"]
    )
    assert report["action_attempts"][0]["rejected_actions"] == []
    assert report["action_responses"] == [
        "I found one bounded item and scheduled the next wake.",
        "I closed the scheduled rehearsal item and can stop.",
    ]
    assert any(
        item["operation_type"] == "memory_open_items"
        and item["result_status"] == "applied"
        for item in report["memory_operations"]
    )
    assert any(
        item["operation_type"] == "present_wake_to_model"
        for item in report["scheduler_operations"]
    )
    assert {
        "model",
        "protocol",
        "harness",
        "substrate",
        "provider",
        "scorer",
        "restart_boundary",
    }.issubset(set(report["failure_taxonomy_layers"]))
    assert {
        ("store_autonomous_action_record", "applied"),
        ("apply_schedule_request", "applied"),
        ("apply_closure", "applied"),
        ("apply_policy_disposition", "applied"),
        ("complete_rehearsal_event", "applied"),
    }.issubset(_operation_statuses(report))
    assert report["open_items_after"]["ok"] is True
    assert report["open_items_after"]["items"] == []
    assert report["no_open_items_due_to_model_authored_closure"] is True
    assert report["invariant_failures"] == []
    assert all(report["invariants"].values())
    assert report["stopped_because"] == "idle: no open work remained"
    assert report == reconstructed


def test_restartable_rehearsal_event_log_runs_seed_schedule_closure_idle(tmp_path):
    result = run_fake_autonomy_rehearsal(output_dir=tmp_path)
    statuses = [
        item["status"] for item in result.report["event_statuses"]
        if item["record_type"] == "event_status"
    ]
    policy_actions = [
        item["policy_action"] for item in result.report["event_statuses"]
        if item["record_type"] == "policy_disposition"
    ]

    assert statuses == ["pending", "running", "completed"]
    assert policy_actions == ["stop_complete"]
    assert result.report["suppressed_event_count"] == 0
    assert result.report["recovered_event_count"] == 0


def test_restartable_rehearsal_resume_after_seed_apply_retries_without_duplicates(
    tmp_path,
):
    paths = RehearsalPaths.from_root(tmp_path)
    runner = RestartableAutonomyRehearsal(paths=paths)

    with pytest.raises(RehearsalInterrupted, match="after_seed_apply"):
        runner.run(interrupt_after="after_seed_apply")

    resumed = RestartableAutonomyRehearsal(paths=paths).run()
    report = resumed.to_dict()
    ledger = ActionLedger(paths.ledger_path)
    operations = [
        record["payload"]
        for record in ledger.read_records()
        if record["record_type"] == "operation"
    ]

    assert report["frontier"]["cycle_id"] == 2
    assert report["no_open_items_due_to_model_authored_closure"] is True
    assert report["invariant_failures"] == []
    assert report["invariants"]["restart_frontier_clean"] is True
    assert report["invariants"]["no_pending_or_running_events"] is True
    assert report["stopped_because"] == "idle: no open work remained"
    assert any(item["status"] == "suppressed" for item in report["event_statuses"])
    assert sum(
        1 for item in report["event_statuses"]
        if item["record_type"] == "event_status"
        and item["status"] == "completed"
    ) == 1
    assert sum(
        1 for op in operations
        if op["operation_type"] == "apply_schedule_request"
        and op["result_status"] == "applied"
    ) == 2


def test_restartable_rehearsal_resume_after_event_claim_recovers_pending_wake(
    tmp_path,
):
    paths = RehearsalPaths.from_root(tmp_path)
    runner = RestartableAutonomyRehearsal(paths=paths)

    with pytest.raises(RehearsalInterrupted, match="after_event_claim"):
        runner.run(interrupt_after="after_event_claim")

    report = RestartableAutonomyRehearsal(paths=paths).run().to_dict()
    statuses = [
        item["status"] for item in report["event_statuses"]
        if item["record_type"] == "event_status"
    ]

    assert report["frontier"]["cycle_id"] == 2
    assert report["no_open_items_due_to_model_authored_closure"] is True
    assert report["invariant_failures"] == []
    assert report["invariants"]["event_reached_completed"] is True
    assert report["stopped_because"] == "idle: no open work remained"
    assert statuses == ["pending", "running", "pending", "running", "completed"]
