import json
import uuid
from datetime import datetime, timedelta, timezone

from hamutay.assembly.ledger import Ledger, iso
from hamutay.events import EventStore, build_inbound_event, run_next_event
from hamutay.plaza.note import note_lower_bound, note_producer, plaza_note
from hamutay.plaza.send import send

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _wake(ev, started=T0):
    return {"cycle": 1, "record_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "event_id": ev,
            "run_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "started_at": iso(started)}


def _completed_wake(store: EventStore, *, started):
    """Produce a completed wake exactly as the real store would: a pending event,
    a running record whose started_at is deterministic, and its completed join.

    There is deliberately no `completed=`: note_lower_bound joins the completed
    wake back to its running record and reads `started_at`, never `completed_at`,
    so a completed time is not a parameter of anything under test. The earlier
    version took one and mutated an in-memory copy that never reached the file."""
    e = build_inbound_event(purpose="p", sender="tony")
    store.append(e)
    run_id = uuid.uuid4()
    running = store._build_running(e, run_id=run_id, now=started)
    store.append(running)
    store.append_completed_atomic(
        event=e, run_id=str(run_id), wake_cycle=1, result_record_id=uuid.uuid4(),
        response_text="ok",
    )
    return e, running


def test_lower_bound_is_the_completed_wakes_started_at_by_event_and_run(tmp_path):
    st = EventStore(tmp_path / "s.events.jsonl")
    assert note_lower_bound(st.read_records()) is None
    _completed_wake(st, started=T0)
    assert note_lower_bound(st.read_records()) == T0
    _completed_wake(st, started=T0 + timedelta(hours=1))
    assert note_lower_bound(st.read_records()) == T0 + timedelta(hours=1)


def test_note_names_exact_seqs_and_a_bounded_command(house):
    root, cfg, binding = house
    st = EventStore(cfg.members["fable"].events)
    _completed_wake(st, started=T0)
    send(cfg, actor="door:qwen", via="tool", to="elder", text="q→e", now=T0 + timedelta(minutes=2), wake=_wake("11111111-1111-4111-8111-111111111111"))
    send(cfg, actor="door:elder", via="tool", to="plaza", text="post", now=T0 + timedelta(minutes=3), wake=_wake("22222222-1111-4111-8111-111111111111"))
    send(cfg, actor="door:elder", via="tool", to="fable", text="e→f", now=T0 + timedelta(minutes=4), wake=_wake("33333333-1111-4111-8111-111111111111"))
    send(cfg, actor="door:qwen", via="tool", to="elder", text="old", now=T0 - timedelta(hours=1), wake=_wake("44444444-1111-4111-8111-111111111111"))
    notes = plaza_note(cfg, "fable", st.read_records())
    assert len(notes) == 1
    n = notes[0]
    assert n.startswith("plaza: 2 message(s) since your last wake began, at seq 1, 3 (1 posts, 1 between other doors; latest from door:elder at ")
    assert "read --since-seq 1 --through-seq 3 --for fable" in n
    assert plaza_note(cfg, "qwen", st.read_records()) and "at seq 3" in plaza_note(cfg, "qwen", st.read_records())[0]
    # elder is sender or recipient of every message sent above (seq 1, 4 addressed to elder;
    # seq 2, 3 from elder), so visible_since's from/to exclusion leaves elder nothing to say,
    # even with no completed wake of its own (a door with no join counts everything, but
    # "everything" here is still empty once self-authored and self-addressed mail is excluded).
    assert plaza_note(cfg, "elder", EventStore(cfg.members["elder"].events).read_records()) == []


def test_note_abbreviates_past_twelve_and_is_absent_when_nothing(house):
    root, cfg, binding = house
    st = EventStore(cfg.members["fable"].events)
    assert plaza_note(cfg, "fable", st.read_records()) == []
    for i in range(14):
        send(cfg, actor="door:qwen", via="tool", to="plaza", text=f"p{i}", now=T0 + timedelta(minutes=i),
             wake=_wake(f"{i:08d}-1111-4111-8111-111111111111"))
    n = plaza_note(cfg, "fable", st.read_records())[0]
    assert "at seq 1, 2, 3, …, 12, 13, 14 (" in n and "--since-seq 1 --through-seq 14" in n


def test_note_is_omitted_when_the_lock_is_held(house):
    root, cfg, binding = house
    send(cfg, actor="door:qwen", via="tool", to="plaza", text="p", now=T0, wake=_wake("11111111-1111-4111-8111-111111111111"))
    errors = []
    led = Ledger(cfg.plaza)
    with led.locked():
        assert plaza_note(cfg, "fable", [], on_error=errors.append) == []
    assert errors and "lock" in errors[0]


def test_run_next_event_extra_notes_none_is_unchanged_and_producer_appends(house, monkeypatch):
    root, cfg, binding = house
    st = EventStore(cfg.members["fable"].events)
    send(cfg, actor="door:qwen", via="tool", to="plaza", text="p", now=T0, wake=_wake("11111111-1111-4111-8111-111111111111"))
    seen = []

    class Session:
        _prior_states = [(1, uuid.uuid4(), {}, iso(T0))]
        _bridge = None
        _state = {}
        cycle = 1

        def exchange(self, envelope, **kw):
            seen.append(json.loads(envelope)); return "ok"

    st.append(build_inbound_event(purpose="p", sender="tony"))
    run_next_event(Session(), st, now=T0)
    assert "operational_notes" not in seen[-1]
    st.append(build_inbound_event(purpose="p2", sender="tony"))
    run_next_event(Session(), st, now=T0, extra_notes=note_producer(cfg, "fable", st, on_error=lambda s: None))
    assert seen[-1]["operational_notes"][-1].startswith("plaza: 1 message(s)")


def test_the_note_does_not_read_the_store_a_second_time(house):
    """I3: run_next_event already reads the store's records two statements before it
    calls extra_notes; the note used to call store.read_records() again -- an
    unbounded, blocking flock -- on a path whose whole contract is that it never
    costs the wake anything. The producer now receives those records."""
    root, cfg, binding = house
    st = EventStore(cfg.members["fable"].events)
    send(cfg, actor="door:qwen", via="tool", to="plaza", text="p", now=T0,
         wake=_wake("11111111-1111-4111-8111-111111111111"))

    reads = []

    class CountingStore:
        def __init__(self, inner):
            self._inner = inner

        def read_records(self):
            reads.append(1)
            return self._inner.read_records()

        def __getattr__(self, name):
            return getattr(self._inner, name)

    produce = note_producer(cfg, "fable", CountingStore(st), on_error=lambda s: None)
    notes = produce(build_inbound_event(purpose="p", sender="tony"), st.read_records())
    assert notes and notes[0].startswith("plaza: 1 message(s)")
    assert reads == [], "the note read the store again instead of using the records it was given"


def test_a_held_store_lock_does_not_stall_the_wake_and_yields_no_note(house):
    """I3, the behaviour that matters: a store lock held by someone else must not
    stall the note. With the records passed through there is no second acquisition
    at all, so the note is produced promptly whatever the lock is doing."""
    import threading
    import time

    root, cfg, binding = house
    st = EventStore(cfg.members["fable"].events)
    send(cfg, actor="door:qwen", via="tool", to="plaza", text="p", now=T0,
         wake=_wake("11111111-1111-4111-8111-111111111111"))
    records = st.read_records()          # what run_next_event holds when it calls the producer

    held = threading.Event()
    release = threading.Event()

    def hold_the_store_lock():
        with EventStore(cfg.members["fable"].events)._locked():
            held.set()
            release.wait(30)

    t = threading.Thread(target=hold_the_store_lock, daemon=True)
    t.start()
    assert held.wait(10)
    result = {}

    def produce_the_note():
        try:
            fn = note_producer(cfg, "fable", st, on_error=lambda s: None)
            result["notes"] = fn(build_inbound_event(purpose="p", sender="tony"), records)
        except Exception as e:                                    # pragma: no cover
            result["error"] = e

    started = time.monotonic()
    w = threading.Thread(target=produce_the_note, daemon=True)
    w.start()
    w.join(10)
    elapsed = time.monotonic() - started
    release.set(); t.join(10)

    assert not w.is_alive(), "the note blocked on the held store lock"
    assert elapsed < 5, f"the note took {elapsed:.1f}s while the store lock was held"
    assert result.get("notes"), result
    assert result["notes"][0].startswith("plaza: 1 message(s)")


def test_run_next_event_passes_its_records_to_extra_notes(house):
    """The wiring end to end: the real run_next_event calls the real producer, and the
    note reaches the envelope, with no second store read."""
    root, cfg, binding = house
    st = EventStore(cfg.members["fable"].events)
    send(cfg, actor="door:qwen", via="tool", to="plaza", text="p", now=T0,
         wake=_wake("11111111-1111-4111-8111-111111111111"))
    seen = []

    class Session:
        _prior_states = [(1, uuid.uuid4(), {}, iso(T0))]
        _bridge = None
        _state = {}
        cycle = 1

        def exchange(self, envelope, **kw):
            seen.append(json.loads(envelope)); return "ok"

    got = []

    def extra(event, records):
        got.append((event["event_id"], len(records)))
        return ["x"]

    st.append(build_inbound_event(purpose="p", sender="tony"))
    run_next_event(Session(), st, now=T0, extra_notes=extra)
    assert len(got) == 1 and got[0][1] > 0          # the records run_next_event had read
    assert seen[-1]["operational_notes"][-1] == "x"
