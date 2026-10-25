"""Exercise the real session commit path; replace only model inference."""

import json

import pytest

from hamutay.taste_open import ExchangeResult, OpenTasteSession

from .test_executor import REASON, UNTIL


class QuietBackend:
    wake_mode = "natural"

    def __init__(self, *, fail=False):
        self.fail = fail
        self.result = None
        self.pending = []

    def call(self, *, tool_executor, **kwargs):
        self.result = tool_executor.execute("declare_quiet", {
            "reason": REASON, "until": UNTIL, "wake_at_until": True,
        })
        self.pending = list(tool_executor.pending_events)
        if self.fail:
            raise RuntimeError("validation wake failed after declaring quiet")
        return ExchangeResult(
            raw_output={"response": "Quiet declared."}, stop_reason="end_turn",
            tool_activity=tool_executor.activity_log,
        )


def make_session(tmp_path, backend):
    return OpenTasteSession(
        model="validation-model", backend=backend,
        log_path=str(tmp_path / "session.jsonl"),
        event_log_path=str(tmp_path / "events.jsonl"),
        enable_tools=True, project_root=tmp_path, wake_mode="natural",
        memory_base_probability=0,
    )


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_success_commits_quiet_wake_with_cycle_record_id(tmp_path):
    backend = QuietBackend()
    session = make_session(tmp_path, backend)

    session.exchange("Choose a quiet.", event_managed=True)

    records = read_rows(tmp_path / "events.jsonl")
    declaration, = [row for row in records if row.get("record_type") == "quiet_declaration"]
    event, = [row for row in records if row.get("record_type") == "event_status"]
    cycle, = read_rows(tmp_path / "session.jsonl")
    assert declaration["reason"] == REASON
    assert declaration["declared_by_record_id"] == cycle["record_id"]
    assert event["scheduled_by_record_id"] == cycle["record_id"]
    assert event["scheduled_by_cycle"] == cycle["cycle"]
    assert event["event_id"] == backend.result["wake_event_id"]
    assert event["not_before"] == UNTIL
    assert event["status"] == "pending"
    assert event["label"] == "quiet_end"
    assert cycle["scheduled_events"][0]["event_id"] == event["event_id"]


def test_failed_wake_commits_neither_declaration_nor_buffered_event(tmp_path):
    backend = QuietBackend(fail=True)
    session = make_session(tmp_path, backend)

    with pytest.raises(RuntimeError, match="validation wake failed"):
        session.exchange("Choose a quiet, then fail.", event_managed=True)

    # Require a real buffered event so the rollback check cannot pass vacuously.
    assert len(backend.pending) == 1
    assert backend.pending[0]["label"] == "quiet_end"
    assert read_rows(tmp_path / "events.jsonl") == []
    records = read_rows(tmp_path / "session.jsonl")
    assert not any(row.get("record_type") == "quiet_declaration" for row in records)
    wake_records = [
        row for row in records
        if row.get("cycle") == backend.pending[0]["scheduled_by_cycle"]
    ]
    # The wake must leave failure evidence, never a completed cycle record.
    assert wake_records
    assert all(row.get("status") == "failed" for row in wake_records)
    assert any(
        row.get("failure_classification", {}).get("error")
        == "validation wake failed after declaring quiet"
        for row in wake_records
    )
