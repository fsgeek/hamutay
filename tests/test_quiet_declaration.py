"""Quiet with reason — a resident can say why it is going quiet.

Spec: docs/superpowers/specs/2026-09-05-quiet-with-reason-design.md.
Written test-first by the implementing session; Codex's independent
validation lives in test_quiet_declaration_validation.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from hamutay.events import (
    EventStore,
    build_inbound_event,
    format_event_report,
    operational_notes_for_event,
    summarize_event_log,
)
from hamutay.heartbeat import derive_quiet_reason

UTC = timezone.utc


# --- helpers -----------------------------------------------------------------


def _complete(store, *, cycle, record_id, purpose="work"):
    """A claimed-and-completed inbound event whose wake was `cycle`/`record_id`."""
    event = build_inbound_event(purpose=purpose, sender="tony")
    store.append(event)
    store.append_running(event)
    store.append_completed(
        event=event,
        run_id=str(uuid4()),
        wake_cycle=cycle,
        result_record_id=record_id,
        response_text="done",
    )
    return event


def _declare(store, *, cycle, record_id, reason="thinking", until=None,
             created_at=None):
    from hamutay.events import build_quiet_declaration

    record = build_quiet_declaration(
        reason=reason,
        declared_by_cycle=cycle,
        declared_by_record_id=record_id,
        until=until,
    )
    if created_at is not None:
        record["created_at"] = created_at
    store.append(record)
    return record


def _completed_record(*, cycle, record_id, completed_at, event_id=None):
    """A completed event_status with a chosen clock (the quiet starts here)."""
    return {
        "record_type": "event_status",
        "event_id": event_id or str(uuid4()),
        "event_type": "inbound_message",
        "status": "completed",
        "run_id": str(uuid4()),
        "completed_at": completed_at,
        "wake_cycle": cycle,
        "result_record_id": str(record_id),
        "response_text": "done",
    }


def _running_record(event, started_at):
    """The claim of `event` at a chosen clock (the quiet ends here)."""
    return {
        "record_type": "event_status",
        "event_id": event["event_id"],
        "event_type": event.get("event_type", "inbound_message"),
        "status": "running",
        "run_id": str(uuid4()),
        "started_at": started_at,
    }


# --- the record --------------------------------------------------------------


def test_build_quiet_declaration_shape():
    from hamutay.events import RECORD_TYPE_QUIET_DECLARATION, build_quiet_declaration

    rid = uuid4()
    record = build_quiet_declaration(
        reason="waiting on the elder", declared_by_cycle=7, declared_by_record_id=rid,
        until="2026-09-19T00:00:00Z",
    )
    assert record["record_type"] == RECORD_TYPE_QUIET_DECLARATION == "quiet_declaration"
    assert record["declared_by_cycle"] == 7
    assert record["declared_by_record_id"] == str(rid)
    assert record["reason"] == "waiting on the elder"
    assert record["until"] == "2026-09-19T00:00:00Z"
    assert "event_id" not in record  # not an event: no lifecycle
    assert record["declaration_id"]
    datetime.fromisoformat(record["created_at"])


def test_build_quiet_declaration_omits_until_when_not_given():
    from hamutay.events import build_quiet_declaration

    record = build_quiet_declaration(
        reason="nothing to say", declared_by_cycle=1, declared_by_record_id=uuid4()
    )
    assert "until" not in record


def test_build_quiet_declaration_rejects_empty_reason():
    import pytest
    from hamutay.events import build_quiet_declaration

    with pytest.raises(ValueError):
        build_quiet_declaration(
            reason="   ", declared_by_cycle=1, declared_by_record_id=uuid4()
        )


def test_build_quiet_declaration_rejects_naive_until():
    import pytest
    from hamutay.events import build_quiet_declaration

    with pytest.raises(ValueError, match="timezone"):
        build_quiet_declaration(
            reason="ok", declared_by_cycle=1, declared_by_record_id=uuid4(),
            until="2026-09-19T00:00:00",
        )


def test_build_quiet_declaration_rejects_unparseable_until():
    import pytest
    from hamutay.events import build_quiet_declaration

    with pytest.raises(ValueError):
        build_quiet_declaration(
            reason="ok", declared_by_cycle=1, declared_by_record_id=uuid4(),
            until="next tuesday",
        )


# --- the tool ----------------------------------------------------------------


def test_declare_quiet_schema_is_natural_mode_only():
    from hamutay.tools.schemas import DECLARE_QUIET_SCHEMA, TOOL_SCHEMAS

    assert DECLARE_QUIET_SCHEMA["name"] == "declare_quiet"
    assert DECLARE_QUIET_SCHEMA["input_schema"]["required"] == ["reason"]
    assert "until" in DECLARE_QUIET_SCHEMA["input_schema"]["properties"]
    # Terminal shape stays byte-for-byte what the elder ran.
    assert "declare_quiet" not in TOOL_SCHEMAS


def _executor(tmp_path, *, record_id=None):
    from hamutay.tools import ToolExecutor

    return ToolExecutor(
        project_root=tmp_path,
        cycle=3,
        scheduled_by_record_id=record_id,
    )


def test_declare_quiet_buffers_a_declaration_for_cycle_commit(tmp_path):
    rid = uuid4()
    ex = _executor(tmp_path, record_id=rid)
    result = ex.execute("declare_quiet", {"reason": "listening", "until": "2026-09-19T00:00:00Z"})
    assert "error" not in result
    pending = ex.pending_quiet_declaration
    assert pending["record_type"] == "quiet_declaration"
    assert pending["declared_by_cycle"] == 3
    assert pending["declared_by_record_id"] == str(rid)
    assert pending["reason"] == "listening"
    assert pending["until"] == "2026-09-19T00:00:00Z"


def test_declare_quiet_last_call_wins(tmp_path):
    ex = _executor(tmp_path, record_id=uuid4())
    ex.execute("declare_quiet", {"reason": "first"})
    ex.execute("declare_quiet", {"reason": "second"})
    assert ex.pending_quiet_declaration["reason"] == "second"


def test_declare_quiet_rejects_empty_reason_and_keeps_nothing(tmp_path):
    ex = _executor(tmp_path, record_id=uuid4())
    result = ex.execute("declare_quiet", {"reason": ""})
    assert "error" in result
    assert ex.pending_quiet_declaration is None


def test_declare_quiet_bad_until_does_not_replace_a_good_declaration(tmp_path):
    ex = _executor(tmp_path, record_id=uuid4())
    ex.execute("declare_quiet", {"reason": "good"})
    result = ex.execute("declare_quiet", {"reason": "bad", "until": "soon-ish"})
    assert "error" in result
    assert ex.pending_quiet_declaration["reason"] == "good"


def test_declare_quiet_needs_a_cycle_record_id(tmp_path):
    ex = _executor(tmp_path, record_id=None)
    result = ex.execute("declare_quiet", {"reason": "no store"})
    assert "error" in result
    assert ex.pending_quiet_declaration is None


# --- the daemon's honest word -------------------------------------------------


def test_quiet_is_declared_when_latest_completed_wake_declared(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=3, record_id=rid, reason="listening")
    _complete(store, cycle=3, record_id=rid)
    assert derive_quiet_reason(store.read_records()) == "declared_quiet"


def test_quiet_is_undeclared_after_a_clean_completion_with_no_declaration(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _complete(store, cycle=1, record_id=uuid4())
    assert derive_quiet_reason(store.read_records()) == "undeclared_quiet"


def test_chosen_quiet_is_retired():
    import inspect

    import hamutay.heartbeat as hb

    assert "chosen_quiet" not in inspect.getsource(hb)


def test_a_declaration_binds_only_the_quiet_after_its_own_wake(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    r1, r2 = uuid4(), uuid4()
    _declare(store, cycle=1, record_id=r1)
    _complete(store, cycle=1, record_id=r1)
    _complete(store, cycle=2, record_id=r2)  # later wake, said nothing
    assert derive_quiet_reason(store.read_records()) == "undeclared_quiet"


def test_declaration_join_does_not_depend_on_record_order(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _complete(store, cycle=3, record_id=rid)
    _declare(store, cycle=3, record_id=rid)  # declaration after completed
    assert derive_quiet_reason(store.read_records()) == "declared_quiet"


def test_orphan_declaration_without_a_completed_wake_is_inert(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _complete(store, cycle=1, record_id=uuid4())
    _declare(store, cycle=2, record_id=uuid4())  # its wake never completed
    assert derive_quiet_reason(store.read_records()) == "undeclared_quiet"


def test_expiry_still_beats_a_declaration(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=1, record_id=rid)
    _complete(store, cycle=1, record_id=rid)
    late = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(late)
    store.append_expired(late)
    assert derive_quiet_reason(store.read_records()) == "starved_expired"


def test_a_later_failed_wake_ends_the_declaration_authority(tmp_path):
    """Codex review, blocking 3: the quiet after a failure is not the quiet
    the resident described."""
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=1, record_id=rid, reason="resting")
    _complete(store, cycle=1, record_id=rid)
    broken = build_inbound_event(purpose="crashes", sender="tony")
    store.append(broken)
    store.append_running(broken)
    store.append_failed(event=broken, run_id=str(uuid4()), exc=RuntimeError("boom"))
    assert derive_quiet_reason(store.read_records()) == "undeclared_quiet"


def test_an_old_expiry_does_not_latch_starvation_forever(tmp_path):
    """Codex review, should-fix 2: starvation belongs to the current idle
    episode. An expiry followed by a successful wake is history."""
    store = EventStore(str(tmp_path / "events.jsonl"))
    late = build_inbound_event(
        purpose="too late", sender="tony", expires_at="2000-01-01T00:00:00Z"
    )
    store.append(late)
    store.append_expired(late)
    rid = uuid4()
    _declare(store, cycle=2, record_id=rid, reason="back")
    _complete(store, cycle=2, record_id=rid)
    assert derive_quiet_reason(store.read_records()) == "declared_quiet"


def test_quiet_declaration_for_latest_wake_returns_the_resident_words(tmp_path):
    from hamutay.heartbeat import quiet_declaration_for_latest_wake

    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=5, record_id=rid, reason="digesting", until="2026-09-19T00:00:00Z")
    _complete(store, cycle=5, record_id=rid)
    found = quiet_declaration_for_latest_wake(store.read_records())
    assert found["reason"] == "digesting"
    assert found["until"] == "2026-09-19T00:00:00Z"
    assert found["declared_by_cycle"] == 5


def test_quiet_declaration_for_latest_wake_is_none_when_undeclared(tmp_path):
    from hamutay.heartbeat import quiet_declaration_for_latest_wake

    store = EventStore(str(tmp_path / "events.jsonl"))
    _complete(store, cycle=1, record_id=uuid4())
    assert quiet_declaration_for_latest_wake(store.read_records()) is None


class _StubSession:
    pass


def test_heartbeat_status_detail_carries_the_declaration(tmp_path):
    from hamutay.heartbeat import HeartbeatLoop

    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=2, record_id=rid, reason="listening", until="2026-09-19T00:00:00Z")
    _complete(store, cycle=2, record_id=rid)
    quiet = {"pending_runnable_count": 0, "pending_waiting_count": 0}
    loop = HeartbeatLoop(
        _StubSession(),
        store,
        poll_interval=30.0,
        sleep=lambda s: None,
        run_pending=lambda session, s, **kw: {"results": []},
        summarize=lambda records, now=None: quiet,
    )
    loop.step()
    status = [
        r for r in store.read_records() if r.get("record_type") == "heartbeat_status"
    ][-1]
    assert (status["status"], status["reason"]) == ("quiet", "declared_quiet")
    assert status["detail"]["reason"] == "listening"
    assert status["detail"]["until"] == "2026-09-19T00:00:00Z"
    assert status["detail"]["declared_by_cycle"] == 2


# --- the next wake is told ----------------------------------------------------


def test_envelope_note_reports_the_declaration_and_how_long_the_quiet_lasted(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    # The tool was called a minute before the wake completed; the quiet
    # starts at completion and ends at this event's claim.
    _declare(
        store, cycle=4, record_id=rid, reason="waiting on the elder",
        until="2026-09-19T00:00:00Z", created_at="2026-09-04T23:59:00+00:00",
    )
    store.append(_completed_record(cycle=4, record_id=rid, completed_at="2026-09-05T00:00:00+00:00"))
    event = build_inbound_event(purpose="knock", sender="tony")
    store.append(event)
    store.append(_running_record(event, "2026-09-07T06:30:00+00:00"))
    notes = operational_notes_for_event(
        store.read_records(), event, now=datetime(2026, 9, 7, 6, 31, tzinfo=UTC)
    )
    assert len(notes) == 1
    note = notes[0]
    assert 'Your cycle 4 declared quiet on 2026-09-04T23:59:00+00:00: "waiting on the elder"' in note
    assert "(until 2026-09-19T00:00:00Z)" in note
    assert "This wake ends that quiet after 2d 6h." in note


def test_envelope_has_no_declaration_note_when_latest_wake_declared_nothing(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    r1, r2 = uuid4(), uuid4()
    _declare(store, cycle=1, record_id=r1, reason="old")
    _complete(store, cycle=1, record_id=r1)
    _complete(store, cycle=2, record_id=r2)
    event = build_inbound_event(purpose="knock", sender="tony")
    store.append(event)
    notes = operational_notes_for_event(
        store.read_records(), event, now=datetime.now(UTC)
    )
    assert notes == []


def test_envelope_note_without_until_says_so_plainly(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=4, record_id=rid, reason="nothing to add",
             created_at="2026-09-04T23:59:30+00:00")
    store.append(_completed_record(cycle=4, record_id=rid, completed_at="2026-09-05T00:00:00+00:00"))
    event = build_inbound_event(purpose="knock", sender="tony")
    store.append(event)
    store.append(_running_record(event, "2026-09-05T01:00:00+00:00"))
    notes = operational_notes_for_event(
        store.read_records(), event, now=datetime(2026, 9, 5, 1, 0, tzinfo=UTC)
    )
    assert len(notes) == 1
    assert "until" not in notes[0]
    assert notes[0].endswith('"nothing to add". This wake ends that quiet after 1h 0m.')


def test_envelope_note_falls_back_to_now_when_the_event_has_no_claim_record(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=4, record_id=rid, reason="x")
    store.append(_completed_record(cycle=4, record_id=rid, completed_at="2026-09-05T00:00:00+00:00"))
    event = build_inbound_event(purpose="knock", sender="tony")
    store.append(event)
    notes = operational_notes_for_event(
        store.read_records(), event, now=datetime(2026, 9, 5, 3, 0, tzinfo=UTC)
    )
    assert "after 3h 0m." in notes[0]


def test_envelope_note_omits_the_duration_when_the_interval_is_invalid(tmp_path):
    """A batch's scheduler clock can precede the declaring wake's completion;
    the note must not invent a negative or misleading span."""
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=4, record_id=rid, reason="x")
    store.append(_completed_record(cycle=4, record_id=rid, completed_at="2026-09-05T00:00:00+00:00"))
    event = build_inbound_event(purpose="knock", sender="tony")
    store.append(event)
    notes = operational_notes_for_event(
        store.read_records(), event, now=datetime(2026, 9, 4, 23, 0, tzinfo=UTC)
    )
    assert notes[0].endswith('"x". This wake ends that quiet.')
    assert "after" not in notes[0]


def test_declared_quiet_and_a_budget_rest_yield_two_ordered_notes(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=4, record_id=rid, reason="x")
    store.append(_completed_record(cycle=4, record_id=rid, completed_at="2026-09-05T00:00:00+00:00"))
    event = build_inbound_event(purpose="waited", sender="tony")
    event["created_at"] = "2026-09-05T01:00:00+00:00"
    store.append(event)
    store.append({
        "record_type": "heartbeat_status", "heartbeat_record_id": "hb-rest",
        "status": "resting", "reason": "daily_budget_reached",
        "created_at": "2026-09-05T02:00:00+00:00",
        "detail": {"day": "2026-09-05", "wakes": 48},
    })
    store.append({
        "record_type": "heartbeat_status", "heartbeat_record_id": "hb-active",
        "status": "active", "reason": "runnable_pending",
        "created_at": "2026-09-06T00:00:05+00:00",
    })
    notes = operational_notes_for_event(
        store.read_records(), event, now=datetime(2026, 9, 6, 0, 0, 5, tzinfo=UTC)
    )
    assert len(notes) == 2
    assert notes[0].startswith("heartbeat rested from")
    assert notes[1].startswith("Your cycle 4 declared quiet")


def test_a_future_self_scheduled_wake_is_told_about_the_declaration(tmp_path):
    """Declare-plus-schedule is allowed: the daemon waits, and the scheduled
    wake, when it runs, is told what the resident declared."""
    from hamutay.events import build_pending_event

    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    future = build_pending_event(
        purpose="check back", requested_context=[{"tool": "recall", "cycle": 4}],
        scheduled_by_cycle=4,
        scheduled_by_record_id=rid, not_before="2026-09-19T00:00:00Z",
    )
    store.append(future)
    _declare(store, cycle=4, record_id=rid, reason="quiet until my check")
    store.append(_completed_record(cycle=4, record_id=rid, completed_at="2026-09-05T00:00:00+00:00"))
    store.append(_running_record(future, "2026-09-19T00:00:01+00:00"))
    notes = operational_notes_for_event(
        store.read_records(), future, now=datetime(2026, 9, 19, 0, 0, 1, tzinfo=UTC)
    )
    assert len(notes) == 1
    assert '"quiet until my check"' in notes[0]
    assert "after 14d 0h." in notes[0]


# --- the report ---------------------------------------------------------------


def test_report_shows_the_latest_declaration_and_daemon_quiet_reason(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=3, record_id=rid, reason="listening", until="2026-09-19T00:00:00Z")
    _complete(store, cycle=3, record_id=rid)
    store.append({
        "record_type": "heartbeat_status", "heartbeat_record_id": "hb-1",
        "status": "quiet", "reason": "declared_quiet",
        "created_at": "2026-09-05T00:05:00+00:00",
        "detail": {"reason": "listening", "until": "2026-09-19T00:00:00Z", "declared_by_cycle": 3},
    })
    summary = summarize_event_log(store.read_records())
    assert summary["latest_quiet_declaration"]["reason"] == "listening"
    assert summary["latest_quiet_declaration"]["declared_by_cycle"] == 3
    assert summary["latest_heartbeat_status"]["reason"] == "declared_quiet"
    text = format_event_report(summary)
    assert "Heartbeat: quiet (declared_quiet)" in text
    assert 'Quiet declared by cycle 3: "listening" until 2026-09-19T00:00:00Z' in text


def test_report_ignores_orphan_declarations_and_counts_them(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    rid = uuid4()
    _declare(store, cycle=3, record_id=rid, reason="real")
    _complete(store, cycle=3, record_id=rid)
    _declare(store, cycle=4, record_id=uuid4(), reason="orphan: wake never completed")
    summary = summarize_event_log(store.read_records())
    assert summary["latest_quiet_declaration"]["reason"] == "real"
    assert summary["orphan_quiet_declaration_count"] == 1
    text = format_event_report(summary)
    assert "orphan" not in text.split("Orphan quiet declarations")[0]
    assert "Orphan quiet declarations (wake never completed): 1" in text


def test_report_without_declarations_has_none_and_no_line(tmp_path):
    store = EventStore(str(tmp_path / "events.jsonl"))
    _complete(store, cycle=1, record_id=uuid4())
    summary = summarize_event_log(store.read_records())
    assert summary["latest_quiet_declaration"] is None
    assert summary["latest_heartbeat_status"] is None
    assert "Quiet declared" not in format_event_report(summary)


# --- the constitution and the budget ------------------------------------------


def test_constitution_stops_claiming_undeclared_quiet_was_chosen():
    from hamutay.heartbeat import CONSTITUTION

    assert "recorded as chosen" not in CONSTITUTION
    assert "declare_quiet" in CONSTITUTION
    assert "undeclared" in CONSTITUTION
    assert "schedules nothing" in CONSTITUTION


def test_constitution_never_tells_the_resident_when_to_declare():
    from hamutay.heartbeat import CONSTITUTION

    sentence = [s for s in CONSTITUTION.split(". ") if "declare_quiet" in s]
    assert sentence, "declare_quiet must be introduced in the constitution"
    lowered = " ".join(sentence).lower()
    for prior in ("should declare", "must declare", "always declare", "before going quiet"):
        assert prior not in lowered


def test_daily_budget_default_matches_tonys_number():
    from hamutay.heartbeat import build_parser

    args = build_parser().parse_args(["--log-path", "x.jsonl"])
    assert args.daily_budget_usd == 1.5
    assert args.daily_wake_cap == 48


# --- the session: offered on the natural shape, committed with the wake ------


class _DeclaringNaturalBackend:
    wake_mode = "natural"

    def __init__(self, declare=True):
        self.calls = []
        self._declare = declare

    def call(self, model, system, messages, experiment_label,
             extra_tools=None, tool_executor=None):
        from hamutay.taste_open import ExchangeResult

        self.calls.append({"system": system, "extra_tools": extra_tools})
        if tool_executor is not None:
            tool_executor.execute("update_state", {"updates": {"mood": "calm"}})
            if self._declare:
                tool_executor.execute(
                    "declare_quiet",
                    {"reason": "nothing to add", "until": "2026-09-19T00:00:00Z"},
                )
        return ExchangeResult(
            raw_output={"response": "text reply", "mood": "calm"},
            tool_activity=tool_executor.activity_log if tool_executor else None,
        )


def _natural_session(tmp_path, backend):
    from hamutay.taste_open import OpenTasteSession

    return OpenTasteSession(
        model="m",
        backend=backend,
        log_path=str(tmp_path / "s.jsonl"),
        enable_tools=True,
        project_root=tmp_path,
        wake_mode="natural",
    )


def test_event_managed_natural_wake_offers_declare_quiet_and_describes_it(tmp_path):
    backend = _DeclaringNaturalBackend(declare=False)
    session = _natural_session(tmp_path, backend)
    session.exchange("hello", event_managed=True)
    call = backend.calls[0]
    assert "declare_quiet" in [t["name"] for t in call["extra_tools"]]
    assert "declare_quiet" in call["system"]


def test_direct_natural_exchange_does_not_offer_declare_quiet(tmp_path):
    """Codex review, blocking 2: outside an event-managed wake no completed
    status will ever own the declaration, so the tool is not offered and
    the prompt does not name it."""
    backend = _DeclaringNaturalBackend(declare=False)
    session = _natural_session(tmp_path, backend)
    session.exchange("hello")
    call = backend.calls[0]
    assert "declare_quiet" not in [t["name"] for t in call["extra_tools"]]
    assert "declare_quiet" not in call["system"]
    assert "update_state" in [t["name"] for t in call["extra_tools"]]


def test_event_runner_drives_an_event_managed_wake_end_to_end(tmp_path):
    """The real path: run_next_event → exchange(event_managed=True) →
    declaration and completed status both in the store → declared_quiet."""
    from hamutay.events import run_next_event

    session = _natural_session(tmp_path, _DeclaringNaturalBackend())
    store = session._event_store
    store.append(build_inbound_event(purpose="hello", sender="tony"))
    completed = run_next_event(session, store)
    assert completed["status"] == "completed"
    records = store.read_records()
    declarations = [r for r in records if r.get("record_type") == "quiet_declaration"]
    assert len(declarations) == 1
    assert declarations[0]["declared_by_record_id"] == completed["result_record_id"]
    assert derive_quiet_reason(records) == "declared_quiet"


def test_session_terminal_mode_does_not_offer_declare_quiet(tmp_path):
    from hamutay.taste_open import ExchangeResult, OpenTasteSession

    class _TerminalFake:
        def call(self, model, system, messages, experiment_label,
                 extra_tools=None, tool_executor=None):
            self.system = system
            self.extra_tools = extra_tools
            return ExchangeResult(raw_output={"response": "r"})

    backend = _TerminalFake()
    session = OpenTasteSession(
        model="m", backend=backend, log_path=str(tmp_path / "s.jsonl"),
        enable_tools=True, project_root=tmp_path,
    )
    session.exchange("hello")
    assert "declare_quiet" not in [t["name"] for t in backend.extra_tools]
    assert "declare_quiet" not in backend.system


def test_session_commits_the_declaration_to_the_event_store_with_the_wake(tmp_path):
    from hamutay.events import default_event_log_path

    session = _natural_session(tmp_path, _DeclaringNaturalBackend())
    session.exchange("hello", event_managed=True)
    store = EventStore(str(default_event_log_path(str(tmp_path / "s.jsonl"))))
    declarations = [
        r for r in store.read_records() if r.get("record_type") == "quiet_declaration"
    ]
    assert len(declarations) == 1
    record_id = session._prior_states[-1][1]
    assert declarations[0]["declared_by_record_id"] == str(record_id)
    assert declarations[0]["declared_by_cycle"] == session.cycle
    assert declarations[0]["reason"] == "nothing to add"


def test_session_log_record_carries_the_declaration(tmp_path):
    import json

    session = _natural_session(tmp_path, _DeclaringNaturalBackend())
    session.exchange("hello", event_managed=True)
    record = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert record["quiet_declaration"]["reason"] == "nothing to add"


def test_session_log_record_has_null_declaration_when_none_made(tmp_path):
    import json

    session = _natural_session(tmp_path, _DeclaringNaturalBackend(declare=False))
    session.exchange("hello", event_managed=True)
    record = json.loads((tmp_path / "s.jsonl").read_text().splitlines()[-1])
    assert record["quiet_declaration"] is None
