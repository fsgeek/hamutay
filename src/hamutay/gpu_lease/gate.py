from __future__ import annotations
import hashlib, urllib.error, urllib.request, uuid
from hamutay.events import _GateToken
from . import ledger
from .actions import (Ctx, REGISTRY, EnsureStopped, Expire, NotFree, QuarantineEnter, ServerStart,
                      is_free, quarantine_if_indeterminate, resolve_dangling, resolve_tombstones, run)
from .state import MalformedState, list_tombstones, locked, read_lease, read_quarantine
from .systemd import SystemdUnavailable

CLOSING_ACTIONS = ("release", "expire", "release_force")
PROBE_TIMEOUT = 2.0


def _default_fetch(url, timeout):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _ok_outcomes(rows, *actions):
    return [r for r in rows if r.get("phase") == "outcome" and r.get("outcome") == "ok"
            and r.get("action") in actions]


class LeaseGate:
    def __init__(self, store, ctx: Ctx, *, base_url=None, fetch=None,
                 session=None, discover=None, explicit_limit=None):
        self.store, self.ctx = store, ctx
        self._token = _GateToken()
        # ctx.now() is used for the actions claim() runs (resolve_dangling, Expire,
        # is_free); `now` passed to claim() is used for the lease read and the store
        # claim it makes directly. Task 8 wires Ctx.now to the loop's clock, so the
        # two coincide in practice.
        self._base_url = base_url
        self._fetch = fetch or _default_fetch
        self._ready_invocation = self._latest_ready_invocation()
        # The context ceiling is a property of the *server invocation*, not of
        # the door: a loan restarts llama-server, possibly with a different -c.
        # The session is where a newly discovered ceiling lands; explicit_limit,
        # when the human gave one, is never overwritten.
        self._session = session
        self._discover = discover
        self._explicit_limit = explicit_limit
        self._current_invocation = None

    def _context_validated(self) -> bool:
        """Has a ceiling been established for the invocation now running?

        True when the human pinned one with --context-limit (nothing may
        overwrite it), or when there is no session to teach. Otherwise the log
        must already carry a substrate_observation naming *this* InvocationID:
        a ceiling learned about the previous invocation says nothing about the
        server that came back from the loan.
        """
        if self._explicit_limit is not None or self._session is None:
            return True
        log_path = getattr(self._session, "_log_path", None)
        if not log_path:
            return False
        # Imported here, not at module scope: heartbeat.main() imports this
        # module, so a module-level import back into it would close the cycle.
        from hamutay.heartbeat import latest_context_observation

        launch = getattr(self._session, "_launch_config", None) or {}
        _, seen = latest_context_observation(
            log_path,
            model=launch.get("model"),
            provider=launch.get("provider"),
            base_url=launch.get("base_url"),
        )
        return seen == self._current_invocation

    def _quarantine_malformed_lease(self, view):
        """A lease file that will not parse is exactly the state nobody can act on.

        The spec fences it rather than merely reporting it blocked: a blocked
        caller retries forever against bytes that will never become a lease,
        and meanwhile nothing tells the operator the resource needs a hand.
        The digest is an occurrence identity for the unreadable bytes."""
        return self._enter_quarantine(
            "malformed_lease", hashlib.sha256(view.raw or b"").hexdigest()[:16])

    def _free_info(self, now):
        free, why = is_free(self.ctx)
        if free:
            return None
        view = read_lease(self.ctx.paths, now)
        if why == "lease_malformed":
            # Fence first, then report the fence -- not the malformation -- as
            # the reason the caller is blocked, so claim() and observe() agree.
            info = self._quarantine_malformed_lease(view)
            return {"kind": "quarantine", "lease": None, "raw": "", **info}
        # `lease` is None for reasons that aren't about the lease file itself
        # (quarantine, quarantine_unreadable, tombstone).
        return {"kind": why, "lease": view.data, "raw": (view.raw or b"")[:200].decode("utf-8", "replace")}

    def claim(self, now):
        with locked(self.ctx.paths):
            resolve_dangling(self.ctx, REGISTRY)
            if read_lease(self.ctx.paths, now).kind == "expired":
                # resolve_dangling just above already reconciled any dangling
                # intent, so this pass needs no registry. Between that read and
                # here the lease may no longer be expired (a dangling release
                # reconciled it, or the clock moved on) — Expire().intent()
                # re-reads and raises NotFree in that case, which the following
                # is_free() evaluates correctly.
                try:
                    run(self.ctx, Expire())
                except NotFree:
                    pass
            info = self._free_info(now)
            if info and info["kind"] == "tombstone":
                resolve_tombstones(self.ctx)
                info = self._free_info(now)
            if info:
                return "blocked", info
            claim = self.store.claim_next_pending(now=now, lease_token=self._token)
        return ("claimed", claim) if claim is not None else ("none", None)

    # --- ledger-derived memory --------------------------------------------

    def _latest_ready_invocation(self):
        """The invocation the ledger last observed ready, or None.

        A readiness edge is per InvocationID: the latest observation row for
        each invocation decides, and only an invocation whose latest row is
        `server_ready` is remembered as ready."""
        latest = {}
        for r in ledger.rows(self.ctx.paths):
            if r.get("phase") == "observation" and r.get("action") in ("server_ready", "server_unready"):
                latest[r.get("invocation_id")] = r.get("action")
        ready = [inv for inv, action in latest.items() if action == "server_ready"]
        return ready[-1] if ready else None

    def note_ready(self, invocation_id, ready):
        """Append an observation row only on an edge for this invocation."""
        if ready and self._ready_invocation == invocation_id:
            return None
        if not ready and self._ready_invocation != invocation_id:
            return None
        row = ledger.append(self.ctx.paths, {
            "action_id": str(uuid.uuid4()), "phase": "observation",
            "action": "server_ready" if ready else "server_unready",
            "invocation_id": invocation_id, "by": self.ctx.by, "at": self.ctx.now().isoformat()})
        self._ready_invocation = invocation_id if ready else None
        return row

    # --- the four observations ---------------------------------------------

    def _quarantine_bytes(self):
        try:
            return self.ctx.paths.quarantine.read_bytes()
        except OSError:
            return b""

    def _quarantine_info(self):
        q = read_quarantine(self.ctx.paths)
        return None if q is None else {"episode_id": q["quarantine_id"], "reason": q.get("reason")}

    def _enter_quarantine(self, reason, digest):
        run(self.ctx, QuarantineEnter(reason, digest), REGISTRY)
        q = read_quarantine(self.ctx.paths)
        return {"episode_id": q["quarantine_id"], "reason": q.get("reason")}

    def observe(self, now):
        """LEASE_LIVE | QUARANTINED | FREE-not-ready | FREE-ready.

        Everything that touches state runs under 4090.lock; the readiness probe
        is a network call and deliberately runs outside it."""
        with locked(self.ctx.paths):
            resolve_dangling(self.ctx, REGISTRY)
            try:
                info = self._quarantine_info()
            except MalformedState:
                # The digest names what was actually on disk, not how reading it
                # failed: an occurrence identity for the unreadable bytes.
                info = self._enter_quarantine(
                    "unreadable", hashlib.sha256(self._quarantine_bytes()).hexdigest()[:16])
            if info is not None:
                return "quarantined", info
            view = read_lease(self.ctx.paths, now)
            if view.kind == "malformed":
                return "quarantined", self._quarantine_malformed_lease(view)
            if view.kind == "expired":
                # resolve_dangling above already reconciled any dangling intent,
                # so this pass needs no registry; the lease may have stopped
                # being expired in between, which Expire().intent() reports as
                # NotFree — re-read and carry on.
                try:
                    run(self.ctx, Expire())
                except NotFree:
                    pass
                view = read_lease(self.ctx.paths, now)
            if view.kind == "live":
                d = view.data
                return "lease_live", {"episode_id": d["lease_id"], "holder": d["holder"],
                                      "purpose": d["purpose"], "since": d["since"],
                                      "expires_at": d["expires_at"],
                                      "expected_until": d.get("expected_until")}
            if list_tombstones(self.ctx.paths):
                # A scope that cannot be killed quarantines the resource; re-read.
                resolve_tombstones(self.ctx)
                try:
                    info = self._quarantine_info()
                except MalformedState:
                    info = None
                if info is not None:
                    return "quarantined", info
            # These two show() calls sit outside any action, so a systemd that
            # is momentarily unavailable would raise straight out of the poll
            # loop and take the heartbeat down — a restart storm against a
            # substrate that is merely busy. Report not-ready instead: the door
            # warms, transitions nothing, and retries on the next poll.
            try:
                server = self.ctx.systemd.show(self.ctx.server_unit)
                if server.get("active_state") not in ("active", "activating"):
                    out = run(self.ctx, ServerStart(), REGISTRY)
                    quarantine_if_indeterminate(self.ctx, out)
                    server = self.ctx.systemd.show(self.ctx.server_unit)
            except SystemdUnavailable as e:
                return "free_not_ready", {"error": str(e), "context": "systemd_unavailable"}
        invocation_id = server.get("invocation_id", "")
        self._current_invocation = invocation_id
        ready = bool(self._base_url) and self.probe()
        self.note_ready(invocation_id, ready)
        if ready:
            if not self._context_validated():
                # The server answers, but nobody has asked *this* invocation
                # what it will hold. Ask now; a server that will not say stays
                # unready rather than letting a wake run against a guess.
                from hamutay.taste_open import discover_llama_server_context

                found = (self._discover or discover_llama_server_context)(self._base_url)
                if not found or int(found) <= 0:
                    return "free_not_ready", {"invocation_id": invocation_id,
                                              "ready": True, "context": "undiscovered"}
                self._session.apply_context_limit(
                    int(found), "discovered", invocation_id)
            if self._context_validated():
                return "free_ready", {"invocation_id": invocation_id}
        return "free_not_ready", {"invocation_id": invocation_id, "ready": ready}

    def probe(self) -> bool:
        return self._fetch(f"{self._base_url}/models", PROBE_TIMEOUT) == 200

    def ensure_stopped(self, episode_id):
        """Stop the server for this episode, once. The ledger is the memory:
        an ok ensure_stopped outcome for this episode_id suppresses repeats."""
        with locked(self.ctx.paths):
            rows = ledger.rows(self.ctx.paths)
            if any(r.get("episode_id") == episode_id for r in _ok_outcomes(rows, "ensure_stopped")):
                return None
            out = run(self.ctx, EnsureStopped(episode_id), REGISTRY)
            quarantine_if_indeterminate(self.ctx, out)
            return out

    # --- boot reconciliation ------------------------------------------------

    def reconcile_on_boot(self, now):
        """Close substrate episodes that ended while the heartbeat was down and
        reconstruct rests the store never saw. Runs before _hydrate_last_transition,
        so the records it appends are what hydration reads."""
        # Imported here, not at module scope: heartbeat.main() imports this
        # module, so a module-level import back into it would close the cycle.
        from hamutay.heartbeat import SUBSTRATE_REST_REASONS, append_heartbeat_status
        with locked(self.ctx.paths):
            resolve_dangling(self.ctx, REGISTRY)
            statuses = [r for r in self.store.read_records() if r.get("record_type") == "heartbeat_status"]
            view = read_lease(self.ctx.paths, now)
            live_id = view.data["lease_id"] if view.kind == "live" else None
            try:
                q = read_quarantine(self.ctx.paths)
            except MalformedState:
                q = None
            q_id = q["quarantine_id"] if q else None
            rows = ledger.rows(self.ctx.paths)

            # 1. close the substrate episode that ended while we were down.
            open_ep = None
            for r in statuses:
                detail = r.get("detail") or {}
                if r.get("status") == "resting" and r.get("reason") in SUBSTRATE_REST_REASONS:
                    open_ep = detail.get("episode_id")
                elif not (r.get("status") == "waking" and r.get("reason") == "boot"):
                    # waking/boot leaves the episode open (a restart mid-lease);
                    # anything else is the episode already closed.
                    open_ep = None
            if open_ep is not None and open_ep not in (live_id, q_id):
                closed_at = next((r["at"] for r in reversed(_ok_outcomes(rows, *CLOSING_ACTIONS))
                                  if r.get("episode_id") == open_ep), None)
                append_heartbeat_status(
                    self.store, status="waking", reason="substrate_returning",
                    detail={"episode_id": open_ep,
                            "closed_at_source": "ledger" if closed_at else "boot"},
                    created_at=closed_at or now.isoformat())

            # 2. reconstruct rests for force_stops the store never recorded (a
            # crash between force-stop's own record and its outcome).
            rested = {(r.get("detail") or {}).get("episode_id")
                      for r in statuses if r.get("status") == "resting"}
            # force_stop only, never ensure_stopped: cmd_force_stop runs the
            # ForceStop action, which ledgers action: "force_stop", so an
            # ensure_stopped row from a force-stop cannot exist.
            for r in _ok_outcomes(rows, "force_stop"):
                episode_id = r.get("episode_id")
                if episode_id in rested:
                    continue
                rested.add(episode_id)
                append_heartbeat_status(
                    self.store, status="resting", reason="substrate_lent",
                    detail={"episode_id": episode_id, "source": "reconstructed_from_ledger",
                            "continuation": False},
                    created_at=r["at"])
                if episode_id != live_id:
                    append_heartbeat_status(
                        self.store, status="waking", reason="substrate_returning",
                        detail={"episode_id": episode_id, "closed_at_source": "ledger"},
                        created_at=r["at"])
