"""Contract §§1–4: actual CLI and door writers, independent raw-file faults."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import subprocess
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import pytest

from .support import NOW, bytes_at, ok, opening, refused, update


def test_paths_and_gitignore(house):
    out = ok(house.post())
    assert out["seq"] == 1 and house.board.exists()
    assert house.board.with_name("board.jsonl.lock").exists()
    # Query ignore rules, without inspecting any community contents or git index.
    result = subprocess.run(["git", "check-ignore", "--no-index", "community/board/board.jsonl",
                             "community/board/board.jsonl.lock", "community/board/board.enabled"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert set(result.stdout.splitlines()) == {"community/board/board.jsonl",
        "community/board/board.jsonl.lock", "community/board/board.enabled"}


def test_cli_dormant_and_overview(house):
    house.gate.unlink()
    overview = house.cli()
    assert overview.returncode == 0 and "dormant" in overview.stdout.lower()
    out = house.cli_json("post", "--by", "tony", "--title", "Draft", "--what", "Read", "--kind", "review")
    assert out["posted"] is True and "dormant" in out["note"].lower()
    read = house.cli_json("read")
    assert read["enabled"] is False and read["board_seq"] == 1
    assert read["path"] == str(house.board)
    assert len(read["entries"]) == 1
    assert not house.store.read_records()
    house.gate.touch()
    assert house.cli().returncode == 0
    assert house.cli_json("read")["enabled"] is True


@pytest.mark.parametrize("cmd", ["post", "note", "status"])
def test_cli_refuses_door_writer(house, cmd):
    args = {"post": ["--title", "T", "--what", "W", "--kind", "review"],
            "note": ["--id", str(uuid4()), "--text", "N"],
            "status": ["--id", str(uuid4()), "--status", "taken"]}[cmd]
    before = house.snapshot()
    result = house.cli(cmd, "--by", "door:alpha", *args)
    assert result.returncode == 2 and result.stderr
    assert house.snapshot() == before


def test_record_shapes(house):
    first = ok(house.post())
    oid = first["opportunity_id"]
    ok(house.tool("board_post", {"record_type": "note", "opportunity_id": oid, "text": "Evidence"}))
    ok(house.tool("board_post", {"record_type": "status", "opportunity_id": oid, "status": "taken"}))
    rows = house.rows()
    common = {"record_type", "seq", "created_at", "opportunity_id"}
    assert set(rows[0]) == common | {"posted_by", "posted_at", "title", "what", "why", "help_wanted",
        "kind", "tags", "owner", "record_of_help"}
    assert set(rows[1]) == common | {"by", "text"}
    assert set(rows[2]) == common | {"by", "status", "reason"}
    assert UUID(oid).version == 4 and str(UUID(oid)) == oid
    from datetime import datetime
    for seq, row in enumerate(rows, 1):
        assert row["seq"] == seq
        assert datetime.fromisoformat(row["created_at"]).utcoffset() is not None
    assert datetime.fromisoformat(rows[0]["posted_at"]).utcoffset() is not None


def test_writer_normalization(house):
    out = ok(house.post(title="  Draft  ", kind=" ＲＥＶＩＥＷ ",
                        tags=[" ＭＥＭＯＲＹ ", "memory", "NeW"], owner=" ＴＯＮＹ "))
    assert out["owner"] == "tony" and out["tags"] == ["memory", "new"]
    row = house.rows()[0]
    assert (row["title"], row["kind"], row["posted_by"]) == ("Draft", "review", "door:alpha")


@pytest.mark.parametrize("field,value", [
    ("title", ""), ("title", " \t "), ("title", "x" * 121), ("title", "two\nlines"),
    ("what", ""), ("what", " \n"), ("what", "x" * 2001),
    ("why", "x" * 1001), ("help_wanted", "x" * 1001), ("record_of_help", "x" * 501),
    ("kind", "science"), ("kind", None), ("tags", [f"tag{i}" for i in range(9)]),
    ("tags", ["x" * 33]), ("tags", ["has_space "]), ("tags", [""]),
    ("tags", ["é"]), ("tags", "memory"), ("owner", "door:Bad.Dot"),
    ("owner", "guest:a"), ("owner", "guest:" + "a" * 33), ("owner", "someone"),
    ("title", None), ("what", None), ("title", 123), ("what", []),
    ("why", False), ("help_wanted", []), ("record_of_help", 4),
    ("tags", False), ("owner", 123),
])
def test_opening_writer_rejects_invalid_fields(house, field, value):
    refused(house, "board_post", {"title": "Draft", "what": "Read", "kind": "review", field: value})


@pytest.mark.parametrize("field,value", [("title", "x" * 120), ("what", "x" * 2000),
    ("what", "x"), ("why", "x" * 1000), ("why", ""),
    ("help_wanted", "x" * 1000), ("record_of_help", "x" * 500),
    ("tags", ["a" * 32] + [f"tag{i}" for i in range(7)]),
    ("owner", "door:a_0-"), ("owner", "guest:" + "a" * 32),
    *[("kind", kind) for kind in ["review", "design", "build", "analysis", "writing", "testimony", "other"]]])
def test_opening_writer_accepts_boundaries(house, field, value):
    ok(house.post(**{field: value}))
    assert len(house.rows()) == 1


@pytest.mark.parametrize("fields", [
    ["why"], ["help_wanted"], ["record_of_help"], ["tags"], ["owner"],
    ["why", "help_wanted", "record_of_help", "tags", "owner"],
])
def test_opening_optional_null_is_absent(house, fields):
    first = ok(house.post(**dict.fromkeys(fields)))
    row, = house.rows()
    defaults = {"why": "", "help_wanted": "", "record_of_help": "",
                "tags": [], "owner": "door:alpha"}
    assert {field: row[field] for field in defaults} == defaults
    assert all(row[field] is not None for field in defaults)
    duplicate = ok(house.post())
    assert duplicate["duplicate_of_seq"] == first["seq"]
    assert house.rows() == [row]


def test_status_optional_null_reason_is_absent(house):
    oid = ok(house.post())["opportunity_id"]
    data = {"record_type": "status", "opportunity_id": oid, "status": "taken"}
    first = ok(house.tool("board_post", {**data, "reason": None}))
    rows = house.rows()
    assert rows[-1]["reason"] == ""
    duplicate = ok(house.tool("board_post", data))
    assert duplicate["duplicate_of_seq"] == first["seq"]
    assert house.rows() == rows


@pytest.mark.parametrize("record_type,field,value", [
    ("note", "text", ""), ("note", "text", " \n"), ("note", "text", "x" * 1001),
    ("note", "text", None), ("status", "status", "paused"),
    ("status", "status", None), ("status", "reason", "x" * 501),
    ("status", "reason", False)])
def test_update_writer_limits(house, record_type, field, value):
    oid = ok(house.post())["opportunity_id"]
    data = {"record_type": record_type, "opportunity_id": oid,
            **({"text": "Evidence"} if record_type == "note" else {"status": "taken", "reason": ""}),
            field: value}
    refused(house, "board_post", data)


def test_owner_and_closed_final(house):
    oid = ok(house.post(owner="tony"))["opportunity_id"]
    for data in ({"record_type": "note", "text": "no"}, {"record_type": "status", "status": "taken"}):
        refused(house, "board_post", {"opportunity_id": oid, **data})
    house.cli_json("note", "--by", "tony", "--id", oid, "--text", "x" * 1000)
    house.cli_json("status", "--by", "tony", "--id", oid, "--status", "closed", "--reason", "x" * 500)
    for args in [("note", "--text", "again"), ("status", "--status", "open"), ("status", "--status", "closed", "--reason", "x" * 500)]:
        before = house.snapshot()
        result = house.cli(args[0], "--by", "tony", "--id", oid, *args[1:])
        assert result.returncode == 2 and result.stderr.startswith(f"board {args[0]}:")
        assert house.snapshot() == before


def test_five_open_cap_and_reopen(house):
    ids = [ok(house.post(title=f"Draft {i}"))["opportunity_id"] for i in range(5)]
    refused(house, "board_post", {"title": "Sixth", "what": "Review", "kind": "review"})
    ok(house.tool("board_post", {"record_type": "status", "opportunity_id": ids[0], "status": "taken"}))
    ok(house.post(title="Sixth"))
    refused(house, "board_post", {"record_type": "status", "opportunity_id": ids[0], "status": "open"})
    ok(house.tool("board_post", {"title": "Beta", "what": "Review", "kind": "review"}, door="beta"))


def test_cap_belongs_to_poster(house):
    for i in range(5):
        ok(house.post(title=f"Owned by Tony {i}", owner="tony"))
    refused(house, "board_post", {"title": "Sixth", "what": "Review", "kind": "review", "owner": "custodian"})
    house.cli_json("post", "--by", "tony", "--title", "Tony's", "--what", "Read", "--kind", "review", "--owner", "door:alpha")


def test_daily_record_cap_and_duplicates(house):
    oid = ok(house.post())["opportunity_id"]
    for i in range(18):
        ok(house.tool("board_post", {"record_type": "note", "opportunity_id": oid, "text": f"Note {i}"}))
    last = {"record_type": "status", "opportunity_id": oid, "status": "taken", "reason": "Working"}
    ok(house.tool("board_post", last))
    assert len(house.rows()) == 20
    for data in ({"title": "New", "what": "Read", "kind": "review"},
                 {"record_type": "note", "opportunity_id": oid, "text": "21st"},
                 {**last, "reason": "21st"}):
        refused(house, "board_post", data)
    assert ok(house.post())["duplicate_of_seq"] == 1
    assert ok(house.tool("board_post", {"record_type": "note", "opportunity_id": oid, "text": "Note 0"}))["duplicate_of_seq"] == 2
    assert ok(house.tool("board_post", last))["duplicate_of_seq"] == 20
    assert len(house.rows()) == 20
    # Another writer is independent, then UTC midnight resets alpha's cap.
    ok(house.tool("board_post", {"title": "Beta", "what": "Read", "kind": "review"}, door="beta"))
    ok(house.tool("board_post", {"record_type": "note", "opportunity_id": oid, "text": "Tomorrow"}, now=NOW + timedelta(days=1)))


def test_utc_record_cap(house):
    first = opening(posted_by="door:alpha", owner="door:alpha", created_at="2026-10-15T23:30:00-07:00")
    rows = [first] + [update(first, i, created_at="2026-10-15T23:30:00-07:00") for i in range(2, 21)]
    house.seed(rows)
    data = {"record_type": "note", "opportunity_id": first["opportunity_id"], "text": "UTC 16"}
    before = house.snapshot()
    out = house.tool("board_post", data, now=NOW + timedelta(days=1))
    assert "error" in out and house.snapshot() == before
    ok(house.tool("board_post", {**data, "text": "UTC 17"}, now=NOW + timedelta(days=2)))


def test_dedup_and_first_open_status(house):
    oid = ok(house.post())["opportunity_id"]
    assert ok(house.post(title=" A draft "))["duplicate_of_seq"] == 1
    base = {"opportunity_id": oid}
    note = {**base, "record_type": "note", "text": "Evidence"}
    assert ok(house.tool("board_post", note))["seq"] == 2
    assert ok(house.tool("board_post", note))["duplicate_of_seq"] == 2
    status = {**base, "record_type": "status", "status": "open", "reason": ""}
    assert ok(house.tool("board_post", status))["seq"] == 3  # no implicit status record
    assert ok(house.tool("board_post", status))["duplicate_of_seq"] == 3
    ok(house.tool("board_post", {**status, "reason": "Different"}))
    assert ok(house.tool("board_post", status))["seq"] == 5


def test_closed_opening_can_be_reposted(house):
    oid = ok(house.post())["opportunity_id"]
    ok(house.tool("board_post", {"record_type": "status", "opportunity_id": oid, "status": "closed"}))
    result = ok(house.post())
    assert result["opportunity_id"] != oid and result["seq"] == 3


def test_guest_admission(house):
    out = house.cli_json("post", "--by", "guest:visitor", "--title", "Guest", "--what", "Read", "--kind", "review")
    assert out["owner"] == "guest:visitor"
    before = house.snapshot()
    result = house.cli("post", "--by", "guest:stranger", "--title", "Guest", "--what", "Read", "--kind", "review")
    assert result.returncode == 2 and result.stderr.startswith("board post:")
    assert house.snapshot() == before


def test_cli_read_projection_and_since(house):
    row = opening()
    house.seed([row, update(row, 2), update(row, 3, "status", status="closed", reason="Done")])
    assert house.cli_json("read")["entries"] == []
    result = house.cli_json("read", "--all", "--id", row["opportunity_id"])
    entry, = result["entries"]
    assert entry["status"] == "closed" and entry["status_reason"] == "Done" and entry["status_seq"] == 3
    assert set(entry["notes"][0]) == {"seq", "by", "created_at", "text"}
    assert len(entry["status_history"]) == 1
    assert len(house.cli_json("read", "--all", "--since-seq", 2)["entries"]) == 1
    assert house.cli_json("read", "--all", "--since-seq", 4)["entries"] == []
    missing = house.cli_json("read", "--id", str(uuid4()))
    assert missing["entries"] == [] and missing["error"]


def test_cli_newest_fifty(house):
    rows = house.many(53)
    out = house.cli_json("read", "--all")
    assert out["omitted_older"] == 3 and out["board_seq"] == 53
    assert {e["opportunity_id"] for e in out["entries"]} == {r["opportunity_id"] for r in rows[3:]}


FAULTS = [
    "extra", "missing", "seq", "timestamp", "uuid", "uuid_case", "uuid_version", "title_untrimmed",
    "title_multiline", "title_long", "what_blank", "what_long", "why_long", "help_long", "help_record_long",
    "label", "owner", "tag_unnormalized", "tag_duplicate", "tag_long", "tags_many", "kind",
    "duplicate_opening", "orphan_note", "orphan_status", "foreign_note", "foreign_status", "after_closed",
    "note_empty", "note_long", "note_extra", "status_extra", "invalid_status", "reason_long", "json_middle", "json_final_terminated"]


def corrupt_rows(fault):
    row = opening(opportunity_id="12345678-abcd-4123-8123-123456789abc")
    rows = [row]
    changes = {
        "extra": {"extra": True}, "seq": {"seq": 2}, "timestamp": {"created_at": "2026-10-15T12:00:00"},
        "uuid": {"opportunity_id": "not-a-uuid"}, "uuid_case": {"opportunity_id": row["opportunity_id"].upper()},
        "uuid_version": {"opportunity_id": str(uuid5(NAMESPACE_URL, "wrong-version"))},
        "title_untrimmed": {"title": " Draft "}, "title_multiline": {"title": "a\nb"}, "title_long": {"title": "x" * 121},
        "what_blank": {"what": " "}, "what_long": {"what": "x" * 2001}, "why_long": {"why": "x" * 1001},
        "help_long": {"help_wanted": "x" * 1001}, "help_record_long": {"record_of_help": "x" * 501},
        "label": {"posted_by": "Tony"}, "owner": {"owner": "invalid"},
        "tag_unnormalized": {"tags": ["Memory"]}, "tag_duplicate": {"tags": ["memory", "memory"]},
        "tag_long": {"tags": ["x" * 33]}, "tags_many": {"tags": [f"t{i}" for i in range(9)]}, "kind": {"kind": "bad"}}
    if fault in changes:
        row.update(changes[fault])
    elif fault == "missing":
        del row["why"]
    elif fault == "duplicate_opening":
        rows.append({**row, "seq": 2})
    elif fault.startswith("orphan_"):
        rows = [update(row, 1, fault.split("_")[1])]
    elif fault.startswith("foreign_"):
        rows.append(update(row, 2, fault.split("_")[1], by="custodian"))
    elif fault == "after_closed":
        rows.extend([update(row, 2, "status", status="closed"), update(row, 3)])
    elif fault.startswith("note_"):
        rows.append(update(row, 2, **{"empty": {"text": " "}, "long": {"text": "x" * 1001}, "extra": {"extra": 1}}[fault[5:]]))
    elif fault == "status_extra":
        rows.append(update(row, 2, "status", extra=1))
    elif fault == "invalid_status":
        rows.append(update(row, 2, "status", status="paused"))
    elif fault == "reason_long":
        rows.append(update(row, 2, "status", reason="x" * 501))
    text = "".join(json.dumps(r) + "\n" for r in rows)
    if fault == "json_middle":
        text = "{broken}\n" + text
    if fault == "json_final_terminated":
        text += "{broken}\n"
    return text


@pytest.mark.parametrize("fault", FAULTS)
def test_corruption_fails_closed_everywhere(house, fault):
    house.filter()
    house.board.write_text(corrupt_rows(fault))
    before = house.snapshot()
    result = house.cli("read", "--since-seq", 999)
    assert result.returncode == 2 and result.stderr.startswith("board read:")
    result = house.cli("post", "--by", "tony", "--title", "New", "--what", "Read", "--kind", "review")
    assert result.returncode == 2
    for name, data in [("board_read", {"since_seq": 999}),
                       ("board_post", {"title": "New", "what": "Read", "kind": "review"})]:
        refused(house, name, data)
    result, _ = house.pass_()
    assert result["skipped"] is False and result["error"]
    assert house.snapshot() == before


def test_torn_final_line_repaired(house):
    row = opening()
    house.seed([row])
    with house.board.open("a") as stream:
        stream.write('{"record_type":"opening","seq":2,')
    assert len(house.cli_json("read")["entries"]) == 1
    out = house.cli_json("post", "--by", "custodian", "--title", "Next", "--what", "Read", "--kind", "review")
    assert out["seq"] == 2 and len(house.rows()) == 2
    assert bytes_at(house.board).endswith(b"\n")


@pytest.mark.parametrize("committed_count", [0, 1])
def test_complete_unterminated_json_is_ignored_and_overwritten(house, committed_count):
    committed = [opening()] if committed_count else []
    house.seed(committed)
    prefix = bytes_at(house.board)
    tail = opening(committed_count + 1)
    with house.board.open("a") as stream:
        stream.write(json.dumps(tail))
    before = house.snapshot()
    for read in [house.cli_json("read"), ok(house.tool("board_read"))]:
        assert read["board_seq"] == committed_count
        assert [row["opportunity_id"] for row in read["entries"]] == [
            row["opportunity_id"] for row in committed]
    assert house.snapshot() == before
    house.filter()
    house.notice_done()
    house.pass_()
    assert {event["board"]["opportunity_id"] for event in house.matches()} == {
        row["opportunity_id"] for row in committed}
    # Retrying the uncommitted opening must append once, without deduplicating it.
    out = house.cli_json("post", "--by", tail["posted_by"], "--title", tail["title"],
                         "--what", tail["what"], "--kind", tail["kind"])
    assert out["seq"] == committed_count + 1 and "duplicate_of_seq" not in out
    rows = house.rows()
    assert rows[:-1] == committed and len(rows) == committed_count + 1
    assert rows[-1]["opportunity_id"] != tail["opportunity_id"]
    assert bytes_at(house.board).startswith(prefix) and bytes_at(house.board).endswith(b"\n")


def test_cli_concurrent_writers(house):
    def post(i):
        return house.cli("post", "--by", "tony" if i < 5 else "custodian",
                         "--title", f"Concurrent {i}", "--what", "Read", "--kind", "review")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(post, range(10)))
    assert all(r.returncode == 0 for r in results), [r.stderr for r in results]
    rows = house.rows()
    assert [r["seq"] for r in rows] == list(range(1, 11))
    assert len({r["opportunity_id"] for r in rows}) == 10


def test_nonowner_cli_refusals_are_atomic(house):
    row = opening(owner="custodian")
    house.seed([row])
    for command, fields in [("note", ["--text", "No authority"]), ("status", ["--status", "taken"])]:
        before = house.snapshot()
        result = house.cli(command, "--by", "tony", "--id", row["opportunity_id"], *fields)
        assert result.returncode == 2 and result.stderr.startswith(f"board {command}:")
        assert house.snapshot() == before


@pytest.mark.parametrize("record_type", ["note", "status"])
def test_writer_refuses_unknown_opportunity(house, record_type):
    refused(house, "board_post", {"record_type": record_type, "opportunity_id": str(uuid4()),
        **({"text": "Orphan"} if record_type == "note" else {"status": "open"})})


def test_dedup_is_scoped_to_poster(house):
    first = ok(house.post())
    second = ok(house.tool("board_post", {"title": "A draft", "what": "Review a draft", "kind": "review"}, door="beta"))
    assert second["opportunity_id"] != first["opportunity_id"] and second["seq"] == 2
    assert len(house.rows()) == 2


def test_duplicates_do_not_use_open_cap(house):
    first = ok(house.post())
    for i in range(4):
        ok(house.post(title=f"Other {i}"))
    duplicate = ok(house.post())
    assert duplicate["duplicate_of_seq"] == first["seq"] and len(house.rows()) == 5


def test_cli_and_door_writers_share_lock(house):
    def cli_post(i):
        return house.cli_json("post", "--by", "tony", "--title", f"Human {i}", "--what", "Read", "--kind", "review")
    def door_post(i):
        return ok(house.post(title=f"Door {i}"))
    with ThreadPoolExecutor(max_workers=10) as pool:
        jobs = [pool.submit(cli_post, i) for i in range(5)] + [pool.submit(door_post, i) for i in range(5)]
        results = [job.result() for job in jobs]
    assert len(results) == 10
    assert [r["seq"] for r in house.rows()] == list(range(1, 11))
    assert len(house.cli_json("read")["entries"]) == 10


@pytest.mark.parametrize("kind", [" REVIEW ", " ＲＥＶＩＥＷ "])
def test_cli_label_normalization(house, kind):
    result = house.cli_json("post", "--by", " ＴＯＮＹ ", "--title", "  Draft  ", "--what", "Read", "--kind", kind, "--tags", " ＭＥＭＯＲＹ ,memory")
    assert result["owner"] == "tony" and result["tags"] == ["memory"]
    assert house.rows()[0]["title"] == "Draft"
    assert house.rows()[0]["kind"] == "review"


@pytest.mark.parametrize("field,value", [("title", "é" * 120), ("what", "🦙" * 2000)])
def test_limits_count_characters_not_bytes(house, field, value):
    ok(house.post(**{field: value}))
    assert house.rows()[0][field] == value
