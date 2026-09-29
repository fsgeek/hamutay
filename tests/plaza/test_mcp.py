import asyncio
import json
from datetime import datetime, timezone

import pytest

from hamutay.assembly.binding import MembersMalformed
from hamutay.plaza.send import SendRefused
from hamutay.plaza.mcp import build_server, plaza_post_impl, plaza_read_impl, plaza_send_impl

UTC = timezone.utc


def test_server_registers_exactly_three_tools_and_fixes_the_label_at_build(house_guests):
    root, cfg, binding = house_guests
    server = build_server(root, "levadura")
    names = sorted(t.name for t in asyncio.run(server.list_tools()))
    assert names == ["plaza_post", "plaza_read", "plaza_send"]
    desc = {t.name: t.description for t in asyncio.run(server.list_tools())}
    assert "guest:levadura" in desc["plaza_send"] and "48" in desc["plaza_send"] and "token" in desc["plaza_send"].lower()
    assert "inclusive" in desc["plaza_read"]


def test_impls_send_read_and_post_under_the_fixed_label_and_reload_admission_per_call(house_guests):
    root, cfg, binding = house_guests
    r = plaza_send_impl(root, "levadura", "elder", "hello from levadura", key="t1")
    assert r["sent"] and r["delivery"] == "landed"
    again = plaza_send_impl(root, "levadura", "door:elder", "hello from levadura", key="t1")
    assert again["duplicate_of_seq"] == r["seq"]
    p = plaza_post_impl(root, "levadura", "a post", key="p1")
    assert p["delivery"] == "post"
    rows = plaza_read_impl(root, "levadura", since_seq=1)
    assert [x["from"] for x in rows] == ["guest:levadura", "guest:levadura"] and rows[0]["via"] == "mcp"
    assert plaza_read_impl(root, "levadura", since_seq=rows[-1]["seq"] + 1) == []
    # removal between calls: the next write is refused, nothing cached
    from .conftest import write_members
    write_members(root, plaza=True, guests=[])
    refused = plaza_send_impl(root, "levadura", "elder", "again", key="t2")
    assert refused["sent"] is False and "not admitted" in refused["refused"]
    conflict = plaza_send_impl(root, "levadura", "elder", "other words", key="t1")
    assert conflict["sent"] is False


def test_impls_refuse_cleanly_when_the_plaza_is_off(house_unplaza):
    root, cfg, binding = house_unplaza
    r = plaza_send_impl(root, "levadura", "elder", "x")
    assert r["sent"] is False and "not enabled" in r["refused"]
    with pytest.raises(SendRefused):
        plaza_read_impl(root, "levadura")


def test_a_malformed_house_is_not_hidden_from_a_reader(house_guests):
    root, cfg, binding = house_guests
    mp = root / "community/plaza/members.json"
    body = json.loads(mp.read_text()); body["guests"] = "x"; mp.write_text(json.dumps(body))
    with pytest.raises(MembersMalformed):
        plaza_read_impl(root, "levadura")
    r = plaza_send_impl(root, "levadura", "elder", "x")
    assert r["sent"] is False and "MembersMalformed" in r["refused"]
