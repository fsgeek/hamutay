from __future__ import annotations
import fcntl, traceback, uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from . import ledger
from .state import Paths, read_lease, read_quarantine, list_tombstones, MalformedState
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

def _row(ctx, action, action_id, phase, **fields):
    return ledger.append(ctx.paths, {"action_id": action_id, "phase": phase, "action": action.name,
                                     "by": ctx.by, "at": ctx.now().isoformat(), **fields})

def _finish(ctx, action, action_id, *, reconciled=False, error=None):
    try:
        obs = action.observe(ctx)
        held = action.predicate(ctx)
    except (SystemdUnavailable, MalformedState, OSError) as e:
        obs, held = {"error": str(e)}, None
    if error is not None:
        outcome = "error"
    elif held is None:
        outcome = "indeterminate"
    else:
        outcome = "ok" if held else "not_performed"
    detail = {"error": error} if error else {}
    # Outcome rows carry the intent's fields; the outcome row's own keys win on collision.
    intent_fields = getattr(action, "intent_fields", {}) or {}
    row = _row(ctx, action, action_id, "outcome", **{
        **intent_fields,
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
    _row(ctx, action, action_id, "intent", **action.intent_fields)
    error = None
    try:
        action.perform(ctx)
    except Exception as e:  # every failure is an outcome, never a lost intent
        error = f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"
    return _finish(ctx, action, action_id, error=error)

def resolve_dangling(ctx: Ctx, registry: dict[str, Callable[[dict], Action]]) -> list[dict]:
    """For each dangling intent: rebuild the action from its intent row, perform any owed
    side effects (perform is idempotent by contract), evaluate, write the reconciled outcome."""
    _assert_locked(ctx)
    done = []
    for intent in ledger.dangling_intents(ledger.rows(ctx.paths)):
        build = registry.get(intent.get("action"))
        if build is None:
            done.append(_row(ctx, type("Unknown", (Action,), {"name": intent.get("action", "?")})(),
                             intent["action_id"], "outcome", outcome="indeterminate", reconciled=True,
                             observed={}, detail={"error": "no reconciler for this action"}))
            continue
        action = build(intent)
        action.action_id = intent["action_id"]
        action.intent_fields = {k: v for k, v in intent.items() if k not in FRAMEWORK_KEYS}
        error = None
        try:
            if not action.predicate(ctx):
                action.perform(ctx)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        done.append(_finish(ctx, action, intent["action_id"], reconciled=True, error=error))
    return done
