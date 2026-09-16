"""Record builders, deterministic ids, and the reducer (spec §2)."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from .ledger import iso, parse_instant

STANCES = ("assent", "dissent", "abstain", "defer")
OBJECTIONS = ("dissent", "defer")
BOOTSTRAP_GOVERNING = {"procedure_id": None, "rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)"}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def payload_sha256(payload: dict) -> str:
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def closing_id_for(question_id: str) -> str:
    return str(uuid5(UUID(question_id), "closing"))


def child_question_id(lineage_id: str, round_n: int) -> str:
    return str(uuid5(UUID(lineage_id), f"round-{round_n}"))


def closing_event_id(closing_id: str, door: str) -> str:
    return str(uuid5(UUID(closing_id), door))


def quorum_for(members: dict, governing: dict) -> int:
    q = governing.get("quorum", "ceil(half)")
    return int(q) if isinstance(q, int) else math.ceil(len(members) / 2)


def _instant(s: str) -> str:
    return iso(parse_instant(s))


def build_procedure(payload: dict, artifact: dict, *, status: str, proposed_by_question_id=None,
                    activated_by_closing_id=None, procedure_id=None, version=None) -> dict:
    if status not in ("provisional", "active", "rejected"):
        raise ValueError(f"bad procedure status {status!r}")
    return {"record_type": "procedure", "procedure_id": procedure_id or str(uuid4()),
            "version": version, "status": status, "payload": payload,
            "payload_sha256": payload_sha256(payload), "artifact": artifact,
            "proposed_by_question_id": proposed_by_question_id,
            "activated_by_closing_id": activated_by_closing_id}


def build_question(*, text, convener, opened_at, closes_at, governing, members_snapshot, proposal,
                   lineage_id=None, question_id=None, round_n=1, parent_question_id=None) -> dict:
    qid = question_id or str(uuid4())
    if parse_instant(closes_at) <= parse_instant(opened_at):
        raise ValueError("closes_at must be after opened_at")
    return {"record_type": "question", "question_id": qid, "lineage_id": lineage_id or qid,
            "round": round_n, "parent_question_id": parent_question_id, "convener": str(convener),
            "text": str(text), "proposal": dict(proposal), "opened_at": _instant(opened_at),
            "closes_at": _instant(closes_at), "governing": dict(governing),
            "members": {n: dict(m) for n, m in members_snapshot.items()},
            "delivery": {n: {"event_id": str(uuid4())} for n in members_snapshot}}


def build_position(*, question, member, cycle, record_id, event_id, run_id, wake_started_at,
                   stance, reasons, events_path) -> dict:
    if stance not in STANCES:
        raise ValueError(f"stance must be one of {STANCES}")
    if member not in question["members"]:
        raise ValueError(f"{member} is not in this question's members")
    return {"record_type": "position", "position_id": str(uuid4()), "lineage_id": question["lineage_id"],
            "question_id": question["question_id"], "member": f"door:{member}", "cycle": int(cycle),
            "record_id": str(record_id), "event_id": str(event_id), "run_id": str(run_id),
            "wake_started_at": _instant(wake_started_at), "events_path": str(events_path),
            "stance": stance, "reasons": (str(reasons) if reasons else None)}


def build_late_position(position: dict, closing_id: str) -> dict:
    late = {k: v for k, v in position.items() if k not in ("seq", "created_at")}
    late["record_type"] = "late_position"; late["closing_id"] = closing_id
    return late


def build_testimony(*, question, by, text) -> dict:
    if by not in ("tony", "custodian"):
        raise ValueError("testimony is tony's or the custodian's")
    return {"record_type": "testimony", "testimony_id": str(uuid4()), "lineage_id": question["lineage_id"],
            "question_id": question["question_id"], "by": by, "text": str(text)}


def build_withdrawal(*, question_id, by, reasons) -> dict:
    return {"record_type": "withdrawal", "question_id": question_id, "by": by,
            "reasons": (str(reasons) if reasons else None)}


def build_delivery(*, for_, id_, door, event_id, state, landed_at=None, detail=None) -> dict:
    if for_ not in ("question", "closing") or state not in ("landed", "store_unreadable", "cancelled"):
        raise ValueError("bad delivery")
    return {"record_type": "delivery", "for": for_, "id": id_, "door": door, "event_id": event_id,
            "state": state, "landed_at": (_instant(landed_at) if landed_at else None), "detail": detail}


def build_execution(*, closing, by, outcome, what, reasons) -> dict:
    if closing.get("outcome") != "assented":
        raise ValueError("execution references an assented closing only")
    if outcome not in ("done", "declined") or (outcome == "declined" and not reasons):
        raise ValueError("outcome done|declined; declined needs reasons")
    return {"record_type": "execution", "execution_id": str(uuid4()), "closing_id": closing["closing_id"],
            "question_id": closing["question_id"], "proposal_sha256": closing["proposal_sha256"],
            "by": by, "outcome": outcome, "what": str(what), "reasons": (str(reasons) if reasons else None)}


@dataclass
class View:
    records: list[dict]
    procedures: dict[str, list[dict]] = field(default_factory=dict)
    questions: dict[str, dict] = field(default_factory=dict)
    closings: dict[str, dict] = field(default_factory=dict)          # by question_id
    closings_by_id: dict[str, dict] = field(default_factory=dict)
    deliveries: dict[tuple, dict] = field(default_factory=dict)      # (for, id, door) -> latest
    positions: list[dict] = field(default_factory=list)
    testimony: list[dict] = field(default_factory=list)
    withdrawals: dict[str, dict] = field(default_factory=dict)
    executions: dict[str, list[dict]] = field(default_factory=dict)

    @property
    def active_procedure(self) -> dict | None:
        actives = [r for rs in self.procedures.values() for r in rs if r.get("status") == "active"]
        return max(actives, key=lambda r: r["seq"]) if actives else None

    def governing_for_new_question(self) -> dict:
        act = self.active_procedure
        if act is None:
            return dict(BOOTSTRAP_GOVERNING)
        p = act["payload"]
        return {"procedure_id": act["procedure_id"], "rule": p.get("rule", "consent-v0"),
                "max_rounds": p.get("max_rounds", 3), "quorum": p.get("quorum", "ceil(half)")}

    def next_version(self) -> int:
        return max((int(r.get("version") or 0) for rs in self.procedures.values() for r in rs), default=0) + 1

    def open_questions(self) -> list[dict]:
        return [q for q in self.questions.values() if q["question_id"] not in self.closings]

    def open_lineage_for(self, convener: str) -> dict | None:
        for q in self.open_questions():
            if q["convener"] == convener:
                return q
        return None

    def snapshots_of_open_questions(self) -> list[dict]:
        return [q["members"] for q in self.open_questions()]

    def delivery_truth(self, for_: str, id_: str, door: str) -> dict:
        if for_ == "question":
            q = self.questions.get(id_)
            if q is not None and q.get("derived_from_closing"):
                cid = q["derived_from_closing"]
                truth = self.delivery_truth("closing", cid, door)
                truth["event_id"] = closing_event_id(cid, door)
                return truth
            planned = (q or {}).get("delivery", {}).get(door, {})
        else:
            planned = self.closings_by_id.get(id_, {}).get("delivery", {}).get(door, {})
        row = self.deliveries.get((for_, id_, door))
        if row is None:
            return {"state": "planned", "landed_at": None, "event_id": planned.get("event_id"), "detail": None}
        return {"state": row["state"], "landed_at": row.get("landed_at"),
                "event_id": row.get("event_id"), "detail": row.get("detail")}

    def positions_for_lineage(self, lineage_id: str) -> list[dict]:
        return [p for p in self.positions if p["lineage_id"] == lineage_id]

    def testimony_for_lineage(self, lineage_id: str) -> list[dict]:
        return [t for t in self.testimony if t["lineage_id"] == lineage_id]

    def withdrawal_for(self, question_id: str) -> dict | None:
        return self.withdrawals.get(question_id)

    def executions_for(self, closing_id: str) -> list[dict]:
        return list(self.executions.get(closing_id, []))

    def outstanding_deliveries(self) -> list[tuple]:
        out = []
        for q in self.questions.values():
            if q.get("derived_from_closing"):
                continue
            closed = q["question_id"] in self.closings
            for door in q["members"]:
                st = self.delivery_truth("question", q["question_id"], door)["state"]
                if st in ("planned", "store_unreadable"):
                    out.append(("question", q["question_id"], door, closed))
        for c in self.closings_by_id.values():
            for door in c["delivery"]:
                st = self.delivery_truth("closing", c["closing_id"], door)["state"]
                if st in ("planned", "store_unreadable"):
                    out.append(("closing", c["closing_id"], door, False))
        return out

    def missing_activations(self) -> list[dict]:
        out = []
        for c in self.closings_by_id.values():
            if c["outcome"] != "assented":
                continue
            proposal = c.get("proposal")
            if proposal is None:
                q = self.questions.get(c["question_id"])
                if q is None:
                    continue
                proposal = q["proposal"]
            if proposal.get("kind") != "procedure":
                continue
            pid = proposal["procedure_id"]
            done = any(r.get("activated_by_closing_id") == c["closing_id"]
                       for r in self.procedures.get(pid, []))
            if not done:
                out.append(c)
        return out

    def next_deadline(self) -> datetime | None:
        ds = [parse_instant(q["closes_at"]) for q in self.open_questions()]
        return min(ds) if ds else None

    def quiescent(self, now: datetime) -> bool:
        if self.outstanding_deliveries() or self.missing_activations():
            return False
        for q in self.open_questions():
            if self.withdrawal_for(q["question_id"]) is not None:
                return False
            if parse_instant(q["closes_at"]) <= now:
                return False
        return True


def reduce(records: list[dict]) -> View:
    records = sorted(records, key=lambda r: int(r.get("seq", 0)))
    v = View(records=records)
    for r in records:
        t = r.get("record_type")
        if t == "procedure":
            v.procedures.setdefault(r["procedure_id"], []).append(r)
        elif t == "question":
            v.questions[r["question_id"]] = r
        elif t == "closing":
            v.closings[r["question_id"]] = r
            v.closings_by_id[r["closing_id"]] = r
            nq = r.get("next_question")
            if nq:
                v.questions[nq["question_id"]] = {
                    "record_type": "question", **nq, "lineage_id": r["lineage_id"],
                    "parent_question_id": r["question_id"], "convener": v.questions[r["question_id"]]["convener"]
                    if r["question_id"] in v.questions else None,
                    "derived_from_closing": r["closing_id"], "seq": r["seq"], "created_at": r["created_at"],
                    "delivery": {d: {"event_id": closing_event_id(r["closing_id"], d)} for d in nq["members"]},
                }
        elif t == "delivery":
            v.deliveries[(r["for"], r["id"], r["door"])] = r
        elif t == "position":
            v.positions.append(r)
        elif t == "testimony":
            v.testimony.append(r)
        elif t == "withdrawal":
            v.withdrawals.setdefault(r["question_id"], r)
        elif t == "execution":
            v.executions.setdefault(r["closing_id"], []).append(r)
    return v
