"""The durable outbox (spec §7): cancel stale, then land, at most once per store."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from hamutay.events import EventStore, StoreUnavailable, build_inbound_event

from .header import closing_text, event_purpose_for_question
from .ledger import Ledger, iso
from .records import View, build_delivery, closing_event_id

STORE_LOCK_WINDOW_S = 2.0


def _version_of(view: View, governing: dict) -> int | None:
    pid = governing.get("procedure_id")
    if pid is None:
        return None
    rs = view.procedures.get(pid) or []
    return rs[-1].get("version") if rs else None


def _event_for(view: View, for_: str, obj: dict, door: str) -> dict:
    if for_ == "question":
        return build_inbound_event(
            purpose=event_purpose_for_question(obj, version=_version_of(view, obj["governing"])),
            sender="assembly", label=f"assembly:{obj['question_id']}",
            event_id=obj["delivery"][door]["event_id"],
            assembly={"assembly_question_id": obj["question_id"], "expires_at": obj["closes_at"]})
    nq = obj.get("next_question")
    ev = build_inbound_event(
        purpose=closing_text(obj, view, version=_version_of(view, obj["governing"])),
        sender="assembly", label=f"assembly-closing:{obj['question_id']}",
        event_id=closing_event_id(obj["closing_id"], door),
        assembly=({"assembly_question_id": nq["question_id"], "expires_at": nq["closes_at"]} if nq else None))
    if not nq:
        ev["defer_to_declared_quiet"] = True
    return ev


def run_outbox(ledger: Ledger, view: View, *, now: datetime, open_store=EventStore) -> list[dict]:
    """Caller holds the ledger lock. Returns the delivery rows appended."""
    out: list[dict] = []
    for for_, id_, door, closed in view.outstanding_deliveries():
        if for_ == "question" and closed:
            truth = view.delivery_truth(for_, id_, door)
            out.append(ledger.append_unlocked(build_delivery(
                for_=for_, id_=id_, door=door, event_id=truth["event_id"], state="cancelled")))
            continue
        obj = view.questions[id_] if for_ == "question" else view.closings_by_id[id_]
        # a closing carries no `members` of its own; its delivery path comes from the
        # QUESTION's member snapshot, which is frozen for the whole lineage
        path = Path(obj["members"][door]["events"]) if for_ == "question" \
            else Path(view.questions[obj["question_id"]]["members"][door]["events"])
        event = _event_for(view, for_, obj, door)
        try:
            open_store(path).append_if_absent(event, timeout_s=STORE_LOCK_WINDOW_S)
        except StoreUnavailable as e:
            prev = view.delivery_truth(for_, id_, door)
            if prev["state"] == "store_unreadable" and (prev.get("detail") or {}).get("error") == str(e):
                continue                                   # deduplicated; still retried next pass
            out.append(ledger.append_unlocked(build_delivery(
                for_=for_, id_=id_, door=door, event_id=event["event_id"], state="store_unreadable",
                detail={"error": str(e)})))
            continue
        out.append(ledger.append_unlocked(build_delivery(
            for_=for_, id_=id_, door=door, event_id=event["event_id"], state="landed", landed_at=iso(now))))
    return out
