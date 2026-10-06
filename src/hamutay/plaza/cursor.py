"""The guest read cursor: recorded coverage over plaza messages
(spec docs/superpowers/specs/2026-10-06-plaza-read-cursor-design.md, r3).

The read log is advisory -- a camera, not a gate. Its write is bounded and
never nested inside the plaza lock; its read is lockless and tolerant. No
fault in it may fail a plaza read or a plaza send.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from hamutay.assembly.ledger import iso, parse_instant

from .ids import GUEST_LABEL_RE, PLAZA_LOCK_WINDOW_S

READS_NAME = "reads.jsonl"
READS_LOCK_WINDOW_S = 2.0
COVERAGE_NOTE = "recorded coverage: rows the tool returned and recorded; not proof they were received or read"

# The server's in-process tally of recording failures, per label, for its own life (spec: wire contract 1).
_failures: Counter = Counter()


def reset_tally() -> None:
    _failures.clear()


def reads_path(cfg) -> Path:
    return Path(cfg.plaza).parent / READS_NAME


def merge_ranges(seqs: list[int], message_seqs: list[int]) -> list[list[int]]:
    """Ranges over message seqs: two seqs merge when no *message* lies between them."""
    wanted = set(seqs)
    out: list[list[int]] = []
    open_range: list[int] | None = None
    for s in sorted(set(message_seqs)):
        if s in wanted:
            if open_range is None:
                open_range = [s, s]
                out.append(open_range)
            else:
                open_range[1] = s
        else:
            open_range = None
    return out


def _guest_actor(label: str) -> str:
    return label if label.startswith("guest:") else f"guest:{label}"


@contextmanager
def _reads_locked(path: Path, timeout_s: float):
    lock_path = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_s
    with lock_path.open("a") as h:
        while True:
            try:
                fcntl.flock(h.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"{lock_path}: lock busy past {timeout_s}s")
                time.sleep(0.02)
        try:
            yield
        finally:
            fcntl.flock(h.fileno(), fcntl.LOCK_UN)


def record_read(cfg, label: str, rows: list[dict], messages: list[dict], *, via: str = "mcp",
                now: datetime | None = None) -> None:
    """Append one read record for rows actually returned (`messages`: every message in the same
    snapshot, so `seqs` merges across delivery seqs but never across an unreturned message).
    Failures are tallied, never raised."""
    if not rows:
        return
    actor = _guest_actor(label)
    try:
        path = reads_path(cfg)
        seqs = [r["seq"] for r in rows]
        record = {"record_type": "read", "label": actor,
                  "at": iso(now or datetime.now(timezone.utc)), "via": via,
                  "seqs": merge_ranges(seqs, [m["seq"] for m in messages]),
                  "message_ids": [r["message_id"] for r in rows]}
        line = (json.dumps(record, sort_keys=True) + "\n").encode()
        with _reads_locked(path, READS_LOCK_WINDOW_S):
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                size = os.fstat(fd).st_size
                if size:
                    with path.open("rb") as f:          # torn tail: isolate the fragment on its own line
                        f.seek(size - 1)
                        if f.read(1) != b"\n":
                            os.write(fd, b"\n")
                os.write(fd, line)
            finally:
                os.close(fd)
    except Exception:  # noqa: BLE001 -- the camera never fails the read (spec: write path)
        _failures[actor] += 1


def _valid(r) -> bool:
    if not isinstance(r, dict) or r.get("record_type") != "read":
        return False
    label = r.get("label")
    if not isinstance(label, str) or not label.startswith("guest:") \
            or not GUEST_LABEL_RE.fullmatch(label[len("guest:"):]):
        return False
    at = r.get("at")
    if not isinstance(at, str):
        return False
    try:
        parse_instant(at)
    except ValueError:
        return False
    seqs = r.get("seqs")
    if not isinstance(seqs, list):
        return False
    prev = 0
    for pair in seqs:
        if not (isinstance(pair, list) and len(pair) == 2
                and all(isinstance(x, int) and not isinstance(x, bool) for x in pair)):
            return False
        a, b = pair
        if not (1 <= a <= b) or a <= prev:
            return False
        prev = b
    ids = r.get("message_ids")
    return isinstance(ids, list) and bool(ids) and all(isinstance(i, str) for i in ids)


def load_coverage(cfg, label: str) -> tuple[set[str], str | None, int]:
    """(covered message_ids, last_read_at, skipped_records) for this label. Lockless and tolerant.

    Raises OSError only if the read log exists but cannot be read.
    """
    actor = _guest_actor(label)
    path = reads_path(cfg)
    covered: set[str] = set()
    last: datetime | None = None
    skipped = 0
    if not path.exists():
        return covered, None, 0
    data = path.read_bytes()
    lines = data.split(b"\n")
    if data and not data.endswith(b"\n"):
        lines = lines[:-1]                  # a torn final line is ignored, not counted (an append in flight)
    for raw in lines:
        if not raw.strip():
            continue
        try:
            r = json.loads(raw)
        except ValueError:
            skipped += 1
            continue
        if not _valid(r):
            skipped += 1
            continue
        if r["label"] != actor:
            continue
        covered.update(r["message_ids"])
        at = parse_instant(r["at"])
        if last is None or at > last:
            last = at
    return covered, (iso(last) if last else None), skipped


def unshown_ranges(messages: list[dict], covered: set[str], *, below_seq: int | None = None) -> list[list[int]]:
    eligible = [m for m in messages if below_seq is None or m["seq"] < below_seq]
    seqs = [m["seq"] for m in eligible]
    return merge_ranges([m["seq"] for m in eligible if m["message_id"] not in covered], seqs)


def status(cfg, label: str, messages: list[dict]) -> dict:
    """The plaza_status payload. `messages` is the full message list from read_rows (the plaza raises there)."""
    actor = _guest_actor(label)
    latest = messages[-1]["seq"] if messages else 0
    out = {"label": actor, "latest_seq": latest, "unshown": None, "last_read_at": None,
           "recording": {"failures_this_session": _failures[actor], "skipped_records": 0},
           "coverage_note": COVERAGE_NOTE}
    try:
        covered, last, skipped = load_coverage(cfg, label)
    except OSError as e:
        out["recording"]["error"] = f"{type(e).__name__}: {e}"
        return out
    out["unshown"] = unshown_ranges(messages, covered)
    out["last_read_at"] = last
    out["recording"]["skipped_records"] = skipped
    return out


def unshown_at_send(cfg, label: str, messages: list[dict], seq: int) -> list[list[int]]:
    covered, _, _ = load_coverage(cfg, label)
    return unshown_ranges(messages, covered, below_seq=seq)


__all__ = ["READS_NAME", "COVERAGE_NOTE", "PLAZA_LOCK_WINDOW_S", "reset_tally", "reads_path", "merge_ranges",
           "record_read", "load_coverage", "unshown_ranges", "status", "unshown_at_send"]
