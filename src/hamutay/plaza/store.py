"""The recipient's store, through one wrapper that names every failure StoreUnavailable (spec §6)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hamutay.assembly.ledger import parse_instant
from hamutay.events import EventStore, LeaseGateRequired, StoreUnavailable, quiet_declaration_for_latest_wake

STORE_LOCK_WINDOW_S = 2.0


def land(path: Path, event: dict, *, timeout_s: float = STORE_LOCK_WINDOW_S) -> bool:
    """True if appended now, False if already present. Raises only StoreUnavailable."""
    try:
        return EventStore(path).append_if_absent(event, timeout_s=timeout_s)
    except StoreUnavailable:
        raise
    except (OSError, LeaseGateRequired) as e:
        raise StoreUnavailable(f"{path}: {type(e).__name__}: {e}") from e


def recipient_quiet_until(path: Path) -> str | None:
    """The recipient's last completed wake's timed quiet, if still in force and no wake is running; else None."""
    try:
        records = EventStore(path).try_read_records(timeout_s=0.5)
    except (StoreUnavailable, OSError, LeaseGateRequired):
        return None
    latest: dict[str, dict] = {}
    for r in records:
        if r.get("record_type") == "event_status":
            latest[r["event_id"]] = r
    # quiet_declaration_for_latest_wake (via latest_wake_outcome) only looks at
    # terminal statuses (completed/failed); a running wake is invisible to it,
    # so without this guard a running wake would return the PRIOR wake's
    # (stale) declaration instead of "no declaration is in force right now".
    if any(r.get("status") == "running" for r in latest.values()):
        return None
    decl = quiet_declaration_for_latest_wake(records)
    until = (decl or {}).get("until")
    if not until:
        return None
    try:
        dt = parse_instant(until)
    except ValueError:
        return None
    if dt <= datetime.now(timezone.utc):
        return None
    return until
