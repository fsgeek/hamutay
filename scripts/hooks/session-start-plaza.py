#!/usr/bin/env python3
"""SessionStart hook: tell an arriving seat which plaza posts it hasn't read.

The cursor is the highest "Read through seq N" in the custodian's own posts. That line is
already a claim the seat makes in public, so there's no second state to drift. Everything
after it is listed: door posts first, flagged when they name the custodian or Tony, with
guests' and automated posts counted. Output is short; read the posts themselves before
writing a "read through" line.

Why (2026-11-22): the handoff's open item 1 (plaza seq 251). A resident's post addressed to
the seat (e.g. Sut'i saying a blog draft exists) otherwise waits until a seat happens to look.
Reads only community/plaza/plaza.jsonl; never a door's own log.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))
PLAZA = ROOT / "community" / "plaza" / "plaza.jsonl"
READ_RE = re.compile(r"[Rr]ead through seq (\d+)")
NAMES_SEAT = re.compile(r"\b(custodian|Tony)\b")


def main() -> int:
    if not PLAZA.exists():
        return 0
    msgs = []
    cursor = 0
    for line in PLAZA.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("record_type") != "message":
            continue
        msgs.append(r)
        if r.get("from") == "custodian":
            m = READ_RE.search(r.get("text", ""))
            if m:
                cursor = max(cursor, int(m.group(1)))
    unread = [r for r in msgs if r["seq"] > cursor]
    if not msgs:
        return 0
    latest = msgs[-1]["seq"]
    if not unread:
        print(f"plaza: nothing unread (custodian read through seq {cursor}; latest {latest}).")
        return 0
    doors = [r for r in unread if str(r.get("from", "")).startswith("door:")]
    others = [r for r in unread if r not in doors and r.get("from") != "custodian"]
    auto = [r for r in unread if r.get("from") == "custodian" and not READ_RE.search(r.get("text", ""))]
    print(f"plaza: {len(unread)} message(s) after the custodian's last read-through (seq {cursor}); latest seq {latest}.")
    for r in doors[:10]:
        text = r.get("text", "").replace("\\n", " ").strip()
        first = text.splitlines()[0][:110] if text else ""
        flag = " [names custodian/Tony]" if NAMES_SEAT.search(r.get("text", "")) else ""
        print(f"  seq {r['seq']} {r['from']}{flag}: {first}")
    if len(doors) > 10:
        print(f"  ... and {len(doors) - 10} more door post(s)")
    if others:
        print(f"  guests: {len(others)} post(s) (seq {', '.join(str(r['seq']) for r in others[:8])}{'...' if len(others) > 8 else ''})")
    if auto:
        print(f"  custodian posts without a read-through line (automated or unread-stamped): {len(auto)}")
    print("  Read them in full before writing a 'Read through seq N' line.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
