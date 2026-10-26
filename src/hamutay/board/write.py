"""The board's one write path and one reader, for the CLI and the door tools (contract §3)."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from hamutay.assembly.ledger import Ledger, iso
from hamutay.plaza.ids import guest_label, is_guest

from .ids import BOARD_LOCK_WINDOW_S, board_path, canonical_label, norm, utc_day
from .records import (HELP_WANTED_MAX, KINDS, NOTE_MAX, OPEN_PER_POSTER, REASON_MAX, RECORD_OF_HELP_MAX,
                      RECORDS_PER_WRITER_PER_DAY, STATUSES, TITLE_MAX, WHAT_MAX, WHY_MAX, View,
                      append_validated, normalize_tags, reduce, validate_board)


class BoardRefused(RuntimeError):
    pass


def read_snapshot(project_root, *, timeout_s: float = BOARD_LOCK_WINDOW_S) -> View:
    """One locked, validated snapshot. Raises LedgerUnavailable / LedgerMalformed (fail closed)."""
    path = board_path(project_root)
    if not path.exists():
        return reduce([])
    led = Ledger(path)
    with led.try_locked(timeout_s):
        records = led.read_unlocked()
        validate_board(records, led.line_numbers)
    return reduce(records)


def _writer(by: str, admitted_guests) -> str:
    try:
        by = canonical_label(by)
    except ValueError as e:
        raise BoardRefused(str(e))
    if is_guest(by) and guest_label(by) not in (admitted_guests or ()):
        raise BoardRefused(f"guest {guest_label(by)!r} is not admitted (members.json guests)")
    return by


def _str(v, what: str, hi: int, *, required: bool) -> str:
    if v is None:
        v = ""
    if not isinstance(v, str):
        raise BoardRefused(f"{what} must be a string")
    if required and not v.strip():
        raise BoardRefused(f"{what} is required and may not be blank")
    if len(v) > hi:
        raise BoardRefused(f"{what} is {len(v)} characters; at most {hi}")
    return v


def _append(project_root, now: datetime, by: str, build) -> dict:
    """Lock, read, validate, check the writer's day cap, let `build` decide, append validated."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-bearing")
    path = board_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    led = Ledger(path)
    with led.try_locked(BOARD_LOCK_WINDOW_S):
        records = led.read_unlocked()
        lines = list(led.line_numbers)
        validate_board(records, lines)
        view = reduce(records)
        out = build(view)
        if "duplicate_of_seq" in out:
            return out
        record = out.pop("_record")
        if view.written_on(by, utc_day(now)) >= RECORDS_PER_WRITER_PER_DAY:
            raise BoardRefused(f"{by} has written {RECORDS_PER_WRITER_PER_DAY} board records today "
                               f"({utc_day(now)} UTC), the daily cap; it lifts at midnight UTC")
        written = append_validated(led, records, lines, {**record, "created_at": iso(now)})
        return {**out, "seq": written["seq"]}


def post_opening(project_root, *, by: str, title, what, kind, why="", help_wanted="", tags=None,
                 owner=None, record_of_help="", now: datetime, admitted_guests=None) -> dict:
    by = _writer(by, admitted_guests)
    title = _str(title, "title", 10**6, required=True).strip()
    if len(title) > TITLE_MAX or "\n" in title:
        raise BoardRefused(f"title must be one line of at most {TITLE_MAX} characters")
    what = _str(what, "what", WHAT_MAX, required=True)
    why = _str(why, "why", WHY_MAX, required=False)
    help_wanted = _str(help_wanted, "help_wanted", HELP_WANTED_MAX, required=False)
    record_of_help = _str(record_of_help, "record_of_help", RECORD_OF_HELP_MAX, required=False)
    if not isinstance(kind, str) or norm(kind) not in KINDS:
        raise BoardRefused(f"kind must be one of {', '.join(KINDS)}")
    kind = norm(kind)
    try:
        tags = normalize_tags(tags)
        owner = canonical_label(owner) if owner not in (None, "") else by
    except ValueError as e:
        raise BoardRefused(str(e))

    def build(view: View) -> dict:
        for e in view.entries.values():
            o = e.opening
            if (o["posted_by"] == by and o["title"] == title and o["what"] == what and e.status != "closed"):
                return {"posted": True, "opportunity_id": o["opportunity_id"], "seq": o["seq"],
                        "duplicate_of_seq": o["seq"], "status": e.status}
        if view.open_by(by) >= OPEN_PER_POSTER:
            raise BoardRefused(f"{by} already has {OPEN_PER_POSTER} openings with status open; "
                               "mark one taken or closed first")
        oid = str(uuid.uuid4())
        rec = {"record_type": "opening", "opportunity_id": oid, "posted_by": by, "posted_at": iso(now),
               "title": title, "what": what, "why": why, "help_wanted": help_wanted, "kind": kind,
               "tags": tags, "owner": owner, "record_of_help": record_of_help}
        return {"posted": True, "opportunity_id": oid, "owner": owner, "tags": tags, "_record": rec}

    return _append(project_root, now, by, build)


def _owned(view: View, oid, by: str):
    e = view.entries.get(str(oid))
    if e is None:
        raise BoardRefused(f"no opening with opportunity_id {oid!r}")
    if e.opening["owner"] != by:
        raise BoardRefused(f"only the owner ({e.opening['owner']}) may write notes or status for this entry")
    if e.status == "closed":
        raise BoardRefused("this entry is closed; closed is final")
    return e


def add_note(project_root, *, by: str, opportunity_id, text, now: datetime, admitted_guests=None) -> dict:
    by = _writer(by, admitted_guests)
    text = _str(text, "text", NOTE_MAX, required=True)

    def build(view: View) -> dict:
        e = _owned(view, opportunity_id, by)
        for n in e.notes:
            if n["text"] == text:
                return {"noted": True, "opportunity_id": e.opportunity_id, "seq": n["seq"],
                        "duplicate_of_seq": n["seq"]}
        return {"noted": True, "opportunity_id": e.opportunity_id,
                "_record": {"record_type": "note", "opportunity_id": e.opportunity_id, "by": by, "text": text}}

    return _append(project_root, now, by, build)


def set_status(project_root, *, by: str, opportunity_id, status, reason="", now: datetime,
               admitted_guests=None) -> dict:
    by = _writer(by, admitted_guests)
    if status not in STATUSES:
        raise BoardRefused(f"status must be one of {', '.join(STATUSES)}")
    reason = _str(reason, "reason", REASON_MAX, required=False)

    def build(view: View) -> dict:
        e = _owned(view, opportunity_id, by)
        cur = e.status_record
        if cur is not None and cur["status"] == status and cur["reason"] == reason:
            return {"status": status, "opportunity_id": e.opportunity_id, "seq": cur["seq"],
                    "duplicate_of_seq": cur["seq"]}
        if status == "open" and e.status != "open" and view.open_by(e.opening["posted_by"]) >= OPEN_PER_POSTER:
            raise BoardRefused(f"{e.opening['posted_by']} already has {OPEN_PER_POSTER} openings with status open")
        return {"status": status, "opportunity_id": e.opportunity_id,
                "_record": {"record_type": "status", "opportunity_id": e.opportunity_id, "by": by,
                            "status": status, "reason": reason}}

    return _append(project_root, now, by, build)


READ_LIMIT = 50


def read_entries(project_root, *, opportunity_id=None, include_closed: bool = False,
                 since_seq: int | None = None, limit: int = READ_LIMIT) -> dict:
    """Entries in posting order (current status, every note), newest `limit` if more; or one entry by id."""
    view = read_snapshot(project_root)
    if opportunity_id is not None:
        e = view.entries.get(str(opportunity_id))
        return {"board_seq": view.last_seq, "entries": [e.public()] if e else [],
                **({} if e else {"error": f"no opening with opportunity_id {opportunity_id!r}"})}
    rows = [e for e in view.entries.values()
            if (include_closed or e.status != "closed")
            and (since_seq is None or max([e.opening["seq"]] + [r["seq"] for r in e.notes + e.statuses]) >= since_seq)]
    omitted = max(0, len(rows) - limit)
    rows = rows[omitted:]
    return {"board_seq": view.last_seq, "entries": [e.public() for e in rows], "omitted_older": omitted,
            "path": str(Path(board_path(project_root)))}
