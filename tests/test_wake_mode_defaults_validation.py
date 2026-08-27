"""Adversarial validation for wake-shape defaults, inheritance, and markers.

These tests intentionally cover boundaries outside the implementer's
``test_wake_mode_defaults.py`` suite.  Production code is not modified by this
validation file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from hamutay.taste_open import (
    ExchangeResult,
    OpenTasteSession,
    infer_launch_from_log,
    resolve_launch,
)
from hamutay.tools import ToolExecutor


HEARTBEAT_DEFAULT = {
    "model": "anthropic/claude-haiku-4-5",
    "provider": "openrouter",
    "tools": True,
    "wake_mode": "natural",
}


def _write_records(path: Path, *records: dict) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def _state_record(cycle: int, *, wake_mode: object = "terminal", **extra) -> dict:
    record = {
        "cycle": cycle,
        "model": "anthropic/claude-fable-5",
        "state": {"cycle": cycle},
        "system_prompt": "",
        **extra,
    }
    if wake_mode is not _MISSING:
        record["wake_mode"] = wake_mode
    return record


class _Missing:
    pass


_MISSING = _Missing()


class _OutputBackend:
    """Deterministic boundary fake: only the remote model call is replaced."""

    def __init__(self, mode: str, *raw_outputs: dict):
        self.wake_mode = mode
        self._raw_outputs = iter(raw_outputs)

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        return ExchangeResult(raw_output=next(self._raw_outputs))


def _session(
    tmp_path: Path,
    mode: str,
    *raw_outputs: dict,
    log_name: str = "session.jsonl",
    resume: bool = False,
) -> OpenTasteSession:
    return OpenTasteSession(
        model="m",
        backend=_OutputBackend(mode, *raw_outputs),
        log_path=str(tmp_path / log_name),
        enable_tools=True,
        project_root=tmp_path,
        wake_mode=mode,
        resume=resume,
    )


# --- infer_launch_from_log -------------------------------------------------


@pytest.mark.parametrize("logged_wake_mode", [_MISSING, None, ""])
def test_infer_launch_treats_missing_null_and_blank_wake_modes_as_legacy_terminal(
    tmp_path: Path, logged_wake_mode: object
) -> None:
    log = tmp_path / "legacy.jsonl"
    _write_records(
        log,
        _state_record(
            41,
            wake_mode=logged_wake_mode,
            launch={
                "model": "anthropic/claude-fable-5",
                "provider": "openrouter",
                "tools": True,
            },
        ),
    )

    launch = infer_launch_from_log(str(log))

    assert launch is not None
    assert launch["wake_mode"] == "terminal"


def test_infer_launch_keeps_wake_mode_without_a_launch_dictionary(
    tmp_path: Path,
) -> None:
    log = tmp_path / "pre-launch-metadata.jsonl"
    _write_records(log, _state_record(7, wake_mode="natural", launch=None))

    launch = infer_launch_from_log(str(log))

    assert launch is not None
    assert launch["wake_mode"] == "natural"
    assert launch["inferred"] is True


def test_infer_launch_ignores_failure_record_with_a_different_wake_mode(
    tmp_path: Path,
) -> None:
    log = tmp_path / "failed-retry.jsonl"
    _write_records(
        log,
        _state_record(12, wake_mode="natural"),
        {
            "cycle": 13,
            "model": "claude-sonnet-4-6",
            "state": None,
            "wake_mode": "terminal",
            "launch": {
                "model": "claude-sonnet-4-6",
                "provider": "anthropic",
                "tools": False,
                "wake_mode": "terminal",
            },
            "status": "failed",
        },
    )

    launch = infer_launch_from_log(str(log))

    assert launch is not None
    assert launch["source_cycle"] == 12
    assert launch["wake_mode"] == "natural"


# --- resolve_launch --------------------------------------------------------


def test_resolve_launch_distinguishes_absent_key_from_explicit_none() -> None:
    without_key, _ = resolve_launch({}, None, defaults=HEARTBEAT_DEFAULT)
    with_none, _ = resolve_launch({"wake_mode": None}, None, defaults=HEARTBEAT_DEFAULT)

    assert without_key == {}
    assert with_none == {"wake_mode": "natural"}


def test_resolve_launch_partial_defaults_override_only_named_defaults() -> None:
    resolved, notes = resolve_launch(
        {"model": None, "provider": None, "tools": None, "wake_mode": None},
        None,
        defaults={"wake_mode": "natural"},
    )

    assert resolved == {
        "model": "claude-sonnet-4-6",
        "provider": "anthropic",
        "tools": False,
        "wake_mode": "natural",
    }
    assert notes == []


def test_resolve_launch_old_inherited_dict_defaults_missing_shape_to_terminal() -> None:
    """An old resume must not receive the new-session natural default."""
    inherited = {
        "model": "anthropic/claude-fable-5",
        "provider": "openrouter",
        "tools": True,
        "source_cycle": 478,
        "inferred": True,
    }

    resolved, _ = resolve_launch(
        {"wake_mode": None}, inherited, defaults={"wake_mode": "natural"}
    )

    assert resolved["wake_mode"] == "terminal", (
        "a pre-wake_mode inherited launch describes a terminal subject; "
        "caller defaults are only for brand-new subjects"
    )


def test_resolve_launch_wake_shape_change_note_is_separate_and_specific() -> None:
    inherited = {
        "wake_mode": "terminal",
        "source_cycle": 22,
        "inferred": False,
    }

    resolved, notes = resolve_launch({"wake_mode": "natural"}, inherited)

    assert resolved == {"wake_mode": "natural"}
    assert notes[0] == (
        "WAKE SHAPE CHANGE: log's cycle 22 ran with wake_mode='terminal'; "
        "launching with wake_mode='natural'"
    )
    assert not notes[0].startswith("SUBSTRATE CHANGE")


def test_resolve_launch_inheritance_summary_lists_only_requested_keys() -> None:
    inherited = {
        "model": "hidden-model",
        "provider": "openrouter",
        "tools": True,
        "wake_mode": "natural",
        "source_cycle": 9,
        "inferred": False,
    }

    resolved, notes = resolve_launch({"provider": None, "wake_mode": None}, inherited)

    assert resolved == {"provider": "openrouter", "wake_mode": "natural"}
    assert notes == [
        "Substrate inherited from log (cycle 9, recorded in the record): "
        "provider='openrouter', wake_mode='natural'"
    ]


# --- heartbeat launch resolution and refusal ------------------------------


def _heartbeat_args(*argv: str):
    from hamutay.heartbeat import build_parser

    return build_parser().parse_args(list(argv))


def test_heartbeat_fresh_log_defaults_natural_but_legacy_log_inherits_terminal(
    tmp_path: Path,
) -> None:
    from hamutay.heartbeat import resolve_heartbeat_launch

    fresh = tmp_path / "fresh.jsonl"
    legacy = tmp_path / "legacy.jsonl"
    _write_records(legacy, _state_record(88, wake_mode=_MISSING))

    fresh_launch, fresh_notes = resolve_heartbeat_launch(
        _heartbeat_args("--log-path", str(fresh))
    )
    legacy_launch, legacy_notes = resolve_heartbeat_launch(
        _heartbeat_args("--log-path", str(legacy))
    )

    assert fresh_launch == HEARTBEAT_DEFAULT
    assert fresh_notes == []
    assert legacy_launch["wake_mode"] == "terminal"
    assert any(note.startswith("Substrate inherited") for note in legacy_notes)


def test_heartbeat_existing_empty_log_has_no_inherited_shape(tmp_path: Path) -> None:
    from hamutay.heartbeat import resolve_heartbeat_launch

    log = tmp_path / "empty.jsonl"
    log.touch()

    launch, notes = resolve_heartbeat_launch(_heartbeat_args("--log-path", str(log)))

    assert launch == HEARTBEAT_DEFAULT
    assert notes == []


def test_heartbeat_failure_only_log_has_no_inherited_shape(tmp_path: Path) -> None:
    from hamutay.heartbeat import resolve_heartbeat_launch

    log = tmp_path / "failures.jsonl"
    _write_records(
        log,
        {
            "cycle": 3,
            "state": None,
            "model": "claude-sonnet-4-6",
            "wake_mode": "terminal",
            "status": "failed",
        },
        {
            "cycle": 4,
            "state": None,
            "model": "anthropic/claude-fable-5",
            "wake_mode": "natural",
            "status": "failed",
        },
    )

    launch, notes = resolve_heartbeat_launch(_heartbeat_args("--log-path", str(log)))

    assert launch == HEARTBEAT_DEFAULT
    assert notes == []


def test_heartbeat_explicit_shape_equal_to_log_has_no_change_note(
    tmp_path: Path,
) -> None:
    from hamutay.heartbeat import resolve_heartbeat_launch

    log = tmp_path / "natural.jsonl"
    _write_records(log, _state_record(5, wake_mode="natural"))

    launch, notes = resolve_heartbeat_launch(
        _heartbeat_args("--log-path", str(log), "--wake-mode", "natural")
    )

    assert launch["wake_mode"] == "natural"
    assert not any(note.startswith("WAKE SHAPE CHANGE") for note in notes)


def test_heartbeat_main_refuses_anthropic_direct_natural_before_backend_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hamutay import heartbeat

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "heartbeat",
            "--log-path",
            str(tmp_path / "fresh.jsonl"),
            "--provider",
            "anthropic",
            "--wake-mode",
            "natural",
        ],
    )

    with pytest.raises(
        SystemExit,
        match="wake_mode=natural is not implemented on the Anthropic-direct backend",
    ):
        heartbeat.main()


# --- framework-authored _wake_shape marker --------------------------------


def test_terminal_only_session_never_creates_a_wake_shape_marker(
    tmp_path: Path,
) -> None:
    session = _session(
        tmp_path,
        "terminal",
        {"response": "one", "remembered": True},
        {"response": "two"},
    )

    session.exchange("one")
    session.exchange("two")

    records = [
        json.loads(line)
        for line in (tmp_path / "session.jsonl").read_text().splitlines()
    ]
    assert "_wake_shape" not in session.state
    assert all("_wake_shape" not in record["state"] for record in records)


def test_natural_session_stamps_cycle_one_in_state_and_durable_record(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path, "natural", {"response": "awake"})

    session.exchange("hello")

    record = json.loads((tmp_path / "session.jsonl").read_text().splitlines()[-1])
    expected = {"mode": "natural", "since_cycle": 1}
    assert session.state["_wake_shape"] == expected
    assert record["state"]["_wake_shape"] == expected
    assert record["wake_mode"] == "natural"


def test_terminal_natural_terminal_round_trip_restamps_each_shape_change(
    tmp_path: Path,
) -> None:
    terminal = _session(tmp_path, "terminal", {"response": "t1"})
    terminal.exchange("terminal")

    natural = _session(
        tmp_path,
        "natural",
        {"response": "n2"},
        resume=True,
    )
    natural.exchange("natural")
    assert natural.state["_wake_shape"] == {
        "mode": "natural",
        "since_cycle": 2,
    }

    terminal_again = _session(
        tmp_path,
        "terminal",
        {"response": "t3"},
        resume=True,
    )
    terminal_again.exchange("terminal again")

    assert terminal_again.state["_wake_shape"] == {
        "mode": "terminal",
        "since_cycle": 3,
    }
    last = json.loads((tmp_path / "session.jsonl").read_text().splitlines()[-1])
    assert last["wake_mode"] == "terminal"
    assert last["state"]["_wake_shape"] == {
        "mode": "terminal",
        "since_cycle": 3,
    }


def test_marker_survives_a_later_state_merge_that_deletes_other_keys(
    tmp_path: Path,
) -> None:
    session = _session(
        tmp_path,
        "natural",
        {"response": "one", "keep": "yes", "discard": "soon"},
        {"response": "two", "deleted_regions": ["discard"]},
    )

    session.exchange("one")
    session.exchange("two")

    assert session.state["_wake_shape"] == {
        "mode": "natural",
        "since_cycle": 1,
    }
    assert session.state["keep"] == "yes"
    assert "discard" not in session.state


@pytest.mark.parametrize(
    "tool_input",
    [
        {"updates": {"_wake_shape": {"mode": "terminal", "since_cycle": -1}}},
        {"deleted_regions": ["_wake_shape"]},
    ],
    ids=["write", "delete"],
)
def test_update_state_rejects_model_writes_to_framework_wake_shape(
    tmp_path: Path, tool_input: dict
) -> None:
    executor = ToolExecutor(project_root=tmp_path, cycle=2)

    result = executor.execute("update_state", tool_input)

    assert "error" in result
    assert executor.pending_state_updates == {"updates": {}, "deleted_regions": []}


class _DeleteMarkerViaUpdateStateBackend:
    wake_mode = "natural"

    def __init__(self):
        self.calls = 0

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        self.calls += 1
        raw_output = {"response": f"cycle {self.calls}"}
        if self.calls == 2:
            tool_executor.execute("update_state", {"deleted_regions": ["_wake_shape"]})
            raw_output["deleted_regions"] = tool_executor.pending_state_updates[
                "deleted_regions"
            ]
        return ExchangeResult(
            raw_output=raw_output,
            tool_activity=tool_executor.activity_log,
        )


def test_deleting_marker_via_update_state_does_not_reset_since_cycle(
    tmp_path: Path,
) -> None:
    session = OpenTasteSession(
        model="m",
        backend=_DeleteMarkerViaUpdateStateBackend(),
        log_path=str(tmp_path / "delete-attempt.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
        wake_mode="natural",
    )
    session.exchange("first")

    session.exchange("try to delete the marker")

    assert session.state["_wake_shape"] == {
        "mode": "natural",
        "since_cycle": 1,
    }, "a rejected model deletion must not make an unchanged shape look newly started"


def test_raw_output_cannot_spoof_framework_wake_shape_metadata(
    tmp_path: Path,
) -> None:
    session = _session(
        tmp_path,
        "natural",
        {
            "response": "spoof",
            "_wake_shape": {"mode": "natural", "since_cycle": -999},
        },
    )

    session.exchange("hello")

    assert session.state["_wake_shape"] == {
        "mode": "natural",
        "since_cycle": 1,
    }, "the framework, not model raw output, owns wake-shape provenance"


def test_resume_terminal_marker_switches_to_natural_at_resumed_cycle(
    tmp_path: Path,
) -> None:
    log = tmp_path / "resumed.jsonl"
    _write_records(
        log,
        {
            "cycle": 14,
            "model": "m",
            "wake_mode": "terminal",
            "state": {
                "cycle": 14,
                "identity": "resident",
                "_wake_shape": {"mode": "terminal", "since_cycle": 10},
            },
        },
    )
    session = _session(
        tmp_path,
        "natural",
        {"response": "resumed"},
        log_name="resumed.jsonl",
        resume=True,
    )

    session.exchange("wake")

    record = json.loads(log.read_text().splitlines()[-1])
    expected = {"mode": "natural", "since_cycle": 15}
    assert session.state["_wake_shape"] == expected
    assert record["state"]["_wake_shape"] == expected
    assert record["wake_mode"] == "natural"
