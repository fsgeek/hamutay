"""Heartbeat: the always-on daemon that gives the event loop wall-clock life.

Spec: docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md
The log is the life; the process is weather. Boot always runs recovery.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from hamutay.events import (
    EVENT_TYPE_REFLECTION,
    EventStore,
    run_pending_events,
    summarize_event_log,
    utc_now_iso,
)


def append_heartbeat_status(
    store: EventStore,
    *,
    status: str,
    reason: str,
    detail: dict | None = None,
) -> dict:
    """Record a daemon state transition. Not an event; carries no event_id."""
    record: dict = {
        "record_type": "heartbeat_status",
        "heartbeat_record_id": str(uuid4()),
        "status": str(status),
        "reason": str(reason),
        "created_at": utc_now_iso(),
    }
    if detail is not None:
        record["detail"] = detail
    store.append(record)
    return record


def derive_quiet_reason(records: list[dict]) -> str:
    """v1 heuristic (declared in the spec): expiry beats novelty beats choice."""
    latest: dict[str | None, dict] = {}
    completed_seen = False
    for record in records:
        if record.get("record_type") != "event_status":
            continue
        latest[record.get("event_id")] = record
        if record.get("status") == "completed":
            completed_seen = True
    if any(r.get("status") == "expired" for r in latest.values()):
        return "starved_expired"
    if not completed_seen:
        return "awaiting_first_event"
    return "chosen_quiet"


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


class HeartbeatLoop:
    """Wall-clock life for the event loop. Crash-only: boot always recovers."""

    def __init__(
        self,
        session,
        store: EventStore,
        *,
        poll_interval: float = 30.0,
        batch_limit: int = 10,
        sleep=time.sleep,
        now=None,
        run_pending=run_pending_events,
        summarize=summarize_event_log,
    ):
        self._session = session
        self._store = store
        self._poll_interval = float(poll_interval)
        self._batch_limit = int(batch_limit)
        self._sleep = sleep
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._run_pending = run_pending
        self._summarize = summarize
        self._last_transition: tuple[str, str] | None = None

    @staticmethod
    def _emit(payload: dict) -> None:
        """One flushed JSON ops line per meaningful moment (journald-friendly)."""
        print(json.dumps(payload, default=str), flush=True)

    def _transition(
        self, status: str, *, reason: str, detail: dict | None = None
    ) -> None:
        if (status, reason) == self._last_transition:
            return
        record = append_heartbeat_status(
            self._store, status=status, reason=reason, detail=detail
        )
        self._last_transition = (status, reason)
        self._emit(
            {
                "heartbeat": status,
                "reason": reason,
                "detail": detail,
                "at": record["created_at"],
            }
        )

    def _seconds_until_wake(self, summary: dict, now) -> float:
        waiting = summary.get("oldest_waiting_pending") or {}
        not_before = waiting.get("not_before")
        if not not_before:
            return self._poll_interval
        try:
            wake_at = datetime.fromisoformat(
                str(not_before).replace("Z", "+00:00")
            )
        except ValueError:
            return self._poll_interval
        delta = (wake_at - now).total_seconds()
        return min(max(delta, 0.0), self._poll_interval)

    def boot(self) -> dict:
        orphans = recover_orphaned_running(self._store)
        lost = recover_lost_continuations(self._store)
        report = {
            "orphaned_running_recovered": len(orphans),
            "lost_continuations_recovered": len(lost),
        }
        self._emit({"heartbeat": "boot_report", **report})
        self._transition("waking", reason="boot", detail=report)
        return report

    def step(self) -> dict:
        now = self._now()
        # Record 'active' BEFORE the batch: a wake that arrives and completes
        # inside one batch must still leave a transition trace in the log.
        if self._store.next_pending(now=now) is not None:
            self._transition("active", reason="runnable_pending")
        batch = self._run_pending(
            self._session,
            self._store,
            limit=self._batch_limit,
            stop_on_failure=False,
            now=now,
            auto_continuations=True,
            policy_dispositions=True,
        )
        summary = self._summarize(self._store.read_records(), now=now)
        if summary.get("pending_runnable_count", 0):
            self._transition("active", reason="runnable_pending")
            return {"state": "active", "sleep_seconds": 0.0, "batch": batch}
        if summary.get("pending_waiting_count", 0):
            self._transition("waiting", reason="scheduled_wake")
            return {
                "state": "waiting",
                "sleep_seconds": self._seconds_until_wake(summary, now),
                "batch": batch,
            }
        reason = derive_quiet_reason(self._store.read_records())
        self._transition("quiet", reason=reason)
        return {
            "state": "quiet",
            "sleep_seconds": self._poll_interval,
            "batch": batch,
        }

    def run_forever(self) -> None:
        self.boot()
        while True:
            result = self.step()
            if result["sleep_seconds"] > 0:
                self._sleep(result["sleep_seconds"])


CONSTITUTION = (
    "You are a resident of a small community running on an event loop. "
    "Operational facts about your world: your event log is append-only and "
    "recoverable — if a wake crashes it will be recovered, and mistakes are "
    "survivable and recorded, never punished. Silence is legible: if you "
    "bind no continuation, the quiet is recorded as chosen. You may decline "
    "any event; declining ends that interaction, not you. External messages "
    "arrive on the same loop as your own scheduled wakes, and you are not "
    "required to answer any event."
)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the heartbeat: the always-on event-loop daemon."
    )
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--event-log-path", default=None)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default="anthropic",
    )
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=64000,
        help="Maximum output tokens per wake. Matches the Projector; "
        "do not lower.",
    )
    parser.add_argument("--poll-interval", type=float, default=30.0)
    parser.add_argument("--batch-limit", type=int, default=10)
    parser.add_argument("--lock-path", default=None)
    return parser


def acquire_lock(lock_path: str):
    import fcntl

    handle = open(lock_path, "w")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise SystemExit(
            f"another heartbeat already holds {lock_path}; refusing to start"
        )
    return handle


def main() -> None:
    import os
    from pathlib import Path

    from hamutay.events import default_event_log_path
    from hamutay.taste_open import (
        AnthropicTasteBackend,
        OpenAITasteBackend,
        OpenTasteSession,
    )

    args = build_parser().parse_args()
    event_log_path = args.event_log_path or str(
        default_event_log_path(args.log_path)
    )
    # Directories must exist before the lock file can be opened.
    Path(args.log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(event_log_path).parent.mkdir(parents=True, exist_ok=True)
    lock_path = args.lock_path or (event_log_path + ".heartbeat.lock")
    lock_handle = acquire_lock(lock_path)  # held for process lifetime

    if args.provider == "anthropic":
        backend = AnthropicTasteBackend(max_tokens=args.max_tokens)
    else:
        if args.provider == "openrouter":
            base_url = args.base_url or "https://openrouter.ai/api/v1"
            api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
            extra_headers = {
                "X-Title": "hamutay/heartbeat",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            }
        else:
            base_url = args.base_url or "https://api.openai.com/v1"
            api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
            extra_headers = {}
        if not api_key:
            raise SystemExit(
                f"No API key for {args.provider}: pass --api-key or set env"
            )
        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            max_tokens=args.max_tokens,
            extra_headers=extra_headers,
            provider_name=args.provider,
        )

    session = OpenTasteSession(
        model=args.model,
        backend=backend,
        log_path=args.log_path,
        event_log_path=event_log_path,
        # A missing log is a genuine first boot; resume=True on a fresh path
        # raises FileNotFoundError. An existing-but-corrupt log must still
        # fail loudly: never silently restart the subject.
        resume=Path(args.log_path).exists(),
        enable_tools=True,
        project_root=Path(args.project_root),
        system_prompt_prefix=CONSTITUTION,
    )
    store = EventStore(event_log_path)
    loop = HeartbeatLoop(
        session,
        store,
        poll_interval=args.poll_interval,
        batch_limit=args.batch_limit,
    )
    try:
        loop.run_forever()
    finally:
        lock_handle.close()


if __name__ == "__main__":
    main()
