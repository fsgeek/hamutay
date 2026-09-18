"""The bounded repair pass: one plaza-lock scope per unit (spec §6)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from hamutay.assembly.binding import AssemblyBinding
from hamutay.assembly.ledger import Ledger, LedgerMalformed, LedgerUnavailable, iso
from hamutay.events import StoreUnavailable

from . import store as _store
from .event import inbound_event_for
from .ids import PLAZA_LOCK_WINDOW_S, STORE_LOCK_WINDOW_S
from .records import append_validated, build_delivery, reduce, validate_plaza

PASS_UNITS = 4
PASS_BUDGET_S = 6.0
UNIT_NEEDS_S = PLAZA_LOCK_WINDOW_S + STORE_LOCK_WINDOW_S


@dataclass(frozen=True)
class PlazaMemo:
    signature: tuple
    cursor: int          # seq after which the next pass resumes
    undelivered: int     # what the last pass left


def run_plaza_pass(binding: AssemblyBinding, *, now: datetime, memo: PlazaMemo | None = None,
                   land=_store.land, clock=time.monotonic) -> tuple[dict, PlazaMemo]:
    cfg = binding.members
    if cfg.plaza is None:
        return {"skipped": True, "units": 0, "landed": [], "unreadable": []}, (memo or PlazaMemo((0, 0.0), 0, 0))
    ledger = Ledger(cfg.plaza)
    sig = ledger.signature()
    if memo is not None and memo.signature == sig and memo.undelivered == 0:
        return {"skipped": True, "units": 0, "landed": [], "unreadable": []}, memo
    start = clock()
    cursor = memo.cursor if memo is not None else 0
    examined: set[str] = set()
    landed: list[str] = []
    unreadable: list[str] = []
    units = 0
    remaining_after = 0
    while units < PASS_UNITS and (PASS_BUDGET_S - (clock() - start)) >= UNIT_NEEDS_S:
        try:
            with ledger.try_locked(PLAZA_LOCK_WINDOW_S):
                records = ledger.read_unlocked()
                lines = list(ledger.line_numbers)   # append_unlocked rebuilds the ledger's own
                validate_plaza(records, lines)
                view = reduce(records)
                pending = view.undelivered()
                remaining_after = len(pending)
                if not pending:
                    break
                after = [m for m in pending if m["seq"] > cursor] or pending      # wrap once
                target = after[0]
                if target["message_id"] in examined:
                    break                                                         # one full circuit
                examined.add(target["message_id"])
                cursor = target["seq"]
                units += 1
                truth = view.delivery_truth(target["message_id"])
                try:
                    land(Path(target["delivery"]["events_path"]), inbound_event_for(target), timeout_s=STORE_LOCK_WINDOW_S)
                    append_validated(ledger, records, lines,
                                     build_delivery(message=target, state="landed", landed_at=iso(now), detail=None))
                    landed.append(target["message_id"]); remaining_after -= 1
                except StoreUnavailable as e:   # store.land normalises OSError/LeaseGateRequired (M6)
                    err = str(e)
                    if not (truth["state"] == "store_unreadable" and (truth.get("detail") or {}).get("error") == err):
                        append_validated(ledger, records, lines,
                                         build_delivery(message=target, state="store_unreadable",
                                                        landed_at=None, detail={"error": err}))
                    unreadable.append(target["message_id"])
        except LedgerUnavailable:
            # The cursor units already completed in this pass advanced, and the
            # signature read this pass -- not the caller's original memo. Returning
            # that would re-examine messages this pass already landed (harmless, but
            # it re-pays a lock acquisition and a full read+validate each) and could
            # retry a stuck head indefinitely at the front. The spec's fairness
            # paragraph resets the cursor on a process restart, not on a lock timeout.
            return {"skipped": "lock", "units": units, "landed": landed, "unreadable": unreadable}, \
                PlazaMemo(sig, cursor, max(remaining_after, 1))
        except LedgerMalformed as e:
            return {"skipped": False, "error": str(e), "units": units, "landed": landed, "unreadable": unreadable}, \
                PlazaMemo(sig, cursor, 1)
    return {"skipped": False, "units": units, "landed": landed, "unreadable": unreadable}, \
        PlazaMemo(ledger.signature(), cursor, remaining_after)
