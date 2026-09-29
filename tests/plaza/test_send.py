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


def test_send_and_the_validator_agree_that_whitespace_only_text_is_empty(house):
    """M3: send.py refused `not text.strip()` while validate_plaza accepted it
    (falsy only). The divergence was in the safe direction, but the two must agree
    -- the validator is what every reader trusts about what a writer could produce."""
    root, cfg, binding = house
    with pytest.raises(SendRefused):
        send(cfg, actor="door:qwen", via="tool", to="elder", text="   \n\t ", now=T0,
             wake=_wake("11111111-1111-4111-8111-111111111111"))

    from hamutay.assembly.ledger import LedgerMalformed
    from hamutay.plaza.records import build_message, validate_plaza
    from hamutay.plaza.ids import resident_key
    ev = "22222222-1111-4111-8111-111111111111"
    msg = build_message(actor="door:qwen", via="tool", to="plaza", text="  \t ",
                        sent_at=iso(T0), idempotency_key=resident_key(ev, "plaza", "  \t "),
                        delivery=None, wake=_wake(ev))
    with pytest.raises(LedgerMalformed):
        validate_plaza([{**msg, "seq": 1, "created_at": iso(T0)}], [1])


from hamutay.plaza.ids import guest_key


def _guest_send(cfg, **kw):
    args = dict(actor="guest:levadura", via="cli", to="elder", text="hello from outside", now=T0)
    args.update(kw)
    return send(cfg, **args)


def test_guest_is_refused_when_the_key_is_absent_or_the_label_is_not_listed(house):
    root, cfg, binding = house                                   # plaza on, no guests key
    with pytest.raises(SendRefused, match="not admitted"):
        _guest_send(cfg)
    from .conftest import write_members
    from hamutay.assembly.binding import load_members
    write_members(root, plaza=True, guests=["yupi"])
    with pytest.raises(SendRefused, match="not admitted"):
        _guest_send(load_members(root))
    assert not cfg.plaza.exists()                               # nothing was written


def test_guest_send_lands_on_cli_and_on_mcp_with_null_wake(house_guests):
    root, cfg, binding = house_guests
    a = _guest_send(cfg, key="t1")
    b = _guest_send(cfg, via="mcp", to="plaza", text="a post", key="t2")
    assert a["delivery"] == "landed" and b["delivery"] == "post"
    recs = Ledger(cfg.plaza).read()
    assert recs[0]["from"] == "guest:levadura" and recs[0]["via"] == "cli" and recs[0]["wake"] is None
    assert recs[0]["idempotency_key"] == guest_key("levadura", "t1")
    assert recs[0]["delivery"]["members_digest"] == cfg.digest
    assert recs[2]["via"] == "mcp" and recs[2]["delivery"] is None
    store = EventStore(cfg.members["elder"].events).read_records()
    assert store[0]["sender"] == "guest:levadura" and store[0]["origin"] == "member"


def test_guest_token_retry_is_one_message_across_transports_and_a_conflict_is_refused(house_guests):
    root, cfg, binding = house_guests
    a = _guest_send(cfg, key="t1")
    b = _guest_send(cfg, via="mcp", key="t1")                      # same token, other transport (a restarted server)
    c = _guest_send(cfg, key="t1", to="door:elder")                 # same token, recipient spelled canonically
    assert b["duplicate_of_seq"] == a["seq"] == c["duplicate_of_seq"]
    with pytest.raises(SendRefused, match="token reused for different content"):
        _guest_send(cfg, key="t1", text="different words")
    with pytest.raises(SendRefused, match="token reused for different content"):
        _guest_send(cfg, key="t1", to="fable")
    assert len([r for r in Ledger(cfg.plaza).read() if r["record_type"] == "message"]) == 1


def test_guest_without_a_token_sends_a_new_message_each_time(house_guests):
    root, cfg, binding = house_guests
    a = _guest_send(cfg); b = _guest_send(cfg)
    assert a["seq"] != b["seq"] and "duplicate_of_seq" not in b


def test_guest_cap_is_per_label_across_transports_and_posts_are_free(house_guests):
    root, cfg, binding = house_guests
    for i in range(SEND_CAP):
        via = "cli" if i % 2 else "mcp"
        _guest_send(cfg, via=via, key=f"k{i}", now=T0 + timedelta(minutes=i))
    with pytest.raises(SendRefused, match=f"send cap of {SEND_CAP}"):
        _guest_send(cfg, key="one-more", now=T0 + timedelta(hours=1))
    _guest_send(cfg, to="plaza", text="still free", key="post", now=T0 + timedelta(hours=1))     # posts uncapped
    r = _guest_send(cfg, key="k3", now=T0 + timedelta(hours=1))                                   # a retry is not a 49th
    assert "duplicate_of_seq" in r
    _guest_send(cfg, key="tomorrow", now=T0 + timedelta(days=1))                                  # UTC rollover


def test_two_guest_labels_have_separate_counts_and_keys(tmp_path):
    from .conftest import write_members
    from hamutay.assembly.binding import load_members
    write_members(tmp_path, plaza=True, guests=["levadura", "yupi"])
    cfg = load_members(tmp_path)
    a = send(cfg, actor="guest:levadura", via="cli", to="elder", text="same", now=T0, key="first")
    b = send(cfg, actor="guest:yupi", via="cli", to="elder", text="same", now=T0, key="first")
    assert a["seq"] != b["seq"]
    from hamutay.plaza.records import reduce
    v = reduce(Ledger(cfg.plaza).read())
    assert v.sent_today("guest:levadura", T0.date()) == 1 and v.sent_today("guest:yupi", T0.date()) == 1


def test_humans_remain_exempt_from_the_cap(house):
    root, cfg, binding = house
    for i in range(SEND_CAP + 1):
        send(cfg, actor="tony", via="cli", to="elder", text=f"m{i}", now=T0 + timedelta(minutes=i))


def test_guest_retry_after_removal_is_refused_and_earlier_records_stay_valid(house_guests):
    root, cfg, binding = house_guests
    _guest_send(cfg, key="t1")
    from .conftest import write_members
    from hamutay.assembly.binding import load_members
    write_members(root, plaza=True, guests=[])
    cfg2 = load_members(root)
    with pytest.raises(SendRefused, match="not admitted"):
        _guest_send(cfg2, key="t1")
    led = Ledger(cfg2.plaza); recs = led.read()
    validate_plaza(recs, led.line_numbers)                          # the old guest line is still valid
    send(cfg2, actor="tony", via="cli", to="elder", text="after", now=T0)   # and the plaza still writes
