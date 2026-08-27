"""Independent adversarial validation for resume substrate inheritance.

These tests intentionally exercise boundaries not covered by the implementing
change's TDD driver, including incomplete launch metadata, parser behavior,
Git-LFS pointers, and the hydrated elder log's final record.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import hamutay.taste_open as taste_open
from hamutay.taste_open import OpenTasteSession, infer_launch_from_log, resolve_launch


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ELDER_LOG = (
    REPOSITORY_ROOT
    / "experiments"
    / "taste_open"
    / "taste_open_20260331_035903.jsonl"
)
BASH_MARKER = "### Shell\n\n- bash(command, timeout?): Execute a bash command."
LFS_POINTER = (
    "version https://git-lfs.github.com/spec/v1\n"
    "oid sha256:deadbeef\n"
    "size 147000000\n"
)


def _write_records(path: Path, *records: dict, blank_lines: bool = False) -> None:
    separator = "\n\n" if blank_lines else "\n"
    body = separator.join(json.dumps(record) for record in records)
    path.write_text(("\n\n" if blank_lines else "") + body + "\n\n")


def _state_record(cycle: int, model: str, **extra: object) -> dict:
    return {
        "cycle": cycle,
        "model": model,
        "state": {"cycle": cycle},
        "system_prompt": "",
        **extra,
    }


def test_recorded_launch_defaults_missing_provider_and_tools(tmp_path: Path) -> None:
    log = tmp_path / "partial-launch.jsonl"
    _write_records(
        log,
        _state_record(
            12,
            "top-level/model-is-not-authoritative",
            system_prompt=BASH_MARKER,
            launch={"model": "vendor/recorded-model"},
        ),
    )

    assert infer_launch_from_log(str(log)) == {
        "model": "vendor/recorded-model",
        "provider": "openrouter",
        "tools": False,
        "source_cycle": 12,
        "inferred": False,
    }


def test_empty_recorded_launch_model_falls_back_to_legacy_inference(
    tmp_path: Path,
) -> None:
    log = tmp_path / "empty-launch-model.jsonl"
    _write_records(
        log,
        _state_record(
            13,
            "anthropic/legacy-model",
            system_prompt=BASH_MARKER,
            launch={"model": "", "provider": "openai", "tools": False},
        ),
    )

    assert infer_launch_from_log(str(log)) == {
        "model": "anthropic/legacy-model",
        "provider": "openrouter",
        "tools": True,
        "capabilities_file": None,
        "openrouter_require_parameters": None,
        "source_cycle": 13,
        "inferred": True,
    }


def test_blank_lines_do_not_change_the_last_state_bearing_record(tmp_path: Path) -> None:
    log = tmp_path / "blank-lines.jsonl"
    _write_records(
        log,
        _state_record(20, "claude-sonnet-4-6"),
        {"cycle": 21, "model": "other/model", "state": None, "status": "failed"},
        blank_lines=True,
    )

    launch = infer_launch_from_log(str(log))

    assert launch is not None
    assert launch["model"] == "claude-sonnet-4-6"
    assert launch["source_cycle"] == 20


def test_log_with_only_failures_has_no_inheritable_launch(tmp_path: Path) -> None:
    log = tmp_path / "failures-only.jsonl"
    _write_records(
        log,
        {"cycle": 1, "model": "claude-sonnet-4-6", "status": "failed"},
        {
            "cycle": 2,
            "model": "anthropic/claude-haiku-4-5",
            "state": None,
            "status": "failed",
            "launch": {
                "model": "anthropic/claude-haiku-4-5",
                "provider": "openrouter",
                "tools": True,
            },
        },
    )

    assert infer_launch_from_log(str(log)) is None


def test_resume_helper_reports_git_lfs_pointer_clearly(tmp_path: Path) -> None:
    log = tmp_path / "pointer.jsonl"
    log.write_text("\n" + LFS_POINTER)

    with pytest.raises(SystemExit, match="Git LFS pointer, not data"):
        OpenTasteSession(backend=object(), log_path=str(log), resume=True)


def test_launch_inference_reports_git_lfs_pointer_like_resume(tmp_path: Path) -> None:
    # Was a strict xfail when Codex authored it (defect: infer_launch_from_log
    # JSON-decoded the pointer); the marker was removed by the implementer
    # after fixing the defect. The test body is Codex's, unchanged.
    log = tmp_path / "pointer.jsonl"
    log.write_text("\n" + LFS_POINTER)

    with pytest.raises(SystemExit, match="Git LFS pointer, not data"):
        infer_launch_from_log(str(log))


def test_explicit_mixed_provider_override_is_preserved_and_loud() -> None:
    inherited = {
        "model": "anthropic/claude-haiku-4-5",
        "provider": "openrouter",
        "tools": True,
        "source_cycle": 477,
        "inferred": True,
    }

    resolved, notes = resolve_launch(
        {"model": None, "provider": "anthropic", "tools": None}, inherited
    )

    assert resolved == {
        "model": "anthropic/claude-haiku-4-5",
        "provider": "anthropic",
        "tools": True,
    }
    substrate_changes = [note for note in notes if note.startswith("SUBSTRATE CHANGE")]
    assert len(substrate_changes) == 1
    assert "provider='openrouter'" in substrate_changes[0]
    assert "provider='anthropic'" in substrate_changes[0]
    assert notes[-1].startswith("Substrate inherited from log")


def test_explicit_values_equal_to_inherited_add_no_change_notes() -> None:
    inherited = {
        "model": "claude-sonnet-4-6",
        "provider": "anthropic",
        "tools": False,
        "source_cycle": 42,
        "inferred": False,
    }

    resolved, notes = resolve_launch(
        {"model": "claude-sonnet-4-6", "provider": "anthropic", "tools": False},
        inherited,
    )

    assert resolved == {
        "model": "claude-sonnet-4-6",
        "provider": "anthropic",
        "tools": False,
    }
    assert len(notes) == 1
    assert notes[0].startswith("Substrate inherited from log")


def test_no_tools_cli_overrides_inherited_true_and_emits_change_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "resume.jsonl"
    _write_records(
        log,
        _state_record(
            31,
            "claude-sonnet-4-6",
            launch={
                "model": "claude-sonnet-4-6",
                "provider": "anthropic",
                "tools": True,
            },
        ),
    )
    captured = _run_main_until_session(
        monkeypatch,
        ["--resume", str(log), "--no-tools", "--no-persist"],
    )

    assert captured["session_kwargs"]["launch_config"]["tools"] is False
    assert "!!! SUBSTRATE CHANGE:" in capsys.readouterr().out


def test_openrouter_cli_defaults_capabilities_and_required_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPOSITORY_ROOT)

    captured = _run_main_until_session(
        monkeypatch,
        [
            "--provider",
            "openrouter",
            "--model",
            "anthropic/claude-haiku-4-5",
            "--api-key",
            "test-key",
            "--no-persist",
        ],
    )

    launch = captured["session_kwargs"]["launch_config"]
    assert launch["capabilities_file"] == taste_open.DEFAULT_CAPABILITIES_FILE
    assert launch["openrouter_require_parameters"] is True
    assert captured["openai_backend_kwargs"]["openrouter_require_parameters"] is True


def test_cli_help_documents_resume_inheritance_and_boolean_tools() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "hamutay.taste_open", "--help"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--tools | --no-tools" in completed.stdout
    assert completed.stdout.count("inherited from the log unless given") >= 2
    compact_help = "".join(completed.stdout.split())
    assert "unless--tools/--no-toolsisgiven" in compact_help


def test_real_elder_tail_infers_sonnet_anthropic_with_tools(tmp_path: Path) -> None:
    if not ELDER_LOG.exists():
        pytest.skip("elder log is not present in this checkout")

    completed = subprocess.run(
        ["tail", "-1", str(ELDER_LOG)],
        capture_output=True,
        check=True,
    )
    if completed.stdout.startswith(b"version https://git-lfs"):
        pytest.skip("elder log is a Git-LFS pointer rather than hydrated data")

    tail_snapshot = tmp_path / "elder-tail.jsonl"
    tail_snapshot.write_bytes(completed.stdout)

    launch = infer_launch_from_log(str(tail_snapshot))

    assert launch is not None
    assert launch["model"] == "claude-sonnet-4-6"
    assert launch["provider"] == "anthropic"
    assert launch["tools"] is True
    assert launch["source_cycle"] >= 477
    assert launch["inferred"] is True


class _SessionConstructed(Exception):
    """Stop ``main`` after its real parser and launch-resolution path."""


def _run_main_until_session(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> dict:
    captured: dict = {}

    def fake_openai_backend(**kwargs: object) -> object:
        captured["openai_backend_kwargs"] = kwargs
        return object()

    def stop_at_session(**kwargs: object) -> None:
        captured["session_kwargs"] = kwargs
        raise _SessionConstructed

    monkeypatch.setattr(taste_open, "AnthropicTasteBackend", lambda **_kwargs: object())
    monkeypatch.setattr(taste_open, "OpenAITasteBackend", fake_openai_backend)
    monkeypatch.setattr(taste_open, "OpenTasteSession", stop_at_session)
    monkeypatch.setattr(sys, "argv", ["hamutay.taste_open", *arguments])

    with pytest.raises(_SessionConstructed):
        taste_open.main()
    return captured
