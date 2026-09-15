"""Envelope notes for substrate (GPU lease) rest episodes — implementer's TDD tests.

Spec: docs/superpowers/specs/2026-09-15-gpu-lease-design.md §5 "Envelope notes".

The heartbeat rests when the GPU it runs on is lent to another workload
(reason "substrate_lent") or its lease state is unreadable ("substrate_lease_unreadable").
_rest_episodes groups these by detail.episode_id (generalising the existing
same-day budget-rest grouping); operational_notes_for_event renders a note
for any event whose pending interval overlaps the episode (rule a), and —
for closed substrate episodes rule (a) didn't cover — a one-time notice to
the first event created after the loan closed (rule b), at-least-once.
"""
from datetime import datetime, timedelta, timezone

from hamutay.events import _rest_episodes, operational_notes_for_event

T0 = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)


def hs(status, reason, at, **detail):
    return {
        "record_type": "heartbeat_status",
        "status": status,
        "reason": reason,
        "created_at": at.isoformat(),
        "detail": detail,
    }


def ev(status, at, event_id="e1"):
    return {
        "record_type": "event_status",
        "event_id": event_id,
        "status": status,
        "created_at": at.isoformat(),
    }


LENT = dict(episode_id="L1", holder="yupi", purpose="train")


def test_substrate_episode_bridges_boot_continuation():
    statuses = [
        hs("resting", "substrate_lent", T0, **LENT),
        hs("waking", "boot", T0 + timedelta(minutes=5)),
        hs("resting", "substrate_lent", T0 + timedelta(minutes=5, seconds=1), continuation=True, **LENT),
        hs("waking", "substrate_returning", T0 + timedelta(hours=1), episode_id="L1"),
    ]
    eps = _rest_episodes(statuses, now=T0 + timedelta(hours=2))
    assert len(eps) == 1 and eps[0]["end"] == T0 + timedelta(hours=1) and eps[0]["reason"] == "substrate_lent"


def test_note_for_event_that_waited_through_a_loan():
    records = [
        ev("pending", T0 - timedelta(minutes=10)),
        hs("resting", "substrate_lent", T0, **LENT),
        hs("waking", "substrate_returning", T0 + timedelta(hours=1), episode_id="L1"),
    ]
    notes = operational_notes_for_event(records, records[0], now=T0 + timedelta(hours=1, minutes=1))
    assert len(notes) == 1 and 'holder "yupi"' in notes[0] and "GPU allocated to another workload" in notes[0] and "waited 1h" in notes[0]


def test_rule_b_tells_first_event_after_loan_once():
    records = [
        hs("resting", "substrate_lent", T0, **LENT),
        hs("waking", "substrate_returning", T0 + timedelta(hours=1), episode_id="L1"),
        ev("pending", T0 + timedelta(hours=2), "e2"),
    ]
    notes = operational_notes_for_event(records, records[-1], now=T0 + timedelta(hours=2, minutes=1))
    assert len(notes) == 1 and notes[0].startswith("Before this event existed")
    consumed = records + [
        ev("running", T0 + timedelta(hours=2, minutes=1), "e2"),
        ev("completed", T0 + timedelta(hours=2, minutes=2), "e2"),
        ev("pending", T0 + timedelta(hours=3), "e3"),
    ]
    assert operational_notes_for_event(consumed, consumed[-1], now=T0 + timedelta(hours=3, minutes=1)) == []


def test_rule_b_survives_a_failed_first_claim():
    records = [
        hs("resting", "substrate_lent", T0, **LENT),
        hs("waking", "substrate_returning", T0 + timedelta(hours=1), episode_id="L1"),
        ev("pending", T0 + timedelta(hours=2), "e2"),
        ev("running", T0 + timedelta(hours=2, minutes=1), "e2"),
        ev("failed", T0 + timedelta(hours=2, minutes=2), "e2"),
        ev("pending", T0 + timedelta(hours=3), "e3"),
    ]
    notes = operational_notes_for_event(records, records[-1], now=T0 + timedelta(hours=3, minutes=1))
    assert len(notes) == 1 and notes[0].startswith("Before this event existed")


def test_budget_rest_after_event_created_still_gets_no_note():
    records = [
        hs("resting", "daily_budget_reached", T0, day="2026-09-20", cost_usd=1.5, daily_usd=1.5),
        hs("waiting", "scheduled_wake", T0 + timedelta(hours=1)),
        ev("pending", T0 + timedelta(hours=2), "e9"),
    ]
    assert operational_notes_for_event(records, records[-1], now=T0 + timedelta(hours=3)) == []


def test_rule_a_precedes_rule_b_for_same_episode():
    records = [
        ev("pending", T0 - timedelta(minutes=1), "e1"),
        hs("resting", "substrate_lent", T0, **LENT),
        hs("waking", "substrate_returning", T0 + timedelta(hours=1), episode_id="L1"),
    ]
    notes = operational_notes_for_event(records, records[0], now=T0 + timedelta(hours=1, minutes=1))
    assert len(notes) == 1 and not notes[0].startswith("Before")
