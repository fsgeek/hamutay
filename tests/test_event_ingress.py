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
