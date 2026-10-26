"""Persisted outcomes from Change 2–5, using real JSONL stores and a fixed clock.

The spec does not define the new method's return value or a clock argument.
Inspect persisted rows and freeze the existing module clock instead.
"""

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from hamutay import events
from hamutay.context_policy import ContextPolicy
from hamutay.window import ExhaustedBeforeRequest


NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
CREATED = NOW - timedelta(days=1)
ERROR = "OpenAI backend error: {'error': {'code': 429, 'message': 'rate limited'}}"


@pytest.fixture
def clock(monkeypatch):
    clock = SimpleNamespace(now=NOW)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.now.astimezone(tz) if tz else clock.now.replace(tzinfo=None)

    monkeypatch.setattr(events, "datetime", FixedDatetime)
    monkeypatch.setattr(events, "utc_now_iso", lambda: clock.now.isoformat())
    return clock


def pending(store, *, kind="inbound", created=CREATED, **fields):
    if kind == "inbound":
        event = events.build_inbound_event(
            purpose="A knock that must survive provider trouble", sender="validation",
            label="transient-deferral", **fields,
        )
    else:
        event = events.build_pending_event(
            purpose="A reflection that must survive provider trouble",
            requested_context=[{"tool": "recall", "cycle": 7}], scheduled_by_cycle=7,
            scheduled_by_record_id=UUID(int=7), label="transient-deferral", **fields,
        )
    event["created_at"] = created.isoformat()
    event["detail"] = {"validation_marker": "preserve this detail"}
    store.append(event)
    return event


def defer(store, event, run_id="failed-run", **fields):
    store.append_failed_with_deferral(
        event=event, run_id=run_id, exc=RuntimeError(ERROR), **fields,
    )


def persisted(store):
    return events.EventStore(store.path).read_records()


def at(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.mark.parametrize("kind", ["inbound", "reflection"])
def test_first_deferral_preserves_event_and_failed_run_fields(tmp_path, clock, kind):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store, kind=kind)
    original = deepcopy(event)
    running = store.append_running(event)
    context_results = [{"request": {"tool": "recall", "cycle": 7}, "result": {"text": "full evidence"}}]
    admission = {"passes": 2, "validation_marker": "full admission"}

    defer(store, event, running["run_id"], context_results=context_results, admission=admission)

    rows = persisted(store)
    assert [row["status"] for row in rows] == ["pending", "running", "failed", "pending"]
    failed, retry = rows[-2:]
    assert failed["record_type"] == "event_status"
    assert failed["event_id"] == event["event_id"]
    assert failed["event_type"] == event["event_type"]
    assert failed["run_id"] == running["run_id"]
    assert at(failed["failed_at"]) == NOW
    assert failed["error_type"] == "RuntimeError"
    assert failed["error"] == ERROR
    assert failed["context_results"] == context_results
    assert failed["admission"] == admission
    assert failed["detail"]["transient"] is True
    assert at(failed["detail"]["retry_at"]) == NOW + timedelta(minutes=5)
    for key, value in original.items():
        if key != "detail":
            assert retry[key] == value
    assert retry["detail"]["validation_marker"] == "preserve this detail"
    assert retry["detail"]["transient_retry"] == 1
    assert retry["detail"]["retry_of_run"] == running["run_id"]
    assert at(retry["not_before"]) == NOW + timedelta(minutes=5)
    assert "run_id" not in retry and "started_at" not in retry
    assert event == original


def test_next_pending_obeys_retry_time_boundary(tmp_path, clock):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store)
    defer(store, event)
    due = NOW + timedelta(minutes=5)

    assert store.next_pending(now=due - timedelta(microseconds=1)) is None
    assert store.next_pending(now=due)["event_id"] == event["event_id"]
    assert store.next_pending(now=due + timedelta(microseconds=1))["event_id"] == event["event_id"]


def test_due_retry_keeps_original_queue_position(tmp_path, clock):
    store = events.EventStore(tmp_path / "events.jsonl")
    original = pending(store)
    behind = pending(store, created=CREATED + timedelta(minutes=1))
    defer(store, original)

    assert store.next_pending(now=NOW)["event_id"] == behind["event_id"]
    assert store.next_pending(now=NOW + timedelta(minutes=5))["event_id"] == original["event_id"]


@pytest.mark.parametrize("reopen", [False, True], ids=["same-store", "restart-every-run"])
def test_backoff_sequence_and_ninth_failure_cap(tmp_path, clock, reopen):
    store = events.EventStore(tmp_path / "events.jsonl")
    original = pending(store)

    for k, delay_minutes in enumerate([5, 10, 20, 40, 80, 160, 320, 360], start=1):
        if reopen:
            store = events.EventStore(store.path)
        event, running = store.claim_next_pending(now=clock.now)
        before = len(persisted(store))
        defer(store, event, running["run_id"])
        rows = persisted(store)
        assert len(rows) == before + 2
        failed, retry = rows[-2:]
        due = clock.now + timedelta(minutes=delay_minutes)
        assert failed["status"] == "failed"
        assert failed["detail"]["transient"] is True
        assert at(failed["detail"]["retry_at"]) == due
        assert retry["status"] == "pending"
        assert retry["event_id"] == original["event_id"]
        assert retry["created_at"] == original["created_at"]
        assert retry["detail"]["transient_retry"] == k
        assert retry["detail"]["retry_of_run"] == running["run_id"]
        assert at(retry["not_before"]) == due
        assert store.next_pending(now=due - timedelta(microseconds=1)) is None
        clock.now = due

    store = events.EventStore(store.path)
    event, running = store.claim_next_pending(now=clock.now)
    before = len(persisted(store))
    defer(store, event, running["run_id"])
    rows = persisted(store)
    assert len(rows) == before + 1
    failed = rows[-1]
    assert failed["status"] == "failed"
    assert failed["detail"]["transient"] is True
    assert failed["detail"]["retry_cap_reached"] is True
    assert "retry_at" not in failed["detail"]
    assert store.latest_by_event_id()[original["event_id"]] == failed
    assert store.next_pending(now=clock.now + timedelta(days=30)) is None


def test_retry_count_uses_own_history_not_marker_value_or_other_events(tmp_path, clock):
    """Change 3, lines 47–48 says count rows, rather than trust their marker values."""
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store)
    previous = {**event, "detail": {"transient_retry": 80}}
    store.append(previous)
    other = pending(store, created=CREATED + timedelta(minutes=1))
    for k in range(1, 9):
        store.append({**other, "detail": {"transient_retry": k}})
    store = events.EventStore(store.path)
    before = len(persisted(store))

    # Passing the original record also guards against using only event.detail.
    defer(store, event)

    rows = persisted(store)
    assert len(rows) == before + 2, "One earlier retry row must permit a second deferral"
    failed, retry = rows[-2:]
    assert retry["event_id"] == event["event_id"]
    assert retry["detail"]["transient_retry"] == 2
    assert at(retry["not_before"]) == NOW + timedelta(minutes=10)
    assert at(failed["detail"]["retry_at"]) == NOW + timedelta(minutes=10)


@pytest.mark.parametrize("expiry_seconds", [299, 300], ids=["before-retry", "exactly-at-retry"])
def test_expiry_at_or_before_retry_prevents_pending_copy(tmp_path, clock, expiry_seconds):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store, expires_at=(NOW + timedelta(seconds=expiry_seconds)).isoformat())
    before = len(persisted(store))

    defer(store, event)

    rows = persisted(store)
    assert len(rows) == before + 1
    failed = rows[-1]
    assert failed["status"] == "failed"
    assert failed["event_id"] == event["event_id"]
    assert failed["detail"]["transient"] is True
    assert failed["detail"]["retry_after_expiry"] is True
    assert store.next_pending(now=NOW) is None


def test_expiry_just_after_retry_allows_pending_copy(tmp_path, clock):
    store = events.EventStore(tmp_path / "events.jsonl")
    due = NOW + timedelta(minutes=5)
    event = pending(store, expires_at=(due + timedelta(microseconds=1)).isoformat())

    defer(store, event)

    failed, retry = persisted(store)[-2:]
    assert failed["status"] == "failed"
    assert retry["status"] == "pending"
    assert retry["expires_at"] == event["expires_at"]
    assert store.next_pending(now=due)["event_id"] == event["event_id"]


def test_failed_and_pending_are_written_in_one_buffer_under_one_lock(tmp_path, clock, monkeypatch):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store)
    real_lock, real_write = store._locked, store._write_lines_unlocked
    depth = 0
    entries = []
    writes = []

    @contextmanager
    def observed_lock():
        nonlocal depth
        with real_lock():
            entries.append(True)
            depth += 1
            try:
                yield
            finally:
                depth -= 1

    def observed_write(lines):
        writes.append((depth, [json.loads(line) for line in lines]))
        return real_write(lines)

    monkeypatch.setattr(store, "_locked", observed_lock)
    monkeypatch.setattr(store, "_write_lines_unlocked", observed_write)

    defer(store, event)

    assert len(entries) == 1
    assert len(writes) == 1
    assert writes[0][0] == 1
    assert [row["status"] for row in writes[0][1]] == ["failed", "pending"]
    assert persisted(store)[-2:] == writes[0][1]


class FailingSession:
    def __init__(self, exc, *, window_aware=False):
        self.exc = exc
        self._prior_states = []
        self._bridge = None
        self._state = {}
        self.cycle = 1
        self._last_admission = {"passes": 1, "validation_marker": "runner admission"}
        self.context_policy = (
            ContextPolicy(65536, "discovered", 65536, "http://tokenizer.invalid", "probed", {}, 20)
            if window_aware else ContextPolicy.none()
        )
        self.compact_calls = []

    def exchange(self, message, **kwargs):
        self.compact_calls.append(kwargs["compact"])
        raise self.exc


@pytest.mark.parametrize("message", [
    ERROR,
    "OpenAI backend transport failed after retries",
    "anthropic-direct error 529: overloaded",
    "anthropic-direct transport failed",
])
def test_runner_reraises_and_defers_only_claimed_event(tmp_path, clock, message):
    store = events.EventStore(tmp_path / "events.jsonl")
    first = pending(store)
    behind = pending(store, created=CREATED + timedelta(minutes=1))
    exc = RuntimeError(message)
    session = FailingSession(exc)

    with pytest.raises(RuntimeError) as caught:
        events.run_next_event(session, store, now=NOW)

    assert caught.value is exc
    rows = persisted(store)
    assert [row["status"] for row in rows] == ["pending", "pending", "running", "failed", "pending"]
    running, failed, retry = rows[-3:]
    assert failed["event_id"] == first["event_id"]
    assert failed["run_id"] == running["run_id"]
    assert failed["error"] == message
    assert failed["context_results"] == []
    assert failed["admission"] == session._last_admission
    assert failed["detail"]["transient"] is True
    assert at(failed["detail"]["retry_at"]) == NOW + timedelta(minutes=5)
    assert retry["event_id"] == first["event_id"]
    assert retry["created_at"] == first["created_at"]
    assert retry["detail"]["transient_retry"] == 1
    assert retry["detail"]["retry_of_run"] == running["run_id"]
    assert at(retry["not_before"]) == NOW + timedelta(minutes=5)
    assert [row for row in rows if row["event_id"] == behind["event_id"]] == [behind]
    assert store.next_pending(now=NOW)["event_id"] == behind["event_id"]


@pytest.mark.parametrize("message", [
    "OpenAI backend error: {'error': {'code': 401}}",
    "anthropic-direct error 413: too large",
    "ReadTimeout after 300 seconds (not retried ...)",
    "malformed JSON arguments",
    "plain application failure",
])
def test_runner_non_transient_failure_remains_terminal(tmp_path, clock, message):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store)
    exc = RuntimeError(message)

    with pytest.raises(RuntimeError) as caught:
        events.run_next_event(FailingSession(exc), store, now=NOW)

    assert caught.value is exc
    rows = persisted(store)
    assert [row["status"] for row in rows] == ["pending", "running", "failed"]
    assert rows[-1]["event_id"] == event["event_id"]
    assert rows[-1]["error"] == message
    assert not rows[-1].get("detail", {}).get("transient", False)
    assert store.next_pending(now=NOW + timedelta(days=30)) is None


def test_window_failure_still_gets_one_compact_retry(tmp_path, clock):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store)
    exc = ExhaustedBeforeRequest(prompt_tokens=65000, limit=65536, room=535, max_tokens=535)
    session = FailingSession(exc, window_aware=True)

    with pytest.raises(ExhaustedBeforeRequest) as caught:
        events.run_next_event(session, store, now=NOW)
    assert caught.value is exc
    rows = persisted(store)
    assert [row["status"] for row in rows] == ["pending", "running", "failed", "pending"]
    failed, retry = rows[-2:]
    assert retry["event_id"] == event["event_id"]
    assert retry["detail"]["compact_context"] is True
    assert retry["detail"]["retry_of_run"] == failed["run_id"]
    assert "transient_retry" not in retry["detail"]
    assert not failed.get("detail", {}).get("transient", False)
    assert store.next_pending(now=NOW)["event_id"] == event["event_id"]

    with pytest.raises(ExhaustedBeforeRequest):
        events.run_next_event(session, store, now=NOW)
    assert session.compact_calls == [False, True]
    assert [row["status"] for row in persisted(store)][-2:] == ["running", "failed"]
    assert store.next_pending(now=NOW + timedelta(days=30)) is None


def test_window_retry_takes_priority_over_transient_deferral(tmp_path, clock):
    store = events.EventStore(tmp_path / "events.jsonl")
    event = pending(store)
    exc = ExhaustedBeforeRequest(prompt_tokens=65000, limit=65536, room=535, max_tokens=535)
    # Both classifications apply: Change 2 and 5 require compact retry first.
    exc.args = (ERROR,)
    assert events.is_transient_provider_failure(exc) is True

    with pytest.raises(ExhaustedBeforeRequest) as caught:
        events.run_next_event(FailingSession(exc, window_aware=True), store, now=NOW)

    assert caught.value is exc
    rows = persisted(store)
    assert [row["status"] for row in rows] == ["pending", "running", "failed", "pending"]
    failed, retry = rows[-2:]
    assert retry["event_id"] == event["event_id"]
    assert retry["detail"]["compact_context"] is True
    assert retry["detail"]["retry_of_run"] == failed["run_id"]
    assert "transient_retry" not in retry["detail"]
    assert not failed.get("detail", {}).get("transient", False)
    assert store.next_pending(now=NOW)["event_id"] == event["event_id"]
