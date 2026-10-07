import fcntl
import io
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from hamutay.plaza import cli
from hamutay.plaza.send import send
from hamutay.viewer import state
from tests.plaza.conftest import T0


def _run(root, *, bare=False, cwd=None):
    args = [] if bare else ["--project-root", str(root)]
    return subprocess.run(
        [sys.executable, "-m", "hamutay.plaza", *args],
        cwd=cwd or root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=15,
    )


def _snapshot(root):
    # Exclude access times: reads may update them. Include directories and mtimes
    # so artifact creation and mutation are visible, even with identical bytes.
    return {
        str(p.relative_to(root)): (
            p.stat().st_mode,
            p.stat().st_mtime_ns,
            p.read_bytes() if p.is_file() else None,
        )
        for p in [root, *root.rglob("*")]
    }


def _jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _event(status, **fields):
    return {
        "record_type": "event_status",
        "event_id": "wake-1",
        "status": status,
        **fields,
    }


def _door_line(output, name):
    matches = re.findall(rf"^  {re.escape(name)}\s+(.+)$", output, re.MULTILINE)
    assert len(matches) == 1, output
    return matches[0]


@pytest.mark.parametrize("bare", [True, False], ids=["no-arguments", "project-root-only"])
def test_no_subcommand_is_a_successful_read_only_overview(house_guests, bare):
    root, cfg, _ = house_guests
    before = _snapshot(root)
    result = _run(root, bare=bare)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    assert "quiet" in result.stdout.lower()
    for name in cfg.members:
        assert "waiting for an event" in _door_line(result.stdout, name)
        assert "last woke never" in _door_line(result.stdout, name)
    assert "Guests" in result.stdout and "levadura" in result.stdout
    assert "send --by tony --to plaza --text" in result.stdout
    assert "read --since-seq" in result.stdout
    assert "send --help" in result.stdout
    assert _snapshot(root) == before


def test_overview_can_read_an_explicit_root_from_another_directory(house, tmp_path):
    root, _, _ = house
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = _run(root, cwd=elsewhere)
    assert result.returncode == 0, result.stderr
    assert "The doors:" in result.stdout


def test_overview_lists_latest_posts_and_delegates_every_door_to_viewer(house_guests, monkeypatch, capsys):
    root, cfg, _ = house_guests
    for i in range(5):
        send(cfg, actor="tony", via="cli", to="plaza", text=f"public-post-{i}\nsecond-line-{i}", now=T0)
    monkeypatch.setattr(cli, "_now", lambda: T0)
    original = state.door_vitals
    calls = []

    def observe(name, events_path, now, *args, **kwargs):
        calls.append((name, events_path, now))
        return original(name, events_path, now, *args, **kwargs)

    monkeypatch.setattr(state, "door_vitals", observe)
    assert cli.main(["--project-root", str(root)]) == 0
    output = capsys.readouterr().out
    assert "latest seq 5" in output
    assert "public-post-0" not in output and "public-post-1" not in output
    assert [output.index(f"public-post-{i}") for i in range(2, 5)] == sorted(
        output.index(f"public-post-{i}") for i in range(2, 5)
    )
    assert "second-line" not in output
    assert calls == [(name, cfg.members[name].events, T0) for name in sorted(cfg.members)]
    assert "levadura" in output


@pytest.mark.parametrize("plaza_kind", ["empty", "posts", "torn-tail"])
def test_existing_plaza_is_not_modified_and_creates_no_lock(house, plaza_kind):
    root, cfg, _ = house
    cfg.plaza.write_bytes(b"")
    if plaza_kind != "empty":
        send(cfg, actor="tony", via="cli", to="plaza", text="preserve this post", now=T0)
        cfg.plaza.with_suffix(".jsonl.lock").unlink()
    if plaza_kind == "torn-tail":
        with cfg.plaza.open("ab") as stream:
            stream.write(b'{"record_type":"message"')
    before = _snapshot(root)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert _snapshot(root) == before, "The overview created or modified a filesystem artifact"


def test_overview_does_not_open_existing_files_for_writing(house, monkeypatch, capsys):
    root, cfg, _ = house
    cfg.plaza.write_bytes(b"")
    cfg.plaza.with_suffix(".jsonl.lock").write_bytes(b"existing lock sentinel")
    original = io.open
    writes = []

    def observe(file, mode="r", *args, **kwargs):
        if isinstance(file, (str, os.PathLike)) and Path(file).is_relative_to(root):
            if any(flag in mode for flag in "wax+"):
                writes.append((str(file), mode))
        return original(file, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", observe)
    assert cli.main(["--project-root", str(root)]) == 0
    capsys.readouterr()
    assert writes == [], f"Overview requested write access: {writes}"


@pytest.mark.parametrize("bad_record", [b"not-json\n", b"null\n", b'{"seq":1}\n'])
def test_malformed_plaza_degrades_to_message_and_still_shows_doors_and_guests(house_guests, bad_record):
    root, cfg, _ = house_guests
    cfg.plaza.write_bytes(bad_record)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert "could not be read" in result.stdout.lower()
    assert "levadura" in result.stdout
    for name in cfg.members:
        _door_line(result.stdout, name)


@pytest.mark.parametrize("failure", ["plaza-directory", "invalid-utf8", "lock-directory"])
def test_unreadable_plaza_degrades_without_a_traceback(house_guests, failure):
    root, cfg, _ = house_guests
    if failure == "plaza-directory":
        cfg.plaza.mkdir()
    elif failure == "invalid-utf8":
        cfg.plaza.write_bytes(b"\xff\n")
    else:
        cfg.plaza.write_bytes(b"")
        cfg.plaza.with_suffix(".jsonl.lock").mkdir()
    result = _run(root)
    assert "Traceback" not in result.stdout + result.stderr, result.stderr
    assert result.returncode == 0, result.stderr
    # A read-only implementation may ignore a broken lock entirely.
    if failure != "lock-directory":
        assert "could not be read" in result.stdout.lower()
    assert "levadura" in result.stdout
    for name in cfg.members:
        _door_line(result.stdout, name)


@pytest.mark.parametrize("target", ["plaza", "lock"])
def test_permission_denied_plaza_degrades_without_escaping(house_guests, monkeypatch, capsys, target):
    root, cfg, _ = house_guests
    cfg.plaza.write_bytes(b"")
    if target == "plaza":
        original = Path.read_bytes

        def denied(path, *args, **kwargs):
            if path == cfg.plaza:
                raise PermissionError("plaza record is unreadable")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_bytes", denied)
    else:
        original = io.open

        def denied(file, *args, **kwargs):
            if Path(file) == cfg.plaza.with_suffix(".jsonl.lock"):
                raise PermissionError("plaza lock is unreadable")
            return original(file, *args, **kwargs)

        monkeypatch.setattr(io, "open", denied)
    assert cli.main(["--project-root", str(root)]) == 0
    output = capsys.readouterr()
    if target == "plaza":
        assert "could not be read" in output.out.lower()
    assert "Traceback" not in output.out + output.err
    assert "levadura" in output.out


def test_busy_plaza_lock_does_not_prevent_a_successful_overview(house_guests):
    root, cfg, _ = house_guests
    cfg.plaza.write_bytes(b"")
    with cfg.plaza.with_suffix(".jsonl.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert "levadura" in result.stdout
    for name in cfg.members:
        _door_line(result.stdout, name)


@pytest.mark.parametrize("destination", ["plaza", "elder"])
def test_displayed_send_command_can_be_copied_as_a_complete_shell_line(house, destination):
    root, _, _ = house
    overview = _run(root)
    assert overview.returncode == 0, overview.stderr
    lines = [line.strip() for line in overview.stdout.splitlines()
             if line.strip().startswith("deploy/ayllu-plaza send ")
             and f"--to {destination} " in line]
    assert len(lines) == 1, overview.stdout
    # Apply ordinary shell tokenization (including # comments), then invoke the
    # same module as the deploy shim without involving uv or an actual checkout.
    args = shlex.split(lines[0], comments=True)[1:]
    result = subprocess.run(
        [sys.executable, "-m", "hamutay.plaza", "--project-root", str(root), *args],
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_real_door_events_show_awake_quiet_and_waiting(house, monkeypatch, capsys):
    root, cfg, _ = house
    _jsonl(cfg.members["elder"].events, [_event("running", started_at=T0.isoformat())])
    _jsonl(cfg.members["fable"].events, [
        _event("completed", completed_at=T0.isoformat(), result_record_id="quiet-wake"),
        {"record_type": "quiet_declaration", "declared_by_record_id": "quiet-wake",
         "until": "2026-09-21T12:00:00+00:00", "reason": "rest"},
    ])
    _jsonl(cfg.members["qwen"].events, [_event("failed", failed_at=T0.isoformat())])
    monkeypatch.setattr(cli, "_now", lambda: T0)
    assert cli.main(["--project-root", str(root)]) == 0
    output = capsys.readouterr().out
    assert "awake now" in _door_line(output, "elder")
    assert "quiet by its own choice until 2026-09-21" in _door_line(output, "fable")
    assert "last woke just now" in _door_line(output, "fable")
    assert "waiting for an event" in _door_line(output, "qwen")
    assert "last woke just now" in _door_line(output, "qwen")


@pytest.mark.parametrize("until,quiet", [
    ("2026-09-20T05:30:00-07:00", True),  # 12:30 UTC, still in force
    ("2026-09-20T13:00:00+02:00", False),  # 11:00 UTC, expired
    ("2026-09-20T12:00:00+00:00", False),  # expiration is exclusive
])
def test_quiet_expiration_compares_instants_not_iso_strings(house, monkeypatch, capsys, until, quiet):
    root, cfg, _ = house
    _jsonl(cfg.members["elder"].events, [
        _event("completed", completed_at=T0.isoformat(), result_record_id="quiet-wake"),
        {"record_type": "quiet_declaration", "declared_by_record_id": "quiet-wake",
         "until": until, "reason": "rest"},
    ])
    monkeypatch.setattr(cli, "_now", lambda: T0)
    assert cli.main(["--project-root", str(root)]) == 0
    output = capsys.readouterr().out
    line = _door_line(output, "elder")
    assert ("quiet by its own choice" in line) is quiet
    if not quiet:
        assert "waiting for an event" in line


@pytest.mark.parametrize("failure", ["directory", "permission-denied"])
def test_one_unreadable_door_does_not_hide_healthy_doors(house_guests, monkeypatch, capsys, failure):
    root, cfg, _ = house_guests
    bad_events = cfg.members["elder"].events  # first door in sorted order
    if failure == "directory":
        bad_events.mkdir()
    else:
        original = Path.read_bytes

        def denied(path, *args, **kwargs):
            if path == bad_events:
                raise PermissionError("door record is unreadable")
            return original(path, *args, **kwargs)

        bad_events.write_bytes(b"")
        monkeypatch.setattr(Path, "read_bytes", denied)
    assert cli.main(["--project-root", str(root)]) == 0
    output = capsys.readouterr()
    assert "unavailable" in output.out.lower()
    assert "Traceback" not in output.out + output.err
    assert "levadura" in output.out
    for name in ("fable", "qwen"):
        assert "waiting for an event" in _door_line(output.out, name)
    assert "elder" in output.out
