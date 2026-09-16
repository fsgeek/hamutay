"""The assembly ledger: one JSONL file, one flock, every record sequenced."""
from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class LedgerUnavailable(RuntimeError):
    """The ledger lock could not be taken inside the window."""


class LedgerMalformed(RuntimeError):
    """A line other than the final one does not parse; nothing is written."""


def parse_instant(s: str) -> datetime:
    parsed = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"instant must carry a UTC offset: {s!r}")
    return parsed.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("naive datetime")
    return dt.astimezone(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        # _good_end: byte offset after the last complete line, set by read_unlocked()
        # torn_tail: incomplete final line (no trailing newline), set by read_unlocked()
        self.torn_tail: str | None = None
        self._good_end: int | None = None

    @contextmanager
    def locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a") as h:
            fcntl.flock(h.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(h.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def try_locked(self, timeout_s: float):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout_s
        with self.lock_path.open("a") as h:
            while True:
                try:
                    fcntl.flock(h.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise LedgerUnavailable(f"{self.lock_path} busy for {timeout_s}s")
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(h.fileno(), fcntl.LOCK_UN)

    def signature(self) -> tuple[int, float]:
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return (0, 0.0)
        return (st.st_size, st.st_mtime)

    def read_unlocked(self) -> list[dict]:
        self.torn_tail = None
        if not self.path.exists():
            self._good_end = 0
            return []
        data = self.path.read_bytes()
        records: list[dict] = []
        offset = 0
        for i, raw in enumerate(data.split(b"\n")):
            is_last = (i == data.count(b"\n"))
            if not raw.strip():
                offset += len(raw) + 1
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                if is_last and not data.endswith(b"\n"):
                    self.torn_tail = raw.decode("utf-8", "replace")
                    self._good_end = offset
                    return records
                raise LedgerMalformed(f"{self.path}: bad line at byte {offset}")
            offset += len(raw) + 1
        self._good_end = len(data)
        return records

    def read(self) -> list[dict]:
        with self.locked():
            return self.read_unlocked()

    def next_seq_unlocked(self) -> int:
        records = self.read_unlocked()
        return (max((int(r.get("seq", 0)) for r in records), default=0)) + 1

    def append_unlocked(self, record: dict) -> dict:
        """One line: seq, write, flush, fsync, verify growth. Caller holds the lock."""
        seq = self.next_seq_unlocked()          # also sets _good_end / torn_tail
        record = dict(record)
        record["seq"] = seq
        record.setdefault("created_at", iso(datetime.now(timezone.utc)))
        line = (json.dumps(record, sort_keys=True, default=str) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        start = self._good_end if self._good_end is not None else 0
        with self.path.open("r+b" if self.path.exists() else "wb") as f:
            f.seek(start)
            f.truncate()              # drops a torn tail, if any
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        if self.path.stat().st_size != start + len(line):
            raise LedgerMalformed(f"{self.path}: short write")
        self.torn_tail = None
        self._good_end = start + len(line)
        return record

    def append(self, record: dict) -> dict:
        with self.locked():
            return self.append_unlocked(record)
