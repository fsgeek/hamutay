"""Board records, the strict validator, and the reduced view (board v0 contract §3).

The plaza's writer discipline: every reader validates the whole file before it
reduces it (fail closed), and every writer validates the records it read plus
the one it is about to write, at the line it will occupy, before it appends --
so a writer can never produce a line that would disable every strict reader.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from hamutay.assembly.ledger import LedgerMalformed, iso, parse_instant

from .ids import is_label, norm

KINDS = ("review", "design", "build", "analysis", "writing", "testimony", "other")
STATUSES = ("open", "taken", "closed")
TAG_RE = re.compile(r"^[a-z0-9-]{1,32}$")

TITLE_MAX = 120
WHAT_MAX = 2000
WHY_MAX = 1000
HELP_WANTED_MAX = 1000
RECORD_OF_HELP_MAX = 500
TAGS_MAX = 8
NOTE_MAX = 1000
REASON_MAX = 500
OPEN_PER_POSTER = 5
RECORDS_PER_WRITER_PER_DAY = 20

OPENING_FIELDS = {"record_type", "seq", "created_at", "opportunity_id", "posted_by", "posted_at", "title",
                  "what", "why", "help_wanted", "kind", "tags", "owner", "record_of_help"}
NOTE_FIELDS = {"record_type", "seq", "created_at", "opportunity_id", "by", "text"}
STATUS_FIELDS = {"record_type", "seq", "created_at", "opportunity_id", "by", "status", "reason"}


def normalize_tags(raw) -> list[str]:
    """NFKC, case-fold, trim; each must then match [a-z0-9-]{1,32}; blanks refused; duplicates removed."""
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("tags must be a list of strings")
    out: list[str] = []
    for t in raw:
        if not isinstance(t, str):
            raise ValueError(f"tag {t!r} is not a string")
        n = norm(t)
        if not n:
            raise ValueError("a blank tag is refused, not ignored")
        if not TAG_RE.match(n):
            raise ValueError(f"tag {t!r} normalizes to {n!r}, which is not [a-z0-9-]{{1,32}}")
        if n not in out:
            out.append(n)
    if len(out) > TAGS_MAX:
        raise ValueError(f"at most {TAGS_MAX} tags")
    return out


def _bad(msg: str) -> LedgerMalformed:
    return LedgerMalformed(f"board: {msg}")


def _text(v, *, lo: int, hi: int, what: str, line: int) -> None:
    if not isinstance(v, str) or len(v) > hi or (lo > 0 and not v.strip()):
        raise _bad(f"line {line}: {what} must be a string of {lo}..{hi} characters"
                   + (" and not blank" if lo else ""))


def _instant(s, what: str) -> datetime:
    try:
        return parse_instant(s)
    except (ValueError, TypeError):
        raise _bad(f"{what} is not a timezone-bearing instant: {s!r}")


def validate_board(records: list[dict], line_numbers: list[int]) -> None:
    """Raise LedgerMalformed on anything the writers could not have produced."""
    if len(records) != len(line_numbers):
        raise _bad("line numbers do not match records")
    owners: dict[str, str] = {}
    closed: set[str] = set()
    for r, line in zip(records, line_numbers):
        if not isinstance(r, dict):
            raise _bad(f"line {line}: not an object")
        if r.get("seq") != line:
            raise _bad(f"line {line}: seq {r.get('seq')!r} is not the line number")
        _instant(r.get("created_at"), f"line {line} created_at")
        rt = r.get("record_type")
        if rt == "opening":
            if set(r) != OPENING_FIELDS:
                raise _bad(f"line {line}: opening fields are {sorted(set(r) ^ OPENING_FIELDS)} off")
            try:
                u = uuid.UUID(str(r["opportunity_id"]))
            except ValueError:
                raise _bad(f"line {line}: opportunity_id is not a UUID")
            if u.version != 4 or str(u) != r["opportunity_id"]:
                raise _bad(f"line {line}: opportunity_id is not a canonical version-4 UUID")
            if r["opportunity_id"] in owners:
                raise _bad(f"line {line}: second opening for {r['opportunity_id']}")
            if not is_label(r["posted_by"]) or not is_label(r["owner"]):
                raise _bad(f"line {line}: posted_by/owner is not a canonical label")
            _instant(r["posted_at"], f"line {line} posted_at")
            _text(r["title"], lo=1, hi=TITLE_MAX, what="title", line=line)
            if r["title"] != r["title"].strip() or "\n" in r["title"]:
                raise _bad(f"line {line}: title is not one trimmed line")
            _text(r["what"], lo=1, hi=WHAT_MAX, what="what", line=line)
            _text(r["why"], lo=0, hi=WHY_MAX, what="why", line=line)
            _text(r["help_wanted"], lo=0, hi=HELP_WANTED_MAX, what="help_wanted", line=line)
            _text(r["record_of_help"], lo=0, hi=RECORD_OF_HELP_MAX, what="record_of_help", line=line)
            if r["kind"] not in KINDS:
                raise _bad(f"line {line}: bad kind {r['kind']!r}")
            tags = r["tags"]
            try:
                ok = isinstance(tags, list) and normalize_tags(tags) == tags
            except ValueError:
                ok = False
            if not ok:
                raise _bad(f"line {line}: tags are not a normalized list")
            owners[r["opportunity_id"]] = r["owner"]
        elif rt in ("note", "status"):
            want = NOTE_FIELDS if rt == "note" else STATUS_FIELDS
            if set(r) != want:
                raise _bad(f"line {line}: {rt} fields are {sorted(set(r) ^ want)} off")
            oid = r["opportunity_id"]
            if oid not in owners:
                raise _bad(f"line {line}: {rt} for an unknown opportunity {oid!r}")
            if r["by"] != owners[oid]:
                raise _bad(f"line {line}: {rt} by {r['by']!r} but the owner is {owners[oid]!r}")
            if oid in closed:
                raise _bad(f"line {line}: {rt} after the opportunity was closed (closed is final)")
            if rt == "note":
                _text(r["text"], lo=1, hi=NOTE_MAX, what="text", line=line)
            else:
                if r["status"] not in STATUSES:
                    raise _bad(f"line {line}: bad status {r['status']!r}")
                _text(r["reason"], lo=0, hi=REASON_MAX, what="reason", line=line)
                if r["status"] == "closed":
                    closed.add(oid)
        else:
            raise _bad(f"line {line}: unknown record_type {rt!r}")


@dataclass
class Entry:
    opening: dict
    status: str = "open"
    status_record: dict | None = None
    notes: list[dict] = field(default_factory=list)
    statuses: list[dict] = field(default_factory=list)

    @property
    def opportunity_id(self) -> str:
        return self.opening["opportunity_id"]

    def public(self) -> dict:
        """What a reader is shown: the opening, its current status, and every note and status in order."""
        o = self.opening
        return {**{k: o[k] for k in ("opportunity_id", "seq", "title", "what", "why", "help_wanted", "kind",
                                      "tags", "owner", "posted_by", "posted_at", "record_of_help")},
                "status": self.status,
                "status_reason": (self.status_record or {}).get("reason"),
                "status_seq": (self.status_record or {}).get("seq"),
                "notes": [{"seq": n["seq"], "by": n["by"], "created_at": n["created_at"], "text": n["text"]}
                          for n in self.notes],
                "status_history": [{"seq": s["seq"], "status": s["status"], "reason": s["reason"],
                                    "created_at": s["created_at"]} for s in self.statuses]}


@dataclass
class View:
    records: list[dict] = field(default_factory=list)
    entries: dict[str, Entry] = field(default_factory=dict)   # by opportunity_id, posting order
    by_seq: dict[int, dict] = field(default_factory=dict)

    @property
    def last_seq(self) -> int:
        return self.records[-1]["seq"] if self.records else 0

    def written_on(self, label: str, day: str) -> int:
        n = 0
        for r in self.records:
            who = r["posted_by"] if r["record_type"] == "opening" else r["by"]
            if who == label and parse_instant(r["created_at"]).astimezone(timezone.utc).date().isoformat() == day:
                n += 1
        return n

    def open_by(self, poster: str) -> int:
        return sum(1 for e in self.entries.values() if e.opening["posted_by"] == poster and e.status == "open")

    def entry_as_of(self, oid: str, seq: int) -> Entry | None:
        """The entry as it stood after board seq `seq` (for showing it at a claim snapshot)."""
        e = self.entries.get(oid)
        if e is None or e.opening["seq"] > seq:
            return None
        out = Entry(e.opening)
        for s in e.statuses:
            if s["seq"] <= seq:
                out.statuses.append(s); out.status = s["status"]; out.status_record = s
        out.notes = [n for n in e.notes if n["seq"] <= seq]
        return out


def reduce(records: list[dict]) -> View:
    v = View(records=list(records))
    for r in records:
        v.by_seq[r["seq"]] = r
        rt = r["record_type"]
        if rt == "opening":
            v.entries[r["opportunity_id"]] = Entry(r)
        elif rt == "note":
            v.entries[r["opportunity_id"]].notes.append(r)
        elif rt == "status":
            e = v.entries[r["opportunity_id"]]
            e.statuses.append(r); e.status = r["status"]; e.status_record = r
    return v


def append_validated(ledger, records: list[dict], line_numbers: list[int], record: dict) -> dict:
    """Append under the caller's held lock, validator first (as hamutay.plaza.records.append_validated)."""
    next_line = (line_numbers[-1] if line_numbers else 0) + 1
    created_at = record.get("created_at") or iso(datetime.now(timezone.utc))
    candidate = {**record, "seq": next_line, "created_at": created_at}
    validate_board(records + [candidate], list(line_numbers) + [next_line])
    written = ledger.append_unlocked(candidate)
    records.append(written)
    line_numbers.append(written["seq"])
    return written
