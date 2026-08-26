"""Development tests for the heartbeat's event-store ingress surface.

Plan: docs/superpowers/plans/2026-08-26-heartbeat.md
Validating tests are authored separately by Codex per repo norm; these are
the implementer's TDD tests.
"""
from hamutay.events import build_parser


def test_run_next_defaults_to_64000_max_tokens():
    args = build_parser().parse_args(["run-next", "--log-path", "x.jsonl"])
    assert args.max_tokens == 64000


def test_run_all_defaults_to_64000_max_tokens():
    args = build_parser().parse_args(["run-all", "--log-path", "x.jsonl"])
    assert args.max_tokens == 64000


import pytest

from hamutay.events import (
    EVENT_TYPE_INBOUND,
    EventStore,
    build_inbound_event,
)


def test_build_inbound_event_shape():
    record = build_inbound_event(purpose="hello resident", sender="tony")
    assert record["record_type"] == "event_status"
    assert record["event_type"] == EVENT_TYPE_INBOUND
    assert record["status"] == "pending"
    assert record["origin"] == "external"
    assert record["sender"] == "tony"
    assert record["purpose"] == "hello resident"
    assert record["event_id"]
    assert record["created_at"]
    assert "scheduled_by_cycle" not in record


def test_build_inbound_event_requires_purpose_and_sender():
    with pytest.raises(ValueError):
        build_inbound_event(purpose="   ", sender="tony")
    with pytest.raises(ValueError):
        build_inbound_event(purpose="hi", sender="")


def test_inbound_event_is_claimable(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    record = build_inbound_event(purpose="hello", sender="tony")
    store.append(record)
    claimable = store.next_pending()
    assert claimable is not None
    assert claimable["event_id"] == record["event_id"]


def test_inbound_event_honors_not_before(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    record = build_inbound_event(
        purpose="later", sender="tony", not_before="2999-01-01T00:00:00Z"
    )
    store.append(record)
    assert store.next_pending() is None


from uuid import uuid4 as _uuid4

from hamutay.events import build_pending_event


def _pending(store):
    record = build_inbound_event(purpose="work", sender="tony")
    store.append(record)
    return record


def test_append_completed_atomic_persists_both_records(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _pending(store)
    continuation = build_pending_event(
        purpose="continue the work",
        requested_context=[{"tool": "recall", "record_id": str(_uuid4())}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=_uuid4(),
    )
    completed = store.append_completed_atomic(
        event=event,
        run_id=str(_uuid4()),
        wake_cycle=1,
        result_record_id=_uuid4(),
        response_text="done",
        auto_continuation_event=continuation,
    )
    latest = store.latest_by_event_id()
    assert latest[event["event_id"]]["status"] == "completed"
    assert latest[continuation["event_id"]]["status"] == "pending"
    assert completed["auto_continuation_appended"] is True
    assert completed["auto_continuation_event_id"] == continuation["event_id"]


def test_append_completed_atomic_without_continuation(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _pending(store)
    store.append_completed_atomic(
        event=event,
        run_id=str(_uuid4()),
        wake_cycle=1,
        result_record_id=_uuid4(),
        response_text="done",
    )
    latest = store.latest_by_event_id()
    assert latest[event["event_id"]]["status"] == "completed"
    assert "auto_continuation_appended" not in latest[event["event_id"]]


def test_append_many_writes_batch_as_single_payload(tmp_path):
    """The batch must land as one write: all lines present and well-formed."""
    import json as _json

    store = EventStore(str(tmp_path / "events.jsonl"))
    records = [
        build_inbound_event(purpose=f"batch {i}", sender="tony")
        for i in range(3)
    ]
    store.append_many(records)
    lines = (tmp_path / "events.jsonl").read_text().splitlines()
    assert len(lines) == 3
    assert [_json.loads(line)["purpose"] for line in lines] == [
        "batch 0",
        "batch 1",
        "batch 2",
    ]


def test_send_subcommand_appends_to_store(tmp_path):
    from hamutay.events import _handle_send, default_event_log_path

    log_path = tmp_path / "session.jsonl"
    args = build_parser().parse_args(
        [
            "send",
            "--log-path",
            str(log_path),
            "--message",
            "first tick",
            "--sender",
            "tony",
        ]
    )
    written = _handle_send(args)
    store = EventStore(str(default_event_log_path(str(log_path))))
    latest = store.latest_by_event_id()
    assert written["event_id"] in latest
    assert latest[written["event_id"]]["purpose"] == "first tick"
