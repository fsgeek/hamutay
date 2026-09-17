import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from hamutay.assembly.ledger import iso
from hamutay.events import (EventStore, LeaseGateRequired, StoreUnavailable, build_event_envelope,
                            build_inbound_event, build_quiet_declaration)
from hamutay.plaza.event import inbound_event_for, purpose_for
from hamutay.plaza.ids import cli_key, resident_key
from hamutay.plaza.records import build_message
from hamutay.plaza.store import land, recipient_quiet_until

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
EV = "11111111-1111-4111-8111-111111111111"


def _msg(tmp_path, actor="door:qwen", via="tool", text="hello elder"):
    wake = None if via == "cli" else {"cycle": 2, "record_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "event_id": EV,
                                      "run_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "started_at": iso(T0)}
    key = resident_key(EV, "door:elder", text) if via == "tool" else cli_key("k")
    m = build_message(actor=actor, via=via, to="door:elder", text=text, sent_at=iso(T0), idempotency_key=key,
                      delivery={"door": "elder", "events_path": str(tmp_path / "elder.events.jsonl"),
                                "event_id": None, "members_digest": "a" * 64}, wake=wake)
    m["seq"] = 7; m["created_at"] = iso(T0)
    return m


def test_build_inbound_event_default_is_byte_identical(monkeypatch):
    import hamutay.events as ev
    monkeypatch.setattr(ev, "uuid4", lambda: "00000000-0000-4000-8000-000000000000")
    monkeypatch.setattr(ev, "utc_now_iso", lambda: "2026-09-20T12:00:00+00:00")
    golden = ('{"record_type": "event_status", "event_id": "00000000-0000-4000-8000-000000000000", '
              '"event_type": "inbound_message", "status": "pending", "created_at": "2026-09-20T12:00:00+00:00", '
              '"origin": "external", "sender": "tony", "purpose": "p"}')
    got = json.dumps(build_inbound_event(purpose="p", sender="tony"))
    assert got == golden, got   # if the golden's key order differs, fix the GOLDEN from a pre-task run, never the code


def test_member_origin_and_envelope_sentence():
    e = build_inbound_event(purpose="p", sender="door:qwen", origin="member")
    assert e["origin"] == "member" and e["sender"] == "door:qwen"
    env = json.loads(build_event_envelope(e, [], "run"))
    assert env["origin"] == "member"
    assert env["instruction"].startswith("This is a message from another resident, carried by the plaza.")
    ext = build_inbound_event(purpose="p", sender="tony")
    env2 = json.loads(build_event_envelope(ext, [], "run"))
    assert env2["instruction"].startswith("This is an external inbound event. Its origin, sender, and purpose")
    hum = build_inbound_event(purpose="p", sender="tony", origin="member")
    env3 = json.loads(build_event_envelope(hum, [], "run"))
    assert env3["instruction"].startswith("This is a message from a human, carried by the plaza.")


def test_inbound_event_for_is_deterministic_and_defers_to_quiet(tmp_path):
    m = _msg(tmp_path)
    e1, e2 = inbound_event_for(m), inbound_event_for(m)
    assert e1 == e2
    assert e1["event_id"] == m["delivery"]["event_id"]
    assert e1["origin"] == "member" and e1["sender"] == "door:qwen" and e1["label"] == f"plaza:{m['message_id']}"
    assert e1["defer_to_declared_quiet"] is True and "expires_at" not in e1
    p = purpose_for(m)
    assert p.startswith("A message from door:qwen, carried by the plaza (message ")
    assert "plaza seq 7" in p and 'send_message(to="qwen"' in p and "read(path, offset=6, limit=1)" in p
    assert p.endswith("\n\nhello elder")
    h = _msg(tmp_path, actor="tony", via="cli")
    assert 'a post (to="plaza") is how to answer' in purpose_for(h)


def test_land_normalises_every_store_failure(tmp_path):
    m = _msg(tmp_path)
    path = Path(m["delivery"]["events_path"])
    assert land(path, inbound_event_for(m)) is True
    assert land(path, inbound_event_for(m)) is False              # already present, by event_id
    (path.parent / "door.json").write_text("{not json")
    with pytest.raises(StoreUnavailable):
        land(path, inbound_event_for(m))                          # LeaseGateRequired → StoreUnavailable
    (path.parent / "door.json").unlink()
    bad = tmp_path / "nodir" / "x.events.jsonl"
    bad.parent.mkdir(); bad.parent.chmod(0o500)
    try:
        with pytest.raises(StoreUnavailable):
            land(bad, inbound_event_for(m))                       # OSError → StoreUnavailable
    finally:
        bad.parent.chmod(0o700)


def test_recipient_quiet_until_reads_only_completed_declarations(tmp_path):
    path = tmp_path / "elder.events.jsonl"
    assert recipient_quiet_until(path) is None
    st = EventStore(path)
    e = build_inbound_event(purpose="p", sender="tony")
    st.append(e); running = st.append_running(e)
    assert recipient_quiet_until(path) is None                    # a wake is running

    result_record_id = uuid4()
    until = iso(T0 + timedelta(hours=1))
    completed = st.append_completed_atomic(
        event=e, run_id=running["run_id"], wake_cycle=1,
        result_record_id=result_record_id, response_text="done",
    )
    assert recipient_quiet_until(path) is None                    # completed, but no declaration yet

    decl = build_quiet_declaration(
        reason="resting", declared_by_cycle=1,
        declared_by_record_id=result_record_id, until=until,
    )
    st.append(decl)
    assert recipient_quiet_until(path) == until                   # completed wake declared a future quiet

    e2 = build_inbound_event(purpose="p2", sender="tony")
    st.append(e2); st.append_running(e2)
    assert recipient_quiet_until(path) is None                    # a later wake is running again
