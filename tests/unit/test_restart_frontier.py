from uuid import UUID

from hamutay.events import EventStore, build_pending_event
from hamutay.memory.action_application import AutonomousActionApplier
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.restart_frontier import RestartFrontierStore


RUN_ID = "run-phase-4"
RID_BASE = "50000000-0000-0000-0000-0000000000"


def _record_id(index: int) -> UUID:
    return UUID(f"{RID_BASE}{index:02d}")


def _raw_open_action(text: str = "continue this work") -> dict:
    return {
        "response": "I am carrying forward one item.",
        "open_items": [{"kind": "todo", "text": text}],
    }


def _raw_schedule_action() -> dict:
    return {
        "response": "I need a later wake.",
        "schedule_requests": [
            {
                "purpose": "resume scheduled work",
                "requested_context": [
                    {"tool": "recall", "record_id": str(_record_id(1))}
                ],
            }
        ],
    }


def _make_paths(tmp_path):
    return {
        "ledger": tmp_path / "actions.jsonl",
        "events": tmp_path / "events.jsonl",
        "frontier": tmp_path / "frontier.jsonl",
        "snapshot": tmp_path / "memory_snapshot.json",
    }


def _make_frontier(tmp_path):
    paths = _make_paths(tmp_path)
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths["ledger"])
    events = EventStore(paths["events"])
    frontier = RestartFrontierStore(
        frontier_path=paths["frontier"],
        memory_snapshot_path=paths["snapshot"],
    )
    frontier.ensure_run_manifest(
        ledger=ledger,
        run_id=RUN_ID,
        manifest={"model": "fake", "phase": 4},
        sandbox={"live_model_calls": False},
    )
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=0,
        result_record_id=None,
        memory=memory,
        ledger=ledger,
        event_store=events,
        notes={"boundary": "initial"},
    )
    return paths, memory, ledger, events, frontier


def _make_applier(memory, ledger, events):
    return AutonomousActionApplier(
        memory=memory,
        ledger=ledger,
        event_store=events,
        instance_id="restart-test",
    )


def _ledger_operations(ledger: ActionLedger) -> list[dict]:
    return [
        record["payload"]
        for record in ledger.read_records()
        if record["record_type"] == "operation"
    ]


def _reload(paths, *, run_id=RUN_ID):
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths["ledger"])
    events = EventStore(paths["events"])
    frontier = RestartFrontierStore(
        frontier_path=paths["frontier"],
        memory_snapshot_path=paths["snapshot"],
    )
    loaded = frontier.load_latest(
        run_id=run_id,
        memory=memory,
        ledger=ledger,
        event_store=events,
    )
    return memory, ledger, events, frontier, loaded


def test_run_manifest_and_completion_frontier_are_persisted_and_reloaded(tmp_path):
    paths, memory, ledger, events, frontier = _make_frontier(tmp_path)
    applier = _make_applier(memory, ledger, events)
    result = applier.apply_trace(
        parse_autonomous_action(_raw_open_action("persist me")).to_dict(),
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    committed = frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=result.result_record_id,
        memory=memory,
        ledger=ledger,
        event_store=events,
        notes={"boundary": "after completion"},
    )

    reloaded_memory, reloaded_ledger, _events, _frontier, loaded = _reload(paths)
    open_items = reloaded_memory.open_items(reason="resume check")
    manifests = [
        record for record in reloaded_ledger.read_records()
        if record["record_type"] == "run_manifest"
    ]

    assert committed.next_cycle_id == 2
    assert loaded.frontier is not None
    assert loaded.frontier.result_record_id == result.result_record_id
    assert loaded.frontier.ledger_sequence == committed.ledger_sequence
    assert loaded.ledger_verification.ok
    assert loaded.ignored_ledger_records == []
    assert len(manifests) == 1
    assert open_items.ok
    assert open_items.data["items"][0]["item"]["text"] == "persist me"


def test_interruption_before_parse_retries_from_prior_frontier(tmp_path):
    paths, _memory, ledger, _events, _frontier = _make_frontier(tmp_path)

    reloaded_memory, reloaded_ledger, events, frontier, loaded = _reload(paths)
    applier = _make_applier(reloaded_memory, reloaded_ledger, events)
    result = applier.apply_trace(
        parse_autonomous_action(_raw_open_action("after before-parse retry")).to_dict(),
        run_id=RUN_ID,
        cycle_id=loaded.frontier.next_cycle_id,
        result_record_id=_record_id(1),
    )
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=result.result_record_id,
        memory=reloaded_memory,
        ledger=reloaded_ledger,
        event_store=events,
    )
    open_items = reloaded_memory.open_items(reason="retry result")

    assert ledger.verify().ok
    assert loaded.frontier.cycle_id == 0
    assert open_items.data["items"][0]["item"]["text"] == (
        "after before-parse retry"
    )
    assert len([
        op for op in _ledger_operations(reloaded_ledger)
        if op["operation_type"] == "store_autonomous_action_record"
        and op["result_status"] == "applied"
    ]) == 1


def test_interruption_after_parse_preserves_audit_but_not_state(tmp_path):
    paths, _memory, ledger, _events, _frontier = _make_frontier(tmp_path)
    trace = parse_autonomous_action(_raw_open_action("after parse")).to_dict()
    ledger.append_action_trace(run_id=RUN_ID, cycle_id=1, trace=trace)
    ledger.append_validation_operations(run_id=RUN_ID, cycle_id=1, trace=trace)

    reloaded_memory, reloaded_ledger, events, frontier, loaded = _reload(paths)
    assert reloaded_memory.open_items(reason="after parse crash").data["items"] == []
    assert {record["record_type"] for record in loaded.ignored_ledger_records} == {
        "action_trace",
        "operation",
    }

    applier = _make_applier(reloaded_memory, reloaded_ledger, events)
    result = applier.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=loaded.frontier.next_cycle_id,
        result_record_id=_record_id(1),
    )
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=result.result_record_id,
        memory=reloaded_memory,
        ledger=reloaded_ledger,
        event_store=events,
    )

    assert reloaded_memory.open_items(reason="after retry").data["items"][0][
        "item"
    ]["text"] == "after parse"
    assert len([
        op for op in _ledger_operations(reloaded_ledger)
        if op["operation_type"] == "store_autonomous_action_record"
        and op["result_status"] == "applied"
    ]) == 1


def test_interruption_after_memory_write_discards_uncommitted_state_on_resume(
    tmp_path,
):
    paths, memory, ledger, events, _frontier = _make_frontier(tmp_path)
    applier = _make_applier(memory, ledger, events)
    trace = parse_autonomous_action(_raw_open_action("uncommitted write")).to_dict()
    applier.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    assert memory.open_items(reason="before crash").data["items"]

    reloaded_memory, reloaded_ledger, reloaded_events, frontier, loaded = _reload(paths)
    assert reloaded_memory.open_items(reason="after load").data["items"] == []
    assert any(
        record.get("payload", {}).get("operation_type")
        == "store_autonomous_action_record"
        for record in loaded.ignored_ledger_records
    )

    retry = _make_applier(reloaded_memory, reloaded_ledger, reloaded_events)
    result = retry.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=loaded.frontier.next_cycle_id,
        result_record_id=_record_id(1),
    )
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=result.result_record_id,
        memory=reloaded_memory,
        ledger=reloaded_ledger,
        event_store=reloaded_events,
    )
    open_items = reloaded_memory.open_items(reason="after retry")

    assert len(open_items.data["items"]) == 1
    assert open_items.data["items"][0]["item"]["text"] == "uncommitted write"


def test_interruption_after_event_claim_restores_event_to_pending(tmp_path):
    paths, memory, ledger, events, frontier = _make_frontier(tmp_path)
    pending = build_pending_event(
        purpose="claimed before crash",
        requested_context=[{"tool": "recall", "record_id": str(_record_id(1))}],
        scheduled_by_cycle=0,
        scheduled_by_record_id=_record_id(1),
    )
    events.append(pending)
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=0,
        result_record_id=None,
        memory=memory,
        ledger=ledger,
        event_store=events,
        notes={"boundary": "event pending"},
    )
    claimed = events.claim_next_pending(run_id=UUID(int=1))
    assert claimed is not None
    _event, running = claimed
    assert running["status"] == "running"

    _memory, _ledger, reloaded_events, _frontier, loaded = _reload(
        paths,
        run_id=str(UUID(int=1)),
    )
    latest = reloaded_events.latest_by_event_id()[pending["event_id"]]
    next_pending = reloaded_events.next_pending()

    assert len(loaded.recovered_event_records) == 1
    assert latest["status"] == "pending"
    assert latest["purpose"] == "claimed before crash"
    assert next_pending is not None
    assert next_pending["event_id"] == pending["event_id"]


def test_uncommitted_scheduled_event_is_suppressed_on_resume(tmp_path):
    paths, memory, ledger, events, _frontier = _make_frontier(tmp_path)
    applier = _make_applier(memory, ledger, events)
    applier.apply_trace(
        parse_autonomous_action(_raw_schedule_action()).to_dict(),
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    assert events.next_pending() is not None

    _memory, _ledger, reloaded_events, _frontier, loaded = _reload(paths)
    records = reloaded_events.read_records()
    latest = reloaded_events.latest_by_event_id()

    assert len(loaded.suppressed_event_records) == 1
    assert reloaded_events.next_pending() is None
    assert any(record.get("status") == "suppressed" for record in records)
    assert next(iter(latest.values()))["status"] == "suppressed"


def test_resume_after_completion_uses_new_frontier_not_prior_boundary(tmp_path):
    paths, memory, ledger, events, frontier = _make_frontier(tmp_path)
    applier = _make_applier(memory, ledger, events)
    trace = parse_autonomous_action(_raw_open_action("completed frontier")).to_dict()
    result = applier.apply_trace(
        trace,
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=_record_id(1),
    )
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=1,
        result_record_id=result.result_record_id,
        memory=memory,
        ledger=ledger,
        event_store=events,
    )

    reloaded_memory, _ledger, _events, _frontier, loaded = _reload(paths)
    open_items = reloaded_memory.open_items(reason="completed load")

    assert loaded.frontier.cycle_id == 1
    assert loaded.frontier.next_cycle_id == 2
    assert loaded.ignored_ledger_records == []
    assert len(open_items.data["items"]) == 1
    assert open_items.data["items"][0]["item"]["text"] == "completed frontier"
