import json

from hamutay.memory.action_ledger import (
    GENESIS_HASH,
    OPERATION_RECORD_SCHEMA,
    ActionLedger,
    canonical_hash,
)
from hamutay.memory.actions import parse_autonomous_action
from hamutay.tools.schemas import TOOL_SCHEMAS


def test_action_ledger_appends_manifest_trace_and_operation_with_hash_chain(tmp_path):
    ledger = ActionLedger(tmp_path / "actions.jsonl")
    manifest = ledger.append_run_manifest(
        run_id="run-1",
        manifest={"model": "fake", "budget": {"cycles": 2}},
        sandbox={"shell": "disabled"},
    )
    trace = parse_autonomous_action(
        {"response": "ok", "policy_action": "stop_complete"}
    ).to_dict()
    trace_row = ledger.append_action_trace(
        run_id="run-1",
        cycle_id=1,
        trace=trace,
    )
    operation = ledger.append_operation(
        run_id="run-1",
        cycle_id=1,
        operation_id="op-1",
        operation_type="policy_action",
        actor="harness",
        raw_parameters={"policy_action": "stop_complete"},
        validated_parameters={"policy_action": "stop_complete"},
        reason={"text": "accepted model-authored policy"},
        precondition_checks=[{"name": "allowed_policy", "ok": True}],
        result_status="accepted",
        result={"stored": False},
        created_records=[],
    )
    records = ledger.read_records()
    verification = ledger.verify()

    assert [record["sequence"] for record in records] == [1, 2, 3]
    assert manifest["previous_hash"] == GENESIS_HASH
    assert trace_row["previous_hash"] == manifest["record_hash"]
    assert operation["previous_hash"] == trace_row["record_hash"]
    assert manifest["payload"]["manifest_hash"] == canonical_hash(
        {"model": "fake", "budget": {"cycles": 2}}
    )
    assert verification.ok
    assert verification.record_count == 3
    assert verification.errors == []


def test_operation_record_schema_names_required_audit_fields():
    assert OPERATION_RECORD_SCHEMA["record_type"] == "operation"
    assert set(OPERATION_RECORD_SCHEMA["required_payload_fields"]) == {
        "run_id",
        "cycle_id",
        "wake_id",
        "operation_id",
        "operation_type",
        "actor",
        "raw_parameters",
        "validated_parameters",
        "reason",
        "precondition_checks",
        "result_status",
        "result",
        "result_hash",
        "truncation",
        "omission",
        "error",
        "created_records",
    }


def test_action_ledger_logs_accepted_and_rejected_validation_actions_as_operations(
    tmp_path,
):
    ledger = ActionLedger(tmp_path / "actions.jsonl")
    ledger.append_run_manifest(run_id="run-2", manifest={})
    trace = parse_autonomous_action(
        {"response": "ok", "unknown_move": {"x": 1}}
    ).to_dict()
    trace_row = ledger.append_action_trace(run_id="run-2", cycle_id=7, trace=trace)
    operation_rows = ledger.append_validation_operations(
        run_id="run-2",
        cycle_id=7,
        trace=trace,
    )
    rejection_rows = [
        row for row in operation_rows
        if row["payload"]["result_status"] == "rejected"
    ]
    accepted_rows = [
        row for row in operation_rows
        if row["payload"]["result_status"] == "accepted"
    ]

    assert trace_row["payload"]["trace"]["validation_status"] == (
        "accepted_with_rejections"
    )
    assert len(accepted_rows) == 1
    accepted = accepted_rows[0]["payload"]
    assert accepted["operation_type"] == "response"
    assert accepted["validated_parameters"] == {"response": "ok"}
    assert len(rejection_rows) == 1
    rejection = rejection_rows[0]["payload"]
    assert rejection["operation_type"] == "unknown_action"
    assert rejection["result_status"] == "rejected"
    assert rejection["error"]["layer"] == "validation"
    assert ledger.verify().ok


def test_action_ledger_rejection_helper_filters_validation_operations(tmp_path):
    ledger = ActionLedger(tmp_path / "actions.jsonl")
    trace = parse_autonomous_action(
        {"response": "ok", "unknown_move": {"x": 1}}
    ).to_dict()

    rows = ledger.append_validation_rejections(
        run_id="run-2",
        cycle_id=7,
        trace=trace,
    )

    assert len(rows) == 1
    assert rows[0]["payload"]["operation_type"] == "unknown_action"
    assert rows[0]["payload"]["result_status"] == "rejected"


def test_action_ledger_detects_tampering_with_prior_record(tmp_path):
    path = tmp_path / "actions.jsonl"
    ledger = ActionLedger(path)
    ledger.append_run_manifest(run_id="run-3", manifest={"model": "fake"})
    ledger.append_operation(
        run_id="run-3",
        operation_id="op-1",
        operation_type="noop",
        actor="harness",
        result_status="accepted",
        result={"ok": True},
    )

    lines = path.read_text().splitlines()
    first = json.loads(lines[0])
    first["payload"]["manifest"]["model"] = "tampered"
    lines[0] = json.dumps(first, sort_keys=True)
    path.write_text("\n".join(lines) + "\n")

    verification = ledger.verify()

    assert not verification.ok
    assert any(
        error["code"] == "record_hash_mismatch"
        and error["sequence"] == 1
        for error in verification.errors
    )
    assert any(
        error["code"] == "previous_hash_mismatch"
        and error["sequence"] == 2
        for error in verification.errors
    )


def test_action_ledger_redaction_hook_masks_stored_payloads_but_not_manifest_hash(tmp_path):
    def redactor(value):
        if isinstance(value, dict):
            return {
                key: ("<redacted>" if key == "api_key" else redactor(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redactor(item) for item in value]
        return value

    ledger = ActionLedger(tmp_path / "actions.jsonl", redactor=redactor)
    row = ledger.append_run_manifest(
        run_id="run-4",
        manifest={"model": "fake", "api_key": "secret"},
    )

    assert row["payload"]["manifest"] == {
        "model": "fake",
        "api_key": "<redacted>",
    }
    assert row["payload"]["manifest_hash"] == canonical_hash(
        {"model": "fake", "api_key": "secret"}
    )
    assert "secret" not in (tmp_path / "actions.jsonl").read_text()


def test_action_ledger_has_no_model_facing_tool_surface():
    assert "action_ledger" not in TOOL_SCHEMAS
    assert "append_action_ledger" not in TOOL_SCHEMAS
    assert "write_ledger" not in TOOL_SCHEMAS
