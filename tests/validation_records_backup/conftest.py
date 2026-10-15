"""Temporary filesystem and subprocess harness for the public shell interfaces."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

import pytest


REPO = Path(__file__).resolve().parents[2]
BACKUP = REPO / "deploy" / "backup-records.sh"
CHECKER = REPO / "deploy" / "check-backup.sh"
RUN_RE = re.compile(r"20\d{6}T\d{6}Z")
HOST = "records-validation.invalid"


def tree_state(root):
    """Ignore access times, but detect content, entries, modes and mtime changes."""
    if not root.exists():
        return None
    state = {}
    for path in [root, *sorted(root.rglob("*"))]:
        stat = path.lstat()
        state[path.relative_to(root).as_posix()] = (
            stat.st_mode,
            stat.st_mtime_ns,
            path.read_bytes() if path.is_file() else None,
        )
    return state


def payload(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def log_rows(path):
    if not path.exists():
        return []
    raw = path.read_bytes()
    if not raw:
        return []
    assert raw.endswith(b"\n"), f"status log lacks a final newline: {path}"
    rows = [json.loads(line) for line in raw.splitlines()]
    assert all(isinstance(row, dict) for row in rows), rows
    return rows


def run_dirs(root):
    return sorted(p.name for p in root.iterdir() if p.is_dir() and RUN_RE.fullmatch(p.name))


class BackupHarness:
    def __init__(self, base):
        self.base = base
        self.src = base / "source"
        self.local = base / "local"
        self.home = base / "home"
        self.remote_home = base / "remote-home"
        self.bin = base / "bin"
        self.state = base / "shim-state"
        for path in (self.src, self.local, self.home, self.remote_home, self.bin, self.state):
            path.mkdir()
        self.real = {}
        for name in ("rsync", "cp", "sha256sum"):
            executable = shutil.which(name)
            assert executable, f"validation prerequisite missing: {name}"
            self.real[name] = executable
        self.env = os.environ.copy()
        for key in ("BASH_ENV", "ENV", "CDPATH", "RSYNC_RSH", "RECORDS_TEST_FAULT",
                    "RECORDS_TEST_ON_REMOTE", "SHELLOPTS", "BASHOPTS"):
            self.env.pop(key, None)
        self.env.update(
            SRC=str(self.src), LOCAL_ROOT=str(self.local),
            REMOTE=HOST, REMOTE_ROOT="backups/records", KEEP="14",
            HOME=str(self.home), TMPDIR=str(base), LC_ALL="C", TZ="UTC",
            PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
            RECORDS_TEST_BASE=str(base), RECORDS_TEST_REMOTE_HOME=str(self.remote_home),
            RECORDS_TEST_REAL_RSYNC=self.real["rsync"],
            RECORDS_TEST_REAL_CP=self.real["cp"],
            RECORDS_TEST_REAL_SHA256SUM=self.real["sha256sum"],
        )
        shim = Path(__file__).with_name("_shim.py")
        for name in ("ssh", "rsync", "scp", "sha256sum"):
            executable = self.bin / name
            executable.write_text(
                "#!/bin/bash\nexec " + shlex.quote(sys.executable) + " "
                + shlex.quote(str(shim)) + " " + name + ' "$@"\n'
            )
            executable.chmod(0o755)
        self.last_second = None
        self.started = None
        self.ended = None

    @property
    def remote(self):
        return self.remote_home / self.env.get("REMOTE_ROOT", "backups/records")

    def write(self, relative, data):
        path = self.src / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        # Deliberately old, distinct source times reveal rewrites/touch operations.
        os.utime(path, ns=(1_650_000_000_123_456_789, 1_650_000_000_123_456_789))
        return path

    def tool(self, *args, input=None):
        return subprocess.run(
            args, cwd=self.home, env=self.env, text=True, input=input,
            capture_output=True, timeout=30,
        )

    def run(self):
        assert BACKUP.is_file(), f"contract script is absent: {BACKUP}"
        while int(time.time()) == self.last_second:
            time.sleep(0.02)
        self.last_second = int(time.time())
        before = tree_state(self.src)
        previous = log_rows(self.local / "backup-log.jsonl")
        self.started = datetime.now(timezone.utc)
        try:
            result = subprocess.run(
                ["bash", str(BACKUP)], cwd=REPO, env=self.env,
                text=True, capture_output=True, timeout=45,
            )
        finally:
            self.ended = datetime.now(timezone.utc)
            assert tree_state(self.src) == before, "backup modified source bytes, entries, mode or mtime"
        rows = log_rows(self.local / "backup-log.jsonl")
        assert rows[:-1] == previous and len(rows) == len(previous) + 1, (
            "each run must append exactly one status JSON line", result, rows
        )
        return result, rows[-1]

    def ok(self, partial=()):
        result, row = self.run()
        assert result.returncode == 0, (result.stdout, result.stderr, row)
        assert row["status"] == "ok" and row["stage"] == "done", row
        assert RUN_RE.fullmatch(row["run"]), row
        timestamp = datetime.strptime(row["run"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        assert self.started.replace(microsecond=0) <= timestamp <= self.ended, row
        assert isinstance(row["finished"], str) and row["finished"].endswith("Z"), row
        finished = datetime.fromisoformat(row["finished"].replace("Z", "+00:00"))
        assert self.started.replace(microsecond=0) <= finished <= self.ended, row
        assert type(row["bytes"]) is int and row["bytes"] >= 0, row
        assert type(row["files"]) is int, row
        assert isinstance(row["partial_tail"], list), row
        assert all(isinstance(p, str) for p in row["partial_tail"]), row
        assert sorted(row["partial_tail"]) == sorted(partial), row
        root = self.env.get("REMOTE_ROOT", "backups/records").rstrip("/")
        assert row["remote"] == f"{HOST}:{root}/{row['run']}", row
        expected = payload(self.src)
        for snapshot in (self.local / row["run"], self.remote / row["run"]):
            assert payload(snapshot / "community") == expected, snapshot
            assert (snapshot / "community").is_dir(), snapshot
            manifest = snapshot / "MANIFEST.sha256"
            assert manifest.is_file(), snapshot
            lines = manifest.read_text().splitlines()
            expected_lines = [
                f"{hashlib.sha256(data).hexdigest()}  community/{name}"
                for name, data in sorted(expected.items())
            ]
            # sha256sum also permits '*' (binary) instead of the text-mode space.
            normalized = [line[:65] + " " + line[66:] if line[65:66] == "*" else line for line in lines]
            assert normalized == expected_lines, (snapshot, lines, expected_lines)
            assert row["files"] == len(lines), row
            if lines:  # GNU sha256sum -c treats an empty manifest as an error.
                checked = subprocess.run(
                    [self.real["sha256sum"], "-c", "MANIFEST.sha256"],
                    cwd=snapshot, capture_output=True, text=True, timeout=15,
                )
                assert checked.returncode == 0, (checked.stdout, checked.stderr)
        assert (self.remote / "backup-log.jsonl").read_bytes() == (self.local / "backup-log.jsonl").read_bytes()
        return row

    def fails(self, stage):
        result, row = self.run()
        assert result.returncode != 0, (result.stdout, result.stderr, row)
        assert row.get("status") == "failed" and row.get("stage") == stage, (
            row, result.stdout, result.stderr
        )
        return row

    def seed(self, root, names):
        for index, name in enumerate(names):
            directory = root / name
            community = directory / "community"
            community.mkdir(parents=True)
            for relative, data in payload(self.src).items():
                destination = community / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.src / relative, destination)
            (directory / "MANIFEST.sha256").write_text("".join(
                f"{hashlib.sha256(data).hexdigest()}  community/{relative}\n"
                for relative, data in sorted(payload(self.src).items())
            ))
            os.utime(directory, (1_700_000_000 - index, 1_700_000_000 - index))


@pytest.fixture
def backup(tmp_path):
    return BackupHarness(tmp_path)


@pytest.fixture
def checker(backup):
    class CheckerHarness:
        arango = backup.base / "arango"
        records = backup.base / "records-check"

        def write(self, root, filename, rows):
            root.mkdir(exist_ok=True)
            (root / filename).write_text("".join(json.dumps(row) + "\n" for row in rows))

        def record(self, age, status="ok"):
            from datetime import timedelta
            finished = datetime.now(timezone.utc) - timedelta(seconds=age)
            return {"status": status, "finished": finished.isoformat().replace("+00:00", "Z")}

        def healthy(self):
            self.write(self.arango, "backup-log.jsonl", [self.record(3600)])
            self.write(self.arango, "restore-log.jsonl", [self.record(86400)])
            self.write(self.records, "backup-log.jsonl", [self.record(3600)])

        def run(self):
            assert CHECKER.is_file(), f"checker script is absent: {CHECKER}"
            env = dict(backup.env, LOCAL_ROOT=str(self.arango), RECORDS_ROOT=str(self.records))
            before = {root: tree_state(root) for root in (self.arango, self.records)}
            result = subprocess.run(
                ["bash", str(CHECKER)], cwd=REPO, env=env,
                text=True, capture_output=True, timeout=20,
            )
            assert {root: tree_state(root) for root in before} == before, "checker modified its input logs"
            return result

    harness = CheckerHarness()
    harness.healthy()
    return harness
