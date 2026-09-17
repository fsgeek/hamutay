import json
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from hamutay.assembly.binding import bind, load_members
from hamutay.assembly.ledger import Ledger
from hamutay.events import EventStore, StoreUnavailable, build_quiet_declaration
from hamutay.plaza.event import inbound_event_for
from hamutay.plaza.pass_ import run_plaza_pass
from hamutay.plaza.records import SEND_CAP, reduce, validate_plaza
from hamutay.plaza.send import SendRefused, send
from tests.plaza_validation.conftest import T0, tool_send, wake


def test_invariant_1_identity_is_from_the_binding_not_spoofable_tool_input(house):
    from hamutay.events import WakeContext
    from hamutay.tools import ToolExecutor

    root, cfg, binding = house
    context = WakeContext(
        event_id="11111111-1111-4111-8111-111111111111",
        run_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        started_at=T0.isoformat(),
        event={},
    )
    executor = ToolExecutor(
        project_root=root,
        cycle=7,
        scheduled_by_record_id=uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        wake_context=context,
        assembly=binding,
    )
    result = executor.execute(
        "send_message",
        {"to": "elder", "text": "bound identity", "from": "door:fable", "actor": "tony"},
    )
    assert result["sent"] is True
    message = Ledger(cfg.plaza).read()[0]
    assert message["from"] == "door:qwen"
    assert message["delivery"]["events_path"] == str(cfg.members["elder"].events)


def test_invariants_1_and_3_cli_identity_via_and_key_are_recorded(house):
    root, cfg, binding = house
    first = send(
        cfg,
        actor="tony",
        via="cli",
        to="elder",
        text="human message",
        now=T0,
        key="independent-validation-key",
    )
    before = cfg.plaza.read_bytes()
    duplicate = send(
        cfg,
        actor="tony",
        via="cli",
        to="elder",
        text="human message",
        now=T0 + timedelta(minutes=1),
        key="independent-validation-key",
    )
    message = Ledger(cfg.plaza).read()[0]
    assert message["from"] == "tony"
    assert message["via"] == "cli"
    assert message["wake"] is None
    assert duplicate["duplicate_of_seq"] == first["seq"]
    assert cfg.plaza.read_bytes() == before


def test_invariant_2_plaza_line_exists_before_recipient_delivery(house):
    root, cfg, binding = house
    observed = []

    def observing_land(path, event, *, timeout_s=2.0):
        ledger = Ledger(cfg.plaza)
        records = ledger.read()
        assert [record["record_type"] for record in records] == ["message"]
        assert records[0]["delivery"]["event_id"] == event["event_id"]
        assert not path.exists()
        observed.append(records[0]["message_id"])
        return EventStore(path).append_if_absent(event, timeout_s=timeout_s)

    result = tool_send(cfg, land=observing_land)
    assert observed == [result["message_id"]]
    assert [row["record_type"] for row in Ledger(cfg.plaza).read()] == ["message", "delivery"]


def test_invariant_3_repeated_framework_key_is_duplicate_and_writes_nothing(house):
    root, cfg, binding = house
    first = tool_send(cfg, text="same words")
    before = cfg.plaza.read_bytes()
    second = send(
        cfg,
        actor="door:qwen",
        via="tool",
        to="door:elder",
        text="same words",
        now=T0 + timedelta(hours=2),
        wake=wake("11111111-1111-4111-8111-111111111111", run="cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
    )
    assert second["duplicate_of_seq"] == first["seq"]
    assert second["message_id"] == first["message_id"]
    assert cfg.plaza.read_bytes() == before
    assert len(EventStore(cfg.members["elder"].events).read_records()) == 1


def test_invariant_4_unreadable_store_keeps_message_and_records_pending(house):
    root, cfg, binding = house

    def unreadable(path, event, *, timeout_s=2.0):
        raise StoreUnavailable("door store cannot be read")

    result = tool_send(cfg, land=unreadable)
    records = Ledger(cfg.plaza).read()
    assert records[0]["message_id"] == result["message_id"]
    assert records[1]["record_type"] == "delivery"
    assert records[1]["state"] == "store_unreadable"
    assert records[1]["detail"] == {"error": "door store cannot be read"}
    assert result["delivery"] == "pending"


def test_invariant_4_repair_uses_recorded_path_once_after_directory_changes(house):
    root, cfg, binding = house

    def unavailable(path, event, *, timeout_s=2.0):
        raise StoreUnavailable("offline")

    pending = tool_send(cfg, land=unavailable)
    old_path = cfg.members["elder"].events
    members_path = root / "community/plaza/members.json"
    raw = json.loads(members_path.read_text())
    raw["members"]["elder"]["events"] = "community/elder/moved.events.jsonl"
    members_path.write_text(json.dumps(raw))
    changed = load_members(root)
    changed_binding, note = bind(root, changed.members["qwen"].session, changed.members["qwen"].events)
    assert changed_binding is not None, note

    message = reduce(Ledger(cfg.plaza).read()).by_id[pending["message_id"]]
    EventStore(old_path).append_if_absent(inbound_event_for(message))
    result, memo = run_plaza_pass(changed_binding, now=T0)

    assert result["landed"] == [pending["message_id"]]
    assert len(EventStore(old_path).read_records()) == 1
    assert not changed.members["elder"].events.exists()
    assert reduce(Ledger(cfg.plaza).read()).delivery_truth(pending["message_id"])["state"] == "landed"


def test_invariant_5_post_wakes_no_store(house):
    root, cfg, binding = house
    result = tool_send(cfg, to="plaza", text="for everyone to read")
    assert result["delivery"] == "post"
    assert [row["record_type"] for row in Ledger(cfg.plaza).read()] == ["message"]
    assert all(not member.events.exists() for member in cfg.members.values())


def test_invariant_6_mail_defers_timed_quiet_never_expires_and_knocks_untimed(house):
    root, cfg, binding = house
    tool_send(cfg)
    event = EventStore(cfg.members["elder"].events).read_records()[0]
    assert event["defer_to_declared_quiet"] is True
    assert "expires_at" not in event

    future_store = EventStore(root / "future.events.jsonl")
    future_store.append(build_quiet_declaration(
        reason="sleeping",
        declared_by_cycle=1,
        declared_by_record_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        until=(T0 + timedelta(hours=1)).isoformat(),
    ))
    future_store.append(dict(event, event_id="22222222-2222-4222-8222-222222222222"))
    assert future_store.claim_next_pending(now=T0) is None
    assert future_store.claim_next_pending(now=T0 + timedelta(hours=2)) is not None

    untimed_store = EventStore(root / "untimed.events.jsonl")
    untimed_store.append(build_quiet_declaration(
        reason="quiet but reachable",
        declared_by_cycle=1,
        declared_by_record_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        until=None,
    ))
    untimed_store.append(dict(event, event_id="33333333-3333-4333-8333-333333333333"))
    assert untimed_store.claim_next_pending(now=T0) is not None


def test_invariant_7_tool_return_follows_plaza_fsync(house, monkeypatch):
    import hamutay.assembly.ledger as ledger_module

    root, cfg, binding = house
    real_fsync = ledger_module.os.fsync
    calls = []

    def recording_fsync(fd):
        calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(ledger_module.os, "fsync", recording_fsync)
    result = tool_send(cfg, to="plaza", text="durable before return")
    assert result["sent"] is True
    assert calls
    assert cfg.plaza.read_text().endswith("\n")


@pytest.mark.parametrize(
    "change",
    [
        {"to": "unknown"},
        {"to": "qwen"},
        {"text": ""},
        {"text": "x" * 8001},
    ],
    ids=["unknown_recipient", "self", "empty_text", "overlong_text"],
)
def test_invariant_8_each_prelock_refusal_writes_nothing(house, change):
    root, cfg, binding = house
    with pytest.raises(SendRefused):
        tool_send(cfg, **change)
    assert not cfg.plaza.exists()


def test_invariant_8_cap_utc_day_refuses_without_write_duplicate_precedes_cap(house):
    root, cfg, binding = house
    calls = []

    def accepted_without_store(path, event, *, timeout_s=2.0):
        calls.append(event["event_id"])
        return True

    last = None
    for index in range(SEND_CAP):
        last = tool_send(
            cfg,
            text=f"message {index}",
            event_id=f"{index:08d}-1111-4111-8111-111111111111",
            land=accepted_without_store,
            quiet=lambda path: None,
        )
    before = cfg.plaza.read_bytes()
    with pytest.raises(SendRefused) as refused:
        tool_send(
            cfg,
            text="forty ninth",
            event_id="ffffffff-1111-4111-8111-111111111111",
            land=accepted_without_store,
        )
    assert "2026-09-21T00:00:00+00:00" in str(refused.value)
    assert cfg.plaza.read_bytes() == before

    post = tool_send(
        cfg,
        to="plaza",
        text="posts remain uncapped",
        event_id="dddddddd-1111-4111-8111-111111111111",
    )
    assert post["delivery"] == "post"
    after_post = cfg.plaza.read_bytes()

    duplicate = tool_send(
        cfg,
        text=f"message {SEND_CAP - 1}",
        event_id=f"{SEND_CAP - 1:08d}-1111-4111-8111-111111111111",
        land=accepted_without_store,
    )
    assert duplicate["duplicate_of_seq"] == last["seq"]
    assert cfg.plaza.read_bytes() == after_post

    human = send(
        cfg,
        actor="custodian",
        via="cli",
        to="elder",
        text="the tool cap does not apply to humans",
        now=T0,
        key="after-resident-cap",
        land=accepted_without_store,
        quiet=lambda path: None,
    )
    assert human["sent"] is True

    next_utc_day = datetime(2026, 9, 20, 23, 30, tzinfo=timezone(timedelta(hours=-1)))
    accepted = tool_send(
        cfg,
        text="new UTC day",
        now=next_utc_day,
        event_id="eeeeeeee-1111-4111-8111-111111111111",
        land=accepted_without_store,
        quiet=lambda path: None,
    )
    assert accepted["sent"] is True
    assert len(calls) == SEND_CAP + 2


def test_invariant_11_two_senders_serialize_once_and_seq_is_physical_line(house):
    root, cfg, binding = house
    barrier = threading.Barrier(2)
    errors = []

    def sender(actor, recipient, event_id):
        try:
            barrier.wait()
            send(
                cfg,
                actor=actor,
                via="tool",
                to=recipient,
                text=f"from {actor}",
                now=T0,
                wake=wake(event_id),
            )
        except Exception as exc:  # asserted empty below; preserves both thread failures
            errors.append(exc)

    threads = [
        threading.Thread(target=sender, args=("door:qwen", "elder", "11111111-1111-4111-8111-111111111111")),
        threading.Thread(target=sender, args=("door:elder", "qwen", "22222222-2222-4222-8222-222222222222")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    ledger = Ledger(cfg.plaza)
    records = ledger.read()
    validate_plaza(records, ledger.line_numbers)
    assert [row["seq"] for row in records] == ledger.line_numbers == [1, 2, 3, 4]
    assert len([row for row in records if row["record_type"] == "message"]) == 2
    assert len(EventStore(cfg.members["qwen"].events).read_records()) == 1
    assert len(EventStore(cfg.members["elder"].events).read_records()) == 1
