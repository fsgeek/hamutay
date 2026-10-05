"""Session-boundary checks with synthetic backends and isolated startup."""

import argparse
import json
import subprocess
import sys
from itertools import product
from pathlib import Path

import pytest


class SyntheticBackend:
    """A transport double using only TasteBackend's documented call interface."""

    def __init__(self, *args, **kwargs):
        self.calls = []
        self.max_tokens = kwargs.get("max_tokens", 64000)

    def answer(self, **request):
        from hamutay.taste_open import ExchangeResult

        self.calls.append(request)
        return ExchangeResult(
            raw_output={"STATE": {"validation": "synthetic state"}, "response_text": "Synthetic cycle reply."},
            input_tokens=12,
            output_tokens=7,
        )

    def call(self, model, system, messages, experiment_label, extra_tools=None, tool_executor=None):
        return self.answer(model=model, system=system, messages=messages, experiment_label=experiment_label, extra_tools=extra_tools, tool_executor=tool_executor)

    def call_terminal_surface(self, model, system, messages, experiment_label, terminal_surface):
        return self.answer(model=model, system=system, messages=messages, experiment_label=experiment_label, terminal_surface=terminal_surface)


@pytest.mark.parametrize("name, tool_input", [("recall_words", {"cycle": 1}), ("search_words", {"pattern": "synthetic"})])
def test_executor_refuses_words_tools_when_not_offered(tmp_path, name, tool_input):
    from hamutay.tools.executor import ToolExecutor

    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    assert executor.execute(name, tool_input) == {"error": "words tools not offered in this session"}


@pytest.mark.parametrize("name, tool_input", [("recall_words", {"cycle": 17}), ("search_words", {"pattern": "distinctive"})])
def test_executor_reads_only_the_explicitly_offered_log(tmp_path, record, write_log, claim_notice, name, tool_input):
    from hamutay.tools.executor import ToolExecutor

    own, _ = write_log(record(user_message="distinctive own-door words"))
    other, _ = write_log(record(user_message="OTHER_DOOR_MUST_NOT_APPEAR"))
    before = {path: path.read_bytes() for path in (own, other)}
    executor = ToolExecutor(project_root=tmp_path, cycle=18, words_log_path=str(own))
    result = executor.execute(name, tool_input)
    assert result["claim_notice"] == claim_notice
    if name == "recall_words":
        assert result["words"]["incoming"] == "distinctive own-door words"
        assert result["provenance"]["log_path"] == str(own)
    else:
        assert result["records_scanned"] == result["records_matched"] == 1
        assert "distinctive" in result["samples"][0]["snippet"]
    assert "OTHER_DOOR_MUST_NOT_APPEAR" not in json.dumps(result)
    assert {path: path.read_bytes() for path in (own, other)} == before


@pytest.mark.parametrize("declare_quiet, assembly, plaza", list(product([False, True], repeat=3)))
@pytest.mark.parametrize("offered", [False, True], ids=["not-offered", "offered"])
def test_memory_guidance_names_words_tools_only_when_offered(declare_quiet, assembly, plaza, offered):
    from hamutay.taste_open import _natural_tool_guidance

    guidance = _natural_tool_guidance(declare_quiet=declare_quiet, assembly=assembly, plaza=plaza, words=offered)
    for name in ("recall_words", "search_words"):
        assert (name in guidance) is offered
    if offered:
        memory = guidance.split("### Memory", 1)[1]
        memory = memory.split("\n### ", 1)[0]
        tool_lines = [line for line in memory.splitlines() if "recall_words" in line or "search_words" in line]
        assert len(tool_lines) == 2
        assert any("recall_words" in line for line in tool_lines)
        assert any("search_words" in line for line in tool_lines)


def test_words_schemas_are_opt_in_and_describe_claims_and_own_log_scope(claim_notice):
    from hamutay.tools.schemas import RECALL_WORDS_SCHEMA, SEARCH_WORDS_SCHEMA, TOOL_SCHEMAS

    defaults = {schema["name"] for schema in TOOL_SCHEMAS.values()}
    assert not defaults & {"recall_words", "search_words"}
    for schema, name in [(RECALL_WORDS_SCHEMA, "recall_words"), (SEARCH_WORDS_SCHEMA, "search_words")]:
        assert schema["name"] == name
        description = schema["description"]
        assert claim_notice in description
        description = description.lower()
        assert "log" in description
        assert any(scope in description for scope in ("own", "your session", "this session", "this door", "your log"))


@pytest.mark.parametrize("option", [{}, {"words_recall": False}, {"words_recall": True}], ids=["default-off", "explicit-off", "on"])
def test_session_offering_guidance_and_every_cycle_record_follow_the_option(tmp_path, option, claim_notice):
    from hamutay.taste_open import OpenTasteSession

    enabled = option.get("words_recall", False)
    backend = SyntheticBackend()
    path = tmp_path / "own-session.jsonl"
    session = OpenTasteSession(
        model="synthetic-validator-model", backend=backend, log_path=str(path),
        experiment_label="independent-words-validation", project_root=tmp_path,
        enable_tools=True, memory_base_probability=0.0, **option,
    )
    session.exchange("First synthetic incoming message.", force_memory=None)
    session.exchange("Second synthetic incoming message.", force_memory=None)

    cycle_records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    cycle_records = [value for value in cycle_records if "cycle" in value]
    assert len(cycle_records) == 2
    for value in cycle_records:
        if enabled:
            assert value["words_recall"] is True
        else:
            assert "words_recall" not in value, "Off writes nothing, including no false version flag"
    assert backend.calls
    for call in backend.calls:
        schemas = call.get("extra_tools") or []
        names = {schema["name"] for schema in schemas}
        assert ({"recall_words", "search_words"} <= names) is enabled
        if not enabled:
            assert not names & {"recall_words", "search_words"}
        prompt = json.dumps({"system": call["system"], "messages": call["messages"]})
        for name in ("recall_words", "search_words"):
            assert (name in prompt) is enabled
        executor = call.get("tool_executor")
        assert executor is not None, "Tools-enabled sessions must supply their executor"
        result = executor.execute("recall_words", {"cycle": cycle_records[0]["cycle"]})
        if enabled:
            assert result["status"] == "ok"
            assert result["claim_notice"] == claim_notice
            assert result["provenance"]["log_path"] == str(path)
            assert result["words"]["incoming"] == cycle_records[0]["user_message"]
        else:
            assert result == {"error": "words tools not offered in this session"}


def test_taste_open_cli_advertises_the_words_recall_switch():
    completed = subprocess.run(
        [sys.executable, "-m", "hamutay.taste_open", "--help"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--words-recall" in completed.stdout


def isolated_heartbeat_args(heartbeat, tmp_path):
    """Use CLI defaults without assuming which unrelated flags are required."""
    parser = heartbeat.build_parser()
    # argparse's action descriptors are its CLI schema, not feature internals.
    args = argparse.Namespace(**{action.dest: action.default for action in parser._actions if action.dest != "help"})
    path_destinations = {action.dest for action in parser._actions if action.type is Path or isinstance(action.default, Path)}
    for name in vars(args):
        if name in {"log", "log_path", "session_log", "session_log_path"}:
            setattr(args, name, str(tmp_path / "session.jsonl"))
        elif name in {"event_log", "event_log_path", "event_store", "event_store_path", "events"}:
            setattr(args, name, str(tmp_path / "events.sqlite"))
        elif name in {"lock", "lock_path"}:
            setattr(args, name, str(tmp_path / "events.sqlite.lock"))
        elif name == "project_root":
            setattr(args, name, str(tmp_path))
        if name in path_destinations and getattr(args, name) is not None:
            setattr(args, name, Path(getattr(args, name)))
    args.provider = "anthropic"
    args.wake_mode = "terminal"
    args.model = "synthetic-validator-model"
    args.words_recall = False  # Heartbeat must force this on for its doors.
    args.context_limit = 8192
    args.persist = "none"
    return parser, args


@pytest.mark.parametrize("door", ["synthetic-cedar", "synthetic-spruce"])
def test_heartbeat_enables_words_recall_for_each_door(tmp_path, monkeypatch, door):
    import hamutay.heartbeat as heartbeat
    import hamutay.taste_open as taste_open

    root = tmp_path / door
    root.mkdir()
    _, args = isolated_heartbeat_args(heartbeat, root)
    constructors = []
    original_session = taste_open.OpenTasteSession

    def capture_session(*positional, **keywords):
        constructors.append(keywords.copy())
        return original_session(*positional, **keywords)

    monkeypatch.setattr(taste_open, "OpenTasteSession", capture_session)
    monkeypatch.setattr(heartbeat, "OpenTasteSession", capture_session, raising=False)
    monkeypatch.setattr(taste_open, "AnthropicTasteBackend", SyntheticBackend)
    monkeypatch.setattr(heartbeat, "AnthropicTasteBackend", SyntheticBackend, raising=False)
    monkeypatch.setattr(heartbeat, "resolve_persistence", lambda args: (None, "synthetic persistence: off"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-no-network-key")

    heartbeat.build_session(args)
    assert len(constructors) == 1
    assert constructors[0]["words_recall"] is True
    assert Path(constructors[0]["log_path"]) == root / "session.jsonl"


def test_heartbeat_prints_the_exact_words_recall_launch_note(tmp_path, monkeypatch, capsys):
    import hamutay.heartbeat as heartbeat
    import hamutay.taste_open as taste_open

    parser, args = isolated_heartbeat_args(heartbeat, tmp_path)
    monkeypatch.setattr(parser, "parse_args", lambda *a, **kw: args)
    monkeypatch.setattr(heartbeat, "build_parser", lambda: parser)
    monkeypatch.setattr(taste_open, "AnthropicTasteBackend", SyntheticBackend)
    monkeypatch.setattr(heartbeat, "AnthropicTasteBackend", SyntheticBackend, raising=False)
    monkeypatch.setattr(heartbeat, "resolve_persistence", lambda args: (None, "synthetic persistence: off"))
    monkeypatch.setattr(heartbeat, "assert_canonical_lock_path", lambda *a, **kw: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-no-network-key")

    class StoppedLoop:
        @staticmethod
        def _emit(payload: dict) -> None:
            print(json.dumps(payload, default=str), flush=True)

        def __init__(self, *a, **kw):
            pass

        def boot(self):
            pass

        def run_forever(self):
            pass

    monkeypatch.setattr(heartbeat, "HeartbeatLoop", StoppedLoop)
    heartbeat.main()
    output = capsys.readouterr().out
    assert "words recall: on (recall_words, search_words over this door's own log)" in output
