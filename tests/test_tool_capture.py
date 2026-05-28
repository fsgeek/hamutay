"""Tool-capture: every invocation logs capability, exit code, and full result.

Save-everything policy — the durable activity entry keeps the whole result
dict. (The session layer strips `result` for the in-context copy; that split
lives in taste_open.) Uses real but harmless tool calls, no model API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hamutay.tools.executor import ToolExecutor


def _executor() -> ToolExecutor:
    return ToolExecutor(
        project_root=Path.cwd(),
        cycle=1,
        session_start=datetime.now(timezone.utc),
        last_cycle_time=None,
        prior_states=[],
        bridge=None,
    )


def test_bash_capture_is_complete():
    ex = _executor()
    ex.execute("bash", {"command": "echo hello", "reason": "test"})
    entry = ex.activity_log[-1]

    assert entry["tool"] == "bash"
    assert entry["capability"] == "unbounded"
    assert entry["parameters"]["command"] == "echo hello"
    assert "reason" not in entry["parameters"]
    assert entry["reason"] == "test"
    assert entry["exit_code"] == 0
    assert "hello" in entry["result"]["stdout"]
    assert entry["result_hash"]


def test_readonly_tagged_and_no_exit_code():
    ex = _executor()
    ex.execute("clock", {})
    entry = ex.activity_log[-1]

    assert entry["capability"] == "read_only"
    assert entry["exit_code"] is None
    assert "result" in entry


def test_framework_events_persist_via_log_event():
    # Framework budget/recovery events must land in the durable log. The bug:
    # callers did `activity_log.append(...)`, but the property returns a fresh
    # copy each access, so those events were silently dropped — the exact
    # silent-drop this codebase forbids. log_event writes the real list.
    ex = _executor()
    ex.log_event({"tool": "_framework", "event": "budget_recovery"})
    log = ex.activity_log
    assert any(
        e.get("tool") == "_framework" and e.get("event") == "budget_recovery"
        for e in log
    )


def test_activity_log_property_returns_a_snapshot_copy():
    # Lock in why log_event is necessary: mutating the returned list must NOT
    # affect the executor's real log (the copy is a deliberate read snapshot).
    ex = _executor()
    ex.activity_log.append({"tool": "_framework", "event": "ghost"})
    assert ex.activity_log == []
