from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from hamutay.events import EventStore, build_pending_event
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.restart_frontier import RestartFrontierStore
from hamutay.scheduler import ClockPort, EventQueue, SchedulerClock, WallClock


RUN_ID = "wall-clock-boundary"
BASE_TIME = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
RID = UUID("90000000-0000-0000-0000-000000000001")


def _iso(value: datetime) -> str:
    return value.isoformat()


def _event(
    *,
    event_id: str,
    now: datetime,
    not_before_delta: timedelta,
    expires_delta: timedelta | None = None,
    priority: int = 0,
) -> dict:
    event = build_pending_event(
        purpose=f"boundary {event_id}",
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
        ("wall", WallClock()),
    ]


def test_clock_port_accepts_des_and_wall_clock_without_exposing_advance_on_wall():
    des = SchedulerClock.start(BASE_TIME)
    wall = WallClock()

    assert isinstance(des.now(), datetime)
    assert des.now_iso() == BASE_TIME.isoformat()
    assert isinstance(wall.now(), datetime)
    assert wall.now().tzinfo is not None
    assert not hasattr(wall, "advance_to")


def test_des_and_wall_clock_due_ordering_match_by_scheduler_semantics():
    for _name, clock in _clock_cases():
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

        claims = []
        while claim := queue.claim_next_due(now=clock.now()):
            claims.append(claim.event["event_id"])

        assert claims == ["earlier", "priority", "later"]


def test_des_and_wall_clock_expiration_semantics_match():
    for _name, clock in _clock_cases():
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

        assert claim is not None
        assert claim.running["status"] == "expired"
        assert [record["status"] for record in queue.records] == [
            "pending",
            "expired",
        ]


def test_des_and_wall_clock_next_wake_reporting_match():
    for _name, clock in _clock_cases():
        now = clock.now()
        queue = EventQueue()
        first_wake = now + timedelta(minutes=5)
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

        assert queue.next_due(now=clock.now()) is None
        assert queue.next_wake_at(now=clock.now()) == first_wake.isoformat()


def test_des_and_wall_clock_restart_frontier_recover_running_event(tmp_path):
    for name, clock in _clock_cases():
        case_dir = tmp_path / name
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
            manifest={"clock": name},
            sandbox={"live_model_calls": False},
        )
        pending = _event(
            event_id=f"{name}-recover",
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
            notes={"clock": name, "boundary": "pending"},
        )

        claimed = events.claim_next_pending(
            now=clock.now(),
            run_id=UUID("90000000-0000-0000-0000-000000000099"),
        )
        assert claimed is not None
        assert claimed[1]["status"] == "running"

        reloaded_memory = LocalMemorySubstrate()
        reloaded = frontier.load_latest(
            run_id=str(UUID("90000000-0000-0000-0000-000000000099")),
            memory=reloaded_memory,
            ledger=ledger,
            event_store=events,
        )

        latest = events.latest_by_event_id()[pending["event_id"]]
        assert len(reloaded.recovered_event_records) == 1
        assert latest["status"] == "pending"
        assert latest["event_id"] == pending["event_id"]
