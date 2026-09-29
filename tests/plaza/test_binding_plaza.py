import hashlib
import json

import pytest

from hamutay.assembly.binding import MembersMalformed, bind, load_members
from .conftest import DOORS, write_members


def test_plaza_key_is_optional_and_outside_the_snapshot(tmp_path):
    p = write_members(tmp_path, plaza=False)
    cfg = load_members(tmp_path)
    assert cfg.plaza is None
    assert cfg.digest == hashlib.sha256(p.read_bytes()).hexdigest()
    snap_before = cfg.snapshot()
    write_members(tmp_path, plaza=True)
    cfg2 = load_members(tmp_path)
    assert cfg2.plaza == (tmp_path / "community/plaza/plaza.jsonl").resolve()
    assert cfg2.snapshot() == snap_before            # the assembly's freeze is untouched
    assert set(cfg2.snapshot()) == set(DOORS)
    # tmp_path carries this test's own name, so the plan's `"plaza" not in …` cannot pass; assert the shape instead.
    assert "community/plaza/plaza.jsonl" not in json.dumps(cfg2.snapshot())


def test_plaza_key_must_be_a_string_inside_the_root(tmp_path):
    p = write_members(tmp_path, plaza=False)
    body = json.loads(p.read_text()); body["plaza"] = "../outside.jsonl"; p.write_text(json.dumps(body))
    with pytest.raises(MembersMalformed):
        load_members(tmp_path)
    body["plaza"] = 3; p.write_text(json.dumps(body))
    with pytest.raises(MembersMalformed):
        load_members(tmp_path)


def test_bind_note_mentions_the_plaza_only_when_set(tmp_path):
    write_members(tmp_path, plaza=False)
    cfg = load_members(tmp_path)
    b, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert b is not None and note == f"assembly: member qwen bound; ledger {cfg.ledger}"
    write_members(tmp_path, plaza=True)
    cfg = load_members(tmp_path)
    b, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert note == (f"assembly: member qwen bound; ledger {cfg.ledger}; "
                    f"plaza: door qwen may send; log {cfg.plaza}")


def test_guests_key_is_optional_distinguishes_absent_from_empty_and_stays_outside_the_snapshot(tmp_path):
    write_members(tmp_path, plaza=True)
    cfg = load_members(tmp_path)
    assert cfg.guests is None
    snap = cfg.snapshot()
    write_members(tmp_path, plaza=True, guests=[])
    assert load_members(tmp_path).guests == ()
    write_members(tmp_path, plaza=True, guests=["levadura", "yupi"])
    cfg3 = load_members(tmp_path)
    assert cfg3.guests == ("levadura", "yupi")
    assert cfg3.snapshot() == snap                       # the assembly's freeze is untouched
    assert '"guests":' not in json.dumps(cfg3.snapshot())  # guests key is not in snapshot JSON


@pytest.mark.parametrize("bad", [
    "levadura",                 # not a list
    ["Levadura"],               # uppercase
    ["1abc"],                   # leading digit
    ["a" * 33],                 # too long
    ["levadura", "levadura"],   # duplicate
    [3],                        # not a string
])
def test_guests_key_malformed_is_refused_by_name(tmp_path, bad):
    p = write_members(tmp_path, plaza=True)
    body = json.loads(p.read_text()); body["guests"] = bad; p.write_text(json.dumps(body))
    with pytest.raises(MembersMalformed, match="guests"):
        load_members(tmp_path)
    b, note = bind(tmp_path, tmp_path / "community/qwen/session.jsonl", tmp_path / "community/qwen/session.jsonl.events.jsonl")
    assert b is None and "malformed" in note


def test_digest_is_of_the_bytes_that_were_parsed(tmp_path, monkeypatch):
    """§11 r6: one captured buffer. A file replaced between two reads must not pair config A with digest B."""
    import hashlib
    from pathlib import Path as _P
    p = write_members(tmp_path, plaza=True, guests=["levadura"])
    first = p.read_bytes()
    calls = {"n": 0}
    real_read_bytes = _P.read_bytes
    def read_bytes_once_then_swap(self):
        calls["n"] += 1
        data = real_read_bytes(self)
        if self == p and calls["n"] == 1:
            # after the first read, someone installs a new file
            body = json.loads(data); body["guests"] = ["yupi"]; p.write_text(json.dumps(body))
        return data
    monkeypatch.setattr(_P, "read_bytes", read_bytes_once_then_swap)
    monkeypatch.setattr(_P, "read_text", lambda self, *a, **k: (_ for _ in ()).throw(AssertionError("read_text must not be used")))
    cfg = load_members(tmp_path)
    assert cfg.guests == ("levadura",)
    assert cfg.digest == hashlib.sha256(first).hexdigest()


def test_bind_note_counts_guests_only_when_the_key_is_present(tmp_path):
    write_members(tmp_path, plaza=True)
    cfg = load_members(tmp_path)
    b, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert note.endswith(f"plaza: door qwen may send; log {cfg.plaza}")
    write_members(tmp_path, plaza=True, guests=["levadura", "yupi"])
    cfg = load_members(tmp_path)
    b, note = bind(tmp_path, cfg.members["qwen"].session, cfg.members["qwen"].events)
    assert note.endswith(f"plaza: door qwen may send; log {cfg.plaza}; guests 2")
