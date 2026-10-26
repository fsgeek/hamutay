"""Contract §§6–9: real claims, wake runner, envelopes and heartbeat."""
from datetime import datetime, timedelta, timezone
import json
import re
from uuid import uuid4

import pytest

from hamutay.events import build_inbound_event, build_quiet_declaration
from hamutay.heartbeat import HeartbeatLoop, recover_orphaned_running

from .support import FILTER, NOW, Session, board_event, event_id, ok, opening, update


def ready(house, count=1):
    rows = house.many(count)
    house.filter()
    house.notice_done()
    house.queue(rows)
    return rows


def statuses(house, status):
    return [r for r in house.store.read_records() if r.get("event_type") == "board_match" and r.get("status") == status]


def external(house, when=NOW, purpose="Independent message"):
    event = build_inbound_event(purpose=purpose, sender="tony")
    event["created_at"] = when.isoformat()
    house.store.append(event)
    return event


def test_parked_events_and_unparking(house):
    ready(house, 2)
    house.gate.unlink()
    before = house.snapshot()
    assert house.store.next_pending(now=NOW) is None
    assert house.store.claim_next_pending(now=NOW) is None
    summary = house.summary()
    assert summary["pending_runnable_count"] == summary["pending_waiting_count"] == 0
    assert summary["pending_board_parked_count"] == 2
    assert house.snapshot() == before
    event = external(house)
    assert house.store.claim_next_pending(now=NOW)[0]["event_id"] == event["event_id"]
    house.gate.touch()
    assert house.store.next_pending(now=NOW)["event_type"] == "board_match"
    assert house.summary()["pending_runnable_count"] == 2


def test_coalesced_completion(house):
    ready(house, 4)
    result, session = house.run()
    assert result["status"] == "completed" and len(session.messages) == 1 and session.cycle == 1
    running = statuses(house, "running")
    completed = statuses(house, "completed")
    assert len(running) == len(completed) == 4
    assert len({r["run_id"] for r in running + completed}) == 1
    assert len({r["started_at"] for r in running}) == 1
    assert all(r["board_snapshot_seq"] == 4 for r in running)
    assert len({r["wake_cycle"] for r in completed}) == len({r["result_record_id"] for r in completed}) == 1
    primary = result["event_id"]
    assert completed[-1]["event_id"] == primary
    assert completed[-1]["response_text"] == "Synthetic board response"
    for row in completed[:-1]:
        assert row["completed_with_event_id"] == primary
        assert not row.get("response_text")
    assert not house.matches(status="pending")
    house.pass_()
    assert not house.matches(status="pending")
    assert house.run()[0]["status"] == "none"


@pytest.mark.parametrize("first", ["board", "external"])
def test_non_board_ordering_and_separation(house, first):
    ready(house, 3)
    ext = external(house, NOW + timedelta(seconds=1 if first == "board" else -1))
    result, session = house.run()
    assert len(session.messages) == 1
    assert (result["event_id"] == ext["event_id"]) == (first == "external")
    assert len(statuses(house, "running")) == (3 if first == "board" else 0)
    other, _ = house.run()
    assert (other["event_id"] == ext["event_id"]) == (first == "board")


@pytest.mark.parametrize("reason", ["generation", "clear", "passed"])
def test_claim_supersedes_and_reaches_other_event(house, reason):
    rows = ready(house)
    if reason == "generation":
        house.filter(generation=2)
    elif reason == "clear":
        house.filter(None, generation=2)
    else:
        # Only an update is superseded by passing.
        house.seed([rows[0], update(rows[0], 2)])
        house.queue([house.rows()[1]])
        house.store.append({"record_type": "board_pass", "door": "alpha",
                            "opportunity_id": rows[0]["opportunity_id"], "recorded_at": NOW.isoformat()})
        # Complete the opening so the update is the only pending board event.
        house.store.append({"record_type": "event_status", "event_id": event_id("alpha", 1),
            "event_type": "board_match", "status": "completed", "run_id": str(uuid4()),
            "completed_at": NOW.isoformat(), "wake_cycle": 1, "result_record_id": str(uuid4())})
    eid = event_id("alpha", 2 if reason == "passed" else 1)
    ext = external(house, NOW + timedelta(seconds=1))
    summary = house.summary()
    assert summary["pending_runnable_count"] == 1 and summary["pending_waiting_count"] == 0
    claim = house.store.claim_next_pending(now=NOW)
    assert claim[0]["event_id"] == ext["event_id"]
    suppressed = house.store.latest_by_event_id()[eid]
    assert suppressed["status"] == "suppressed" and suppressed["superseded"] is True
    assert suppressed["suppressed_by_policy"] == "board"
    assert suppressed["suppression_reason"] == {"generation": "superseded_by_generation", "clear": "filter_cleared", "passed": "passed"}[reason]
    assert suppressed["superseded_by_generation"] == (1 if reason == "passed" else 2)


@pytest.mark.parametrize("count", [1, 10, 11, 30, 35])
def test_envelope_bounds_and_uncovered_remainder(house, count):
    rows = ready(house, count)
    result, session = house.run()
    envelope = session.messages[0]
    assert envelope["event_type"] == "board_match" and envelope["origin"] == "board"
    text, meta = envelope["board_text"], envelope["board"]
    assert len(text) <= 12000
    required = {"generation", "filter", "snapshot_seq", "entries_full", "entries_titles",
                "entries_full_ids", "entries_titles_ids", "remaining_entries",
                "remaining_events", "batch_event_ids", "coverage_after_this_wake"}
    assert required <= set(meta)
    for field in ("generation", "snapshot_seq", "entries_full", "entries_titles",
                  "remaining_entries", "remaining_events", "coverage_after_this_wake"):
        assert type(meta[field]) is int, (field, meta[field])
    for field in ("entries_full_ids", "entries_titles_ids", "batch_event_ids"):
        assert isinstance(meta[field], list) and all(isinstance(value, str) for value in meta[field])
    assert meta["filter"] == FILTER and meta["generation"] == 1 and meta["snapshot_seq"] == count
    assert 1 <= meta["entries_full"] <= 10 and 0 <= meta["entries_titles"] <= 20
    shown = {r["opportunity_id"] for r in rows if r["opportunity_id"] in text}
    rendered = meta["entries_full"] + meta["entries_titles"]
    assert len(shown) == rendered
    assert len(meta["entries_full_ids"]) == meta["entries_full"]
    assert len(meta["entries_titles_ids"]) == meta["entries_titles"]
    rendered_ids = meta["entries_full_ids"] + meta["entries_titles_ids"]
    assert len(set(rendered_ids)) == rendered and set(rendered_ids) == shown
    assert rendered_ids == sorted(rendered_ids, key=text.index)
    completed = {r["event_id"] for r in statuses(house, "completed")}
    expected = {event_id("alpha", r["seq"]) for r in rows if r["opportunity_id"] in shown}
    assert len(meta["batch_event_ids"]) == len(completed)
    assert set(meta["batch_event_ids"]) == completed == expected
    assert meta["coverage_after_this_wake"] == rendered
    pending = house.matches(status="pending")
    assert meta["remaining_entries"] == meta["remaining_events"] == count - rendered == len(pending)
    assert {r["board"]["opportunity_id"] for r in pending}.isdisjoint(shown)
    house.pass_()
    assert {r["event_id"] for r in house.matches(status="pending")} == {r["event_id"] for r in pending}
    if count > 30:
        assert pending and "pending" in text.lower()
        second, following = house.run(now=NOW + timedelta(minutes=1))
        assert second["status"] == "completed"
        assert len(following.messages) == 1
        second_ids = set(following.messages[0]["board"]["batch_event_ids"])
        assert second_ids.isdisjoint(completed) and second_ids <= {r["event_id"] for r in pending}


def test_full_envelope_current_state(house):
    row, = ready(house)
    house.seed([row, update(row, 2, text="Current evidence"),
                update(row, 3, "status", status="closed", reason="Finished already")])
    _, session = house.run()
    text = session.messages[0]["board_text"]
    for value in [row["title"], row["opportunity_id"], "closed", "Finished already", row["kind"],
                  row["owner"], row["posted_by"], "memory", row["what"], row["why"],
                  row["help_wanted"], row["record_of_help"], "Current evidence", "kinds", "review"]:
        assert value in text
    assert session.messages[0]["board"]["snapshot_seq"] == 3
    assert statuses(house, "running")[0]["board_snapshot_seq"] == 3


def test_long_entry_preserves_latest_notes_and_progress(house):
    row = opening(what="W" * 2000, why="Y" * 1000, help_wanted="H" * 1000, record_of_help="R" * 500)
    notes = [update(row, i, text=f"NOTE-{i:02d}-" + "n" * 980) for i in range(2, 21)]
    house.seed([row, *notes])
    house.filter()
    house.notice_done()
    house.queue([row])
    _, session = house.run()
    text = session.messages[0]["board_text"]
    # §9 r1 protects opening fields and the newest note even at the field limits.
    assert len(text) <= 12000
    for field in ("opportunity_id", "title", "what", "why", "help_wanted", "record_of_help"):
        assert row[field] in text
    assert notes[-1]["text"] in text and "NOTE-02-" not in text
    rendered_notes = [int(n) for n in re.findall(r"NOTE-(\d\d)-", text)]
    assert rendered_notes == sorted(rendered_notes, reverse=True)
    omitted = len(notes) - len(rendered_notes)
    assert re.search(rf"\b{omitted}\b", text)
    assert re.search(r"omit|not shown|left out", text, re.I)
    assert session.messages[0]["board"]["entries_full"] == 1
    assert session.messages[0]["board"]["entries_full_ids"] == [row["opportunity_id"]]
    assert session.messages[0]["board"]["entries_titles_ids"] == []


def test_only_completion_confers_coverage(house):
    row, = ready(house)
    house.store.claim_next_pending(now=NOW)
    house.seed([row, update(row, 2)])
    house.pass_()
    # A running claim is not 'shown': there must not yet be an update subscription.
    assert all(r["board"]["record_type"] == "opening" for r in house.matches())
    recover_orphaned_running(house.store)
    _, session = house.run()
    assert session.messages[0]["board"]["coverage_after_this_wake"] == 1
    house.pass_()
    assert not house.matches(status="pending")  # existing note was included at the first successful claim


def test_read_does_not_confer_coverage(house):
    row = opening()
    house.seed([row])
    ok(house.tool("board_read", {"opportunity_id": row["opportunity_id"]}))
    house.filter()
    house.notice_done()
    house.pass_()
    assert len(house.matches(status="pending")) == 1


def test_subscription_snapshot_and_updates(house):
    row = opening()
    old_note = update(row, 2)
    house.seed([row, old_note])
    house.filter()
    house.notice_done()
    house.queue([row])
    house.run()
    house.pass_()
    assert not house.matches(status="pending")
    house.seed([row, old_note, update(row, 3), update(row, 4, "status", status="taken")])
    # A different nonempty filter does not remove completed subscriptions.
    house.filter({**FILTER, "kinds": ["build"]}, generation=2)
    house.pass_()
    events = house.matches(status="pending")
    assert {r["board"]["board_seq"] for r in events} == {3, 4}
    assert all(r["board"]["clause"] is None and r["board"]["generation"] == 2 for r in events)
    _, session = house.run(now=NOW + timedelta(minutes=1))
    assert session.messages[0]["board"]["coverage_after_this_wake"] == 1
    house.seed([*house.rows(), update(row, 5, "status", status="closed")])
    house.pass_()
    pending, = house.matches(status="pending")
    assert pending["board"]["board_seq"] == 5
    house.run(now=NOW + timedelta(days=1))
    house.pass_()
    assert not house.matches(status="pending")


def test_self_updates_are_excluded(house):
    row = opening(owner="door:alpha")
    house.seed([row])
    house.filter()
    house.notice_done()
    house.queue([row])
    house.run()
    house.seed([row, update(row, 2), update(row, 3, "status")])
    house.pass_()
    assert not house.matches(status="pending")


def test_multiple_updates_render_entry_once(house):
    row, = ready(house)
    house.run()
    house.seed([row, update(row, 2), update(row, 3), update(row, 4, "status")])
    house.pass_()
    _, session = house.run(now=NOW + timedelta(minutes=1))
    meta = session.messages[0]["board"]
    assert meta["entries_full"] == 1 and meta["entries_titles"] == 0
    assert meta["entries_full_ids"] == [row["opportunity_id"]]
    assert meta["entries_titles_ids"] == []
    assert set(meta["batch_event_ids"]) == {event_id("alpha", n) for n in (2, 3, 4)}
    assert meta["coverage_after_this_wake"] == 1


def test_pass_is_door_local(house):
    row, = ready(house)
    house.run()
    ok(house.tool("board_pass", {"opportunity_id": row["opportunity_id"]}, door="beta"))
    house.seed([row, update(row, 2)])
    house.pass_()
    assert len(house.matches(status="pending")) == 1


def test_daily_cap_counts_batches_and_resets(house):
    rows = ready(house, 4)
    house.run()
    # Four running rows share one run_id: they consume only one attempt.
    more = [opening(i, posted_by="custodian") for i in (5, 6)]
    house.seed([*rows, *more])
    house.queue(more)
    assert house.store.next_pending(now=NOW) is not None
    house.run(now=NOW + timedelta(minutes=1))
    last = opening(7, posted_by="custodian")
    house.seed([*rows, *more, last])
    house.queue([last])
    assert house.store.next_pending(now=NOW) is None
    assert house.store.claim_next_pending(now=NOW) is None
    assert house.run()[0]["status"] == "none"
    # Held events do not block an unrelated inbound event.
    ext = external(house, NOW + timedelta(minutes=2))
    assert house.run()[0]["event_id"] == ext["event_id"]
    midnight = datetime(2026, 10, 16, tzinfo=timezone.utc)
    assert house.store.next_pending(now=midnight)["event_type"] == "board_match"
    assert house.run(now=midnight)[0]["status"] == "completed"


def held(house):
    rows = ready(house)
    for i in range(2):
        if i:
            row = opening(i + 1, posted_by="custodian")
            rows.append(row)
            house.seed(rows)
            house.queue([row])
        house.run(now=NOW + timedelta(minutes=i))
    final = opening(3, posted_by="custodian")
    house.seed([*rows, final])
    house.queue([final])


def test_held_summary_and_heartbeat_sleep(house):
    held(house)
    summary = house.summary()
    assert summary["pending_runnable_count"] == 0 and summary["pending_waiting_count"] == 1
    # No new summary key is invented: inspect documented per-event not_before wherever exposed.
    def bounds(obj):
        if isinstance(obj, dict):
            if obj.get("not_before"):
                yield datetime.fromisoformat(obj["not_before"].replace("Z", "+00:00"))
            for value in obj.values():
                yield from bounds(value)
        elif isinstance(obj, list):
            for value in obj:
                yield from bounds(value)
    assert datetime(2026, 10, 16, tzinfo=timezone.utc) in list(bounds(summary))
    session = Session()
    loop = HeartbeatLoop(session, house.store, now=lambda: NOW, poll_interval=30)
    for _ in range(3):
        result = loop.step()
        assert result["state"] == "waiting" and result["sleep_seconds"] > 0
    assert not session.messages
    assert len(statuses(house, "running")) == 2


def test_retries_and_crashes_count_attempts(house):
    ready(house)
    failing = Session(failure=True)
    with pytest.raises(RuntimeError, match="synthetic board wake failure"):
        house.run(failing)
    assert len(house.matches(status="pending")) == 1
    house.store.claim_next_pending(now=NOW + timedelta(minutes=1))
    recovered = recover_orphaned_running(house.store)
    assert recovered
    assert house.store.next_pending(now=NOW + timedelta(minutes=2)) is None
    assert house.summary()["pending_waiting_count"] == 1


def test_onboarding_does_not_use_daily_cap(house):
    house.filter()
    house.pass_()
    notice, _ = house.run()
    assert notice["event_type"] == "inbound_message"
    for n in (1, 2):
        rows = [*house.rows(), opening(n, posted_by="custodian")]
        house.seed(rows)
        house.pass_()
        result, _ = house.run(now=NOW + timedelta(minutes=n))
        assert result["status"] == "completed"
    assert len({r["run_id"] for r in statuses(house, "running")}) == 2


def test_timed_quiet_defers_without_expiry(house):
    ready(house)
    prior = [r for r in house.store.read_records() if r.get("status") == "completed"][-1]
    until = NOW + timedelta(days=5)
    house.store.append(build_quiet_declaration(reason="Resting", declared_by_cycle=prior["wake_cycle"],
        declared_by_record_id=prior["result_record_id"], until=until.isoformat()))
    assert house.store.next_pending(now=NOW) is None
    assert house.store.claim_next_pending(now=NOW) is None
    assert house.summary()["pending_waiting_count"] == 1
    assert not statuses(house, "expired")
    assert house.store.next_pending(now=until) is not None
    assert house.run(now=until)[0]["status"] == "completed"


def test_failure_retry_and_abandonment(house):
    rows = ready(house, 3)
    for attempt in (1, 2, 3):
        with pytest.raises(RuntimeError, match="synthetic board wake failure"):
            house.run(Session(failure=True), now=NOW + timedelta(days=attempt - 1))
        failed = statuses(house, "failed")[-3:]
        assert len(failed) == 3 and len({r["run_id"] for r in failed}) == 1
        for row in failed:
            assert row["board"]["attempt"] == attempt
            assert row["board"]["terminal"] is (attempt == 3)
            assert row["board"]["batch_size"] == 3
        pending = house.matches(status="pending")
        if attempt < 3:
            assert len(pending) == 3
            for row in rows:
                successor, = [e for e in pending if e["board"]["board_seq"] == row["seq"]]
                assert successor["event_id"] == event_id("alpha", row["seq"], attempt=attempt + 1)
                assert successor["board"]["clause"] == {"kinds": ["review"]}
                assert successor["board"]["generation"] == 1
        else:
            assert not pending
    abandoned = [r for r in house.store.read_records() if r.get("record_type") == "board_match_abandoned"]
    assert len(abandoned) == 3
    for r in abandoned:
        assert set(r) == {"record_type", "door", "board_seq", "opportunity_id", "generation", "attempts", "last_event_id", "abandoned_at"}
        assert r["attempts"] == 3 and r["last_event_id"] == event_id("alpha", r["board_seq"], attempt=3)
    house.pass_(now=NOW + timedelta(days=3))
    assert not house.matches(status="pending")
    house.filter(generation=2)
    house.pass_(now=NOW + timedelta(days=3))
    assert {r["event_id"] for r in house.matches(status="pending")} == {event_id("alpha", n, 2) for n in (1, 2, 3)}


@pytest.mark.parametrize("attempt", [1, 3])
def test_failed_batch_surfaced_once(house, attempt):
    rows = house.many(3)
    house.filter()
    house.notice_done()
    house.queue(rows, attempt=attempt)
    with pytest.raises(RuntimeError):
        house.run(Session(failure=True))
    ext = external(house, NOW - timedelta(seconds=1))
    _, session = house.run(now=NOW + timedelta(days=1))
    assert session.contexts[0].event_id == ext["event_id"]
    notes = [n for n in session.messages[0].get("operational_notes", []) if "board" in n.lower() and "fail" in n.lower()]
    assert len(notes) == 1
    note = notes[0].lower()
    assert "3" in note and ("again" in note or "retry" in note)
    # All 3 events retry after attempt 1; all 3 reach the limit at attempt 3.
    assert re.search(r"\b0\b", note) and ("limit" in note or "terminal" in note)
    # Completion surfaces the incident once, then clears the operational note.
    external(house, NOW - timedelta(seconds=2))
    _, following = house.run(now=NOW + timedelta(days=1))
    assert not [n for n in following.messages[0].get("operational_notes", []) if "board" in n.lower() and "fail" in n.lower()]


def test_crash_recovery_preserves_lineage(house):
    ready(house, 3)
    house.store.claim_next_pending(now=NOW)
    recovered = recover_orphaned_running(house.store)
    assert len(recovered) == 3
    assert {r["event_id"] for r in recovered} == {event_id("alpha", n) for n in (1, 2, 3)}
    assert all(r["board"]["attempt"] == 1 for r in recovered)
    assert house.run(now=NOW + timedelta(minutes=1))[0]["status"] == "completed"
    assert len({r["run_id"] for r in statuses(house, "running")}) == 2


def test_retry_and_update_explanations(house):
    row, = ready(house)
    with pytest.raises(RuntimeError):
        house.run(Session(failure=True))
    _, retry = house.run(now=NOW + timedelta(days=1))
    assert "offered again: attempt 2 of 3" in retry.messages[0]["board_text"].lower()
    house.seed([row, update(row, 2), update(row, 3, "status")])
    house.pass_()
    _, update_session = house.run(now=NOW + timedelta(days=2))
    text = update_session.messages[0]["board_text"].lower()
    assert "shown" in text and ("new note" in text or "status change" in text)


def test_corrupt_board_still_claims(house):
    rows = ready(house, 2)
    house.board.write_text("{broken}\n")
    result, session = house.run()
    assert result["status"] == "completed" and len(statuses(house, "completed")) == 2
    envelope = session.messages[0]
    assert envelope["board"]["board_error"]
    for row in rows:
        assert row["opportunity_id"] in envelope["board_text"]
        assert str(row["seq"]) in envelope["board_text"]
    assert re.search(r"could not|cannot|unreadable|error", envelope["board_text"], re.I)
    assert not house.matches(status="pending")


def test_write_during_failed_wake_stands(house):
    ready(house)
    written = []
    def write():
        written.append(ok(house.post(title="From a wake"))["opportunity_id"])
    with pytest.raises(RuntimeError, match="synthetic board wake failure"):
        house.run(Session(failure=True, during=write))
    assert any(r["opportunity_id"] == written[0] for r in house.rows())


def test_heartbeat_reconciles_after_plaza(house):
    house.filter()
    house.notice_done()
    session = Session()
    calls = []
    def assembly_pass(*args, **kwargs):
        calls.append("assembly")
        return {"skipped": True}, None
    def plaza_pass(*args, **kwargs):
        calls.append("plaza")
        if not house.rows():
            house.seed([opening()])
        return {"skipped": True}, None
    loop = HeartbeatLoop(session, house.store, now=lambda: NOW, assembly=house.bindings["alpha"],
                         assembly_pass=assembly_pass, plaza_pass=plaza_pass)
    loop.step()
    assert calls == ["assembly", "plaza"]
    assert len(session.messages) == 1 and session.messages[0]["event_type"] == "board_match"
    second = opening(2, posted_by="custodian")
    house.seed([*house.rows(), second])
    loop.step()
    assert len(session.messages) == 2


def test_update_arriving_during_wake_is_not_lost(house):
    row, = ready(house)
    def arriving():
        house.seed([row, update(row, 2, text="Arrived after claim")])
    house.run(Session(during=arriving))
    house.pass_()
    event, = house.matches(status="pending")
    assert event["board"]["board_seq"] == 2


def test_failed_wake_does_not_subscribe(house):
    row, = ready(house)
    with pytest.raises(RuntimeError):
        house.run(Session(failure=True))
    house.seed([row, update(row, 2)])
    house.pass_()
    assert {r["board"]["record_type"] for r in house.matches(status="pending")} == {"opening"}
    _, session = house.run(now=NOW + timedelta(days=1))
    assert session.messages[0]["board"]["coverage_after_this_wake"] == 1
    assert "New evidence 2" in session.messages[0]["board_text"]


def test_daily_board_cap_is_per_door(house):
    held(house)
    house.filter(door="beta")
    house.notice_done("beta")
    house.queue([house.rows()[0]], door="beta")
    assert house.stores["beta"].next_pending(now=NOW) is not None
    assert house.run(door="beta")[0]["status"] == "completed"
    assert house.store.next_pending(now=NOW) is None


def test_daily_attempt_date_is_utc(house):
    ready(house)
    event = house.matches()[0]
    # Two crashed attempts at different local dates, both on Oct 16 UTC.
    for stamp in ("2026-10-15T23:30:00-07:00", "2026-10-16T08:00:00+00:00"):
        house.store.append({"record_type": "event_status", "event_id": event["event_id"],
            "event_type": "board_match", "status": "running", "run_id": str(uuid4()),
            "started_at": stamp, "board_snapshot_seq": 1})
        recover_orphaned_running(house.store)
    assert house.store.next_pending(now=NOW + timedelta(days=1)) is None
    assert house.store.next_pending(now=NOW + timedelta(days=2)) is not None


def test_envelope_groups_all_events_of_rendered_entry(house):
    rows = [opening(i + 1, posted_by=f"door:poster{i // 5}", owner=f"door:owner{i}") for i in range(35)]
    house.seed(rows)
    house.filter()
    house.notice_done()
    # Independently seed completed first-show wakes yesterday, then two updates
    # per subscription. These are documented records, not editable coverage.
    for index, group in enumerate((rows[:30], rows[30:])):
        run_id, result_id = str(uuid4()), str(uuid4())
        stamp = (NOW - timedelta(days=1) + timedelta(minutes=index)).isoformat()
        events = [board_event(house.root, row) for row in group]
        for event in events:
            event["created_at"] = stamp
        running = [{"record_type": "event_status", "event_id": e["event_id"], "event_type": "board_match",
                    "status": "running", "run_id": run_id, "started_at": stamp, "board_snapshot_seq": 35}
                   for e in events]
        primary = events[-1]["event_id"]
        completed = [{"record_type": "event_status", "event_id": e["event_id"], "event_type": "board_match",
                      "status": "completed", "run_id": run_id, "completed_at": stamp,
                      "wake_cycle": index + 1, "result_record_id": result_id,
                      **({"response_text": "Seen"} if e["event_id"] == primary
                         else {"completed_with_event_id": primary})} for e in events]
        house.store.append_many([*events, *running, *completed])
    updates = []
    for row in rows:
        updates.extend([update(row, 36 + len(updates)), update(row, 37 + len(updates))])
    house.seed([*rows, *updates])
    house.queue(updates)
    _, session = house.run()
    envelope = session.messages[0]
    meta = envelope["board"]
    rendered = {r["opportunity_id"] for r in rows if r["opportunity_id"] in envelope["board_text"]}
    assert 1 <= len(rendered) <= 30
    batch_ids = {event_id("alpha", r["seq"]) for r in updates if r["opportunity_id"] in rendered}
    assert set(meta["batch_event_ids"]) == batch_ids
    pending = house.matches(status="pending")
    assert len(pending) == meta["remaining_events"] == 2 * meta["remaining_entries"]
    assert meta["remaining_entries"] == 35 - len(rendered)
    assert meta["coverage_after_this_wake"] == 35
    assert all(r["board"]["opportunity_id"] not in rendered for r in pending)
