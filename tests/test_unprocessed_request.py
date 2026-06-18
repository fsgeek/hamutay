"""Tests for declared capture of discarded terminal drafts.

No live API calls: these tests use the same fake Anthropic streaming client
shape as the taste_open harness tests.
"""

from __future__ import annotations

import copy

from hamutay.taste_open import AnthropicTasteBackend, ExchangeResult, OpenTasteSession


class _FakeBlock:
    def __init__(self, *, btype, name=None, input=None, id=None, text=None):
        self.type = btype
        self.name = name
        self.input = input
        self.id = id
        self.text = text

    def model_dump(self):
        if self.type == "tool_use":
            return {
                "type": "tool_use",
                "name": self.name,
                "input": self.input,
                "id": self.id,
            }
        return {"type": self.type, "text": self.text}


class _FakeUsage:
    def __init__(self, input_tokens=0, output_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = 0
        self.cache_creation_input_tokens = 0


class _FakeMessage:
    def __init__(self, content, *, stop_reason="tool_use", usage=None):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = usage or _FakeUsage()


class _FakeStreamCtx:
    def __init__(self, item):
        self._item = item

    def __enter__(self):
        if isinstance(self._item, Exception):
            raise self._item
        return self

    def __exit__(self, *_):
        return False

    def get_final_message(self):
        return self._item


class _FakeMessages:
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0
        self.sent_messages = []

    def stream(self, **kwargs):
        self.sent_messages.append(copy.deepcopy(kwargs["messages"]))
        item = self._script[self.calls]
        self.calls += 1
        return _FakeStreamCtx(item)


class _FakeClient:
    def __init__(self, script):
        self.messages = _FakeMessages(script)


class _FakeToolExecutor:
    def __init__(self, result=None):
        self._result = result or {"stdout": "ok", "stderr": "", "exit_code": 0}
        self.activity_log = []
        self.executed = []

    def execute(self, name, tool_input):
        self.executed.append((name, tool_input))
        return self._result

    def log_event(self, event):
        self.activity_log.append(event)


class _SequenceBackend:
    def __init__(self, results: list[ExchangeResult]):
        self._results = list(results)

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        del model, system, messages, experiment_label, extra_tools, tool_executor
        if not self._results:
            raise AssertionError("sequence backend exhausted")
        return self._results.pop(0)


def _tool(name: str) -> dict:
    return {"name": name, "description": "test tool", "input_schema": {}}


def test_bundled_terminal_draft_is_reported_as_unprocessed_request():
    held_draft = {
        "response": "premature before bash result",
        "status": "too_early",
    }
    mixed = _FakeMessage(
        [
            _FakeBlock(
                btype="tool_use",
                name="bash",
                input={"command": "echo observed", "reason": "probe"},
                id="tu_bash_1",
            ),
            _FakeBlock(
                btype="tool_use",
                name="think_and_respond",
                input=held_draft,
                id="tu_tr_1",
            ),
        ],
        usage=_FakeUsage(input_tokens=100, output_tokens=50),
    )
    terminal = _FakeMessage(
        [
            _FakeBlock(
                btype="tool_use",
                name="think_and_respond",
                input={"response": "closed after bash", "status": "done"},
                id="tu_tr_2",
            )
        ],
        usage=_FakeUsage(input_tokens=200, output_tokens=80),
    )
    backend = AnthropicTasteBackend(
        client=_FakeClient([mixed, terminal]),
        max_tokens=64_000,
    )  # type: ignore[arg-type]
    executor = _FakeToolExecutor()

    result = backend.call(
        model="claude-test",
        system="sys",
        messages=[{"role": "user", "content": "run then respond"}],
        experiment_label="unprocessed_request_test",
        extra_tools=[_tool("bash")],
        tool_executor=executor,
    )

    assert result.raw_output == {"response": "closed after bash", "status": "done"}
    assert executor.executed == [
        ("bash", {"command": "echo observed", "reason": "probe"})
    ]
    assert result.unprocessed_request == [
        {
            "turn_index": 0,
            "n_peripheral_tools": 1,
            "held_draft": held_draft,
        }
    ]


def test_clean_terminal_cycle_has_no_unprocessed_request():
    terminal = _FakeMessage(
        [
            _FakeBlock(
                btype="tool_use",
                name="think_and_respond",
                input={"response": "clean close", "status": "done"},
                id="tu_tr_1",
            )
        ],
        usage=_FakeUsage(input_tokens=10, output_tokens=20),
    )
    backend = AnthropicTasteBackend(
        client=_FakeClient([terminal]),
        max_tokens=64_000,
    )  # type: ignore[arg-type]

    result = backend.call(
        model="claude-test",
        system="sys",
        messages=[{"role": "user", "content": "respond"}],
        experiment_label="clean_unprocessed_request_test",
        extra_tools=[_tool("bash")],
        tool_executor=_FakeToolExecutor(),
    )

    assert result.raw_output == {"response": "clean close", "status": "done"}
    assert result.unprocessed_request is None


def test_session_stamps_unprocessed_request_for_one_cycle_only(tmp_path):
    held = [
        {
            "turn_index": 0,
            "n_peripheral_tools": 1,
            "held_draft": {"response": "premature"},
        }
    ]
    backend = _SequenceBackend(
        [
            ExchangeResult(
                raw_output={"response": "first", "status": "done"},
                unprocessed_request=held,
            ),
            ExchangeResult(raw_output={"response": "second", "status": "done"}),
        ]
    )
    session = OpenTasteSession(
        backend=backend,
        log_path=str(tmp_path / "session.jsonl"),
    )

    session.exchange("first")
    assert session.state is not None
    assert session.state["_unprocessed_request"] == held

    session.exchange("second")
    assert "_unprocessed_request" not in session.state
