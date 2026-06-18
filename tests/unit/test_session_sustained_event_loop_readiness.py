from __future__ import annotations

import json

from uuid import UUID

from hamutay.events import (
    EventStore,
    build_pending_event,
    summarize_event_log,
    run_next_event,
)
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.restart_frontier import RestartFrontierStore
from hamutay.taste_open import ExchangeResult, OpenTasteSession


RUN_ID = "70000000-0000-0000-0000-000000000001"
NOW = "2026-06-08T12:00:00+00:00"


class SequenceBackend:
    def __init__(self, outputs: list[dict]):
        self._outputs = list(outputs)
        self.calls: list[dict] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "experiment_label": experiment_label,
                "extra_tools": extra_tools,
                "tool_executor": tool_executor,
            }
        )
        if not self._outputs:
            raise RuntimeError("no fake session output remaining")
        return ExchangeResult(raw_output=self._outputs.pop(0))


def continuation_request() -> dict:
    return {
        "requested": True,
        "kind": "session_bound_continuation",
        "purpose": "Continue the inbound IPC work from <result_record_id>.",
        "requested_context": [
            {
                "tool": "recall",
                "record_id": "<result_record_id>",
                "field": "inbound_status",
            }
        ],
        "label": "session-bound-continuation",
    }


def housekeeping_output(index: int) -> dict:
    return {
        "response": f"housekeeping audit {index} complete",
        "open_items": [],
        "housekeeping_audit": {
            "audit_index": index,
            "open_item_count": 0,
            "status": "clean",
        },
    }


def make_session(tmp_path, backend, *, resume: bool = False) -> OpenTasteSession:
    return OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "session.jsonl"),
        event_log_path=str(tmp_path / "session.events.jsonl"),
        experiment_label="session_sustained_event_loop_readiness",
        memory_base_probability=0,
        enable_tools=False,
        project_root=tmp_path,
        resume=resume,
    )


def append_event(
    store: EventStore,
    session: OpenTasteSession,
    *,
    event_type: str,
    label: str,
    purpose: str,
) -> dict:
    cycle, record_id, _state, _timestamp = session._prior_states[-1]
    event = build_pending_event(
        purpose=purpose,
        requested_context=[{"tool": "recall", "cycle": cycle}],
        scheduled_by_cycle=cycle,
        scheduled_by_record_id=record_id,
        label=label,
        not_before=NOW,
    )
    event["event_type"] = event_type
    store.append(event)
    return event


def mirror_session_state(memory: LocalMemorySubstrate, session: OpenTasteSession) -> str:
    cycle, record_id, state, _timestamp = session._prior_states[-1]
    stored = memory.store_episode(
        record_id=record_id,
        record_type="open_taste_cycle",
        content=state,
        production={
            "who": {"instance": "open-taste-session"},
            "what": {"artifact": "open_taste_cycle"},
            "when": {"cycle": cycle},
            "where": {"project": "hamutay"},
        },
        execution_trace={"tool_path": "session_sustained_event_loop_readiness"},
    )
    if (
        not stored.ok
        and stored.error is not None
        and stored.error.code != "duplicate_record"
    ):
        raise AssertionError(stored.to_dict())
    return str(record_id)


def commit_frontier(
    *,
    frontier: RestartFrontierStore,
    memory: LocalMemorySubstrate,
    ledger: ActionLedger,
    store: EventStore,
    session: OpenTasteSession,
    notes: dict,
) -> None:
    result_record_id = mirror_session_state(memory, session)
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=session.cycle,
        result_record_id=result_record_id,
        memory=memory,
        ledger=ledger,
        event_store=store,
        notes=notes,
    )


def event_histories(store: EventStore) -> dict[str, list[str]]:
    histories: dict[str, list[str]] = {}
    for record in store.read_records():
        event_id = record.get("event_id")
        if event_id:
            histories.setdefault(str(event_id), []).append(str(record.get("status")))
    return histories


def completed_events(store: EventStore) -> list[dict]:
    return [
        record for record in store.read_records()
        if record.get("status") == "completed"
    ]


def test_open_taste_session_sustained_mixed_stream_resumes_after_claim(tmp_path):
    initial_backend = SequenceBackend(
        [
            {"response": "seed ready", "open_items": []},
            {
                "response": "accepted inbound IPC work",
                "open_items": [{"kind": "todo", "text": "finish inbound work"}],
                "inbound_status": "accepted",
                "continuation_request": continuation_request(),
                "policy_decision": {
                    "action": "continue_after",
                    "rationale": "a bound continuation should finish the work",
                },
            },
            {
                "response": "finished bound continuation",
                "open_items": [],
                "continuation_status": "closed",
            },
            housekeeping_output(1),
            housekeeping_output(2),
        ]
    )
    session = make_session(tmp_path, initial_backend)
    store = EventStore(tmp_path / "session.events.jsonl")
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(tmp_path / "session.actions.jsonl")
    frontier = RestartFrontierStore(
        frontier_path=tmp_path / "session.restart_frontier.jsonl",
        memory_snapshot_path=tmp_path / "session.memory_snapshot.json",
    )
    frontier.ensure_run_manifest(
        ledger=ledger,
        run_id=RUN_ID,
        manifest={
            "rehearsal": "open_taste_session_sustained_mixed_event_loop",
            "live_model_calls": False,
        },
        sandbox={"network": "disabled", "shell": "disabled"},
    )

    session.exchange("seed the sustained event-loop instance")
    commit_frontier(
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        notes={"boundary": "seed"},
    )
    append_event(
        store,
        session,
        event_type="inbound_message",
        label="inbound-ipc",
        purpose="Handle inbound IPC message.",
    )

    inbound_result = run_next_event(
        session,
        store,
        auto_continuations=True,
        policy_dispositions=True,
    )
    commit_frontier(
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        notes={"boundary": "after inbound event"},
    )
    continuation = inbound_result["auto_continuation_event"]
    assert continuation["bound_by"] == "continuation_request"
    assert continuation["bound_source_event_id"] == inbound_result["event_id"]
    assert continuation["scheduled_by_record_id"] == inbound_result["result_record_id"]

    run_next_event(session, store, auto_continuations=True)
    commit_frontier(
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        notes={"boundary": "after self-scheduled continuation"},
    )

    for index in range(1, 3):
        append_event(
            store,
            session,
            event_type="housekeeping",
            label=f"housekeeping-{index}",
            purpose=f"Run housekeeping audit {index}.",
        )
        run_next_event(session, store)
        commit_frontier(
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            notes={"boundary": f"after housekeeping {index}"},
        )

    append_event(
        store,
        session,
        event_type="housekeeping",
        label="housekeeping-3",
        purpose="Run housekeeping audit 3.",
    )
    commit_frontier(
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        notes={"boundary": "before interrupted housekeeping claim"},
    )
    claimed = store.claim_next_pending(run_id=UUID(RUN_ID))
    assert claimed is not None
    assert claimed[1]["status"] == "running"

    resumed_memory = LocalMemorySubstrate()
    resumed_ledger = ActionLedger(tmp_path / "session.actions.jsonl")
    resumed_frontier = RestartFrontierStore(
        frontier_path=tmp_path / "session.restart_frontier.jsonl",
        memory_snapshot_path=tmp_path / "session.memory_snapshot.json",
    )
    load = resumed_frontier.load_latest(
        run_id=RUN_ID,
        memory=resumed_memory,
        ledger=resumed_ledger,
        event_store=store,
    )
    assert len(load.recovered_event_records) == 1
    assert load.recovered_event_records[0]["event_type"] == "housekeeping"

    resumed_backend = SequenceBackend([housekeeping_output(i) for i in range(3, 9)])
    resumed = make_session(tmp_path, resumed_backend, resume=True)

    for index in range(3, 9):
        run_next_event(resumed, store)
        commit_frontier(
            frontier=resumed_frontier,
            memory=resumed_memory,
            ledger=resumed_ledger,
            store=store,
            session=resumed,
            notes={"boundary": f"after resumed housekeeping {index}"},
        )
        if index < 8:
            append_event(
                store,
                resumed,
                event_type="housekeeping",
                label=f"housekeeping-{index + 1}",
                purpose=f"Run housekeeping audit {index + 1}.",
            )

    summary = summarize_event_log(store.read_records())
    completions = completed_events(store)
    completed_types = [record.get("event_type") for record in completions]
    histories = event_histories(store)
    session_record_ids = {
        str(record.get("record_id"))
        for record in map(
            json.loads,
            (tmp_path / "session.jsonl").read_text().splitlines(),
        )
        if record.get("record_id")
    }

    assert resumed.cycle == 11
    assert resumed.state["open_items"] == []
    assert resumed.state["housekeeping_audit"] == {
        "audit_index": 8,
        "open_item_count": 0,
        "status": "clean",
    }
    assert summary["status_counts"] == {"completed": 10}
    assert summary["pending_runnable_count"] == 0
    assert summary["lifecycle_anomalies"] == []
    assert completed_types == [
        "inbound_message",
        "self_scheduled_reflection",
        "housekeeping",
        "housekeeping",
        "housekeeping",
        "housekeeping",
        "housekeeping",
        "housekeeping",
        "housekeeping",
        "housekeeping",
    ]
    assert all(record.get("event_id") for record in completions)
    assert all(record.get("result_record_id") in session_record_ids for record in completions)
    assert any(
        statuses == ["pending", "running", "pending", "running", "completed"]
        for statuses in histories.values()
    )
