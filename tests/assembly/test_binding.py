import json
from pathlib import Path

import pytest

from hamutay.assembly.binding import MembersMalformed, bind, load_members


def _write_members(root: Path, members: dict) -> Path:
    plaza = root / "community" / "plaza"
    plaza.mkdir(parents=True, exist_ok=True)
    p = plaza / "members.json"
    p.write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    return p


FOUR = {
    "heartbeat": {"session": "community/heartbeat/session.jsonl",
                  "events": "community/heartbeat/session.jsonl.events.jsonl"},
    "qwen": {"session": "community/qwen/session.jsonl",
             "events": "community/qwen/session.jsonl.events.jsonl"},
}


def test_load_members_resolves_absolute_paths(tmp_path):
    _write_members(tmp_path, FOUR)
    cfg = load_members(tmp_path)
    assert cfg.ledger == (tmp_path / "community/plaza/assembly.jsonl").resolve()
    assert cfg.members["qwen"].events == (tmp_path / "community/qwen/session.jsonl.events.jsonl").resolve()


def test_load_members_absent_is_none(tmp_path):
    assert load_members(tmp_path) is None


@pytest.mark.parametrize("bad", ['{"ledger": 1}', "{", '{"ledger": "x", "members": {"a": {"session": "../out", "events": "b"}}}'])
def test_load_members_malformed_raises(tmp_path, bad):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    (plaza / "members.json").write_text(bad)
    with pytest.raises(MembersMalformed):
        load_members(tmp_path)


def test_bind_matches_log_path_and_live_store(tmp_path):
    _write_members(tmp_path, FOUR)
    b, note = bind(tmp_path, tmp_path / "community/qwen/session.jsonl",
                   tmp_path / "community/qwen/session.jsonl.events.jsonl")
    assert b is not None and b.door == "qwen" and "assembly: member qwen" in note
    assert b.ledger.path == (tmp_path / "community/plaza/assembly.jsonl").resolve()


def test_bind_refuses_store_path_mismatch(tmp_path):
    _write_members(tmp_path, FOUR)
    b, note = bind(tmp_path, tmp_path / "community/qwen/session.jsonl",
                   tmp_path / "elsewhere/events.jsonl")
    assert b is None and "store path" in note


def test_bind_non_member_and_missing_file(tmp_path):
    b, note = bind(tmp_path, tmp_path / "community/x/session.jsonl", tmp_path / "x.events")
    assert b is None and "no members.json" in note
    _write_members(tmp_path, FOUR)
    b, note = bind(tmp_path, tmp_path / "community/x/session.jsonl", tmp_path / "x.events")
    assert b is None and "not a member" in note


def test_bind_malformed_is_fail_closed_with_a_note(tmp_path):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    (plaza / "members.json").write_text("{")
    b, note = bind(tmp_path, tmp_path / "community/qwen/session.jsonl", tmp_path / "e")
    assert b is None and "malformed" in note


def test_bind_refuses_when_an_open_question_snapshot_differs(tmp_path):
    _write_members(tmp_path, FOUR)
    snap = {"qwen": {"session": str((tmp_path / "community/qwen/session.jsonl").resolve()),
                     "events": str((tmp_path / "OLD/events.jsonl").resolve())}}
    b, note = bind(tmp_path, tmp_path / "community/qwen/session.jsonl",
                   tmp_path / "community/qwen/session.jsonl.events.jsonl",
                   open_snapshots=[snap])
    assert b is None and "frozen" in note
