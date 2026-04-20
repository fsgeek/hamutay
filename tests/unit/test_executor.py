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


# ---------------------------------------------------------------------------
# Memory tool dispatch
# ---------------------------------------------------------------------------


def _prior_states_fixture():
    from uuid import UUID
    return [
        (
            1,
            UUID("00000000-0000-0000-0000-000000000001"),
            {"theme": "opening", "cycle": 1},
            "2026-04-18T10:00:00+00:00",
        ),
    ]


def test_executor_resolves_memory_schema(tmp_path):
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2, prior_states=_prior_states_fixture(),
    )
    result = executor.execute("memory_schema", {"cycle": 1})
    assert result["cycle"] == 1
    assert "theme" in result["field_names"]


def test_executor_resolves_recall(tmp_path):
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2, prior_states=_prior_states_fixture(),
    )
    result = executor.execute("recall", {"cycle": 1, "field": "theme"})
    assert result["content"] == "opening"


def test_executor_memory_tool_without_prior_states_returns_empty(tmp_path):
    """Without prior_states, memory tools see an empty history — no crash."""
    executor = ToolExecutor(project_root=tmp_path, cycle=2)
    result = executor.execute("memory_schema", {"cycle": 1})
    assert "error" in result


def test_executor_records_memory_tool_activity(tmp_path):
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2, prior_states=_prior_states_fixture(),
    )
    executor.execute(
        "recall", {"cycle": 1, "field": "theme", "reason": "curious"}
    )
    log = executor.activity_log
    assert log[-1]["tool"] == "recall"
    assert log[-1]["reason"] == "curious"


# ---------------------------------------------------------------------------
# Bridge threaded through to memory tools (cross-session scope)
# ---------------------------------------------------------------------------


def test_executor_passes_bridge_to_recall(tmp_path):
    """recall record_id mode works through the executor when a bridge is present."""
    from unittest.mock import MagicMock
    from uuid import UUID

    rid = UUID("11111111-1111-1111-1111-111111111111")
    bridge = MagicMock()
    bridge.retrieve.return_value = {"theme": "cross-session-content"}

    executor = ToolExecutor(
        project_root=tmp_path, cycle=2,
        prior_states=_prior_states_fixture(),
        bridge=bridge,
    )
    result = executor.execute(
        "recall", {"record_id": str(rid), "field": "theme"}
    )
    assert result["content"] == "cross-session-content"
    bridge.retrieve.assert_called_once_with(rid)


def test_executor_passes_bridge_to_memory_schema(tmp_path):
    """memory_schema record_id mode routes through the bridge."""
    from unittest.mock import MagicMock

    bridge = MagicMock()
    bridge.retrieve.return_value = {
        "theme": "x", "notes": ["a", "b"],
        "provenance": {"author_instance_id": "other"},
    }
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2,
        prior_states=_prior_states_fixture(),
        bridge=bridge,
    )
    result = executor.execute(
        "memory_schema",
        {"record_id": "11111111-1111-1111-1111-111111111111"},
    )
    assert "theme" in result["field_names"]
    # Envelope fields stripped from the schema view.
    assert "provenance" not in result["field_names"]


def test_executor_without_bridge_returns_error_on_record_id(tmp_path):
    """Sensible error when bridge isn't wired and cross-session mode is invoked."""
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2,
        prior_states=_prior_states_fixture(),
    )
    result = executor.execute(
        "recall",
        {"record_id": "11111111-1111-1111-1111-111111111111"},
    )
    assert "error" in result


# ---------------------------------------------------------------------------
# Graph write tool dispatch
# ---------------------------------------------------------------------------


def test_executor_dispatches_store(tmp_path):
    from unittest.mock import MagicMock
    from uuid import UUID

    bridge = MagicMock()
    bridge.session_id = "s"
    bridge.store_instance_record.return_value = UUID(
        "00000000-0000-0000-0000-000000000099"
    )
    executor = ToolExecutor(project_root=tmp_path, cycle=4, bridge=bridge)
    result = executor.execute("store", {"content": {"note": "x"}})
    assert result["record_id"] == "00000000-0000-0000-0000-000000000099"
    assert result["cycle"] == 4


def test_executor_dispatches_annotate_edge(tmp_path):
    from unittest.mock import MagicMock
    from uuid import UUID

    bridge = MagicMock()
    bridge.store_edge.return_value = UUID(
        "00000000-0000-0000-0000-0000000000ee"
    )
    executor = ToolExecutor(project_root=tmp_path, cycle=4, bridge=bridge)
    result = executor.execute(
        "annotate_edge",
        {
            "from_record_id": "00000000-0000-0000-0000-000000000001",
            "to_record_id": "00000000-0000-0000-0000-000000000002",
            "relation": "REFINES",
        },
    )
    assert result["edge_id"] == "00000000-0000-0000-0000-0000000000ee"


def test_executor_store_without_bridge_errors(tmp_path):
    executor = ToolExecutor(project_root=tmp_path, cycle=4)
    result = executor.execute("store", {"content": {"x": 1}})
    assert "error" in result
