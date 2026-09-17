import copy
import uuid

import pytest

from hamutay.assembly.ledger import Ledger, LedgerMalformed, iso
from hamutay.plaza.ids import PLAZA_NS, cli_key, delivery_event_id, resident_key
from hamutay.plaza.pass_ import run_plaza_pass
from hamutay.plaza.records import build_delivery, build_message, validate_plaza
from hamutay.plaza.send import send
from tests.plaza_validation.conftest import T0, wake


def _message(*, actor="door:qwen", via="tool", to="door:elder", text="valid text"):
    message_wake = wake("11111111-1111-4111-8111-111111111111") if via == "tool" else None
    key = resident_key(message_wake["event_id"], to, text) if via == "tool" else cli_key("human-key")
    delivery = None if to == "plaza" else {
        "door": to.removeprefix("door:"),
        "events_path": "/tmp/independent-plaza-validation.events.jsonl",
        "event_id": None,
        "members_digest": "a" * 64,
    }
    return build_message(
        actor=actor,
        via=via,
        to=to,
        text=text,
        sent_at=iso(T0),
        idempotency_key=key,
        delivery=delivery,
        wake=message_wake,
    )


def _number(*records):
    return [dict(record, seq=index, created_at=iso(T0)) for index, record in enumerate(records, 1)]


def _valid_pair():
    message = _message()
    delivery = build_delivery(message=message, state="landed", landed_at=iso(T0), detail=None)
    return _number(message, delivery)


def _mutated(case):
    records = copy.deepcopy(_valid_pair())
    message, delivery = records
    lines = [1, 2]
    if case == "unknown_record_type":
        message["record_type"] = "mystery"
    elif case == "missing_field":
        message.pop("text")
    elif case == "extra_field":
        delivery["surprise"] = True
    elif case == "wrong_field_type":
        message["text"] = 4
    elif case == "seq_not_line":
        message["seq"] = 2
    elif case == "physical_blank_line":
        lines = [1, 3]
    elif case == "naive_instant":
        message["sent_at"] = "2026-09-20T12:00:00"
    elif case == "non_uuid":
        message["message_id"] = "not-a-uuid"
    elif case == "message_not_v4":
        message["message_id"] = str(uuid.uuid5(PLAZA_NS, "wrong-version"))
    elif case == "key_not_v5":
        message["idempotency_key"] = str(uuid.uuid4())
    elif case == "event_not_v5":
        message["delivery"]["event_id"] = str(uuid.uuid4())
    elif case == "foreign_delivery_id":
        message["delivery"]["event_id"] = str(uuid.uuid5(PLAZA_NS, "foreign"))
    elif case == "foreign_tool_key":
        message["idempotency_key"] = str(uuid.uuid5(PLAZA_NS, "foreign"))
    elif case == "bad_actor":
        message["from"] = "Door:Qwen"
    elif case == "bad_recipient":
        message["to"] = "Tony"
    elif case == "self_addressed":
        message["to"] = "door:qwen"
    elif case == "tool_without_door_actor":
        message["from"] = "tony"
    elif case == "tool_without_wake":
        message["wake"] = None
    elif case == "cli_with_door_actor":
        message["via"] = "cli"
        message["wake"] = None
    elif case == "cli_with_wake":
        human = _number(_message(actor="tony", via="cli"))[0]
        human["wake"] = wake("11111111-1111-4111-8111-111111111111")
        records, lines = [human], [1]
    elif case == "directed_without_delivery":
        message["delivery"] = None
    elif case == "post_with_delivery":
        post = _number(_message(to="plaza"))[0]
        post["delivery"] = copy.deepcopy(message["delivery"])
        records, lines = [post], [1]
    elif case == "wrong_delivery_door":
        message["delivery"]["door"] = "fable"
    elif case == "relative_events_path":
        message["delivery"]["events_path"] = "community/elder/events.jsonl"
    elif case == "bad_members_digest":
        message["delivery"]["members_digest"] = "A" * 64
    elif case == "delivery_before_message":
        records = [dict(delivery, seq=1), dict(message, seq=2)]
    elif case == "delivery_unknown_message":
        delivery["message_id"] = str(uuid.uuid4())
    elif case == "delivery_wrong_door":
        delivery["door"] = "fable"
    elif case == "delivery_wrong_event":
        delivery["event_id"] = str(uuid.uuid5(PLAZA_NS, "other-event"))
    elif case == "landed_without_time":
        delivery["landed_at"] = None
    elif case == "landed_with_detail":
        delivery["detail"] = {"error": "impossible"}
    elif case == "unreadable_with_time":
        delivery["state"] = "store_unreadable"
        delivery["detail"] = {"error": "busy"}
    elif case == "unreadable_without_error":
        delivery["state"] = "store_unreadable"
        delivery["landed_at"] = None
        delivery["detail"] = {"error": ""}
    elif case == "empty_text":
        message["text"] = ""
    elif case == "overlong_text":
        message["text"] = "x" * 8001
    elif case == "duplicate_key":
        twin = copy.deepcopy(message)
        twin["message_id"] = str(uuid.uuid4())
        twin["delivery"]["event_id"] = delivery_event_id(twin["message_id"], "elder")
        records, lines = _number(message, twin), [1, 2]
    elif case == "duplicate_message_id":
        twin = _message(text="different")
        twin["message_id"] = message["message_id"]
        twin["delivery"]["event_id"] = delivery_event_id(twin["message_id"], "elder")
        records, lines = _number(message, twin), [1, 2]
    else:  # pragma: no cover - a misspelled parametrization should be loud
        raise AssertionError(case)
    return records, lines


@pytest.mark.parametrize(
    "case",
    [
        "unknown_record_type", "missing_field", "extra_field", "wrong_field_type",
        "seq_not_line", "physical_blank_line", "naive_instant", "non_uuid",
        "message_not_v4", "key_not_v5", "event_not_v5", "foreign_delivery_id",
        "foreign_tool_key", "bad_actor", "bad_recipient", "self_addressed",
        "tool_without_door_actor", "tool_without_wake", "cli_with_door_actor",
        "cli_with_wake", "directed_without_delivery", "post_with_delivery",
        "wrong_delivery_door", "relative_events_path", "bad_members_digest",
        "delivery_before_message", "delivery_unknown_message", "delivery_wrong_door",
        "delivery_wrong_event", "landed_without_time", "landed_with_detail",
        "unreadable_with_time", "unreadable_without_error", "empty_text",
        "overlong_text", "duplicate_key", "duplicate_message_id",
    ],
)
def test_invariant_10_validator_rejects_each_impossible_record_condition(case):
    records, line_numbers = _mutated(case)
    with pytest.raises(LedgerMalformed):
        validate_plaza(records, line_numbers)


def test_invariant_10_validator_accepts_tool_post_cli_and_both_delivery_states():
    tool_message = _message()
    landed = build_delivery(message=tool_message, state="landed", landed_at=iso(T0), detail=None)
    post = _message(to="plaza", text="post")
    cli_message = _message(actor="custodian", via="cli", text="human")
    unreadable = build_delivery(
        message=cli_message,
        state="store_unreadable",
        landed_at=None,
        detail={"error": "busy"},
    )
    records = _number(tool_message, landed, post, cli_message, unreadable)
    validate_plaza(records, [1, 2, 3, 4, 5])


def test_invariant_10_malformed_committed_line_refuses_send_and_stops_pass(house):
    root, cfg, binding = house
    cfg.plaza.write_text('{"record_type":"unknown","seq":1}\n')
    before = cfg.plaza.read_bytes()
    with pytest.raises(LedgerMalformed):
        send(
            cfg,
            actor="door:qwen",
            via="tool",
            to="elder",
            text="must fail closed",
            now=T0,
            wake=wake("11111111-1111-4111-8111-111111111111"),
        )
    outcome, memo = run_plaza_pass(binding, now=T0)
    assert "error" in outcome
    assert outcome["units"] == 0
    assert cfg.plaza.read_bytes() == before
