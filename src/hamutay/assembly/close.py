"""Closing (spec §7 steps 1–8) and the activation derivation."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from hamutay.events import EventStore, StoreUnavailable

from .ledger import Ledger, iso, parse_instant
from .records import (
    OBJECTIONS, View, build_procedure, child_question_id, closing_event_id, closing_id_for,
    quorum_for,
)
from .rule import apply_caps, consent_v0

GRACE = timedelta(minutes=60)
STORE_LOCK_WINDOW_S = 2.0


def _read_store(path: str, open_store) -> list[dict] | None:
    try:
        return open_store(Path(path)).try_read_records(timeout_s=STORE_LOCK_WINDOW_S)
    except StoreUnavailable:
        return None


def _latest_status(records: list[dict], event_id: str) -> dict | None:
    latest = None
    for r in records:
        if r.get("record_type") == "event_status" and r.get("event_id") == event_id:
            latest = r
    return latest


def _completed_index(records: list[dict]) -> dict[str, dict]:
    """result_record_id -> completed row (with its running row's started_at joined)."""
    started = {}
    for r in records:
        if r.get("record_type") == "event_status" and r.get("status") == "running":
            started[(r.get("event_id"), r.get("run_id"))] = r.get("started_at")
    out = {}
    for r in records:
        if r.get("record_type") == "event_status" and r.get("status") == "completed":
            row = dict(r); row["_started_at"] = started.get((r.get("event_id"), r.get("run_id")))
            out[str(r.get("result_record_id"))] = row
    return out


def eligible_positions(view: View, lineage_id: str, stores: dict[str, list[dict] | None],
                       members: list[str]) -> list[dict]:
    out = []
    for p in view.positions_for_lineage(lineage_id):
        door = p["member"].removeprefix("door:")
        if door not in members:
            out.append({"record": p, "eligible": False}); continue
        recs = stores.get(door)
        if recs is None:
            out.append({"record": p, "eligible": None}); continue
        c = _completed_index(recs).get(p["record_id"])
        ok = bool(c) and c.get("event_id") == p["event_id"] and c.get("run_id") == p["run_id"] \
            and c.get("_started_at") == p["wake_started_at"]
        out.append({"record": p, "eligible": ok})
    return out


def active_positions(elig: list[dict], members: list[str]) -> dict[str, dict | None]:
    active: dict[str, dict | None] = {m: None for m in members}
    for e in elig:
        if e["eligible"] is not True:
            continue
        door = e["record"]["member"].removeprefix("door:")
        if active.get(door) is None or e["record"]["seq"] > active[door]["seq"]:
            active[door] = e["record"]
    return active


def absence_for(view: View, q: dict, door: str, recs: list[dict] | None) -> dict:
    truth = view.delivery_truth("question", q["question_id"], door)
    m = f"door:{door}"
    if truth["state"] == "store_unreadable" or recs is None:
        return {"member": m, "reason": "store_unreadable", "detail": truth.get("detail")}
    if truth["state"] != "landed":
        return {"member": m, "reason": "not_delivered", "detail": {"state": truth["state"]}}
    st = _latest_status(recs, truth["event_id"])
    if st is None:
        return {"member": m, "reason": "not_delivered", "detail": {"landed_but_absent_from_store": True}}
    status = st.get("status")
    if status == "expired" and (st.get("detail") or {}).get("reason") == "skipped_by_quiet":
        return {"member": m, "reason": "skipped_by_quiet", "detail": st.get("detail")}
    if status == "pending":
        rest = [r for r in recs if r.get("record_type") == "heartbeat_status"]
        return {"member": m, "reason": "pending_at_close",
                "detail": {"not_before": st.get("not_before"), "latest_heartbeat_status": rest[-1] if rest else None}}
    if status == "running":
        return {"member": m, "reason": "running_at_close", "detail": {"run_id": st.get("run_id")}}
    if status in ("expired", "failed", "suppressed"):
        return {"member": m, "reason": status, "detail": {k: st.get(k) for k in ("error", "detail") if st.get(k)}}
    if status == "completed":
        return {"member": m, "reason": "completed_without_position",
                "detail": {"record_id": st.get("result_record_id")}}
    return {"member": m, "reason": "not_delivered", "detail": {"status": status}}


def try_close(ledger: Ledger, view: View, q: dict, *, now: datetime, actor: str, open_store=EventStore) -> dict | None:
    qid = q["question_id"]
    if qid in view.closings:
        return None
    closes_at = parse_instant(q["closes_at"])
    withdrawn = view.withdrawal_for(qid) is not None
    if now < closes_at and not withdrawn:
        return None
    members = list(q["members"].keys())
    past_grace = now >= closes_at + GRACE
    # step 1: offered
    not_offered, unreadable_wait = [], False
    for d in members:
        t = view.delivery_truth("question", qid, d)
        if t["state"] == "landed" and t["landed_at"] and parse_instant(t["landed_at"]) < closes_at:
            continue
        not_offered.append(d)
        if t["state"] == "store_unreadable":
            unreadable_wait = True
    if unreadable_wait and not past_grace and not withdrawn:
        return None
    # step 2: running or unknown
    stores: dict[str, list[dict] | None] = {}
    running_at_cutoff, unknown_at_cutoff = [], []
    for d in members:
        recs = _read_store(q["members"][d]["events"], open_store)
        stores[d] = recs
        if recs is None:
            if not past_grace and not withdrawn:
                return None
            unknown_at_cutoff.append(d); continue
        for r in recs:
            if r.get("record_type") == "event_status" and r.get("status") == "running":
                if _latest_status(recs, r["event_id"]) is r and r.get("started_at") \
                        and parse_instant(r["started_at"]) < closes_at:
                    if not past_grace and not withdrawn:
                        return None
                    if d not in running_at_cutoff:
                        running_at_cutoff.append(d)
    # step 3: tally
    elig = eligible_positions(view, q["lineage_id"], stores, members)
    active = active_positions(elig, members)
    stances = {d: (p["stance"] if p else None) for d, p in active.items()}
    quorum = quorum_for(q["members"], q["governing"])
    max_rounds = int(q["governing"].get("max_rounds", 3))
    if withdrawn:
        outcome, trace, cap = "withdrawn", "withdrawn by the convener", ""
    else:
        outcome, trace = consent_v0(stances, members=members, round_n=q["round"], max_rounds=max_rounds, quorum=quorum)
        outcome, cap = apply_caps(outcome, round_n=q["round"], max_rounds=max_rounds, not_offered=not_offered,
                                  running_at_cutoff=running_at_cutoff, unknown_at_cutoff=unknown_at_cutoff)
    # step 4: the Empty Chair
    absent = [absence_for(view, q, d, stores[d]) for d in members if active[d] is None]
    # step 6: the child, embedded
    next_q = None
    if outcome == "extended":
        duration = closes_at - parse_instant(q["opened_at"])
        next_q = {"question_id": child_question_id(q["lineage_id"], q["round"] + 1), "round": q["round"] + 1,
                  "opened_at": iso(now), "closes_at": iso(now + duration), "text": q["text"],
                  "proposal": q["proposal"], "governing": q["governing"], "members": q["members"]}
    cid = closing_id_for(qid)
    closing = {"record_type": "closing", "closing_id": cid, "question_id": qid, "lineage_id": q["lineage_id"],
               "round": q["round"], "outcome": outcome, "governing": q["governing"],
               "provisional": q["governing"].get("procedure_id") is None,
               "proposal": q["proposal"], "proposal_sha256": q["proposal"]["sha256"],
               "tally": {"eligible_members": members, "quorum": quorum,
                         "active": {d: (p["position_id"] if p else None) for d, p in active.items()},
                         "objections": sorted(d for d, s in stances.items() if s in OBJECTIONS),
                         "assents": sorted(d for d, s in stances.items() if s == "assent"),
                         "abstentions": sorted(d for d, s in stances.items() if s == "abstain"),
                         "spoke": sum(1 for s in stances.values() if s is not None),
                         "not_offered": not_offered, "running_at_cutoff": running_at_cutoff,
                         "unknown_at_cutoff": unknown_at_cutoff, "trace": trace, "cap": cap},
               "positions": elig, "testimony": view.testimony_for_lineage(q["lineage_id"]), "absent": absent,
               "next_question": next_q, "closed_by": actor, "closed_at": iso(now),
               "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in members}}
    return ledger.append_unlocked(closing)


def derive_activations(ledger: Ledger, view: View) -> list[dict]:
    out = []
    for c in view.missing_activations():
        pid = c["proposal"]["procedure_id"]
        rows = view.procedures.get(pid) or []
        prov = next((r for r in reversed(rows) if r.get("status") == "provisional"), None)
        if prov is None:
            continue
        status = "active" if prov["payload_sha256"] == c["proposal"]["sha256"] else "rejected"
        rec = build_procedure(prov["payload"], prov["artifact"], status=status, procedure_id=pid,
                              version=prov["version"], proposed_by_question_id=prov.get("proposed_by_question_id"),
                              activated_by_closing_id=c["closing_id"])
        if status == "rejected":
            rec["detail"] = {"expected": c["proposal"]["sha256"], "found": prov["payload_sha256"]}
        out.append(ledger.append_unlocked(rec))
    return out
