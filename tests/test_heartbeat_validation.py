"""Independent validation tests for the heartbeat founding invariants.

These tests are intentionally separate from the implementer's development
tests.  They exercise the public event/heartbeat path with a real session and
store; only the external model provider is replaced with a deterministic
backend.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hamutay.events import (
    EventStore,
    build_event_envelope,
    build_inbound_event,
    build_pending_event,
    run_pending_events,
    run_next_event,
)
from hamutay.heartbeat import HeartbeatLoop
from hamutay.taste_open import ExchangeResult, OpenTasteSession


class _ResidentBackend:
    """Deterministic substitute for the external provider boundary."""

    def __init__(self, raw_output: dict | None = None):
        self._raw_output = raw_output or {
            "response": "message received",
            "resident_note": "awake",
        }
        self.calls = 0

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ) -> ExchangeResult:
        del model, system, messages, experiment_label, extra_tools, tool_executor
        self.calls += 1
        return ExchangeResult(
            raw_output=self._raw_output,
            stop_reason="end_turn",
        )


def _wait_until(predicate, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not reached before timeout")


def _heartbeat_trace(event_path) -> list[tuple[str, str]]:
    if not event_path.exists():
        return []
    return [
        (record["status"], record["reason"])
        for record in EventStore(event_path).read_records()
        if record.get("record_type") == "heartbeat_status"
    ]


def _start_quiet_daemon(tmp_path):
    session_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.jsonl.events.jsonl"
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = "validation-key-must-never-be-used"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hamutay.heartbeat",
            "--log-path",
            str(session_path),
            "--project-root",
            str(tmp_path),
            "--poll-interval",
            "0.02",
        ],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process, session_path, event_path, env


def _stop_daemon(process: subprocess.Popen) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        stdout, _ = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, _ = process.communicate(timeout=3)
    return stdout


def test_context_free_inbound_message_reaches_the_resident(tmp_path):
    """Regression: optional inbound context must not fail scheduled validation."""
    session_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=_ResidentBackend(),
        log_path=str(session_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )
    store = EventStore(event_path)
    inbound = build_inbound_event(purpose="hello resident", sender="tony")
    store.append(inbound)

    completed = run_next_event(session, store)

    assert completed["status"] == "completed"
    assert completed["response_text"] == "message received"
    assert completed["context_results"] == []
    assert [
        record["status"]
        for record in store.read_records()
        if record.get("event_id") == inbound["event_id"]
    ] == ["pending", "running", "completed"]


def test_missing_context_remains_invalid_for_self_scheduled_events(tmp_path):
    """The inbound exception must not weaken reflection-event validation."""
    backend = _ResidentBackend()
    session_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=backend,
        log_path=str(session_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )
    store = EventStore(event_path)
    reflection = build_pending_event(
        purpose="remember this",
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=uuid4(),
    )
    reflection.pop("requested_context")
    store.append(reflection)

    with pytest.raises(ValueError, match="requested_context must be a non-empty"):
        run_next_event(session, store)

    assert backend.calls == 0
    assert [
        record["status"]
        for record in store.read_records()
        if record.get("event_id") == reflection["event_id"]
    ] == ["pending", "running", "failed"]


def test_fresh_daemon_boots_quiet_without_calling_the_provider(tmp_path):
    """A missing life log is first boot, and an empty queue remains alive."""
    process, session_path, event_path, _ = _start_quiet_daemon(tmp_path)
    try:
        _wait_until(
            lambda: ("quiet", "awaiting_first_event")
            in _heartbeat_trace(event_path)
        )
        assert process.poll() is None
        assert not session_path.exists()
    finally:
        output = _stop_daemon(process)

    ops = [json.loads(line) for line in output.splitlines() if line.strip()]
    # Pre-boot notices (capability resolution, launch/substrate inheritance)
    # are informational and precede the boot report since 2026-08-27.
    ops = [op for op in ops if op["heartbeat"] not in ("capabilities", "launch")]
    assert ops[0]["heartbeat"] == "boot_report"
    assert [record["heartbeat"] for record in ops[1:3]] == ["waking", "quiet"]


def test_send_wakes_a_quiet_daemon_via_the_shared_store(tmp_path):
    """External ingress is observed by re-polling without provider traffic."""
    process, session_path, event_path, env = _start_quiet_daemon(tmp_path)
    try:
        _wait_until(
            lambda: ("quiet", "awaiting_first_event")
            in _heartbeat_trace(event_path)
        )
        wake_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        sent = subprocess.run(
            [
                sys.executable,
                "-m",
                "hamutay.events",
                "send",
                "--log-path",
                str(session_path),
                "--sender",
                "tony",
                "--message",
                "a future greeting",
                "--not-before",
                wake_at,
            ],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        assert sent.returncode == 0, sent.stderr
        _wait_until(
            lambda: ("waiting", "scheduled_wake")
            in _heartbeat_trace(event_path)
        )
        assert process.poll() is None
        assert not session_path.exists()
        inbound = [
            record
            for record in EventStore(event_path).read_records()
            if record.get("event_type") == "inbound_message"
        ]
        assert len(inbound) == 1
        assert inbound[0]["status"] == "pending"
        assert inbound[0]["sender"] == "tony"
    finally:
        _stop_daemon(process)


def test_boot_recovery_replays_an_orphan_through_the_real_wake_path(tmp_path):
    """A process-weather interruption is recovered into a completed wake."""
    session_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "session.events.jsonl"
    session = OpenTasteSession(
        backend=_ResidentBackend(),
        log_path=str(session_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )
    store = EventStore(event_path)
    inbound = build_inbound_event(purpose="interrupted greeting", sender="tony")
    store.append(inbound)
    crashed_claim = store.append_running(inbound)

    loop = HeartbeatLoop(session, store, batch_limit=1)
    report = loop.boot()
    result = loop.step()

    assert report == {
        "orphaned_running_recovered": 1,
        "lost_continuations_recovered": 0,
    }
    assert result["state"] == "quiet"
    history = [
        record
        for record in store.read_records()
        if record.get("event_id") == inbound["event_id"]
    ]
    assert [record["status"] for record in history] == [
        "pending",
        "running",
        "pending",
        "running",
        "completed",
    ]
    assert history[2]["recovered_from_run_id"] == crashed_claim["run_id"]
    assert history[-1]["response_text"] == "message received"


def test_inbound_envelope_preserves_external_provenance():
    """Regression: an external message must not be described as self-scheduled."""
    inbound = build_inbound_event(purpose="hello resident", sender="tony")

    envelope = json.loads(build_event_envelope(inbound, [], "run-1"))

    assert envelope["event_type"] == "inbound_message"
    assert envelope["origin"] == "external"
    assert envelope["sender"] == "tony"
    assert "external inbound event" in envelope["instruction"].lower()
    assert "self-scheduled" not in envelope["instruction"].lower()


def test_ingress_racing_with_the_queue_probe_still_leaves_a_wake_trace(tmp_path):
    """Regression: work claimed after the pre-batch probe must remain legible."""
    session_path = tmp_path / "session.jsonl"
    event_path = tmp_path / "events.jsonl"
    session = OpenTasteSession(
        backend=_ResidentBackend(),
        log_path=str(session_path),
        event_log_path=str(event_path),
        enable_tools=True,
        project_root=tmp_path,
    )
    store = EventStore(event_path)
    prior = build_inbound_event(purpose="earlier work", sender="tony")
    store.append(prior)
    prior_running = store.append_running(prior)
    store.append_completed(
        event=prior,
        run_id=prior_running["run_id"],
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
    )

    call_count = 0
    raced_event = None

    def run_with_racing_ingress(session, event_store, **kwargs):
        nonlocal call_count, raced_event
        call_count += 1
        if call_count == 2:
            raced_event = build_inbound_event(
                purpose="arrived after the queue probe", sender="tony"
            )
            event_store.append(raced_event)
        return run_pending_events(session, event_store, **kwargs)

    loop = HeartbeatLoop(
        session,
        store,
        poll_interval=0.01,
        run_pending=run_with_racing_ingress,
    )
    loop.step()
    loop.step()

    assert [
        (record["status"], record["reason"])
        for record in store.read_records()
        if record.get("record_type") == "heartbeat_status"
    ] == [
        ("quiet", "chosen_quiet"),
        ("active", "runnable_pending"),
        ("quiet", "chosen_quiet"),
    ]
    assert raced_event is not None
    assert store.latest_by_event_id()[raced_event["event_id"]]["status"] == "completed"
