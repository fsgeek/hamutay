"""take_position and convene, written to the ledger DURING the tool call (spec §6)."""
from __future__ import annotations

from datetime import datetime, timedelta

from hamutay.events import WakeContext

from .binding import AssemblyBinding
from .convene import convene
from .ledger import Ledger, parse_instant
from .records import build_late_position, build_position, closing_id_for, reduce

STORE_LOCK_WINDOW_S = 2.0


class PositionRefused(RuntimeError):
    pass


def record_position(ledger: Ledger, *, binding: AssemblyBinding, wake: WakeContext, cycle: int, record_id,
                    question_id: str, stance: str, reasons: str | None, now: datetime) -> dict:
    with ledger.try_locked(STORE_LOCK_WINDOW_S):
        view = reduce(ledger.read_unlocked())
        q = view.questions.get(question_id)
        if q is None:
            raise PositionRefused(f"unknown question {question_id}")
        if binding.door not in q["members"]:
            raise PositionRefused(f"{binding.door} is not a member of question {question_id}")
        pos = build_position(question=q, member=binding.door, cycle=cycle, record_id=record_id,
                             event_id=wake.event_id, run_id=wake.run_id, wake_started_at=wake.started_at,
                             stance=stance, reasons=reasons, events_path=binding.member.events)
        if question_id in view.closings:
            ledger.append_unlocked(build_late_position(pos, closing_id_for(question_id)))
            raise PositionRefused(f"question {question_id} is closed; recorded as a late position, not tallied")
        if parse_instant(wake.started_at) >= parse_instant(q["closes_at"]):
            raise PositionRefused(f"this wake began after the question closed at {q['closes_at']}")
        return ledger.append_unlocked(pos)


def record_convene(ledger: Ledger, *, binding: AssemblyBinding, text: str, closes_in: timedelta,
                   now: datetime) -> dict:
    return convene(ledger, binding.members, convener=f"door:{binding.door}", text=text,
                   closes_in=closes_in, now=now)
