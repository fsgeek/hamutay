"""Spec test 7: process evidence, capability probe, and fail-closed census."""
import builtins
import io
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from hamutay.assembly.ledger import LedgerMalformed
from hamutay.plaza import mcp, records

from .helpers import STAMP, api

BOOT = "11111111-2222-4333-8444-555555555555"
START = 98765


@pytest.fixture
def census(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    boot = tmp_path / "boot-id"
    boot.write_text(BOOT + "\n")
    root = tmp_path / "house"
    (root / "community/plaza/readers").mkdir(parents=True)
    return root, proc, boot


def process(proc, pid, *, wrapper=False, start=START, label="levadura"):
    path = proc / str(pid)
    path.mkdir()
    argv = (["uv", "run", "python", "-m", "hamutay.plaza.mcp", "--guest", label] if wrapper else
            [sys.executable, "-m", "hamutay.plaza.mcp", "--guest", label])
    (path / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
    # Fields 3–21: state plus 18 numeric fields; then starttime at field 22.
    # Embedded spaces and ')' expose parsers that naively split the whole stat.
    (path / "stat").write_text(f"{pid} (python worker) odd)) S " + " ".join(["0"] * 18) + f" {start} 0\n")
    (path / "exe").symlink_to((shutil.which("uv") or "/usr/bin/uv") if wrapper else sys.executable)
    (path / "comm").write_text("uv\n" if wrapper else "python\n")
    (path / "status").write_text(f"Name:\t{'uv' if wrapper else 'python'}\nPid:\t{pid}\n")
    return path


def record(root, file_pid, **updates):
    body = {"pid": file_pid, "label": "levadura", "boot_id": BOOT, "proc_start": START,
            "accepts": ["carrier"], "written_at": STAMP}
    body.update(updates)
    (root / f"community/plaza/readers/mcp-{file_pid}.json").write_text(json.dumps(body))


def unready(census):
    root, proc, boot = census
    result = api(mcp, "carrier_unready")(root, proc=proc, boot_id=boot)
    assert isinstance(result, list) and all(isinstance(line, str) for line in result)
    return result


@pytest.mark.parametrize("problem", ["missing", "reused-pid", "other-boot", "old-validator", "malformed", "wrong-pid"])
def test_running_server_requires_matching_capability_evidence(census, problem):
    root, proc, _ = census
    process(proc, 101)
    if problem != "missing":
        updates = {"reused-pid": {"proc_start": START + 1}, "other-boot": {"boot_id": "other-boot"},
                   "old-validator": {"accepts": []}, "wrong-pid": {"pid": 102}, "malformed": {}}[problem]
        record(root, 101, **updates)
        if problem == "malformed":
            (root / "community/plaza/readers/mcp-101.json").write_text("not-json")
    failures = unready(census)
    assert len(failures) == 1
    assert "levadura" in failures[0] and "101" in failures[0] and str(START) in failures[0]


def test_every_failing_server_is_reported(census):
    root, proc, _ = census
    process(proc, 101)
    process(proc, 102, label="arbiter")
    record(root, 102, label="arbiter", accepts=[])
    failures = unready(census)
    assert len(failures) == 2
    assert any("101" in line and "levadura" in line for line in failures)
    assert any("102" in line and "arbiter" in line for line in failures)


def test_matching_servers_pass_and_dead_records_and_uv_wrapper_are_ignored(census):
    root, proc, _ = census
    process(proc, 101)
    process(proc, 102, label="arbiter")
    process(proc, 103, wrapper=True)
    record(root, 101)
    record(root, 102, label="arbiter")
    record(root, 999, boot_id="old-boot", accepts=[])
    assert unready(census) == []


def test_no_live_servers_is_ready_despite_stale_records(census):
    root, _, _ = census
    record(root, 999, accepts=[])
    assert unready(census) == []


def deny_reads(monkeypatch, target, error=PermissionError):
    """Cover normal pathlib and open-based readers without relying on chmod/root."""
    for owner, name in [(Path, "read_bytes"), (Path, "read_text"), (io, "open"), (builtins, "open")]:
        original = getattr(owner, name)
        def denied(path, *args, _original=original, **kwargs):
            if isinstance(path, (str, os.PathLike)) and Path(path) == target:
                raise error(f"test read failure: {target}")
            return _original(path, *args, **kwargs)
        monkeypatch.setattr(owner, name, denied)


@pytest.mark.parametrize("field", ["cmdline", "stat"])
def test_permission_failure_cannot_be_skipped_as_process_exit(census, monkeypatch, field):
    root, proc, _ = census
    path = process(proc, 101)
    record(root, 101)
    deny_reads(monkeypatch, path / field)
    failures = unready(census)
    assert failures and any("101" in line for line in failures)


def test_unreadable_process_census_fails_closed(census, monkeypatch):
    _, proc, _ = census
    original = os.scandir
    def denied(path="."):
        if Path(path) == proc:
            raise PermissionError("restricted process census")
        return original(path)
    original_listdir = os.listdir
    def denied_listdir(path="."):
        if Path(path) == proc:
            raise PermissionError("restricted process census")
        return original_listdir(path)
    monkeypatch.setattr(os, "scandir", denied)
    monkeypatch.setattr(os, "listdir", denied_listdir)
    assert unready(census)


def test_unreadable_boot_identity_cannot_establish_readiness(census, monkeypatch):
    root, proc, boot = census
    process(proc, 101)
    record(root, 101)
    deny_reads(monkeypatch, boot)
    assert unready(census)


def test_confirmed_process_exit_during_scan_is_ignored(census, monkeypatch):
    _, proc, _ = census
    path = process(proc, 101)
    original = Path.read_bytes
    def exiting(file, *args, **kwargs):
        if file == path / "cmdline":
            shutil.rmtree(path)
            raise FileNotFoundError("process exited")
        return original(file, *args, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", exiting)
    # Also support text/open based implementations with the same exit event.
    for owner, name in [(io, "open"), (builtins, "open")]:
        original_open = getattr(owner, name)
        def open_exiting(file, *args, _original=original_open, **kwargs):
            if isinstance(file, (str, os.PathLike)) and Path(file) == path / "cmdline":
                shutil.rmtree(path, ignore_errors=True)
                raise FileNotFoundError("process exited")
            return _original(file, *args, **kwargs)
        monkeypatch.setattr(owner, name, open_exiting)
    assert unready(census) == []


def test_reader_record_has_real_process_identity_and_capability(tmp_path):
    before = Path(f"/proc/{os.getpid()}/stat").read_text().rsplit(")", 1)[1].split()[19]
    path = api(mcp, "write_reader_record")(tmp_path, "levadura")
    assert path == tmp_path / f"community/plaza/readers/mcp-{os.getpid()}.json"
    body = json.loads(path.read_text())
    assert {"pid", "label", "boot_id", "proc_start", "accepts", "written_at"} <= body.keys()
    assert body["pid"] == os.getpid() and body["label"] == "levadura"
    assert str(body["proc_start"]) == before
    assert body["boot_id"].strip() == Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    assert "carrier" in body["accepts"]
    from datetime import datetime, timezone
    assert abs((datetime.now(timezone.utc) - datetime.fromisoformat(body["written_at"])).total_seconds()) < 60


def test_accepts_is_computed_from_loaded_validator(tmp_path, monkeypatch):
    def old_validator(*args, **kwargs):
        raise LedgerMalformed("old validator rejects carrier")
    # Patch the loaded module and any already-imported alias; no private helper.
    monkeypatch.setattr(records, "validate_plaza", old_validator)
    if hasattr(mcp, "validate_plaza"):
        monkeypatch.setattr(mcp, "validate_plaza", old_validator)
    path = api(mcp, "write_reader_record")(tmp_path, "levadura")
    assert path is not None
    assert "carrier" not in json.loads(path.read_text())["accepts"]


def test_record_write_failure_reports_stderr_and_does_not_stop_server(tmp_path, capsys, monkeypatch):
    readers = tmp_path / "community/plaza/readers"
    readers.parent.mkdir(parents=True)
    readers.write_text("file prevents directory creation")
    assert api(mcp, "write_reader_record")(tmp_path, "levadura") is None
    assert capsys.readouterr().err
    ran = []
    class Server:
        def run(self):
            # main must try recording before serving even when the write fails.
            assert capsys.readouterr().err
            ran.append(True)
    monkeypatch.setattr(mcp, "build_server", lambda *args: Server())
    assert mcp.main(["--project-root", str(tmp_path), "--guest", "levadura"]) == 0
    assert ran == [True]


def test_main_writes_evidence_before_serving(tmp_path, monkeypatch):
    api(mcp, "write_reader_record")
    observed = []
    class Server:
        def run(self):
            paths = list((tmp_path / "community/plaza/readers").glob("mcp-*.json"))
            assert len(paths) == 1
            observed.append(json.loads(paths[0].read_text()))
    monkeypatch.setattr(mcp, "build_server", lambda *args: Server())
    assert mcp.main(["--project-root", str(tmp_path), "--guest", "levadura"]) == 0
    assert observed[0]["label"] == "levadura"
