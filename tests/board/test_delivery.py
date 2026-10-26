from datetime import timedelta

import pytest

from hamutay.board.delivery import BOARD_TEXT_BUDGET
from hamutay.board.filters import clear_filter, pass_entry, set_filter
from hamutay.board.ids import match_event_id, onboarding_event_id
from hamutay.board.pass_ import run_board_pass
from hamutay.board.write import add_note, set_status
from hamutay.events import EventStore, run_next_event, summarize_event_log

from .conftest import T0, Session, post


def store_of(cfg, door="qwen"):
    return EventStore(cfg.members[door].events)


def bpass(root, st, now=T0, door="qwen"):
    return run_board_pass(door=door, project_root=root, store=st, now=now)[0]


def latest(st):
    return st.latest_by_event_id()


def board_events(st, status=None):
    return [r for r in latest(st).values() if r.get("event_type") == "board_match"
            and (status is None or r.get("status") == status)]


def drain_onboarding(st, now=T0):
    """Run the onboarding notice so it does not take the next claim."""
    s = Session()
    out = run_next_event(s, st, now=now)
    assert out["status"] == "completed" and s.envelopes[0]["origin"] == "board"
    return s.envelopes[0]


# --- dormancy -----------------------------------------------------------------

def test_dormant_without_the_gate_writes_nothing(house):
    root, cfg, _ = house
    st = store_of(cfg)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1)
    before = st.path.read_text()
    assert bpass(root, st)["skipped"] == "dormant"
    assert st.path.read_text() == before


def test_events_already_queued_are_parked_when_the_gate_goes(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1)
    bpass(root, st)
    assert len(board_events(st, "pending")) == 1
    (root / "community" / "board" / "board.enabled").unlink()
    assert st.next_pending(now=T0) is None
    assert st.claim_next_pending(now=T0) is None
    summary = summarize_event_log(st.read_records(), now=T0)
    assert summary["pending_runnable_count"] == 0 and summary["pending_waiting_count"] == 0
    assert summary["pending_board_parked_count"] == 1


def drain_onboarding_after_pass(root, st):
    bpass(root, st)
    return drain_onboarding(st)


# --- onboarding ---------------------------------------------------------------

def test_onboarding_once_per_door_quiet_deferred_listing_open_entries(on):
    root, cfg, _ = on
    post(root, 1, title="Seed one")
    st = store_of(cfg)
    bpass(root, st); bpass(root, st)
    notices = [r for r in st.read_records() if r.get("event_id") == onboarding_event_id("qwen")]
    assert len(notices) == 1
    n = notices[0]
    assert n["defer_to_declared_quiet"] is True and "expires_at" not in n
    assert "never woken by the board" in n["purpose"] and "Seed one" in n["purpose"]
    env = drain_onboarding(st)
    assert "board_text" not in env
    bpass(root, st)
    assert len([r for r in st.read_records() if r.get("event_id") == onboarding_event_id("qwen")]) == 3


# --- matching and the pass ------------------------------------------------------

def test_pass_queues_matches_with_the_deterministic_id(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"], "keywords_any": ["thing"]}, T0)
    post(root, 1)                                  # seq 1: matches
    post(root, 2, kind="build")                    # seq 2: kind does not match
    post(root, 3, by="custodian")                  # seq 3: matches
    res = bpass(root, st)
    ids = {e["event_id"] for e in board_events(st)}
    assert ids == {match_event_id("qwen", 1, 1, 1), match_event_id("qwen", 3, 1, 1)}
    e = next(e for e in board_events(st) if e["board"]["board_seq"] == 1)
    assert e["defer_to_declared_quiet"] is True and "expires_at" not in e
    assert e["board"]["clause"] == {"kinds": ["review"], "keywords_any": ["thing"]}
    assert res["appended"] == 2
    assert bpass(root, st)["appended"] == 0        # idempotent


def test_self_posted_never_matches_and_only_open_entries_queue(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    from hamutay.board.write import post_opening
    post_opening(root, by="door:qwen", title="mine", what="my thing", kind="review", now=T0)
    oid = post(root, 2)["opportunity_id"]
    set_status(root, by="tony", opportunity_id=oid, status="taken", now=T0)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    bpass(root, st)
    assert board_events(st) == []


def test_filter_change_supersedes_and_rescans_clear_then_reset_keeps_the_opening(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1)
    bpass(root, st)
    clear_filter(st, "qwen", T0)
    bpass(root, st)
    first = latest(st)[match_event_id("qwen", 1, 1, 1)]
    assert first["status"] == "suppressed" and first["superseded"] is True
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    bpass(root, st)
    again = latest(st)[match_event_id("qwen", 1, 3, 1)]
    assert again["status"] == "pending"
    claim = st.claim_next_pending(now=T0)
    assert claim is not None and claim[0]["board"]["generation"] == 3


def test_bounded_per_pass_and_completed_by_later_passes(on, monkeypatch):
    import hamutay.board.pass_ as P
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    for i in range(5):
        post(root, i, by=["tony", "custodian"][i % 2])
    monkeypatch.setattr(P, "PASS_MAX_APPENDS", 2)
    monkeypatch.setattr(P.derive_appends, "__kwdefaults__", {"limit": 2})
    r = bpass(root, st)
    assert r["appended"] == 2 and r["truncated"] is True
    bpass(root, st); bpass(root, st)
    assert len(board_events(st)) == 5


# --- the claim ------------------------------------------------------------------

def test_coalesced_claim_one_run_one_wake_all_covered(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    for i in range(3):
        post(root, i)
    bpass(root, st)
    s = Session()
    out = run_next_event(s, st, now=T0)
    assert out["status"] == "completed" and len(s.envelopes) == 1
    env = s.envelopes[0]
    assert env["event_type"] == "board_match" and env["origin"] == "board"
    assert env["board_text"].count("== Entry") == 3 and env["board"]["remaining_entries"] == 0
    assert env["board"]["coverage_after_this_wake"] == 3
    runs = {r["run_id"] for r in st.read_records() if r.get("status") == "running"
            and r.get("event_type") == "board_match"}
    assert len(runs) == 1
    assert all(e["status"] == "completed" for e in board_events(st))
    assert run_next_event(Session(), st, now=T0)["status"] == "none"
    assert bpass(root, st)["appended"] == 0      # shown entries are not queued again


def test_envelope_bounds_ten_full_twenty_titles_rest_pending(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    # each opening is queued while open, then marked taken (5 open per poster); one record per day per poster
    posters = ["tony", "custodian", "guest:levadura"]
    for n in range(35):
        p, day = posters[n % 3], T0 + timedelta(days=n)
        r = post(root, n, by=p, now=day, admitted_guests=("levadura",))
        bpass(root, st)
        set_status(root, by=p, opportunity_id=r["opportunity_id"], status="taken", now=day,
                   admitted_guests=("levadura",))
    assert len(board_events(st, "pending")) == 35
    s = Session()
    run_next_event(s, st, now=T0 + timedelta(days=40))
    env = s.envelopes[0]
    b = env["board"]
    assert b["entries_full"] == 10 and b["entries_titles"] == 20 and len(b["entries_full_ids"]) == 10
    assert b["remaining_entries"] == 5 and "5 more entries" in env["board_text"]
    assert len(env["board_text"]) <= BOARD_TEXT_BUDGET
    assert len(board_events(st, "pending")) == 5 and len(board_events(st, "completed")) == 30


def test_envelope_stays_under_budget_with_maximal_entries(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    for i in range(4):
        post(root, i, by=["tony", "custodian"][i % 2], title="T" * 120, what=f"{i}" + "w" * 1999,
                 why="y" * 1000, help_wanted="h" * 1000, record_of_help="r" * 500)
    bpass(root, st)
    s = Session()
    run_next_event(s, st, now=T0)
    env = s.envelopes[0]
    assert len(env["board_text"]) <= BOARD_TEXT_BUDGET
    shown = env["board"]["entries_full"] + env["board"]["entries_titles"]
    assert shown == 4 - env["board"]["remaining_entries"]


def test_status_revalidated_at_claim(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    oid = post(root, 1)["opportunity_id"]
    bpass(root, st)
    add_note(root, by="tony", opportunity_id=oid, text="found someone", now=T0)
    set_status(root, by="tony", opportunity_id=oid, status="closed", reason="done", now=T0)
    s = Session()
    run_next_event(s, st, now=T0)
    text = s.envelopes[0]["board_text"]
    assert "Status now: closed (done)" in text and "found someone" in text


def test_two_board_wakes_per_utc_day_then_waiting(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    for i in range(3):
        post(root, i, by=["tony", "custodian", "tony"][i])
        bpass(root, st)
        if i < 2:
            assert run_next_event(Session(), st, now=T0)["status"] == "completed"
    assert st.claim_next_pending(now=T0) is None
    summary = summarize_event_log(st.read_records(), now=T0)
    assert summary["pending_runnable_count"] == 0 and summary["pending_waiting_count"] == 1
    tomorrow = T0 + timedelta(days=1)
    assert run_next_event(Session(), st, now=tomorrow)["status"] == "completed"


def test_quiet_defers_board_wakes(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    # the onboarding wake declares a timed quiet
    rid = [r for r in st.read_records() if r.get("status") == "completed"][-1]["result_record_id"]
    st.append({"record_type": "quiet_declaration", "declaration_id": "d", "declared_by_cycle": 2,
               "declared_by_record_id": rid, "reason": "resting",
               "until": (T0 + timedelta(hours=5)).isoformat(), "created_at": T0.isoformat()})
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1)
    bpass(root, st)
    assert st.claim_next_pending(now=T0) is None
    assert st.claim_next_pending(now=T0 + timedelta(hours=6)) is not None


# --- failure ---------------------------------------------------------------------

def test_failed_wake_retries_then_abandons_at_three_and_notes_once_per_run(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1); post(root, 2, by="custodian")
    bpass(root, st)
    days = [T0, T0 + timedelta(days=1), T0 + timedelta(days=2)]
    for k, day in enumerate(days, start=1):
        with pytest.raises(RuntimeError):
            run_next_event(Session(fail=RuntimeError("boom")), st, now=day)
        pend = board_events(st, "pending")
        if k < 3:
            assert sorted(e["board"]["attempt"] for e in pend) == [k + 1, k + 1]
            assert {e["event_id"] for e in pend} == {match_event_id("qwen", s, 1, k + 1) for s in (1, 2)}
        else:
            assert pend == []
    abandoned = [r for r in st.read_records() if r.get("record_type") == "board_match_abandoned"]
    assert {r["board_seq"] for r in abandoned} == {1, 2}
    assert bpass(root, st, now=days[-1])["appended"] == 0     # abandoned is not re-queued under this generation
    # the next wake is told: one note per failed run, the terminal one says so
    from hamutay.board.write import post_opening  # noqa: F401
    from hamutay.events import build_inbound_event
    st.append(build_inbound_event(purpose="hello", sender="tony"))
    s = Session()
    run_next_event(s, st, now=days[-1])
    notes = s.envelopes[0]["operational_notes"]
    board_notes = [n for n in notes if "board match" in n]
    assert len(board_notes) == 3
    assert "reached the limit of 3 attempts" in board_notes[-1]


def test_pass_repairs_a_failure_whose_successor_was_lost(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1)
    bpass(root, st)
    ev, running = st.claim_next_pending(now=T0)
    st.append({"record_type": "event_status", "event_id": ev["event_id"], "event_type": "board_match",
               "status": "failed", "run_id": running["run_id"], "failed_at": T0.isoformat(),
               "error_type": "X", "error": "lost successor"})
    bpass(root, st)
    assert latest(st)[match_event_id("qwen", 1, 1, 2)]["status"] == "pending"


# --- subscriptions -----------------------------------------------------------------

def test_subscription_to_shown_entries_until_pass_or_clear(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    oid = post(root, 1)["opportunity_id"]
    add_note(root, by="tony", opportunity_id=oid, text="before showing", now=T0)
    bpass(root, st)
    s = Session()
    run_next_event(s, st, now=T0)
    assert "before showing" in s.envelopes[0]["board_text"]
    assert bpass(root, st)["appended"] == 0                 # the earlier note was shown as a current note
    add_note(root, by="tony", opportunity_id=oid, text="after showing", now=T0)
    bpass(root, st)
    pend = board_events(st, "pending")
    assert [e["board"]["record_type"] for e in pend] == ["note"]
    s2 = Session()
    run_next_event(s2, st, now=T0)
    assert "new note on an entry you were shown" in s2.envelopes[0]["board_text"]
    tomorrow = T0 + timedelta(days=1)
    pass_entry(st, "qwen", oid, tomorrow)
    add_note(root, by="tony", opportunity_id=oid, text="after pass", now=tomorrow)
    bpass(root, st, now=tomorrow)
    assert board_events(st, "pending") == []


def test_clearing_the_filter_stops_subscriptions(on):
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    oid = post(root, 1)["opportunity_id"]
    bpass(root, st)
    run_next_event(Session(), st, now=T0)
    add_note(root, by="tony", opportunity_id=oid, text="update", now=T0)
    bpass(root, st)
    assert len(board_events(st, "pending")) == 1
    clear_filter(st, "qwen", T0)
    assert st.claim_next_pending(now=T0 + timedelta(days=1)) is None
    assert board_events(st, "pending") == []
    bpass(root, st)
    assert board_events(st, "pending") == []


def test_boot_recovery_repends_a_crashed_batch(on):
    from hamutay.heartbeat import recover_orphaned_running
    root, cfg, _ = on
    st = store_of(cfg)
    drain_onboarding_after_pass(root, st)
    set_filter(st, "qwen", {"kinds": ["review"]}, T0)
    post(root, 1); post(root, 2, by="custodian")
    bpass(root, st)
    st.claim_next_pending(now=T0)                  # crash: never terminalized
    assert len(recover_orphaned_running(st)) == 2
    s = Session()
    run_next_event(s, st, now=T0)
    assert s.envelopes[0]["board_text"].count("== Entry") == 2
