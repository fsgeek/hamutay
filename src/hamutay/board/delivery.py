"""board_match events: what they are, when one may be claimed, how a batch is claimed and shown,
and what a failed batch leaves behind (contract §6-§9).

events.py calls into this module lazily (it imports nothing from here at
module load), so the board stays a leaf: without the gate file no board event
is ever claimable and nothing here writes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from hamutay.assembly.ledger import Ledger, LedgerMalformed, LedgerUnavailable, iso, parse_instant

from .filters import current_filter, passed_ids
from .ids import BOARD_LOCK_WINDOW_S, EVENT_TYPE_BOARD_MATCH, match_event_id, next_utc_midnight, utc_day
from .records import View, reduce, validate_board

MAX_ATTEMPTS = 3
DAILY_BOARD_WAKES = 2
FULL_ENTRIES = 10
TITLE_ENTRIES = 20
BOARD_TEXT_BUDGET = 12000
ENTRY_TEXT_CAP = 6000


def is_board_event(event: dict) -> bool:
    return event.get("event_type") == EVENT_TYPE_BOARD_MATCH


def build_match_event(*, door: str, gate: str, board_file: str, board_seq: int, record_type: str,
                      opportunity_id: str, generation: int, attempt: int, clause: dict | None,
                      now: datetime, compact: bool = False) -> dict:
    what = ("an opening that matched your board filter" if record_type == "opening"
            else f"a {record_type} on a board entry you were shown")
    ev = {
        "record_type": "event_status",
        "event_id": match_event_id(door, board_seq, generation, attempt),
        "event_type": EVENT_TYPE_BOARD_MATCH,
        "status": "pending",
        "created_at": iso(now),
        "origin": "board",
        "sender": "board",
        "purpose": f"Board seq {board_seq}: {what} (opportunity {opportunity_id}).",
        "defer_to_declared_quiet": True,
        "board": {"door": door, "board_seq": int(board_seq), "record_type": record_type,
                  "opportunity_id": opportunity_id, "generation": int(generation), "attempt": int(attempt),
                  "clause": clause, "gate": str(gate), "board_file": str(board_file)},
    }
    if compact:
        ev["detail"] = {"compact_context": True}
    return ev


def _parse(v) -> datetime | None:
    try:
        return parse_instant(v)
    except (ValueError, TypeError):
        return None


class ClaimContext:
    """What the store says about this door's board, computed once per read."""

    def __init__(self, records: list[dict], now: datetime):
        self.now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        self.generation, self.filter = current_filter(records)
        self.passed = passed_ids(records)
        day = utc_day(self.now)
        runs = set()
        latest: dict[str, dict] = {}
        for r in records:
            if r.get("record_type") != "event_status":
                continue
            if r.get("event_id"):
                latest[str(r["event_id"])] = r
            if r.get("status") == "running" and r.get("event_type") == EVENT_TYPE_BOARD_MATCH:
                st = _parse(r.get("started_at"))
                if st is not None and utc_day(st) == day:
                    runs.add(r.get("run_id"))
        self.attempts_today = len(runs)
        self.latest = latest
        # a board event's `board` block lives on its pending record(s); its
        # running/completed/failed rows do not carry it
        self.boards: dict[str, dict] = {}
        for r in records:
            if r.get("event_id") and isinstance(r.get("board"), dict):
                self.boards.setdefault(str(r["event_id"]), r["board"])


def classify(ctx: ClaimContext, event: dict) -> tuple[str, str | None]:
    """(kind, detail): claimable | parked (gate absent) | stale (superseded) | held (daily limit, until)."""
    b = event.get("board") or {}
    gate = b.get("gate")
    if not gate or not Path(gate).exists():
        return "parked", None
    if ctx.filter is None:
        return "stale", "filter_cleared"
    if b.get("generation") != ctx.generation:
        return "stale", "superseded_by_generation"
    if b.get("record_type") != "opening" and b.get("opportunity_id") in ctx.passed:
        return "stale", "passed"
    if ctx.attempts_today >= DAILY_BOARD_WAKES:
        return "held", iso(next_utc_midnight(ctx.now))
    return "claimable", None


def superseded_record(event: dict, reason: str, ctx: ClaimContext) -> dict:
    """Terminal: recorded with the existing `suppressed` status so every reader of the store understands it."""
    return {"record_type": "event_status", "event_id": event["event_id"], "event_type": EVENT_TYPE_BOARD_MATCH,
            "status": "suppressed", "suppressed_at": iso(ctx.now), "suppressed_by_policy": "board",
            "suppression_reason": reason, "superseded": True, "superseded_by_generation": ctx.generation}


def read_view(board_file: str | Path) -> View:
    path = Path(board_file)
    if not path.exists():
        return reduce([])
    led = Ledger(path)
    with led.try_locked(BOARD_LOCK_WINDOW_S):
        records = led.read_unlocked()
        validate_board(records, led.line_numbers)
    return reduce(records)


# --- rendering ---------------------------------------------------------------

def _clause_text(clause: dict | None) -> str:
    if not clause:
        return "your filter"
    return " AND ".join(f"{k} {json.dumps(v, ensure_ascii=False)}" for k, v in clause.items())


def _reason(e: dict) -> str:
    b = e["board"]
    if b["record_type"] == "opening":
        s = f"your filter matched it on {_clause_text(b.get('clause'))}"
    elif b["record_type"] == "note":
        s = f"a new note on an entry you were shown (board seq {b['board_seq']})"
    else:
        s = f"a status change on an entry you were shown (board seq {b['board_seq']})"
    if b.get("attempt", 1) > 1:
        s += f" [offered again: attempt {b['attempt']} of {MAX_ATTEMPTS}]"
    return s


def _full_text(n: int, oid: str, events: list[dict], view: View | None, error: str | None) -> str:
    reasons = "; ".join(_reason(e) for e in events)
    entry = view.entries.get(oid) if view is not None else None
    if entry is None:
        why = error or "no opening with this id is on the board"
        seqs = ", ".join(str(e["board"]["board_seq"]) for e in events)
        return (f"== Entry {n} (opportunity {oid})\nWhy you see it: {reasons}\n"
                f"The board could not be shown at claim ({why}); board seqs {seqs}; "
                f"board_read(opportunity_id=\"{oid}\") may read it later.\n")
    o = entry.opening
    st = entry.status + (f" ({entry.status_record['reason']})" if entry.status_record and entry.status_record["reason"] else "")
    head = [f"== Entry {n}: \"{o['title']}\" (opportunity {oid})",
            f"Why you see it: {reasons}",
            f"Status now: {st} [read at claim]",
            f"Kind {o['kind']}; owner {o['owner']}; posted by {o['posted_by']} at {o['posted_at']}; "
            f"tags: {', '.join(o['tags']) or 'none'}; opening board seq {o['seq']}",
            f"What: {o['what']}"]
    for label, key in (("Why", "why"), ("Help wanted", "help_wanted"), ("Record of help", "record_of_help")):
        if o[key]:
            head.append(f"{label}: {o[key]}")
    text = "\n".join(head) + "\n"
    if not entry.notes:
        return text + "Notes: none.\n"
    lines = [f"  - board seq {x['seq']}, {x['created_at']}: {x['text']}" for x in entry.notes]
    kept: list[str] = []
    # the newest note always (it is the entry's current word); then older ones,
    # newest first, while the entry stays within ENTRY_TEXT_CAP
    for line in reversed(lines):
        if kept and len(text) + sum(len(k) + 1 for k in kept) + len(line) + 160 > ENTRY_TEXT_CAP:
            break
        kept.insert(0, line)
    omitted = len(lines) - len(kept)
    notes = f"Notes ({len(lines)}):\n" + "\n".join(kept) + "\n"
    if omitted:
        notes += (f"  ({omitted} earlier note{'s' if omitted != 1 else ''} not shown here; "
                  f"board_read(opportunity_id=\"{oid}\") has every note.)\n")
    return text + notes


def _title_line(oid: str, events: list[dict], view: View | None) -> str:
    entry = view.entries.get(oid) if view is not None else None
    title = entry.opening["title"] if entry else "(not readable at claim)"
    status = entry.status if entry else "unknown"
    return f"- \"{title}\" (opportunity {oid}; status {status}; {_reason(events[0])})\n"


def render_batch(eligible: list[dict], view: View | None, error: str | None, ctx: ClaimContext,
                 shown_before: set[str]) -> tuple[list[dict], dict]:
    """Select what one wake shows and render it: ≤10 entries in full, ≤20 more by title and id,
    ≤BOARD_TEXT_BUDGET characters in all. Events whose entry is not rendered are not selected."""
    groups: dict[str, list[dict]] = {}
    for e in sorted(eligible, key=lambda e: (e["board"]["board_seq"], e["board"]["attempt"])):
        groups.setdefault(e["board"]["opportunity_id"], []).append(e)
    snap = view.last_seq if view is not None else None
    header = ("The opportunities board woke you: entries matched the filter you set, or entries you were "
              "shown changed. Each entry below is shown as it stands now (status and notes read at claim, "
              f"board seq {snap if snap is not None else 'unknown'}).\n"
              f"Your filter as stored (generation {ctx.generation}): "
              f"{json.dumps(ctx.filter, ensure_ascii=False)}\n\n")
    footer_reserve = 700
    budget = BOARD_TEXT_BUDGET - len(header) - footer_reserve
    full: list[tuple[str, str]] = []
    titles: list[tuple[str, str]] = []
    remaining: list[str] = []
    used = 0
    for oid, evs in groups.items():
        if len(full) < FULL_ENTRIES:
            t = _full_text(len(full) + 1, oid, evs, view, error)
            if used + len(t) + 1 <= budget:
                full.append((oid, t)); used += len(t) + 1
                continue
        if len(titles) < TITLE_ENTRIES:
            t = _title_line(oid, evs, view)
            if used + len(t) <= budget:
                titles.append((oid, t)); used += len(t)
                continue
        remaining.append(oid)
    chosen = {oid for oid, _ in full} | {oid for oid, _ in titles}
    selected = [e for oid, evs in groups.items() if oid in chosen for e in evs]
    remaining_events = sum(len(groups[o]) for o in remaining)
    coverage_after = len(shown_before | chosen)
    body = header + "\n".join(t for _, t in full)
    if titles:
        body += ("\nMore entries, by title and id (they count as shown; board_read(opportunity_id) "
                 "reads any of them in full):\n" + "".join(t for _, t in titles))
    footer = "\n"
    if remaining:
        footer += (f"{len(remaining)} more entr{'ies' if len(remaining) != 1 else 'y'} "
                   f"({remaining_events} board event{'s' if remaining_events != 1 else ''}) also matched and "
                   "were not shown in this wake; they stay pending for your next board wake and are not "
                   "counted as shown.\n")
    footer += (f"If this wake completes, you will have been shown {coverage_after} board "
               f"entr{'ies' if coverage_after != 1 else 'y'} in all. board_pass(opportunity_id) stops "
               "updates for one entry; set_board_filter and clear_board_filter change what wakes you. "
               "The board is community/board/board.jsonl, one record per line, seq equals line number.\n")
    text = body + footer
    context = {"text": text, "generation": ctx.generation, "filter": ctx.filter, "snapshot_seq": snap,
               "entries_full": len(full), "entries_titles": len(titles),
               "entries_full_ids": [o for o, _ in full], "entries_titles_ids": [o for o, _ in titles],
               "remaining_entries": len(remaining), "remaining_events": remaining_events,
               "batch_event_ids": [e["event_id"] for e in selected],
               "coverage_after_this_wake": coverage_after}
    if error:
        context["board_error"] = error
    return selected, context


def shown_opportunities(ctx: ClaimContext) -> set[str]:
    out = set()
    for r in _completed_board_events(ctx.latest):
        b = ctx.boards.get(str(r.get("event_id")))
        if b and b.get("opportunity_id"):
            out.add(str(b["opportunity_id"]))
    return out


def _completed_board_events(latest: dict[str, dict]):
    for r in latest.values():
        if r.get("event_type") == EVENT_TYPE_BOARD_MATCH and r.get("status") == "completed":
            yield r


# --- the claim ---------------------------------------------------------------

def claim_board_batch(records: list[dict], pending_board: list[dict], *, now: datetime, run_id,
                      build_running, quiet_claimable, is_due) -> tuple[list[dict], dict | None, dict | None]:
    """Coalesce at claim. Returns (records to append, primary event | None, its running record | None).

    Called by EventStore.claim_next_pending under the store lock. Stale events
    (an older filter generation, a cleared filter, a passed entry) are
    superseded here; the rest, if the day's board-wake limit allows, are
    claimed together under ONE run_id: as many as one envelope renders.
    """
    ctx = ClaimContext(records, now)
    appends: list[dict] = []
    eligible: list[dict] = []
    for e in pending_board:
        kind, detail = classify(ctx, e)
        if kind == "stale":
            appends.append(superseded_record(e, detail, ctx))
            continue
        if kind != "claimable" or not is_due(e, now=now) or not quiet_claimable(records, e, now):
            continue
        eligible.append(e)
    if not eligible:
        return appends, None, None
    board_file = eligible[0]["board"]["board_file"]
    view, error = None, None
    try:
        view = read_view(board_file)
    except (LedgerUnavailable, LedgerMalformed, OSError) as err:
        # shown degraded (ids and seqs, the error named), never dropped: a board
        # that cannot be read must not leave a runnable event the claim refuses forever
        error = f"{type(err).__name__}: {err}"
    selected, context = render_batch(eligible, view, error, ctx, shown_opportunities(ctx))
    run_id = str(run_id or uuid4())
    running = []
    for e in selected:
        r = build_running(e, run_id=run_id, now=ctx.now)
        r["board_snapshot_seq"] = context["snapshot_seq"]
        running.append(r)
    appends.extend(running)
    primary = dict(selected[0])
    primary["board_context"] = context
    primary["_board_batch"] = [dict(e) for e in selected]
    return appends, primary, running[0]


def holds_for_summary(records: list[dict], pending: list[dict], now: datetime) -> dict[str, tuple[str, str | None]]:
    """event_id -> (kind, until) for every pending board event that is not claimable now."""
    out: dict[str, tuple[str, str | None]] = {}
    ctx = None
    for e in pending:
        if not is_board_event(e):
            continue
        ctx = ctx or ClaimContext(records, now)
        kind, detail = classify(ctx, e)
        if kind != "claimable":
            out[str(e.get("event_id"))] = (kind, detail)
    return out


# --- completion and failure --------------------------------------------------

def failure_records(event: dict, *, run_id: str, exc: Exception, now: datetime, compact: bool,
                    context_results=None, admission=None) -> list[dict]:
    """A failed batch loses nothing: each event fails, then gets a successor (attempt+1) or, at the
    cap, a terminal `board_match_abandoned` record. Failures first, successors after, one buffer."""
    batch = event.get("_board_batch") or [event]
    failed, after = [], []
    for i, e in enumerate(batch):
        b = dict(e["board"])
        attempt = int(b.get("attempt", 1))
        terminal = attempt >= MAX_ATTEMPTS
        r = {"record_type": "event_status", "event_id": e["event_id"], "event_type": EVENT_TYPE_BOARD_MATCH,
             "status": "failed", "run_id": run_id, "failed_at": iso(now), "error_type": type(exc).__name__,
             "error": str(exc), "board": {**b, "terminal": terminal, "batch_size": len(batch)}}
        if i == 0:
            if context_results is not None:
                r["context_results"] = context_results
            if admission is not None:
                r["admission"] = admission
        failed.append(r)
        if terminal:
            after.append({"record_type": "board_match_abandoned", "door": b["door"], "board_seq": b["board_seq"],
                          "opportunity_id": b["opportunity_id"], "generation": b["generation"],
                          "attempts": attempt, "last_event_id": e["event_id"], "abandoned_at": iso(now)})
        else:
            after.append(build_match_event(door=b["door"], gate=b["gate"], board_file=b["board_file"],
                                           board_seq=b["board_seq"], record_type=b["record_type"],
                                           opportunity_id=b["opportunity_id"], generation=b["generation"],
                                           attempt=attempt + 1, clause=b.get("clause"), now=now, compact=compact))
    return failed + after
