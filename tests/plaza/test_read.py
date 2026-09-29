from datetime import datetime, timedelta, timezone

import pytest

from hamutay.plaza.read import read_rows
from hamutay.plaza.send import send

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def test_read_rows_is_inclusive_on_both_bounds_and_empty_is_empty(house_guests):
    root, cfg, binding = house_guests
    assert read_rows(cfg) == []                                   # no file yet: empty, not a refusal
    for i in range(3):
        send(cfg, actor="guest:levadura", via="cli", to="elder", text=f"m{i}", now=T0 + timedelta(minutes=i), key=f"k{i}")
    send(cfg, actor="guest:levadura", via="mcp", to="plaza", text="post", now=T0, key="p")
    rows = read_rows(cfg)
    assert [r["seq"] for r in rows] == [1, 3, 5, 7]              # deliveries are not rows
    assert rows[0]["truth"]["state"] == "landed" and rows[3]["truth"] == {"state": "post"}
    assert [r["seq"] for r in read_rows(cfg, since_seq=3, through_seq=5)] == [3, 5]
    assert [r["seq"] for r in read_rows(cfg, since_seq=8)] == []
    assert [r["seq"] for r in read_rows(cfg, posts_only=True)] == [7]
    assert [r["seq"] for r in read_rows(cfg, for_door="elder")] == [7]     # elder's own mail excluded
    assert [r["seq"] for r in read_rows(cfg, door="elder")] == [1, 3, 5]
    last = rows[-1]["seq"]
    assert read_rows(cfg, since_seq=last + 1) == []              # resume at last plus one


def test_read_rows_reports_a_malformed_plaza(house_guests):
    from hamutay.assembly.ledger import LedgerMalformed
    root, cfg, binding = house_guests
    send(cfg, actor="tony", via="cli", to="elder", text="x", now=T0)
    with cfg.plaza.open("a") as f:
        f.write('{"record_type": "note", "seq": 3}\n')
    with pytest.raises(LedgerMalformed):
        read_rows(cfg)
