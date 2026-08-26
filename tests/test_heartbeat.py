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


def test_heartbeat_status_record_shape(tmp_path):
    from hamutay.heartbeat import append_heartbeat_status

    store = EventStore(str(tmp_path / "events.jsonl"))
    record = append_heartbeat_status(
        store, status="quiet", reason="chosen_quiet", detail={"note": "test"}
    )
    assert record["record_type"] == "heartbeat_status"
    assert record["status"] == "quiet"
    assert record["reason"] == "chosen_quiet"
    assert record["created_at"]
    assert "event_id" not in record
    persisted = store.read_records()
    assert persisted[-1]["record_type"] == "heartbeat_status"


def test_heartbeat_status_does_not_disturb_the_queue(tmp_path):
    from hamutay.heartbeat import append_heartbeat_status

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="real work", sender="tony")
    store.append(event)
    append_heartbeat_status(store, status="active", reason="runnable_pending")
    claimable = store.next_pending()
    assert claimable is not None
    assert claimable["event_id"] == event["event_id"]


def test_derive_quiet_reason_awaiting_first_event(tmp_path):
    from hamutay.heartbeat import derive_quiet_reason

    store = EventStore(str(tmp_path / "events.jsonl"))
    assert derive_quiet_reason(store.read_records()) == "awaiting_first_event"


def test_derive_quiet_reason_starved_on_expiry(tmp_path):
    from hamutay.heartbeat import derive_quiet_reason

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(event)
    store.append_expired(event)
    assert derive_quiet_reason(store.read_records()) == "starved_expired"


def test_derive_quiet_reason_chosen_after_clean_completion(tmp_path):
    from hamutay.heartbeat import derive_quiet_reason

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="work", sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done, resting",
    )
    assert derive_quiet_reason(store.read_records()) == "chosen_quiet"


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
