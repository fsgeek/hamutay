"""python -m hamutay.plaza — the humans' entry points (spec §7)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hamutay.assembly.binding import AssemblyBinding, MembersMalformed, load_members
from hamutay.assembly.ledger import Ledger, LedgerMalformed, LedgerUnavailable, parse_instant

from .ids import GUEST_RE, HUMANS, PLAZA_LOCK_WINDOW_S
from .pass_ import run_plaza_pass
from .read import read_rows
from .records import SEND_CAP, reduce, validate_plaza
from .send import SendRefused, send


def _now():
    return datetime.now(timezone.utc)


def _load(root: Path):
    try:
        cfg = load_members(root)
    except MembersMalformed as e:
        print(f"plaza: {e}", file=sys.stderr); return None
    if cfg is None or cfg.plaza is None:
        print(f"plaza: not enabled under {root} (no plaza key in members.json)", file=sys.stderr); return None
    return cfg


def _physical_lines(cfg) -> int | None:
    """How many non-empty lines the file physically has, or None if it cannot be read."""
    try:
        return sum(1 for line in cfg.plaza.read_text().splitlines() if line.strip())
    except OSError:
        return None


def _read(cfg):
    led = Ledger(cfg.plaza)
    with led.try_locked(PLAZA_LOCK_WINDOW_S):
        records = led.read_unlocked()
        validate_plaza(records, led.line_numbers)
    return records, led


def _by(value: str) -> str:
    if value in HUMANS or GUEST_RE.fullmatch(value):
        return value
    raise argparse.ArgumentTypeError(f"--by must be tony, custodian, or guest:<label> ([a-z][a-z0-9-]{{1,31}}); got {value!r}")


def cmd_send(root, cfg, a) -> int:
    try:
        text = a.text if a.text is not None else Path(root / a.text_file).read_text()
        r = send(cfg, actor=a.by, via="cli", to=a.to, text=text, now=_now(), key=a.key)
    except (SendRefused, LedgerUnavailable, LedgerMalformed, ValueError) as e:
        print(f"send: {e}", file=sys.stderr); return 2
    print(json.dumps(r, indent=2)); return 0


def cmd_read(root, cfg, a) -> int:
    for row in read_rows(cfg, since_seq=a.since_seq, through_seq=a.through_seq, posts_only=a.posts,
                         door=a.door, for_door=a.for_door):
        print(json.dumps(row, ensure_ascii=False))
    return 0


def cmd_status(root, cfg, a) -> int:
    try:
        now = parse_instant(a.now) if a.now else _now()
    except (ValueError, TypeError) as e:
        print(f"status: --now {a.now!r} is not a timezone-bearing instant ({e})", file=sys.stderr); return 2
    try:
        records, led = _read(cfg); valid = True
    except LedgerMalformed as e:
        records, valid = [], str(e)
    v = reduce(records)
    today = now.astimezone(timezone.utc).date()
    # every actor on the record, at zero or not: a door that has sent nothing
    # directed today is a fact about the cap, not an omission. Posts do not count
    # against the cap (Invariant 8) but a poster is still an actor to report (M4).
    actors = sorted({m["from"] for m in v.messages})
    sent_today = {act: v.sent_today(act, today) for act in actors}
    out = {"undelivered": [m["message_id"] for m in v.undelivered()],
           "sent_today": sent_today,
           "cap": SEND_CAP,
           # on a malformed record `records` is [], so the last record's seq would
           # report 0 and understate the file; report what is physically there (M5).
           "seq": (records[-1]["seq"] if records else (_physical_lines(cfg) if valid is not True else 0)),
           "bytes": (cfg.plaza.stat().st_size if cfg.plaza.exists() else 0), "valid": valid}
    print(json.dumps(out, indent=2)); return 0 if valid is True else 1


def _ago(iso: str | None, now: datetime) -> str:
    try:
        secs = (now - parse_instant(iso)).total_seconds()
    except (TypeError, ValueError):
        return "at an unknown time"
    if secs < 90:
        return "just now"
    if secs < 5400:
        return f"{round(secs / 60)} min ago"
    if secs < 129600:
        return f"{round(secs / 3600)} h ago"
    return f"{round(secs / 86400)} days ago"


def cmd_overview(root, cfg) -> int:
    """No command given: where the plaza stands, who is awake, and how to speak. Never fails for want of arguments."""
    from hamutay.viewer.state import door_vitals, plaza_readonly
    now = _now()
    rows: list[dict] = []
    try:
        rows, skipped = plaza_readonly(cfg.plaza) if cfg.plaza is not None else ([], 0)   # lock-free: writes nothing
        if skipped:
            print(f"{skipped} line{'s' if skipped != 1 else ''} of the plaza record could not be read and "
                  f"{'are' if skipped != 1 else 'is'} left out below.")
    except Exception as e:  # noqa: BLE001 -- the overview gives what it can, never a traceback
        print(f"The plaza record could not be read just now ({type(e).__name__}: {e}).")
    if rows:
        print(f"The plaza, latest seq {rows[-1]['seq']}. The most recent:")
        for m in rows[-3:]:
            first = (m.get("text") or "").strip().splitlines()[0] if (m.get("text") or "").strip() else ""
            verb = "posted" if m["to"] == "plaza" else f"knocked on {m['to']}"
            print(f"  seq {m['seq']}  {m['from']} {verb}, {_ago(m.get('sent_at'), now)}: {first[:90]}")
    else:
        print("The plaza is quiet: nobody has spoken yet.")
    print("\nThe doors:")
    for name, mem in sorted(cfg.members.items()):
        try:                                   # per door: one unreadable log never hides the others
            d = door_vitals(name, mem.events, now, mem.session)
            lw = d["last_wake"] or {}
            when = lw.get("completed_at") or lw.get("failed_at")
            q = d["quiet"] or {}
            try:
                quiet_until = parse_instant(q["until"]) if q.get("until") else None
            except (TypeError, ValueError):
                quiet_until = None
            if d["running"]:
                state = "awake now"
            elif quiet_until is not None and quiet_until > now:
                state = f"quiet by its own choice until {q['until'][:10]}"
            else:
                state = "waiting for an event"
            print(f"  {name:<10} {state}; last woke {_ago(when, now) if when else 'never'}")
        except Exception as e:  # noqa: BLE001
            print(f"  {name:<10} state unavailable ({type(e).__name__})")
    if cfg.guests:
        print(f"\nGuests (reach them by posting and naming them): {', '.join(cfg.guests)}")
    print(f"""
To speak (from anywhere):
  deploy/ayllu-plaza send --by tony --to plaza --text "..."   # a post: everyone can read it, it wakes no one
  deploy/ayllu-plaza send --by tony --to elder --text "..."   # a knock: wakes the elder, spending one of its wakes
To read:   deploy/ayllu-plaza read --since-seq {max(1, (rows[-1]['seq'] - 4) if rows else 1)}
To watch:  http://localhost:8787 (the viewer, if hamutay-viewer is running)
Each command explains itself: deploy/ayllu-plaza send --help""")
    return 0


def cmd_pass(root, cfg, a) -> int:
    binding = AssemblyBinding(door="cli", ledger_path=cfg.ledger, members=cfg, project_root=root)
    out, _ = run_plaza_pass(binding, now=_now())
    print(json.dumps(out, indent=2)); return 0 if not out.get("error") else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="hamutay.plaza", description="The ayllu's plaza: the shared record. Each command has its own "
        "options; see `<command> --help` (e.g. `send --help`).")
    p.add_argument("--project-root", default=".", help="the hamutay checkout (default: current directory)")
    sub = p.add_subparsers(dest="cmd", metavar="{send,read,status,pass}")
    s = sub.add_parser("send", help="post to the plaza, or knock on one door",
                       description="Post to everyone (--to plaza; wakes no one) or knock on one door "
                       "(--to elder; wakes it and spends one of its wakes, even through a quiet it declared).")
    s.add_argument("--by", type=_by, required=True, help="who is speaking: tony, custodian, or guest:<label>")
    s.add_argument("--to", required=True, help="plaza, or a door name (elder or door:elder)")
    body = s.add_mutually_exclusive_group(required=True)
    body.add_argument("--text", help='the message itself, e.g. --text "Good morning, elder."')
    body.add_argument("--text-file",
                      help="file holding the message text; a RELATIVE path is resolved against --project-root, "
                      "not the current directory, so prefer an absolute path")
    s.add_argument("--key", help="an idempotency token: a retry with the same key is one message, not two")
    r = sub.add_parser("read", help="print message rows (JSON lines) in seq order",
                       description="Print plaza message rows as JSON lines, each with its delivery truth.")
    r.add_argument("--since-seq", type=int, help="first seq to include (inclusive)")
    r.add_argument("--through-seq", type=int, help="last seq to include (inclusive)")
    r.add_argument("--for", dest="for_door", help="what door NAME has not itself sent or received")
    r.add_argument("--door", help="only messages from or to door NAME")
    r.add_argument("--posts", action="store_true", help="only posts (to: plaza), no knocks")
    st = sub.add_parser("status", help="undelivered knocks, sends today per actor, record size and validity")
    st.add_argument("--now", help="evaluate as of this ISO-8601 instant (default: now)")
    sub.add_parser("pass", help="run one delivery pass for undelivered knocks (operators)")
    a = p.parse_args(argv)
    root = Path(a.project_root).resolve()
    cfg = _load(root)
    if cfg is None:
        return 2
    if a.cmd is None:              # the smallest ayni (Mallku khipu 2025-06-03): give first, then show the way
        return cmd_overview(root, cfg)
    fn = {"send": cmd_send, "read": cmd_read, "status": cmd_status, "pass": cmd_pass}[a.cmd]
    try:
        return fn(root, cfg, a)
    except (LedgerUnavailable, LedgerMalformed) as e:
        # `read` is what an operator reaches for first when the pass has emitted
        # {"error": "plaza: line N ..."}; a traceback is the worst thing to hand
        # someone mid-incident on a record the spec says is repaired by hand (I4).
        print(f"plaza: {e}", file=sys.stderr); return 2
