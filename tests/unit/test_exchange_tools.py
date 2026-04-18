"""Tests for the multi-turn tool exchange cycle.

These tests cover the pure functions and data shapes used by the
multi-turn tool loop. The full API round-trip is exercised by the
integration test in tests/integration/.
"""

from types import SimpleNamespace

from hamutay.taste_open import (
    ExchangeResult,
    _build_messages,
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


# ---------------------------------------------------------------------------
# OpenTasteSession integration with tools (no API call)
# ---------------------------------------------------------------------------


class _FakeBackend:
    """A backend that returns a canned ExchangeResult and records its inputs."""

    def __init__(self, result: ExchangeResult):
        self._result = result
        self.last_extra_tools = None
        self.last_tool_executor = None

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        self.last_extra_tools = extra_tools
        self.last_tool_executor = tool_executor
        return self._result


def test_session_passes_tools_to_backend_when_enabled(tmp_path):
    """When enable_tools=True, session hands extra_tools and a ToolExecutor
    to the backend."""
    from hamutay.taste_open import OpenTasteSession

    backend = _FakeBackend(
        ExchangeResult(
            raw_output={"response": "ok", "updated_regions": []},
            stop_reason="end_turn",
            tool_activity=[
                {"tool": "clock", "reason": None, "result_summary": "cycle 1"}
            ],
        )
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "log.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
    )
    session.exchange("hello")
    assert backend.last_extra_tools is not None
    assert len(backend.last_extra_tools) == 3
    assert backend.last_tool_executor is not None


def test_session_omits_tools_when_disabled(tmp_path):
    """enable_tools=False passes no tools — preserves old behavior."""
    from hamutay.taste_open import OpenTasteSession

    backend = _FakeBackend(
        ExchangeResult(
            raw_output={"response": "ok", "updated_regions": []},
            stop_reason="end_turn",
        )
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "log.jsonl"),
        enable_tools=False,
    )
    session.exchange("hello")
    assert backend.last_extra_tools is None
    assert backend.last_tool_executor is None


def test_session_attaches_activity_log_to_state(tmp_path):
    """When tool_activity comes back from the backend, it ends up on state."""
    from hamutay.taste_open import OpenTasteSession

    activity = [
        {"tool": "read", "reason": "looking", "result_summary": "read f.py"}
    ]
    backend = _FakeBackend(
        ExchangeResult(
            raw_output={"response": "ok", "updated_regions": []},
            stop_reason="end_turn",
            tool_activity=activity,
        )
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "log.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
    )
    session.exchange("hello")
    assert session.state is not None
    assert session.state.get("_activity_log") == activity


def test_session_activity_log_overwrites_each_cycle(tmp_path):
    """Activity log is per-cycle, not cumulative — each cycle's activity
    replaces the last, so state carries forward the most recent cycle's
    tool use rather than accumulating forever."""
    from hamutay.taste_open import OpenTasteSession

    first = [{"tool": "clock", "reason": None, "result_summary": "cycle 1"}]
    second = [{"tool": "read", "reason": "checking", "result_summary": "read x"}]
    backend = _FakeBackend(
        ExchangeResult(
            raw_output={"response": "ok", "updated_regions": []},
            stop_reason="end_turn",
            tool_activity=first,
        )
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "log.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
    )
    session.exchange("first")
    assert session.state is not None
    assert session.state["_activity_log"] == first

    # Second cycle returns different activity
    backend._result = ExchangeResult(
        raw_output={"response": "ok2", "updated_regions": []},
        stop_reason="end_turn",
        tool_activity=second,
    )
    session.exchange("second")
    assert session.state["_activity_log"] == second


# ---------------------------------------------------------------------------
# System prompt tool guidance
# ---------------------------------------------------------------------------


def test_build_messages_includes_tool_guidance_when_enabled():
    _, system = _build_messages(
        prior_state=None,
        user_message="hello",
        cycle=1,
        tools_enabled=True,
    )
    assert "read" in system.lower()
    assert "clock" in system.lower()
    assert "search_project" in system.lower()


def test_build_messages_omits_tool_guidance_when_disabled():
    _, system = _build_messages(
        prior_state=None,
        user_message="hello",
        cycle=1,
        tools_enabled=False,
    )
    # No mention of the concrete tools
    assert "search_project" not in system.lower()
    assert "clock()" not in system.lower()


def test_tool_guidance_does_not_call_reason_mandatory():
    """`reason` is optional. The guidance must not call it mandatory —
    that wording trains the model to manufacture reasons to satisfy the
    schema. The field exists to record intent when there is one."""
    _, system = _build_messages(
        prior_state=None,
        user_message="hello",
        cycle=1,
        tools_enabled=True,
    )
    assert "mandatory" not in system.lower()
    assert "optional" in system.lower()


def test_tool_guidance_is_not_coercive():
    """Guidance must not reward or require tool use. The framework is
    there to enable the model, not to shape it into a tool-caller."""
    _, system = _build_messages(
        prior_state=None,
        user_message="hello",
        cycle=1,
        tools_enabled=True,
    )
    # The only acceptable form of "required" is in "not required"
    lowered = system.lower()
    for idx in range(len(lowered)):
        if lowered[idx : idx + 8] == "required":
            before = lowered[max(0, idx - 10) : idx]
            assert "not " in before, (
                f"guidance contains a positive 'required' near: "
                f"...{lowered[max(0, idx - 20) : idx + 20]}..."
            )
