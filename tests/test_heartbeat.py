"""Development tests for the heartbeat daemon.

Plan: docs/superpowers/plans/2026-08-26-heartbeat.md
Validating tests are authored separately by Codex per repo norm; these are
the implementer's TDD tests.
"""
from uuid import uuid4

from hamutay.events import EventStore, build_inbound_event
from hamutay.heartbeat import (
    recover_lost_continuations,
    recover_orphaned_running,
)


def _crashed_mid_wake(store):
    event = build_inbound_event(purpose="interrupted work", sender="tony")
    store.append(event)
    store.append_running(event)
    return event


def test_recover_orphaned_running_repends_original(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = _crashed_mid_wake(store)
    recovered = recover_orphaned_running(store)
    assert len(recovered) == 1
    latest = store.latest_by_event_id()[event["event_id"]]
    assert latest["status"] == "pending"
    assert latest["purpose"] == "interrupted work"
    assert latest["recovered_by"] == "boot_recovery"
    assert latest["recovered_from_run_id"]


def test_recover_orphaned_running_is_idempotent(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _crashed_mid_wake(store)
    recover_orphaned_running(store)
    assert recover_orphaned_running(store) == []


def test_recover_orphaned_running_ignores_terminal_events(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="done work", sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
    )
    assert recover_orphaned_running(store) == []


def test_heartbeat_status_record_shape(tmp_path):
    from hamutay.heartbeat import append_heartbeat_status

    store = EventStore(str(tmp_path / "events.jsonl"))
    record = append_heartbeat_status(
        store, status="quiet", reason="chosen_quiet", detail={"note": "test"}
    )
    assert record["record_type"] == "heartbeat_status"
    assert record["status"] == "quiet"
    assert record["reason"] == "chosen_quiet"
    assert record["created_at"]
    assert "event_id" not in record
    persisted = store.read_records()
    assert persisted[-1]["record_type"] == "heartbeat_status"


def test_heartbeat_status_does_not_disturb_the_queue(tmp_path):
    from hamutay.heartbeat import append_heartbeat_status

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="real work", sender="tony")
    store.append(event)
    append_heartbeat_status(store, status="active", reason="runnable_pending")
    claimable = store.next_pending()
    assert claimable is not None
    assert claimable["event_id"] == event["event_id"]


def test_derive_quiet_reason_awaiting_first_event(tmp_path):
    from hamutay.heartbeat import derive_quiet_reason

    store = EventStore(str(tmp_path / "events.jsonl"))
    assert derive_quiet_reason(store.read_records()) == "awaiting_first_event"


def test_derive_quiet_reason_starved_on_expiry(tmp_path):
    from hamutay.heartbeat import derive_quiet_reason

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(event)
    store.append_expired(event)
    assert derive_quiet_reason(store.read_records()) == "starved_expired"


def test_derive_quiet_reason_chosen_after_clean_completion(tmp_path):
    from hamutay.heartbeat import derive_quiet_reason

    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="work", sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done, resting",
    )
    assert derive_quiet_reason(store.read_records()) == "chosen_quiet"


class _StubSession:
    pass


def _loop(tmp_path, *, summaries, batch=None):
    """A HeartbeatLoop with stubbed run/summarize; summaries consumed in order."""
    from hamutay.heartbeat import HeartbeatLoop

    store = EventStore(str(tmp_path / "events.jsonl"))
    sleeps = []
    summary_iter = iter(summaries)

    loop = HeartbeatLoop(
        _StubSession(),
        store,
        poll_interval=30.0,
        sleep=sleeps.append,
        run_pending=lambda session, s, **kw: batch or {"results": []},
        summarize=lambda records, now=None: next(summary_iter),
    )
    return loop, store, sleeps


def test_step_active_when_runnable(tmp_path):
    loop, store, _ = _loop(
        tmp_path,
        summaries=[{"pending_runnable_count": 2, "pending_waiting_count": 0}],
    )
    result = loop.step()
    assert result["state"] == "active"
    assert result["sleep_seconds"] == 0.0


def test_step_waiting_sleeps_until_wake_capped_by_poll(tmp_path):
    from datetime import datetime, timedelta, timezone

    wake_at = (datetime.now(timezone.utc) + timedelta(seconds=7)).isoformat()
    loop, store, _ = _loop(
        tmp_path,
        summaries=[
            {
                "pending_runnable_count": 0,
                "pending_waiting_count": 1,
                "oldest_waiting_pending": {"not_before": wake_at},
            }
        ],
    )
    result = loop.step()
    assert result["state"] == "waiting"
    assert 0.0 < result["sleep_seconds"] <= 30.0


def test_step_quiet_appends_status_once_per_transition(tmp_path):
    quiet_summary = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    loop, store, _ = _loop(tmp_path, summaries=[quiet_summary, quiet_summary])
    loop.step()
    loop.step()
    statuses = [
        r for r in store.read_records() if r.get("record_type") == "heartbeat_status"
    ]
    assert len(statuses) == 1
    assert statuses[0]["status"] == "quiet"
    assert statuses[0]["reason"] == "awaiting_first_event"


def test_quiet_to_work_to_quiet_leaves_a_trace(tmp_path):
    """Cross-family finding 2: a wake completed entirely inside one batch must
    still record active, and the return to quiet must record chosen_quiet."""
    from hamutay.heartbeat import HeartbeatLoop

    quiet_summary = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="quick work", sender="tony")

    def fake_run(session, s, **kw):
        if s.next_pending() is None:
            return {"results": []}
        s.append_running(event)
        s.append_completed(
            event=event,
            run_id=str(uuid4()),
            wake_cycle=1,
            result_record_id=uuid4(),
            response_text="done",
        )
        return {"results": [{"status": "completed"}]}

    summary_iter = iter([quiet_summary, quiet_summary])
    loop = HeartbeatLoop(
        _StubSession(),
        store,
        poll_interval=30.0,
        sleep=lambda s: None,
        run_pending=fake_run,
        summarize=lambda records, now=None: next(summary_iter),
    )
    loop.step()  # empty store: quiet/awaiting_first_event
    store.append(event)
    loop.step()  # work arrives and completes inside this one step
    trace = [
        (r["status"], r["reason"])
        for r in store.read_records()
        if r.get("record_type") == "heartbeat_status"
    ]
    assert trace == [
        ("quiet", "awaiting_first_event"),
        ("active", "runnable_pending"),
        ("quiet", "chosen_quiet"),
    ]


def test_quiet_reason_change_is_recorded(tmp_path):
    """Cross-family finding 2b: dedup by (status, reason) — a starvation that
    arrives while already quiet must still be recorded."""
    quiet_summary = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    loop, store, _ = _loop(tmp_path, summaries=[quiet_summary, quiet_summary])
    loop.step()  # quiet/awaiting_first_event
    event = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(event)
    store.append_expired(event)
    loop.step()
    trace = [
        (r["status"], r["reason"])
        for r in store.read_records()
        if r.get("record_type") == "heartbeat_status"
    ]
    assert trace[-1] == ("quiet", "starved_expired")
    assert len(trace) == 2


def test_boot_recovers_and_announces(tmp_path):
    loop, store, _ = _loop(tmp_path, summaries=[])
    event = build_inbound_event(purpose="interrupted", sender="tony")
    store.append(event)
    store.append_running(event)
    report = loop.boot()
    assert report["orphaned_running_recovered"] == 1
    statuses = [
        r for r in store.read_records() if r.get("record_type") == "heartbeat_status"
    ]
    assert statuses[-1]["status"] == "waking"


def test_recover_lost_continuations_declares_the_loss(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    event = build_inbound_event(purpose="work", sender="tony")
    store.append(event)
    store.append_running(event)
    lost_id = str(uuid4())
    # Simulate the crash gap: completed record annotated, continuation
    # never appended (append_completed alone does exactly this).
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=1,
        result_record_id=uuid4(),
        response_text="done",
        auto_continuation_event={"event_id": lost_id},
    )
    recovered = recover_lost_continuations(store)
    assert len(recovered) == 1
    replacement = store.latest_by_event_id()[lost_id]
    assert replacement["status"] == "pending"
    assert "declared_loss" in replacement
    assert replacement["recovered_by"] == "boot_recovery"
    assert recover_lost_continuations(store) == []


def test_heartbeat_parser_defaults():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x.jsonl"])
    assert args.max_tokens == 64000
    assert args.poll_interval == 30.0
    assert args.batch_limit == 10
    # Substrate flags default to "inherit from the log"; a fresh log takes
    # HEARTBEAT_LAUNCH_DEFAULTS (see tests/test_wake_mode_defaults.py).
    assert args.model is None
    assert args.provider is None
    assert args.wake_mode is None


def test_no_constitution_bypass_exists():
    import pytest

    from hamutay.heartbeat import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(["--log-path", "x.jsonl", "--no-constitution"])


def test_single_instance_lock(tmp_path):
    import pytest

    from hamutay.heartbeat import acquire_lock

    lock_path = str(tmp_path / "hb.lock")
    held = acquire_lock(lock_path)
    assert held is not None
    with pytest.raises(SystemExit):
        acquire_lock(lock_path)
    held.close()


def test_constitution_is_operational_not_cognitive():
    from hamutay.heartbeat import CONSTITUTION

    lowered = CONSTITUTION.lower()
    # Operational facts must be present.
    assert "recover" in lowered
    assert "decline" in lowered
    # Cognitive priors must be absent (no-harness-priors norm).
    for banned in ("strand", "curate", "curation", "compact", "schema"):
        assert banned not in lowered


def test_heartbeat_parser_capability_flags():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x.jsonl"])
    assert args.capabilities_file is None
    assert args.no_openrouter_require_parameters is False


def test_load_capability_profile_for_the_resident():
    from hamutay.heartbeat import load_capability_profile

    profile, note = load_capability_profile(
        "openrouter",
        "anthropic/claude-haiku-4-5",
        "experiments/taste_open/capabilities.json",
    )
    assert profile.supports_tools
    assert profile.tool_choice_mode == "function_object"
    assert "anthropic/claude-haiku-4-5" in note


def test_load_capability_profile_missing_file_falls_back(tmp_path):
    from hamutay.heartbeat import load_capability_profile

    profile, note = load_capability_profile(
        "openrouter", "some/model", str(tmp_path / "nope.json")
    )
    assert profile.supports_tools
    assert "not found" in note


def test_load_capability_profile_missing_entry_falls_back(tmp_path):
    import json as _json

    from hamutay.heartbeat import load_capability_profile

    path = tmp_path / "caps.json"
    path.write_text(_json.dumps({"openrouter:other/model": {"supports_tools": True}}))
    profile, note = load_capability_profile("openrouter", "some/model", str(path))
    assert profile.supports_tools
    assert "no capabilities entry" in note


def test_step_emits_completed_responses(tmp_path, capsys):
    batch = {
        "results": [
            {
                "status": "completed",
                "response_text": "hello tony",
                "event_id": "e1",
            }
        ],
        "ran": 1,
    }
    loop, store, _ = _loop(
        tmp_path,
        summaries=[{"pending_runnable_count": 0, "pending_waiting_count": 0}],
        batch=batch,
    )
    loop.step()
    out = capsys.readouterr().out
    assert "hello tony" in out
    assert "wake_completed" in out


def test_constitution_declares_wake_ending_physics():
    from hamutay.heartbeat import CONSTITUTION

    lowered = CONSTITUTION.lower()
    assert "wake ends" in lowered
    assert "prose" in lowered
