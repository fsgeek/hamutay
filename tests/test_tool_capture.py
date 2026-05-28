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
