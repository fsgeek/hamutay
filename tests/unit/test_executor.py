"""Tests for the ToolExecutor — dispatch and activity logging."""

from datetime import datetime, timezone

from hamutay.tools.executor import ToolExecutor


def test_executor_resolves_read(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')\n")
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    result = executor.execute("read", {"path": "hello.py", "reason": "testing"})
    assert "print" in result["content"]


def test_executor_resolves_clock(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=5)
    result = executor.execute("clock", {})
    assert result["cycle"] == 5


def test_executor_rejects_unknown_tool(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    result = executor.execute("delete_everything", {})
    assert "error" in result


def test_executor_records_activity(tmp_path):
    (tmp_path / "f.py").write_text("x\n")
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    executor.execute("read", {"path": "f.py", "reason": "checking"})
    executor.execute("clock", {})
    log = executor.activity_log
    assert len(log) == 2
    assert log[0]["tool"] == "read"
    assert log[0]["reason"] == "checking"
    assert log[1]["tool"] == "clock"
    # Clock was called without a reason; absence preserved as None
    assert log[1]["reason"] is None
    # Each entry carries a result summary and a hash
    for entry in log:
        assert "result_summary" in entry
        assert "result_hash" in entry
        assert "duration_ms" in entry


def test_executor_preserves_session_state_for_clock(tmp_path):
    """Clock uses the executor's session_start and last_cycle_time."""
    start = datetime(2026, 4, 18, 10, 0, 0, tzinfo=timezone.utc)
    last = datetime(2026, 4, 18, 10, 5, 0, tzinfo=timezone.utc)
    executor = ToolExecutor(
        project_root=tmp_path,
        cycle=3,
        session_start=start,
        last_cycle_time=last,
    )
    result = executor.execute("clock", {})
    assert result["session_start"] == start.isoformat()
    assert result["last_cycle_time"] == last.isoformat()
