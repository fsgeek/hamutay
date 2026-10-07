"""What the viewer shows, gathered read-only from the shared record.

Shown: the plaza (every message, with delivery truth), the assembly (questions,
positions, closings, testimony, executions), and each door's vital signs taken
from its event log: wake times and outcomes, failed-wake errors, rests, declared
quiet, and spend from its billing ledger.

Never shown: a door's home. Not its session log, authored state, raw output,
nor the response_text its event log holds for each completed wake. A door that
wants the community to hear it speaks on the plaza.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hamutay.assembly.binding import load_members
from hamutay.events import quiet_declaration_for_latest_wake
from hamutay.plaza.records import reduce

WEEK = timedelta(days=7)
EVENT_FIELDS = ("event_id", "event_type", "status", "run_id", "sender", "purpose",
                "created_at", "started_at", "completed_at", "failed_at", "expired_at",
                "wake_cycle", "error_type", "error")


def _tolerant_jsonl(path: Path) -> list[dict]:
    """Every parseable, newline-terminated line. An unterminated final line is a torn append (the
    project's ledger convention) even if it parses; a malformed line is skipped. Never repairs, locks or fails."""
    if not path.exists():
        return []
    data = path.read_bytes()
    lines = data.split(b"\n")
    lines = lines[:-1]                     # the piece after the last newline: empty, or a torn append
    out = []
    for raw in lines:
        if not raw.strip():
            continue
        try:
            r = json.loads(raw)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def _instant(s) -> datetime | None:
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def door_vitals(name: str, events_path: Path, now: datetime, session_path: Path | None = None) -> dict:
    records = _tolerant_jsonl(events_path)
    statuses = [r for r in records if r.get("record_type") == "event_status"]
    latest_by_event: dict[str, dict] = {}
    for r in statuses:
        latest_by_event[str(r.get("event_id"))] = r
    outcomes = [r for r in statuses if r.get("status") in ("completed", "failed")]
    wakes = []
    for r in outcomes[-12:]:
        w = {k: r.get(k) for k in EVENT_FIELDS if r.get(k) is not None}
        err = w.get("error")
        if isinstance(err, str) and len(err) > 300:
            w["error"] = err[:300] + "…"
        wakes.append(w)
    week_ago = now - WEEK
    week = [r for r in outcomes if (_instant(r.get("completed_at") or r.get("failed_at")) or now) >= week_ago]
    heartbeat = [r for r in records if r.get("record_type") == "heartbeat_status"]
    # the quiet in force is the one the latest wake declared, if it completed (events.py's own join)
    quiet = quiet_declaration_for_latest_wake(records)
    # billing lives beside the session log (billing.py: <session>.billing.jsonl), whatever the events file is called
    billing_path = (Path(str(session_path) + ".billing.jsonl") if session_path is not None
                    else Path(str(events_path).replace(".events.jsonl", ".billing.jsonl")))
    billing = _tolerant_jsonl(billing_path)
    spend: dict[str, float] = {}
    for b in billing:                                  # one row per generation id; later fetches win
        if isinstance(b.get("usage_usd"), (int, float)) and b.get("generation_id"):
            if (_instant(b.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= week_ago:
                spend[b["generation_id"]] = float(b["usage_usd"])
    last_hb = heartbeat[-1] if heartbeat else None
    return {
        "name": name,
        "now_status": ({k: last_hb.get(k) for k in ("status", "reason", "created_at")} if last_hb else None),
        "running": [e for e, r in latest_by_event.items() if r.get("status") == "running"],
        "pending": sum(1 for r in latest_by_event.values() if r.get("status") == "pending"),
        "last_wake": wakes[-1] if wakes else None,
        "wakes": wakes,
        "week": {"completed": sum(1 for r in week if r["status"] == "completed"),
                 "failed": sum(1 for r in week if r["status"] == "failed"),
                 "spend_usd_reconciled": round(sum(spend.values()), 4)},
        "quiet": ({k: quiet.get(k) for k in ("reason", "until", "created_at", "declared_by_cycle")}
                  if quiet else None),
    }


def assembly_view(ledger: Path) -> list[dict]:
    records = _tolerant_jsonl(ledger)
    questions: dict[str, dict] = {}
    order: list[str] = []
    def add_question(r: dict, seq, convener) -> None:
        qid = str(r.get("question_id"))
        if qid in questions:
            return
        questions[qid] = {"question_id": qid, "lineage_id": r.get("lineage_id"), "seq": seq,
                          "round": r.get("round"), "convener": r.get("convener") or convener,
                          "text": r.get("text"), "opened_at": r.get("opened_at"), "closes_at": r.get("closes_at"),
                          "positions": [], "testimony": [], "closing": None, "execution": None}
        order.append(qid)

    for r in records:
        t = r.get("record_type")
        if t == "question":
            add_question(r, r.get("seq"), None)
        elif t in ("position", "testimony", "closing", "execution"):
            q = questions.get(str(r.get("question_id")))
            if q is None:
                continue
            if t == "position":
                q["positions"].append({k: r.get(k) for k in ("member", "stance", "reasons", "cycle", "created_at", "seq")})
            elif t == "testimony":
                q["testimony"].append({k: r.get(k) for k in ("by", "text", "created_at", "seq")})
            elif t == "closing":
                q["closing"] = {k: r.get(k) for k in ("outcome", "closed_at", "closed_by", "absent", "seq")}
                nxt = r.get("next_question")
                if isinstance(nxt, dict) and nxt.get("question_id"):   # an extended question's next round
                    add_question(nxt, r.get("seq"), q["convener"])
            else:
                q["execution"] = {k: r.get(k) for k in ("by", "outcome", "what", "created_at", "seq")}
    return [questions[q] for q in reversed(order)]


def gather(project_root: Path, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = load_members(project_root)
    if cfg is None:
        return {"error": "members.json not found: the community is not configured here", "at": now.isoformat()}
    plaza, plaza_error = [], None
    if cfg.plaza is not None:
        try:
            # read lock-free and tolerant: the viewer takes no lock (a lock file is a write) and skips a
            # malformed line rather than losing the whole plaza; the plaza's own readers stay strict
            records = [r for r in _tolerant_jsonl(Path(cfg.plaza))
                       if r.get("record_type") != "message"
                       or (r.get("message_id") and r.get("idempotency_key") is not None)]
            v = reduce(records)
            for m in v.messages:
                row = dict(m)
                row["truth"] = v.delivery_truth(m["message_id"]) if m.get("delivery") else {"state": "post"}
                plaza.append(row)
        except Exception as e:  # noqa: BLE001 -- shown on the page, never raised to the browser as a 500
            plaza, plaza_error = [], f"{type(e).__name__}: {e}"
    return {
        "at": now.isoformat(),
        "doors": [door_vitals(name, m.events, now, m.session) for name, m in sorted(cfg.members.items())],
        "guests": list(cfg.guests or ()),
        "plaza": [{k: m.get(k) for k in ("seq", "from", "to", "text", "sent_at", "truth")} for m in plaza],
        "plaza_error": plaza_error,
        "assembly": assembly_view(cfg.ledger),
    }
