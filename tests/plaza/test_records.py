import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from hamutay.assembly.ledger import LedgerMalformed, iso
from hamutay.plaza.ids import (PLAZA_NS, canonical_to, cli_key, delivery_event_id, door_name, is_door,
                               resident_key, sha256_text)
from hamutay.plaza.records import (MAX_TEXT_CHARS, SEND_CAP, build_delivery, build_message, reduce,
                                   validate_plaza)

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
EV = "11111111-1111-4111-8111-111111111111"


def _wake(event_id=EV):
    return {"cycle": 3, "record_id": str(uuid.uuid4()), "event_id": event_id,
            "run_id": str(uuid.uuid4()), "started_at": iso(T0)}


def _msg(to="door:elder", text="hello", actor="door:qwen", via="tool", sent_at=T0, wake=None, key=None):
    delivery = None
    if to != "plaza":
        delivery = {"door": door_name(to), "events_path": "/abs/community/elder/session.jsonl.events.jsonl",
                    "event_id": None, "members_digest": "a" * 64}
    wake = wake if wake is not None else (_wake() if via == "tool" else None)
    key = key or (resident_key(wake["event_id"], to, text) if via == "tool" else cli_key("k"))
    m = build_message(actor=actor, via=via, to=to, text=text, sent_at=iso(sent_at),
                      idempotency_key=key, delivery=delivery, wake=wake)
    return m


def _seq(records):
    out = []
    for i, r in enumerate(records, start=1):
        r = dict(r); r["seq"] = i; r.setdefault("created_at", iso(T0)); out.append(r)
    return out


def test_ids_are_deterministic_and_named():
    assert PLAZA_NS == uuid.uuid5(uuid.NAMESPACE_URL, "hamutay:plaza")
    assert canonical_to("elder") == "door:elder" == canonical_to("door:elder")
    assert canonical_to("plaza") == "plaza"
    with pytest.raises(ValueError):
        canonical_to("Tony")
    assert door_name("door:qwen") == "qwen" and is_door("door:qwen") and not is_door("tony")
    k = resident_key(EV, "door:elder", "hello")
    assert k == str(uuid.uuid5(PLAZA_NS, f"{EV}\0door:elder\0{sha256_text('hello')}"))
    assert uuid.UUID(k).version == 5
    assert cli_key("migration-announcement") == str(uuid.uuid5(PLAZA_NS, "cli\0migration-announcement"))
    mid = str(uuid.uuid4())
    assert delivery_event_id(mid, "elder") == str(uuid.uuid5(PLAZA_NS, f"{mid}\0door:elder"))


def test_build_message_fills_the_delivery_event_id_and_shapes():
    m = _msg()
    assert uuid.UUID(m["message_id"]).version == 4
    assert m["delivery"]["event_id"] == delivery_event_id(m["message_id"], "elder")
    assert m["record_type"] == "message" and m["via"] == "tool" and m["to"] == "door:elder"
    p = _msg(to="plaza")
    assert p["delivery"] is None
    h = _msg(actor="tony", via="cli", to="door:qwen")
    assert h["wake"] is None


def test_validator_accepts_everything_the_writers_produce():
    m1 = _msg(); d1 = build_delivery(message=m1, state="landed", landed_at=iso(T0), detail=None)
    m2 = _msg(to="plaza", text="a post")
    m3 = _msg(actor="custodian", via="cli", to="door:qwen", text="hi", key=cli_key("x"))
    d3 = build_delivery(message=m3, state="store_unreadable", landed_at=None, detail={"error": "busy"})
    recs = _seq([m1, d1, m2, m3, d3])
    validate_plaza(recs, [1, 2, 3, 4, 5])


def _mut(fn):
    """Wrap a plan mutator (which returns `(r.__setitem__(...), ln)`, discarding the
    in-place-mutated list) so it instead mutates in place AND returns the pair the
    caller actually needs: `(recs, ln)`. Preserves each case's mutation text verbatim."""
    return lambda recs, ln: (fn(recs, ln), (recs, ln))[1]


@pytest.mark.parametrize("mutate, expect", [
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "record_type": "note"}), ln)),
     "unknown record_type"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "extra": 1}), ln)),
     "message fields are"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "seq": 2}), ln)),                       # seq != line
     "is not the line number"),
    (lambda r, ln: (r, [2, 3]),                                                            # blank line before
     "is not the line number"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "sent_at": "2026-09-20T12:00:00"}), ln)),  # naive
     "sent_at is not a timezone-bearing instant"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "message_id": str(uuid.uuid5(PLAZA_NS, "x"))}), ln)),
     "message_id is not a version-4"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "idempotency_key": str(uuid.uuid4())}), ln)),
     "idempotency_key is not a version-5"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "from": "Door:Qwen"}), ln)),
     "bad actor"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "to": "door:qwen"}), ln)),               # to == from
     "cannot address itself"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "via": "cli"}), ln)),                    # cli with door actor
     "via cli needs a human actor"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "delivery": None}), ln)),                # directed without delivery
     "bad delivery block"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "delivery": {**r[0]["delivery"], "door": "fable"}}), ln)),
     "delivery.door is not the addressee"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "delivery": {**r[0]["delivery"], "events_path": "rel/p"}}), ln)),
     "delivery.events_path is not absolute"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "delivery": {**r[0]["delivery"], "members_digest": "zz"}}), ln)),
     "delivery.members_digest is not sha256 hex"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "delivery": {**r[0]["delivery"],
                                                                "event_id": str(uuid.uuid5(PLAZA_NS, "y"))}}), ln)),
     "delivery.event_id is not derived from the message"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "text": "",
                          "idempotency_key": resident_key(r[0]["wake"]["event_id"], r[0]["to"], "")}), ln)),
     "text empty or over"),
    (_mut(lambda r, ln: (r.__setitem__(0, {**r[0], "text": "x" * (MAX_TEXT_CHARS + 1),
                          "idempotency_key": resident_key(r[0]["wake"]["event_id"], r[0]["to"],
                                                          "x" * (MAX_TEXT_CHARS + 1))}), ln)),
     "text empty or over"),
    (_mut(lambda r, ln: (r.__setitem__(1, {**r[1], "landed_at": None}), ln)),               # landed without instant
     "landed needs landed_at"),
    (_mut(lambda r, ln: (r.__setitem__(1, {**r[1], "message_id": str(uuid.uuid4())}), ln)),
     "delivery for an unknown or undirected message"),
    (_mut(lambda r, ln: (r.__setitem__(1, {**r[1], "event_id": str(uuid.uuid5(PLAZA_NS, "z"))}), ln)),
     "delivery door/event_id differ"),
])
def test_validator_rejects_each_condition(mutate, expect):
    m1 = _msg(); d1 = build_delivery(message=m1, state="landed", landed_at=iso(T0), detail=None)
    recs = _seq([m1, d1]); ln = [1, 2]
    recs, ln = mutate(recs, ln)
    with pytest.raises(LedgerMalformed, match=re.escape(expect)):
        validate_plaza(recs, ln)


def test_validator_rejects_a_tool_message_with_a_foreign_key_and_any_second_key_or_id():
    m1 = _msg()
    bad = dict(m1); bad["idempotency_key"] = str(uuid.uuid5(PLAZA_NS, "foreign"))
    with pytest.raises(LedgerMalformed):
        validate_plaza(_seq([bad]), [1])
    twin = dict(m1); twin["message_id"] = str(uuid.uuid4())    # same content, same key
    twin["delivery"] = {**twin["delivery"], "event_id": delivery_event_id(twin["message_id"], "elder")}
    with pytest.raises(LedgerMalformed):
        validate_plaza(_seq([m1, twin]), [1, 2])
    same_id = dict(_msg(text="other")); same_id["message_id"] = m1["message_id"]
    same_id["delivery"] = {**same_id["delivery"], "event_id": delivery_event_id(m1["message_id"], "elder")}
    with pytest.raises(LedgerMalformed):
        validate_plaza(_seq([m1, same_id]), [1, 2])
    store_unreadable_with_landing = build_delivery(message=m1, state="store_unreadable", landed_at=iso(T0), detail={"error": "x"})
    with pytest.raises(LedgerMalformed):
        validate_plaza(_seq([m1, store_unreadable_with_landing]), [1, 2])


def test_view_truths_counts_and_visibility():
    m1 = _msg(text="one")
    d1 = build_delivery(message=m1, state="store_unreadable", landed_at=None, detail={"error": "busy"})
    d2 = build_delivery(message=m1, state="landed", landed_at=iso(T0 + timedelta(seconds=5)), detail=None)
    m2 = _msg(to="plaza", text="post", sent_at=T0 + timedelta(minutes=1))
    m3 = _msg(actor="door:elder", to="door:fable", text="e→f", sent_at=T0 + timedelta(minutes=2),
              wake=_wake("22222222-2222-4222-8222-222222222222"))
    m4 = _msg(actor="door:elder", to="door:qwen", text="e→q", sent_at=T0 + timedelta(minutes=3),
              wake=_wake("33333333-3333-4333-8333-333333333333"))
    v = reduce(_seq([m1, d1, m2, m3, d2, m4]))
    assert [m["text"] for m in v.messages] == ["one", "post", "e→f", "e→q"]
    assert v.delivery_truth(m1["message_id"])["state"] == "landed"
    assert v.delivery_truth(m3["message_id"])["state"] == "planned"
    assert [m["text"] for m in v.undelivered()] == ["e→f", "e→q"]
    assert v.sent_today("door:qwen", date(2026, 9, 20)) == 1       # the post is not counted
    assert v.sent_today("door:elder", date(2026, 9, 20)) == 2
    assert v.sent_today("door:elder", date(2026, 9, 21)) == 0
    # qwen's view: excludes its own (one, post) and mail to it (e→q); sees e→f
    assert [m["text"] for m in v.visible_since(T0, "qwen")] == ["e→f"]
    assert [m["text"] for m in v.visible_since(None, "fable")] == ["one", "post", "e→q"]
    assert [m["text"] for m in v.visible_since(T0 + timedelta(minutes=2, seconds=30), "fable")] == ["e→q"]
    assert v.by_key[m1["idempotency_key"]]["seq"] == 1
    assert SEND_CAP == 48


def test_the_two_lock_windows_are_defined_once_and_imported(tmp_path):
    """M2: the plan's Global Constraints name PLAZA_LOCK_WINDOW_S and
    STORE_LOCK_WINDOW_S once each; ids.py is the one definition and every
    plaza module is the same object, not a coincidentally equal float."""
    import ast
    from pathlib import Path

    # via import_module, not attribute access -- hamutay.plaza's __init__ rebinds
    # the name `send` on the package to the send *function*, shadowing the module.
    from importlib import import_module

    ids = import_module("hamutay.plaza.ids")
    send = import_module("hamutay.plaza.send")
    note = import_module("hamutay.plaza.note")
    cli = import_module("hamutay.plaza.cli")
    pass_ = import_module("hamutay.plaza.pass_")
    store = import_module("hamutay.plaza.store")

    assert ids.PLAZA_LOCK_WINDOW_S == ids.STORE_LOCK_WINDOW_S == 2.0
    for mod in (send, note, cli, pass_):
        assert mod.PLAZA_LOCK_WINDOW_S is ids.PLAZA_LOCK_WINDOW_S, mod.__name__
    for mod in (store, pass_):
        assert mod.STORE_LOCK_WINDOW_S is ids.STORE_LOCK_WINDOW_S, mod.__name__

    # and nothing in the package assigns either name outside ids.py
    pkg = Path(ids.__file__).parent
    for py in sorted(pkg.glob("*.py")):
        if py.name == "ids.py":
            continue
        for node in ast.walk(ast.parse(py.read_text())):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    assert getattr(t, "id", None) not in ("PLAZA_LOCK_WINDOW_S", "STORE_LOCK_WINDOW_S"), py.name
