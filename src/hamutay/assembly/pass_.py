"""One pass: outbox, closing, activation, outbox (spec §7)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hamutay.events import EventStore

from .binding import AssemblyBinding
from .close import derive_activations, try_close
from .ledger import LedgerMalformed, LedgerUnavailable, parse_instant
from .outbox import run_outbox
from .records import reduce


# The pass holds the ledger lock across every door's store read (eligibility must be
# judged against a store snapshot no older than the ledger snapshot), so under store
# contention it can hold it for many seconds. A heartbeat that cannot take it inside
# this window emits the error and tries again next poll rather than blocking (I2).
LEDGER_LOCK_WINDOW_S = 10.0


@dataclass(frozen=True)
class PassMemo:
    signature: tuple
    quiescent_until: datetime | None


def run_pass(binding: AssemblyBinding, *, now: datetime, actor: str, memo: PassMemo | None = None,
             open_store=EventStore) -> tuple[dict, PassMemo]:
    ledger = binding.ledger
    sig = ledger.signature()
    if memo is not None and memo.signature == sig and memo.quiescent_until is not None and now < memo.quiescent_until:
        return {"skipped": True, "outbox": 0, "closed": [], "activated": []}, memo
    try:
        with ledger.try_locked(LEDGER_LOCK_WINDOW_S):
            view = reduce(ledger.read_unlocked())
            n = len(run_outbox(ledger, view, now=now, open_store=open_store))
            view = reduce(ledger.read_unlocked())
            closed = []
            # frozen before the loop: a child created by an extension in this pass has
            # closes_at > now, so it can never be due in the same pass
            for q in list(view.open_questions()):
                c = try_close(ledger, view, q, now=now, actor=actor, open_store=open_store)
                if c is not None:
                    closed.append(c["question_id"])
                    view = reduce(ledger.read_unlocked())
            activated = [r["procedure_id"] for r in derive_activations(ledger, view)]
            view = reduce(ledger.read_unlocked())
            n += len(run_outbox(ledger, view, now=now, open_store=open_store))
            view = reduce(ledger.read_unlocked())
            quiescent = view.quiescent(now)
            new_memo = PassMemo(ledger.signature(), view.next_deadline() if quiescent else None)
            if quiescent and new_memo.quiescent_until is None:
                new_memo = PassMemo(new_memo.signature, datetime.max.replace(tzinfo=now.tzinfo))
        return {"skipped": False, "outbox": n, "closed": closed, "activated": activated}, new_memo
    except (LedgerMalformed, LedgerUnavailable) as e:
        return {"skipped": False, "error": str(e), "outbox": 0, "closed": [], "activated": []}, \
            (memo or PassMemo(sig, None))
