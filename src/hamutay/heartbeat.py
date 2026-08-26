"""Heartbeat: the always-on daemon that gives the event loop wall-clock life.

Spec: docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md
The log is the life; the process is weather. Boot always runs recovery.
"""
from __future__ import annotations

from hamutay.events import (
    EVENT_TYPE_REFLECTION,
    EventStore,
    utc_now_iso,
)


def recover_orphaned_running(store: EventStore) -> list[dict]:
    """Re-pend events whose latest status is a claim that never terminalized."""
    records = store.read_records()
    latest = store.latest_by_event_id()
    recovered = []
    for event_id, last in latest.items():
        if last.get("status") != "running":
            continue
        original = None
        for record in records:
            if (
                record.get("record_type") == "event_status"
                and record.get("event_id") == event_id
                and record.get("status") == "pending"
            ):
                original = record
        if original is None:
            continue
        repend = dict(original)
        repend["status"] = "pending"
        repend["recovered_by"] = "boot_recovery"
        repend["recovered_at"] = utc_now_iso()
        repend["recovered_from_run_id"] = last.get("run_id")
        store.append(repend)
        recovered.append(repend)
    return recovered


def recover_lost_continuations(store: EventStore) -> list[dict]:
    """Materialize continuations lost in a completed/continuation crash gap.

    append_completed_atomic narrows this window to a single write syscall,
    but power loss can still split it, and older logs predate the atomic
    path entirely. This recovery therefore applies to all log versions.
    The content is unrecoverable; the replacement event says so.
    """
    records = store.read_records()
    known = {
        record.get("event_id")
        for record in records
        if record.get("record_type") == "event_status"
    }
    recovered = []
    for record in records:
        if record.get("record_type") != "event_status":
            continue
        if record.get("status") != "completed":
            continue
        if not record.get("auto_continuation_appended"):
            continue
        lost_id = record.get("auto_continuation_event_id")
        if not lost_id or lost_id in known:
            continue
        replacement = {
            "record_type": "event_status",
            "event_id": lost_id,
            "event_type": EVENT_TYPE_REFLECTION,
            "status": "pending",
            "created_at": utc_now_iso(),
            "recovered_by": "boot_recovery",
            "recovered_at": utc_now_iso(),
            "recovered_from_completed_record": record.get("result_record_id"),
            "declared_loss": (
                "The content of this continuation was lost in a crash between "
                "the completed append and the continuation append. Only its "
                "id and the fact of its intent survive."
            ),
            "purpose": (
                "Recover a lost continuation. A previous wake bound a "
                "continuation whose content did not survive a crash. Consult "
                "your current state for the wake recorded at result_record_id "
                f"{record.get('result_record_id')} and either re-derive the "
                "intended continuation or record that it is no longer needed."
            ),
        }
        store.append(replacement)
        known.add(lost_id)
        recovered.append(replacement)
    return recovered
