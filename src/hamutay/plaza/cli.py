"""python -m hamutay.plaza — the humans' entry points (spec §7)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hamutay.assembly.binding import AssemblyBinding, MembersMalformed, load_members
from hamutay.assembly.ledger import Ledger, LedgerMalformed, LedgerUnavailable, parse_instant

from .pass_ import run_plaza_pass
from .records import reduce, validate_plaza
from .send import PLAZA_LOCK_WINDOW_S, SendRefused, send


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


def _read(cfg):
    led = Ledger(cfg.plaza)
    with led.try_locked(PLAZA_LOCK_WINDOW_S):
        records = led.read_unlocked()
        validate_plaza(records, led.line_numbers)
    return records, led


def cmd_send(root, cfg, a) -> int:
    try:
        r = send(cfg, actor=a.by, via="cli", to=a.to, text=Path(root / a.text_file).read_text(), now=_now(), key=a.key)
    except (SendRefused, LedgerUnavailable, LedgerMalformed, ValueError) as e:
        print(f"send: {e}", file=sys.stderr); return 2
    print(json.dumps(r, indent=2)); return 0


def cmd_read(root, cfg, a) -> int:
    records, _ = _read(cfg)
    v = reduce(records)
    for m in v.messages:
        if a.since_seq is not None and m["seq"] < a.since_seq:
            continue
        if a.through_seq is not None and m["seq"] > a.through_seq:
            continue
        if a.posts and m["to"] != "plaza":
            continue
        if a.door and m["from"] != f"door:{a.door}" and m["to"] != f"door:{a.door}":
            continue
        if a.for_door and (m["from"] == f"door:{a.for_door}" or m["to"] == f"door:{a.for_door}"):
            continue
        row = dict(m); row["truth"] = v.delivery_truth(m["message_id"]) if m["delivery"] else {"state": "post"}
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
    actors = sorted({m["from"] for m in v.messages if m["to"] != "plaza"})
    sent_today = {act: v.sent_today(act, today) for act in actors if v.sent_today(act, today)}
    out = {"undelivered": [m["message_id"] for m in v.undelivered()],
           "sent_today": sent_today,
           "seq": (records[-1]["seq"] if records else 0),
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
    s = sub.add_parser("send"); s.add_argument("--by", choices=["tony", "custodian"], required=True)
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
    except LedgerUnavailable as e:
        print(f"plaza: {e}", file=sys.stderr); return 2
