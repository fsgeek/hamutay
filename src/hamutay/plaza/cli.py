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
        r = send(cfg, actor=a.by, via="cli", to=a.to, text=Path(root / a.text_file).read_text(), now=_now(), key=a.key)
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


def cmd_pass(root, cfg, a) -> int:
    binding = AssemblyBinding(door="cli", ledger_path=cfg.ledger, members=cfg, project_root=root)
    out, _ = run_plaza_pass(binding, now=_now())
    print(json.dumps(out, indent=2)); return 0 if not out.get("error") else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hamutay.plaza")
    p.add_argument("--project-root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send"); s.add_argument("--by", type=_by, required=True)
    s.add_argument("--to", required=True); s.add_argument("--text-file", required=True); s.add_argument("--key")
    r = sub.add_parser("read"); r.add_argument("--since-seq", type=int); r.add_argument("--through-seq", type=int)
    r.add_argument("--for", dest="for_door"); r.add_argument("--door"); r.add_argument("--posts", action="store_true")
    st = sub.add_parser("status"); st.add_argument("--now")
    sub.add_parser("pass")
    a = p.parse_args(argv)
    root = Path(a.project_root).resolve()
    cfg = _load(root)
    if cfg is None:
        return 2
    fn = {"send": cmd_send, "read": cmd_read, "status": cmd_status, "pass": cmd_pass}[a.cmd]
    try:
        return fn(root, cfg, a)
    except (LedgerUnavailable, LedgerMalformed) as e:
        # `read` is what an operator reaches for first when the pass has emitted
        # {"error": "plaza: line N ..."}; a traceback is the worst thing to hand
        # someone mid-incident on a record the spec says is repaired by hand (I4).
        print(f"plaza: {e}", file=sys.stderr); return 2
