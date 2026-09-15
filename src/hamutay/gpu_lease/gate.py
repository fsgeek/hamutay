from __future__ import annotations
from hamutay.events import _GateToken
from .actions import Ctx, REGISTRY, Expire, NotFree, is_free, resolve_dangling, resolve_tombstones, run
from .state import locked, read_lease


class LeaseGate:
    def __init__(self, store, ctx: Ctx):
        self.store, self.ctx = store, ctx
        self._token = _GateToken()
        # ctx.now() is used for the actions claim() runs (resolve_dangling, Expire,
        # is_free); `now` passed to claim() is used for the lease read and the store
        # claim it makes directly. Task 8 wires Ctx.now to the loop's clock, so the
        # two coincide in practice.

    def _free_info(self, now):
        free, why = is_free(self.ctx)
        if free:
            return None
        view = read_lease(self.ctx.paths, now)
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
