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
from hamutay.plaza.read import read_rows

WEEK = timedelta(days=7)
EVENT_FIELDS = ("event_id", "event_type", "status", "run_id", "sender", "purpose",
                "created_at", "started_at", "completed_at", "failed_at", "expired_at",
                "wake_cycle", "error_type", "error")


def _tolerant_jsonl(path: Path) -> list[dict]:
    """Every parseable line; a torn or malformed line is skipped (the viewer never repairs or fails)."""
    if not path.exists():
        return []
    out = []
    for raw in path.read_bytes().split(b"\n"):
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


def door_vitals(name: str, events_path: Path, now: datetime) -> dict:
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
    quiet = [r for r in records if r.get("record_type") == "quiet_declaration"]
    billing = _tolerant_jsonl(Path(str(events_path).replace(".events.jsonl", ".billing.jsonl")))
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
        "quiet": ({k: quiet[-1].get(k) for k in ("reason", "until", "created_at", "declared_by_cycle")}
                  if quiet else None),
    }


def assembly_view(ledger: Path) -> list[dict]:
    records = _tolerant_jsonl(ledger)
    questions: dict[str, dict] = {}
    order: list[str] = []
    for r in records:
        t = r.get("record_type")
        if t == "question":
            qid = str(r.get("question_id"))
            questions[qid] = {"question_id": qid, "lineage_id": r.get("lineage_id"), "seq": r.get("seq"),
                              "round": r.get("round"), "convener": r.get("convener"), "text": r.get("text"),
                              "opened_at": r.get("opened_at"), "closes_at": r.get("closes_at"),
                              "positions": [], "testimony": [], "closing": None, "execution": None}
            order.append(qid)
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
            plaza = read_rows(cfg)
        except Exception as e:  # noqa: BLE001 -- shown on the page, never raised to the browser as a 500
            plaza_error = f"{type(e).__name__}: {e}"
    return {
        "at": now.isoformat(),
        "doors": [door_vitals(name, m.events, now) for name, m in sorted(cfg.members.items())],
        "guests": list(cfg.guests or ()),
        "plaza": [{k: m.get(k) for k in ("seq", "from", "to", "text", "sent_at", "truth")} for m in plaza],
        "plaza_error": plaza_error,
        "assembly": assembly_view(cfg.ledger),
    }
