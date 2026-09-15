from __future__ import annotations
import subprocess, sys, time
from datetime import timedelta
from .actions import REGISTRY, Lease, Renew, Release, WorkloadKilled, run, scope_dead, quarantine_if_indeterminate
from .cli import wait_ready, parse_seconds, _expire_if_needed
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


def _release_if_ours(ctx, lease_id):
    """Release only if the lease is still ours: a wait-loop failure can mean the lease was
    replaced by another holder, and releasing then would tear down someone else's lease
    (Important 5). Live or expired-but-still-named-ours both count as "ours to clean up";
    anything else (absent, or a different lease_id) is left alone."""
    view = read_lease(ctx.paths, ctx.now())
    if view.data is not None and view.data.get("lease_id") == lease_id:
        _release(ctx, lease_id)
    else:
        print("run: lease no longer ours; not releasing", file=sys.stderr)


def _shutdown(ctx, scope, lease_id, sleep, *, exit_code):
    """Stop the scope, observe it dead, then release — the one path every non-happy exit
    uses. If the kill's outcome is not ok, quarantine (scope_unkillable) and do NOT
    release: the lease and tombstone stay in place for the next actor to resolve
    (controller ruling 4 and CRITICAL 2)."""
    kill_out = _kill_scope(ctx, scope, sleep)
    if kill_out["outcome"] == "ok":
        _release(ctx, lease_id)
    else:
        with locked(ctx.paths):
            quarantine_if_indeterminate(ctx, kill_out, reason="scope_unkillable")
        print("run: could not confirm the workload was killed; quarantined, lease left in "
              "place for the next actor to resolve", file=sys.stderr)
    return exit_code


def supervise(a, ctx, *, launcher=None, sleep=time.sleep) -> int:
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
        # An expired lease is not FREE until an `expire` action kills its scope
        # and removes it. `ayllu-gpu lease` does this; `run` did not, so a lease
        # left expired by a dead holder refused every subsequent run with exit 2
        # until someone ran `lease` or `release` by hand.
        _expire_if_needed(ctx)
        out = run(ctx, act, REGISTRY)
    if out["outcome"] != "ok":
        print(f"run: lease refused: {out['detail'].get('error', out['outcome'])}", file=sys.stderr)
        return 2
    lease_id, scope = act.lease_id, scope_unit_for(act.lease_id)
    renew_period = ttl.total_seconds() / 3
    last_renew = ctx.now()
    last_attempt = None

    def tick():
        """Renew on schedule; return True if the lease is safe to keep running on.

        The kill predicate here is time-only (expires_at - now <= KILL_MARGIN): expires_at
        is re-read from the lease file on every call, so a renew that landed is already
        reflected in it. That is what makes this satisfy the spec's "...and the last renew
        did not succeed" clause by construction — no separate success/failure flag needed.
        """
        nonlocal last_renew, last_attempt
        now = ctx.now()
        due = (now - last_renew).total_seconds() >= renew_period
        retry_ok = last_attempt is None or (now - last_attempt).total_seconds() >= RENEW_RETRY
        if due and retry_ok:
            last_attempt = now
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
                _release_if_ours(ctx, lease_id)
                return 3
            sleep(POLL)

        # launch under the lock, after re-checking, and confirm registration before releasing the lock
        launch_refused = False
        proc = None
        registered = False
        with locked(ctx.paths):
            ok, why = wait_ready(ctx, lease_id, LAUNCH_MIN_REMAINING, already_locked=True)
            if not ok:
                launch_refused = True
            else:
                proc = launcher(scope, command)
                launched = True
                waited = 0.0
                while waited < REGISTER_TIMEOUT and ctx.systemd.show(scope)["load_state"] != "loaded":
                    sleep(1.0); waited += 1.0
                registered = ctx.systemd.show(scope)["load_state"] == "loaded"
        if launch_refused:
            print(f"run: launch refused: {why}", file=sys.stderr)
            _release_if_ours(ctx, lease_id)
            return 3
        if not registered:
            return _shutdown(ctx, scope, lease_id, sleep, exit_code=6)

        # supervise the workload
        killed = False
        while proc.poll() is None:
            if not tick():
                killed = True
                break
            sleep(POLL)
        if killed:
            return _shutdown(ctx, scope, lease_id, sleep, exit_code=5)
        # command exited; make sure the whole scope is gone before release (release never
        # precedes scope death)
        if not scope_dead(ctx.systemd.show(scope)):
            return _shutdown(ctx, scope, lease_id, sleep, exit_code=5)
        _release(ctx, lease_id)
        rc = proc.returncode
        if rc is None:
            return 5
        if rc < 0:
            return 128 + (-rc)
        return rc
    except (KeyboardInterrupt, SystemExit):
        if launched:
            _shutdown(ctx, scope, lease_id, sleep, exit_code=5)
        else:
            _release_if_ours(ctx, lease_id)
        raise
