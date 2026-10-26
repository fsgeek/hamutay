"""The board's reconciliation pass, run on each heartbeat poll (contract §6), and the onboarding notice (§11).

Durable by recomputation: each pass derives, from the board and the door's own
event store, which board_match events should exist for the door's current
filter generation and appends the missing ones, bounded per pass. Nothing is
trusted to a cursor: the memo below only lets a pass skip work when neither
file has changed since a pass that left nothing to do, and it is advanced only
after the appends it covers have been written.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from hamutay.assembly.ledger import LedgerMalformed, LedgerUnavailable, iso
from hamutay.events import EVENT_TYPE_INBOUND, StoreUnavailable

from .delivery import (EVENT_TYPE_BOARD_MATCH, MAX_ATTEMPTS, ClaimContext, build_match_event, classify,
                       read_view, superseded_record)
from .filters import match
from .ids import ONBOARDING_LABEL, STORE_LOCK_WINDOW_S, board_enabled, board_path, gate_path, onboarding_event_id
from .records import View

PASS_MAX_APPENDS = 32
ONBOARDING_LIST_MAX = 20


@dataclass(frozen=True)
class BoardMemo:
    signature: tuple
    clean: bool        # the pass that produced this memo left nothing to do


def _sig(path: Path) -> tuple:
    try:
        st = path.stat()
    except FileNotFoundError:
        return (0, 0.0)
    return (st.st_size, st.st_mtime_ns)


def onboarding_text(view: View) -> str:
    open_entries = [e for e in view.entries.values() if e.status == "open"]
    lines = [f"- \"{e.opening['title']}\" (opportunity {e.opportunity_id}; kind {e.opening['kind']}; "
             f"owner {e.opening['owner']})" for e in open_entries[:ONBOARDING_LIST_MAX]]
    more = len(open_entries) - len(lines)
    listing = ("\n".join(lines) + (f"\n- ... and {more} more; board_read lists them." if more > 0 else "")
               if lines else "(none open when this notice was written)")
    return (
        "The opportunities board is open. It is the ayllu's shared list of work wanted: anyone in the house "
        "(Tony, the custodian, a door, a guest) may post an opening -- a review, a design, a build, an "
        "analysis, some writing, testimony -- saying what is wanted, why, and what help would look like. It "
        "lives at community/board/board.jsonl, one record per line, seq equals line number, and everyone "
        "can read it.\n\n"
        "Your tools: board_read lists the entries (or one, by opportunity_id, with every note); board_post "
        "posts an opening, or, on an entry you own, a note or a status (open, taken, closed); "
        "set_board_filter(kinds, tags_any, owners_any, keywords_any) chooses what should wake you -- AND "
        "across fields, OR within one; it scans the open entries at once and queues what matches; "
        "clear_board_filter removes it; board_pass(opportunity_id) stops updates about one entry.\n\n"
        "A door with no filter is never woken by the board. That is a choice, and it is yours: you may set "
        "no filter at all. With a filter, the board wakes you at most twice per UTC day, gathers every "
        "match into one wake, and shows each entry with its current status. Your posts never wake you.\n\n"
        f"Open entries now:\n{listing}\n\n"
        "This notice is sent once. Nothing obliges you to answer it.")


def onboarding_event(door: str, view: View, now: datetime) -> dict:
    return {"record_type": "event_status", "event_id": onboarding_event_id(door), "event_type": EVENT_TYPE_INBOUND,
            "status": "pending", "created_at": iso(now), "origin": "board", "sender": "board",
            "label": ONBOARDING_LABEL, "purpose": onboarding_text(view), "defer_to_declared_quiet": True}


def derive_appends(records: list[dict], view: View, *, door: str, project_root, now: datetime,
                   limit: int = PASS_MAX_APPENDS) -> tuple[list[dict], bool]:
    """(records to append, truncated). Pure: everything from the board view and the store records."""
    me = f"door:{door}"
    gate = str(gate_path(project_root))
    bfile = str(board_path(project_root))
    ctx = ClaimContext(records, now)
    out: list[dict] = []
    known = {str(r.get("event_id")) for r in records if r.get("event_id")}
    if onboarding_event_id(door) not in known:
        out.append(onboarding_event(door, view, now))

    board_events = [r for r in ctx.latest.values() if r.get("event_type") == EVENT_TYPE_BOARD_MATCH]
    for e in board_events:
        if e.get("status") == "pending":
            first = _first_pending(records, e["event_id"]) or e
            kind, why = classify(ctx, first)
            if kind == "stale":
                out.append(superseded_record(first, why, ctx))

    if ctx.filter is None:
        return _bound(out, limit)

    # coverage: board seqs whose event's wake completed; entries shown, with the board seq as of first showing
    running_snap: dict[tuple[str, str], int | None] = {}
    for r in records:
        if r.get("record_type") == "event_status" and r.get("status") == "running" \
                and r.get("event_type") == EVENT_TYPE_BOARD_MATCH:
            running_snap[(str(r["event_id"]), str(r.get("run_id")))] = r.get("board_snapshot_seq")
    covered: set[int] = set()
    first_shown: dict[str, int] = {}
    for e in board_events:
        if e.get("status") != "completed":
            continue
        b = e.get("board") or _board_of(records, e["event_id"])
        if not b:
            continue
        covered.add(int(b["board_seq"]))
        snap = running_snap.get((str(e["event_id"]), str(e.get("run_id"))))
        snap = int(snap) if isinstance(snap, int) else int(b["board_seq"])
        oid = b["opportunity_id"]
        first_shown[oid] = min(first_shown.get(oid, snap), snap)

    # the current generation's lineages: board_seq -> (highest attempt, its latest status)
    lineage: dict[int, tuple[int, str, dict]] = {}
    for e in board_events:
        b = _board_of(records, e["event_id"])
        if not b or b.get("generation") != ctx.generation:
            continue
        seq, att = int(b["board_seq"]), int(b.get("attempt", 1))
        if seq not in lineage or att > lineage[seq][0]:
            lineage[seq] = (att, e.get("status"), b)
    abandoned = {int(r["board_seq"]) for r in records if r.get("record_type") == "board_match_abandoned"
                 and r.get("generation") == ctx.generation and isinstance(r.get("board_seq"), int)}

    def want(seq: int, record_type: str, oid: str, clause):
        if seq in covered or seq in abandoned:
            return
        att, status = 1, None
        if seq in lineage:
            att, status, _ = lineage[seq]
            if status != "failed":
                return                     # pending, running, completed or superseded: handled
            if att >= MAX_ATTEMPTS:
                out.append({"record_type": "board_match_abandoned", "door": door, "board_seq": seq,
                            "opportunity_id": oid, "generation": ctx.generation, "attempts": att,
                            "last_event_id": None, "abandoned_at": iso(now)})
                return
            att += 1                       # repair: a failure whose successor was never written
        ev = build_match_event(door=door, gate=gate, board_file=bfile, board_seq=seq, record_type=record_type,
                               opportunity_id=oid, generation=ctx.generation, attempt=att, clause=clause, now=now)
        if ev["event_id"] not in known:
            out.append(ev)

    for r in view.records:
        seq, rt, oid = r["seq"], r["record_type"], r["opportunity_id"]
        if rt == "opening":
            entry = view.entries[oid]
            if r["posted_by"] == me or oid in first_shown or entry.status != "open":
                continue
            clause = match(ctx.filter, r)
            if clause is not None:
                want(seq, rt, oid, clause)
        else:
            if oid not in first_shown or oid in ctx.passed or r["by"] == me or seq <= first_shown[oid]:
                continue
            want(seq, rt, oid, None)
    return _bound(out, limit)


def _bound(out: list[dict], limit: int) -> tuple[list[dict], bool]:
    return out[:limit], len(out) > limit


def _first_pending(records: list[dict], event_id: str) -> dict | None:
    for r in records:
        if r.get("event_id") == event_id and r.get("status") == "pending":
            return r
    return None


def _board_of(records: list[dict], event_id: str) -> dict | None:
    for r in records:
        if r.get("event_id") == event_id and isinstance(r.get("board"), dict):
            return r["board"]
    return None


def run_board_pass(*, door: str, project_root, store, now: datetime,
                   memo: BoardMemo | None = None) -> tuple[dict, BoardMemo | None]:
    """One bounded pass. Dormant (no reads, no writes) while the gate file is absent."""
    if not board_enabled(project_root):
        return {"skipped": "dormant", "appended": 0}, None
    sig = (_sig(board_path(project_root)), _sig(Path(store.path)))
    if memo is not None and memo.clean and memo.signature == sig:
        return {"skipped": True, "appended": 0}, memo
    try:
        view = read_view(board_path(project_root))
    except (LedgerUnavailable, LedgerMalformed) as e:
        return {"skipped": False, "error": f"board: {type(e).__name__}: {e}", "appended": 0}, memo
    truncated = False

    def derive(records):
        nonlocal truncated
        out, truncated = derive_appends(records, view, door=door, project_root=project_root, now=now)
        return out
    try:
        written = store.append_derived(derive, timeout_s=STORE_LOCK_WINDOW_S)
    except (StoreUnavailable, OSError) as e:
        return {"skipped": False, "error": f"store: {type(e).__name__}: {e}", "appended": 0}, memo
    # the memo advances only now, after the appends it covers are written
    new_memo = BoardMemo((_sig(board_path(project_root)), _sig(Path(store.path))), clean=not truncated)
    queued = sum(1 for r in written if r.get("event_type") == EVENT_TYPE_BOARD_MATCH and r.get("status") == "pending")
    return {"skipped": False, "appended": len(written), "queued": queued, "truncated": truncated,
            "events": [r.get("event_id") or r.get("record_type") for r in written]}, new_memo
