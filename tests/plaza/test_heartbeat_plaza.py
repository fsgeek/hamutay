import subprocess
from datetime import datetime, timezone
from pathlib import Path

from hamutay.events import EventStore, run_pending_events
from hamutay.heartbeat import HeartbeatLoop, _run_pending_for, build_constitution, guests_flag, source_note
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


def test_constitution_guest_sentence_is_separate_and_only_under_its_flag():
    from hamutay.tools.schemas import GUESTS_CONSTITUTION_SENTENCE
    assert GUESTS_CONSTITUTION_SENTENCE == (
        "Guests — session instances from other projects of the ayllu, named under guests in "
        "community/plaza/members.json — may write to the plaza and to your door under a guest: label; "
        "a guest has no door, so a post is how to answer one. ")
    assert GUESTS_CONSTITUTION_SENTENCE not in PLAZA_CONSTITUTION_CLAUSE
    plain = build_constitution(None, assembly=True, plaza=True)
    assert GUESTS_CONSTITUTION_SENTENCE not in plain
    assert plain == build_constitution(None, assembly=True, plaza=True, guests=False)     # golden: bytes unchanged
    with_guests = build_constitution(None, assembly=True, plaza=True, guests=True)
    assert with_guests == plain.replace(PLAZA_CONSTITUTION_CLAUSE, PLAZA_CONSTITUTION_CLAUSE + GUESTS_CONSTITUTION_SENTENCE, 1)
    assert build_constitution(None, assembly=True, guests=True) == build_constitution(None, assembly=True)   # no plaza, no sentence
    assert build_constitution(None, guests=True) == build_constitution(None)


def test_guests_flag_reads_the_binding(house, house_guests, house_unplaza):
    """guests_flag returns True only when the key is present on a plaza-enabled binding."""
    # house_guests: plaza=True, guests=["levadura"]
    _, _, binding_guests = house_guests
    assert guests_flag(binding_guests) is True

    # house: plaza=True, guests key absent
    _, _, binding_no_guests = house
    assert guests_flag(binding_no_guests) is False

    # house_unplaza: plaza=False, guests key absent
    _, _, binding_unplaza = house_unplaza
    assert guests_flag(binding_unplaza) is False

    # No binding at all
    assert guests_flag(None) is False


def test_build_session_passes_guests_flag_to_the_constitution(tmp_path, monkeypatch):
    """build_session passes the result of guests_flag(assembly_binding) to build_constitution."""
    from hamutay import heartbeat as hb
    from .conftest import write_members
    from hamutay.assembly.binding import bind, load_members

    write_members(tmp_path, plaza=True, guests=["levadura"])
    cfg = load_members(tmp_path)
    real_binding, _ = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)

    guests_flag_calls = []
    build_constitution_kwargs = {}

    original_guests_flag = hb.guests_flag
    original_build_constitution = hb.build_constitution

    def mock_guests_flag(binding):
        guests_flag_calls.append(binding)
        return original_guests_flag(binding)

    def mock_build_constitution(*args, **kwargs):
        build_constitution_kwargs.update(kwargs)
        return original_build_constitution(*args, **kwargs)

    monkeypatch.setattr(hb, "guests_flag", mock_guests_flag)
    monkeypatch.setattr(hb, "build_constitution", mock_build_constitution)
    monkeypatch.setattr(hb, "bind", lambda *a, **k: (real_binding, "mocked"))
    monkeypatch.setattr(hb.HeartbeatLoop, "_emit", lambda *a, **k: None)

    # Build launch args similar to test_heartbeat.py::_launch_args
    from hamutay.heartbeat import build_parser
    argv = [
        "--log-path", str(tmp_path / "session.jsonl"),
        "--provider", "openrouter",
        "--model", "m",
        "--api-key", "test-key",
        "--no-persist",
    ]
    args = build_parser().parse_args(argv)
    args.project_root = str(tmp_path)

    hb.build_session(args)

    assert len(guests_flag_calls) == 1
    assert build_constitution_kwargs.get("guests") is True
