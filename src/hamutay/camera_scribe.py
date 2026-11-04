"""The camera's scribe: receive the gate's messages, coalesce, store, and say when the camera wasn't looking.

Spec: docs/superpowers/specs/2026-11-03-access-camera-design.md (r7), R5-R8, R11, R12. Runs as the system
user hamutay-camera (never the house user), from the root-owned installed copy
/usr/local/lib/hamutay-camera/scribe.py, with camera.py beside it. Credentials come from
/etc/hamutay-camera/scribe.ini (owner hamutay-camera, mode 600) and are never printed. It accepts only
datagrams whose kernel-reported sender uid is 0 (the gate).
"""

from __future__ import annotations

import base64
import configparser
import fcntl
import json
import os
import signal
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from hamutay import camera
except ImportError:  # the installed copy, run with python3 -I: camera.py sits beside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import camera  # type: ignore[no-redef]
import struct

RUN_DIR = Path(os.environ.get("RUNTIME_DIRECTORY", "/run/hamutay-camera"))
SOCKET_PATH = RUN_DIR / "events.sock"
LOCK_PATH = RUN_DIR / "scribe.lock"
SPOOL_PATH = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/hamutay-camera")) / "spool.jsonl"
SPOOL_MAX = 256 * 1024 * 1024
CONFIG = Path("/etc/hamutay-camera/scribe.ini")
UCRED = struct.Struct("iII")  # pid, uid, gid
ALIVE_EVERY = 60.0
INSERT_TIMEOUT = 5.0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Store:
    """ArangoDB over HTTP (stdlib only). insert() returns "stored", "conflict" or "failed"."""

    def __init__(self, url: str, user: str, password: str, db: str = "ayllu_camera"):
        self.base = url.rstrip("/") + f"/_db/{db}"
        self.auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

    def _req(self, path: str, body: dict | None = None, method: str = "POST"):
        data = None if body is None else json.dumps(body, default=camera._json_default).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", "Authorization": self.auth})
        with urllib.request.urlopen(req, timeout=INSERT_TIMEOUT) as r:
            return json.load(r)

    def insert(self, record: dict) -> str:
        record = dict(record)
        collection = record.pop("_collection")
        try:
            self._req(f"/_api/document/{collection}", record)
            return "stored"
        except urllib.error.HTTPError as e:
            return "conflict" if e.code == 409 else "failed"
        except (OSError, ValueError):
            return "failed"

    def last_session_end(self, session: str) -> dict | None:
        """The newest alive or down status of any earlier session, or None if there was never one."""
        q = ("FOR s IN status FILTER s.session != @me AND s.kind IN ['alive', 'down'] "
             "SORT s.at DESC LIMIT 1 RETURN s")
        body = self._req("/_api/cursor", {"query": q, "bindVars": {"me": session}})
        rows = body.get("result") or []
        return rows[0] if rows else None


class Scribe:
    def __init__(self, store: Store):
        self.store = store
        self.session = camera._uuid7()
        self.coalescer = camera.Coalescer()
        self.tracker = camera.GateTracker()
        self.spool = camera.Spool(SPOOL_PATH, SPOOL_MAX)
        self.start_gap_done = False
        self.coverage_parts: dict[str, dict[int, dict]] = {}
        self.coverage_recorded: str | None = None
        self.coverage_announced: str | None = None
        self.last_beat: dict | None = None
        self.prev_beat_counts: dict | None = None
        self.c = self._zero()
        self.prev_lost = 0
        self.stopping = False

    @staticmethod
    def _zero() -> dict:
        return {"opens_received": 0, "records_written": 0, "records_spooled": 0, "dropped_by_scribe": 0,
                "attribution_partial": 0, "attribution_lost": 0, "rejected_sender": 0}

    # --- storing -----------------------------------------------------------------------------------

    def put(self, collection: str, doc: dict) -> None:
        rec = {"_key": camera._uuid7(), "session": self.session, **doc, "_collection": collection}
        if collection == "entries":
            rec.setdefault("spooled", False)
        result = self.store.insert(rec)
        if result in ("stored", "conflict"):
            if collection == "entries":
                self.c["records_written"] += 1
            return
        if collection == "entries":
            rec["spooled"] = True
        if self.spool.append(rec):
            if collection == "entries":
                self.c["records_spooled"] += 1
        else:
            self.c["dropped_by_scribe"] += 1

    def status(self, kind: str, **fields) -> None:
        self.put("status", {"kind": kind, "at": utcnow(), **fields})

    def replay(self) -> None:
        if SPOOL_PATH.exists() and SPOOL_PATH.stat().st_size > 0:
            self.spool.replay(self.store.insert)

    # --- messages ----------------------------------------------------------------------------------

    def handle(self, msg: dict) -> None:
        for s in self.tracker.observe(msg, utcnow()):
            kind = s.pop("kind")
            self.put("status", {"kind": kind, "at": utcnow(), **s})
        kind = msg.get("kind")
        if kind == "open":
            self.c["opens_received"] += 1
            state = (msg.get("reader") or {}).get("attribution")
            if state == "partial":
                self.c["attribution_partial"] += 1
            elif state == "lost":
                self.c["attribution_lost"] += 1
            msg["t"] = camera._parse(msg["t"])
            for rec in self.coalescer.add(msg):
                self.put("entries", rec)
        elif kind == "beat":
            self.last_beat = msg
            self.coverage_announced = msg.get("coverage_version")
        elif kind == "coverage":
            version = msg.get("coverage_version")
            parts = self.coverage_parts.setdefault(version, {})
            parts[msg["part"]] = msg
            if len(parts) == msg["parts"]:
                marks, unmarked = [], []
                for i in range(msg["parts"]):
                    marks += parts[i]["marks"]
                    unmarked += parts[i]["unmarked"]
                if camera.coverage_version(marks, unmarked) == version and version != self.coverage_recorded:
                    self.status("coverage", gen=msg.get("gen"), coverage_version=version,
                                coverage={"marks": marks, "unmarked": unmarked})
                    self.coverage_recorded = version
                self.coverage_parts = {}

    # --- periodic ----------------------------------------------------------------------------------

    def ensure_start_gap(self) -> None:
        if self.start_gap_done:
            return
        try:
            last = self.store.last_session_end(self.session)
        except (OSError, ValueError, urllib.error.HTTPError):
            return  # database not answering; try again next tick
        gap = camera.scribe_gap_on_start(last, utcnow())
        if gap is not None:
            kind = gap.pop("kind")
            self.put("status", {"kind": kind, "at": utcnow(), **gap})
        self.start_gap_done = True

    def alive(self) -> None:
        for rec in self.coalescer.flush():
            self.put("entries", rec)
        counts = dict(self.c)
        counts["lost_in_channel"] = self.tracker.lost_in_channel - self.prev_lost
        self.prev_lost = self.tracker.lost_in_channel
        if self.last_beat is not None:
            b = {k: self.last_beat.get(k, 0) for k in ("opened", "answered", "dropped")}
            p = self.prev_beat_counts if (self.prev_beat_counts and self.prev_beat_counts.get("gen")
                                          == self.last_beat.get("gen")) else {"opened": 0, "answered": 0, "dropped": 0}
            counts["gate_dropped"] = b["dropped"] - p.get("dropped", 0)
            counts["gate_answered_minus_opened"] = (b["answered"] - b["opened"]) - (p.get("answered", 0) - p.get("opened", 0))
            self.prev_beat_counts = {**b, "gen": self.last_beat.get("gen")}
            counts["gate_last_beat"] = self.last_beat.get("t")
        extra = {}
        if self.coverage_announced and self.coverage_announced != self.coverage_recorded:
            extra["coverage_pending"] = self.coverage_announced
        self.status("alive", counts=counts, **extra)
        self.c = self._zero()

    def stop(self) -> None:
        for rec in self.coalescer.flush():
            self.put("entries", rec)
        self.status("down")


def load_store() -> Store:
    cp = configparser.ConfigParser()
    if not cp.read(CONFIG):
        sys.exit(f"camera scribe: {CONFIG} not found (deploy/camera/install.sh writes it)")
    s = cp["scribe"]
    return Store(s.get("url", "http://127.0.0.1:8529"), s["user"], s["password"])


def bind_socket() -> tuple[socket.socket, int]:
    RUN_DIR.mkdir(mode=0o750, parents=True, exist_ok=True)
    lock = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("camera scribe: another scribe holds the lock")
    try:
        SOCKET_PATH.unlink()
    except FileNotFoundError:
        pass
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    sock.bind(str(SOCKET_PATH))
    sock.settimeout(1.0)
    return sock, lock


def main() -> None:
    store = load_store()
    sock, _lock = bind_socket()
    scribe = Scribe(store)

    def on_term(signum, frame):
        scribe.stopping = True
    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)

    scribe.status("up")
    scribe.ensure_start_gap()
    scribe.replay()
    t_alive = time.monotonic()
    while not scribe.stopping:
        try:
            data, anc, _flags, _addr = sock.recvmsg(65536, socket.CMSG_SPACE(UCRED.size))
            uid = None
            for level, kind, payload in anc:
                if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                    _pid, uid, _gid = UCRED.unpack(payload[:UCRED.size])
            if uid != 0:
                scribe.c["rejected_sender"] += 1  # only the gate (root) may speak here
            else:
                try:
                    scribe.handle(json.loads(data))
                except (ValueError, KeyError, TypeError):
                    pass  # a malformed message is counted by the seq gap it leaves
        except socket.timeout:
            pass
        for s in scribe.tracker.tick(utcnow()):
            kind = s.pop("kind")
            scribe.put("status", {"kind": kind, "at": utcnow(), **s})
        if time.monotonic() - t_alive >= ALIVE_EVERY:
            scribe.ensure_start_gap()
            scribe.alive()
            scribe.replay()
            t_alive = time.monotonic()
    scribe.stop()
    try:
        SOCKET_PATH.unlink()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
