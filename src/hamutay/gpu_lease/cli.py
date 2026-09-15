from __future__ import annotations
import argparse, fcntl, json, signal, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import ledger
from .actions import (Ctx, REGISTRY, Lease, Renew, Release, Expire, EnsureStopped, ForceStop,
                      ReleaseForce, NotFree, run, resolve_dangling, is_free)
from .state import paths, locked, read_lease, read_quarantine, parse_instant, parse_ttl, MalformedState
from .systemd import Systemd


def _ctx(p, systemd, now, by="ayllu-gpu"):
    return Ctx(p, systemd, now=now, by=by)


def _expire_if_needed(ctx):
    if read_lease(ctx.paths, ctx.now()).kind == "expired":
        run(ctx, Expire(), REGISTRY)


def cmd_lease(a, ctx):
    exp = parse_instant(a.expected_until) if a.expected_until else None
    act = Lease(a.holder, a.purpose, parse_ttl(a.ttl), exp)
    with locked(ctx.paths):
        _expire_if_needed(ctx)
        out = run(ctx, act, REGISTRY)
    if out["outcome"] != "ok":
        print(f"lease refused: {out['detail'].get('error', out['outcome'])}", file=sys.stderr)
        return 2
    print(act.lease_id)
    return 0


def cmd_renew(a, ctx):
    with locked(ctx.paths):
        out = run(ctx, Renew(a.lease_id, parse_ttl(a.ttl)), REGISTRY)
    return 0 if out["outcome"] == "ok" else 2


def cmd_release(a, ctx):
    with locked(ctx.paths):
        if a.force:
            out = run(_ctx(ctx.paths, ctx.systemd, ctx.now, by=a.by), ReleaseForce(a.by, a.reason), REGISTRY)
            if out["outcome"] != "ok":
                print(f"release --force refused: {out['detail'].get('error', out['outcome'])}",
                      file=sys.stderr)
        else:
            view = read_lease(ctx.paths, ctx.now())
            if view.data is None or view.data["lease_id"] != a.lease_id:
                return 2
            out = run(ctx, Release(a.lease_id), REGISTRY)
    return 0 if out["outcome"] == "ok" else 2


def wait_ready(ctx, lease_id, min_remaining: timedelta, *, already_locked: bool = False) -> tuple[bool, str]:
    acked = any(r.get("phase") == "outcome" and r.get("outcome") == "ok"
                and r.get("action") in ("ensure_stopped", "force_stop") and r.get("episode_id") == lease_id
                for r in ledger.rows(ctx.paths))
    if not acked:
        return False, "no acknowledged stop for this lease"
    if ctx.systemd.show(ctx.server_unit)["active_state"] not in ("inactive", "failed"):
        return False, "server not inactive"

    def _check_under_lock():
        try:
            if read_quarantine(ctx.paths) is not None:
                return False, "quarantined"
        except MalformedState:
            return False, "quarantine unreadable"
        view = read_lease(ctx.paths, ctx.now())
        if view.kind != "live" or view.data["lease_id"] != lease_id:
            return False, f"lease {view.kind}"
        if parse_instant(view.data["expires_at"]) - ctx.now() < min_remaining:
            return False, "less than min-remaining left"
        return True, ""

    # flock is per file descriptor: a nested `locked(paths)` from inside a lock
    # already held by this process would deadlock, so a caller holding the lock
    # (Task 5, from inside the lease-run supervisor) says so and we skip taking
    # it again.
    if already_locked:
        return _check_under_lock()
    with locked(ctx.paths):
        return _check_under_lock()


def cmd_wait(a, ctx):
    deadline = time.monotonic() + parse_seconds(a.timeout)
    while True:
        ok, why = wait_ready(ctx, a.lease_id, parse_ttl(a.min_remaining))
        if ok:
            return 0
        if time.monotonic() >= deadline:
            print(f"wait: {why}", file=sys.stderr)
            return 3
        time.sleep(min(5.0, max(0.0, deadline - time.monotonic())))


def parse_seconds(s: str) -> float:
    if s.endswith("s"):
        return float(s[:-1])
    return parse_ttl(s).total_seconds()


def cmd_status(a, ctx):
    view = read_lease(ctx.paths, ctx.now())
    free, why = is_free(ctx)
    print(json.dumps({"state": "free" if free else why, "lease": view.data, "kind": view.kind,
                      "server": ctx.systemd.show(ctx.server_unit)}, indent=1, default=str))
    return 0


def door_dir(p) -> Path:
    return Path(p.door.read_text().strip())


def heartbeat_lock_path(door: Path) -> Path:
    return door / "session.jsonl.events.jsonl.heartbeat.lock"


def cmd_force_stop(a, ctx):
    from hamutay.events import EventStore
    from hamutay.heartbeat import append_heartbeat_status
    door = door_dir(ctx.paths)
    with locked(ctx.paths):
        view = read_lease(ctx.paths, ctx.now())
        if view.data is None or view.data["lease_id"] != a.lease_id:
            print("force-stop: no such lease", file=sys.stderr)
            return 2
        hb = heartbeat_lock_path(door).open("a")
        try:
            fcntl.flock(hb.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("force-stop refused: heartbeat is running; it will act within its poll interval, "
                  "or is inside a wake that must finish", file=sys.stderr)
            hb.close()
            return 4
        try:
            d = view.data
            append_heartbeat_status(EventStore(door / "session.jsonl.events.jsonl"),
                status="resting", reason="substrate_lent",
                detail={"episode_id": d["lease_id"], "holder": d["holder"], "purpose": d["purpose"],
                        "since": d["since"], "expires_at": d["expires_at"],
                        "expected_until": d.get("expected_until"), "source": "force_stop", "continuation": False},
                created_at=ctx.now().isoformat())
            out = run(_ctx(ctx.paths, ctx.systemd, ctx.now, by=a.by), ForceStop(a.lease_id), REGISTRY)
        finally:
            fcntl.flock(hb.fileno(), fcntl.LOCK_UN)
            hb.close()
    return 0 if out["outcome"] == "ok" else 1


def cmd_migrate_quiesce(a, ctx):
    """Stop the old heartbeat under its own store lock, once no wake is running.

    Migration precondition: the door has no door.json yet, so EventStore's
    lease_binding is unset and this only reads the store — no gate involved.
    """
    from hamutay.events import EventStore
    door = Path(a.door)
    store = EventStore(door / "session.jsonl.events.jsonl")
    deadline = time.monotonic() + parse_seconds(a.timeout)
    while True:
        with store._lock_path.open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                latest = store._latest_by_event_id_from_records(store._read_records_unlocked())
                if not any(r.get("status") == "running" for r in latest.values()):
                    subprocess.run([a.systemctl, "--user", "stop", a.unit], check=True)
                    return 0
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        if time.monotonic() >= deadline:
            print("migrate-quiesce: a wake is still running; nothing stopped", file=sys.stderr)
            return 1
        time.sleep(30)


def cmd_run(a, ctx):
    from . import run as run_mod
    launcher = getattr(a, "launcher", None)
    sleep = getattr(a, "sleep", None) or time.sleep
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    signal.signal(signal.SIGHUP, lambda *_: sys.exit(129))
    return run_mod.supervise(a, ctx, launcher=launcher, sleep=sleep)


def build_parser():
    ap = argparse.ArgumentParser(prog="ayllu-gpu")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("lease"); s.add_argument("--holder", required=True); s.add_argument("--purpose", required=True)
    s.add_argument("--ttl", default="6h"); s.add_argument("--expected-until"); s.set_defaults(fn=cmd_lease)
    s = sub.add_parser("renew"); s.add_argument("--lease-id", required=True); s.add_argument("--ttl", default="6h"); s.set_defaults(fn=cmd_renew)
    s = sub.add_parser("release"); s.add_argument("--lease-id"); s.add_argument("--force", action="store_true")
    s.add_argument("--by"); s.add_argument("--reason"); s.set_defaults(fn=cmd_release)
    s = sub.add_parser("wait"); s.add_argument("--lease-id", required=True); s.add_argument("--timeout", default="30m")
    s.add_argument("--min-remaining", default="3m"); s.set_defaults(fn=cmd_wait)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("force-stop"); s.add_argument("--lease-id", required=True); s.add_argument("--by", required=True)
    s.add_argument("--reason", required=True); s.set_defaults(fn=cmd_force_stop)
    s = sub.add_parser("run"); s.add_argument("--holder", required=True); s.add_argument("--purpose", required=True)
    s.add_argument("--ttl", default="15m"); s.add_argument("--expected-until")
    s.add_argument("--wait-timeout", default="30m")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("migrate-quiesce")
    s.add_argument("--door", required=True); s.add_argument("--unit", required=True)
    s.add_argument("--timeout", default="30m"); s.add_argument("--systemctl", default="systemctl")
    s.set_defaults(fn=cmd_migrate_quiesce)
    return ap


def main(argv=None, *, systemd=None, now=None, launcher=None, sleep=None, **overrides) -> int:
    a = build_parser().parse_args(argv)
    a.launcher = launcher
    a.sleep = sleep
    for k, v in overrides.items():
        setattr(a, k, v)
    if a.cmd == "release" and not a.force and not a.lease_id:
        print("release needs --lease-id (or --force --by --reason)", file=sys.stderr)
        return 2
    if a.cmd == "release" and a.force and not (a.by and a.reason):
        print("release --force needs --by and --reason", file=sys.stderr)
        return 2
    ctx = _ctx(paths(), systemd or Systemd(), now or (lambda: datetime.now(timezone.utc)))
    try:
        return a.fn(a, ctx)
    except (ValueError, NotFree) as e:
        print(f"{a.cmd}: {e}", file=sys.stderr)
        return 2
