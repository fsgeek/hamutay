import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hamutay.assembly.binding import load_members
from hamutay.assembly.convene import ConveneRefused, convene
from hamutay.assembly.ledger import Ledger, iso
from hamutay.assembly.outbox import run_outbox
from hamutay.assembly.records import reduce
from hamutay.events import EventStore, StoreUnavailable

UTC = timezone.utc
T0 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


@pytest.fixture
def house(tmp_path):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    members = {d: {"session": f"community/{d}/session.jsonl", "events": f"community/{d}/session.jsonl.events.jsonl"}
               for d in ("qwen", "elder")}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    for d in ("qwen", "elder"):
        (tmp_path / "community" / d).mkdir()
    cfg = load_members(tmp_path)
    return tmp_path, Ledger(cfg.ledger), cfg


def test_convene_writes_a_question_with_the_snapshot_and_refuses_a_second_open_lineage(house):
    root, led, cfg = house
    q = convene(led, cfg, convener="custodian", text="first?", closes_in=timedelta(days=7), now=T0,
                proposal_procedure={"rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)"},
                artifact={"path": "p", "commit": "c", "sha256": "s"})
    assert q["members"] == cfg.snapshot() and q["proposal"]["kind"] == "procedure"
    assert q["governing"]["procedure_id"] is None and q["closes_at"] == iso(T0 + timedelta(days=7))
    with pytest.raises(ConveneRefused):
        convene(led, cfg, convener="custodian", text="second?", closes_in=timedelta(days=7), now=T0)
    q2 = convene(led, cfg, convener="tony", text="other?", closes_in=timedelta(days=2), now=T0)
    assert q2["proposal"]["kind"] == "text"


def test_convene_bounds_and_missing_procedure(house):
    root, led, cfg = house
    with pytest.raises(ConveneRefused):
        convene(led, cfg, convener="tony", text="t", closes_in=timedelta(hours=23), now=T0)
    with pytest.raises(ConveneRefused):
        convene(led, cfg, convener="tony", text="t", closes_in=timedelta(days=31), now=T0)
    with pytest.raises(ConveneRefused):          # no procedure record exists yet, no proposal
        convene(led, cfg, convener="tony", text="t", closes_in=timedelta(days=2), now=T0)


def test_outbox_lands_each_delivery_at_most_once_and_records_landed_at(house):
    root, led, cfg = house
    q = convene(led, cfg, convener="tony", text="t", closes_in=timedelta(days=2), now=T0,
                proposal_procedure={"rule": "consent-v0"}, artifact={})
    with led.locked():
        rows = run_outbox(led, reduce(led.read_unlocked()), now=T0)
    assert sorted(r["door"] for r in rows) == ["elder", "qwen"] and all(r["state"] == "landed" for r in rows)
    store = EventStore(cfg.members["qwen"].events)
    evs = [r for r in store.read_records() if r.get("event_id") == q["delivery"]["qwen"]["event_id"]]
    assert len(evs) == 1 and evs[0]["defer_to_declared_quiet"] is True
    assert evs[0]["assembly_question_id"] == q["question_id"] and evs[0]["expires_at"] == q["closes_at"]
    assert evs[0]["purpose"].startswith("An assembly question, put by tony")
    with led.locked():
        again = run_outbox(led, reduce(led.read_unlocked()), now=T0)
    assert again == [] and len([r for r in store.read_records() if r.get("event_id") == evs[0]["event_id"]]) == 1


def test_outbox_records_store_unreadable_once_per_error_and_retries(house, monkeypatch):
    root, led, cfg = house
    convene(led, cfg, convener="tony", text="t", closes_in=timedelta(days=2), now=T0,
            proposal_procedure={"rule": "consent-v0"}, artifact={})
    calls = {"n": 0}
    real = EventStore.append_if_absent

    def flaky(self, event, *, timeout_s=2.0):
        if "qwen" in str(self.path):
            calls["n"] += 1
            raise StoreUnavailable("busy")
        return real(self, event, timeout_s=timeout_s)

    monkeypatch.setattr(EventStore, "append_if_absent", flaky)
    with led.locked():
        run_outbox(led, reduce(led.read_unlocked()), now=T0)
        run_outbox(led, reduce(led.read_unlocked()), now=T0)
    rows = [r for r in led.read() if r["record_type"] == "delivery" and r["door"] == "qwen"]
    assert len(rows) == 1 and rows[0]["state"] == "store_unreadable" and calls["n"] == 2
    monkeypatch.setattr(EventStore, "append_if_absent", real)
    with led.locked():
        run_outbox(led, reduce(led.read_unlocked()), now=T0)
    view = reduce(led.read())
    q = view.open_questions()[0]
    assert view.delivery_truth("question", q["question_id"], "qwen")["state"] == "landed"


def test_outbox_cancels_a_stale_question_delivery_after_its_closing(house, monkeypatch):
    from hamutay.assembly.records import closing_event_id, closing_id_for
    root, led, cfg = house
    q = convene(led, cfg, convener="tony", text="t", closes_in=timedelta(days=2), now=T0,
                proposal_procedure={"rule": "consent-v0"}, artifact={})
    cid = closing_id_for(q["question_id"])
    led.append({"record_type": "closing", "closing_id": cid, "question_id": q["question_id"],
                "lineage_id": q["lineage_id"], "round": 1, "outcome": "unresolved", "governing": q["governing"],
                "provisional": True, "tally": {"trace": "t"}, "positions": [], "testimony": [], "absent": [],
                "next_question": None, "closed_by": "cli:test", "closed_at": iso(T0 + timedelta(days=2)),
                "proposal_sha256": q["proposal"]["sha256"],
                "delivery": {d: {"event_id": closing_event_id(cid, d)} for d in q["members"]}})
    with led.locked():
        rows = run_outbox(led, reduce(led.read_unlocked()), now=T0 + timedelta(days=2))
    kinds = sorted((r["for"], r["state"]) for r in rows)
    assert kinds == [("closing", "landed"), ("closing", "landed"), ("question", "cancelled"), ("question", "cancelled")]
    store = EventStore(cfg.members["qwen"].events)
    ids = {r.get("event_id") for r in store.read_records()}
    assert q["delivery"]["qwen"]["event_id"] not in ids and closing_event_id(cid, "qwen") in ids


def test_parse_closes_in_units_and_rejects_garbage():
    from hamutay.assembly.convene import parse_closes_in
    assert parse_closes_in("7d") == timedelta(days=7)
    assert parse_closes_in("48h") == timedelta(hours=48)
    assert parse_closes_in("90m") == timedelta(minutes=90)
    with pytest.raises(ValueError):
        parse_closes_in("7 days")


def test_convene_refuses_when_a_member_was_added_while_a_lineage_is_open(house, tmp_path):
    """I3: convene compared only the doors present in the snapshot, so a member ADDED
    to members.json after a question opened slipped past the path freeze."""
    root, led, cfg = house
    convene(led, cfg, convener="custodian", text="first?", closes_in=timedelta(days=7), now=T0,
            proposal_procedure={"rule": "consent-v0"}, artifact={})
    plaza = root / "community" / "plaza"
    members = {d: {"session": f"community/{d}/session.jsonl", "events": f"community/{d}/session.jsonl.events.jsonl"}
               for d in ("qwen", "elder", "fable")}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    (root / "community" / "fable").mkdir()
    cfg2 = load_members(root)
    with pytest.raises(ConveneRefused, match="fable"):
        convene(led, cfg2, convener="tony", text="second?", closes_in=timedelta(days=2), now=T0)


def test_convene_refuses_when_a_member_was_removed_while_a_lineage_is_open(house):
    root, led, cfg = house
    convene(led, cfg, convener="custodian", text="first?", closes_in=timedelta(days=7), now=T0,
            proposal_procedure={"rule": "consent-v0"}, artifact={})
    plaza = root / "community" / "plaza"
    members = {"qwen": {"session": "community/qwen/session.jsonl",
                        "events": "community/qwen/session.jsonl.events.jsonl"}}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    cfg2 = load_members(root)
    with pytest.raises(ConveneRefused, match="elder"):
        convene(led, cfg2, convener="tony", text="second?", closes_in=timedelta(days=2), now=T0)
