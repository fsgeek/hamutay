"""One reader for the CLI's `read` and the MCP's `plaza_read` (spec §11 r6)."""
from __future__ import annotations

from hamutay.assembly.ledger import Ledger

from .ids import PLAZA_LOCK_WINDOW_S
from .records import reduce, validate_plaza


def read_rows(cfg, *, since_seq: int | None = None, through_seq: int | None = None,
              posts_only: bool = False, door: str | None = None, for_door: str | None = None) -> list[dict]:
    """Message rows in seq order, each with `truth`; both bounds inclusive; empty is empty."""
    return read_snapshot(cfg, since_seq=since_seq, through_seq=through_seq, posts_only=posts_only,
                         door=door, for_door=for_door)[0]


def read_snapshot(cfg, *, since_seq: int | None = None, through_seq: int | None = None,
                  posts_only: bool = False, door: str | None = None,
                  for_door: str | None = None) -> tuple[list[dict], list[dict]]:
    """(rows, every message) from ONE locked snapshot -- the rows read_rows returns, plus the full
    message list the read cursor needs to merge ranges and compute coverage (cursor spec r3).

    No page or byte ceiling is promised (declared): a caller bounds its own read
    with `through_seq`. Raises LedgerUnavailable / LedgerMalformed as the CLI does.
    """
    if not cfg.plaza.exists():
        return [], []
    led = Ledger(cfg.plaza)
    with led.try_locked(PLAZA_LOCK_WINDOW_S):
        records = led.read_unlocked()
        validate_plaza(records, led.line_numbers)
    v = reduce(records)
    out: list[dict] = []
    for m in v.messages:
        if since_seq is not None and m["seq"] < since_seq:
            continue
        if through_seq is not None and m["seq"] > through_seq:
            continue
        if posts_only and m["to"] != "plaza":
            continue
        if door and m["from"] != f"door:{door}" and m["to"] != f"door:{door}":
            continue
        if for_door and (m["from"] == f"door:{for_door}" or m["to"] == f"door:{for_door}"):
            continue
        row = dict(m)
        row["truth"] = v.delivery_truth(m["message_id"]) if m["delivery"] else {"state": "post"}
        out.append(row)
    return out, list(v.messages)
