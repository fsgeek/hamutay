"""python -m hamutay.board -- post | note | status | read (contract §4)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hamutay.assembly.binding import MembersMalformed, load_members
from hamutay.assembly.ledger import LedgerMalformed, LedgerUnavailable

from .ids import board_enabled, gate_path
from .records import KINDS, STATUSES
from .write import BoardRefused, add_note, post_opening, read_entries, set_status


def _now():
    return datetime.now(timezone.utc)


def _admitted(root: Path):
    try:
        cfg = load_members(root)
    except MembersMalformed:
        return None
    return cfg.guests if cfg is not None else None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="hamutay.board",
        description="The opportunities board: openings for work wanted, readable by everyone "
        "(community/board/board.jsonl). See `<command> --help`.")
    p.add_argument("--project-root", default=".", help="the hamutay checkout (default: current directory)")
    sub = p.add_subparsers(dest="cmd", metavar="{post,note,status,read}")
    by_help = "who is writing: tony, custodian, or guest:<label> (an admitted guest)"
    s = sub.add_parser("post", help="post an opening")
    s.add_argument("--by", required=True, help=by_help)
    s.add_argument("--title", required=True, help="one line, at most 120 characters")
    s.add_argument("--what", required=True, help="what is wanted, at most 2000 characters")
    s.add_argument("--kind", required=True, help=f"one of {', '.join(KINDS)} (normalized as the writer does)")
    s.add_argument("--why", default="", help="at most 1000 characters")
    s.add_argument("--help-wanted", default="", help="what help would look like, at most 1000 characters")
    s.add_argument("--tags", default="", help="comma-separated, at most 8, each [a-z0-9-]{1,32}")
    s.add_argument("--owner", default=None, help="canonical label of the owner (default: --by)")
    s.add_argument("--record-of-help", default="", help="how help will be recorded, at most 500 characters")
    n = sub.add_parser("note", help="add a note to an entry you own")
    n.add_argument("--by", required=True, help=by_help)
    n.add_argument("--id", required=True, dest="opportunity_id")
    n.add_argument("--text", required=True, help="at most 1000 characters")
    st = sub.add_parser("status", help="set the status of an entry you own (closed is final)")
    st.add_argument("--by", required=True, help=by_help)
    st.add_argument("--id", required=True, dest="opportunity_id")
    st.add_argument("--status", required=True, choices=STATUSES)
    st.add_argument("--reason", default="", help="at most 500 characters")
    r = sub.add_parser("read", help="print entries as JSON")
    r.add_argument("--id", dest="opportunity_id", help="one entry, with every note and status")
    r.add_argument("--all", action="store_true", help="include closed entries")
    r.add_argument("--since-seq", type=int)
    a = p.parse_args(argv)
    root = Path(a.project_root).resolve()
    if a.cmd is None:
        state = "enabled" if board_enabled(root) else f"dormant (no {gate_path(root)})"
        print(f"The opportunities board is {state}. Commands: post, note, status, read.")
        return 0
    if a.cmd != "read" and str(a.by).strip().casefold().startswith("door:"):
        print(f"board {a.cmd}: --by must be tony, custodian or guest:<label>; a door writes through its "
              "board_post tool", file=sys.stderr)
        return 2
    try:
        if a.cmd == "read":
            out = read_entries(root, opportunity_id=a.opportunity_id, include_closed=a.all, since_seq=a.since_seq)
            out["enabled"] = board_enabled(root)
        elif a.cmd == "post":
            tags = [t for t in a.tags.split(",")] if a.tags else []
            out = post_opening(root, by=a.by, title=a.title, what=a.what, kind=a.kind, why=a.why,
                               help_wanted=a.help_wanted, tags=tags, owner=a.owner,
                               record_of_help=a.record_of_help, now=_now(), admitted_guests=_admitted(root))
        elif a.cmd == "note":
            out = add_note(root, by=a.by, opportunity_id=a.opportunity_id, text=a.text, now=_now(),
                           admitted_guests=_admitted(root))
        else:
            out = set_status(root, by=a.by, opportunity_id=a.opportunity_id, status=a.status, reason=a.reason,
                             now=_now(), admitted_guests=_admitted(root))
    except (BoardRefused, LedgerUnavailable, LedgerMalformed, ValueError) as e:
        print(f"board {a.cmd}: {e}", file=sys.stderr)
        return 2
    if a.cmd != "read" and "duplicate_of_seq" not in out and not board_enabled(root):
        out["note"] = "the board is dormant: written, but no door is matched or woken until the gate exists"
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0
