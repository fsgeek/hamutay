from uuid import UUID

from hamutay.events import EventStore, build_pending_event
from hamutay.memory.action_application import AutonomousActionApplier
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.bridge import LocalMemorySubstrate


RUN_ID = "run-phase-3"
RID_BASE = "40000000-0000-0000-0000-0000000000"


def _record_id(index: int) -> UUID:
    return UUID(f"{RID_BASE}{index:02d}")


def _open_item_action(text: str = "inspect evidence") -> dict:
    return {
        "response": "I am opening work.",
        "open_items": [{"kind": "todo", "text": text}],
    }


def _make_applier(tmp_path):
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(tmp_path / "actions.jsonl")
    events = EventStore(tmp_path / "events.jsonl")
    applier = AutonomousActionApplier(
        memory=memory,
        ledger=ledger,
        event_store=events,
        instance_id="test-instance",
    )
    return applier, memory, ledger, events


def _ledger_operations(ledger: ActionLedger) -> list[dict]:
    return [
        record["payload"]
        for record in ledger.read_records()
        if record["record_type"] == "operation"
    ]


def test_application_writes_open_items_to_memory_and_logs_exact_operation(tmp_path):
    applier, memory, ledger, _events = _make_applier(tmp_path)
    trace = parse_autonomous_action(_open_item_action()).to_dict()

    result = applier.apply_trace(trace, run_id=RUN_ID, cycle_id=1)
    open_items = memory.open_items(reason="test")
    operations = _ledger_operations(ledger)

    assert result.status == "applied"
    assert result.result_record_id is not None
    assert open_items.ok
    assert open_items.data["items"][0]["item"] == {
        "kind": "todo",
        "text": "inspect evidence",
    }
    store_operation = next(
        op for op in operations
        if op["operation_type"] == "store_autonomous_action_record"
    )
    assert store_operation["result_status"] == "applied"
    assert store_operation["raw_parameters"]["content"]["open_items"] == [
        {"kind": "todo", "text": "inspect evidence"}
    ]
    assert store_operation["created_records"] == [
        {"record_type": "memory_record", "record_id": result.result_record_id}
    ]
    assert ledger.verify().ok


def test_application_closes_exact_open_item_handle_with_attestation(tmp_path):
    applier, memory, ledger, _events = _make_applier(tmp_path)
    opened = applier.apply_trace(
        parse_autonomous_action(_open_item_action("close me")).to_dict(),
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    assert opened.result_record_id == str(_record_id(1))
    handle = memory.open_items(reason="before closure").data["items"][0]["handle"]
    close_trace = parse_autonomous_action(
        {
            "response": "I closed the work.",
            "closures": [
                {
                    "target_handle": handle,
                    "status": "resolved",
                    "basis": "the work was completed",
                }
            ],
        }
    ).to_dict()

    closed = applier.apply_trace(
        close_trace,
        run_id=RUN_ID,
        cycle_id=2,
        result_record_id=_record_id(2),
    )
    open_items = memory.open_items(reason="after closure")
    operations = _ledger_operations(ledger)

    assert closed.status == "applied"
    assert open_items.ok
    assert open_items.data["items"] == []
    closure_operation = next(
        op for op in operations if op["operation_type"] == "apply_closure"
    )
    assert closure_operation["result_status"] == "applied"
    assert closure_operation["validated_parameters"]["target_handle"] == handle
    assert closure_operation["created_records"][0]["record_type"] == (
        "memory_attestation"
    )
    assert ledger.verify().ok


def test_schedule_requests_create_pending_events_only_through_ledger_and_dedupe(
    tmp_path,
):
    applier, _memory, ledger, events = _make_applier(tmp_path)
    raw = {
        "response": "I will resume later.",
        "schedule_requests": [
            {
                "purpose": "resume work",
                "requested_context": [
                    {"tool": "recall", "record_id": str(_record_id(1))}
                ],
                "not_before": "2026-06-10T12:00:00+00:00",
            }
        ],
    }
    trace = parse_autonomous_action(raw).to_dict()

    first = applier.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    second = applier.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    event_records = [
        record for record in events.read_records()
        if record.get("status") == "pending"
    ]
    operations = [
        op for op in _ledger_operations(ledger)
        if op["operation_type"] == "apply_schedule_request"
    ]

    assert first.status == "applied"
    assert second.status == "applied_with_refusals"
    assert len(event_records) == 1
    assert event_records[0]["audit_operation_id"] == (
        "cycle-1:apply-schedule-request:1"
    )
    assert event_records[0]["schedule_fingerprint"]
    assert operations[0]["result_status"] == "accepted"
    assert operations[0]["result"]["event_to_append"]["event_id"] == (
        event_records[0]["event_id"]
    )
    assert event_records[0]["audit_ledger_sequence"]
    assert event_records[0]["audit_ledger_record_hash"]
    applied_operation = next(
        op for op in operations
        if op["result_status"] == "applied"
    )
    assert applied_operation["created_records"] == [
        {"record_type": "event_status", "event_id": event_records[0]["event_id"]}
    ]
    no_op_operation = next(
        op for op in operations
        if op["result_status"] == "no_op"
    )
    assert no_op_operation["precondition_checks"][0]["name"] == (
        "duplicate_schedule_fingerprint_absent"
    )
    assert ledger.verify().ok


def test_tool_originated_schedule_events_are_refused_for_autonomy_runs(tmp_path):
    applier, _memory, ledger, events = _make_applier(tmp_path)
    tool_event = build_pending_event(
        purpose="legacy tool schedule",
        requested_context=[{"tool": "recall", "record_id": str(_record_id(1))}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=_record_id(1),
    )

    result = applier.apply_trace(
        parse_autonomous_action({"response": "No model schedule."}).to_dict(),
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
        tool_pending_events=[tool_event],
    )
    tool_refusals = [
        op for op in _ledger_operations(ledger)
        if op["operation_type"] == "refuse_tool_schedule_event"
    ]

    assert result.status == "applied_with_refusals"
    assert events.read_records() == []
    assert len(tool_refusals) == 1
    assert tool_refusals[0]["result_status"] == "refused"
    assert tool_refusals[0]["raw_parameters"]["pending_event"] == tool_event
    assert tool_refusals[0]["error"]["code"] == (
        "schedule_event_tool_disabled_for_autonomy"
    )
    assert ledger.verify().ok


def test_policy_action_appends_policy_disposition_when_source_event_is_available(
    tmp_path,
):
    applier, _memory, ledger, events = _make_applier(tmp_path)
    source_event = build_pending_event(
        purpose="wake for policy",
        requested_context=[{"tool": "recall", "record_id": str(_record_id(1))}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=_record_id(1),
    )
    events.append(source_event)

    result = applier.apply_trace(
        parse_autonomous_action(
            {"response": "This is complete.", "policy_action": "stop_complete"}
        ).to_dict(),
        run_id=RUN_ID,
        cycle_id=2,
        result_record_id=_record_id(2),
        event=source_event,
    )
    dispositions = [
        record for record in events.read_records()
        if record.get("record_type") == "policy_disposition"
    ]
    policy_operations = [
        op for op in _ledger_operations(ledger)
        if op["operation_type"] == "apply_policy_disposition"
    ]

    assert result.status == "applied"
    assert len(dispositions) == 1
    assert dispositions[0]["policy_action"] == "stop_complete"
    assert dispositions[0]["classification"] == "complete"
    assert policy_operations[0]["result_status"] == "applied"
    assert policy_operations[0]["created_records"] == [
        {
            "record_type": "policy_disposition",
            "disposition_id": dispositions[0]["disposition_id"],
        }
    ]
    assert ledger.verify().ok


def test_rejected_trace_logs_refusal_without_mutating_memory_or_events(tmp_path):
    applier, memory, ledger, events = _make_applier(tmp_path)
    trace = parse_autonomous_action(
        {"open_items": [{"kind": "todo", "text": "must not persist"}]}
    ).to_dict()

    result = applier.apply_trace(trace, run_id=RUN_ID, cycle_id=1)
    open_items = memory.open_items(reason="test rejected")
    operations = _ledger_operations(ledger)

    assert result.status == "rejected"
    assert open_items.ok
    assert open_items.data["items"] == []
    assert events.read_records() == []
    assert any(
        op["operation_type"] == "apply_open_item"
        and op["result_status"] == "refused"
        and op["error"]["code"] == "action_trace_rejected"
        for op in operations
    )
    assert not any(
        op["operation_type"] == "store_autonomous_action_record"
        for op in operations
    )
    assert ledger.verify().ok


def test_invalid_subactions_are_logged_but_not_applied(tmp_path):
    applier, _memory, ledger, events = _make_applier(tmp_path)
    trace = parse_autonomous_action(
        {
            "response": "The invalid schedule must not be inferred.",
            "schedule_requests": [
                {
                    "purpose": "bad context",
                    "requested_context": [
                        {
                            "tool": "recall",
                            "record_id": str(_record_id(1)),
                            "extra": "not allowed",
                        }
                    ],
                }
            ],
        }
    ).to_dict()

    result = applier.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    operations = _ledger_operations(ledger)

    assert trace["validation_status"] == "accepted_with_rejections"
    assert result.status == "applied"
    assert events.read_records() == []
    assert any(
        op["operation_type"] == "schedule_request"
        and op["result_status"] == "rejected"
        and op["error"]["layer"] == "validation"
        for op in operations
    )
    assert not any(
        op["operation_type"] == "apply_schedule_request"
        for op in operations
    )
    assert ledger.verify().ok


def test_live_equivalent_fake_run_opens_closes_schedules_and_stops_from_actions(
    tmp_path,
):
    applier, memory, ledger, events = _make_applier(tmp_path)
    cycle_1 = parse_autonomous_action(
        {
            "response": "I found work and will resume it.",
            "open_items": [{"kind": "todo", "text": "resolve boundary"}],
            "schedule_requests": [
                {
                    "purpose": "resume boundary work",
                    "requested_context": [
                        {"tool": "recall", "record_id": str(_record_id(1))}
                    ],
                }
            ],
        }
    ).to_dict()

    first = applier.apply_trace(
        cycle_1,
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    source_event = next(
        record for record in events.read_records()
        if record.get("status") == "pending"
    )
    handle = memory.open_items(reason="wake 2").data["items"][0]["handle"]
    cycle_2 = parse_autonomous_action(
        {
            "response": "The work is resolved; I can stop.",
            "closures": [
                {
                    "target_handle": handle,
                    "status": "resolved",
                    "basis": "boundary resolved in fake run",
                }
            ],
            "policy_action": "stop_complete",
        }
    ).to_dict()

    second = applier.apply_trace(
        cycle_2,
        run_id=RUN_ID,
        cycle_id=2,
        result_record_id=_record_id(2),
        event=source_event,
    )
    open_after = memory.open_items(reason="after fake run")
    records = events.read_records()
    operations = _ledger_operations(ledger)

    assert first.status == "applied"
    assert second.status == "applied"
    assert open_after.ok
    assert open_after.data["items"] == []
    assert any(record.get("status") == "pending" for record in records)
    assert any(
        record.get("record_type") == "policy_disposition"
        and record.get("policy_action") == "stop_complete"
        for record in records
    )
    assert {
        "store_autonomous_action_record",
        "apply_schedule_request",
        "apply_closure",
        "apply_policy_disposition",
    }.issubset({op["operation_type"] for op in operations})
    assert not any("rehearsal" in str(op).lower() for op in operations)
    assert ledger.verify().ok
