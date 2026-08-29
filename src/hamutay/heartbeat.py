"""Heartbeat: the always-on daemon that gives the event loop wall-clock life.

Spec: docs/superpowers/specs/2026-08-26-heartbeat-founding-spec.md
The log is the life; the process is weather. Boot always runs recovery.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
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
    ):
        self._session = session
        self._store = store
        self._ledger = ledger
        self._budget = budget
        self._resting_day: str | None = None
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
        self,
        status: str,
        *,
        reason: str,
        detail: dict | None = None,
        now: datetime | None = None,
    ) -> None:
        if (status, reason) == self._last_transition:
            return
        stamp = _as_utc(now).isoformat() if now is not None else None
        record = append_heartbeat_status(
            self._store, status=status, reason=reason, detail=detail, created_at=stamp
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
        already_resting_today = (
            self._last_transition == ("resting", "daily_budget_reached")
            and self._resting_day == day["day"]
        )
        if not already_resting_today:
            # One episode per UTC day: a rest record for this day already in
            # the store means a restart interrupted it; continue, don't start.
            # A new day that is also exceeded is a new episode, so the
            # (status, reason) de-dup must not swallow it.
            self._last_transition = None
            self._resting_day = day["day"]
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
                "resting", reason="daily_budget_reached", detail=detail, now=now
            )
        remaining = (resumes_at - _as_utc(now)).total_seconds()
        return {
            "state": "resting",
            "sleep_seconds": min(max(remaining, 0.0), self._poll_interval),
            "batch": None,
        }

    def step(self) -> dict:
        now = self._now()
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
            # batch_limit of them.
            limit=1 if self._budget is not None else self._batch_limit,
            stop_on_failure=False,
            now=now,
            auto_continuations=True,
            policy_dispositions=True,
        )
        # Ingress can land after next_pending() above and still be claimed by
        # the batch.  Use the batch result as the authoritative second signal
        # so that such a wake cannot disappear between two identical quiet
        # transitions.
        if batch.get("ran", 0):
            self._transition("active", reason="runnable_pending", now=now)
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
        reason = derive_quiet_reason(self._store.read_records())
        self._transition("quiet", reason=reason, now=now)
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


def build_constitution(budget: "WakeBudget | None") -> str:
    """The operational prefix as configured: true under either setting."""
    if budget is None:
        return _CONSTITUTION_BASE + UNBUDGETED_SENTENCE
    return _CONSTITUTION_BASE + BUDGET_SENTENCE.format(
        usd=f" of {budget.daily_usd:.2f} USD",
        wakes=f" of {budget.daily_wakes} wakes",
    )


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
        },
        inherited,
        defaults=HEARTBEAT_LAUNCH_DEFAULTS,
    )
    return launch, notes


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
        default=5.0,
        help="Cost ceiling per UTC day for this resident (default 5.00).",
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

    launch, launch_notes = resolve_heartbeat_launch(args)
    args.model, args.provider = launch["model"], launch["provider"]
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
        capability, cap_note = load_capability_profile(
            args.provider, args.model, args.capabilities_file
        )
        HeartbeatLoop._emit({"heartbeat": "capabilities", "note": cap_note})
        backend = OpenAITasteBackend(
            base_url=base_url,
            api_key=api_key,
            max_tokens=args.max_tokens,
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
        system_prompt_prefix=build_constitution(budget),
        wake_mode=wake_mode,
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
        },
    )
    store = EventStore(event_log_path)
    loop = HeartbeatLoop(
        session,
        store,
        poll_interval=args.poll_interval,
        batch_limit=args.batch_limit,
        ledger=DailyLedger(args.log_path),
        budget=budget,
    )
    try:
        loop.run_forever()
    finally:
        lock_handle.close()


if __name__ == "__main__":
    main()
