"""The camera's pure logic: who opened what in a door's home, and when the camera wasn't looking.

Spec: docs/superpowers/specs/2026-11-03-access-camera-design.md (r6). Everything here runs without root
and without a database, so the gate (root, installed copy) and the scribe (house user) share one tested
implementation of each rule. The gate imports only the standard library; so does this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

MESSAGE_LIMIT = 8192
USER_MANAGER_PREFIX = "/user.slice/user-1000.slice/user@1000.service/"
HOUSE_UID = 1000
READER_FIELDS = ("uid", "exe", "comm", "cgroup", "cwd")
MAX_ANCESTORS = 4


# --- R3 ---------------------------------------------------------------------------------------------

def is_self_read(reader: dict, path: str, homes: dict[str, str]) -> bool:
    """True only when a door's own heartbeat unit opens a file in that door's home (R3)."""
    try:
        uid, cgroup = reader["uid"], reader["cgroup"]
    except (KeyError, TypeError):
        return False
    if uid != HOUSE_UID or not isinstance(cgroup, str) or not isinstance(path, str):
        return False
    # No exemption on uncertain attribution (R3; review 1 S4).
    if reader.get("reused") or reader.get("attribution", "complete") != "complete":
        return False
    if any(reader.get(f) is None for f in ("pid", "start_time", "exe", "comm", "cwd")):
        return False
    if not cgroup.startswith(USER_MANAGER_PREFIX):
        return False
    unit = cgroup.rsplit("/", 1)[-1]
    prefix, suffix = "hamutay-heartbeat@", ".service"
    if not (unit.startswith(prefix) and unit.endswith(suffix)):
        return False
    door = unit[len(prefix):-len(suffix)]
    home = homes.get(door)
    if not home:
        return False
    return os.path.dirname(os.path.normpath(path)) == os.path.normpath(home)


# --- R4 ---------------------------------------------------------------------------------------------

def _read_text(p: Path) -> str | None:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return None


def _readlink(p: Path) -> str | None:
    try:
        return os.readlink(p)
    except OSError:
        return None


def _stat_fields(text: str | None) -> tuple[int | None, int | None]:
    """(start_time, ppid) from /proc/<pid>/stat. Fields are counted after the ')' that closes comm."""
    if text is None:
        return None, None
    close = text.rfind(")")
    if close < 0:
        return None, None
    rest = text[close + 1:].split()
    # rest[0] is field 3 (state); field n is rest[n - 3].
    try:
        ppid = int(rest[4 - 3])
    except (IndexError, ValueError):
        ppid = None
    try:
        start = int(rest[22 - 3])
    except (IndexError, ValueError):
        start = None
    return start, ppid


def _real_uid(text: str | None) -> int | None:
    if text is None:
        return None
    for line in text.splitlines():
        if line.startswith("Uid:"):
            parts = line.split()
            try:
                return int(parts[1])
            except (IndexError, ValueError):
                return None
    return None


def _cgroup_path(text: str | None) -> str | None:
    if text is None:
        return None
    for line in text.splitlines():
        if line.startswith("0::"):
            return line.rsplit(":", 1)[-1].strip()
    return None


def attribution_state(snapshot: dict) -> str:
    if not snapshot.get("proc_readable"):
        return "lost"
    before, after = snapshot.get("start_time_before"), snapshot.get("start_time_after")
    if before is None or before != after:
        return "partial"
    if any(snapshot.get(f) is None for f in READER_FIELDS):
        return "partial"
    return "complete"


def read_reader(pid: int, proc_root: Path = Path("/proc"),
                between: Callable[[], None] | None = None) -> dict:
    d = Path(proc_root) / str(pid)
    try:
        os.listdir(d)
        proc_readable = True
    except OSError:
        proc_readable = False
    stat1 = _read_text(d / "stat") if proc_readable else None
    start_before, ppid = _stat_fields(stat1)
    comm = _read_text(d / "comm") if proc_readable else None
    reader = {
        "pid": pid,
        "uid": _real_uid(_read_text(d / "status")) if proc_readable else None,
        "exe": _readlink(d / "exe") if proc_readable else None,
        "comm": comm.rstrip("\n") if comm is not None else None,
        "cgroup": _cgroup_path(_read_text(d / "cgroup")) if proc_readable else None,
        "cwd": _readlink(d / "cwd") if proc_readable else None,
    }
    if between is not None:
        between()
    start_after = _stat_fields(_read_text(d / "stat"))[0] if proc_readable else None
    reader["start_time"] = start_before
    reader["reused"] = (start_before is not None and start_after is not None and start_before != start_after)
    reader["ancestors"] = _ancestors(ppid, Path(proc_root)) if proc_readable else []
    snap = {"proc_readable": proc_readable, "start_time_before": start_before,
            "start_time_after": start_after, **reader}
    snap["attribution"] = attribution_state(snap)
    return snap


def _ancestors(ppid: int | None, proc_root: Path) -> list[dict]:
    out: list[dict] = []
    while ppid and ppid != 1 and len(out) < MAX_ANCESTORS:
        d = proc_root / str(ppid)
        stat = _read_text(d / "stat")
        if stat is None:
            break
        start, parent = _stat_fields(stat)
        comm = _read_text(d / "comm")
        out.append({"pid": ppid, "start_time": start, "exe": _readlink(d / "exe"),
                    "comm": comm.rstrip("\n") if comm is not None else None})
        ppid = parent
    return out


# --- Messages ---------------------------------------------------------------------------------------

def _dumps(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False, default=_json_default).encode("utf-8")


def encode_message(obj: dict) -> bytes:
    data = _dumps(obj)
    if len(data) <= MESSAGE_LIMIT:
        return data
    if obj.get("kind") != "open":
        raise ValueError(f"{obj.get('kind')!r} message is {len(data)} bytes, over {MESSAGE_LIMIT}")
    import copy
    msg = copy.deepcopy(obj)
    msg["truncated"] = True
    reader = msg.get("reader") or {}
    ancestors = list(reader.get("ancestors") or [])
    while ancestors:
        ancestors.pop()
        reader["ancestors"] = ancestors
        data = _dumps(msg)
        if len(data) <= MESSAGE_LIMIT:
            return data
    # Cut path, then cwd, from the left (keeping their tails) until it fits.
    for fields in ((("path", msg),), ((("cwd", reader),)), (("path", msg), ("cwd", reader))):
        trial = copy.deepcopy(msg)
        trial_reader = trial.get("reader") or {}
        holders = {"path": trial, "cwd": trial_reader}
        for key, _ in fields:
            holders[key][key] = _fit_tail(trial, holders[key], key)
        data = _dumps(trial)
        if len(data) <= MESSAGE_LIMIT:
            return data
    raise ValueError("open message does not fit even with path and cwd cut")


def _fit_tail(msg: dict, holder: dict, key: str) -> str:
    """The longest tail of holder[key] such that msg encodes within MESSAGE_LIMIT (other fields as now)."""
    val = holder.get(key)
    if not isinstance(val, str) or not val:
        return val
    lo, hi = 0, len(val)  # number of characters to keep
    while lo < hi:
        mid = (lo + hi + 1) // 2
        holder[key] = val[len(val) - mid:]
        if len(_dumps(msg)) <= MESSAGE_LIMIT:
            lo = mid
        else:
            hi = mid - 1
    holder[key] = val[len(val) - lo:] if lo else ""
    return holder[key]


# --- Coverage ---------------------------------------------------------------------------------------

def coverage_version(marks: list, unmarked: list) -> str:
    canon = json.dumps({"marks": sorted(marks), "unmarked": sorted(unmarked)}, separators=(",", ":"),
                       ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(canon).hexdigest()


def split_coverage(marks: list, unmarked: list, gen: str, seq_start: int, t: datetime) -> list[dict]:
    version = coverage_version(marks, unmarked)
    rows = [("marks", list(m)) for m in sorted(marks)] + [("unmarked", list(u)) for u in sorted(unmarked)]
    ts = t

    def envelope(seq: int, part: int, parts: int, m: list, u: list) -> dict:
        return {"v": 1, "kind": "coverage", "gen": gen, "seq": seq, "t": ts, "coverage_version": version,
                "part": part, "parts": parts, "marks": m, "unmarked": u}

    # Size against a worst-case envelope (large part/parts/seq numbers), so filling in real numbers
    # never pushes a part over the limit.
    big = 10 ** 9
    groups: list[tuple[list, list]] = []
    cur_m: list = []
    cur_u: list = []
    for kind, row in rows:
        trial_m = cur_m + [row] if kind == "marks" else cur_m
        trial_u = cur_u + [row] if kind == "unmarked" else cur_u
        if len(_dumps(envelope(big, big, big, trial_m, trial_u))) <= MESSAGE_LIMIT:
            cur_m, cur_u = trial_m, trial_u
            continue
        if not cur_m and not cur_u:
            raise ValueError("a single coverage row does not fit in one message")
        groups.append((cur_m, cur_u))
        cur_m = [row] if kind == "marks" else []
        cur_u = [row] if kind == "unmarked" else []
        if len(_dumps(envelope(big, big, big, cur_m, cur_u))) > MESSAGE_LIMIT:
            raise ValueError("a single coverage row does not fit in one message")
    if cur_m or cur_u or not groups:
        groups.append((cur_m, cur_u))
    parts = len(groups)
    return [envelope(seq_start + i, i, parts, m, u) for i, (m, u) in enumerate(groups)]


# --- Time -------------------------------------------------------------------------------------------

def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse(t) -> datetime:
    if isinstance(t, datetime):
        return t.astimezone(timezone.utc)
    s = str(t)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def window_of(t: datetime) -> datetime:
    return t.replace(second=0, microsecond=0)


# --- R5 ---------------------------------------------------------------------------------------------

class Coalescer:
    def __init__(self, max_keys: int = 10000):
        self.max_keys = max_keys
        self._held: dict[tuple, dict] = {}

    def add(self, msg: dict) -> list[dict]:
        t = _parse(msg["t"])
        reader = msg.get("reader") or {}
        window = window_of(t)
        key = (msg.get("gen"), reader.get("pid"), reader.get("start_time"), msg.get("path_sha256"), window)
        if key in self._held:
            rec = self._held[key]
            rec["count"] += 1
            rec["first"] = min(rec["first"], t)
            rec["last"] = max(rec["last"], t)
            rec["coalesced"] = True
            return []
        flushed: list[dict] = []
        identity = key[:4]
        if identity not in {k[:4] for k in self._held} and self._identities() >= self.max_keys:
            flushed = self.flush()
        self._held[key] = {
            "gen": msg.get("gen"), "window_start": window, "first": t, "last": t, "count": 1,
            "coalesced": False, "door": msg.get("door"), "path": msg.get("path"),
            "path_sha256": msg.get("path_sha256"), "truncated": bool(msg.get("truncated", False)),
            "reader": reader, "attribution": reader.get("attribution", msg.get("attribution")),
        }
        return flushed

    def flush(self, before: datetime | None = None) -> list[dict]:
        out = []
        for key in list(self._held):
            if before is None or self._held[key]["window_start"] < before:
                out.append(self._held.pop(key))
        return out

    def _identities(self) -> int:
        return len({k[:4] for k in self._held})

    def __len__(self) -> int:
        return self._identities()


# --- R7 ---------------------------------------------------------------------------------------------

def _uuid7() -> str:
    if hasattr(uuid, "uuid7"):
        return str(uuid.uuid7())
    import secrets
    import time
    ms = time.time_ns() // 1_000_000
    b = bytearray(ms.to_bytes(6, "big") + secrets.token_bytes(10))
    b[6] = (b[6] & 0x0F) | 0x70
    b[8] = (b[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(b)))


def scribe_gap_on_start(last: dict | None, now: datetime) -> dict | None:
    if last is None:
        return None
    cause = "stopped" if last.get("kind") == "down" else "unknown"
    return {"kind": "gap", "scope": "scribe", "gap_from": _parse(last["at"]), "gap_to": now, "cause": cause}


class GateTracker:
    def __init__(self, silence: timedelta = timedelta(seconds=10)):
        self.silence = silence
        self.lost_in_channel = 0
        self._gen: str | None = None
        self._high: int | None = None
        self._last_beat_t: datetime | None = None
        self._last_beat_arrival: datetime | None = None
        self._last_counters: dict | None = None
        self._open_gap: dict | None = None

    def _gap(self, start, end, gap_id=None) -> dict:
        return {"kind": "gap", "scope": "gate", "gap_id": gap_id or _uuid7(), "gap_from": start, "gap_to": end}

    def observe(self, msg: dict, now: datetime) -> list[dict]:
        out: list[dict] = []
        gen, seq = msg.get("gen"), msg.get("seq")
        t = _parse(msg["t"]) if msg.get("t") is not None else now
        if gen != self._gen:
            if self._gen is not None:
                out.append({"kind": "gate_restart", "gen": gen, "old_gen": self._gen,
                            "counts": self._last_counters})
                if self._open_gap is not None:
                    out.append(self._gap(self._open_gap["gap_from"], t, self._open_gap["gap_id"]))
                    self._open_gap = None
                else:
                    out.append(self._gap(self._last_beat_t, t))
            self._gen, self._high = gen, None
            self._last_beat_t = None
        if isinstance(seq, int):
            if self._high is None:
                self._high = seq
            elif seq > self._high:
                if seq > self._high + 1:
                    self.lost_in_channel += seq - self._high - 1
                self._high = seq
        if msg.get("kind") == "beat":
            if self._open_gap is not None:
                out.append(self._gap(self._open_gap["gap_from"], t, self._open_gap["gap_id"]))
                self._open_gap = None
            self._last_beat_t = t
            self._last_beat_arrival = now
            self._last_counters = {k: msg.get(k) for k in ("opened", "self_reads", "answered", "dropped")}
        return out

    def tick(self, now: datetime) -> list[dict]:
        if self._open_gap is not None or self._last_beat_arrival is None:
            return []
        if now - self._last_beat_arrival > self.silence:
            gap = self._gap(self._last_beat_t, None)
            self._open_gap = gap
            return [gap]
        return []


# --- R8 ---------------------------------------------------------------------------------------------

def _json_default(o):
    if isinstance(o, datetime):
        return _iso(o)
    raise TypeError(f"not JSON serializable: {type(o).__name__}")


class Spool:
    def __init__(self, path: Path, max_bytes: int):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.refused = 0

    def append(self, record: dict) -> bool:
        line = (json.dumps(record, separators=(",", ":"), ensure_ascii=False, default=_json_default)
                + "\n").encode("utf-8")
        try:
            size = self.path.stat().st_size if self.path.exists() else 0
            if size + len(line) > self.max_bytes:
                self.refused += 1
                return False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            try:
                os.write(fd, line)
                os.fsync(fd)
            finally:
                os.close(fd)
            return True
        except OSError:
            self.refused += 1
            return False

    def replay(self, insert: Callable[[dict], str]) -> dict:
        counts = {"stored": 0, "conflict": 0, "torn": 0, "remaining": 0}
        if not self.path.exists():
            return counts
        raw = self.path.read_bytes()
        lines = raw.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
            complete_tail = True
        else:
            complete_tail = False
        records: list[bytes] = []
        for i, line in enumerate(lines):
            is_last = i == len(lines) - 1
            try:
                json.loads(line)
                records.append(line)
            except ValueError:
                if is_last and not complete_tail:
                    counts["torn"] += 1
                elif is_last:
                    counts["torn"] += 1
                else:
                    counts["torn"] += 1
        left: list[bytes] = []
        for i, line in enumerate(records):
            result = insert(json.loads(line))
            if result == "stored":
                counts["stored"] += 1
            elif result == "conflict":
                counts["conflict"] += 1
            else:
                left = records[i:]
                break
        counts["remaining"] = len(left)
        if not left:
            self._rewrite([])
        return counts

    def _rewrite(self, lines: list[bytes]) -> None:
        """Replace the spool with exactly `lines`: write new file, fsync, rename, fsync the directory."""
        tmp = self.path.with_name(self.path.name + ".new")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            for line in lines:
                os.write(fd, line + b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.path)
        dfd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
