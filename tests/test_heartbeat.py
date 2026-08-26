"""Development tests for the heartbeat daemon.

Plan: docs/superpowers/plans/2026-08-26-heartbeat.md
Validating tests are authored separately by Codex per repo norm; these are
the implementer's TDD tests.
"""
from uuid import uuid4

from hamutay.events import EventStore, build_inbound_event
from hamutay.heartbeat import (
    recover_lost_continuations,
    recover_orphaned_running,
)


def _crashed_mid_wake(store):
    event = build_inbound_event(purpose="interrupted work", sender="tony")
    store.append(event)
    store.append_running(event)
    return event


def test_recover_orphaned_running_repends_original(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _crashed_mid_wake(store)
    recovered = recover_orphaned_running(store)
    assert len(recovered) == 1
    latest = store.latest_by_event_id()[event["event_id"]]
    assert latest["status"] == "pending"
    assert latest["purpose"] == "interrupted work"
    assert latest["recovered_by"] == "boot_recovery"
    assert latest["recovered_from_run_id"]


def test_recover_orphaned_running_is_idempotent(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _crashed_mid_wake(store)
    recover_orphaned_running(store)
    assert recover_orphaned_running(store) == []


def test_recover_orphaned_running_ignores_terminal_events(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="done work", sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
    )
    assert recover_orphaned_running(store) == []


def test_recover_lost_continuations_declares_the_loss(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="work", sender="tony")
    store.append(event)
    store.append_running(event)
    lost_id = str(uuid4())
    # Simulate the crash gap: completed record annotated, continuation
    # never appended (append_completed alone does exactly this).
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
        auto_continuation_event={"event_id": lost_id},
    )
    recovered = recover_lost_continuations(store)
    assert len(recovered) == 1
    replacement = store.latest_by_event_id()[lost_id]
    assert replacement["status"] == "pending"
    assert "declared_loss" in replacement
    assert replacement["recovered_by"] == "boot_recovery"
    assert recover_lost_continuations(store) == []
