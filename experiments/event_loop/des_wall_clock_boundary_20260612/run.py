"""Goal 9 DES/wall-clock scheduler boundary probe.

This runner performs no live model calls. It compares the deterministic
SchedulerClock baseline with the WallClock adapter on scheduler semantics that
should not depend on real elapsed time.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import EventStore, build_pending_event
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.restart_frontier import RestartFrontierStore
from hamutay.scheduler import ClockPort, EventQueue, SchedulerClock, WallClock


ARTIFACT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = ARTIFACT_DIR / "results.json"
ROWS_DIR = ARTIFACT_DIR / "rows"
EXPERIMENT_ID = "des_wall_clock_boundary_20260612"
BASE_TIME = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
RUN_ID = "goal9-des-wall-clock-boundary"
RID = UUID("91000000-0000-0000-0000-000000000001")
RECOVERY_RUN_ID = UUID("91000000-0000-0000-0000-000000000099")


JsonDict = dict[str, Any]


@dataclass
class ProbeResult:
    ok: bool
    observed: JsonDict
    failure_layer: str | None = None
    failure: str | None = None

    def to_dict(self) -> JsonDict:
        payload: JsonDict = {"ok": self.ok, "observed": self.observed}
        if self.failure_layer:
            payload["failure_layer"] = self.failure_layer
        if self.failure:
            payload["failure"] = self.failure
        return payload


def _iso(value: datetime) -> str:
    return value.isoformat()


def _event(
    *,
    event_id: str,
    now: datetime,
    not_before_delta: timedelta,
    expires_delta: timedelta | None = None,
    priority: int = 0,
) -> JsonDict:
    event = build_pending_event(
        purpose=f"Goal 9 boundary probe {event_id}",
        requested_context=[{"tool": "recall", "record_id": str(RID)}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=RID,
        not_before=_iso(now + not_before_delta),
        expires_at=(
            _iso(now + expires_delta) if expires_delta is not None else None
        ),
    )
    event["event_id"] = event_id
    event["created_at"] = _iso(now - timedelta(minutes=1))
    event["priority"] = priority
    return event


def _clock_cases() -> list[tuple[str, ClockPort]]:
    return [
        ("des", SchedulerClock.start(BASE_TIME)),
        ("wall_clock", WallClock()),
    ]


def _due_order(clock: ClockPort) -> ProbeResult:
    now = clock.now()
    queue = EventQueue()
    queue.append_pending(
        _event(
            event_id="later",
            now=now,
            not_before_delta=timedelta(seconds=-1),
            priority=2,
        )
    )
    queue.append_pending(
        _event(
            event_id="earlier",
            now=now,
            not_before_delta=timedelta(seconds=-2),
            priority=9,
        )
    )
    queue.append_pending(
        _event(
            event_id="priority",
            now=now,
            not_before_delta=timedelta(seconds=-1),
            priority=1,
        )
    )
    queue.append_pending(
        _event(
            event_id="waiting",
            now=now,
            not_before_delta=timedelta(hours=1),
        )
    )
    observed: list[str] = []
    while claim := queue.claim_next_due(now=clock.now()):
        observed.append(str(claim.event["event_id"]))
    expected = ["earlier", "priority", "later"]
    return ProbeResult(
        ok=observed == expected,
        observed={"claim_order": observed, "expected": expected},
        failure_layer=None if observed == expected else "semantic_scheduler",
        failure=None if observed == expected else "due ordering diverged",
    )


def _expiration(clock: ClockPort) -> ProbeResult:
    now = clock.now()
    queue = EventQueue()
    queue.append_pending(
        _event(
            event_id="expired",
            now=now,
            not_before_delta=timedelta(hours=1),
            expires_delta=timedelta(seconds=-1),
        )
    )
    claim = queue.claim_next_due(now=clock.now())
    statuses = [record["status"] for record in queue.records]
    ok = (
        claim is not None
        and claim.running["status"] == "expired"
        and statuses == ["pending", "expired"]
    )
    return ProbeResult(
        ok=ok,
        observed={"claim_status": claim.running["status"] if claim else None, "statuses": statuses},
        failure_layer=None if ok else "semantic_scheduler",
        failure=None if ok else "expiration did not terminalize pending event",
    )


def _next_wake(clock: ClockPort) -> ProbeResult:
    now = clock.now()
    first_wake = now + timedelta(minutes=5)
    queue = EventQueue()
    queue.append_pending(
        _event(
            event_id="second-waiting",
            now=now,
            not_before_delta=timedelta(minutes=10),
        )
    )
    queue.append_pending(
        _event(
            event_id="first-waiting",
            now=now,
            not_before_delta=timedelta(minutes=5),
        )
    )
    due = queue.next_due(now=clock.now())
    next_wake = queue.next_wake_at(now=clock.now())
    ok = due is None and next_wake == first_wake.isoformat()
    return ProbeResult(
        ok=ok,
        observed={
            "next_due_event_id": due.get("event_id") if due else None,
            "next_wake_at": next_wake,
            "expected_next_wake_at": first_wake.isoformat(),
        },
        failure_layer=None if ok else "semantic_scheduler",
        failure=None if ok else "next wake reporting diverged",
    )


def _restart_frontier(clock_name: str, clock: ClockPort) -> ProbeResult:
    case_dir = ROWS_DIR / clock_name / "restart_frontier"
    case_dir.mkdir(parents=True, exist_ok=True)
    ledger = ActionLedger(case_dir / "actions.jsonl")
    events = EventStore(case_dir / "events.jsonl")
    memory = LocalMemorySubstrate()
    frontier = RestartFrontierStore(
        frontier_path=case_dir / "frontier.jsonl",
        memory_snapshot_path=case_dir / "memory_snapshot.json",
    )
    frontier.ensure_run_manifest(
        ledger=ledger,
        run_id=RUN_ID,
        manifest={"experiment_id": EXPERIMENT_ID, "clock": clock_name},
        sandbox={"live_model_calls": False, "clock_mode": clock_name},
    )
    pending = _event(
        event_id=f"{clock_name}-recover",
        now=clock.now(),
        not_before_delta=timedelta(seconds=-1),
    )
    events.append(pending)
    frontier.commit_frontier(
        run_id=RUN_ID,
        cycle_id=0,
        result_record_id=None,
        memory=memory,
        ledger=ledger,
        event_store=events,
        notes={"clock": clock_name, "boundary": "pending"},
    )
    claimed = events.claim_next_pending(now=clock.now(), run_id=RECOVERY_RUN_ID)
    loaded = frontier.load_latest(
        run_id=str(RECOVERY_RUN_ID),
        memory=LocalMemorySubstrate(),
        ledger=ledger,
        event_store=events,
    )
    latest = events.latest_by_event_id()[pending["event_id"]]
    ok = (
        claimed is not None
        and claimed[1]["status"] == "running"
        and len(loaded.recovered_event_records) == 1
        and latest["status"] == "pending"
    )
    return ProbeResult(
        ok=ok,
        observed={
            "claimed_status": claimed[1]["status"] if claimed else None,
            "recovered_count": len(loaded.recovered_event_records),
            "latest_status": latest["status"],
            "ledger_verification_ok": loaded.ledger_verification.ok,
        },
        failure_layer=None if ok else "semantic_scheduler",
        failure=None if ok else "restart frontier did not recover running event",
    )


def _run_clock_case(name: str, clock: ClockPort) -> JsonDict:
    probes = {
        "due_ordering": _due_order(clock),
        "expiration": _expiration(clock),
        "next_wake_reporting": _next_wake(clock),
        "restart_frontier": _restart_frontier(name, clock),
    }
    return {
        "clock": name,
        "clock_now_sample": clock.now_iso(),
        "ok": all(result.ok for result in probes.values()),
        "probes": {key: value.to_dict() for key, value in probes.items()},
    }


def _classify(rows: list[JsonDict]) -> JsonDict:
    semantic_failures: list[JsonDict] = []
    runtime_failures: list[JsonDict] = []
    for row in rows:
        for probe_name, probe in row["probes"].items():
            if probe["ok"]:
                continue
            failure = {
                "clock": row["clock"],
                "probe": probe_name,
                "failure_layer": probe.get("failure_layer"),
                "failure": probe.get("failure"),
            }
            if row["clock"] == "wall_clock":
                runtime_failures.append(failure)
            else:
                semantic_failures.append(failure)
    des = next(row for row in rows if row["clock"] == "des")
    wall = next(row for row in rows if row["clock"] == "wall_clock")
    return {
        "classification": "passed" if des["ok"] and wall["ok"] else "failed",
        "des_semantic_baseline_ok": des["ok"],
        "wall_clock_boundary_ok": wall["ok"],
        "semantic_scheduler_failures": semantic_failures,
        "runtime_availability_failures": runtime_failures,
        "requires_wall_clock_for_current_research_claim": False,
    }


def main() -> None:
    if ROWS_DIR.exists():
        shutil.rmtree(ROWS_DIR)
    ROWS_DIR.mkdir(parents=True)
    rows: list[JsonDict] = []
    for name, clock in _clock_cases():
        try:
            row = _run_clock_case(name, clock)
        except Exception as exc:  # pragma: no cover - exercised by artifact runs.
            row = {
                "clock": name,
                "ok": False,
                "probes": {},
                "failure_layer": (
                    "runtime_availability"
                    if name == "wall_clock" else "semantic_scheduler"
                ),
                "failure": f"{type(exc).__name__}: {exc}",
            }
        rows.append(row)
        (ROWS_DIR / f"{name}.json").write_text(
            json.dumps(row, indent=2, sort_keys=True, default=str) + "\n"
        )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": False,
        "rows": rows,
        "comparison": _classify(rows),
    }
    RESULTS_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n"
    )
    print(json.dumps(result["comparison"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
