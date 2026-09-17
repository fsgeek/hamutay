import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hamutay.events import EventStore, run_pending_events
from hamutay.heartbeat import HeartbeatLoop, _run_pending_for, build_constitution, source_note
from hamutay.plaza.pass_ import PlazaMemo
from hamutay.tools.schemas import ASSEMBLY_CONSTITUTION_CLAUSE, PLAZA_CONSTITUTION_CLAUSE

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


class _Stub:
    def exchange(self, *a, **k):
        return "ok"


def test_source_note_reports_commit_and_cleanliness(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false",
                    "commit", "-q", "--allow-empty", "-m", "x"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    assert source_note(tmp_path) == f"source: commit {sha} clean"
    (tmp_path / "f").write_text("x")
    assert source_note(tmp_path) == f"source: commit {sha} dirty"
    assert source_note(tmp_path / "nope") == "source: unknown"


def test_constitution_gains_the_plaza_clause_only_when_asked():
    base = build_constitution(None, assembly=True)
    assert PLAZA_CONSTITUTION_CLAUSE not in base
    with_it = build_constitution(None, assembly=True, plaza=True)
    assert with_it.count(PLAZA_CONSTITUTION_CLAUSE) == 1
    assert with_it.index(ASSEMBLY_CONSTITUTION_CLAUSE) < with_it.index(PLAZA_CONSTITUTION_CLAUSE)
    assert build_constitution(None, plaza=True) == build_constitution(None)   # no assembly, no plaza clause


def test_step_runs_the_plaza_pass_after_the_assembly_pass_and_never_dies(house, capsys):
    root, cfg, binding = house
    order = []
    def fake_assembly(binding, *, now, actor, memo=None, open_store=None):
        order.append("assembly"); from hamutay.assembly.pass_ import PassMemo
        return {"skipped": True, "outbox": 0, "closed": [], "activated": []}, PassMemo((1, 1.0), None)
    def fake_plaza(binding, *, now, memo=None, land=None, clock=None):
        order.append("plaza")
        if len(order) == 2:
            raise RuntimeError("boom")
        return {"skipped": False, "units": 1, "landed": ["m"], "unreadable": []}, PlazaMemo((1, 1.0), 1, 0)
    store = EventStore(cfg.members["qwen"].events)
    loop = HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None, now=lambda: T0,
                         assembly=binding, assembly_pass=fake_assembly, plaza_pass=fake_plaza)
    loop.step(); loop.step()
    assert order == ["assembly", "plaza", "assembly", "plaza"]
    out = capsys.readouterr().out
    assert '"heartbeat": "plaza", "error": "RuntimeError: boom"' in out
    assert '"landed": ["m"]' in out


def test_unbound_or_unplaza_loop_never_calls_the_plaza_pass(house_unplaza):
    root, cfg, binding = house_unplaza
    calls = []
    def fake_plaza(binding, *, now, memo=None, land=None, clock=None):
        calls.append(1); return {"skipped": True, "units": 0, "landed": [], "unreadable": []}, PlazaMemo((0, 0.0), 0, 0)
    store = EventStore(cfg.members["qwen"].events)
    HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None, now=lambda: T0,
                  assembly=binding, plaza_pass=fake_plaza).step()
    HeartbeatLoop(_Stub(), store, poll_interval=1.0, sleep=lambda s: None, now=lambda: T0,
                  assembly=None, plaza_pass=fake_plaza).step()
    assert calls == []


def test_run_pending_for_wires_extra_notes_only_when_plaza_is_set(house, house_unplaza):
    root, cfg, binding = house
    store = EventStore(cfg.members["qwen"].events)
    on_error = lambda s: None

    assert _run_pending_for(None, store, on_error) is run_pending_events

    root_u, cfg_u, binding_u = house_unplaza
    store_u = EventStore(cfg_u.members["qwen"].events)
    assert _run_pending_for(binding_u, store_u, on_error) is run_pending_events

    wired = _run_pending_for(binding, store, on_error)
    assert wired is not run_pending_events
    import functools
    assert isinstance(wired, functools.partial)
    assert wired.func is run_pending_events
    assert "extra_notes" in wired.keywords
