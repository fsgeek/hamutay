"""Tests for the multi-turn tool exchange cycle.

These tests cover the pure functions and data shapes used by the
multi-turn tool loop. The full API round-trip is exercised by the
integration test in tests/integration/.
"""

from types import SimpleNamespace

from hamutay.taste_open import (
    ExchangeResult,
    _split_tool_use_blocks,
    execute_concurrent_tool_calls,
)


def test_exchange_result_carries_tool_activity():
    result = ExchangeResult(
        raw_output={"response": "hello", "updated_regions": []},
        stop_reason="end_turn",
        tool_activity=[
            {"tool": "clock", "reason": "checking", "result_summary": "cycle 5"},
        ],
    )
    assert result.tool_activity is not None
    assert len(result.tool_activity) == 1
    assert result.tool_activity[0]["tool"] == "clock"


def test_exchange_result_default_tool_activity_is_none():
    result = ExchangeResult(raw_output={})
    assert result.tool_activity is None


def test_split_tool_use_blocks_identifies_think_and_respond():
    content = [
        SimpleNamespace(
            type="tool_use",
            name="think_and_respond",
            id="tr_1",
            input={"response": "hi", "updated_regions": []},
        ),
    ]
    split = _split_tool_use_blocks(content)
    assert split.think_and_respond_input == {"response": "hi", "updated_regions": []}
    assert split.other_tool_uses == []


def test_split_tool_use_blocks_separates_other_tools():
    content = [
        SimpleNamespace(
            type="tool_use", name="clock", id="c_1", input={}
        ),
        SimpleNamespace(
            type="tool_use",
            name="read",
            id="r_1",
            input={"path": "x.py"},
        ),
    ]
    split = _split_tool_use_blocks(content)
    assert split.think_and_respond_input is None
    assert len(split.other_tool_uses) == 2
    assert split.other_tool_uses[0].name == "clock"
    assert split.other_tool_uses[1].name == "read"


def test_split_tool_use_blocks_handles_concurrent():
    """think_and_respond alongside other tool calls in the same response."""
    content = [
        SimpleNamespace(
            type="tool_use", name="clock", id="c_1", input={}
        ),
        SimpleNamespace(
            type="tool_use",
            name="think_and_respond",
            id="tr_1",
            input={"response": "hi", "updated_regions": []},
        ),
    ]
    split = _split_tool_use_blocks(content)
    assert split.think_and_respond_input is not None
    assert len(split.other_tool_uses) == 1
    assert split.other_tool_uses[0].name == "clock"


def test_split_tool_use_blocks_ignores_text_blocks():
    content = [
        SimpleNamespace(type="text", text="thinking out loud"),
        SimpleNamespace(
            type="tool_use",
            name="think_and_respond",
            id="tr_1",
            input={"response": "hi", "updated_regions": []},
        ),
    ]
    split = _split_tool_use_blocks(content)
    assert split.think_and_respond_input is not None
    assert split.other_tool_uses == []


def test_execute_concurrent_tool_calls_runs_each_block(tmp_path):
    """When think_and_respond arrives alongside other tools, the framework
    executes those tools rather than silently dropping them — the model
    expressed intent and the framework honors it."""
    (tmp_path / "f.py").write_text("x\n")

    from hamutay.tools import ToolExecutor
    executor = ToolExecutor(project_root=tmp_path, cycle=1)

    blocks = [
        SimpleNamespace(
            type="tool_use", name="clock", id="c_1", input={}
        ),
        SimpleNamespace(
            type="tool_use",
            name="read",
            id="r_1",
            input={"path": "f.py"},
        ),
    ]
    execute_concurrent_tool_calls(blocks, executor)

    log = executor.activity_log
    assert len(log) == 2
    assert log[0]["tool"] == "clock"
    assert log[1]["tool"] == "read"


def test_execute_concurrent_tool_calls_tolerates_no_executor():
    """With no executor, the function is a no-op — safe to call."""
    blocks = [
        SimpleNamespace(type="tool_use", name="clock", id="c_1", input={}),
    ]
    execute_concurrent_tool_calls(blocks, None)  # should not raise
