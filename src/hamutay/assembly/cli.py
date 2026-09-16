"""python -m hamutay.assembly — the human's entry points (spec §9, §10)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from hamutay.events import EventStore, StoreUnavailable

from .binding import AssemblyBinding, MembersMalformed, load_members
from .close import active_positions, eligible_positions
from .convene import ConveneRefused, convene, parse_closes_in
from .ledger import Ledger, LedgerMalformed, LedgerUnavailable, parse_instant
from .pass_ import run_pass
from .records import build_execution, build_testimony, build_withdrawal, reduce


def _now():
    return datetime.now(timezone.utc)


def _artifact(root: Path, path: str, commit: str) -> dict:
    out = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if out.returncode != 0:
        raise ConveneRefused(f"artifact: git show {commit}:{path} failed: {out.stderr.decode()[:200]}")
    return {"path": path, "commit": commit, "sha256": hashlib.sha256(out.stdout).hexdigest()}


def _cli_binding(root: Path, cfg) -> AssemblyBinding:
    return AssemblyBinding(door="cli", ledger_path=cfg.ledger, members=cfg, project_root=root)


def cmd_convene(root, cfg, led, a) -> int:
    text = Path(root / a.text_file).read_text()
    proposal = artifact = None
    if a.proposal_procedure:
        proposal = json.loads(Path(root / a.proposal_procedure).read_text())
        if not (a.artifact and a.artifact_commit):
            print("convene: --proposal-procedure needs --artifact and --artifact-commit", file=sys.stderr); return 2
    try:
        if proposal is not None:
            artifact = _artifact(root, a.artifact, a.artifact_commit)
        q = convene(led, cfg, convener=a.by, text=text, closes_in=parse_closes_in(a.closes_in), now=_now(),
                    proposal_procedure=proposal, artifact=artifact)
    except (ConveneRefused, ValueError) as e:
        print(f"convene: {e}", file=sys.stderr); return 2
    run_pass(_cli_binding(root, cfg), now=_now(), actor=f"cli:{a.by}")
    print(json.dumps(q, indent=2, default=str)); return 0


def _open_question_or_refuse(view, qid: str, now) -> dict | None:
    q = view.questions.get(qid)
    if q is None or qid in view.closings or now >= parse_instant(q["closes_at"]):
        return None
    return q


def cmd_testify(root, cfg, led, a) -> int:
    with led.locked():
        view = reduce(led.read_unlocked())
        q = _open_question_or_refuse(view, a.question_id, _now())
        if q is None:
            print("testify: question unknown, closed, or past its deadline", file=sys.stderr); return 2
        rec = led.append_unlocked(build_testimony(question=q, by=a.by, text=Path(root / a.text_file).read_text()))
    print(json.dumps(rec, indent=2, default=str)); return 0


def cmd_withdraw(root, cfg, led, a) -> int:
    with led.locked():
        view = reduce(led.read_unlocked())
        q = _open_question_or_refuse(view, a.question_id, _now())
        if q is None or q["convener"] != a.by:
            print("withdraw: not an open question of this convener", file=sys.stderr); return 2
        rec = led.append_unlocked(build_withdrawal(question_id=a.question_id, by=a.by, reasons=a.reasons))
    run_pass(_cli_binding(root, cfg), now=_now(), actor=f"cli:{a.by}")
    print(json.dumps(rec, indent=2, default=str)); return 0


def cmd_execute(root, cfg, led, a) -> int:
    with led.locked():
        view = reduce(led.read_unlocked())
        c = view.closings_by_id.get(a.closing_id)
        if c is None or c["outcome"] != "assented" or any(e["outcome"] == "done" for e in view.executions_for(a.closing_id)):
            print("execute: needs an assented closing with no prior done execution", file=sys.stderr); return 2
        try:
            rec = led.append_unlocked(build_execution(closing=c, by=a.by, outcome=a.outcome, what=a.what, reasons=a.reasons))
        except ValueError as e:
            print(f"execute: {e}", file=sys.stderr); return 2
    print(json.dumps(rec, indent=2, default=str)); return 0


def cmd_pass(root, cfg, led, a) -> int:
    out, _ = run_pass(_cli_binding(root, cfg), now=_now(), actor=a.actor)
    print(json.dumps(out, indent=2, default=str)); return 0


def cmd_status(root, cfg, led, a) -> int:
    view = reduce(led.read()); now = _now()
    act = view.active_procedure
    opens = []
    for q in view.open_questions():
        members = list(q["members"])
        stores = {}
        for d in members:
            try:
                stores[d] = EventStore(Path(q["members"][d]["events"])).try_read_records(timeout_s=0.5)
            except StoreUnavailable:
                stores[d] = None
        active = active_positions(eligible_positions(view, q["lineage_id"], stores, members), members)
        opens.append({"question_id": q["question_id"], "lineage_id": q["lineage_id"], "round": q["round"],
                      "convener": q["convener"], "opened_at": q["opened_at"], "closes_at": q["closes_at"],
                      "seconds_to_close": (parse_instant(q["closes_at"]) - now).total_seconds(),
                      "delivery": {d: view.delivery_truth("question", q["question_id"], d) for d in members},
                      "active": {d: (p["stance"] if p else None) for d, p in active.items()},
                      "absent_so_far": [d for d in members if active[d] is None and stores[d] is not None],
                      "unknown": [d for d in members if stores[d] is None]})
    print(json.dumps({"governing": view.governing_for_new_question(),
                      "active_procedure": ({"procedure_id": act["procedure_id"], "version": act["version"]} if act else None),
                      "open_questions": opens}, indent=2, default=str)); return 0


def cmd_history(root, cfg, led, a) -> int:
    records = led.read()
    view = reduce(records)
    qids = {qid for qid, q in view.questions.items() if q["lineage_id"] == a.lineage_id}
    cids = {c["closing_id"] for c in view.closings_by_id.values() if c["lineage_id"] == a.lineage_id}
    pids = {q["proposal"]["procedure_id"] for q in view.questions.values()
            if q["lineage_id"] == a.lineage_id and q["proposal"]["kind"] == "procedure"}
    rows = [r for r in records if r.get("lineage_id") == a.lineage_id
            or r.get("question_id") in qids
            or r.get("closing_id") in cids
            or (r.get("record_type") == "delivery" and r.get("id") in qids | cids)
            or (r.get("record_type") == "procedure" and r.get("procedure_id") in pids)]
    print(json.dumps(rows, indent=2, default=str)); return 0


def cmd_procedure(root, cfg, led, a) -> int:
    print(json.dumps(reduce(led.read()).procedures, indent=2, default=str)); return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hamutay.assembly")
    p.add_argument("--project-root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("convene"); s.add_argument("--by", required=True); s.add_argument("--text-file", required=True)
    s.add_argument("--closes-in", required=True); s.add_argument("--proposal-procedure"); s.add_argument("--artifact")
    s.add_argument("--artifact-commit"); s.set_defaults(fn=cmd_convene)
    s = sub.add_parser("testify"); s.add_argument("--by", required=True, choices=["tony", "custodian"])
    s.add_argument("--question-id", required=True); s.add_argument("--text-file", required=True); s.set_defaults(fn=cmd_testify)
    s = sub.add_parser("withdraw"); s.add_argument("--by", required=True, choices=["tony", "custodian"])
    s.add_argument("--question-id", required=True)
    s.add_argument("--reasons"); s.set_defaults(fn=cmd_withdraw)
    s = sub.add_parser("execute"); s.add_argument("--by", required=True, choices=["tony", "custodian"])
    s.add_argument("--closing-id", required=True); s.add_argument("--outcome", required=True, choices=["done", "declined"])
    s.add_argument("--what", required=True); s.add_argument("--reasons"); s.set_defaults(fn=cmd_execute)
    s = sub.add_parser("pass"); s.add_argument("--actor", default="cli:custodian"); s.set_defaults(fn=cmd_pass)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("history"); s.add_argument("--lineage-id", required=True); s.set_defaults(fn=cmd_history)
    sub.add_parser("procedure").set_defaults(fn=cmd_procedure)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    root = Path(a.project_root).resolve()
    try:
        cfg = load_members(root)
    except MembersMalformed as e:
        print(f"assembly: members.json malformed: {e}", file=sys.stderr); return 2
    if cfg is None:
        print(f"assembly: no members.json under {root}", file=sys.stderr); return 2
    led = Ledger(cfg.ledger)
    try:
        return a.fn(root, cfg, led, a)
    except (LedgerMalformed, LedgerUnavailable) as e:
        print(f"assembly: {e}", file=sys.stderr); return 2
