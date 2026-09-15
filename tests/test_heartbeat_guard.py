import json
from datetime import datetime, timezone
import pytest
from hamutay.events import EventStore, LeaseGateRequired, build_inbound_event, run_next_event, run_pending_events
from hamutay.gpu_lease.actions import Ctx, REGISTRY, Lease, Release, run as run_action
from hamutay.gpu_lease.gate import LeaseGate
from hamutay.gpu_lease.state import paths, locked
from hamutay.gpu_lease import ledger
from datetime import timedelta
from hamutay.heartbeat import (GPU_LEASE_SENTENCE, DailyLedger, HeartbeatLoop, WakeBudget,
                               assert_canonical_lock_path, assert_lease_door_has_base_url,
                               build_constitution)

NOW = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)

class FakeSystemd:  # minimal copy of tests/gpu_lease/conftest.py's
    def __init__(self): self.units = {}; self.calls = []; self.fail_show = False
    def show(self, unit):
        return dict(self.units.get(unit, {"active_state": "inactive", "sub_state": "dead", "load_state": "not-found", "invocation_id": ""}))
    def start(self, unit): self.calls.append(("start", unit)); self.units[unit] = {"active_state": "active", "sub_state": "running", "load_state": "loaded", "invocation_id": "i1"}; return 0, ""
    def stop(self, unit): self.calls.append(("stop", unit)); self.units.setdefault(unit, {}).update(active_state="inactive", sub_state="dead", load_state="loaded"); return 0, ""
    def kill(self, unit, signal="TERM"): return 0, ""

@pytest.fixture
def bound(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    door = tmp_path / "community" / "qwen"; door.mkdir(parents=True)
    (door / "door.json").write_text(json.dumps({"gpu_lease": "4090"}))
    store = EventStore(door / "session.jsonl.events.jsonl")
    store.append(build_inbound_event(purpose="hello", sender="t"))
    return store, paths(), FakeSystemd()

def test_bound_store_refuses_unguarded_claim(bound):
    store, _, _ = bound
    assert store.lease_binding == "4090"
    with pytest.raises(LeaseGateRequired):
        store.claim_next_pending(now=NOW)
    with pytest.raises(LeaseGateRequired):
        run_next_event(None, store, now=NOW)

def test_unbound_store_unchanged(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    store.append(build_inbound_event(purpose="hello", sender="t"))
    assert store.claim_next_pending(now=NOW) is not None

def test_gate_claims_when_free_and_blocks_when_leased(bound):
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx)
    status, payload = gate.claim(NOW)
    assert status == "claimed" and payload[1]["status"] == "running"
    store.append(build_inbound_event(purpose="again", sender="t"))
    with locked(p):
        run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    status, payload = gate.claim(NOW)
    assert status == "blocked" and payload["kind"] == "lease"

def test_run_pending_events_stops_on_lease_blocked(bound):
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    batch = run_pending_events(None, store, limit=3, now=NOW, claim_gate=LeaseGate(store, ctx))
    assert batch["ran"] == 0 and batch["results"][0]["status"] == "lease_blocked"

def test_dangling_release_of_expired_lease_does_not_raise(bound):
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        outcome = run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    lease_id = outcome["lease_id"]
    # A release intent was written but never reconciled to an outcome: it is
    # dangling. resolve_dangling() will reconcile it (the scope is already
    # dead under FakeSystemd), leaving no lease at all -- claim() must not
    # let Expire()'s own NotFree escape when the lease it expected is gone.
    ledger.append(p, {"action_id": "dangling-release-1", "phase": "intent", "action": "release",
                       "by": ctx.by, "at": NOW.isoformat(), "lease_id": lease_id,
                       "generation_before": 1, "scope_unit": outcome["scope_unit"],
                       "episode_id": lease_id})
    later = NOW + timedelta(hours=2)  # past the 1h ttl: lease is expired
    ctx_later = Ctx(p, sd, now=lambda: later, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx_later)
    status, payload = gate.claim(later)  # must not raise NotFree
    assert status in ("none", "claimed")

def test_expire_not_free_race_does_not_raise(bound, monkeypatch):
    """Directly exercises the ruling: if the lease stops being expired between
    gate.claim()'s expired-check and Expire().intent()'s own re-read (a dangling
    expire/release reconciled concurrently, or the clock advancing), intent()
    raises NotFree. claim() must swallow it, not propagate it, and evaluate
    is_free() on the now-current state."""
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        run_action(ctx, Lease("yupi", "t", timedelta(hours=1), None), REGISTRY)
    later = NOW + timedelta(hours=2)
    ctx_later = Ctx(p, sd, now=lambda: later, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx_later)

    import hamutay.gpu_lease.gate as gate_module

    def _raises_not_free(self, ctx):
        raise gate_module.NotFree("lease no longer expired")

    monkeypatch.setattr(gate_module.Expire, "intent", _raises_not_free)
    status, payload = gate.claim(later)  # must not raise
    assert status in ("none", "claimed", "blocked")

def test_malformed_door_json_raises_lease_gate_required(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    door = tmp_path / "community" / "broken"; door.mkdir(parents=True)
    (door / "door.json").write_text('{"gpu_lease":')
    with pytest.raises(LeaseGateRequired):
        EventStore(door / "session.jsonl.events.jsonl")

def test_empty_gpu_lease_is_unbound(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    door = tmp_path / "community" / "empty"; door.mkdir(parents=True)
    (door / "door.json").write_text(json.dumps({"gpu_lease": ""}))
    store = EventStore(door / "session.jsonl.events.jsonl")
    assert store.lease_binding is None


# --- Task 7: one transition API with episode keys, hydrated from the store --

def _loop(store, now, **kw):
    return HeartbeatLoop(None, store, now=lambda: now, sleep=lambda s: None,
                         run_pending=lambda *a, **k: {"ran": 0, "results": []},
                         summarize=lambda records, now: {"pending_runnable_count": 0, "pending_waiting_count": 0}, **kw)


def test_transition_dedups_on_episode_key(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    loop = _loop(store, NOW)
    loop._transition("resting", reason="substrate_lent", episode_key="L1", detail={"episode_id": "L1"}, now=NOW)
    loop._transition("resting", reason="substrate_lent", episode_key="L1", detail={"episode_id": "L1"}, now=NOW)
    loop._transition("resting", reason="substrate_lent", episode_key="L2", detail={"episode_id": "L2"}, now=NOW)
    statuses = [r for r in store.read_records() if r.get("record_type") == "heartbeat_status"]
    assert [r["detail"]["episode_id"] for r in statuses] == ["L1", "L2"]


def test_hydration_from_store_prevents_swallowing_after_restart(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    first = _loop(store, NOW)
    first._transition("quiet", reason="undeclared_quiet", now=NOW)
    second = _loop(store, NOW)
    second._hydrate_last_transition()
    assert second._last_transition == ("quiet", "undeclared_quiet", None)
    second._transition("resting", reason="substrate_lent", episode_key="L1", detail={"episode_id": "L1"}, now=NOW)
    second._transition("quiet", reason="undeclared_quiet", now=NOW)   # must append: last was the rest
    statuses = [r["status"] for r in store.read_records() if r.get("record_type") == "heartbeat_status"]
    assert statuses == ["quiet", "resting", "quiet"]


def test_hydration_from_empty_store_is_none(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    loop = _loop(store, NOW)
    loop._hydrate_last_transition()
    assert loop._last_transition is None


def test_hydration_reads_day_key_when_no_episode_id(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    first = _loop(store, NOW)
    first._transition("resting", reason="daily_budget_reached", detail={"day": "2026-09-15"}, now=NOW, episode_key="2026-09-15")
    second = _loop(store, NOW)
    second._hydrate_last_transition()
    assert second._last_transition == ("resting", "daily_budget_reached", "2026-09-15")


def test_transition_no_episode_key_dedups_as_before(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    loop = _loop(store, NOW)
    loop._transition("quiet", reason="undeclared_quiet", now=NOW)
    loop._transition("quiet", reason="undeclared_quiet", now=NOW)
    statuses = [r for r in store.read_records() if r.get("record_type") == "heartbeat_status"]
    assert len(statuses) == 1


def test_boot_hydrates_before_appending_waking_boot(tmp_path):
    store = EventStore(tmp_path / "s.jsonl.events.jsonl")
    first = _loop(store, NOW)
    first._transition("resting", reason="substrate_lent", episode_key="L1", detail={"episode_id": "L1"}, now=NOW)
    second = _loop(store, NOW)
    second.boot()
    assert second._last_transition == ("waking", "boot", None)
    statuses = [(r["status"], r["reason"]) for r in store.read_records() if r.get("record_type") == "heartbeat_status"]
    assert statuses == [("resting", "substrate_lent"), ("waking", "boot")]


# --- Task 8: the substrate guard in the heartbeat loop ----------------------

def _guarded_loop(store, p, sd, now, ready=True):
    ctx = Ctx(p, sd, now=lambda: now, by="heartbeat:qwen")
    gate = LeaseGate(store, ctx, base_url="http://127.0.0.1:8081/v1",
                     fetch=lambda url, timeout: 200 if ready else None)
    loop = HeartbeatLoop(None, store, now=lambda: now, sleep=lambda s: None,
                         run_pending=lambda *a, **k: {"ran": 0, "results": []},
                         summarize=lambda records, now: {"pending_runnable_count": 0,
                                                         "pending_waiting_count": 0},
                         guard=gate)
    return loop, gate, ctx


def _statuses(store):
    return [(r["status"], r["reason"], (r.get("detail") or {}).get("episode_id"))
            for r in store.read_records() if r.get("record_type") == "heartbeat_status"]


def test_rest_record_precedes_stop_and_wait_ack_exists(bound):
    store, p, sd = bound
    sd.units["hamutay-llama-server.service"] = {"active_state": "active", "sub_state": "running",
                                                "load_state": "loaded", "invocation_id": "i1"}
    loop, gate, ctx = _guarded_loop(store, p, sd, NOW)
    with locked(p):
        act = Lease("yupi", "t", timedelta(hours=1), None); run_action(ctx, act, REGISTRY)
    result = loop.step()
    assert result["state"] == "resting"
    assert _statuses(store)[-1] == ("resting", "substrate_lent", act.lease_id)
    rest_at = [r for r in store.read_records() if r.get("status") == "resting"][0]["created_at"]
    stop_rows = [r for r in ledger.rows(p) if r["action"] == "ensure_stopped" and r["phase"] == "outcome"]
    assert stop_rows and stop_rows[0]["outcome"] == "ok" and stop_rows[0]["at"] >= rest_at
    assert ("stop", "hamutay-llama-server.service") in sd.calls
    # a second step appends nothing new and does not stop again
    n = len(sd.calls); loop.step()
    assert len([c for c in sd.calls[n:] if c[0] == "stop"]) == 0 and _statuses(store)[-1][0] == "resting"


def test_return_sequence_starts_server_warms_then_claims(bound):
    store, p, sd = bound
    sd.units["hamutay-llama-server.service"] = {"active_state": "inactive", "sub_state": "dead",
                                                "load_state": "loaded", "invocation_id": ""}
    loop, gate, ctx = _guarded_loop(store, p, sd, NOW, ready=False)
    with locked(p):
        act = Lease("yupi", "t", timedelta(hours=1), None); run_action(ctx, act, REGISTRY)
    loop.step()                                  # resting
    with locked(p):
        run_action(ctx, Release(act.lease_id), REGISTRY)
    r = loop.step()
    assert r["state"] == "warming" and ("start", "hamutay-llama-server.service") in sd.calls
    assert _statuses(store)[-1] == ("waking", "substrate_returning", act.lease_id)
    gate._fetch = lambda url, timeout: 200
    gate._context_validated = lambda: True     # Task 9 supplies the real check
    r = loop.step()
    assert r["state"] in ("quiet", "active", "waiting")
    obs = [x for x in ledger.rows(p) if x.get("phase") == "observation"]
    assert [o["action"] for o in obs] == ["server_ready"]
    loop.step()
    assert len([x for x in ledger.rows(p) if x.get("phase") == "observation"]) == 1   # no churn


def test_two_leases_back_to_back_are_two_episodes(bound):
    store, p, sd = bound
    loop, gate, ctx = _guarded_loop(store, p, sd, NOW)
    with locked(p):
        a = Lease("yupi", "t", timedelta(hours=1), None); run_action(ctx, a, REGISTRY)
    loop.step()
    with locked(p):
        run_action(ctx, Release(a.lease_id), REGISTRY)
        b = Lease("tq", "t", timedelta(hours=1), None); run_action(ctx, b, REGISTRY)
    loop.step()
    eps = [s[2] for s in _statuses(store) if s[0] == "resting"]
    assert eps == [a.lease_id, b.lease_id]


def test_boot_reconciliation_closes_episode_ended_while_down(bound):
    store, p, sd = bound
    loop, gate, ctx = _guarded_loop(store, p, sd, NOW)
    with locked(p):
        a = Lease("yupi", "t", timedelta(hours=1), None); run_action(ctx, a, REGISTRY)
    loop.step()
    later = NOW + timedelta(minutes=30)
    with locked(p):
        run_action(Ctx(p, sd, now=lambda: later, by="ayllu-gpu"), Release(a.lease_id), REGISTRY)
    loop2, gate2, _ = _guarded_loop(store, p, sd, later + timedelta(minutes=5))
    loop2.boot()
    st = _statuses(store)
    assert st[-2] == ("waking", "substrate_returning", a.lease_id) and st[-1] == ("waking", "boot", None)
    returning = [r for r in store.read_records() if r.get("reason") == "substrate_returning"][0]
    assert returning["created_at"].startswith(later.isoformat()[:16]) and returning["detail"]["closed_at_source"] == "ledger"


def test_restart_during_lease_appends_continuation(bound):
    store, p, sd = bound
    loop, gate, ctx = _guarded_loop(store, p, sd, NOW)
    with locked(p):
        a = Lease("yupi", "t", timedelta(hours=1), None); run_action(ctx, a, REGISTRY)
    loop.step()
    loop2, _, _ = _guarded_loop(store, p, sd, NOW + timedelta(minutes=1))
    loop2.boot(); loop2.step()
    st = _statuses(store)
    assert st[-2] == ("waking", "boot", None) and st[-1] == ("resting", "substrate_lent", a.lease_id)
    assert [r for r in store.read_records() if r.get("status") == "resting"][-1]["detail"]["continuation"] is True


def test_quarantine_rests_with_its_own_reason_and_no_start(bound):
    store, p, sd = bound
    p.dir.mkdir(parents=True, exist_ok=True); p.lease.write_bytes(b"{garbage")
    loop, gate, ctx = _guarded_loop(store, p, sd, NOW)
    r = loop.step()
    assert r["state"] == "resting" and _statuses(store)[-1][:2] == ("resting", "substrate_lease_unreadable")
    assert not any(c[0] == "start" for c in sd.calls)
    assert p.quarantine.exists()


# --- Task 8 review round 1: reconstruction arm, launch assertions -----------

def _force_stop_row(p, episode_id, at):
    """An ok force_stop outcome as cmd_force_stop would leave it."""
    return ledger.append(p, {"action_id": "fs-" + episode_id, "phase": "outcome",
                             "action": "force_stop", "outcome": "ok", "episode_id": episode_id,
                             "by": "ayllu-gpu", "at": at, "observed": {}, "detail": {}})


def test_boot_reconstructs_rest_for_force_stop_the_store_never_saw(bound):
    """A crash between force-stop's own record and its outcome leaves an ok
    force_stop in the ledger with no resting record. Boot rebuilds both ends."""
    store, p, sd = bound
    at = (NOW - timedelta(minutes=20)).isoformat()
    _force_stop_row(p, "ep-forced", at)
    loop, gate, _ = _guarded_loop(store, p, sd, NOW)
    gate.reconcile_on_boot(NOW)
    rebuilt = [r for r in store.read_records()
               if r.get("record_type") == "heartbeat_status"
               and (r.get("detail") or {}).get("episode_id") == "ep-forced"]
    assert [(r["status"], r["reason"]) for r in rebuilt] == [
        ("resting", "substrate_lent"), ("waking", "substrate_returning")]
    assert rebuilt[0]["detail"]["source"] == "reconstructed_from_ledger"
    assert rebuilt[0]["created_at"] == at and rebuilt[1]["created_at"] == at
    # idempotent: the episode now has a resting record, so a second pass is quiet
    before = len(store.read_records())
    gate.reconcile_on_boot(NOW)
    assert len(store.read_records()) == before


def test_boot_reconstructs_rest_only_while_the_forced_lease_is_still_live(bound):
    """A force_stop whose lease is still live is an open episode: rebuild the
    rest, but do not close what has not ended."""
    store, p, sd = bound
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    with locked(p):
        act = Lease("yupi", "t", timedelta(hours=1), None); run_action(ctx, act, REGISTRY)
    at = NOW.isoformat()
    _force_stop_row(p, act.lease_id, at)
    loop, gate, _ = _guarded_loop(store, p, sd, NOW)
    gate.reconcile_on_boot(NOW)
    rebuilt = [r for r in store.read_records()
               if r.get("record_type") == "heartbeat_status"
               and (r.get("detail") or {}).get("episode_id") == act.lease_id]
    assert [(r["status"], r["reason"]) for r in rebuilt] == [("resting", "substrate_lent")]
    assert rebuilt[0]["detail"]["source"] == "reconstructed_from_ledger"


def test_canonical_lock_path_assertion_both_ways(tmp_path):
    events = str(tmp_path / "s.jsonl.events.jsonl")
    assert_canonical_lock_path(events + ".heartbeat.lock", events)   # must not raise
    with pytest.raises(SystemExit) as caught:
        assert_canonical_lock_path(str(tmp_path / "elsewhere.lock"), events)
    assert "canonical" in str(caught.value)


def test_lease_door_requires_a_base_url():
    assert_lease_door_has_base_url(None, None)                       # unbound: no opinion
    assert_lease_door_has_base_url("4090", "http://127.0.0.1:8081/v1")
    with pytest.raises(SystemExit) as caught:
        assert_lease_door_has_base_url("4090", None)
    assert "anthropic-direct backend cannot participate" in str(caught.value)


def test_constitution_gains_the_gpu_lease_sentence_only_when_bound():
    budget = WakeBudget(1.5, 48)
    assert build_constitution(budget).endswith(".")
    assert GPU_LEASE_SENTENCE not in build_constitution(budget)
    assert GPU_LEASE_SENTENCE not in build_constitution(None)
    assert build_constitution(budget, gpu_lease=True).endswith(GPU_LEASE_SENTENCE)
    assert build_constitution(None, gpu_lease=True).endswith(GPU_LEASE_SENTENCE)


# --- Task 9: context ceiling across a loan ----------------------------------

def test_latest_context_observation_prefers_later_matching_record(tmp_path):
    from hamutay.heartbeat import latest_context_observation
    log = tmp_path / "s.jsonl"
    lines = [
        {"cycle": 1, "state": {}, "launch": {"model": "q", "provider": "openai",
                                             "base_url": "http://127.0.0.1:8081/v1",
                                             "context_limit": 65536}},
        {"record_type": "substrate_observation", "context_limit": 32768,
         "source": "discovered", "invocation_id": "inv9", "model": "q",
         "provider": "openai", "base_url": "http://127.0.0.1:8081/v1",
         "at": "2026-09-20T15:00:00+00:00"},
        {"record_type": "substrate_observation", "context_limit": 1000,
         "source": "discovered", "invocation_id": "other", "model": "z",
         "provider": "openai", "base_url": "http://127.0.0.1:9999/v1",
         "at": "2026-09-20T15:01:00+00:00"},
    ]
    log.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    assert latest_context_observation(
        str(log), model="q", provider="openai",
        base_url="http://127.0.0.1:8081/v1") == (32768, "inv9")
    assert latest_context_observation(
        str(log), model="q", provider="openai", base_url="http://other") == (None, None)
    assert latest_context_observation(
        str(tmp_path / "absent.jsonl"), model="q", provider="openai",
        base_url="http://127.0.0.1:8081/v1") == (None, None)


def test_latest_context_observation_takes_the_launch_when_it_is_later(tmp_path):
    """A state-bearing record written after the observation wins, and carries
    no invocation_id — the launch is not evidence about any invocation."""
    from hamutay.heartbeat import latest_context_observation
    log = tmp_path / "s.jsonl"
    launch = {"model": "q", "provider": "openai",
              "base_url": "http://127.0.0.1:8081/v1", "context_limit": 65536}
    lines = [
        {"record_type": "substrate_observation", "context_limit": 32768,
         "source": "discovered", "invocation_id": "inv9", "model": "q",
         "provider": "openai", "base_url": "http://127.0.0.1:8081/v1", "at": "x"},
        "not json at all",
        {"cycle": 1, "state": None, "launch": launch},          # stateless: skipped
        {"cycle": 2, "state": {}, "launch": launch},
    ]
    log.write_text("\n".join(
        line if isinstance(line, str) else json.dumps(line) for line in lines) + "\n")
    assert latest_context_observation(
        str(log), model="q", provider="openai",
        base_url="http://127.0.0.1:8081/v1") == (65536, None)


def test_resolve_context_limit_inherits_when_discovery_fails(tmp_path):
    from hamutay.heartbeat import resolve_context_limit
    log = tmp_path / "s.jsonl"
    log.write_text(json.dumps({
        "cycle": 1, "state": {},
        "launch": {"model": "q", "provider": "openai",
                   "base_url": "http://127.0.0.1:8081/v1",
                   "context_limit": 65536}}) + "\n")

    class A:
        context_limit = None
        provider = "openai"
        base_url = "http://127.0.0.1:8081/v1"
        model = "q"

    assert resolve_context_limit(
        A(), discover=lambda url: None, log_path=str(log)) == (65536, "inherited")
    # discovery still beats inheritance
    assert resolve_context_limit(
        A(), discover=lambda url: 40000, log_path=str(log)) == (40000, "discovered")

    class B(A):
        context_limit = 4096

    assert resolve_context_limit(
        B(), discover=lambda url: None, log_path=str(log)) == (4096, "explicit")
    # no log to inherit from: provider default
    assert resolve_context_limit(A(), discover=lambda url: None) == (None, "provider default")


def test_parser_rejects_nonpositive_context_limit():
    from hamutay.heartbeat import build_parser
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--log-path", "x", "--context-limit", "0"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--log-path", "x", "--context-limit", "-5"])
    assert build_parser().parse_args(
        ["--log-path", "x", "--context-limit", "4096"]).context_limit == 4096


def test_apply_context_limit_updates_backend_and_appends_observation(tmp_path):
    from hamutay.taste_open import OpenTasteSession

    class Backend:
        wake_mode = "natural"
        _context_limit = 1

        def call(self, *a, **k):
            raise AssertionError("not called")

    log = tmp_path / "s.jsonl"
    session = OpenTasteSession(
        model="q", backend=Backend(), log_path=str(log), enable_tools=True,
        wake_mode="natural",
        launch_config={"model": "q", "provider": "openai",
                       "base_url": "http://127.0.0.1:8081/v1"})
    session.apply_context_limit(65536, "discovered", "inv1")
    assert session._backend._context_limit == 65536
    assert session._launch_config["context_limit"] == 65536
    assert session._launch_config["context_limit_source"] == "discovered"
    rec = json.loads(log.read_text().splitlines()[-1])
    assert rec["record_type"] == "substrate_observation"
    assert rec["invocation_id"] == "inv1"
    assert rec["context_limit"] == 65536
    assert rec["source"] == "discovered"
    assert rec["model"] == "q" and rec["provider"] == "openai"
    assert rec["base_url"] == "http://127.0.0.1:8081/v1"
    datetime.fromisoformat(rec["at"])          # a real UTC ISO timestamp


def test_gate_does_not_claim_until_discovery_succeeds_for_new_invocation(bound, tmp_path):
    store, p, sd = bound
    sd.units["hamutay-llama-server.service"] = {
        "active_state": "active", "sub_state": "running",
        "load_state": "loaded", "invocation_id": "inv-new"}
    log_path = tmp_path / "s.jsonl"

    class Session:
        _backend = type("B", (), {"_context_limit": None})()
        _launch_config = {"model": "q", "provider": "openai",
                          "base_url": "http://127.0.0.1:8081/v1"}
        _log_path = str(log_path)
        applied: list = []

        def apply_context_limit(self, limit, source, inv):
            self.applied.append((limit, source, inv))
            log_path.write_text(json.dumps({
                "record_type": "substrate_observation", "context_limit": limit,
                "source": source, "invocation_id": inv,
                **self._launch_config, "at": "x"}) + "\n")

    session = Session()
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")
    attempts = []

    def discover(url):
        attempts.append(url)
        return None if len(attempts) < 2 else 65536

    gate = LeaseGate(store, ctx, base_url="http://127.0.0.1:8081/v1",
                     fetch=lambda u, t: 200, session=session, discover=discover)
    status, info = gate.observe(NOW)
    assert status == "free_not_ready" and info["context"] == "undiscovered"
    status, info = gate.observe(NOW)
    assert status == "free_ready"
    assert session.applied == [(65536, "discovered", "inv-new")]
    # already validated for this invocation: no third discovery attempt
    assert gate.observe(NOW)[0] == "free_ready" and len(attempts) == 2


def test_gate_with_an_explicit_limit_never_discovers(bound):
    store, p, sd = bound
    sd.units["hamutay-llama-server.service"] = {
        "active_state": "active", "sub_state": "running",
        "load_state": "loaded", "invocation_id": "inv-new"}
    ctx = Ctx(p, sd, now=lambda: NOW, by="heartbeat:qwen")

    def discover(url):
        raise AssertionError("explicit is never overwritten")

    gate = LeaseGate(store, ctx, base_url="http://127.0.0.1:8081/v1",
                     fetch=lambda u, t: 200, session=object(),
                     discover=discover, explicit_limit=4096)
    assert gate.observe(NOW)[0] == "free_ready"
