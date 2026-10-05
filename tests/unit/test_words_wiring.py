"""Wiring for recall_words / search_words (plan 2026-10-05-recall-words, task 2).

Offered only when the session option is on; never named when not offered;
every cycle record says which side of the change it is on.
"""

import json
import subprocess
import sys

import pytest

from hamutay.taste_open import (
    _TOOL_GUIDANCE,
    ExchangeResult,
    OpenTasteSession,
    _build_messages,
    _natural_tool_guidance,
)
from hamutay.tools.executor import _CAPABILITY, ToolExecutor
from hamutay.tools.schemas import (
    RECALL_WORDS_SCHEMA,
    SEARCH_WORDS_SCHEMA,
    TOOL_SCHEMAS,
)
from hamutay.tools.words import CLAIM_NOTICE


def _log(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(json.dumps({
        "cycle": 1, "record_id": "r1", "timestamp": "t", "user_message": "hello",
        "response_text": "hi there", "tool_activity_full": None,
    }) + "\n")
    return path


# --- executor -------------------------------------------------------------


def test_executor_not_offered_answers_error(tmp_path):
    ex = ToolExecutor(project_root=tmp_path, cycle=2)
    for tool in ("recall_words", "search_words"):
        assert ex.execute(tool, {"cycle": 1, "pattern": "hi"}) == {
            "error": "words tools not offered in this session"
        }


def test_executor_dispatches_when_offered(tmp_path):
    path = _log(tmp_path)
    ex = ToolExecutor(project_root=tmp_path, cycle=2, words_log_path=str(path))
    out = ex.execute("recall_words", {"cycle": 1, "reason": "look back"})
    assert out["status"] == "ok" and out["words"]["reply"] == "hi there"
    out = ex.execute("search_words", {"pattern": "HELLO"})
    assert out["records_matched"] == 1
    log = ex.activity_log
    assert [e["tool"] for e in log] == ["recall_words", "search_words"]
    assert all(e["capability"] == "read_only" for e in log)
    assert log[0]["reason"] == "look back"


def test_capabilities_are_read_only():
    assert _CAPABILITY["recall_words"] == "read_only"
    assert _CAPABILITY["search_words"] == "read_only"


# --- schemas --------------------------------------------------------------


def test_schemas_exist_but_are_not_offered_by_default():
    assert RECALL_WORDS_SCHEMA["name"] == "recall_words"
    assert SEARCH_WORDS_SCHEMA["name"] == "search_words"
    assert "recall_words" not in TOOL_SCHEMAS and "search_words" not in TOOL_SCHEMAS
    for schema in (RECALL_WORDS_SCHEMA, SEARCH_WORDS_SCHEMA):
        desc = schema["description"]
        assert "claim" in desc and "own" in desc and "log" in desc
        assert "reason" in schema["input_schema"]["properties"]
    props = RECALL_WORDS_SCHEMA["input_schema"]["properties"]
    assert {"cycle", "record_id", "fields", "max_chars"} <= set(props)
    props = SEARCH_WORDS_SCHEMA["input_schema"]["properties"]
    assert {"pattern", "fields", "max_samples", "from_cycle", "to_cycle"} <= set(props)
    assert SEARCH_WORDS_SCHEMA["input_schema"]["required"] == ["pattern"]


# --- guidance -------------------------------------------------------------


def _memory_section(text):
    return text.split("### Memory", 1)[1].split("### Graph writes", 1)[0]


def test_guidance_names_words_tools_only_when_offered():
    for text in (
        _TOOL_GUIDANCE,
        _natural_tool_guidance(),
        _natural_tool_guidance(declare_quiet=True, assembly=True, plaza=True),
    ):
        assert "recall_words" not in text and "search_words" not in text
    for text in (
        _natural_tool_guidance(words=True),
        _natural_tool_guidance(declare_quiet=True, assembly=True, plaza=True, words=True),
    ):
        mem = _memory_section(text)
        assert "recall_words(" in mem and "search_words(" in mem
        assert text.count("recall_words(") == 1


@pytest.mark.parametrize("wake_mode", ["terminal", "natural"])
def test_build_messages_guidance_follows_the_option(wake_mode):
    _, off = _build_messages(None, "hi", 1, tools_enabled=True, wake_mode=wake_mode)
    _, on = _build_messages(
        None, "hi", 1, tools_enabled=True, wake_mode=wake_mode, words_recall=True
    )
    assert "recall_words" not in off and "search_words" not in off
    assert "recall_words(" in _memory_section(on) and "search_words(" in _memory_section(on)
    _, no_tools = _build_messages(None, "hi", 1, tools_enabled=False, words_recall=True)
    assert "recall_words" not in no_tools


# --- session --------------------------------------------------------------


class _NaturalBackend:
    wake_mode = "natural"

    def __init__(self, actions=()):
        self.actions = list(actions)
        self.calls = []
        self.results = []

    def call(self, model, system, messages, experiment_label,
             extra_tools=None, tool_executor=None):
        self.calls.append({"system": system, "extra_tools": extra_tools})
        for tool, params in self.actions:
            self.results.append(tool_executor.execute(tool, params))
        return ExchangeResult(
            raw_output={"response": "done"},
            tool_activity=tool_executor.activity_log if tool_executor else None,
            stop_reason="end_turn",
        )


def _session(tmp_path, backend, **kw):
    return OpenTasteSession(
        model="m", backend=backend, log_path=str(tmp_path / "session.jsonl"),
        event_log_path=str(tmp_path / "session.events.jsonl"),
        enable_tools=True, project_root=tmp_path, wake_mode="natural", **kw,
    )


def _records(tmp_path):
    return [json.loads(line) for line in (tmp_path / "session.jsonl").read_text().splitlines()]


def test_session_off_offers_nothing_and_writes_no_flag(tmp_path):
    backend = _NaturalBackend([("recall_words", {"cycle": 1})])
    s = _session(tmp_path, backend)
    s.exchange("first")
    names = [t["name"] for t in backend.calls[0]["extra_tools"]]
    assert "recall_words" not in names and "search_words" not in names
    assert "recall_words" not in backend.calls[0]["system"]
    assert backend.results == [{"error": "words tools not offered in this session"}]
    assert "words_recall" not in _records(tmp_path)[0]


def test_session_on_offers_reads_own_log_and_flags_records(tmp_path):
    backend = _NaturalBackend()
    s = _session(tmp_path, backend, words_recall=True)
    s.exchange("first knock")
    backend.actions = [("recall_words", {"cycle": 1})]
    s.exchange("second knock")
    names = [t["name"] for t in backend.calls[0]["extra_tools"]]
    assert "recall_words" in names and "search_words" in names
    assert "recall_words(" in _memory_section(backend.calls[0]["system"])
    out = backend.results[0]
    assert out["status"] == "ok" and out["claim_notice"] == CLAIM_NOTICE
    assert out["words"]["incoming"] == "first knock"
    assert out["provenance"]["log_path"] == str(tmp_path / "session.jsonl")
    assert all(r.get("words_recall") is True for r in _records(tmp_path))


# --- CLI ------------------------------------------------------------------


def test_taste_open_cli_has_words_recall_flag_default_off():
    out = subprocess.run(
        [sys.executable, "-m", "hamutay.taste_open", "--help"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "--words-recall" in out
