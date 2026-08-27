"""Natural wake shape is the default; a resumed log inherits its own shape.

Tony's law (8-27): make the desired behavior the default and add switches
to override it — otherwise a bare restart silently scrambles a subject (the
elder's Sonnet-by-default day). Implementer's TDD tests; Codex validates
separately.
"""
import json

import pytest

from hamutay.taste_open import (
    ExchangeResult,
    OpenTasteSession,
    infer_launch_from_log,
    resolve_launch,
)


def _write_records(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --- the log knows its wake shape ----------------------------------------


def test_infer_launch_reads_wake_mode_from_the_record(tmp_path):
    log = tmp_path / "s.jsonl"
    _write_records(log, [{
        "cycle": 3, "state": {"cycle": 3}, "model": "anthropic/claude-fable-5",
        "launch": {"model": "anthropic/claude-fable-5", "provider": "openrouter",
                   "tools": True},
        "wake_mode": "natural",
    }])
    assert infer_launch_from_log(str(log))["wake_mode"] == "natural"


def test_infer_launch_treats_a_record_without_wake_mode_as_terminal(tmp_path):
    # Every record written before 2026-08-27 ran the terminal shape.
    log = tmp_path / "s.jsonl"
    _write_records(log, [{
        "cycle": 478, "state": {"cycle": 478}, "model": "claude-sonnet-4-6",
        "system_prompt": "- bash(command",
    }])
    assert infer_launch_from_log(str(log))["wake_mode"] == "terminal"


# --- resolve_launch: inherit, override loudly, default per caller ---------


def test_resolve_launch_inherits_wake_mode_when_flag_unset():
    inherited = {"model": "m", "provider": "openrouter", "tools": True,
                 "wake_mode": "terminal", "source_cycle": 17, "inferred": False}
    resolved, notes = resolve_launch(
        {"model": None, "provider": None, "tools": None, "wake_mode": None},
        inherited,
    )
    assert resolved["wake_mode"] == "terminal"
    assert not any(n.startswith("WAKE SHAPE CHANGE") for n in notes)


def test_resolve_launch_explicit_wake_mode_change_is_loud():
    inherited = {"model": "m", "provider": "openrouter", "tools": True,
                 "wake_mode": "terminal", "source_cycle": 17, "inferred": False}
    resolved, notes = resolve_launch(
        {"model": None, "provider": None, "tools": None, "wake_mode": "natural"},
        inherited,
    )
    assert resolved["wake_mode"] == "natural"
    changes = [n for n in notes if n.startswith("WAKE SHAPE CHANGE")]
    assert len(changes) == 1
    assert "cycle 17" in changes[0]
    assert "wake_mode='terminal'" in changes[0]
    assert "wake_mode='natural'" in changes[0]


def test_resolve_launch_defaults_are_the_callers_choice():
    resolved, _ = resolve_launch(
        {"model": None, "provider": None, "tools": None, "wake_mode": None},
        None,
        defaults={"model": "anthropic/claude-haiku-4-5", "provider": "openrouter",
                  "tools": True, "wake_mode": "natural"},
    )
    assert resolved == {
        "model": "anthropic/claude-haiku-4-5", "provider": "openrouter",
        "tools": True, "wake_mode": "natural",
    }


def test_resolve_launch_without_wake_mode_key_is_unchanged():
    # Callers that don't know about wake shape (older code paths) still get
    # exactly the three historical keys.
    resolved, _ = resolve_launch(
        {"model": "x", "provider": "anthropic", "tools": False}, None
    )
    assert resolved == {"model": "x", "provider": "anthropic", "tools": False}


# --- heartbeat: natural by default, inherit on restart --------------------


def test_heartbeat_parser_launch_flags_default_to_inherit():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x.jsonl"])
    assert args.model is None
    assert args.provider is None
    assert args.wake_mode is None


def test_heartbeat_fresh_log_launches_natural_haiku_on_openrouter(tmp_path):
    from hamutay.heartbeat import build_parser, resolve_heartbeat_launch

    args = build_parser().parse_args(["--log-path", str(tmp_path / "new.jsonl")])
    launch, notes = resolve_heartbeat_launch(args)
    assert launch["wake_mode"] == "natural"
    assert launch["provider"] == "openrouter"
    assert launch["model"] == "anthropic/claude-haiku-4-5"
    assert launch["tools"] is True


def test_heartbeat_restart_inherits_terminal_shape_from_the_log(tmp_path):
    from hamutay.heartbeat import build_parser, resolve_heartbeat_launch

    log = tmp_path / "resident.jsonl"
    _write_records(log, [{
        "cycle": 18, "state": {"cycle": 18}, "model": "anthropic/claude-fable-5",
        "launch": {"model": "anthropic/claude-fable-5", "provider": "openrouter",
                   "tools": True},
        "wake_mode": "terminal",
    }])
    args = build_parser().parse_args(["--log-path", str(log)])
    launch, notes = resolve_heartbeat_launch(args)
    assert launch["wake_mode"] == "terminal"
    assert launch["model"] == "anthropic/claude-fable-5"
    assert not any(n.startswith("WAKE SHAPE CHANGE") for n in notes)


def test_heartbeat_explicit_switch_is_loud(tmp_path):
    from hamutay.heartbeat import build_parser, resolve_heartbeat_launch

    log = tmp_path / "resident.jsonl"
    _write_records(log, [{
        "cycle": 18, "state": {"cycle": 18}, "model": "anthropic/claude-fable-5",
        "launch": {"model": "anthropic/claude-fable-5", "provider": "openrouter",
                   "tools": True},
        "wake_mode": "terminal",
    }])
    args = build_parser().parse_args(
        ["--log-path", str(log), "--wake-mode", "natural"]
    )
    launch, notes = resolve_heartbeat_launch(args)
    assert launch["wake_mode"] == "natural"
    assert any(n.startswith("WAKE SHAPE CHANGE") for n in notes)


def test_heartbeat_rejects_unknown_wake_mode():
    from hamutay.heartbeat import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(["--log-path", "x.jsonl", "--wake-mode", "weird"])


# --- the marker the Fable resident asked for ------------------------------


class _Backend:
    def __init__(self, mode):
        self.wake_mode = mode

    def call(self, model, system, messages, experiment_label,
             extra_tools=None, tool_executor=None):
        return ExchangeResult(raw_output={"response": "r"})


def _session(tmp_path, mode, log_name="s.jsonl", resume=False):
    return OpenTasteSession(
        model="m", backend=_Backend(mode), log_path=str(tmp_path / log_name),
        enable_tools=True, project_root=tmp_path, wake_mode=mode, resume=resume,
    )


def test_first_wake_writes_wake_shape_marker(tmp_path):
    s = _session(tmp_path, "natural")
    s.exchange("hi")
    assert s._state["_wake_shape"] == {"mode": "natural", "since_cycle": 1}


def test_marker_is_stable_while_the_shape_is_unchanged(tmp_path):
    s = _session(tmp_path, "natural")
    s.exchange("hi")
    s.exchange("again")
    assert s._state["_wake_shape"] == {"mode": "natural", "since_cycle": 1}


def test_marker_moves_when_a_resumed_subject_changes_shape(tmp_path):
    s = _session(tmp_path, "terminal")
    s.exchange("hi")
    s.exchange("still terminal")
    switched = _session(tmp_path, "natural", resume=True)
    switched.exchange("now natural")
    assert switched._state["_wake_shape"] == {"mode": "natural", "since_cycle": 3}
    record = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert record["wake_mode"] == "natural"
    assert record["state"]["_wake_shape"]["since_cycle"] == 3


# --- the interactive CLI (the elder's harness) exposes it too ------------


def test_interactive_cli_help_documents_wake_mode_inheritance():
    import subprocess
    import sys
    from pathlib import Path as _P

    completed = subprocess.run(
        [sys.executable, "-m", "hamutay.taste_open", "--help"],
        cwd=_P(__file__).resolve().parents[1],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--wake-mode {terminal,natural}" in completed.stdout
    compact = "".join(completed.stdout.split())
    assert "WAKESHAPECHANGE" in compact
