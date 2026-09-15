from __future__ import annotations
import subprocess, sys, time
from datetime import timedelta
from .actions import REGISTRY, Lease, Renew, Release, WorkloadKilled, run, scope_dead
from .state import locked, read_lease, parse_ttl, parse_instant, scope_unit_for

MIN_TTL = timedelta(minutes=15)
KILL_MARGIN = timedelta(minutes=6)       # 30s detect + 60s grace + 90s stop + 60s bookkeeping + 120s margin
LAUNCH_MIN_REMAINING = timedelta(minutes=6)
RENEW_RETRY = 30.0
TERM_GRACE = 60.0
REGISTER_TIMEOUT = 10.0
POLL = 5.0


def default_launcher(scope_unit, command):
    unit = scope_unit[:-len(".scope")]
    return subprocess.Popen(["systemd-run", "--user", "--scope", "--unit", unit, "--collect", "--", *command])


def renew_once(ctx, lease_id, ttl) -> bool:
    with locked(ctx.paths):
        out = run(ctx, Renew(lease_id, ttl), REGISTRY)
    return out["outcome"] == "ok"


def _kill_scope(ctx, scope, sleep):
    ctx.systemd.kill(scope, "TERM")
    waited = 0.0
    while waited < TERM_GRACE and not scope_dead(ctx.systemd.show(scope)):
        sleep(POLL); waited += POLL
    with locked(ctx.paths):
        return run(ctx, WorkloadKilled(scope), REGISTRY)


def _release(ctx, lease_id):
    with locked(ctx.paths):
        return run(ctx, Release(lease_id), REGISTRY)


def _shutdown(ctx, scope, lease_id, sleep):
    """Stop the scope, observe it dead, then release — the one path every exit uses.
    If the kill's outcome is not ok, do NOT release: the lease and tombstone stay in
    place for the next actor to resolve (controller ruling 4)."""
    kill_out = _kill_scope(ctx, scope, sleep)
    if kill_out["outcome"] == "ok":
        _release(ctx, lease_id)
    else:
        print("run: could not confirm the workload was killed; lease left in place "
              "for the next actor to resolve", file=sys.stderr)
    return kill_out


def supervise(a, ctx, *, launcher=None, sleep=time.sleep) -> int:
    from .cli import wait_ready, parse_seconds  # deferred: cli imports run.supervise at module load

    launcher = launcher or default_launcher
    ttl = parse_ttl(a.ttl)
    if ttl < MIN_TTL:
        print(f"run: --ttl must be at least 15m (got {a.ttl})", file=sys.stderr)
        return 2
    command = [c for c in a.command if c != "--"]
    if not command:
        print("run: no command after --", file=sys.stderr)
        return 2
    exp = parse_instant(a.expected_until) if a.expected_until else None
    act = Lease(a.holder, a.purpose, ttl, exp)
    with locked(ctx.paths):
        out = run(ctx, act, REGISTRY)
    if out["outcome"] != "ok":
        print(f"run: lease refused: {out['detail'].get('error', out['outcome'])}", file=sys.stderr)
        return 2
    lease_id, scope = act.lease_id, scope_unit_for(act.lease_id)
    renew_period = ttl.total_seconds() / 3
    last_renew = ctx.now()

    def tick():
        """Renew on schedule; return True if the lease is safe to keep running on."""
        nonlocal last_renew
        now = ctx.now()
        if (now - last_renew).total_seconds() >= renew_period:
            if renew_once(ctx, lease_id, ttl):
                last_renew = now
        view = read_lease(ctx.paths, now)
        if view.kind != "live" or view.data["lease_id"] != lease_id:
            return False
        return parse_instant(view.data["expires_at"]) - now > KILL_MARGIN

    launched = False
    try:
        # wait, supervising
        deadline = ctx.now() + timedelta(seconds=parse_seconds(a.wait_timeout))
        while True:
            ok, why = wait_ready(ctx, lease_id, LAUNCH_MIN_REMAINING)
            if ok:
                break
            if not tick() or ctx.now() >= deadline:
                print(f"run: wait failed: {why}", file=sys.stderr)
                _release(ctx, lease_id)
                return 3
            sleep(POLL)

        # launch under the lock, after re-checking, and confirm registration before releasing the lock
        with locked(ctx.paths):
            ok, why = wait_ready(ctx, lease_id, LAUNCH_MIN_REMAINING, already_locked=True)
            if not ok:
                print(f"run: launch refused: {why}", file=sys.stderr)
                _release(ctx, lease_id)
                return 3
            proc = launcher(scope, command)
            launched = True
            waited = 0.0
            while waited < REGISTER_TIMEOUT and ctx.systemd.show(scope)["load_state"] != "loaded":
                sleep(1.0); waited += 1.0
            registered = ctx.systemd.show(scope)["load_state"] == "loaded"
        if not registered:
            _shutdown(ctx, scope, lease_id, sleep)
            return 6

        # supervise the workload
        killed = False
        while proc.poll() is None:
            if not tick():
                kill_out = _kill_scope(ctx, scope, sleep)
                killed = True
                if kill_out["outcome"] != "ok":
                    print("run: could not confirm the workload was killed; lease left in place "
                          "for the next actor to resolve", file=sys.stderr)
                    return 5
                break
            sleep(POLL)
        if not killed:
            # command exited; make sure the whole scope is gone before release
            if not scope_dead(ctx.systemd.show(scope)):
                kill_out = _kill_scope(ctx, scope, sleep)
                if kill_out["outcome"] != "ok":
                    print("run: could not confirm the scope was dead after exit; lease left in place "
                          "for the next actor to resolve", file=sys.stderr)
                    return 5
        _release(ctx, lease_id)
        return 5 if killed else int(proc.returncode or 0)
    except (KeyboardInterrupt, SystemExit):
        if launched:
            _shutdown(ctx, scope, lease_id, sleep)
        else:
            _release(ctx, lease_id)
        raise
