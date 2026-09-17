import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hamutay.assembly.ledger import Ledger, LedgerMalformed, LedgerUnavailable, iso
from hamutay.events import EventStore, StoreUnavailable
from hamutay.plaza.ids import resident_key
from hamutay.plaza.records import SEND_CAP, reduce, validate_plaza
from hamutay.plaza.send import SendRefused, send

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
EV = "11111111-1111-4111-8111-111111111111"


def _wake(event_id=EV, started=T0):
    return {"cycle": 3, "record_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "event_id": event_id,
            "run_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "started_at": iso(started)}


def _tool_send(cfg, **kw):
    args = dict(actor="door:qwen", via="tool", to="elder", text="hello", now=T0, wake=_wake())
    args.update(kw)
    return send(cfg, **args)


def test_plaza_first_then_delivery_landed_in_the_recorded_path(house):
    root, cfg, binding = house
    r = _tool_send(cfg)
    assert r["sent"] and r["delivery"] == "landed" and r["seq"] == 1 and r["to"] == "door:elder"
    led = Ledger(cfg.plaza); recs = led.read()
    validate_plaza(recs, led.line_numbers)
    m, d = recs
    assert m["from"] == "door:qwen" and m["via"] == "tool" and m["sent_at"] == iso(T0)
    assert m["delivery"]["events_path"] == str(cfg.members["elder"].events)
    assert m["delivery"]["members_digest"] == cfg.digest
    assert m["idempotency_key"] == resident_key(EV, "door:elder", "hello")
    assert d["state"] == "landed"
    store = EventStore(cfg.members["elder"].events).read_records()
    assert len(store) == 1 and store[0]["event_id"] == m["delivery"]["event_id"] and store[0]["origin"] == "member"


def test_post_writes_the_plaza_only(house):
    root, cfg, binding = house
    r = _tool_send(cfg, to="plaza", text="a post")
    assert r["delivery"] == "post"
    assert len(Ledger(cfg.plaza).read()) == 1
    for d in cfg.members.values():
        assert not d.events.exists()


def test_same_key_is_a_duplicate_success_with_no_write(house):
    root, cfg, binding = house
    a = _tool_send(cfg)
    b = _tool_send(cfg, wake=_wake(started=T0 + timedelta(hours=1)))     # re-pended wake, new run, same event
    assert b["sent"] and b["duplicate_of_seq"] == a["seq"] and b["message_id"] == a["message_id"]
    assert len(Ledger(cfg.plaza).read()) == 2
    assert len(EventStore(cfg.members["elder"].events).read_records()) == 1


def test_refusals_write_nothing(house):
    root, cfg, binding = house
    for kw in (dict(to="nobody"), dict(to="qwen"), dict(text=""), dict(text="x" * 8001), dict(to="Tony")):
        with pytest.raises(SendRefused):
            _tool_send(cfg, **kw)
    assert not cfg.plaza.exists()


def test_cap_counts_directed_tool_sends_per_utc_day_after_the_key_lookup(house):
    root, cfg, binding = house
    for i in range(SEND_CAP):
        _tool_send(cfg, text=f"m{i}", wake=_wake(event_id=f"{i:08d}-1111-4111-8111-111111111111"))
    with pytest.raises(SendRefused) as e:
        _tool_send(cfg, text="one more", wake=_wake(event_id="ffffffff-1111-4111-8111-111111111111"))
    assert "2026-09-21T00:00:00+00:00" in str(e.value)
    # a retry of the 48th is a duplicate success, not a refusal
    r = _tool_send(cfg, text=f"m{SEND_CAP - 1}", wake=_wake(event_id=f"{SEND_CAP - 1:08d}-1111-4111-8111-111111111111"))
    assert r["duplicate_of_seq"]
    # posts are not counted; the next UTC day is fresh; dates are taken in UTC
    _tool_send(cfg, to="plaza", text="still allowed")
    late = datetime(2026, 9, 20, 23, 30, tzinfo=timezone(timedelta(hours=-1)))   # 00:30Z on the 21st
    r = _tool_send(cfg, text="new day", now=late, wake=_wake(event_id="eeeeeeee-1111-4111-8111-111111111111"))
    assert r["delivery"] == "landed"


def test_store_unavailable_leaves_the_message_pending(house):
    root, cfg, binding = house
    def broken(path, event, *, timeout_s=2.0):
        raise StoreUnavailable("busy")
    r = _tool_send(cfg, land=broken)
    assert r["delivery"] == "pending"
    v = reduce(Ledger(cfg.plaza).read())
    assert v.delivery_truth(r["message_id"]) == {"state": "store_unreadable", "event_id": v.by_id[r["message_id"]]["delivery"]["event_id"],
                                                 "landed_at": None, "detail": {"error": "busy"}}


def test_recipient_quiet_is_reported_as_the_last_declaration(house):
    root, cfg, binding = house
    r = _tool_send(cfg, quiet=lambda path: "2026-09-25T00:00:00+00:00")
    assert r["recipient_last_declared_quiet_until"] == "2026-09-25T00:00:00+00:00"
    r2 = _tool_send(cfg, text="again", wake=_wake(event_id="22222222-1111-4111-8111-111111111111"), quiet=lambda path: None)
    assert "recipient_last_declared_quiet_until" not in r2


def test_human_send_via_cli(house):
    root, cfg, binding = house
    r = send(cfg, actor="tony", via="cli", to="qwen", text="hi", now=T0, key="announce-1")
    assert r["delivery"] == "landed"
    m = Ledger(cfg.plaza).read()[0]
    assert m["wake"] is None and m["via"] == "cli" and m["from"] == "tony"
    r2 = send(cfg, actor="tony", via="cli", to="qwen", text="hi", now=T0, key="announce-1")
    assert r2["duplicate_of_seq"] == 1
    for i in range(SEND_CAP + 1):                                   # the cap does not apply to humans
        send(cfg, actor="custodian", via="cli", to="elder", text=f"n{i}", now=T0)


def test_malformed_plaza_refuses_every_send(house):
    root, cfg, binding = house
    _tool_send(cfg)
    with cfg.plaza.open("a") as f:
        f.write(json.dumps({"record_type": "note", "seq": 3}) + "\n")
    with pytest.raises(LedgerMalformed):
        _tool_send(cfg, text="two", wake=_wake(event_id="22222222-1111-4111-8111-111111111111"))


def test_two_senders_at_once_both_land_exactly_once(house):
    root, cfg, binding = house
    errors = []
    def go(actor, to, ev):
        try:
            send(cfg, actor=actor, via="tool", to=to, text="race", now=T0, wake=_wake(event_id=ev))
        except LedgerUnavailable as e:
            errors.append(e)
    ts = [threading.Thread(target=go, args=("door:qwen", "elder", "aaaaaaa1-1111-4111-8111-111111111111")),
          threading.Thread(target=go, args=("door:elder", "qwen", "aaaaaaa2-1111-4111-8111-111111111111"))]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not errors
    led = Ledger(cfg.plaza); recs = led.read(); validate_plaza(recs, led.line_numbers)
    assert [r["record_type"] for r in recs] == ["message", "delivery", "message", "delivery"]
    assert len(EventStore(cfg.members["elder"].events).read_records()) == 1
    assert len(EventStore(cfg.members["qwen"].events).read_records()) == 1
