"""The plaza note: what appeared since this door's last wake began (spec §5)."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from hamutay.assembly.binding import MembersConfig
from hamutay.assembly.ledger import Ledger, LedgerMalformed, LedgerUnavailable, parse_instant
from hamutay.events import latest_completed_wake

from .ids import PLAZA_LOCK_WINDOW_S
from .records import reduce, validate_plaza


def note_lower_bound(store_records: list[dict]) -> datetime | None:
    done = latest_completed_wake(store_records)
    if done is None:
        return None
    for r in store_records:
        if r.get("record_type") == "event_status" and r.get("status") == "running" \
                and r.get("event_id") == done.get("event_id") and r.get("run_id") == done.get("run_id"):
            try:
                return parse_instant(r["started_at"])
            except (KeyError, ValueError, TypeError):
                return None
    return None


def _seq_list(seqs: list[int]) -> str:
    if len(seqs) <= 12:
        return ", ".join(str(s) for s in seqs)
    return ", ".join(str(s) for s in seqs[:3]) + ", …, " + ", ".join(str(s) for s in seqs[-3:])


def plaza_note(cfg: MembersConfig, door: str, store_records: list[dict],
               on_error: Callable[[str], None] = lambda s: None) -> list[str]:
    if cfg.plaza is None or not cfg.plaza.exists():
        return []
    ledger = Ledger(cfg.plaza)
    try:
        with ledger.try_locked(PLAZA_LOCK_WINDOW_S):
            records = ledger.read_unlocked()
            validate_plaza(records, ledger.line_numbers)
    except LedgerUnavailable as e:
        on_error(f"plaza note: lock not acquired ({e}); no note this wake"); return []
    except LedgerMalformed as e:
        on_error(f"plaza note: {e}; no note this wake"); return []
    seen = reduce(records).visible_since(note_lower_bound(store_records), door)
    if not seen:
        return []
    seqs = [m["seq"] for m in seen]
    posts = sum(1 for m in seen if m["to"] == "plaza")
    latest = seen[-1]
    return [(f"plaza: {len(seen)} message(s) since your last wake began, at seq {_seq_list(seqs)} "
             f"({posts} posts, {len(seen) - posts} between other doors; latest from {latest['from']} at "
             f"{latest['sent_at']}). Each is one line of community/plaza/plaza.jsonl (seq equals line number); "
             f"lines {seqs[0]}..{seqs[-1]} contain them among delivery records and your own mail; "
             f"`deploy/ayllu-plaza read --since-seq {seqs[0]} --through-seq {seqs[-1]} --for {door}` prints "
             f"exactly them, however much is appended later.")]


def note_producer(cfg: MembersConfig, door: str, store, on_error: Callable[[str], None]):
    def produce(event: dict) -> list[str]:
        try:
            return plaza_note(cfg, door, store.read_records(), on_error=on_error)
        except Exception as e:  # the note must never take a wake down
            on_error(f"plaza note: {type(e).__name__}: {e}; no note this wake"); return []
    return produce
