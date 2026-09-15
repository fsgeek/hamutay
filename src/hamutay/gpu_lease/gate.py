from __future__ import annotations
from hamutay.events import _GateToken
from .actions import Ctx, REGISTRY, Expire, is_free, resolve_dangling, resolve_tombstones, run
from .state import locked, read_lease, read_quarantine, MalformedState


class LeaseGate:
    def __init__(self, store, ctx: Ctx):
        self.store, self.ctx = store, ctx
        self._token = _GateToken()

    def _free_info(self):
        free, why = is_free(self.ctx)
        if free:
            return None
        view = read_lease(self.ctx.paths, self.ctx.now())
        return {"kind": why, "lease": view.data, "raw": (view.raw or b"")[:200].decode("utf-8", "replace")}

    def claim(self, now):
        with locked(self.ctx.paths):
            resolve_dangling(self.ctx, REGISTRY)
            if read_lease(self.ctx.paths, self.ctx.now()).kind == "expired":
                run(self.ctx, Expire(), REGISTRY)
            info = self._free_info()
            if info and info["kind"] == "tombstone":
                resolve_tombstones(self.ctx)
                info = self._free_info()
            if info:
                return "blocked", info
            claim = self.store.claim_next_pending(now=now, lease_token=self._token)
        return ("claimed", claim) if claim is not None else ("none", None)
