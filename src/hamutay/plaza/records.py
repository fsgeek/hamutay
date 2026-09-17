"""Plaza records, the strict validator, and the reduced view (spec §2)."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from hamutay.assembly.ledger import LedgerMalformed, parse_instant

from .ids import HUMANS, canonical_to, delivery_event_id, door_name, is_door, resident_key

SEND_CAP = 48
MAX_TEXT_CHARS = 8000
ACTOR_RE = re.compile(r"^(door:[a-z0-9_-]+|tony|custodian)$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

MESSAGE_FIELDS = {"record_type", "seq", "created_at", "message_id", "idempotency_key", "from", "via",
                  "to", "text", "sent_at", "delivery", "wake"}
DELIVERY_FIELDS = {"record_type", "seq", "created_at", "message_id", "door", "event_id", "state",
                   "landed_at", "detail"}
DELIVERY_SUB = {"door", "events_path", "event_id", "members_digest"}
WAKE_SUB = {"cycle", "record_id", "event_id", "run_id", "started_at"}


def build_message(*, actor: str, via: str, to: str, text: str, sent_at: str, idempotency_key: str,
                  delivery: dict | None, wake: dict | None) -> dict:
    to = canonical_to(to)
    message_id = str(uuid.uuid4())
    if delivery is not None:
        delivery = dict(delivery)
        delivery["event_id"] = delivery_event_id(message_id, door_name(to))
    return {"record_type": "message", "message_id": message_id, "idempotency_key": str(idempotency_key),
            "from": actor, "via": via, "to": to, "text": text, "sent_at": sent_at,
            "delivery": delivery, "wake": wake}


def build_delivery(*, message: dict, state: str, landed_at: str | None, detail: dict | None) -> dict:
    d = message["delivery"]
    return {"record_type": "delivery", "message_id": message["message_id"], "door": d["door"],
            "event_id": d["event_id"], "state": state, "landed_at": landed_at, "detail": detail}


def _bad(msg: str) -> LedgerMalformed:
    return LedgerMalformed(f"plaza: {msg}")


def _uuid(s, version: int | None, what: str) -> None:
    try:
        u = uuid.UUID(str(s))
    except (ValueError, TypeError, AttributeError):
        raise _bad(f"{what} is not a UUID: {s!r}")
    if version is not None and u.version != version:
        raise _bad(f"{what} is not a version-{version} UUID: {s!r}")


def _instant(s, what: str) -> datetime:
    try:
        return parse_instant(s)
    except (ValueError, TypeError):
        raise _bad(f"{what} is not a timezone-bearing instant: {s!r}")


def validate_plaza(records: list[dict], line_numbers: list[int]) -> None:
    """Raise LedgerMalformed on anything the writers could not have produced."""
    if not isinstance(records, list) or not isinstance(line_numbers, list) \
            or len(records) != len(line_numbers):
        raise _bad("line numbers do not match records")
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    messages: dict[str, dict] = {}
    for r, line in zip(records, line_numbers):
        if not isinstance(r, dict):
            raise _bad(f"line {line}: not an object")
        if r.get("seq") != line:
            raise _bad(f"line {line}: seq {r.get('seq')!r} is not the line number")
        _instant(r.get("created_at"), f"line {line} created_at")
        rt = r.get("record_type")
        if rt == "message":
            if set(r) != MESSAGE_FIELDS:
                raise _bad(f"line {line}: message fields are {sorted(set(r) ^ MESSAGE_FIELDS)} off")
            _uuid(r["message_id"], 4, f"line {line} message_id")
            _uuid(r["idempotency_key"], 5, f"line {line} idempotency_key")
            actor, via, to = r["from"], r["via"], r["to"]
            if not (is_door(actor) or actor in HUMANS):
                raise _bad(f"line {line}: bad actor {actor!r}")
            if to != "plaza" and not is_door(to):
                raise _bad(f"line {line}: bad to {to!r}")
            if to == actor:
                raise _bad(f"line {line}: a door cannot address itself")
            if via not in ("tool", "cli"):
                raise _bad(f"line {line}: bad via {via!r}")
            wake = r["wake"]
            if via == "tool" and not (is_door(actor) and isinstance(wake, dict)):
                raise _bad(f"line {line}: via tool needs a door actor and a wake")
            if via == "cli" and not (actor in HUMANS and wake is None):
                raise _bad(f"line {line}: via cli needs a human actor and no wake")
            if wake is not None:
                if set(wake) != WAKE_SUB or not isinstance(wake["cycle"], int):
                    raise _bad(f"line {line}: bad wake")
                _uuid(wake["record_id"], None, f"line {line} wake.record_id")
                _uuid(wake["event_id"], None, f"line {line} wake.event_id")
                _uuid(wake["run_id"], None, f"line {line} wake.run_id")
                _instant(wake["started_at"], f"line {line} wake.started_at")
                if r["idempotency_key"] != resident_key(wake["event_id"], to, r["text"]):
                    raise _bad(f"line {line}: idempotency_key is not the framework's")
            text = r["text"]
            if not isinstance(text, str) or not text or len(text) > MAX_TEXT_CHARS:
                raise _bad(f"line {line}: text empty or over {MAX_TEXT_CHARS}")
            _instant(r["sent_at"], f"line {line} sent_at")
            d = r["delivery"]
            if to == "plaza":
                if d is not None:
                    raise _bad(f"line {line}: a post carries no delivery")
            else:
                if not isinstance(d, dict) or set(d) != DELIVERY_SUB:
                    raise _bad(f"line {line}: bad delivery block")
                if d["door"] != door_name(to):
                    raise _bad(f"line {line}: delivery.door is not the addressee")
                if not (isinstance(d["events_path"], str) and d["events_path"].startswith("/")):
                    raise _bad(f"line {line}: delivery.events_path is not absolute")
                if not (isinstance(d["members_digest"], str) and HEX64.match(d["members_digest"])):
                    raise _bad(f"line {line}: delivery.members_digest is not sha256 hex")
                _uuid(d["event_id"], 5, f"line {line} delivery.event_id")
                if d["event_id"] != delivery_event_id(r["message_id"], d["door"]):
                    raise _bad(f"line {line}: delivery.event_id is not derived from the message")
            if r["message_id"] in seen_ids:
                raise _bad(f"line {line}: second message_id {r['message_id']}")
            if r["idempotency_key"] in seen_keys:
                raise _bad(f"line {line}: second idempotency_key {r['idempotency_key']}")
            seen_ids.add(r["message_id"]); seen_keys.add(r["idempotency_key"])
            messages[r["message_id"]] = r
        elif rt == "delivery":
            if set(r) != DELIVERY_FIELDS:
                raise _bad(f"line {line}: delivery fields are {sorted(set(r) ^ DELIVERY_FIELDS)} off")
            m = messages.get(r["message_id"])
            if m is None or m["delivery"] is None:
                raise _bad(f"line {line}: delivery for an unknown or undirected message")
            if r["door"] != m["delivery"]["door"] or r["event_id"] != m["delivery"]["event_id"]:
                raise _bad(f"line {line}: delivery door/event_id differ from the message's")
            state, landed_at, detail = r["state"], r["landed_at"], r["detail"]
            if state == "landed":
                if landed_at is None or detail is not None:
                    raise _bad(f"line {line}: landed needs landed_at and no detail")
                _instant(landed_at, f"line {line} landed_at")
            elif state == "store_unreadable":
                if landed_at is not None or not (isinstance(detail, dict) and isinstance(detail.get("error"), str)
                                                 and detail["error"]):
                    raise _bad(f"line {line}: store_unreadable needs detail.error and no landed_at")
            else:
                raise _bad(f"line {line}: bad delivery state {state!r}")
        else:
            raise _bad(f"line {line}: unknown record_type {rt!r}")


@dataclass
class View:
    messages: list[dict] = field(default_factory=list)
    by_key: dict[str, dict] = field(default_factory=dict)
    by_id: dict[str, dict] = field(default_factory=dict)
    _deliveries: dict[str, dict] = field(default_factory=dict)   # latest per message_id

    def delivery_truth(self, message_id: str) -> dict:
        d = self._deliveries.get(message_id)
        if d is None:
            m = self.by_id[message_id]
            return {"state": "planned", "event_id": m["delivery"]["event_id"], "landed_at": None, "detail": None}
        return {"state": d["state"], "event_id": d["event_id"], "landed_at": d["landed_at"], "detail": d["detail"]}

    def undelivered(self) -> list[dict]:
        return [m for m in self.messages if m["delivery"] is not None
                and self.delivery_truth(m["message_id"])["state"] != "landed"]

    def sent_today(self, actor: str, day: date) -> int:
        n = 0
        for m in self.messages:
            if m["from"] == actor and m["to"] != "plaza" \
                    and parse_instant(m["sent_at"]).astimezone(timezone.utc).date() == day:
                n += 1
        return n

    def visible_since(self, bound: datetime | None, door: str) -> list[dict]:
        me = f"door:{door}"
        out = []
        for m in self.messages:
            if m["from"] == me or m["to"] == me:
                continue
            if bound is not None and parse_instant(m["sent_at"]) < bound:
                continue
            out.append(m)
        return out


def reduce(records: list[dict]) -> View:
    v = View()
    for r in sorted(records, key=lambda r: int(r.get("seq", 0))):
        if r.get("record_type") == "message":
            v.messages.append(r); v.by_key[r["idempotency_key"]] = r; v.by_id[r["message_id"]] = r
        elif r.get("record_type") == "delivery":
            v._deliveries[r["message_id"]] = r
    return v
