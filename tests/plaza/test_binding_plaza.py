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
