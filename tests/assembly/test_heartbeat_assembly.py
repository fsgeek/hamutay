import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.convene import convene
from hamutay.assembly.ledger import Ledger
from hamutay.assembly.pass_ import PassMemo
from hamutay.events import EventStore, build_inbound_event, format_event_report, summarize_event_log
from hamutay.heartbeat import HeartbeatLoop, build_constitution
from hamutay.tools.schemas import ASSEMBLY_CONSTITUTION_CLAUSE

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _house(tmp_path):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    members = {d: {"session": f"community/{d}/session.jsonl", "events": f"community/{d}/session.jsonl.events.jsonl"}
               for d in ("qwen", "elder")}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    for d in ("qwen", "elder"):
        (tmp_path / "community" / d).mkdir()
    cfg = load_members(tmp_path)
    b, _ = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    return cfg, b


def test_constitution_gains_the_clause_only_when_bound():
    base = build_constitution(None)
    assert ASSEMBLY_CONSTITUTION_CLAUSE not in base
    with_it = build_constitution(None, assembly=True)
    assert ASSEMBLY_CONSTITUTION_CLAUSE in with_it and with_it.endswith(base[-40:])


class _Stub:
    def exchange(self, *a, **k):
        return "ok"


def test_step_runs_the_pass_first_and_keeps_the_memo(tmp_path):
    cfg, b = _house(tmp_path)
    calls = []

    def fake_pass(binding, *, now, actor, memo=None, open_store=None):
        calls.append((actor, memo))
        return {"skipped": False, "outbox": 1, "closed": [], "activated": []}, PassMemo((1, 1.0), None)

    store = EventStore(cfg.members["qwen"].events)
    loop = HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None,
                         run_pending=lambda s, st, **kw: {"results": []},
                         summarize=lambda records, now=None: {"pending_runnable_count": 0, "pending_waiting_count": 0},
                         assembly=b, assembly_pass=fake_pass)
    loop.step(); loop.step()
    assert calls[0][0] == "heartbeat:qwen" and calls[0][1] is None and calls[1][1] == PassMemo((1, 1.0), None)


def test_step_survives_a_pass_error(tmp_path):
    cfg, b = _house(tmp_path)

    def bad_pass(binding, *, now, actor, memo=None, open_store=None):
        return {"skipped": False, "error": "ledger malformed", "outbox": 0, "closed": [], "activated": []}, memo

    store = EventStore(cfg.members["qwen"].events)
    loop = HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None,
                         run_pending=lambda s, st, **kw: {"results": []},
                         summarize=lambda records, now=None: {"pending_runnable_count": 0, "pending_waiting_count": 0},
                         assembly=b, assembly_pass=bad_pass)
    assert loop.step()["state"] == "quiet"


def test_unbound_loop_never_calls_the_pass(tmp_path):
    store = EventStore(tmp_path / "e.jsonl")
    called = []
    loop = HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None,
                         run_pending=lambda s, st, **kw: {"results": []},
                         summarize=lambda records, now=None: {"pending_runnable_count": 0, "pending_waiting_count": 0},
                         assembly_pass=lambda *a, **k: called.append(1))
    loop.step()
    assert not called


def test_report_shows_open_questions_and_my_position(tmp_path):
    from hamutay.assembly.records import reduce
    cfg, b = _house(tmp_path)
    led = Ledger(cfg.ledger)
    q = convene(led, cfg, convener="tony", text="t", closes_in=timedelta(days=2), now=T0,
                proposal_procedure={"rule": "consent-v0"}, artifact={})
    store = EventStore(cfg.members["qwen"].events)
    store.append(build_inbound_event(purpose="x", sender="tony"))
    s = summarize_event_log(store.read_records(), now=T0, assembly_view=reduce(led.read()), door="qwen")
    assert s["assembly"]["observational"] is True
    assert s["assembly"]["open_questions"][0]["question_id"] == q["question_id"]
    assert s["assembly"]["open_questions"][0]["my_position"] is None
    text = format_event_report(s)
    assert "assembly (observational): 1 open" in text and q["question_id"] in text


def test_main_binds_and_prints_the_note(tmp_path, monkeypatch, capsys):
    """Boot-level: bind() is called with the open snapshots and the note is emitted."""
    import hamutay.heartbeat as hb
    cfg, b = _house(tmp_path)
    seen = {}
    def fake_bind(project_root, log_path, event_store_path, *, open_snapshots=None):
        seen["snaps"] = open_snapshots
        return None, "assembly: test note"
    monkeypatch.setattr(hb, "bind", fake_bind)
    note = hb.resolve_assembly_binding(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert note[0] is None and note[1] == "assembly: test note" and seen["snaps"] == []


def test_step_survives_a_raising_pass(tmp_path):
    """A pass that raises (not just returns an error dict) must not kill step().

    run_pass itself only catches LedgerMalformed/LedgerUnavailable; any other
    exception has to be caught in _assembly_step, or a bug in the pass (or in
    a test double standing in for it) would take the whole daemon down.
    """
    cfg, b = _house(tmp_path)
    calls = []

    def raising_pass(binding, *, now, actor, memo=None, open_store=None):
        calls.append(1)
        raise RuntimeError("boom")

    store = EventStore(cfg.members["qwen"].events)
    loop = HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None,
                         run_pending=lambda s, st, **kw: {"results": []},
                         summarize=lambda records, now=None: {"pending_runnable_count": 0, "pending_waiting_count": 0},
                         assembly=b, assembly_pass=raising_pass)
    assert loop.step()["state"] == "quiet"
    # The loop is not disabled by one failure: the next step calls the pass again.
    assert loop.step()["state"] == "quiet"
    assert calls == [1, 1]


def test_summarize_for_falls_back_when_the_assembly_block_fails(tmp_path):
    """A summarize callback must never let a broken assembly ledger kill the report."""
    from hamutay.heartbeat import _summarize_for

    cfg, b = _house(tmp_path)
    # Corrupt the ledger after binding: a malformed line raises LedgerMalformed
    # when read, which _assembly_view swallows (returns None), and
    # summarize_event_log with assembly_view=None produces no "assembly" key.
    Path(cfg.ledger).write_text("garbage\n")

    summarize = _summarize_for(b)
    result = summarize([], now=T0)
    assert "assembly" not in result
    assert result["pending_runnable_count"] == 0
