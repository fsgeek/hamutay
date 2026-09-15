from __future__ import annotations
import fcntl, hashlib, json, os, traceback, uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable
from . import ledger
from .state import (Paths, read_lease, read_quarantine, list_tombstones, MalformedState,
                    write_atomic, parse_instant, parse_ttl, scope_unit_for, RESOURCE)
from .systemd import SystemdUnavailable

SERVER_UNIT = "hamutay-llama-server.service"

FRAMEWORK_KEYS = {"record_type", "action_id", "phase", "action", "by", "at"}

@dataclass
class Ctx:
    paths: Paths
    systemd: object
    now: Callable[[], datetime]
    by: str
    server_unit: str = SERVER_UNIT

class Action:
    name: str = ""
    action_id: str = ""
    intent_fields: dict
    extra_detail: dict | None = None

    def intent(self, ctx: Ctx) -> dict: return {}
    def perform(self, ctx: Ctx) -> None: ...
    def predicate(self, ctx: Ctx) -> bool: raise NotImplementedError
    def observe(self, ctx: Ctx) -> dict:
        obs = {}
        try:
            obs["server"] = ctx.systemd.show(ctx.server_unit)
        except SystemdUnavailable as e:
            obs["server_error"] = str(e)
        try:
            lease = read_lease(ctx.paths, ctx.now())
            obs["lease_present"] = lease.kind != "absent"
            obs["lease_kind"] = lease.kind
            obs["lease_mutation_id"] = (lease.data or {}).get("mutation_id")
        except OSError as e:
            obs["lease_error"] = str(e)
        try:
            q = read_quarantine(ctx.paths)
            obs["quarantine_id"] = q and q.get("quarantine_id")
        except MalformedState as e:
            obs["quarantine_error"] = str(e)
        obs["tombstones"] = list_tombstones(ctx.paths)
        return obs

def _assert_locked(ctx: Ctx) -> None:
    """The caller must hold 4090.lock: a non-blocking probe that succeeds means nobody does."""
    if ctx.paths is None:
        raise RuntimeError("run() needs a Ctx with paths and the lock held")
    with ctx.paths.lock.open("a") as probe:
        try:
            fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
    raise RuntimeError("run() called without holding 4090.lock")

def _row(ctx, action, action_id, phase, fields=None):
    return ledger.append(ctx.paths, {**(fields or {}), "record_type": "gpu_lease", "action_id": action_id,
                                     "phase": phase, "action": action.name, "by": ctx.by,
                                     "at": ctx.now().isoformat()})

def _finish(ctx, action, action_id, *, reconciled=False, error=None, observation_failed=None):
    try:
        obs = action.observe(ctx)
        held = action.predicate(ctx)
    except Exception as e:
        obs, held = {"error": str(e)}, None
    if observation_failed is not None:
        outcome = "indeterminate"
    elif error is not None:
        outcome = "error"
    elif held is None:
        outcome = "indeterminate"
    else:
        outcome = "ok" if held else "not_performed"
    err = observation_failed if observation_failed is not None else error
    detail = {**dict(action.extra_detail or {}), **({"error": err} if err else {})}
    # Outcome rows carry the intent's fields; the outcome row's own keys win on collision.
    row = _row(ctx, action, action_id, "outcome", {
        **action.intent_fields,
        "outcome": outcome, "observed": obs, "detail": detail,
        **({"reconciled": True} if reconciled else {}),
    })
    return row

def run(ctx: Ctx, action: Action, registry: dict | None = None) -> dict:
    _assert_locked(ctx)
    if registry:
        resolve_dangling(ctx, registry)
    action_id = str(uuid.uuid4())
    action.action_id = action_id
    action.intent_fields = action.intent(ctx)
    _row(ctx, action, action_id, "intent", action.intent_fields)
    error = None
    observation_failed = None
    try:
        action.perform(ctx)
    except (SystemdUnavailable, MalformedState, OSError) as e:
        # The spec's blanket rule: any action whose perform() cannot read
        # systemctl show or a state file goes indeterminate -> quarantine_enter,
        # never a hard error.
        observation_failed = f"{type(e).__name__}: {e}"
    except Exception as e:  # every other failure is an outcome, never a lost intent
        error = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"
    return _finish(ctx, action, action_id, error=error, observation_failed=observation_failed)

def resolve_dangling(ctx: Ctx, registry: dict[str, Callable[[dict], Action]]) -> list[dict]:
    """For each dangling intent: rebuild the action from its intent row, perform any owed
    side effects (perform is idempotent by contract), evaluate, write the reconciled outcome."""
    _assert_locked(ctx)
    done = []
    for intent in ledger.dangling_intents(ledger.rows(ctx.paths)):
        build = registry.get(intent.get("action"))
        if build is None:
            done.append(_row(ctx, type("Unknown", (Action,), {"name": intent.get("action", "?")})(),
                             intent["action_id"], "outcome", {"outcome": "indeterminate", "reconciled": True,
                             "observed": {}, "detail": {"error": "no reconciler for this action"}}))
            continue
        action = build(intent)
        action.action_id = intent["action_id"]
        action.intent_fields = {k: v for k, v in intent.items() if k not in FRAMEWORK_KEYS}
        error = None
        observation_failed = None
        try:
            if not action.predicate(ctx):
                action.perform(ctx)
        except (SystemdUnavailable, MalformedState, OSError) as e:
            # Same rule as run(): an observation failure during reconciliation is
            # indeterminate, never a hard error.
            observation_failed = f"{type(e).__name__}: {e}"
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        done.append(_finish(ctx, action, intent["action_id"], reconciled=True,
                            error=error, observation_failed=observation_failed))
    return done


# --- Concrete actions --------------------------------------------------

class NotFree(Exception):
    pass


def scope_dead(obs: dict) -> bool:
    return obs.get("load_state") == "not-found" or obs.get("active_state") in ("inactive", "failed")


def is_free(ctx: Ctx) -> tuple[bool, str]:
    try:
        if read_quarantine(ctx.paths) is not None:
            return False, "quarantine"
    except MalformedState:
        return False, "quarantine_unreadable"
    view = read_lease(ctx.paths, ctx.now())
    if view.kind == "malformed":
        return False, "lease_malformed"
    if view.kind == "live":
        return False, "lease"
    if view.kind == "expired":
        return False, "expired"     # an Expire action must run first
    if list_tombstones(ctx.paths):
        return False, "tombstone"
    return True, ""


def _tombstone(ctx, scope_unit):
    return ctx.paths.tombstones / scope_unit


class WorkloadKilled(Action):
    name = "workload_killed"

    def __init__(self, scope_unit):
        self.scope_unit = scope_unit

    def intent(self, ctx):
        return {"scope_unit": self.scope_unit}

    def perform(self, ctx):
        # A SystemdUnavailable here propagates to run()'s framework guard, which
        # reports indeterminate (spec: any unreadable systemctl show/state file ->
        # indeterminate -> quarantine_enter). The tombstone is only unlinked once
        # the stop is actually observed dead, so a failure after a successful stop
        # doesn't silently skip removing it.
        obs = ctx.systemd.show(self.scope_unit)
        if not scope_dead(obs):
            ctx.systemd.stop(self.scope_unit)
        if scope_dead(ctx.systemd.show(self.scope_unit)):
            try:
                _tombstone(ctx, self.scope_unit).unlink()
            except FileNotFoundError:
                pass

    def predicate(self, ctx):
        return scope_dead(ctx.systemd.show(self.scope_unit)) and not _tombstone(ctx, self.scope_unit).exists()

    def observe(self, ctx):
        obs = super().observe(ctx)
        try:
            obs["scope"] = {"scope_unit": self.scope_unit, **ctx.systemd.show(self.scope_unit)}
        except SystemdUnavailable as e:
            obs["scope_error"] = str(e)
        return obs


def _workload_killed(row):
    return WorkloadKilled(row["scope_unit"])


def resolve_tombstones(ctx: Ctx) -> list[dict]:
    """Run one workload_killed per tombstone, in order; stop and quarantine on the first failure."""
    outs = []
    for scope in list_tombstones(ctx.paths):
        out = run(ctx, WorkloadKilled(scope))
        outs.append(out)
        if out["outcome"] != "ok":
            quarantine_if_indeterminate(ctx, out, reason="scope_unkillable")
            break
    return outs


class QuarantineEnter(Action):
    name = "quarantine_enter"

    def __init__(self, reason, observed_digest, cause_action_id=None):
        self.reason, self.digest, self.cause = reason, observed_digest, cause_action_id
        self.quarantine_id = str(uuid.uuid4())

    def intent(self, ctx):
        return {"reason": self.reason, "observed_digest": self.digest,
                "cause_action_id": self.cause, "quarantine_id": self.quarantine_id}

    def perform(self, ctx):
        write_atomic(ctx.paths.quarantine, {
            "quarantine_id": self.quarantine_id, "reason": self.reason,
            "source_action_id": self.action_id, "cause_action_id": self.cause,
            "observed_digest": self.digest, "at": ctx.now().isoformat()})

    def predicate(self, ctx):
        try:
            q = read_quarantine(ctx.paths)
        except MalformedState:
            return False
        return bool(q) and q.get("source_action_id") == self.action_id


def _quarantine_enter(row):
    action = QuarantineEnter(row["reason"], row.get("observed_digest"), row.get("cause_action_id"))
    action.quarantine_id = row["quarantine_id"]
    return action


def quarantine_if_indeterminate(ctx: Ctx, outcome_row: dict, reason="indeterminate_action") -> dict | None:
    if outcome_row.get("outcome") != "indeterminate" and reason == "indeterminate_action":
        return None
    digest = hashlib.sha256(json.dumps(outcome_row.get("observed", {}), sort_keys=True).encode()).hexdigest()[:16]
    return run(ctx, QuarantineEnter(reason, digest, cause_action_id=outcome_row.get("action_id")))


class Lease(Action):
    name = "lease"

    def __init__(self, holder, purpose, ttl: timedelta, expected_until):
        self.holder, self.purpose, self.ttl, self.expected_until = holder, purpose, ttl, expected_until
        self.lease_id = None
        self.generation_before = 0

    def intent(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        renewing = view.kind == "live" and view.data["holder"] == self.holder
        self.lease_id = view.data["lease_id"] if renewing else str(uuid.uuid4())
        self.generation_before = view.data["generation"] if renewing else 0
        return {"holder": self.holder, "purpose": self.purpose, "ttl_seconds": int(self.ttl.total_seconds()),
                "lease_id": self.lease_id, "scope_unit": scope_unit_for(self.lease_id),
                "generation_before": self.generation_before, "episode_id": self.lease_id,
                "expected_until": self.expected_until.isoformat() if self.expected_until else None}

    def perform(self, ctx):
        # lease_id is fixed by intent(): a renew reuses the existing id, a fresh
        # lease uses the id chosen there. Never recompute it here.
        now = ctx.now()
        view = read_lease(ctx.paths, now)
        if view.kind == "live" and view.data["holder"] == self.holder:
            data = dict(view.data)
            data["generation"] += 1
        else:
            free, why = is_free(ctx)
            if not free:
                raise NotFree(why)
            data = {"resource": RESOURCE, "lease_id": self.lease_id, "generation": 1,
                    "holder": self.holder, "purpose": self.purpose, "since": now.isoformat(),
                    "scope_unit": scope_unit_for(self.lease_id)}
        data["mutation_id"] = self.action_id
        data["expires_at"] = (now + self.ttl).isoformat()
        if self.expected_until is not None:
            data["expected_until"] = self.expected_until.isoformat()
        write_atomic(ctx.paths.lease, data)
        ctx.paths.tombstones.mkdir(parents=True, exist_ok=True)
        _tombstone(ctx, data["scope_unit"]).touch()

    def predicate(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        return (view.data is not None and view.data.get("mutation_id") == self.action_id
                and _tombstone(ctx, view.data["scope_unit"]).exists())


def _lease_builder(row):
    action = Lease(row["holder"], row["purpose"], timedelta(seconds=row["ttl_seconds"]),
                    parse_instant(row["expected_until"]) if row.get("expected_until") else None)
    # resolve_dangling never calls intent(): restore what intent() would have set.
    action.lease_id = row["lease_id"]
    action.generation_before = row["generation_before"]
    return action


class Renew(Action):
    name = "renew"

    def __init__(self, lease_id, ttl: timedelta):
        self.lease_id, self.ttl = lease_id, ttl

    def intent(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        return {"lease_id": self.lease_id, "ttl": f"{int(self.ttl.total_seconds()) // 60}m",
                "generation_before": (view.data or {}).get("generation"), "episode_id": self.lease_id}

    def perform(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        if view.kind != "live" or view.data["lease_id"] != self.lease_id:
            raise NotFree(f"no live lease {self.lease_id}")
        data = dict(view.data)
        data["generation"] += 1
        data["mutation_id"] = self.action_id
        data["expires_at"] = (ctx.now() + self.ttl).isoformat()
        write_atomic(ctx.paths.lease, data)

    def predicate(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        return view.data is not None and view.data.get("mutation_id") == self.action_id


def _renew_builder(row):
    return Renew(row["lease_id"], parse_ttl(row["ttl"]))


class Release(Action):
    name = "release"

    def __init__(self, lease_id):
        self.lease_id = lease_id
        self.generation_before = 0
        self.scope_unit = None

    def intent(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        d = view.data or {}
        self.generation_before = d.get("generation", 0)
        self.scope_unit = d.get("scope_unit") or scope_unit_for(self.lease_id)
        return {"lease_id": self.lease_id, "generation_before": self.generation_before,
                "scope_unit": self.scope_unit, "episode_id": self.lease_id}

    def perform(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        if view.data is not None and view.data["lease_id"] != self.lease_id:
            raise NotFree("lease belongs to another id")
        if not scope_dead(ctx.systemd.show(self.scope_unit)):
            ctx.systemd.stop(self.scope_unit)
        if scope_dead(ctx.systemd.show(self.scope_unit)):
            try:
                _tombstone(ctx, self.scope_unit).unlink()
            except FileNotFoundError:
                pass
            if view.data is not None:
                ctx.paths.lease.unlink(missing_ok=True)

    def predicate(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        if view.kind == "absent":
            lease_gone = True
        elif view.data["lease_id"] != self.lease_id:
            lease_gone = True
        elif view.data["generation"] > self.generation_before:
            # cannot happen for a release (release never bumps generation), kept
            # for symmetry/honesty of the predicate.
            lease_gone = True
        else:
            lease_gone = False
        return (scope_dead(ctx.systemd.show(self.scope_unit)) and not _tombstone(ctx, self.scope_unit).exists()
                and lease_gone)


def _release_builder(row):
    action = Release(row["lease_id"])
    action.generation_before = row["generation_before"]
    action.scope_unit = row["scope_unit"]
    return action


class Expire(Release):
    name = "expire"

    def __init__(self):
        self.lease_id = None
        self.generation_before = 0
        self.scope_unit = None

    def intent(self, ctx):
        view = read_lease(ctx.paths, ctx.now())
        if view.kind != "expired":
            raise NotFree("nothing expired")
        self.lease_id = view.data["lease_id"]
        return super().intent(ctx)


def _expire_builder(row):
    action = Expire()
    action.lease_id = row["lease_id"]
    action.generation_before = row["generation_before"]
    action.scope_unit = row["scope_unit"]
    return action


class EnsureStopped(Action):
    name = "ensure_stopped"

    def __init__(self, episode_id):
        self.episode_id = episode_id
        self.already = None

    def intent(self, ctx):
        return {"episode_id": self.episode_id}

    def perform(self, ctx):
        obs = ctx.systemd.show(ctx.server_unit)
        self.already = obs["active_state"] in ("inactive", "failed")
        if not self.already:
            ctx.systemd.stop(ctx.server_unit)
        self.extra_detail = {"already_inactive": self.already}

    def predicate(self, ctx):
        return ctx.systemd.show(ctx.server_unit)["active_state"] in ("inactive", "failed")


def _ensure_stopped_builder(row):
    return EnsureStopped(row["episode_id"])


class ForceStop(EnsureStopped):
    name = "force_stop"


def _force_stop_builder(row):
    return ForceStop(row["episode_id"])


class ServerStart(Action):
    name = "server_start"

    def intent(self, ctx):
        return {}

    def perform(self, ctx):
        free, why = is_free(ctx)
        if not free:
            raise NotFree(why)
        if ctx.systemd.show(ctx.server_unit)["active_state"] not in ("active", "activating"):
            ctx.systemd.start(ctx.server_unit)

    def predicate(self, ctx):
        return ctx.systemd.show(ctx.server_unit)["active_state"] in ("active", "activating")


def _server_start_builder(row):
    return ServerStart()


class ReleaseForce(Action):
    name = "release_force"

    def __init__(self, by, reason):
        self.who, self.reason = by, reason
        self.originals = []

    def _escrow(self, ctx, name):
        return ctx.paths.dir / f"{RESOURCE}.{name}.escrow-{self.action_id}"

    def intent(self, ctx):
        self.originals = [n for n in ("lease", "quarantine") if getattr(ctx.paths, n).exists()]
        return {"reason": self.reason, "forced_by": self.who, "originals_present": self.originals,
                "tombstones": list_tombstones(ctx.paths)}

    def perform(self, ctx):
        for scope in list_tombstones(ctx.paths):
            run(ctx, WorkloadKilled(scope))
        for name in self.originals:
            orig = getattr(ctx.paths, name)
            if orig.exists():
                os.replace(orig, self._escrow(ctx, name))
            self._escrow(ctx, name).unlink(missing_ok=True)

    def predicate(self, ctx):
        for name in self.originals:
            if getattr(ctx.paths, name).exists() or self._escrow(ctx, name).exists():
                return False
        return not list_tombstones(ctx.paths)


def _release_force_builder(row):
    action = ReleaseForce(row.get("forced_by"), row.get("reason"))
    action.originals = row["originals_present"]
    return action


REGISTRY: dict[str, Callable[[dict], Action]] = {
    "lease": _lease_builder,
    "renew": _renew_builder,
    "release": _release_builder,
    "expire": _expire_builder,
    "release_force": _release_force_builder,
    "quarantine_enter": _quarantine_enter,
    "ensure_stopped": _ensure_stopped_builder,
    "force_stop": _force_stop_builder,
    "server_start": _server_start_builder,
    "workload_killed": _workload_killed,
}
