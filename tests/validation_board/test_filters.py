"""Contract §§2,5,10: opt-in, normalization and truth-table matching."""
from copy import deepcopy
from uuid import uuid4

import pytest

from .support import FILTER, TOOLS, bytes_at, ok, opening, refused


def test_dormant_pass_and_tool_gate(house):
    house.gate.unlink()
    house.filter()
    row = opening()
    house.seed([row])
    house.queue([row], generation=0)
    before = house.snapshot()
    result, _ = house.pass_()
    assert result == {"skipped": "dormant", "appended": 0}
    for name in TOOLS:
        out = house.tool(name)
        assert out == {"error": f"{name}: the board is not enabled in this house"}
    assert house.snapshot() == before


def test_gate_checked_each_call(house):
    ok(house.tool("board_read"))
    house.gate.unlink()
    assert "error" in house.tool("board_read")
    before = house.snapshot()
    assert house.pass_()[0] == {"skipped": "dormant", "appended": 0}
    assert house.snapshot() == before
    house.gate.write_text("0 false disabled are all ignored")
    ok(house.tool("board_read"))
    assert house.pass_()[0].get("skipped") != "dormant"


def test_generation_storage_and_isolation(house):
    assert not house.store.read_records()
    first = ok(house.tool("set_board_filter", {"kinds": ["review"]}))
    assert first["generation"] == 1 and first["filter"] == FILTER
    second = ok(house.tool("clear_board_filter"))
    assert second["generation"] == 2 and second["filter"] is None and second["note"]
    third = ok(house.tool("set_board_filter", {"kinds": ["review"]}))
    assert third["generation"] == 3
    records = [r for r in house.store.read_records() if r.get("record_type") == "board_filter"]
    assert [r["generation"] for r in records] == [1, 2, 3]
    for r in records:
        assert set(r) == {"record_type", "door", "generation", "filter", "recorded_at"}
        assert r["door"] == "alpha"
    beta = ok(house.tool("set_board_filter", {"kinds": ["design"]}, door="beta"))
    assert beta["generation"] == 1


def test_filter_normalization(house):
    result = ok(house.tool("set_board_filter", {
        "kinds": [" ＲＥＶＩＥＷ ", "review", "BUILD"], "tags_any": [" ＭＥＭＯＲＹ ", "memory", "new"],
        "owners_any": [" ＴＯＮＹ ", "tony", "DOOR:ALPHA"],
        "keywords_any": [" ＤＲＡＦＴ ", "draft", "Straße", "STRASSE"]}))
    expected = {"kinds": ["review", "build"], "tags_any": ["memory", "new"],
                "owners_any": ["tony", "door:alpha"], "keywords_any": ["draft", "strasse"]}
    assert result["filter"] == expected
    records = [r for r in house.store.read_records() if r.get("record_type") == "board_filter"]
    assert records[-1]["filter"] == expected


INVALID = [
    {"unknown": []}, {"kinds": "review"}, {"tags_any": {}}, {"owners_any": 3},
    {"keywords_any": [None]}, {"keywords_any": [2]}, {"keywords_any": ["ab"]},
    {"keywords_any": ["x" * 65]}, {"kinds": ["science"]}, {"tags_any": ["has space"]},
    {"tags_any": ["has_underscore"]}, {"tags_any": ["é"]}, {"tags_any": ["x" * 33]},
    {"owners_any": ["outsider"]}, {"owners_any": ["door:"]}, {"owners_any": ["guest:a"]},
    *[{field: [blank]} for field in FILTER for blank in ("", " \t ", "\u3000")],
    *[{field: ["review" if field == "kinds" else "tony" if field == "owners_any" else "abc"] * 17}
      for field in FILTER],
]


@pytest.mark.parametrize("data", INVALID)
def test_invalid_filter_is_atomic(house, data):
    house.filter()
    refused(house, "set_board_filter", data)


def test_filter_limits_accept_endpoints(house):
    data = {"kinds": ["review"] * 16, "tags_any": ["a" * 32],
            "owners_any": ["guest:" + "a" * 32], "keywords_any": ["abc", "x" * 64]}
    result = ok(house.tool("set_board_filter", data))
    assert result["filter"]["kinds"] == ["review"]
    assert result["filter"]["keywords_any"] == data["keywords_any"]


@pytest.mark.parametrize("data", [{}, {"kinds": None}, {key: [] for key in FILTER},
                                  {key: None for key in FILTER}])
def test_empty_filter_matches_nothing(house, data):
    house.seed([opening()])
    result = ok(house.tool("set_board_filter", data))
    assert result["filter"] == {key: [] for key in FILTER}
    assert result["queued_now"] == 0 and result["note"]
    assert not house.matches()


@pytest.mark.parametrize("changes,expected", [
    ({}, True), ({"kind": "build"}, True), ({"kind": "other"}, False),
    ({"tags": ["second"]}, True), ({"tags": ["unrelated"]}, False),
    ({"owner": "custodian"}, True), ({"owner": "door:beta"}, False),
    ({"title": "Nothing", "what": "An OVERDRAFTING exercise"}, True),
    ({"title": "ＰＲＥＤＲＡＦＴ", "what": "Nothing"}, True),
    ({"title": "Nothing", "what": "A completely unrelated exercise"}, False),
])
def test_matching_truth_table(house, changes, expected):
    row = opening(title="Draft", what="Something", **{k: v for k, v in changes.items() if k not in ("title", "what")})
    row.update({k: v for k, v in changes.items() if k in ("title", "what")})
    house.seed([row])
    data = {"kinds": ["review", "build"], "tags_any": ["memory", "second"],
            "owners_any": ["tony", "custodian"], "keywords_any": ["draft", "elsewhere"]}
    result = ok(house.tool("set_board_filter", data))
    assert result["queued_now"] == int(expected)
    events = house.matches(status="pending")
    assert len(events) == int(expected)
    if expected:
        clause = events[0]["board"]["clause"]
        assert set(clause) == set(FILTER)
        assert clause["kinds"] == [row["kind"]]
        assert clause["tags_any"] == [row["tags"][0]]
        assert clause["owners_any"] == [row["owner"]]
        assert clause["keywords_any"] == ["draft"]


def test_set_scans_immediately(house):
    house.seed([opening()])
    result = ok(house.tool("set_board_filter", {"keywords_any": ["draft", "memory"]}))
    assert result["queued_now"] == 1
    assert house.matches()[0]["board"]["clause"] == {"keywords_any": ["draft", "memory"]}


def test_set_scan_error_keeps_filter(house):
    house.board.write_text("{broken}\n")
    result = ok(house.tool("set_board_filter", {"kinds": ["review"]}))
    assert result["filter"] == FILTER and result["generation"] == 1
    assert result["scan_error"] and "queued_now" not in result
    assert [r["generation"] for r in house.store.read_records() if r.get("record_type") == "board_filter"] == [1]
    assert not house.matches()


@pytest.mark.parametrize("spoof", [{"posted_by": "tony"}, {"by": "tony"},
    {"door": "beta"}, {"store": "elsewhere.jsonl"}, {"project_root": "/unusable-board-root"}])
def test_tool_identity_and_store_are_bound(house, spoof):
    before_beta = bytes_at(house.stores["beta"].path)
    result = house.post(**spoof)
    if "error" in result:
        assert result["error"].startswith("board_post:") and not house.rows()
    else:
        assert house.rows()[0]["posted_by"] == "door:alpha"
        assert house.rows()[0]["owner"] == "door:alpha"
    assert bytes_at(house.stores["beta"].path) == before_beta


def test_board_read_response_and_coverage_not_editable(house):
    house.seed([opening()])
    before = house.snapshot()
    result = ok(house.tool("board_read"))
    assert set(result) == {"board_seq", "entries", "omitted_older", "path"}
    assert house.snapshot() == before
    refused(house, "set_board_coverage", {"opportunity_id": house.rows()[0]["opportunity_id"]})


@pytest.mark.parametrize("include_closed", [False, True])
def test_board_read_closed_and_since_projection(house, include_closed):
    from .support import update
    row = opening()
    house.seed([row, update(row, 2), update(row, 3, "status", status="closed", reason="Done")])
    before = house.snapshot()
    result = ok(house.tool("board_read", {"include_closed": include_closed, "since_seq": 2}))
    assert result["board_seq"] == 3
    assert len(result["entries"]) == int(include_closed)
    if include_closed:
        entry, = result["entries"]
        assert entry["opportunity_id"] == row["opportunity_id"]
        assert entry["status"] == "closed" and entry["status_reason"] == "Done"
        assert entry["notes"][0]["seq"] == 2
    assert house.snapshot() == before
