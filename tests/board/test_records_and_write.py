import json
import uuid
from datetime import timedelta

import pytest

from hamutay.assembly.ledger import LedgerMalformed
from hamutay.board.ids import NS_BOARD, board_path, match_event_id
from hamutay.board.write import BoardRefused, add_note, read_entries, read_snapshot, set_status

from .conftest import T0, post


def test_ns_board_is_fixed_and_distinct_from_the_plaza():
    from hamutay.plaza.ids import PLAZA_NS
    assert str(NS_BOARD) == "e095e4d0-cfce-5dc7-86c8-4e7a231df71b"
    assert NS_BOARD != PLAZA_NS
    assert match_event_id("qwen", 3, 2, 1) == str(uuid.uuid5(NS_BOARD, "qwen:3:g2:a1"))


def test_post_writes_a_validated_opening_with_seq_equal_line(house):
    root = house[0]
    r = post(root, 1, tags=["Paper", "ＲＥＶＩＥＷ", "paper"], why="because", owner="custodian")
    assert r["seq"] == 1 and r["tags"] == ["paper", "review"] and r["owner"] == "custodian"
    rec = json.loads(board_path(root).read_text().splitlines()[0])
    assert rec["record_type"] == "opening" and rec["seq"] == 1 and rec["posted_by"] == "tony"
    assert uuid.UUID(rec["opportunity_id"]).version == 4
    assert set(rec) == {"record_type", "seq", "created_at", "opportunity_id", "posted_by", "posted_at", "title",
                        "what", "why", "help_wanted", "kind", "tags", "owner", "record_of_help"}


@pytest.mark.parametrize("kw,msg", [
    ({"title": "x" * 121}, "title"),
    ({"what": "y" * 2001}, "what"),
    ({"why": "z" * 1001}, "why"),
    ({"help_wanted": "z" * 1001}, "help_wanted"),
    ({"record_of_help": "z" * 501}, "record_of_help"),
    ({"kind": "party"}, "kind"),
    ({"tags": ["a b"]}, "tag"),
    ({"tags": [""]}, "blank"),
    ({"tags": [f"t{i}" for i in range(9)]}, "8"),
    ({"owner": "nobody"}, "label"),
    ({"by": "door:qwen x"}, "label"),
])
def test_post_refuses_out_of_bounds(house, kw, msg):
    with pytest.raises(BoardRefused, match=msg):
        post(house[0], 1, **kw)
    assert not board_path(house[0]).exists() or board_path(house[0]).read_text() == ""


def test_five_open_per_poster_and_twenty_per_day(house):
    root = house[0]
    ids = [post(root, i)["opportunity_id"] for i in range(5)]
    with pytest.raises(BoardRefused, match="5 openings"):
        post(root, 5)
    set_status(root, by="tony", opportunity_id=ids[0], status="taken", now=T0)
    post(root, 5)                                  # taken is not open
    for i in range(13):
        add_note(root, by="tony", opportunity_id=ids[1], text=f"n{i}", now=T0)
    # 5 openings + 1 status + 1 opening + 13 notes = 20
    with pytest.raises(BoardRefused, match="daily cap"):
        add_note(root, by="tony", opportunity_id=ids[1], text="one more", now=T0)
    add_note(root, by="tony", opportunity_id=ids[1], text="next day", now=T0 + timedelta(days=1))


def test_notes_and_status_are_owner_only_and_closed_is_final(house):
    root = house[0]
    oid = post(root, 1, owner="custodian")["opportunity_id"]
    with pytest.raises(BoardRefused, match="owner"):
        add_note(root, by="tony", opportunity_id=oid, text="hi", now=T0)
    add_note(root, by="custodian", opportunity_id=oid, text="hi", now=T0)
    set_status(root, by="custodian", opportunity_id=oid, status="closed", reason="done", now=T0)
    with pytest.raises(BoardRefused, match="closed"):
        set_status(root, by="custodian", opportunity_id=oid, status="open", now=T0)
    with pytest.raises(BoardRefused, match="closed"):
        add_note(root, by="custodian", opportunity_id=oid, text="again", now=T0)
    e = read_entries(root, opportunity_id=oid)["entries"][0]
    assert e["status"] == "closed" and e["status_reason"] == "done" and [n["text"] for n in e["notes"]] == ["hi"]


def test_repeats_are_one_record(house):
    root = house[0]
    a = post(root, 1)
    b = post(root, 1)
    assert b["duplicate_of_seq"] == a["seq"] and b["opportunity_id"] == a["opportunity_id"]
    add_note(root, by="tony", opportunity_id=a["opportunity_id"], text="x", now=T0)
    assert add_note(root, by="tony", opportunity_id=a["opportunity_id"], text="x", now=T0)["duplicate_of_seq"] == 2
    assert len(board_path(root).read_text().splitlines()) == 2


def test_guests_must_be_admitted(house):
    root = house[0]
    with pytest.raises(BoardRefused, match="not admitted"):
        post(root, 1, by="guest:levadura")
    assert post(root, 1, by="guest:levadura", admitted_guests=("levadura",))["seq"] == 1


def test_strict_reader_fails_closed_and_writer_refuses(house):
    root = house[0]
    post(root, 1)
    p = board_path(root)
    rec = json.loads(p.read_text())
    rec["kind"] = "party"
    p.write_text(json.dumps(rec) + "\n")
    with pytest.raises(LedgerMalformed):
        read_snapshot(root)
    with pytest.raises(LedgerMalformed):
        post(root, 2)
    assert len(p.read_text().splitlines()) == 1


def test_validator_rejects_a_note_by_a_non_owner_written_by_hand(house):
    root = house[0]
    oid = post(root, 1)["opportunity_id"]
    p = board_path(root)
    p.write_text(p.read_text() + json.dumps({"record_type": "note", "seq": 2, "created_at": T0.isoformat(),
                                             "opportunity_id": oid, "by": "custodian", "text": "x"}) + "\n")
    with pytest.raises(LedgerMalformed, match="owner"):
        read_snapshot(root)
