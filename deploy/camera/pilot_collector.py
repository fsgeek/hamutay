"""Camera pilot: record who opens files in each door's home and the plaza.

Phase-1 pilot for docs/superpowers/specs/2026-10-03-access-camera-design.md,
run as root (fanotify needs CAP_SYS_ADMIN; WSL2 refuses kernel audit even to
root, so the design's Source A is out). Notification class only: it never
blocks or refuses a read. A reader that exits before its /proc entry is read
is recorded with its pid and attribution "lost", and the rate of that is the
pilot's main measurement.

Output: one JSON line per (reader, path) per coalescing window, to --out.
Never records command lines (they can carry secrets): only exe, comm,
uid, and the systemd unit or session from the cgroup.
"""

import argparse
import ctypes
import json
import os
import re
import select
import struct
import sys
import time
from datetime import datetime, timezone

FAN_CLASS_NOTIF, FAN_CLASS_CONTENT, FAN_CLOEXEC = 0x0, 0x4, 0x1
FAN_OPEN_PERM, FAN_ALLOW = 0x00010000, 0x01
RESPONSE = struct.Struct("iI")  # fd, response
FAN_OPEN, FAN_EVENT_ON_CHILD, FAN_MARK_ADD = 0x20, 0x08000000, 0x1
AT_FDCWD = -100
EVENT = struct.Struct("IBBHQii")  # event_len, vers, reserved, metadata_len, mask, fd, pid

libc = ctypes.CDLL("libc.so.6", use_errno=True)


def unit_of(cgroup_text: str) -> str:
    """The most specific systemd unit or scope named in a cgroup path."""
    path = cgroup_text.strip().rsplit(":", 1)[-1]
    units = re.findall(r"[^/]+\.(?:service|scope)", path)
    return units[-1] if units else path or "?"


def attribute(pid: int) -> dict:
    try:
        exe = os.readlink(f"/proc/{pid}/exe")
        with open(f"/proc/{pid}/cgroup") as f:
            unit = unit_of(f.read())
        with open(f"/proc/{pid}/comm") as f:
            comm = f.read().strip()
        uid = os.stat(f"/proc/{pid}").st_uid
        return {"attribution": "ok", "exe": exe, "comm": comm, "unit": unit, "uid": uid}
    except OSError:
        return {"attribution": "lost"}


def door_of(path: str, community: str) -> str | None:
    rel = os.path.relpath(path, community)
    head = rel.split(os.sep, 1)[0]
    return None if head.startswith("..") else head


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--community", default="/home/tony/projects/hamutay/community")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=600)
    ap.add_argument("--window", type=float, default=60)
    ap.add_argument("--perm", action="store_true",
                    help="permission mode: hold each open until its reader is attributed, then ALWAYS allow")
    args = ap.parse_args()

    klass = FAN_CLASS_CONTENT if args.perm else FAN_CLASS_NOTIF
    mask = FAN_OPEN_PERM if args.perm else FAN_OPEN
    fd = libc.fanotify_init(klass | FAN_CLOEXEC, os.O_RDONLY | os.O_LARGEFILE)
    if fd < 0:
        sys.exit(f"fanotify_init: {os.strerror(ctypes.get_errno())}")
    watched = []
    for name in sorted(os.listdir(args.community)):
        d = os.path.join(args.community, name)
        if os.path.isdir(d):
            if libc.fanotify_mark(fd, FAN_MARK_ADD, mask | FAN_EVENT_ON_CHILD, AT_FDCWD, d.encode()) != 0:
                sys.exit(f"fanotify_mark {d}: {os.strerror(ctypes.get_errno())}")
            watched.append(name)

    me = os.getpid()
    open_windows: dict[tuple, dict] = {}
    deadline = time.monotonic() + args.seconds
    out = open(args.out, "a", buffering=1)
    out.write(json.dumps({"record": "start", "at": datetime.now(timezone.utc).isoformat(), "watched": watched, "perm": args.perm}) + "\n")
    held_us: list[float] = []

    def flush(older_than: float) -> None:
        for key in [k for k, v in open_windows.items() if v["_t0"] <= older_than]:
            rec = open_windows.pop(key)
            rec.pop("_t0")
            out.write(json.dumps(rec) + "\n")

    os.set_blocking(fd, False)
    while time.monotonic() < deadline:
        # Block on the fd, not a sleep: in permission mode every waiting reader
        # pays for our wake-up latency.
        ready, _, _ = select.select([fd], [], [], 0.5)
        if not ready:
            flush(time.monotonic() - args.window)
            continue
        try:
            buf = os.read(fd, 65536)
        except BlockingIOError:
            continue
        off = 0
        while off + EVENT.size <= len(buf):
            length, _, _, _, _mask, efd, pid = EVENT.unpack_from(buf, off)
            off += length
            if efd < 0:
                continue
            t_in = time.perf_counter()
            try:
                path = os.readlink(f"/proc/self/fd/{efd}")
                # In permission mode the reader is still blocked here, so /proc/<pid> exists.
                who = attribute(pid) if pid != me else None
            finally:
                if args.perm:  # never refuse: always allow, even if attribution failed
                    os.write(fd, RESPONSE.pack(efd, FAN_ALLOW))
                    held_us.append((time.perf_counter() - t_in) * 1e6)
                os.close(efd)
            if pid == me:
                continue
            door = door_of(path, args.community)
            self_read = (who.get("unit") == f"hamutay-heartbeat@{door}.service")
            key = (pid, path)
            now = time.monotonic()
            if key in open_windows:
                open_windows[key]["count"] += 1
            else:
                open_windows[key] = {
                    "record": "open", "at": datetime.now(timezone.utc).isoformat(),
                    "pid": pid, "path": path, "door": door, "self_read": self_read,
                    "count": 1, "_t0": now, **who,
                }
        flush(time.monotonic() - args.window)
    flush(float("inf"))
    held = sorted(held_us)
    stats = ({"n": len(held), "p50_us": held[len(held) // 2], "p99_us": held[int(len(held) * 0.99)],
              "max_us": held[-1]} if held else {})
    out.write(json.dumps({"record": "stop", "at": datetime.now(timezone.utc).isoformat(), "held": stats}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
