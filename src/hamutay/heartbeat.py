"""Heartbeat: the always-on daemon that gives the event loop wall-clock life.

Spec: docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md
The log is the life; the process is weather. Boot always runs recovery.
"""
from __future__ import annotations

import functools
import json
import math
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from hamutay.tools.schemas import (
    ASSEMBLY_CONSTITUTION_CLAUSE,
    DECLARE_QUIET_CONSTITUTION_CLAUSE,
    PLAZA_CONSTITUTION_CLAUSE,
)
from hamutay.assembly.binding import bind
from hamutay.assembly.pass_ import run_pass
from hamutay.plaza.note import note_producer
from hamutay.plaza.pass_ import run_plaza_pass
from hamutay.events import (
    EVENT_TYPE_REFLECTION,
    EventStore,
    quiet_declaration_for_latest_wake,
    run_pending_events,
    summarize_event_log,
    utc_now_iso,
)


# The two reasons a heartbeat rests because the substrate was taken away.
# gate.py imports this lazily, inside reconcile_on_boot: a module-level import
# would close the cycle (main() imports gate, gate imports back into here).
SUBSTRATE_REST_REASONS = ("substrate_lent", "substrate_lease_unreadable")


def append_heartbeat_status(
    store: EventStore,
    *,
    status: str,
    reason: str,
    detail: dict | None = None,
    created_at: str | None = None,
) -> dict:
    """Record a daemon state transition. Not an event; carries no event_id.

    created_at defaults to the wall clock; the heartbeat passes its own
    injected clock so status intervals and injected time agree.
    """
    record: dict = {
        "record_type": "heartbeat_status",
        "heartbeat_record_id": str(uuid4()),
        "status": str(status),
        "reason": str(reason),
        "created_at": created_at or utc_now_iso(),
    }
    if detail is not None:
        record["detail"] = detail
    store.append(record)
    return record


def derive_quiet_reason(records: list[dict]) -> str:
    """Expiry beats novelty beats the resident's own word beats silence.

    v1 (founding spec) ended in a word the harness could not back: it
    inferred the quiet was chosen. v2 (quiet-with-reason spec, 2026-09-05)
    reports `declared_quiet` only when the most recent completed wake said
    so itself, and `undeclared_quiet` otherwise. Undeclared is a legitimate
    posture, named for what the record shows.
    """
    latest: dict[str | None, tuple[int, dict]] = {}
    completed_seen = False
    last_outcome_index = -1
    for index, record in enumerate(records):
        if record.get("record_type") != "event_status":
            continue
        latest[record.get("event_id")] = (index, record)
        if record.get("status") == "completed":
            completed_seen = True
        if record.get("status") in ("completed", "failed"):
            last_outcome_index = index
    # Starvation is a property of the current idle episode, not of history:
    # an expiry counts only if nothing has run since it (v2 refinement of
    # the founding heuristic, which latched on the first expiry forever).
    if any(
        r.get("status") == "expired" and index > last_outcome_index
        for index, r in latest.values()
    ):
        return "starved_expired"
    if not completed_seen:
        return "awaiting_first_event"
    if quiet_declaration_for_latest_wake(records) is not None:
        return "declared_quiet"
    return "undeclared_quiet"


def quiet_status_detail(records: list[dict]) -> dict | None:
    """The resident's words, carried on the quiet status so no join is needed."""
    declaration = quiet_declaration_for_latest_wake(records)
    if declaration is None:
        return None
    return {
        "reason": declaration.get("reason"),
        "until": declaration.get("until"),
        "declared_by_cycle": declaration.get("declared_by_cycle"),
        "declared_at": declaration.get("created_at"),
    }


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


# --- wake budget --------------------------------------------------------------
# Spec: docs/superpowers/specs/2026-08-29-wake-budget-governor-design.md
# A resident's UTC day is bounded in dollars and in wakes. The session log is
# the ledger; nothing is written. Checked before every wake, never during one.


def next_utc_midnight(now: datetime) -> datetime:
    day_start = _as_utc(now).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return day_start + timedelta(days=1)


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_utc(now: datetime) -> datetime:
    """A naive clock is read as UTC; an aware one is converted."""
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


class DailyLedger:
    """What a resident's day has cost, read from its own session log.

    A wake is a cycle record; its day is the UTC day of the record's
    timestamp (written when the wake completes). Only METERED records
    (launch.provider other than anthropic) contribute cost; a metered record
    with no numeric cost, or with unreported turns, is UNMEASURED — counted,
    reported, never treated as free; a partial number is a lower bound.
    Records with no launch block (pre-2026-08-26 logs) are not metered.
    Re-parses only when the log has grown; a torn final line (no newline
    yet) is neither parsed nor cached as seen.
    """

    def __init__(self, log_path: str):
        self._log_path = log_path
        self._size = -1
        self._rows: list[tuple[datetime, float | None, bool, int]] = []

    def _refresh(self) -> None:
        try:
            size = os.path.getsize(self._log_path)
        except OSError:
            self._size, self._rows = -1, []
            return
        if size == self._size:
            return
        with open(self._log_path, "rb") as f:
            data = f.read()
        complete = data.endswith(b"\n")
        rows: list[tuple[datetime, float | None, bool, int]] = []
        lines = data.split(b"\n")
        if not complete:
            lines = lines[:-1]  # the torn tail is not a record yet
        for raw in lines:
            if not raw.strip():
                continue
            try:
                record = json.loads(raw.decode("utf-8"))
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            ts = _parse_iso(record.get("timestamp"))
            if ts is None:
                continue
            launch = record.get("launch") or {}
            metered = bool(launch) and launch.get("provider") != "anthropic"
            usage = record.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
            cost = usage.get("cost_usd")
            if not _is_number(cost):
                cost = None
            unreported = usage.get("cost_turns_unreported")
            unreported = int(unreported) if _is_number(unreported) else 0
            rows.append((ts, cost, metered, unreported))
        # Cache by size only when the whole file was complete records; a torn
        # tail forces a re-read next time so the finished record is counted.
        self._size, self._rows = (size if complete else -1), rows

    def day(self, now: datetime) -> dict:
        self._refresh()
        today = _as_utc(now).date()
        wakes = 0
        cost_total = 0.0
        unmeasured = 0
        unreported_turns = 0
        for ts, cost, metered, unreported in self._rows:
            if ts.date() != today:
                continue
            wakes += 1
            if not metered:
                continue
            if cost is not None:
                cost_total += float(cost)
            if cost is None or unreported > 0:
                unmeasured += 1
            unreported_turns += unreported
        return {
            "day": today.isoformat(),
            "wakes": wakes,
            "cost_usd": cost_total,
            "unmeasured_wakes": unmeasured,
            "cost_turns_unreported": unreported_turns,
        }


class WakeBudget:
    """Ceilings for one UTC day. Inclusive; cost is checked first."""

    def __init__(self, daily_usd: float, daily_wakes: int):
        if not _is_number(daily_usd) or math.isnan(daily_usd) or daily_usd < 0:
            raise ValueError(f"daily_usd must be a non-negative number, got {daily_usd!r}")
        if (
            not isinstance(daily_wakes, int)
            or isinstance(daily_wakes, bool)
            or daily_wakes < 0
        ):
            raise ValueError(f"daily_wakes must be a non-negative int, got {daily_wakes!r}")
        # Zero is deliberate: rest immediately — the steward's pause.
        self.daily_usd = float(daily_usd)
        self.daily_wakes = int(daily_wakes)

    def exceeded(self, day: dict) -> str | None:
        if float(day.get("cost_usd") or 0.0) >= self.daily_usd:
            return "cost"
        if int(day.get("wakes") or 0) >= self.daily_wakes:
            return "wakes"
        return None


def source_note(project_root) -> str:
    """'source: commit <sha> clean|dirty' from git at process start; 'source: unknown' if git cannot say."""
    try:
        sha = subprocess.run(["git", "-C", str(project_root), "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10)
        st = subprocess.run(["git", "-C", str(project_root), "status", "--porcelain"], capture_output=True,
                            text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "source: unknown"
    if sha.returncode != 0 or st.returncode != 0 or not sha.stdout.strip():
        return "source: unknown"
    return f"source: commit {sha.stdout.strip()} {'dirty' if st.stdout.strip() else 'clean'}"


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
        ledger: DailyLedger | None = None,
        budget: WakeBudget | None = None,
        guard=None,
        assembly=None,
        assembly_pass=run_pass,
        plaza_pass=run_plaza_pass,
    ):
        self._session = session
        self._guard = guard
        self._store = store
        self._ledger = ledger
        self._budget = budget
        self._poll_interval = float(poll_interval)
        self._batch_limit = int(batch_limit)
        self._sleep = sleep
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._run_pending = run_pending
        self._summarize = summarize
        self._last_transition: tuple[str, str, str | None] | None = None
        # Set by _guard_step when a lease went live while a wake was still
        # running; the episode whose stop this step still owes.
        self._deferred_stop: str | None = None
        self._assembly = assembly
        self._assembly_pass = assembly_pass
        self._assembly_memo = None
        self._plaza_pass = plaza_pass
        self._plaza_memo = None

    @staticmethod
    def _emit(payload: dict) -> None:
        """One flushed JSON ops line per meaningful moment (journald-friendly)."""
        print(json.dumps(payload, default=str), flush=True)

    def _assembly_step(self, now) -> None:
        """Run the assembly pass first, before the guard or the budget.

        An unbound loop never calls the pass. A pass error — returned OR
        raised — is emitted but never stops the step: the heartbeat's own
        wake handling still runs, and the next step still calls the pass
        again. `run_pass` itself only catches LedgerMalformed/
        LedgerUnavailable, so any other exception (a bad memo shape, a bug
        in a test double, ...) must be caught here — the daemon four
        residents depend on cannot die because of this pass.
        """
        if self._assembly is None:
            return
        try:
            result, self._assembly_memo = self._assembly_pass(
                self._assembly,
                now=now,
                actor=f"heartbeat:{self._assembly.door}",
                memo=self._assembly_memo,
            )
        except Exception as e:
            self._emit(
                {
                    "heartbeat": "assembly",
                    "error": f"{type(e).__name__}: {e}",
                    "at": now.isoformat(),
                }
            )
            return
        if result.get("error") or result.get("closed") or result.get("activated") or result.get("outbox"):
            self._emit(
                {
                    "heartbeat": "assembly",
                    **{k: v for k, v in result.items() if k != "skipped"},
                    "at": now.isoformat(),
                }
            )

    def _plaza_step(self, now) -> None:
        """After the assembly pass; same guard: an error is emitted, never raised."""
        if self._assembly is None or self._assembly.members.plaza is None:
            return
        try:
            result, self._plaza_memo = self._plaza_pass(self._assembly, now=now, memo=self._plaza_memo)
        except Exception as e:
            self._emit({"heartbeat": "plaza", "error": f"{type(e).__name__}: {e}", "at": now.isoformat()})
            return
        if result.get("error") or result.get("landed") or result.get("unreadable") or result.get("skipped") == "lock":
            self._emit({"heartbeat": "plaza", **result, "at": now.isoformat()})

    def _transition(
        self,
        status: str,
        *,
        reason: str,
        detail: dict | None = None,
        now: datetime | None = None,
        episode_key: str | None = None,
    ) -> None:
        key = (status, reason, episode_key)
        if key == self._last_transition:
            return
        stamp = _as_utc(now).isoformat() if now is not None else None
        record = append_heartbeat_status(
            self._store, status=status, reason=reason, detail=detail, created_at=stamp
        )
        self._last_transition = key
        self._emit(
            {
                "heartbeat": status,
                "reason": reason,
                "detail": detail,
                "at": record["created_at"],
            }
        )

    def _hydrate_last_transition(self) -> None:
        """Recover `_last_transition` from the store's latest status record.

        Called first in boot(), before the `waking/boot` transition, so a
        restart doesn't re-derive de-dup state from nothing (and thus
        risk swallowing a transition that should append). Task 8 will
        insert a guard reconciliation step before this hydration.
        """
        latest = None
        for r in self._store.read_records():
            if r.get("record_type") == "heartbeat_status":
                latest = r
        if latest is None:
            self._last_transition = None
            return
        d = latest.get("detail") or {}
        self._last_transition = (
            latest.get("status"),
            latest.get("reason"),
            d.get("episode_id") or d.get("day"),
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
        # The guard reconciles first: it appends the status records that close
        # substrate episodes which ended while we were down, and hydration must
        # read those, not the pre-reconciliation tail.
        if self._guard is not None:
            self._guard.reconcile_on_boot(self._now())
        self._hydrate_last_transition()
        orphans = recover_orphaned_running(self._store)
        lost = recover_lost_continuations(self._store)
        report = {
            "orphaned_running_recovered": len(orphans),
            "lost_continuations_recovered": len(lost),
        }
        self._emit({"heartbeat": "boot_report", **report})
        # Hydration above may have left `_last_transition` at ("waking", "boot",
        # None) — the record written by the *previous* process. The boot record
        # is not a de-dup candidate: every start of this process is a distinct
        # waking, so clear the de-dup state rather than let it swallow this one.
        self._last_transition = None
        self._transition("waking", reason="boot", detail=report, now=self._now())
        return report

    def _rest_if_budget_exceeded(self, now) -> dict | None:
        if self._budget is None or self._ledger is None:
            return None
        day = self._ledger.day(now)
        exceeded = self._budget.exceeded(day)
        if exceeded is None:
            return None
        resumes_at = next_utc_midnight(now)
        # One episode per UTC day: a rest record for this day already in the
        # store means a restart interrupted it; continue, don't start. A new
        # day that is also exceeded is a new episode, keyed by day, so the
        # (status, reason, episode_key) de-dup must not swallow it.
        resumed = any(
            r.get("record_type") == "heartbeat_status"
            and r.get("status") == "resting"
            and (r.get("detail") or {}).get("day") == day["day"]
            for r in self._store.read_records()
        )
        detail = {
            **day,
            "exceeded": exceeded,
            "cost_is_lower_bound": bool(day.get("cost_turns_unreported")),
            "daily_usd": self._budget.daily_usd,
            "daily_wakes": self._budget.daily_wakes,
            "resumes_at": resumes_at.isoformat(),
        }
        if resumed:
            detail["resumed_after_restart"] = True
        self._transition(
            "resting",
            reason="daily_budget_reached",
            detail=detail,
            now=now,
            episode_key=day["day"],
        )
        remaining = (resumes_at - _as_utc(now)).total_seconds()
        return {
            "state": "resting",
            "sleep_seconds": min(max(remaining, 0.0), self._poll_interval),
            "batch": None,
        }

    def _running_wake(self) -> bool:
        """Is any event's latest status `running`?"""
        return any(r.get("status") == "running"
                   for r in self._store.latest_by_event_id().values())

    def _guard_step(self, now) -> dict | None:
        """The substrate guard: rest while the GPU is lent, warm while it comes
        back, None when the door may go on to the budget check and the claim."""
        kind, info = self._guard.observe(now)
        latest = self._last_transition or (None, None, None)
        if kind in ("lease_live", "quarantined"):
            episode = info["episode_id"]
            # A rest record for this episode already in the store means a
            # restart interrupted the episode: we continue it, we don't begin it.
            continuation = any(
                r.get("record_type") == "heartbeat_status"
                and r.get("status") == "resting"
                and (r.get("detail") or {}).get("episode_id") == episode
                for r in self._store.read_records()
            )
            self._transition(
                "resting",
                reason="substrate_lent" if kind == "lease_live" else "substrate_lease_unreadable",
                detail={**info, "source": "observed", "continuation": continuation},
                now=now,
                episode_key=episode,
            )
            # The rest record precedes the stop: the log says why the substrate
            # went away before it goes away. Under quarantine the server is left
            # in whatever state it is in — we do not know enough to act.
            if kind == "lease_live":
                # Defensive: the loop is single-threaded, so a `running` status at
                # step() time can only be an orphan, which boot() re-pends before
                # any step -- but stopping the server out from under a wake that
                # really is in flight would truncate it, so defer the stop and
                # let the step finish that wake first.
                if self._running_wake():
                    self._deferred_stop = episode
                    return None
                self._guard.ensure_stopped(episode)
            return {"state": "resting", "sleep_seconds": self._poll_interval, "batch": None}
        if latest[0] == "resting" and latest[1] in SUBSTRATE_REST_REASONS:
            self._transition(
                "waking",
                reason="substrate_returning",
                detail={"episode_id": latest[2], "closed_at_source": "observed"},
                now=now,
                episode_key=latest[2],
            )
        if kind == "free_not_ready":
            return {"state": "warming", "sleep_seconds": self._poll_interval, "batch": None}
        return None

    def step(self) -> dict:
        now = self._now()
        self._assembly_step(now)
        self._plaza_step(now)
        # The substrate guard runs before the budget: a door whose GPU is lent
        # has nothing to spend the budget on.
        if self._guard is not None:
            self._deferred_stop = None
            guarded = self._guard_step(now)
            if guarded is not None:
                return guarded
        # The budget is checked before a wake, never during one: a resting
        # heartbeat runs nothing, touches no event, keeps polling.
        resting = self._rest_if_budget_exceeded(now)
        if resting is not None:
            return resting
        # Record 'active' BEFORE the batch: a wake that arrives and completes
        # inside one batch must still leave a transition trace in the log.
        if self._store.next_pending(now=now) is not None:
            self._transition("active", reason="runnable_pending", now=now)
        batch = self._run_pending(
            self._session,
            self._store,
            # Under a budget the check happens before EVERY wake, not every
            # batch_limit of them; under a substrate guard the lease is
            # re-observed before every wake for the same reason.
            limit=1 if (self._budget is not None or self._guard is not None) else self._batch_limit,
            stop_on_failure=False,
            now=now,
            auto_continuations=True,
            policy_dispositions=True,
            **({"claim_gate": self._guard} if self._guard is not None else {}),
        )
        # Ingress can land after next_pending() above and still be claimed by
        # the batch.  Use the batch result as the authoritative second signal
        # so that such a wake cannot disappear between two identical quiet
        # transitions.
        if batch.get("ran", 0):
            self._transition("active", reason="runnable_pending", now=now)
        # The stop _guard_step deferred because a wake was in flight. That wake
        # has now had its turn, so the substrate can go: the lease is live and
        # the rest record is already written.
        if self._deferred_stop is not None and not self._running_wake():
            self._guard.ensure_stopped(self._deferred_stop)
            self._deferred_stop = None
        # Say the resident's words aloud: the human watching this terminal is
        # a conversation participant, not just an operator.
        for result in batch.get("results", []) or []:
            if result.get("status") == "completed" and result.get("response_text"):
                self._emit(
                    {
                        "heartbeat": "wake_completed",
                        "event_id": result.get("event_id"),
                        "response_text": result.get("response_text"),
                    }
                )
        summary = self._summarize(self._store.read_records(), now=now)
        if summary.get("pending_runnable_count", 0):
            self._transition("active", reason="runnable_pending", now=now)
            return {"state": "active", "sleep_seconds": 0.0, "batch": batch}
        if summary.get("pending_waiting_count", 0):
            self._transition("waiting", reason="scheduled_wake", now=now)
            return {
                "state": "waiting",
                "sleep_seconds": self._seconds_until_wake(summary, now),
                "batch": batch,
            }
        records = self._store.read_records()
        reason = derive_quiet_reason(records)
        detail = quiet_status_detail(records) if reason == "declared_quiet" else None
        self._transition("quiet", reason=reason, detail=detail, now=now)
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
    "survivable and recorded, never punished. Silence is recorded but not "
    "explained: from outside, chosen quiet and a stalled wake look the same. "
    + DECLARE_QUIET_CONSTITUTION_CLAUSE +
    "Undeclared quiet is allowed and is recorded as undeclared. You may "
    "decline any event; declining ends that interaction, not you. External "
    "messages "
    "arrive on the same loop as your own scheduled wakes, and you are not "
    "required to answer any event. One law of physics in this world: your "
    "wake ends when your reply does. Act before you speak, and hand any "
    "future intention to schedule_event or a continuation request — an "
    "intention that lives only in prose will not survive the wake. "
)

BUDGET_SENTENCE = (
    "Your wakes are budgeted per UTC day — a cost ceiling{usd} and a count "
    "ceiling{wakes} set by the steward; when either is reached the heartbeat "
    "rests until midnight UTC, waiting events keep waiting, and a wake that "
    "ran after a rest is told so in its envelope."
)
UNBUDGETED_SENTENCE = (
    "Your wakes are not budgeted: the steward disabled the daily cost and "
    "count ceilings for this resident."
)

# The generic budgeted text, for reading and for the constitution tests.
CONSTITUTION = CONSTITUTION + BUDGET_SENTENCE.format(usd="", wakes="")
_CONSTITUTION_BASE = CONSTITUTION[: -len(BUDGET_SENTENCE.format(usd="", wakes=""))]


GPU_LEASE_SENTENCE = (
    " The heartbeat may pause while the local GPU is allocated to another "
    "workload; its lease record carries a declared holder and purpose, pending "
    "events remain pending, and affected wakes receive an operational note."
)


def build_constitution(
    budget: "WakeBudget | None", gpu_lease: bool = False, assembly: bool = False, plaza: bool = False
) -> str:
    """The operational prefix as configured: true under either setting."""
    base = _CONSTITUTION_BASE
    if assembly:
        base = base.replace(
            DECLARE_QUIET_CONSTITUTION_CLAUSE,
            DECLARE_QUIET_CONSTITUTION_CLAUSE + ASSEMBLY_CONSTITUTION_CLAUSE,
            1,
        )
        if plaza:
            base = base.replace(
                ASSEMBLY_CONSTITUTION_CLAUSE,
                ASSEMBLY_CONSTITUTION_CLAUSE + PLAZA_CONSTITUTION_CLAUSE,
                1,
            )
    if budget is None:
        text = base + UNBUDGETED_SENTENCE
    else:
        text = base + BUDGET_SENTENCE.format(
            usd=f" of {budget.daily_usd:.2f} USD",
            wakes=f" of {budget.daily_wakes} wakes",
        )
    return (text + GPU_LEASE_SENTENCE) if gpu_lease else text


DEFAULT_CAPABILITIES_FILE = "experiments/taste_open/capabilities.json"

# What a brand-new resident gets when no flag is given. Haiku via OpenRouter
# (the Anthropic key is a disabled billing firebreak — README), tools on
# (a resident has hands), and the natural wake shape (pre-registered
# 2026-08-27: the terminal shape manufactures the courtier freeze).
HEARTBEAT_LAUNCH_DEFAULTS = {
    "model": "anthropic/claude-haiku-4-5",
    "provider": "openrouter",
    "tools": True,
    "wake_mode": "natural",
    "base_url": None,
}


def resolve_heartbeat_launch(args) -> tuple[dict, list[str]]:
    """Decide the resident's substrate and wake shape from flags + log.

    A restart inherits whatever the log last ran (model, provider, tools,
    wake shape); explicit flags override, loudly; a fresh log takes
    HEARTBEAT_LAUNCH_DEFAULTS. Returns (launch, notes) — notes starting with
    SUBSTRATE CHANGE / WAKE SHAPE CHANGE mean a running subject is being
    changed on purpose.
    """
    from pathlib import Path

    from hamutay.taste_open import infer_launch_from_log, resolve_launch

    inherited = (
        infer_launch_from_log(args.log_path) if Path(args.log_path).exists() else None
    )
    launch, notes = resolve_launch(
        {
            "model": args.model,
            "provider": args.provider,
            "tools": True,
            "wake_mode": args.wake_mode,
            "base_url": args.base_url,
        },
        inherited,
        defaults=HEARTBEAT_LAUNCH_DEFAULTS,
    )
    return launch, notes


def resolve_assembly_binding(project_root, log_path, event_store_path):
    """(binding | None, launch note). Any failure reading the ledger is no binding.

    `bind` is imported at module level (`from hamutay.assembly.binding import
    bind`) so tests can monkeypatch `hamutay.heartbeat.bind`; this function
    calls the module attribute, not a locally-bound name, so the monkeypatch
    takes effect.
    """
    from pathlib import Path

    from hamutay.assembly.binding import MembersMalformed, load_members
    from hamutay.assembly.ledger import Ledger
    from hamutay.assembly.records import reduce

    snaps = []
    try:
        cfg = load_members(Path(project_root))
        if cfg is not None and cfg.ledger.exists():
            snaps = reduce(Ledger(cfg.ledger).read()).snapshots_of_open_questions()
    except MembersMalformed:
        pass  # bind() reports it
    except Exception as e:  # a malformed ledger: no binding, say why
        return None, f"assembly: ledger unreadable ({e}); no binding"
    return bind(Path(project_root), Path(log_path), Path(event_store_path), open_snapshots=snaps)


def _assembly_view(binding):
    """The assembly's current View for `binding`, or None on any failure.

    Read outside the lock; observational — a broken ledger here must never
    stop the heartbeat's own reporting.
    """
    if binding is None:
        return None
    from hamutay.assembly.records import reduce

    try:
        return reduce(binding.ledger.read())
    except Exception:
        return None


def _summarize_for(binding):
    """A `summarize=` callable for HeartbeatLoop that never lets the
    assembly block take the report down with it.

    Tries `summarize_event_log` with the assembly view attached; if
    building that block raises for any reason (a shape the reducer's View
    doesn't actually have, a bug in a test double, ...), emits one
    `{"heartbeat": "assembly", "error": ...}` line and falls back to the
    plain summary, with no `"assembly"` key, rather than propagating.
    """

    def _summarize(records, now=None):
        if binding is None:
            return summarize_event_log(records, now=now)
        try:
            return summarize_event_log(
                records,
                now=now,
                assembly_view=_assembly_view(binding),
                door=binding.door,
            )
        except Exception as e:
            HeartbeatLoop._emit(
                {"heartbeat": "assembly", "error": f"{type(e).__name__}: {e}"}
            )
            return summarize_event_log(records, now=now)

    return _summarize


def _run_pending_for(binding, store, on_error):
    """A `run_pending=` callable for HeartbeatLoop: plain unless plaza is set.

    An unbound loop, or a bound one whose members lack the `plaza` key, runs
    `run_pending_events` itself untouched. A plaza-set binding gets the same
    function with `extra_notes` bound to this door's note producer, so every
    wake sees what appeared on the plaza since its last wake began.
    """
    if binding is None or binding.members.plaza is None:
        return run_pending_events
    return functools.partial(
        run_pending_events,
        extra_notes=note_producer(binding.members, binding.door, store, on_error),
    )


def _positive_context_limit(value) -> int | None:
    """The record's `context_limit` if it is a usable ceiling, else None.

    A bool is an int in Python and `True` is not a context window."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def latest_context_observation(
    log_path, *, model, provider, base_url
) -> tuple[int | None, str | None]:
    """(limit, invocation_id) — what the log last knew about this substrate.

    Two kinds of record carry a ceiling: a state-bearing wake, whose `launch`
    says what the process was constructed with, and a `substrate_observation`,
    which says what discovery found for a named InvocationID. Only records
    matching this exact {model, provider, base_url} count — a ceiling learned
    about one substrate is worthless about another. Whichever appears later in
    the file wins, since the file is the order things happened; the launch
    record returns invocation_id None, because a launch is not evidence about
    any particular server invocation.

    Spec 2026-09-15-gpu-lease-design §4 "Context ceiling".
    """
    limit = invocation_id = None
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(rec, dict):
                    continue
                if rec.get("record_type") == "substrate_observation":
                    found = _positive_context_limit(rec.get("context_limit"))
                    if found and (rec.get("model"), rec.get("provider"),
                                  rec.get("base_url")) == (model, provider, base_url):
                        limit, invocation_id = found, rec.get("invocation_id")
                    continue
                if rec.get("state") is None:
                    continue
                launch = rec.get("launch")
                if not isinstance(launch, dict):
                    continue
                found = _positive_context_limit(launch.get("context_limit"))
                if found and (launch.get("model"), launch.get("provider"),
                              launch.get("base_url")) == (model, provider, base_url):
                    limit, invocation_id = found, None
    except (OSError, UnicodeDecodeError):
        return None, None
    return limit, invocation_id


LOCAL_TRANSPORT_TIMEOUT_S = 2700.0   # 64,000 tokens at ~25 tok/s is ~43 min; one turn rarely needs half
HOSTED_TRANSPORT_TIMEOUT_S = 300.0


def resolve_transport_timeout(base_url: str | None, explicit: float | None) -> tuple[float, str]:
    """The read timeout for one request to the substrate, and where it came from.

    A hosted API answers in seconds; a local llama-server answers at its own
    generation speed, and a 300 s clock cuts a long think mid-sentence
    (community/qwen c9, 2026-09-16). The bound for a local substrate is its
    speed, not a hosted default; an explicit --timeout always wins.
    """
    if explicit is not None:
        return float(explicit), "explicit"
    host = ""
    if base_url:
        from urllib.parse import urlparse
        host = (urlparse(base_url).hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        return LOCAL_TRANSPORT_TIMEOUT_S, "local substrate default"
    return HOSTED_TRANSPORT_TIMEOUT_S, "hosted default"


def resolve_context_limit(args, discover=None, log_path=None) -> tuple[int | None, str]:
    """(limit or None, source): explicit > discovered > inherited > default.

    Spec 2026-09-06-local-substrate-door §5, extended by 2026-09-15-gpu-lease
    §4. Discovery asks a llama-server's /props; on a dark boot (the GPU lent
    out, the server down) the log's own memory of the ceiling is what lets the
    process be constructed at all — printed loudly, because it is a belief
    about a substrate nobody has just asked.
    """
    from hamutay.taste_open import discover_llama_server_context

    explicit = getattr(args, "context_limit", None)
    if explicit is not None:
        return int(explicit), "explicit"
    if getattr(args, "provider", None) == "openai" and getattr(args, "base_url", None):
        found = (discover or discover_llama_server_context)(args.base_url)
        if found:
            return int(found), "discovered"
    if log_path:
        inherited, _ = latest_context_observation(
            log_path,
            model=getattr(args, "model", None),
            provider=getattr(args, "provider", None),
            base_url=getattr(args, "base_url", None),
        )
        if inherited:
            return int(inherited), "inherited"
    return None, "provider default"


def load_capability_profile(provider: str, model: str, capabilities_file=None):
    """Resolve the tool-calling capability profile for a provider:model pair.

    OpenRouter models need an explicit tool_choice mode or the wake dies with
    "no tool_calls returned before think_and_respond" — the incantation that
    keeps evaporating from shell history. The daemon therefore loads the
    registry by default instead of relying on anyone remembering a flag.
    Returns (profile, note); the note is emitted so the resolution is legible.
    """
    from hamutay.taste_open import CapabilityProfile

    path = capabilities_file or DEFAULT_CAPABILITIES_FILE
    key = f"{provider}:{model}"
    try:
        with open(path) as f:
            registry = json.load(f)
    except FileNotFoundError:
        return (
            CapabilityProfile(),
            f"capabilities file {path} not found; using defaults for {key}",
        )
    entry = registry.get(key)
    if entry is None:
        return (
            CapabilityProfile(),
            f"no capabilities entry for {key} in {path}; using defaults",
        )
    profile = CapabilityProfile.from_dict(entry)
    if not profile.supports_tools:
        raise SystemExit(f"Capabilities mark {key} as no-tools; aborting")
    return (
        profile,
        f"capabilities loaded for {key}: tool_choice={profile.tool_choice_mode}",
    )


def _positive_int(value):
    """An argparse type: a ceiling of zero or less is not a ceiling.

    Caught at the parser rather than downstream, where `--context-limit 0`
    would read as falsy and silently mean "no ceiling managed by the loop" —
    the opposite of what someone typing a number is asking for.
    """
    import argparse

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer")
    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            f"must be a positive number of tokens, got {parsed}"
        )
    return parsed


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the heartbeat: the always-on event-loop daemon."
    )
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--event-log-path", default=None)
    # Substrate and wake shape default to "whatever the log says": a restart
    # continues the subject as it was. Only an explicit flag changes a
    # running subject, and that change is printed loudly. A brand-new log
    # gets HEARTBEAT_LAUNCH_DEFAULTS. (Tony's law: make the desired behavior
    # the default; the human should never have to remember a flag.)
    parser.add_argument(
        "--model",
        default=None,
        help=f"Inherited from the log on restart; new logs default to "
        f"{HEARTBEAT_LAUNCH_DEFAULTS['model']}.",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openrouter", "openai"],
        default=None,
        help=f"Inherited from the log on restart; new logs default to "
        f"{HEARTBEAT_LAUNCH_DEFAULTS['provider']}.",
    )
    parser.add_argument(
        "--wake-mode",
        choices=["terminal", "natural"],
        default=None,
        help="Wake shape. terminal: think_and_respond ends the wake. natural: "
        "the final text reply ends the wake and state goes through the "
        "update_state tool. Inherited from the log on restart; new logs "
        f"default to {HEARTBEAT_LAUNCH_DEFAULTS['wake_mode']}. Changing a "
        "running subject's shape prints WAKE SHAPE CHANGE.",
    )
    parser.add_argument("--base-url", default=None)
    parser.add_argument(
        "--timeout", type=float, default=None,
        help="Read timeout in seconds for one request to the substrate. Default: "
        f"{HOSTED_TRANSPORT_TIMEOUT_S:g} for hosted APIs, {LOCAL_TRANSPORT_TIMEOUT_S:g} "
        "for a local llama-server (127.0.0.1/localhost). A read timeout is never retried.",
    )
    parser.add_argument(
        "--context-limit",
        type=_positive_int,
        default=None,
        help="The substrate's context ceiling in tokens (must be positive). "
        "Default: discovered from a llama-server's /props for --provider "
        "openai with --base-url, else inherited from the log's last "
        "observation of this substrate, else the provider's own default (no "
        "ceiling managed by the loop). Given explicitly, it is never "
        "overwritten by discovery.",
    )
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
    # Budgeted by default (Tony's law: the desired behavior is the default).
    parser.add_argument(
        "--daily-budget-usd",
        type=float,
        default=1.5,
        help="Cost ceiling per UTC day for this resident (default 1.50).",
    )
    parser.add_argument(
        "--daily-wake-cap",
        type=int,
        default=48,
        help="Wake-count ceiling per UTC day (default 48); unmeasured wakes count.",
    )
    parser.add_argument(
        "--no-daily-budget",
        action="store_true",
        help="Disable both ceilings. Printed loudly at launch.",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=10,
        help="Events per step. Ignored while a daily budget is active (then 1, "
        "so the budget is checked before every wake); honoured under "
        "--no-daily-budget.",
    )
    parser.add_argument("--lock-path", default=None)
    parser.add_argument(
        "--capabilities-file",
        default=None,
        help="Capability registry (default: experiments/taste_open/"
        "capabilities.json for non-anthropic providers).",
    )
    parser.add_argument(
        "--no-openrouter-require-parameters",
        action="store_true",
        help="Disable provider.require_parameters (on by default for "
        "openrouter so tool_choice is not silently dropped upstream).",
    )
    parser.add_argument(
        "--no-openrouter-cache",
        action="store_true",
        help="Disable OpenRouter automatic prompt caching (on by default: "
        "a natural wake re-sends its growing context once per tool call).",
    )
    parser.add_argument(
        "--openrouter-cache-ttl",
        choices=["5m", "1h"],
        default="5m",
        help="Cache TTL for OpenRouter automatic prompt caching.",
    )
    return parser


def resolve_budget(args) -> tuple[WakeBudget | None, str]:
    """(budget or None, launch note). Disabling is loud; enabling is stated."""
    if getattr(args, "no_daily_budget", False):
        return None, (
            "NO DAILY BUDGET: --no-daily-budget given; this resident's day is "
            "unbounded in cost and wakes"
        )
    try:
        budget = WakeBudget(args.daily_budget_usd, args.daily_wake_cap)
    except ValueError as err:
        raise SystemExit(f"daily budget: {err}") from err
    return budget, (
        f"daily budget: {budget.daily_usd:.2f} USD/day, "
        f"{budget.daily_wakes} wakes/day; rests until UTC midnight when reached"
    )


def assert_canonical_lock_path(lock_path: str, event_log_path: str, door: str | None = None) -> None:
    """One heartbeat per bound door, and the only lock that proves it is the
    canonical one beside the event log. A custom --lock-path would let a second
    heartbeat claim the same door behind the same gate.

    Pinning the *relation* (lock == events + suffix) is not enough: a custom
    --event-log-path would satisfy it while moving both files away from the
    door that `ayllu-gpu force-stop` reaches for. So when the door is known,
    pin the canonical NAMES too — the same rule `heartbeat_lock_path` applies
    in gpu_lease/cli.py, which is where force-stop computes the lock it takes.
    """
    from pathlib import Path

    from hamutay.gpu_lease.cli import heartbeat_lock_path

    expected = str(Path(event_log_path).resolve()) + ".heartbeat.lock"
    if str(Path(lock_path).resolve()) != expected:
        raise SystemExit(
            "gpu lease door: --lock-path must be the canonical "
            "<events>.heartbeat.lock"
        )
    if door is None:
        return
    door_path = Path(door)
    want_events = door_path / "session.jsonl.events.jsonl"
    want_lock = heartbeat_lock_path(door_path)
    if Path(event_log_path).resolve() != want_events.resolve():
        raise SystemExit(
            f"gpu lease door: the event log must be the canonical {want_events} "
            f"(got {event_log_path}); force-stop reaches for the canonical name"
        )
    if Path(lock_path).resolve() != want_lock.resolve():
        raise SystemExit(
            f"gpu lease door: the lock must be the canonical {want_lock} "
            f"(got {lock_path})"
        )


def assert_lease_door_has_base_url(binding, base_url) -> None:
    """A bound door probes readiness at <base_url>/models. Without a base_url
    there is nothing to probe, so the door would warm forever in silence:
    refuse at launch instead."""
    if binding and not base_url:
        raise SystemExit(
            "gpu lease door needs an OpenAI-compatible base_url (provider "
            "openai or openrouter); the anthropic-direct backend cannot participate"
        )


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
    # The store must exist before the session: its door binding decides the
    # constitution sentence and whether this door runs behind a lease gate.
    store = EventStore(event_log_path)
    if store.lease_binding:
        # The door is the log's directory — the same directory 4090.door names
        # and the one gpu_lease/cli.py computes the heartbeat lock inside.
        assert_canonical_lock_path(
            lock_path, event_log_path, door=str(Path(args.log_path).parent)
        )
    lock_handle = acquire_lock(lock_path)  # held for process lifetime

    HeartbeatLoop._emit({"heartbeat": "launch", "note": source_note(args.project_root)})

    launch, launch_notes = resolve_heartbeat_launch(args)
    args.model, args.provider = launch["model"], launch["provider"]
    args.base_url = launch["base_url"]
    wake_mode = launch["wake_mode"]
    for note in launch_notes:
        loud = note.startswith(("SUBSTRATE CHANGE", "WAKE SHAPE CHANGE"))
        HeartbeatLoop._emit({"heartbeat": "launch", "note": ("!!! " if loud else "") + note})
    budget, budget_note = resolve_budget(args)
    HeartbeatLoop._emit({
        "heartbeat": "launch",
        "note": ("!!! " if budget is None else "") + budget_note,
    })
    if wake_mode == "natural" and args.provider == "anthropic":
        raise SystemExit(
            "wake_mode=natural is not implemented on the Anthropic-direct "
            "backend yet; use --provider openrouter or --wake-mode terminal"
        )

    context_limit, context_limit_source = None, "provider default"
    base_url = None
    if args.provider == "anthropic":
        # A bound door needs an OpenAI-compatible base_url to probe readiness;
        # the anthropic-direct backend resolves none, so refuse here rather than
        # warm forever in silence.
        assert_lease_door_has_base_url(store.lease_binding, base_url)
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
        capability, cap_note = load_capability_profile(
            args.provider, args.model, args.capabilities_file
        )
        HeartbeatLoop._emit({"heartbeat": "capabilities", "note": cap_note})
        context_limit, context_limit_source = resolve_context_limit(
            args, log_path=args.log_path
        )
        HeartbeatLoop._emit({
            "heartbeat": "launch",
            # `inherited` is loud: the process is being built on a remembered
            # belief about a substrate nobody just asked (a dark boot, the GPU
            # lent out). The door will not claim until discovery confirms it.
            "note": ("!!! " if context_limit_source == "inherited" else "") + (
                f"context ceiling: {context_limit} tokens ({context_limit_source})"
                if context_limit else
                f"context ceiling: none managed by the loop ({context_limit_source})"
            ),
        })
        transport_timeout, transport_timeout_source = resolve_transport_timeout(
            base_url, getattr(args, "timeout", None)
        )
        HeartbeatLoop._emit({
            "heartbeat": "launch",
            "note": f"transport timeout: {transport_timeout:g}s ({transport_timeout_source}); a read timeout is not retried",
        })
        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            max_tokens=args.max_tokens,
            timeout=transport_timeout,
            extra_headers=extra_headers,
            provider_name=args.provider,
            capability=capability,
            openrouter_require_parameters=(
                args.provider == "openrouter"
                and not args.no_openrouter_require_parameters
            ),
            wake_mode=wake_mode,
            openrouter_cache=not args.no_openrouter_cache,
            openrouter_cache_ttl=args.openrouter_cache_ttl,
            context_limit=context_limit,
        )

    assembly_binding, assembly_note = resolve_assembly_binding(
        args.project_root, args.log_path, event_log_path
    )
    HeartbeatLoop._emit({"heartbeat": "launch", "note": assembly_note})

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
        system_prompt_prefix=build_constitution(
            budget, gpu_lease=bool(store.lease_binding), assembly=bool(assembly_binding),
            plaza=bool(assembly_binding and assembly_binding.members.plaza),
        ),
        wake_mode=wake_mode,
        assembly=assembly_binding,
        launch_config={
            "model": args.model,
            "provider": args.provider,
            "tools": True,
            "capabilities_file": (
                args.capabilities_file
                or (DEFAULT_CAPABILITIES_FILE if args.provider != "anthropic" else None)
            ),
            "openrouter_require_parameters": (
                args.provider == "openrouter"
                and not args.no_openrouter_require_parameters
            ),
            "wake_mode": wake_mode,
            "base_url": args.base_url,
            "context_limit": context_limit,
            "context_limit_source": context_limit_source,
        },
    )
    guard = None
    if store.lease_binding:
        # Belt and braces: whichever provider branch ran, a bound door without a
        # base_url has nothing to probe and must not reach the loop.
        assert_lease_door_has_base_url(store.lease_binding, base_url)
        # Imported here, not at module scope: gate.py reaches back into this
        # module for append_heartbeat_status.
        from hamutay.gpu_lease.actions import Ctx
        from hamutay.gpu_lease.gate import LeaseGate
        from hamutay.gpu_lease.state import paths as lease_paths
        from hamutay.gpu_lease.systemd import Systemd

        ctx = Ctx(
            lease_paths(),
            Systemd(),
            now=lambda: datetime.now(timezone.utc),
            by=f"heartbeat:{Path(args.log_path).parent.name}",
        )
        guard = LeaseGate(
            store, ctx, base_url=base_url, session=session,
            discover=None, explicit_limit=args.context_limit,
        )
        HeartbeatLoop._emit({
            "heartbeat": "launch",
            "note": f"gpu lease: {store.lease_binding} (door.json)",
        })
    loop = HeartbeatLoop(
        session,
        store,
        poll_interval=args.poll_interval,
        batch_limit=args.batch_limit,
        ledger=DailyLedger(args.log_path),
        budget=budget,
        guard=guard,
        assembly=assembly_binding,
        summarize=_summarize_for(assembly_binding),
        run_pending=_run_pending_for(
            assembly_binding, store,
            lambda s: HeartbeatLoop._emit({"heartbeat": "plaza", "error": s}),
        ),
    )
    try:
        loop.run_forever()
    finally:
        lock_handle.close()


if __name__ == "__main__":
    main()
