"""The camera's gate: answer every open in a door's home, and say who opened it.

Spec: docs/superpowers/specs/2026-11-03-access-camera-design.md (r6). Runs as root, from the installed
copy in /usr/local/lib/hamutay-camera/ (R11), with /usr/bin/python3 -I. Standard library only, plus
camera.py installed beside it.

Per event (R1): read the path; snapshot the reader (R4); answer FAN_ALLOW; close the event fd; then send
one datagram to the scribe. A failed response write, or any error outside the per-event block, exits
with status 70: the kernel then allows every pending event when the group closes (R2d). This process
never answers FAN_DENY, never forks, and never opens a file inside a home (that would wait on itself).
"""

import ctypes
import hashlib
import json
import os
import resource
import select
import socket
import stat
import struct
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera  # noqa: E402  (installed beside this file)

FAN_CLASS_CONTENT = 0x04
FAN_CLOEXEC = 0x01
FAN_NONBLOCK = 0x02
FAN_OPEN_PERM = 0x00010000
FAN_EVENT_ON_CHILD = 0x08000000
FAN_MARK_ADD, FAN_MARK_REMOVE = 0x01, 0x02
FAN_MARK_DONT_FOLLOW, FAN_MARK_ONLYDIR = 0x04, 0x08
FAN_ALLOW = 0x01
AT_FDCWD = -100
EVENT = struct.Struct("IBBHQii")  # event_len, vers, reserved, metadata_len, mask, fd, pid
RESPONSE = struct.Struct("iI")
BATCH = 64
EXIT_FAILED = 70

BEAT_EVERY = 2.0
RESCAN_EVERY = 10.0
COVERAGE_EVERY = 30.0
DIRS_PER_HOME = 256
SOCKET_PATH = "/run/hamutay-camera/events.sock"  # r7: the scribe user's directory, 0750
CACHE_SECONDS = 1.0  # R4a

libc = ctypes.CDLL("libc.so.6", use_errno=True)


def fail(why: str) -> None:
    try:
        sys.stderr.write(f"gate: exiting {EXIT_FAILED}: {why}\n")
        sys.stderr.flush()
    finally:
        os._exit(EXIT_FAILED)


def sd_notify(state: str) -> None:
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.sendto(state.encode(), addr)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Gate:
    def __init__(self, community: Path, members: Path, socket_path: str):
        self.community = community
        self.members = members
        self.socket_path = socket_path
        self.gen = camera._uuid7()
        self.seq = 0
        self.me = os.getpid()
        self.counts = {"opened": 0, "self_reads": 0, "answered": 0, "dropped": 0}
        self.homes: dict[str, str] = {}          # door -> home path
        self.marks: dict[tuple, str] = {}         # (dev, ino) -> path
        self.unmarked: list[list] = []
        self.rescan_queue: deque = deque()
        self.cache: dict[int, tuple[int, float, dict]] = {}  # pid -> (start_time, taken_at, snapshot)
        self.version = camera.coverage_version([], [])
        self.out = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.out.setblocking(False)
        self.fan = libc.fanotify_init(FAN_CLASS_CONTENT | FAN_CLOEXEC | FAN_NONBLOCK,
                                      os.O_RDONLY | os.O_LARGEFILE | os.O_CLOEXEC)
        if self.fan < 0:
            fail(f"fanotify_init: {os.strerror(ctypes.get_errno())}")

    # --- channel -----------------------------------------------------------------------------------

    def send(self, msg: dict) -> None:
        msg = {"v": 1, "gen": self.gen, "seq": self.seq, **msg}
        self.seq += 1
        try:
            data = camera.encode_message(msg)
            self.out.sendto(data, self.socket_path)
        except (OSError, ValueError):
            self.counts["dropped"] += 1

    def beat(self) -> None:
        self.send({"kind": "beat", "t": now(), **self.counts, "coverage_version": self.version,
                   "marks_count": len(self.marks)})

    def send_coverage(self) -> None:
        marks = [[dev, ino, path] for (dev, ino), path in self.marks.items()]
        try:
            parts = camera.split_coverage(marks, self.unmarked, self.gen, self.seq, now())
        except ValueError:
            self.counts["dropped"] += 1
            return
        for part in parts:
            self.seq = part["seq"] + 1
            try:
                self.out.sendto(camera.encode_message(part), self.socket_path)
            except (OSError, ValueError):
                self.counts["dropped"] += 1

    # --- coverage (R9) -----------------------------------------------------------------------------

    def read_homes(self) -> None:
        try:
            members = json.loads(self.members.read_text())["members"]
        except (OSError, ValueError, KeyError, TypeError):
            return  # keep the last good list; a broken file must not unmark everyone
        self.homes = {name: str(self.community / name) for name in members}

    def walk(self, door: str) -> tuple[list[tuple], list[list]]:
        home = self.homes[door]
        try:
            st = os.lstat(home)
        except OSError:
            return [], [[home, "missing"]]
        if not stat.S_ISDIR(st.st_mode):
            return [], [[home, "not_a_directory"]]
        if st.st_uid != camera.HOUSE_UID:
            return [], [[home, "wrong_owner"]]
        found, unmarked = [], []
        queue = deque([home])
        while queue:
            d = queue.popleft()
            if len(found) >= DIRS_PER_HOME:
                unmarked.append([d, "limit"])
                continue
            try:
                dst = os.lstat(d)
            except OSError:
                continue
            found.append(((dst.st_dev, dst.st_ino), d))
            try:
                with os.scandir(d) as it:
                    for e in it:
                        if e.is_dir(follow_symlinks=False):
                            queue.append(e.path)
            except OSError:
                pass
        return found, unmarked

    def mark(self, path: str, add: bool) -> bool:
        flags = (FAN_MARK_ADD if add else FAN_MARK_REMOVE) | FAN_MARK_DONT_FOLLOW | FAN_MARK_ONLYDIR
        rc = libc.fanotify_mark(self.fan, flags, FAN_OPEN_PERM | FAN_EVENT_ON_CHILD, AT_FDCWD,
                                path.encode())
        return rc == 0

    def rescan_home(self, door: str, desired: dict, unmarked: list) -> None:
        found, missed = self.walk(door)
        unmarked.extend(missed)
        for key, path in found:
            if key not in self.marks:
                if self.mark(path, True):
                    self.marks[key] = path
                else:
                    unmarked.append([path, "mark_failed:" + os.strerror(ctypes.get_errno())])
                    continue
            desired[key] = path

    def rescan_all(self, ping) -> None:
        """A full rescan, pinging the watchdog after each home (R9a). Used at start."""
        self.read_homes()
        desired: dict[tuple, str] = {}
        unmarked: list[list] = []
        for door in list(self.homes):
            self.rescan_home(door, desired, unmarked)
            ping()
        self.finish_rescan(desired, unmarked)

    def finish_rescan(self, desired: dict, unmarked: list) -> None:
        for key in [k for k in self.marks if k not in desired]:
            path = self.marks.pop(key)
            try:
                self.mark(path, False)  # gone or no longer a home
            except OSError:
                pass
        self.unmarked = sorted(unmarked)
        marks = [[dev, ino, path] for (dev, ino), path in self.marks.items()]
        version = camera.coverage_version(marks, self.unmarked)
        if version != self.version:
            self.version = version
            self.send_coverage()

    def door_of(self, path: str) -> str | None:
        for door, home in self.homes.items():
            if path == home or path.startswith(home + "/"):
                return door
        return None

    # --- events (R1, R4) ---------------------------------------------------------------------------

    def snapshot(self, pid: int) -> dict:
        """R4 with R4a: a full snapshot at most CACHE_SECONDS old, identity checked on every open."""
        t = time.monotonic()
        hit = self.cache.get(pid)
        if hit is not None and t - hit[1] < CACHE_SECONDS:
            try:
                with open(f"/proc/{pid}/stat", "rb") as f:
                    start, _ppid = camera._stat_fields(f.read().decode("utf-8", "replace"))
            except OSError:
                start = None
            if start is not None and start == hit[0]:
                return {**hit[2], "_cached": True}
        reader = camera.read_reader(pid)
        if reader.get("attribution") == "complete":
            self.cache[pid] = (reader["start_time"], t, reader)
        else:
            self.cache.pop(pid, None)
        if len(self.cache) > 4096:
            self.cache = {k: v for k, v in self.cache.items() if t - v[1] < CACHE_SECONDS}
        return reader

    @staticmethod
    def fresh_uid(pid: int):
        try:
            with open(f"/proc/{pid}/status", "rb") as f:
                return camera._real_uid(f.read().decode("utf-8", "replace"))
        except OSError:
            return None

    @staticmethod
    def fresh_cgroup(pid: int):
        try:
            with open(f"/proc/{pid}/cgroup", "rb") as f:
                return camera._cgroup_path(f.read().decode("utf-8", "replace"))
        except OSError:
            return None

    def answer_batch(self, buf: bytes) -> list[tuple]:
        """Answer every event in the batch (R1). Returns (t, path, reader) for each non-self open; the
        caller builds and sends messages only after every event here has been answered (R4a)."""
        seen: list[tuple] = []
        off = 0
        while off + EVENT.size <= len(buf):
            length, _v, _r, _meta, _mask, efd, pid = EVENT.unpack_from(buf, off)
            off += length if length >= EVENT.size else EVENT.size
            if efd < 0:
                continue
            item = None
            try:
                try:
                    path = os.readlink(f"/proc/self/fd/{efd}")
                except OSError:
                    path = None
                if pid != self.me and path is not None:
                    reader = self.snapshot(pid)
                    self.counts["opened"] += 1
                    exempt = camera.is_self_read(reader, path, self.homes)
                    if exempt and reader.get("_cached"):
                        # An exemption is never decided from a cached snapshot (R4a): re-read the
                        # fields R3 rests on, so a process that left a door's unit is not exempt.
                        fresh = dict(reader, uid=self.fresh_uid(pid), cgroup=self.fresh_cgroup(pid))
                        exempt = camera.is_self_read(fresh, path, self.homes)
                        if not exempt:
                            reader = camera.read_reader(pid)
                    if exempt:
                        self.counts["self_reads"] += 1
                    else:
                        reader = {k: v for k, v in reader.items() if k != "_cached"}
                        item = (now(), path, reader)
            except Exception:
                item = None  # attribution must never block the answer
            finally:
                try:
                    os.write(self.fan, RESPONSE.pack(efd, FAN_ALLOW))
                except OSError as e:
                    fail(f"response write: {e}")
                self.counts["answered"] += 1
                os.close(efd)
            if item is not None:
                seen.append(item)
        return seen

    def send_opens(self, seen: list[tuple]) -> None:
        for t, path, reader in seen:
            self.send({"kind": "open", "t": t, "path": path,
                       "path_sha256": hashlib.sha256(path.encode("utf-8", "surrogateescape")).hexdigest(),
                       "door": self.door_of(path), "reader": reader})

    def members_stamp(self):
        try:
            st = os.stat(self.members)
            return (st.st_ino, st.st_mtime_ns)
        except OSError:
            return None

    def run(self) -> None:
        last_ping = [0.0]

        def ping() -> None:
            sd_notify("WATCHDOG=1")
            last_ping[0] = time.monotonic()

        sd_notify("READY=1")  # R2a: the watchdog is armed before any reader can wait
        ping()
        self.rescan_all(ping)
        self.send_coverage()
        self.beat()
        t_beat = t_cov = time.monotonic()
        t_rescan = time.monotonic()
        pending: dict | None = None  # an in-progress rescan, one home per loop turn
        stamp = self.members_stamp()
        while True:
            ready, _, _ = select.select([self.fan], [], [], 0.25)
            if ready:
                try:
                    buf = os.read(self.fan, BATCH * EVENT.size)
                except BlockingIOError:
                    buf = b""
                if buf:
                    seen = self.answer_batch(buf)
                    ping()
                    self.send_opens(seen)
            t = time.monotonic()
            if t - last_ping[0] >= BEAT_EVERY:
                ping()
            if t - t_beat >= BEAT_EVERY:
                self.beat()
                t_beat = t
            new_stamp = self.members_stamp()
            changed = new_stamp != stamp
            stamp = new_stamp
            if pending is None and (changed or t - t_rescan >= RESCAN_EVERY):
                self.read_homes()  # R9: a members change starts a rescan at once
                pending = {"doors": deque(self.homes), "queued": set(self.homes), "desired": {}, "unmarked": []}
                t_rescan = t
            elif pending is not None and changed:
                # Join the rescan in progress rather than restarting it, so repeated changes can't
                # starve finish_rescan (unmarking and coverage).
                self.read_homes()
                for door in self.homes:
                    if door not in pending["queued"]:
                        pending["doors"].append(door)
                        pending["queued"].add(door)
            if pending is not None:
                if pending["doors"]:
                    door = pending["doors"].popleft()
                    if door in self.homes:
                        self.rescan_home(door, pending["desired"], pending["unmarked"])
                    ping()
                else:
                    self.finish_rescan(pending["desired"], pending["unmarked"])
                    pending = None
            if t - t_cov >= COVERAGE_EVERY:
                self.send_coverage()
                t_cov = t


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--community", default="/home/tony/projects/hamutay/community")
    ap.add_argument("--members", default=None)
    ap.add_argument("--socket", default=SOCKET_PATH)
    args = ap.parse_args()
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))  # R1a
    except (ValueError, OSError):
        pass
    community = Path(args.community)
    members = Path(args.members) if args.members else community / "plaza" / "members.json"
    try:
        Gate(community, members, args.socket).run()
    except SystemExit:
        raise
    except BaseException as e:  # R1: anything outside the per-event block ends the gate
        fail(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
