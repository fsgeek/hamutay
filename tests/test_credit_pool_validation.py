"""Independent validation of the 18 credit-pool behaviours (2026-10-19).

Expected amounts and wording come from the spec, not production helpers.
All configuration and logs are temporary; the provider boundary is offline.
"""

from __future__ import annotations

import builtins
import functools
import json
import socket
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import hamutay.heartbeat as hb
import hamutay.taste_open as taste
from hamutay.credit_pool import (
    CreditPool,
    PoolSpend,
    load_credit_pool,
    pool_note,
    pool_note_producer,
)
from hamutay.events import EventStore, build_inbound_event, run_pending_events
from hamutay.taste_open import ExchangeResult, OpenTasteSession


UTC = timezone.utc
NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
START = datetime(2026, 10, 1, tzinfo=UTC)
END = datetime(2026, 11, 1, tzinfo=UTC)
MISSING = object()
CONFIG = {
    "credit_usd": 200,
    "period_start": "2026-10-01",
    "period_end": "2026-10-31",
}
ACTIVE = (
    "Credit pool: $187.50 of $200.00 remaining (estimated from tokens; "
    "Anthropic's bill is authoritative). It expires 2026-10-31; "
    "unused credit does not carry over."
)
EXPIRED = (
    "Credit pool: the period that ended 2026-10-31 is over; "
    "its unused credit did not carry over."
)


@pytest.fixture(autouse=True)
def isolated_home_and_no_network(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))

    def forbidden(*args, **kwargs):
        raise AssertionError("credit-pool validation must never use the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)

    # Session writes must stay in this pool's period even when tests run later.
    monkeypatch.setattr(taste, "datetime", FixedDatetime)


@pytest.fixture
def pool():
    return CreditPool(200, date(2026, 10, 1), date(2026, 10, 31))


def write_config(tmp_path, **overrides):
    path = tmp_path / "pool.json"
    path.write_text(json.dumps(CONFIG | overrides))
    return path


def cycle(ts="2026-10-19T12:00:00Z", *, cost=MISSING,
          provider="anthropic", metered=True, unreported=MISSING):
    launch = {"provider": provider, "model": "offline-validation"}
    if metered is not MISSING:
        launch["metered"] = metered
    usage = {"input_tokens": 100, "output_tokens": 10}
    if cost is not MISSING:
        usage["cost_usd"] = cost
    if unreported is not MISSING:
        usage["cost_turns_unreported"] = unreported
    return {"cycle": 1, "timestamp": ts, "state": {},
            "launch": launch, "usage": usage}


def write_log(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


# Config: behaviours 1-3. Rejecting bad data must be an explained SystemExit.


def test_config_defaults_unknown_keys_and_inclusive_last_day(tmp_path):
    loaded = load_credit_pool(write_config(tmp_path, _comment="ignored"))
    assert loaded.credit_usd == 200
    assert loaded.spent_before_tracking_usd == 0
    assert loaded.period_start_confirmed is False
    assert loaded.window == (START, END)


@pytest.mark.parametrize("value", [0, 0.25, 200])
def test_config_accepts_nonnegative_numbers_in_both_fields(tmp_path, value):
    loaded = load_credit_pool(write_config(
        tmp_path, credit_usd=value, spent_before_tracking_usd=value))
    assert loaded.credit_usd == value
    assert loaded.spent_before_tracking_usd == value


@pytest.mark.parametrize("value,want", [
    (True, True), (False, False), (1, False), (0, False),
    ("true", False), ("false", False), (None, False), ({}, False),
])
def test_confirmation_requires_json_true_not_truthiness(tmp_path, value, want):
    loaded = load_credit_pool(write_config(tmp_path, period_start_confirmed=value))
    assert loaded.period_start_confirmed is want


@pytest.mark.parametrize("text", ["not json", "{", "[]", "null", "true", "42", '"pool"'])
def test_bad_json_or_non_object_refuses_to_load(tmp_path, text):
    path = tmp_path / "bad-pool.json"
    path.write_text(text)
    with pytest.raises(SystemExit, match="credit pool:.*(read|JSON object)"):
        load_credit_pool(path)


@pytest.mark.parametrize("key", ["credit_usd", "spent_before_tracking_usd"])
@pytest.mark.parametrize("value", [True, False, -0.01, "200", None, [], {}])
def test_invalid_amount_names_the_field(tmp_path, key, value):
    with pytest.raises(SystemExit, match=key):
        load_credit_pool(write_config(tmp_path, **{key: value}))


@pytest.mark.parametrize("key", ["credit_usd", "spent_before_tracking_usd"])
@pytest.mark.parametrize("token", ["NaN", "Infinity", "1e309"])
def test_nonfinite_amount_refuses_to_publish_a_balance(tmp_path, key, token):
    """NaN/Infinity aren't JSON numbers; overflow cannot yield a valid balance."""
    path = tmp_path / "nonfinite-pool.json"
    body = CONFIG | {key: "REPLACE_NUMBER"}
    path.write_text(json.dumps(body).replace('"REPLACE_NUMBER"', token))
    with pytest.raises(SystemExit, match="credit pool:"):
        load_credit_pool(path)


@pytest.mark.parametrize("key", ["credit_usd", "period_start", "period_end"])
def test_missing_required_field_is_named(tmp_path, key):
    body = CONFIG.copy()
    del body[key]
    path = tmp_path / "missing-field.json"
    path.write_text(json.dumps(body))
    with pytest.raises(SystemExit, match=key):
        load_credit_pool(path)


@pytest.mark.parametrize("key", ["period_start", "period_end"])
@pytest.mark.parametrize("value", ["2026-02-30", "yesterday", "2026-10-01T00:00:00Z", None, True])
def test_bad_date_is_named(tmp_path, key, value):
    with pytest.raises(SystemExit, match=key):
        load_credit_pool(write_config(tmp_path, **{key: value}))


def test_reversed_period_refuses_to_load(tmp_path):
    with pytest.raises(SystemExit, match="period_end.*period_start"):
        load_credit_pool(write_config(tmp_path, period_end="2026-09-30"))


def test_single_day_period_includes_the_whole_day(tmp_path):
    loaded = load_credit_pool(write_config(tmp_path, period_start="2026-10-31"))
    assert loaded.window == (datetime(2026, 10, 31, tzinfo=UTC), END)


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid-utf8", "permission"])
def test_unreadable_file_exits_with_path_and_problem(tmp_path, monkeypatch, kind):
    path = tmp_path / "unreadable-pool.json"
    if kind == "directory":
        path.mkdir()
    elif kind == "invalid-utf8":
        path.write_bytes(b"\xff\xfe")
    elif kind == "permission":
        original = Path.read_text

        def read_text(self, *args, **kwargs):
            if self == path:
                raise PermissionError("validation permission denied")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", read_text)
    with pytest.raises(SystemExit) as exc:
        load_credit_pool(path)
    assert "credit pool:" in str(exc.value)
    assert str(path) in str(exc.value)
    assert "cannot read" in str(exc.value)


# Spend: behaviours 4-9. Large excluded costs make incorrect scope visible.


def test_pool_sums_every_door_plus_prior_spend_with_exact_window_edges(tmp_path):
    pool = load_credit_pool(write_config(tmp_path, spent_before_tracking_usd=7.25))
    write_log(tmp_path / "community/elder/session.jsonl", [
        cycle("2026-09-30T23:59:59.999999Z", cost=1000),
        cycle("2026-10-01T00:00:00Z", cost=1.25),
        cycle("2026-10-31T23:59:59.999999Z", cost=2.50),
        cycle("2026-11-01T00:00:00Z", cost=2000),
        cycle(cost=4000, provider="openrouter"),
        cycle(cost=8000, provider="openai"),
        cycle(cost=16000, metered=MISSING),
    ])
    write_log(tmp_path / "community/fable/session.jsonl", [
        cycle(cost=3), cycle(cost=32000, metered=False),
    ])
    for relative in ["session.jsonl", "experiments/demo/session.jsonl",
                     "smoke/session.jsonl", "community/session.jsonl",
                     "community/elder/nested/session.jsonl",
                     "community/elder/other.jsonl"]:
        write_log(tmp_path / relative, [cycle(cost=64000)])
    assert PoolSpend(tmp_path, pool).total() == {
        "cost_usd": 14, "wakes": 3, "unmeasured_wakes": 0,
    }


@pytest.mark.parametrize("metered", [MISSING, False, 1, "true", None])
def test_anthropic_requires_exact_metered_true(tmp_path, pool, metered):
    write_log(tmp_path / "community/fable/session.jsonl", [
        cycle(cost=199, metered=metered),
    ])
    assert PoolSpend(tmp_path, pool).total() == {
        "cost_usd": 0, "wakes": 0, "unmeasured_wakes": 0,
    }


@pytest.mark.parametrize("cost", [MISSING, None, True, False, "1.25", {}, []])
def test_nonnumeric_cost_is_an_unmeasured_wake_not_free(tmp_path, pool, cost):
    write_log(tmp_path / "community/fable/session.jsonl", [cycle(cost=cost)])
    spend = PoolSpend(tmp_path, pool).total()
    assert spend == {"cost_usd": 0, "wakes": 1, "unmeasured_wakes": 1}
    assert pool_note(pool, spend, None, NOW) == (
        "Credit pool: $200.00 of $200.00 remaining (estimated from tokens; "
        "Anthropic's bill is authoritative). It expires 2026-10-31; unused "
        "credit does not carry over. 1 wake(s) had no cost estimate, so the "
        "remaining amount is an upper bound. There is no daily ceiling."
    )


def test_partial_cost_is_counted_and_missing_turns_count_wakes_once(tmp_path, pool):
    write_log(tmp_path / "community/fable/session.jsonl", [
        cycle(cost=0.25, unreported=3), cycle(unreported=2), cycle(cost=0),
        cycle(provider="openrouter", unreported=9),
        cycle(metered=MISSING, unreported=9),
    ])
    spend = PoolSpend(tmp_path, pool).total()
    assert spend == {"cost_usd": 0.25, "wakes": 3, "unmeasured_wakes": 2}
    assert "2 wake(s) had no cost estimate, so the remaining amount is an upper bound." in pool_note(
        pool, spend, 25, NOW)


@pytest.mark.parametrize("provider,want", [
    (None, {"wakes": 3, "cost_usd": 3.75, "unmeasured_wakes": 1}),
    ("anthropic", {"wakes": 2, "cost_usd": 1.25, "unmeasured_wakes": 1}),
    ("openrouter", {"wakes": 1, "cost_usd": 2.5, "unmeasured_wakes": 0}),
    ("openai", {"wakes": 0, "cost_usd": 0, "unmeasured_wakes": 0}),
])
def test_span_filters_metered_provider_without_changing_day(tmp_path, provider, want):
    log = write_log(tmp_path / "session.jsonl", [
        cycle(cost=1.25), cycle(cost=99, metered=MISSING),
        cycle(cost=2.50, provider="openrouter"), cycle(),
        {"timestamp": NOW.isoformat(), "state": {}, "usage": {"cost_usd": 999}},
    ])
    ledger = hb.DailyLedger(str(log))
    assert ledger.span(START, END, provider=provider) == want
    assert ledger.day(NOW) == {
        "day": "2026-10-19", "wakes": 5, "cost_usd": 3.75,
        "unmeasured_wakes": 1, "cost_turns_unreported": 0,
    }


def test_span_normalizes_offsets_and_naive_timestamps_to_utc(tmp_path):
    log = write_log(tmp_path / "session.jsonl", [
        cycle("2026-09-30T17:00:00-07:00", cost=1),
        cycle("2026-10-01T00:00:00", cost=2),
        cycle("2026-11-01T01:00:00+01:00", cost=99),
    ])
    assert hb.DailyLedger(str(log)).span(
        datetime(2026, 9, 30, 17, tzinfo=timezone(timedelta(hours=-7))),
        datetime(2026, 11, 1), provider="anthropic",
    ) == {"wakes": 2, "cost_usd": 3, "unmeasured_wakes": 0}


def test_pool_refreshes_appends_and_new_doors_without_double_counting_prior_spend(tmp_path):
    pool = load_credit_pool(write_config(tmp_path, spent_before_tracking_usd=7.25))
    spend = PoolSpend(tmp_path, pool)
    assert spend.total() == {"wakes": 0, "cost_usd": 7.25, "unmeasured_wakes": 0}
    log = write_log(tmp_path / "community/fable/session.jsonl", [cycle(cost=1)])
    assert spend.total()["cost_usd"] == 8.25
    with log.open("a") as stream:
        stream.write(json.dumps(cycle(cost=2)) + "\n")
    write_log(tmp_path / "community/new-door/session.jsonl", [cycle(cost=3)])
    assert spend.total() == {"wakes": 3, "cost_usd": 13.25, "unmeasured_wakes": 0}
    assert spend.total() == {"wakes": 3, "cost_usd": 13.25, "unmeasured_wakes": 0}


@pytest.mark.parametrize("same_size", [False, True])
def test_pool_ignores_torn_tail_until_newline_even_without_size_growth(tmp_path, pool, same_size):
    log = write_log(tmp_path / "community/fable/session.jsonl", [cycle(cost=1)])
    with log.open("ab") as stream:
        stream.write(json.dumps(cycle(cost=2)).encode() + (b"\r" if same_size else b""))
    spend = PoolSpend(tmp_path, pool)
    assert spend.total() == {"wakes": 1, "cost_usd": 1, "unmeasured_wakes": 0}
    with log.open("r+b") as stream:
        stream.seek(-1 if same_size else 0, 2)
        stream.write(b"\n")
    assert spend.total() == {"wakes": 2, "cost_usd": 3, "unmeasured_wakes": 0}


def test_span_skips_bad_records_and_reuses_complete_unchanged_log(tmp_path, monkeypatch):
    log = write_log(tmp_path / "session.jsonl", [
        [], None, 42, "not a record", {"timestamp": "bad"}, cycle(cost=1.25),
    ])
    with log.open("a") as stream:
        stream.write("{broken json\n")
    ledger = hb.DailyLedger(str(log))
    assert ledger.span(START, END) == {"wakes": 1, "cost_usd": 1.25, "unmeasured_wakes": 0}
    original = builtins.open

    def no_reread(file, *args, **kwargs):
        if Path(file) == log:
            raise AssertionError("a complete unchanged log must use the cached rows")
        return original(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", no_reread)
    assert ledger.span(START, END) == {"wakes": 1, "cost_usd": 1.25, "unmeasured_wakes": 0}


# Note: behaviours 10-13. Equality intentionally forbids added spending advice.


@pytest.mark.parametrize("ceiling,suffix", [
    (25, " Today's ceiling: $25.00."), (0, " Today's ceiling: $0.00."),
    (None, " There is no daily ceiling."),
])
@pytest.mark.parametrize("now", [NOW, datetime(2026, 10, 31, 23, 59, 59, 999999, tzinfo=UTC)])
def test_active_note_is_exact_facts_only(pool, ceiling, suffix, now):
    assert pool_note(pool, {"cost_usd": 12.5, "unmeasured_wakes": 0}, ceiling, now) == ACTIVE + suffix


@pytest.mark.parametrize("spent", [200, 201.25, 1000])
def test_exhausted_pool_never_shows_negative_remaining(pool, spent):
    assert pool_note(pool, {"cost_usd": spent}, 25, NOW) == (
        "Credit pool: $0.00 of $200.00 remaining (estimated from tokens; "
        "Anthropic's bill is authoritative). It expires 2026-10-31; "
        "unused credit does not carry over. Today's ceiling: $25.00."
    )


def test_note_rounds_remaining_and_ceiling_to_two_places(pool):
    assert pool_note(pool, {"cost_usd": 12.3456}, 1.234, NOW) == (
        "Credit pool: $187.65 of $200.00 remaining (estimated from tokens; "
        "Anthropic's bill is authoritative). It expires 2026-10-31; "
        "unused credit does not carry over. Today's ceiling: $1.23."
    )


@pytest.mark.parametrize("now", [END, datetime(2026, 12, 15, tzinfo=UTC),
    datetime(2026, 10, 31, 17, tzinfo=timezone(timedelta(hours=-7)))])
@pytest.mark.parametrize("ceiling,suffix", [
    (25, " Today's ceiling: $25.00."), (None, " There is no daily ceiling."),
])
def test_expired_note_at_and_after_end_has_no_available_balance(pool, now, ceiling, suffix):
    assert pool_note(pool, {"cost_usd": 12.5, "unmeasured_wakes": 3}, ceiling, now) == EXPIRED + suffix


# Wiring: behaviours 14-18. Real stores, event runner, envelope and session.


class OfflineBackend:
    def __init__(self):
        self.envelopes = []

    def call(self, model, system, messages, experiment_label,
             extra_tools=None, tool_executor=None):
        self.envelopes.append(json.loads(messages[-1]["content"]))
        return ExchangeResult(raw_output={"response": "received", "resident_note": "awake"},
                              cost_usd=0.25)


def resident(tmp_path):
    backend = OfflineBackend()
    session = OpenTasteSession(
        model="offline-validation", backend=backend,
        log_path=str(tmp_path / "community/resident/session.jsonl"),
        project_root=tmp_path, enable_tools=True,
        launch_config={"provider": "anthropic", "metered": True},
    )
    return session, backend


@pytest.mark.parametrize("bound_without_plaza", [False, True])
def test_without_pool_or_plaza_runner_is_unchanged_and_envelope_has_no_pool(tmp_path, bound_without_plaza):
    store = EventStore(tmp_path / "events.jsonl")
    binding = SimpleNamespace(members=SimpleNamespace(plaza=None)) if bound_without_plaza else None
    wired = hb._run_pending_for(binding, store, pytest.fail)
    assert wired is run_pending_events
    session, backend = resident(tmp_path)
    store.append(build_inbound_event(purpose="hello", sender="validation"))
    assert wired(session, store, limit=1)["ran"] == 1
    assert not any("Credit pool:" in n for n in backend.envelopes[0].get("operational_notes", []))


def test_pool_only_partial_recomputes_spend_at_every_wake_in_one_batch(tmp_path, pool):
    store = EventStore(tmp_path / "events.jsonl")
    write_log(tmp_path / "community/other/session.jsonl", [cycle(cost=12.5)])
    producer = pool_note_producer(tmp_path, pool, 25, now=lambda: NOW)
    wired = hb._run_pending_for(None, store, pytest.fail, pool_notes=producer)
    assert isinstance(wired, functools.partial)
    assert wired.func is run_pending_events
    assert wired.keywords["extra_notes"] is producer
    session, backend = resident(tmp_path)
    for purpose in ["first", "second"]:
        store.append(build_inbound_event(purpose=purpose, sender="validation"))
    assert wired(session, store, limit=2)["ran"] == 2
    assert backend.envelopes[0]["operational_notes"] == [ACTIVE + " Today's ceiling: $25.00."]
    assert backend.envelopes[1]["operational_notes"] == [
        "Credit pool: $187.25 of $200.00 remaining (estimated from tokens; "
        "Anthropic's bill is authoritative). It expires 2026-10-31; unused "
        "credit does not carry over. Today's ceiling: $25.00."
    ]


@pytest.mark.parametrize("include_pool", [False, True])
def test_plaza_notes_reach_envelope_before_optional_pool(tmp_path, pool, include_pool):
    from hamutay.assembly.binding import bind, load_members
    from hamutay.plaza.send import send

    members = tmp_path / "community/plaza/members.json"
    members.parent.mkdir(parents=True)
    members.write_text(json.dumps({
        "ledger": "community/plaza/assembly.jsonl", "plaza": "community/plaza/plaza.jsonl",
        "members": {door: {"session": f"community/{door}/session.jsonl",
                           "events": f"community/{door}/session.jsonl.events.jsonl"}
                    for door in ["resident", "other"]},
    }))
    for door in ["resident", "other"]:
        (tmp_path / "community" / door).mkdir()
    cfg = load_members(tmp_path)
    binding, _ = bind(tmp_path, cfg.members["resident"].session, cfg.members["resident"].events)
    assert binding is not None
    send(cfg, actor="tony", via="cli", to="plaza", text="hello", now=NOW, key="test-post")
    store = EventStore(cfg.members["resident"].events)
    producer = pool_note_producer(tmp_path, pool, None, now=lambda: NOW) if include_pool else None
    wired = hb._run_pending_for(binding, store, pytest.fail, pool_notes=producer)
    session, backend = resident(tmp_path)
    store.append(build_inbound_event(purpose="hello", sender="validation"))
    assert wired(session, store, limit=1)["ran"] == 1
    notes = backend.envelopes[0]["operational_notes"]
    assert notes[0].startswith("plaza: 1 message(s)")
    if include_pool:
        assert notes[1:] == [
            "Credit pool: $200.00 of $200.00 remaining (estimated from tokens; "
            "Anthropic's bill is authoritative). It expires 2026-10-31; unused "
            "credit does not carry over. There is no daily ceiling."
        ]
    else:
        assert len(notes) == 1


@pytest.fixture
def launch_offline(tmp_path, monkeypatch, capsys):
    """Keep main's config, lock, ledger, runner and reporting; replace model construction."""
    captured = {}

    def build_offline(args):
        budget, _ = hb.resolve_budget(args)
        return SimpleNamespace(_heartbeat_base_url=None, _heartbeat_budget=budget,
                               _assembly=None), None, {"provider": "openrouter"}

    def stop_at_loop(loop):
        captured["loop"] = loop

    monkeypatch.setattr(hb, "build_session", build_offline)
    monkeypatch.setattr(hb.HeartbeatLoop, "run_forever", stop_at_loop)

    def launch(*args):
        monkeypatch.setattr(sys, "argv", [
            "heartbeat", "--log-path", str(tmp_path / "community/launch/session.jsonl"),
            "--project-root", str(tmp_path), "--no-persist", *args,
        ])
        hb.main()
        captured["output"] = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        return captured

    return launch


@pytest.mark.parametrize("confirmed", [MISSING, False, "true", 1, True])
def test_launch_reports_estimate_period_and_loud_unconfirmed_start(tmp_path, launch_offline, confirmed):
    overrides = {"spent_before_tracking_usd": 7.25}
    if confirmed is not MISSING:
        overrides["period_start_confirmed"] = confirmed
    path = write_config(tmp_path, **overrides)
    write_log(tmp_path / "community/fable/session.jsonl", [cycle(cost=5.25)])
    result = launch_offline("--credit-pool", str(path), "--daily-budget-usd", "25")
    notes = [r["note"] for r in result["output"] if r.get("heartbeat") == "launch"]
    assert len(notes) == 1
    note = notes[0]
    assert "$187.50 of $200.00 remaining by the house's estimate" in note
    assert "period 2026-10-01 to 2026-10-31" in note
    assert note.startswith("!!! ") is (confirmed is not True)
    assert ("(period_start unconfirmed)" in note) is (confirmed is not True)


@pytest.mark.parametrize("text", ["{bad", "[]", json.dumps(CONFIG | {"credit_usd": True}),
                                  json.dumps(CONFIG | {"credit_usd": float("nan")})],
                         ids=["syntax", "array", "boolean", "nan-credit"])
def test_malformed_pool_refuses_main_before_loop_or_balance_output(tmp_path, launch_offline, capsys, text):
    path = tmp_path / "bad-pool.json"
    path.write_text(text)
    with pytest.raises(SystemExit, match="credit pool:"):
        launch_offline("--credit-pool", str(path))
    assert "remaining" not in capsys.readouterr().out


def test_main_without_flag_ignores_default_home_pool_file(tmp_path, launch_offline):
    path = Path.home() / ".config/hamutay/anthropic-pool.json"
    path.parent.mkdir(parents=True)
    path.write_text("malformed default config must never be consulted")
    result = launch_offline()
    assert not any("credit pool" in r.get("note", "").lower() for r in result["output"])
    assert result["loop"]._run_pending is run_pending_events


@pytest.mark.parametrize("budget_args,suffix", [
    (["--daily-budget-usd", "25"], " Today's ceiling: $25.00."),
    (["--no-daily-budget"], " There is no daily ceiling."),
])
def test_main_wires_actual_daily_ceiling_into_the_wake(tmp_path, launch_offline, budget_args, suffix):
    # A wide period keeps this CLI test independent of the wall clock.
    path = write_config(tmp_path, period_start="2000-01-01", period_end="2099-12-31")
    result = launch_offline("--credit-pool", str(path), *budget_args)
    session, backend = resident(tmp_path)
    store = EventStore(tmp_path / "community/launch/session.jsonl.events.jsonl")
    store.append(build_inbound_event(purpose="show the ceiling", sender="validation"))
    assert result["loop"]._run_pending(session, store, limit=1)["ran"] == 1
    assert backend.envelopes[0]["operational_notes"] == [
        "Credit pool: $200.00 of $200.00 remaining (estimated from tokens; "
        "Anthropic's bill is authoritative). It expires 2099-12-31; unused "
        "credit does not carry over." + suffix
    ]


def test_metered_direct_day_still_trips_existing_25_dollar_fuse(tmp_path):
    log = write_log(tmp_path / "session.jsonl", [cycle(cost=12.5), cycle(cost=12.5)])
    store = EventStore(tmp_path / "events.jsonl")
    store.append(build_inbound_event(purpose="wait for tomorrow", sender="validation"))
    session, backend = resident(tmp_path)
    args = hb.build_parser().parse_args(["--log-path", str(log), "--daily-budget-usd", "25"])
    budget, _ = hb.resolve_budget(args)
    loop = hb.HeartbeatLoop(session, store, ledger=hb.DailyLedger(str(log)), budget=budget,
                            now=lambda: NOW, sleep=lambda _: None)
    assert loop.step()["state"] == "resting"
    assert backend.envelopes == []
    assert store.next_pending(now=NOW) is not None
