"""send_message's one write path, for the tool and the CLI (spec §3)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hamutay.assembly.binding import MembersConfig
from hamutay.assembly.ledger import Ledger, iso
from hamutay.events import StoreUnavailable

from . import store as _store
from .event import inbound_event_for
from .ids import HUMANS, PLAZA_LOCK_WINDOW_S, canonical_to, cli_key, door_name, is_door, resident_key
from .records import MAX_TEXT_CHARS, SEND_CAP, build_delivery, build_message, reduce, validate_plaza


class SendRefused(RuntimeError):
    pass


def _next_utc_midnight(now: datetime) -> datetime:
    u = now.astimezone(timezone.utc)
    return (u + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def send(cfg: MembersConfig, *, actor: str, via: str, to: str, text: str, now: datetime,
         wake: dict | None = None, key: str | None = None, land=_store.land,
         quiet=_store.recipient_quiet_until) -> dict:
    if cfg.plaza is None:
        raise SendRefused("the plaza is not enabled for this house")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-bearing")
    if via == "tool":
        if not (is_door(actor) and isinstance(wake, dict)):
            raise SendRefused("a tool send needs a door actor and a wake")
    elif via == "cli":
        if actor not in HUMANS or wake is not None:
            raise SendRefused("a cli send needs a human actor and no wake")
    else:
        raise SendRefused(f"bad via {via!r}")
    try:
        to = canonical_to(to)
    except ValueError as e:
        raise SendRefused(str(e))
    if to != "plaza" and door_name(to) not in cfg.members:
        raise SendRefused(f"{to} is not a member door")
    if to == actor:
        raise SendRefused("a door cannot address itself")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
        raise SendRefused(f"text must be 1..{MAX_TEXT_CHARS} characters")
    idem = resident_key(wake["event_id"], to, text) if via == "tool" else cli_key(key or str(uuid.uuid4()))

    ledger = Ledger(cfg.plaza)
    with ledger.try_locked(PLAZA_LOCK_WINDOW_S):
        records = ledger.read_unlocked()
        validate_plaza(records, ledger.line_numbers)
        view = reduce(records)
        prior = view.by_key.get(idem)
        if prior is not None:
            return {"sent": True, "message_id": prior["message_id"], "seq": prior["seq"], "to": prior["to"],
                    "delivery": ("post" if prior["to"] == "plaza"
                                 else ("landed" if view.delivery_truth(prior["message_id"])["state"] == "landed"
                                       else "pending")),
                    "duplicate_of_seq": prior["seq"]}
        if via == "tool" and to != "plaza":
            day = now.astimezone(timezone.utc).date()
            if view.sent_today(actor, day) >= SEND_CAP:
                raise SendRefused(f"send cap of {SEND_CAP} directed messages reached for {day}; "
                                  f"lifts at {iso(_next_utc_midnight(now))}")
        sent_at = iso(now)
        delivery = None
        if to != "plaza":
            member = cfg.members[door_name(to)]
            delivery = {"door": member.name, "events_path": str(member.events), "event_id": None,
                        "members_digest": cfg.digest}
        msg = build_message(actor=actor, via=via, to=to, text=text, sent_at=sent_at, idempotency_key=idem,
                            delivery=delivery, wake=wake)
        next_line = (ledger.line_numbers[-1] if ledger.line_numbers else 0) + 1
        validate_plaza(records + [{**msg, "seq": next_line, "created_at": sent_at}], ledger.line_numbers + [next_line])
        msg = ledger.append_unlocked(msg)
        out = {"sent": True, "message_id": msg["message_id"], "seq": msg["seq"], "to": to, "delivery": "post"}
        if delivery is None:
            return out
        path = Path(msg["delivery"]["events_path"])
        try:
            land(path, inbound_event_for(msg))
            ledger.append_unlocked(build_delivery(message=msg, state="landed", landed_at=iso(now), detail=None))
            out["delivery"] = "landed"
        except StoreUnavailable as e:
            ledger.append_unlocked(build_delivery(message=msg, state="store_unreadable", landed_at=None,
                                                  detail={"error": str(e)}))
            out["delivery"] = "pending"
        q = quiet(path) if out["delivery"] == "landed" else None
        if q:
            out["recipient_last_declared_quiet_until"] = q
        return out
