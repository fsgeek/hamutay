"""Contract §§6,10,11: durable reconciliation from public records."""
from datetime import timedelta
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from .support import FILTER, NOW, NS_BOARD, TOOLS, board_event, event_id, ok, opening, update


def test_event_shape_and_ids(house):
    row = opening()
    house.seed([row])
    house.filter()
    house.notice_done()
    result, _ = house.pass_()
    assert result["skipped"] is False and result["queued"] == 1
    event, = house.matches(status="pending")
    assert NS_BOARD == uuid5(NAMESPACE_URL, "hamutay:board")
    assert NS_BOARD != uuid5(NAMESPACE_URL, "hamutay:plaza")
    assert event["event_id"] == event_id("alpha", 1)
    assert event["record_type"] == "event_status" and event["event_type"] == "board_match"
    assert event["origin"] == event["sender"] == "board"
    assert event["purpose"] and event["defer_to_declared_quiet"] is True
    assert not ({"expires_at", "not_before", "requested_context"} & set(event))
    assert event["board"] == board_event(house.root, row)["board"]
    house.filter(door="beta")
    house.notice_done("beta")
    house.pass_(door="beta")
    other, = house.matches("beta")
    assert other["event_id"] == event_id("beta", 1) != event["event_id"]


@pytest.mark.parametrize("case,expected", [("open", 1), ("taken", 0), ("closed", 0),
    ("self", 0), ("self_owned_by_other", 0), ("foreign_owned_by_self", 1), ("mismatch", 0)])
def test_openings_eligibility(house, case, expected):
    row = opening()
    if case in ("self", "self_owned_by_other"):
        row["posted_by"] = "door:alpha"
        row["owner"] = "door:alpha" if case == "self" else "tony"
    if case == "foreign_owned_by_self":
        row["owner"] = "door:alpha"
    if case == "mismatch":
        row["kind"] = "analysis"
    house.seed([row] + ([update(row, 2, "status", status=case)] if case in ("taken", "closed") else []))
    house.filter()
    house.notice_done()
    house.pass_()
    assert len(house.matches()) == expected


def test_no_filter_no_matches(house):
    house.seed([opening()])
    house.pass_()
    assert not house.matches()
    assert len([r for r in house.store.read_records() if r.get("label") == "board:onboarding"]) == 1


def test_generation_rescan_and_supersession(house):
    house.seed([opening()])
    house.notice_done()
    assert ok(house.tool("set_board_filter", {"kinds": ["review"]}))["generation"] == 1
    first, = house.matches(status="pending")
    assert ok(house.tool("clear_board_filter"))["generation"] == 2
    house.pass_()
    old = house.store.latest_by_event_id()[first["event_id"]]
    assert old["status"] == "suppressed" and old["superseded"] is True
    assert old["suppression_reason"] == "filter_cleared"
    assert old["suppressed_by_policy"] == "board" and old["superseded_by_generation"] == 2
    assert ok(house.tool("set_board_filter", {"kinds": ["review"]}))["generation"] == 3
    again, = house.matches(status="pending")
    assert again["event_id"] == event_id("alpha", 1, 3) != first["event_id"]
    assert again["board"]["generation"] == 3
    before = house.snapshot()
    house.pass_()
    assert house.snapshot() == before


def test_nonempty_generation_supersedes_old_pending(house):
    house.seed([opening()])
    house.notice_done()
    ok(house.tool("set_board_filter", {"kinds": ["review"]}))
    first, = house.matches()
    ok(house.tool("set_board_filter", {"kinds": ["build"]}))
    house.pass_()
    row = house.store.latest_by_event_id()[first["event_id"]]
    assert row["status"] == "suppressed" and row["superseded"] is True
    assert row["suppression_reason"] == "superseded_by_generation"
    assert row["superseded_by_generation"] == 2
    assert not house.matches(status="pending")


def test_clear_supersedes(house):
    row = opening()
    house.seed([row])
    house.notice_done()
    house.filter()
    house.queue()
    ok(house.tool("clear_board_filter"))
    house.pass_()
    assert house.store.next_pending(now=NOW) is None
    assert not house.matches(status="pending")
    house.seed([row, update(row, 2)])
    house.pass_()
    assert not house.matches(status="pending")


def test_pass_supersedes_updates(house):
    row = opening()
    house.seed([row])
    house.filter()
    house.notice_done()
    house.queue()
    house.run()
    house.seed([row, update(row, 2)])
    house.pass_()
    pending, = house.matches(status="pending")
    assert pending["board"]["record_type"] == "note"
    result = ok(house.tool("board_pass", {"opportunity_id": row["opportunity_id"]}))
    assert result == {"passed": True, "opportunity_id": row["opportunity_id"], "already_passed": False}
    house.pass_()
    latest = house.store.latest_by_event_id()[pending["event_id"]]
    assert latest["suppression_reason"] == "passed" and latest["superseded"] is True
    before = house.snapshot()
    assert ok(house.tool("board_pass", {"opportunity_id": row["opportunity_id"]}))["already_passed"] is True
    assert house.snapshot() == before
    passes = [r for r in house.store.read_records() if r.get("record_type") == "board_pass"]
    assert len(passes) == 1 and set(passes[0]) == {"record_type", "door", "opportunity_id", "recorded_at"}
    house.seed([row, update(row, 2), update(row, 3, "status", status="closed")])
    house.pass_()
    assert not house.matches(status="pending")


@pytest.mark.parametrize("attempt", [1, 2, 3])
def test_repair_missing_successor(house, attempt):
    row = opening()
    house.seed([row])
    house.filter()
    house.notice_done()
    house.queue(attempt=attempt)
    eid = event_id("alpha", 1, attempt=attempt)
    house.store.append(dict(record_type="event_status", event_id=eid, event_type="board_match",
        status="failed", run_id=str(uuid4()), failed_at=NOW.isoformat(), error="crash after failure",
        board={**board_event(house.root, row, attempt=attempt)["board"], "terminal": attempt == 3, "batch_size": 1}))
    result, _ = house.pass_()
    assert not result.get("error")
    if attempt < 3:
        successor, = house.matches(status="pending")
        assert successor["event_id"] == event_id("alpha", 1, attempt=attempt + 1)
        assert successor["board"]["attempt"] == attempt + 1
    else:
        abandoned = [r for r in house.store.read_records() if r.get("record_type") == "board_match_abandoned"]
        assert len(abandoned) == 1 and abandoned[0]["attempts"] == 3
        assert not house.matches(status="pending")
    before = house.snapshot()
    house.pass_()
    assert house.snapshot() == before


def test_bounded_pass_continues(house):
    rows = house.many(70)
    house.filter()
    seen = set()
    memo = None
    truncated = False
    for _ in range(8):
        before = len(house.store.read_records())
        result, memo = house.pass_(memo=memo)
        added = len(house.store.read_records()) - before
        assert 0 <= added <= 32
        if result.get("skipped") is False:
            assert result["appended"] == added
            truncated |= result["truncated"] is True
        seen.update(r["board"]["board_seq"] for r in house.matches())
        if len(seen) == len(rows):
            break
    assert truncated and seen == set(range(1, 71))
    assert len(house.matches()) == 70


def test_reconcile_idempotent_and_memo_invalidates(house):
    row = opening()
    house.seed([row])
    house.filter()
    house.notice_done()
    _, memo = house.pass_()
    before = house.snapshot()
    result, memo = house.pass_(memo=memo)
    assert result.get("skipped") is True or result.get("appended") == 0
    assert house.snapshot() == before
    house.seed([row, opening(2, posted_by="custodian")])
    house.pass_(memo=memo)
    assert {r["board"]["board_seq"] for r in house.matches()} == {1, 2}
    house.filter(generation=2)
    house.pass_(memo=memo)
    assert {r["event_id"] for r in house.matches(status="pending")} == {
        event_id("alpha", 1, 2), event_id("alpha", 2, 2)}


def test_bad_event_store_is_atomic(house):
    house.seed([opening()])
    house.store.path.write_text("{broken}\n")
    before = house.snapshot()
    result, _ = house.pass_()
    assert result["skipped"] is False and result["error"]
    assert house.snapshot() == before


def test_onboarding_once_per_door(house):
    for door in ("alpha", "beta"):
        house.pass_(door=door)
        notices = [r for r in house.stores[door].read_records() if r.get("label") == "board:onboarding"]
        event, = notices
        assert event["event_id"] == str(uuid5(NS_BOARD, f"{door}:onboarding"))
        assert event["event_type"] == "inbound_message" and event["status"] == "pending"
        assert event["origin"] == event["sender"] == "board"
        assert event["defer_to_declared_quiet"] is True and "expires_at" not in event
    before = house.snapshot()
    house.gate.unlink()
    house.pass_()
    house.gate.touch()
    house.pass_()
    assert house.snapshot() == before


def test_onboarding_content_and_limit(house):
    rows = house.many(23)
    for i, row in enumerate(rows):
        row["title"] = f"Onboarding fixture entry {i:04d}"
    house.seed(rows)
    house.pass_()
    event, = [r for r in house.store.read_records() if r.get("label") == "board:onboarding"]
    text = event["purpose"]
    lower = text.lower()
    for tool in TOOLS:
        assert tool in text
    assert "filter" in lower and any(word in lower for word in ("choice", "choose", "opt", "optional"))
    assert "never" in lower or "not wake" in lower or "no board" in lower
    for number in ("5", "20", "2"):
        assert number in text
    listed = [r for r in rows if r["title"] in text]
    assert len(listed) == 20 and "3" in text


def test_bounded_pass_counts_supersession_and_repair(house):
    rows = house.many(40)
    house.notice_done()
    house.filter(generation=1)
    house.queue(rows)
    house.filter(generation=2)
    memo = None
    for _ in range(10):
        before = len(house.store.read_records())
        result, memo = house.pass_(memo=memo)
        added = len(house.store.read_records()) - before
        assert 0 <= added <= 32
        if result.get("skipped") is False:
            assert result["appended"] == added
        if len(house.matches(status="pending")) == 40 and all(
                e["board"]["generation"] == 2 for e in house.matches(status="pending")):
            break
    latest = house.store.latest_by_event_id()
    assert all(latest[event_id("alpha", row["seq"])]["status"] == "suppressed" for row in rows)
    assert {r["event_id"] for r in house.matches(status="pending")} == {event_id("alpha", n, 2) for n in range(1, 41)}
