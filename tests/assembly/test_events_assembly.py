import json
import threading
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from hamutay.events import (
    EventStore, StoreUnavailable, WakeContext, assembly_claimable, build_inbound_event,
    build_quiet_declaration, summarize_event_log,
)

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _iso(dt):
    return dt.isoformat()


def _assembly_event(closes_at, qid="q1", event_id=None):
    return build_inbound_event(purpose="q", sender="assembly", event_id=event_id,
                               assembly={"assembly_question_id": qid, "expires_at": _iso(closes_at)})


def _complete_with_quiet(store, *, until):
    ev = build_inbound_event(purpose="x", sender="tony")
    store.append(ev); store.append_running(ev)
    rid = uuid4()
    store.append_completed(event=ev, run_id=str(uuid4()), wake_cycle=1, result_record_id=rid, response_text="r")
    store.append(build_quiet_declaration(reason="rest", declared_by_cycle=1, declared_by_record_id=rid, until=until))


def test_build_inbound_event_accepts_a_stable_id_and_assembly_fields():
    eid = str(uuid4())
    ev = _assembly_event(T0 + timedelta(days=7), event_id=eid)
    assert ev["event_id"] == eid and ev["defer_to_declared_quiet"] is True
    assert ev["assembly_question_id"] == "q1" and ev["expires_at"] == _iso(T0 + timedelta(days=7))
    with pytest.raises(ValueError):
        build_inbound_event(purpose="q", sender="assembly", event_id="not-a-uuid")


def test_append_if_absent_is_at_most_once(tmp_path):
    store = EventStore(tmp_path / "e.jsonl")
    ev = _assembly_event(T0 + timedelta(days=7))
    assert store.append_if_absent(ev) is True
    assert store.append_if_absent(ev) is False
    assert len([r for r in store.read_records() if r["event_id"] == ev["event_id"]]) == 1
    store.append_running(ev)                       # a lifecycle row with the same id
    assert store.append_if_absent(ev) is False


def test_try_read_records_times_out_and_wraps_malformed(tmp_path):
    store = EventStore(tmp_path / "e.jsonl")
    store.append(build_inbound_event(purpose="x", sender="tony"))
    held, release = threading.Event(), threading.Event()

    def holder():
        with store._locked():
            held.set(); release.wait(5)

    t = threading.Thread(target=holder); t.start(); held.wait(5)
    with pytest.raises(StoreUnavailable):
        store.try_read_records(timeout_s=0.3)
    release.set(); t.join()
    with (tmp_path / "e.jsonl").open("a") as f:
        f.write("garbage\n")
    with pytest.raises(StoreUnavailable):
        store.try_read_records(timeout_s=0.3)


def test_assembly_claimable_defers_expires_and_ignores_untimed_quiet(tmp_path):
    store = EventStore(tmp_path / "e.jsonl")
    ev = _assembly_event(T0 + timedelta(days=7))
    assert assembly_claimable(store.read_records(), ev, T0)[0] == "claimable"
    _complete_with_quiet(store, until=_iso(T0 + timedelta(days=2)))
    kind, detail = assembly_claimable(store.read_records(), ev, T0)
    assert kind == "deferred" and detail["quiet_until"] == _iso(T0 + timedelta(days=2))
    assert assembly_claimable(store.read_records(), ev, T0 + timedelta(days=3))[0] == "claimable"
    _complete_with_quiet(store, until=_iso(T0 + timedelta(days=9)))
    assert assembly_claimable(store.read_records(), ev, T0)[0] == "expire_by_quiet"
    _complete_with_quiet(store, until=None)
    assert assembly_claimable(store.read_records(), ev, T0)[0] == "claimable"


def test_claim_path_honours_the_predicate_and_non_assembly_events_are_unchanged(tmp_path):
    store = EventStore(tmp_path / "e.jsonl")
    plain = build_inbound_event(purpose="plain", sender="tony")
    store.append(plain)
    _complete_with_quiet(store, until=_iso(T0 + timedelta(days=2)))
    ev = _assembly_event(T0 + timedelta(days=7)); store.append(ev)
    # plain is claimed first (oldest), quiet or not
    claimed, running = store.claim_next_pending(now=T0)
    assert claimed["event_id"] == plain["event_id"]
    store.append_completed(event=plain, run_id=running["run_id"], wake_cycle=2, result_record_id=uuid4(), response_text="r")
    # the assembly event is deferred while the timed quiet holds ...
    _complete_with_quiet(store, until=_iso(T0 + timedelta(days=2)))
    assert store.next_pending(now=T0) is None and store.claim_next_pending(now=T0) is None
    # ... and claimable after
    assert store.next_pending(now=T0 + timedelta(days=3))["event_id"] == ev["event_id"]
    # a quiet that outlasts the question expires it without a wake
    _complete_with_quiet(store, until=_iso(T0 + timedelta(days=9)))
    claimed, status = store.claim_next_pending(now=T0)
    assert claimed["event_id"] == ev["event_id"] and status["status"] == "expired"
    assert status["detail"] == {"reason": "skipped_by_quiet", "quiet_until": _iso(T0 + timedelta(days=9))}


def test_summary_reports_a_deferred_event_as_waiting_until_the_quiet_ends(tmp_path):
    store = EventStore(tmp_path / "e.jsonl")
    _complete_with_quiet(store, until=_iso(T0 + timedelta(days=2)))
    ev = _assembly_event(T0 + timedelta(days=7)); store.append(ev)
    s = summarize_event_log(store.read_records(), now=T0)
    assert s["pending_runnable_count"] == 0 and s["pending_waiting_count"] == 1
    assert s["oldest_waiting_pending"]["not_before"] == _iso(T0 + timedelta(days=2))


def test_run_next_event_passes_a_wake_context(tmp_path):
    from hamutay.events import run_next_event
    store = EventStore(tmp_path / "e.jsonl")
    ev = build_inbound_event(purpose="x", sender="tony"); store.append(ev)
    seen = {}

    class Session:
        _prior_states = [(1, uuid4(), {}, _iso(T0))]
        _bridge = None
        cycle = 1
        _state = {}
        def exchange(self, envelope, *, wake_context=None, **kw):
            seen["ctx"] = wake_context
            return "ok"

    run_next_event(Session(), store, now=T0)
    ctx = seen["ctx"]
    assert isinstance(ctx, WakeContext) and ctx.event_id == ev["event_id"]
    running = [r for r in store.read_records() if r.get("status") == "running"][0]
    assert ctx.run_id == running["run_id"] and ctx.started_at == running["started_at"]
