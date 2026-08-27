"""Development tests for --wake-mode natural.

Pre-registration: docs/wake-mode-preregistration-20260827.md
Validating tests are authored separately by Codex per repo norm; these are
the implementer's TDD tests.
"""

import pytest

from hamutay.taste_open import (
    CapabilityProfile,
    ExchangeResult,
    OpenAITasteBackend,
    OpenTasteSession,
)
from hamutay.tools import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS, UPDATE_STATE_SCHEMA


# --- executor: update_state buffers into the cycle, last write wins --------


def _executor(tmp_path):
    return ToolExecutor(project_root=tmp_path, cycle=3)


def test_update_state_buffers_updates_and_deletions(tmp_path):
    ex = _executor(tmp_path)
    result = ex.execute(
        "update_state",
        {"updates": {"identity": "x"}, "deleted_regions": ["stale"]},
    )
    assert result == {"recorded": ["identity"], "deleted": ["stale"]}
    assert ex.pending_state_updates == {
        "updates": {"identity": "x"},
        "deleted_regions": ["stale"],
    }


def test_update_state_last_write_wins_within_a_wake(tmp_path):
    ex = _executor(tmp_path)
    ex.execute("update_state", {"updates": {"a": 1, "b": 1}})
    ex.execute("update_state", {"updates": {"a": 2}})
    assert ex.pending_state_updates["updates"] == {"a": 2, "b": 1}


def test_update_state_write_after_delete_is_a_write(tmp_path):
    ex = _executor(tmp_path)
    ex.execute("update_state", {"deleted_regions": ["k"]})
    ex.execute("update_state", {"updates": {"k": "back"}})
    assert ex.pending_state_updates == {
        "updates": {"k": "back"},
        "deleted_regions": [],
    }


def test_update_state_delete_after_write_is_a_delete(tmp_path):
    ex = _executor(tmp_path)
    ex.execute("update_state", {"updates": {"k": "v"}})
    ex.execute("update_state", {"deleted_regions": ["k"]})
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": ["k"]}


def test_update_state_rejects_protocol_keys(tmp_path):
    ex = _executor(tmp_path)
    result = ex.execute("update_state", {"updates": {"response": "no"}})
    assert "error" in result
    assert ex.pending_state_updates == {"updates": {}, "deleted_regions": []}


def test_update_state_is_logged_as_bounded_write(tmp_path):
    ex = _executor(tmp_path)
    ex.execute("update_state", {"updates": {"a": 1}, "reason": "because"})
    entry = ex.activity_log[-1]
    assert entry["tool"] == "update_state"
    assert entry["capability"] == "bounded_write"
    assert entry["reason"] == "because"
    assert entry["parameters"] == {"updates": {"a": 1}}


def test_update_state_schema_is_not_in_the_terminal_tool_set():
    # Terminal mode must be byte-for-byte what the residents run today.
    assert "update_state" not in TOOL_SCHEMAS
    assert UPDATE_STATE_SCHEMA["name"] == "update_state"


# --- backend: natural wake loop ------------------------------------------


def _scripted_backend(script, capability=None):
    backend = OpenAITasteBackend(
        api_key="k",
        capability=capability,
        wake_mode="natural",
    )
    backend.payloads = []

    def fake_post(payload):
        backend.payloads.append(payload)
        return script.pop(0)

    backend._post_chat = fake_post
    return backend


def _tool_call(name, args, call_id="c1"):
    import json

    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _turn(content=None, tool_calls=None, finish="stop"):
    return {
        "choices": [
            {
                "finish_reason": finish,
                "message": {"content": content, "tool_calls": tool_calls},
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def test_natural_wake_ends_on_text_and_merges_update_state(tmp_path):
    (tmp_path / "note.txt").write_text("hello")
    script = [
        _turn(
            content="Reading first.",
            tool_calls=[
                _tool_call("read", {"path": "note.txt"}, "c1"),
                _tool_call(
                    "update_state",
                    {"updates": {"seen": "note"}, "deleted_regions": ["old"]},
                    "c2",
                ),
            ],
            finish="tool_calls",
        ),
        _turn(content="Done. The note says hello."),
    ]
    backend = _scripted_backend(script)
    ex = _executor(tmp_path)
    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "look"}],
        experiment_label="t",
        extra_tools=[UPDATE_STATE_SCHEMA, TOOL_SCHEMAS["read"]],
        tool_executor=ex,
    )
    assert isinstance(result, ExchangeResult)
    assert result.stop_reason == "end_turn"
    assert result.raw_output == {
        "response": "Done. The note says hello.",
        "seen": "note",
        "deleted_regions": ["old"],
    }
    names = [t["tool"] for t in result.tool_activity]
    assert names == ["read", "update_state"]
    assert result.interim_text == ["Reading first."]


def test_natural_wake_with_no_update_state_carries_nothing(tmp_path):
    backend = _scripted_backend([_turn(content="Just talking.")])
    result = backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "hi"}],
        experiment_label="t",
        extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=_executor(tmp_path),
    )
    assert result.raw_output == {"response": "Just talking."}


def test_natural_wake_offers_no_terminal_tool_and_uses_auto_choice(tmp_path):
    forced = CapabilityProfile(tool_choice_mode="function_object")
    backend = _scripted_backend([_turn(content="ok")], capability=forced)
    backend.call(
        model="m",
        system="s",
        messages=[{"role": "user", "content": "hi"}],
        experiment_label="t",
        extra_tools=[UPDATE_STATE_SCHEMA],
        tool_executor=_executor(tmp_path),
    )
    payload = backend.payloads[0]
    tool_names = [t["function"]["name"] for t in payload["tools"]]
    assert "think_and_respond" not in tool_names
    assert "update_state" in tool_names
    assert payload["tool_choice"] == "auto"


def test_natural_wake_refuses_truncated_reply(tmp_path):
    backend = _scripted_backend([_turn(content="partial", finish="length")])
    with pytest.raises(RuntimeError, match="length"):
        backend.call(
            model="m",
            system="s",
            messages=[{"role": "user", "content": "hi"}],
            experiment_label="t",
            extra_tools=[UPDATE_STATE_SCHEMA],
            tool_executor=_executor(tmp_path),
        )


# --- session: wiring ------------------------------------------------------


class _NaturalFakeBackend:
    wake_mode = "natural"

    def __init__(self):
        self.calls = []

    def call(self, model, system, messages, experiment_label,
             extra_tools=None, tool_executor=None):
        self.calls.append({"system": system, "extra_tools": extra_tools})
        if tool_executor is not None:
            tool_executor.execute("update_state", {"updates": {"mood": "calm"}})
        return ExchangeResult(
            raw_output={"response": "text reply", "mood": "calm"},
            tool_activity=tool_executor.activity_log if tool_executor else None,
        )


def test_session_natural_mode_offers_update_state_and_describes_it(tmp_path):
    backend = _NaturalFakeBackend()
    session = OpenTasteSession(
        model="m",
        backend=backend,
        log_path=str(tmp_path / "s.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
        wake_mode="natural",
    )
    reply = session.exchange("hello")
    assert reply == "text reply"
    call = backend.calls[0]
    names = [t["name"] for t in call["extra_tools"]]
    assert "update_state" in names
    assert "think_and_respond" not in call["system"]
    assert "update_state" in call["system"]
    assert session._state["mood"] == "calm"


def test_session_natural_mode_is_recorded_in_the_log(tmp_path):
    import json

    log = tmp_path / "s.jsonl"
    session = OpenTasteSession(
        model="m",
        backend=_NaturalFakeBackend(),
        log_path=str(log),
        enable_tools=True,
        project_root=tmp_path,
        wake_mode="natural",
    )
    session.exchange("hello")
    record = json.loads(log.read_text().splitlines()[-1])
    assert record["wake_mode"] == "natural"


def test_session_terminal_mode_is_the_default_and_unchanged(tmp_path):
    import json

    class _TerminalFake:
        def call(self, model, system, messages, experiment_label,
                 extra_tools=None, tool_executor=None):
            self.system = system
            self.extra_tools = extra_tools
            return ExchangeResult(raw_output={"response": "r"})

    backend = _TerminalFake()
    log = tmp_path / "s.jsonl"
    session = OpenTasteSession(
        model="m", backend=backend, log_path=str(log),
        enable_tools=True, project_root=tmp_path,
    )
    session.exchange("hello")
    assert "think_and_respond" in backend.system
    assert "update_state" not in [t["name"] for t in backend.extra_tools]
    record = json.loads(log.read_text().splitlines()[-1])
    assert record["wake_mode"] == "terminal"


def test_session_natural_mode_rejects_backend_without_support(tmp_path):
    class _Plain:
        def call(self, *a, **k):
            raise AssertionError("should not be called")

    with pytest.raises(ValueError, match="natural"):
        OpenTasteSession(
            model="m", backend=_Plain(), log_path=str(tmp_path / "s.jsonl"),
            enable_tools=True, project_root=tmp_path, wake_mode="natural",
        )


def test_session_natural_mode_requires_tools(tmp_path):
    with pytest.raises(ValueError, match="tools"):
        OpenTasteSession(
            model="m", backend=_NaturalFakeBackend(),
            log_path=str(tmp_path / "s.jsonl"),
            enable_tools=False, project_root=tmp_path, wake_mode="natural",
        )
