"""Independent acceptance tests for the finalized plaza read-cursor r3 spec.

The implementation is exercised through its declared MCP interface and filesystem
boundaries. No private cursor helpers are used, except the supplied reset_tally hook.
Coverage of Testing items: 1 (row equality), 2/5 (message-only gaps), 3 (ranges),
4 (status), 6/7 (faults and enrichment), 8 (identity), 9 (concurrency),
10 (checkpoint), 11 (torn-tail repair).
"""

import asyncio
import builtins
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

import pytest

from hamutay.assembly.binding import load_members
from hamutay.assembly.ledger import Ledger, LedgerUnavailable
from hamutay.events import StoreUnavailable
from hamutay.plaza import mcp
from hamutay.plaza.pass_ import run_plaza_pass
from hamutay.plaza.read import read_rows
from hamutay.plaza.records import validate_plaza
from hamutay.plaza.send import send

from guests_validation.conftest import house_guests, records, write_members
from .conftest import T0, tool_send
from .test_invariant_9_deployment import _copy_script, _write_executable


COVERAGE_NOTE = (
    "recorded coverage: rows the tool returned and recorded; "
    "not proof they were received or read"
)
STAMP = "2026-10-06T19:00:00Z"


@pytest.fixture(autouse=True)
def isolated_tally():
    # An absent implementation should fail individual behavioral assertions,
    # rather than prevent collection of the independent checkpoint tests.
    try:
        cursor = importlib.import_module("hamutay.plaza.cursor")
    except ModuleNotFoundError as exc:
        if exc.name != "hamutay.plaza.cursor":
            raise
    else:
        cursor.reset_tally()


def _reads(cfg):
    return cfg.plaza.parent / "reads.jsonl"


def _log(cfg):
    path = _reads(cfg)
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _seed(cfg, destinations=("plaza",), *, prefix="seed"):
    """Use the existing shared writer; CLI writes themselves record no reads."""
    return [
        send(cfg, actor="guest:levadura", via="cli", to=destination,
             text=f"{prefix}-{index}", key=f"{prefix}-{index}", now=T0)
        for index, destination in enumerate(destinations)
    ]


def _read_record(rows, *, label="guest:levadura", at=STAMP, seqs=None):
    return {
        "record_type": "read", "label": label, "at": at, "via": "mcp",
        "seqs": seqs if seqs is not None else [[rows[0]["seq"], rows[-1]["seq"]]],
        "message_ids": [row["message_id"] for row in rows],
    }


def _put_log(cfg, *entries):
    _reads(cfg).write_text("".join(json.dumps(entry) + "\n" for entry in entries))


def _ranges(rows, selected_ids):
    """Independent oracle: adjacency in the message list, never numeric adjacency."""
    result = []
    previous_selected = False
    for row in rows:
        selected = row["message_id"] in selected_ids
        if selected:
            if previous_selected:
                result[-1][1] = row["seq"]
            else:
                result.append([row["seq"], row["seq"]])
        previous_selected = selected
    return result


def _assert_read_record(record, rows, all_rows):
    assert record["record_type"] == "read"
    assert record["via"] == "mcp"
    assert record["label"].startswith("guest:")
    assert datetime.fromisoformat(record["at"]).tzinfo is not None
    assert record["message_ids"] == [row["message_id"] for row in rows]
    assert record["seqs"] == _ranges(all_rows, set(record["message_ids"]))


def _assert_durable_result(cfg, result):
    assert result["sent"] is True
    row = next(row for row in read_rows(cfg) if row["message_id"] == result["message_id"])
    assert row["seq"] == result.get("duplicate_of_seq", result.get("seq"))
    return row


def _deny_cursor_io(monkeypatch, cfg, *, reading=False, writing=False):
    """Inject OS-style faults without depending on the cursor's file-I/O choices."""
    target = _reads(cfg).resolve()

    def is_target(path):
        return isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).resolve() == target

    def wrapper(original):
        def checked(file, mode="r", *args, **kwargs):
            writable = any(char in mode for char in "wax+")
            readable = "r" in mode or "+" in mode
            if is_target(file) and ((writing and writable) or (reading and readable)):
                raise PermissionError("injected read-log permission failure")
            return original(file, mode, *args, **kwargs)
        return checked

    monkeypatch.setattr(builtins, "open", wrapper(builtins.open))
    monkeypatch.setattr(io, "open", wrapper(io.open))
    original_os_open = os.open

    def checked_os_open(path, flags, *args, **kwargs):
        access = flags & os.O_ACCMODE
        writable = access in (os.O_WRONLY, os.O_RDWR)
        readable = access in (os.O_RDONLY, os.O_RDWR)
        if is_target(path) and ((writing and writable) or (reading and readable)):
            raise PermissionError("injected read-log permission failure")
        return original_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", checked_os_open)


@contextmanager
def _held_read_lock(cfg):
    with _reads(cfg).with_name("reads.jsonl.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _bounded_call(call, *, timeout=4.0):
    outcome = queue.Queue()

    def worker():
        try:
            outcome.put((True, call()))
        except BaseException as exc:
            outcome.put((False, exc))

    thread = threading.Thread(target=worker, daemon=True)
    started = time.monotonic()
    thread.start()
    thread.join(timeout)
    assert not thread.is_alive(), f"call did not finish within {timeout}s"
    success, value = outcome.get_nowait()
    if not success:
        raise value
    return value, time.monotonic() - started


@pytest.mark.parametrize("log_state", ["absent", "present", "unwritable"])
@pytest.mark.parametrize("options", [
    {}, {"since_seq": 2, "through_seq": 5}, {"posts_only": True},
    {"since_seq": 2, "through_seq": 5, "posts_only": True}, {"since_seq": 99},
])
def test_read_rows_are_unchanged_by_recording(house_guests, monkeypatch, log_state, options):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "elder", "plaza", "elder", "plaza"))
    all_rows = read_rows(cfg)
    expected = read_rows(cfg, **options)
    if log_state != "absent":
        _put_log(cfg, _read_record(all_rows[:1], label="guest:yupi"))
    before = _reads(cfg).read_bytes() if _reads(cfg).exists() else b""
    if log_state == "unwritable":
        _deny_cursor_io(monkeypatch, cfg, writing=True)
    actual = mcp.plaza_read_impl(root, "levadura", **options)
    assert actual == expected
    assert isinstance(actual, list)
    after = _reads(cfg).read_bytes() if _reads(cfg).exists() else b""
    if not expected or log_state == "unwritable":
        assert after == before
    else:
        assert after.startswith(before)
        assert len(_log(cfg)) == (1 if log_state == "absent" else 2)
        _assert_read_record(_log(cfg)[-1], expected, all_rows)


def test_directed_and_repair_delivery_seqs_do_not_close_bounded_read_gaps(house_guests):
    root, cfg, binding = house_guests
    _seed(cfg, ("plaza", "elder"))

    def offline(path, event, *, timeout_s=2.0):
        raise StoreUnavailable("offline for repair test")

    pending = tool_send(cfg, land=offline)
    _seed(cfg, prefix="after-pending")
    repaired, _ = run_plaza_pass(binding, now=T0)
    assert repaired["landed"] == [pending["message_id"]]
    _seed(cfg, ("elder",), prefix="after-repair")
    assert [row["seq"] for row in read_rows(cfg)] == [1, 2, 4, 6, 8]
    assert [row["seq"] for row in records(cfg) if row["record_type"] == "delivery"] == [3, 5, 7, 9]

    rows = mcp.plaza_read_impl(root, "levadura", since_seq=2, through_seq=7, posts_only=True)
    assert [row["seq"] for row in rows] == [6]
    assert _log(cfg)[-1]["seqs"] == [[6, 6]]
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["latest_seq"] == 8  # The final ledger seq is a delivery, 9.
    assert status["unshown"] == [[1, 4], [8, 8]]
    rows = mcp.plaza_read_impl(root, "levadura", since_seq=3, through_seq=7)
    assert [row["seq"] for row in rows] == [4, 6]
    assert _log(cfg)[-1]["seqs"] == [[4, 6]]
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == [[1, 2], [8, 8]]
    mcp.plaza_read_impl(root, "levadura")
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == []


def test_overlapping_adjacent_single_and_out_of_order_reads_merge_across_deliveries(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "elder", "plaza", "elder", "plaza"))
    assert [row["seq"] for row in read_rows(cfg)] == [1, 2, 4, 5, 7]
    cases = [
        (7, 7, [[1, 5]], [[7, 7]]),
        (2, 4, [[1, 1], [5, 5]], [[2, 4]]),
        (4, 5, [[1, 1]], [[4, 5]]),
        (1, 1, [], [[1, 1]]),
    ]
    for since, through, unshown, recorded in cases:
        mcp.plaza_read_impl(root, "levadura", since_seq=since, through_seq=through)
        assert mcp.plaza_status_impl(root, "levadura")["unshown"] == unshown
        assert _log(cfg)[-1]["seqs"] == recorded


def test_fresh_fully_read_and_empty_status_wire_contract(house_guests):
    root, cfg, _ = house_guests
    empty = mcp.plaza_status_impl(root, "levadura")
    assert empty == {
        "label": "guest:levadura", "latest_seq": 0, "unshown": [], "last_read_at": None,
        "recording": {"failures_this_session": 0, "skipped_records": 0},
        "coverage_note": COVERAGE_NOTE,
    }
    assert not _reads(cfg).exists()
    assert mcp.plaza_read_impl(root, "levadura") == []
    assert not _reads(cfg).exists()
    _seed(cfg, ("elder", "plaza", "elder"))
    before = cfg.plaza.read_bytes()
    fresh = mcp.plaza_status_impl(root, "levadura")
    assert fresh["unshown"] == [[1, 4]]
    assert fresh["latest_seq"] == 4
    assert fresh["last_read_at"] is None
    assert cfg.plaza.read_bytes() == before and not _reads(cfg).exists()
    mcp.plaza_read_impl(root, "levadura")
    complete = mcp.plaza_status_impl(root, "levadura")
    assert complete["unshown"] == []
    assert complete["last_read_at"] == _log(cfg)[-1]["at"]


def test_status_reports_only_its_fixed_label_and_takes_no_parameters(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg)
    mcp.plaza_read_impl(root, "levadura")
    assert mcp.plaza_status_impl(root, "yupi")["unshown"] == [[1, 1]]
    assert mcp.plaza_status_impl(root, "yupi")["last_read_at"] is None

    async def exercise():
        server = mcp.build_server(root, "levadura")
        tools = {tool.name: tool for tool in await server.list_tools()}
        assert set(tools) == {"plaza_read", "plaza_post", "plaza_send", "plaza_status"}
        schema = tools["plaza_status"].inputSchema
        assert schema.get("properties", {}) == {}
        assert not schema.get("required")
        response = await server.call_tool("plaza_status", {})
        # FastMCP versions return content blocks, (content, structured data),
        # or a CallToolResult. The cursor spec constrains the JSON body.
        if isinstance(response, tuple):
            contents = response[0]
        elif isinstance(response, list):
            contents = response
        else:
            assert response.isError is False
            contents = response.content
        body = json.loads(next(block.text for block in contents if block.type == "text"))
        assert body["label"] == "guest:levadura"
        assert body["unshown"] == []

    asyncio.run(exercise())


def test_posts_only_leaves_every_skipped_directed_message_unshown(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg, ("elder", "plaza", "elder", "plaza", "elder"))
    assert [row["seq"] for row in mcp.plaza_read_impl(root, "levadura", posts_only=True)] == [3, 6]
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == [[1, 1], [4, 4], [7, 7]]


def test_last_read_at_is_maximum_parsed_label_time_and_empty_reads_do_not_advance_it(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza"))
    rows = read_rows(cfg)
    maximum = "2026-10-06T13:00:00-07:00"  # 20:00Z, later than the next physical line.
    _put_log(cfg,
             _read_record(rows[:1], at=maximum),
             _read_record(rows[1:], at="2026-10-06T19:30:00Z"),
             _read_record(rows, label="guest:yupi", at="2026-10-07T00:00:00Z"),
             _read_record(rows, at="2099-01-01T00:00:00Z", seqs=[[2, 1]]))
    before = _reads(cfg).read_bytes()
    status = mcp.plaza_status_impl(root, "levadura")
    assert datetime.fromisoformat(status["last_read_at"]) == datetime.fromisoformat(maximum)
    assert status["recording"]["skipped_records"] == 1
    assert mcp.plaza_read_impl(root, "levadura", since_seq=3) == []
    assert _reads(cfg).read_bytes() == before
    assert mcp.plaza_status_impl(root, "levadura")["last_read_at"] == status["last_read_at"]


@pytest.mark.parametrize("broken", ["disabled", "malformed_members", "malformed_plaza", "unavailable"])
def test_status_preserves_plaza_fail_closed_errors(house_guests, broken):
    root, cfg, _ = house_guests
    if broken == "disabled":
        write_members(root, plaza=False, guests=["levadura"])
    elif broken == "malformed_members":
        (root / "community/plaza/members.json").write_text("{broken}\n")
    elif broken == "malformed_plaza":
        cfg.plaza.write_text('{"record_type":"unknown","seq":1}\n')
    else:
        cfg.plaza.mkdir()
    with pytest.raises(Exception) as read_error:
        mcp.plaza_read_impl(root, "levadura")
    with pytest.raises(type(read_error.value)):
        mcp.plaza_status_impl(root, "levadura")


def test_failed_recording_is_advisory_tallied_per_label_and_resettable(house_guests, monkeypatch):
    root, cfg, _ = house_guests
    _seed(cfg)
    _put_log(cfg)
    expected = read_rows(cfg)
    _deny_cursor_io(monkeypatch, cfg, writing=True)
    assert mcp.plaza_read_impl(root, "levadura") == expected
    assert mcp.plaza_read_impl(root, "levadura") == expected
    assert mcp.plaza_read_impl(root, "yupi") == expected
    assert mcp.plaza_read_impl(root, "levadura", since_seq=99) == []
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["recording"] == {"failures_this_session": 2, "skipped_records": 0}
    assert status["unshown"] == [[1, 1]]
    assert status["last_read_at"] is None
    assert mcp.plaza_status_impl(root, "yupi")["recording"]["failures_this_session"] == 1
    assert _reads(cfg).read_bytes() == b""
    importlib.import_module("hamutay.plaza.cursor").reset_tally()
    assert mcp.plaza_status_impl(root, "levadura")["recording"]["failures_this_session"] == 0
    assert mcp.plaza_status_impl(root, "yupi")["recording"]["failures_this_session"] == 0
    post = mcp.plaza_post_impl(root, "levadura", "append-only fault is advisory")
    _assert_durable_result(cfg, post)
    assert post["unshown_at_send"] == [[1, 1]]
    directed = mcp.plaza_send_impl(root, "levadura", "elder", "still admitted")
    _assert_durable_result(cfg, directed)
    assert directed["unshown_at_send"] == [[1, post["seq"]]]
    assert "cursor_error" not in post and "cursor_error" not in directed


@pytest.mark.parametrize("method", ["post", "send"])
def test_unreadable_read_log_makes_status_unknown_but_send_stays_accepted(house_guests, monkeypatch, method):
    root, cfg, _ = house_guests
    _seed(cfg)
    _put_log(cfg, _read_record(read_rows(cfg)))
    _deny_cursor_io(monkeypatch, cfg, reading=True, writing=True)
    assert mcp.plaza_read_impl(root, "levadura") == read_rows(cfg)
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["latest_seq"] == 1
    assert status["unshown"] is None
    assert isinstance(status["recording"]["error"], str) and status["recording"]["error"]
    assert status["recording"]["failures_this_session"] == 1
    if method == "post":
        result = mcp.plaza_post_impl(root, "levadura", "durable despite cursor error", key="fault")
        duplicate = mcp.plaza_post_impl(root, "levadura", "durable despite cursor error", key="fault")
    else:
        result = mcp.plaza_send_impl(root, "levadura", "elder", "durable despite cursor error", key="fault")
        duplicate = mcp.plaza_send_impl(root, "levadura", "elder", "durable despite cursor error", key="fault")
    for response in (result, duplicate):
        _assert_durable_result(cfg, response)
        assert response["unshown_at_send"] is None
        assert isinstance(response["cursor_error"], str) and response["cursor_error"]
        assert "refused" not in response
    assert duplicate["duplicate_of_seq"] == result["seq"]
    assert duplicate["message_id"] == result["message_id"]


@pytest.mark.parametrize("field,value", [
    ("record_type", "message"), ("label", "door:qwen"), ("label", "guest:"),
    ("at", "not an instant"), ("seqs", "1-2"), ("seqs", [[1]]),
    ("seqs", [[0, 1]]), ("seqs", [[2, 1]]), ("seqs", [["1", 2]]),
    ("seqs", [[2, 2], [1, 1]]), ("seqs", [[1, 2], [2, 3]]),
    ("message_ids", []), ("message_ids", "not a list"), ("message_ids", [1]),
])
def test_invalid_read_records_are_skipped_and_counted_without_lending_coverage(house_guests, field, value):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza", "plaza"))
    rows = read_rows(cfg)
    invalid = _read_record(rows)
    invalid[field] = value
    _put_log(cfg, _read_record(rows[:1]), invalid)
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["unshown"] == [[2, 3]]
    assert status["recording"]["skipped_records"] == 1
    assert datetime.fromisoformat(status["last_read_at"]) == datetime.fromisoformat(STAMP)
    post = mcp.plaza_post_impl(root, "levadura", "malformed camera records cannot gate a post")
    _assert_durable_result(cfg, post)
    assert post["unshown_at_send"] == [[2, 3]]
    directed = mcp.plaza_send_impl(root, "levadura", "elder", "or a directed send")
    _assert_durable_result(cfg, directed)
    assert directed["unshown_at_send"] == [[2, post["seq"]]]
    assert "cursor_error" not in post and "cursor_error" not in directed
    assert mcp.plaza_read_impl(root, "levadura") == read_rows(cfg)
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == []
    assert mcp.plaza_status_impl(root, "levadura")["recording"]["skipped_records"] == 1


def test_malformed_json_is_skipped_and_unterminated_final_record_is_ignored(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza", "plaza"))
    rows = read_rows(cfg)
    _reads(cfg).write_text(
        json.dumps(_read_record(rows[:1])) + "\n{malformed}\n"
        + json.dumps(_read_record(rows[1:], at="2099-01-01T00:00:00Z"))
    )
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["unshown"] == [[2, 3]]
    assert datetime.fromisoformat(status["last_read_at"]) == datetime.fromisoformat(STAMP)
    assert status["recording"]["skipped_records"] == 1  # Torn final line is ignored.
    post = mcp.plaza_post_impl(root, "levadura", "a torn tail cannot refuse a post")
    _assert_durable_result(cfg, post)
    assert post["unshown_at_send"] == [[2, 3]]
    directed = mcp.plaza_send_impl(root, "levadura", "elder", "a torn tail cannot refuse mail")
    _assert_durable_result(cfg, directed)
    assert directed["unshown_at_send"] == [[2, post["seq"]]]


@pytest.mark.parametrize("fragment", ['{"record_type":"read"', "broken fragment"])
def test_torn_tail_is_isolated_before_next_append_and_counted_as_skipped(house_guests, fragment):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza"))
    _reads(cfg).write_text(fragment)
    assert mcp.plaza_status_impl(root, "levadura")["recording"]["skipped_records"] == 0
    rows = mcp.plaza_read_impl(root, "levadura", since_seq=2, through_seq=2)
    data = _reads(cfg).read_bytes()
    assert data.startswith(fragment.encode() + b"\n") and data.endswith(b"\n")
    lines = data.splitlines()
    assert len(lines) == 2
    _assert_read_record(json.loads(lines[1]), rows, read_rows(cfg))
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["unshown"] == [[1, 1]]
    assert status["recording"]["skipped_records"] == 1
    mcp.plaza_read_impl(root, "levadura", since_seq=1, through_seq=1)
    assert len(_reads(cfg).read_bytes().splitlines()) == 3
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == []
    assert mcp.plaza_status_impl(root, "levadura")["recording"]["skipped_records"] == 1


def test_busy_read_log_lock_is_bounded_and_never_changes_read_rows(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg)
    expected = read_rows(cfg)
    with _held_read_lock(cfg):
        rows, elapsed = _bounded_call(lambda: mcp.plaza_read_impl(root, "levadura"))
        assert rows == expected
        assert elapsed < 3.5  # Spec: bounded 2 s wait, plus scheduling allowance.
        status, _ = _bounded_call(lambda: mcp.plaza_status_impl(root, "levadura"), timeout=1.5)
        assert status["recording"]["failures_this_session"] == 1
        assert status["unshown"] == [[1, 1]]
        assert not _reads(cfg).exists() or _reads(cfg).read_bytes() == b""
    mcp.plaza_read_impl(root, "levadura")
    status = mcp.plaza_status_impl(root, "levadura")
    assert status["unshown"] == [] and status["recording"]["failures_this_session"] == 1


def test_status_and_send_enrichment_do_not_take_the_read_log_lock(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg)
    mcp.plaza_read_impl(root, "levadura")
    before = _reads(cfg).read_bytes()
    with _held_read_lock(cfg):
        status, _ = _bounded_call(lambda: mcp.plaza_status_impl(root, "levadura"), timeout=1.5)
        assert status["unshown"] == []
        post, _ = _bounded_call(lambda: mcp.plaza_post_impl(root, "levadura", "no nested cursor lock"), timeout=1.5)
        _assert_durable_result(cfg, post)
        assert post["unshown_at_send"] == []
        directed, _ = _bounded_call(lambda: mcp.plaza_send_impl(root, "levadura", "elder", "lockless enrichment"), timeout=1.5)
        _assert_durable_result(cfg, directed)
        assert directed["unshown_at_send"] == [[post["seq"], post["seq"]]]
        assert _reads(cfg).read_bytes() == before


@pytest.mark.parametrize("method", ["post", "send"])
def test_success_and_duplicates_are_enriched_relative_to_original_message_seq(house_guests, method):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "elder"))

    def write():
        if method == "post":
            return mcp.plaza_post_impl(root, "levadura", "original", key="same")
        return mcp.plaza_send_impl(root, "levadura", "elder", "original", key="same")

    original = write()
    _assert_durable_result(cfg, original)
    assert original["unshown_at_send"] == [[1, 2]]
    assert "cursor_error" not in original
    later = mcp.plaza_post_impl(root, "levadura", "after original")
    before = cfg.plaza.read_bytes()
    duplicate = write()
    assert duplicate["sent"] is True
    assert duplicate["duplicate_of_seq"] == original["seq"]
    assert duplicate["message_id"] == original["message_id"]
    assert duplicate["unshown_at_send"] == [[1, 2]]
    assert cfg.plaza.read_bytes() == before
    assert later["seq"] > duplicate["duplicate_of_seq"]
    # Coverage is sampled for each response, including a retry after another read.
    mcp.plaza_read_impl(root, "levadura", since_seq=1, through_seq=1)
    duplicate = write()
    assert duplicate["unshown_at_send"] == [[2, 2]]
    assert duplicate["message_id"] == original["message_id"]
    assert cfg.plaza.read_bytes() == before


@pytest.mark.parametrize("method", ["post", "send"])
def test_fresh_plaza_read_failure_after_commit_cannot_turn_success_into_refusal(house_guests, monkeypatch, method):
    root, cfg, _ = house_guests
    _seed(cfg)
    real_lock = Ledger.try_locked
    acquisitions = 0

    def fail_after_write(self, timeout_s):
        nonlocal acquisitions
        acquisitions += 1
        if acquisitions > 1:
            raise LedgerUnavailable("plaza unavailable only after the accepted write")
        return real_lock(self, timeout_s)

    with monkeypatch.context() as scoped:
        scoped.setattr(Ledger, "try_locked", fail_after_write)
        if method == "post":
            result = mcp.plaza_post_impl(root, "levadura", "accepted before read failure")
        else:
            result = mcp.plaza_send_impl(root, "levadura", "elder", "accepted before read failure")
    _assert_durable_result(cfg, result)
    assert acquisitions >= 2
    assert result["unshown_at_send"] is None
    assert isinstance(result["cursor_error"], str) and result["cursor_error"]
    assert "refused" not in result


@pytest.mark.parametrize("method", ["post", "send"])
def test_enrichment_samples_new_coverage_but_excludes_messages_appended_after_commit(house_guests, monkeypatch, method):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza"))
    real_lock = Ledger.try_locked
    acquisitions = 0
    interleaved = []

    def interleave_after_commit(self, timeout_s):
        nonlocal acquisitions
        acquisitions += 1
        if acquisitions == 2:
            # The original write's scope has returned; its enrichment now starts.
            # A later message must be excluded, and this label's intervening read
            # must be included in the coverage sampled for the response.
            interleaved.extend(_seed(cfg, prefix="between-commit-and-enrichment"))
            rows = mcp.plaza_read_impl(root, "levadura", since_seq=1, through_seq=1)
            assert [row["seq"] for row in rows] == [1]
        return real_lock(self, timeout_s)

    with monkeypatch.context() as scoped:
        scoped.setattr(Ledger, "try_locked", interleave_after_commit)
        if method == "post":
            result = mcp.plaza_post_impl(root, "levadura", "original commit")
        else:
            result = mcp.plaza_send_impl(root, "levadura", "elder", "original commit")
    _assert_durable_result(cfg, result)
    assert len(interleaved) == 1 and interleaved[0]["seq"] > result["seq"]
    assert result["unshown_at_send"] == [[2, 2]]
    assert "cursor_error" not in result


@pytest.mark.parametrize("method", ["post", "send"])
@pytest.mark.parametrize("reason", ["not_admitted", "bad_text", "conflicting_key"])
def test_refusals_gain_no_cursor_metadata_and_write_nothing(house_guests, method, reason):
    root, cfg, _ = house_guests

    def write(text):
        if method == "post":
            return mcp.plaza_post_impl(root, "levadura", text, key="refusal")
        return mcp.plaza_send_impl(root, "levadura", "elder", text, key="refusal")

    assert write("held")["sent"] is True
    if reason == "not_admitted":
        write_members(root, plaza=True, guests=[])
        text = "held"
    elif reason == "bad_text":
        text = ""
    else:
        text = "different words"
    before = cfg.plaza.read_bytes()
    response = write(text)
    assert response["sent"] is False
    assert "unshown_at_send" not in response and "cursor_error" not in response
    assert cfg.plaza.read_bytes() == before
    assert not _reads(cfg).exists()


def test_coverage_is_message_identity_even_when_recorded_ranges_claim_other_seqs(house_guests):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza", "plaza"))
    rows = read_rows(cfg)
    _put_log(cfg, _read_record(rows[1:2], seqs=[[1, 9999]]))
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == [[1, 1], [3, 3]]
    assert mcp.plaza_status_impl(root, "levadura")["recording"]["skipped_records"] == 0


def test_replaced_plaza_does_not_inherit_another_historys_coverage(house_guests, tmp_path):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza"), prefix="history-a")
    a = mcp.plaza_read_impl(root, "levadura")
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == []
    other = tmp_path / "history-b"
    write_members(other, plaza=True, guests=["levadura"])
    other_cfg = load_members(other)
    _seed(other_cfg, ("plaza", "plaza"), prefix="history-b")
    cfg.plaza.write_bytes(other_cfg.plaza.read_bytes())
    assert not {row["message_id"] for row in a}.intersection(row["message_id"] for row in read_rows(cfg))
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == [[1, 2]]
    mcp.plaza_read_impl(root, "levadura", since_seq=2)
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == [[1, 1]]


def test_restored_shared_prefix_keeps_only_ids_that_actually_survived(house_guests, tmp_path):
    root, cfg, _ = house_guests
    _seed(cfg, ("plaza", "plaza"), prefix="before-restore")
    original = records(cfg)
    mcp.plaza_read_impl(root, "levadura")
    other = tmp_path / "replacement-message"
    write_members(other, plaza=True, guests=["levadura"])
    other_cfg = load_members(other)
    _seed(other_cfg, prefix="restored-new-message")
    replacement = dict(records(other_cfg)[0], seq=2)
    assert replacement["message_id"] != original[1]["message_id"]
    cfg.plaza.write_text(json.dumps(original[0]) + "\n" + json.dumps(replacement) + "\n")
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == [[2, 2]]
    mcp.plaza_read_impl(root, "levadura", since_seq=2, through_seq=2)
    assert mcp.plaza_status_impl(root, "levadura")["unshown"] == []


@pytest.mark.parametrize("labels", [("levadura", "yupi", "levadura", "yupi"), ("levadura",) * 4],
                         ids=["two-labels", "same-label"])
def test_interleaved_reads_status_and_posts_finish_with_coherent_coverage(house_guests, labels):
    root, _, _ = house_guests
    write_members(root, plaza=True, guests=["levadura", "yupi"])
    cfg = load_members(root)
    _seed(cfg, ("plaza", "elder", "plaza"))
    start = threading.Barrier(len(labels))
    outcomes = queue.Queue()

    def exercise(index, label):
        returned = []
        try:
            start.wait(timeout=5)
            for step in range(8):
                rows = mcp.plaza_read_impl(root, label, since_seq=1 + step % 3, posts_only=bool(step % 2))
                if rows:
                    returned.append((f"guest:{label}", tuple(row["message_id"] for row in rows)))
                status = mcp.plaza_status_impl(root, label)
                assert status["label"] == f"guest:{label}"
                assert status["recording"]["failures_this_session"] == 0
                post = mcp.plaza_post_impl(root, label, f"worker {index}, step {step}", key=f"worker-{index}-{step}")
                assert post["sent"] is True and post["unshown_at_send"] is not None
                assert all(end < post["seq"] for _, end in post["unshown_at_send"])
            outcomes.put((returned, None))
        except BaseException as exc:
            outcomes.put((returned, exc))

    workers = [threading.Thread(target=exercise, args=(index, label), daemon=True)
               for index, label in enumerate(labels)]
    for worker in workers:
        worker.start()
    deadline = time.monotonic() + 20
    for worker in workers:
        worker.join(max(0, deadline - time.monotonic()))
    assert all(not worker.is_alive() for worker in workers), "deadlock among read, status and post"
    expected = Counter()
    for _ in workers:
        returned, error = outcomes.get_nowait()
        assert error is None, repr(error)
        expected.update(returned)
    data = _reads(cfg).read_bytes()
    assert data.endswith(b"\n")
    read_log = _log(cfg)
    assert Counter((entry["label"], tuple(entry["message_ids"])) for entry in read_log) == expected
    ledger = records(cfg)
    validate_plaza(ledger, list(range(1, len(ledger) + 1)))
    rows = read_rows(cfg)
    by_id = {row["message_id"]: row for row in rows}
    for entry in read_log:
        _assert_read_record(entry, [by_id[identity] for identity in entry["message_ids"]], rows)
    for label in set(labels):
        covered = {identity for entry in read_log if entry["label"] == f"guest:{label}"
                   for identity in entry["message_ids"]}
        status = mcp.plaza_status_impl(root, label)
        assert status["latest_seq"] == rows[-1]["seq"]
        assert status["unshown"] == _ranges(rows, set(by_id) - covered)
        assert status["recording"] == {"failures_this_session": 0, "skipped_records": 0}


@pytest.fixture
def checkpoint_harness(tmp_path):
    """Use the frozen deployment test's lock shim, without initializing a repo.

    Copy and execute the script as a black box; do not inspect its implementation.
    The git shim provides discovery and clean-index checks, refusing mutations. No real git
    executable is invoked by this harness or by the script it runs.
    """
    root = tmp_path / "checkpoint-house"
    root.mkdir()
    script = _copy_script(root, "checkpoint-community-log.sh")
    plaza = root / "community/plaza"
    plaza.mkdir(parents=True)
    fakebin = tmp_path / "checkpoint-bin"
    fakebin.mkdir()
    lock_log = tmp_path / "locks.log"
    marker = tmp_path / "lock-held"
    _write_executable(
        fakebin / "flock",
        '#!/bin/sh\n'
        'if [ -e "$LOCK_MARKER" ]; then echo nested >> "$LOCK_LOG"; exit 99; fi\n'
        'lock=$1; shift\n'
        'echo "begin:$lock" >> "$LOCK_LOG"\n'
        'echo "$lock" > "$LOCK_MARKER"\n'
        '"$@"\n'
        'rc=$?\n'
        'rm -f "$LOCK_MARKER"\n'
        'echo "end:$lock" >> "$LOCK_LOG"\n'
        'case "$lock" in *reads.jsonl.lock)\n'
        '  if [ "$MUTATE_READS_AFTER_UNLOCK" = yes ]; then\n'
        '    echo "changed after snapshot release" > community/plaza/reads.jsonl\n'
        '  fi;; esac\n'
        'exit $rc\n',
    )
    _write_executable(
        fakebin / "cp",
        '#!/bin/sh\n'
        'for source in "$@"; do\n'
        '  case "$source" in *community/plaza/*.jsonl)\n'
        '    if [ ! -f "$LOCK_MARKER" ] || [ "$(cat "$LOCK_MARKER")" != "$source.lock" ]; then\n'
        '      echo "snapshot copied outside its own lock: $source" >&2; exit 98\n'
        '    fi;; esac\n'
        'done\n'
        'exec /bin/cp "$@"\n',
    )
    _write_executable(fakebin / "date", '#!/bin/sh\necho "$CHECKPOINT_STAMP"\n')
    _write_executable(
        fakebin / "git",
        '#!/bin/sh\n'
        'case "$*" in\n'
        '  *rev-parse*--show-toplevel*) echo "$CHECKPOINT_ROOT";;\n'
        '  *rev-parse*--git-dir*) echo .git;;\n'
        '  *rev-parse*--is-inside-work-tree*) echo true;;\n'
        '  *diff*--cached*--quiet*) exit 0;;\n'
        '  *) echo "unexpected git command blocked by test shim: $*" >&2; exit 97;;\n'
        'esac\n',
    )
    environment = dict(os.environ,
        PATH=f"{fakebin}:{os.environ['PATH']}",
        LOCK_LOG=str(lock_log), LOCK_MARKER=str(marker),
        AYLLU_STATE_DIR=str(tmp_path / "state"),
        CHECKPOINT_ROOT=str(root), CHECKPOINT_STAMP=STAMP,
        MUTATE_READS_AFTER_UNLOCK="no",
    )

    def run(*, mutate_reads=False):
        completed = subprocess.run(
            ["bash", str(script), "--no-commit", "--root", str(root)],
            capture_output=True, text=True,
            env=dict(environment, MUTATE_READS_AFTER_UNLOCK="yes" if mutate_reads else "no"),
            timeout=15,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        return (plaza / "CHECKPOINTS.txt").read_bytes(), lock_log.read_text().splitlines()

    return plaza, run


def _checkpoint_field(name, data):
    return f"{name}:{hashlib.sha256(data).hexdigest()}:{len(data)}"


@pytest.mark.parametrize("include_reads", [False, True], ids=["legacy-output", "third-scope"])
def test_checkpoint_preserves_old_bytes_and_adds_a_separate_conditional_scope(checkpoint_harness, include_reads):
    plaza, run = checkpoint_harness
    assembly = b'{"seq":1}\n'
    messages = b'{"seq":1,"record_type":"message"}\n'
    reads = (json.dumps({"record_type": "read", "label": "guest:levadura",
                         "at": STAMP, "via": "mcp", "seqs": [[1, 1]],
                         "message_ids": ["checkpoint-only-identity"]}) + "\n").encode()
    (plaza / "assembly.jsonl").write_bytes(assembly)
    (plaza / "plaza.jsonl").write_bytes(messages)
    if include_reads:
        (plaza / "reads.jsonl").write_bytes(reads)
    output, scopes = run()
    expected_fields = [_checkpoint_field("assembly.jsonl", assembly), _checkpoint_field("plaza.jsonl", messages)]
    expected_scopes = [
        "begin:community/plaza/assembly.jsonl.lock", "end:community/plaza/assembly.jsonl.lock",
        "begin:community/plaza/plaza.jsonl.lock", "end:community/plaza/plaza.jsonl.lock",
    ]
    if include_reads:
        expected_fields.append(_checkpoint_field("reads.jsonl", reads))
        expected_scopes += ["begin:community/plaza/reads.jsonl.lock", "end:community/plaza/reads.jsonl.lock"]
    assert output == (STAMP + " " + " ".join(expected_fields) + "\n").encode()
    assert scopes == expected_scopes
    assert b"guest:levadura" not in output and b"checkpoint-only-identity" not in output
    if not include_reads:
        assert not (plaza / "reads.jsonl.lock").exists()


def test_checkpoint_guard_includes_a_directory_holding_only_the_read_log(checkpoint_harness):
    plaza, run = checkpoint_harness
    data = b'{"record_type":"read","label":"guest:levadura"}\n'
    (plaza / "reads.jsonl").write_bytes(data)
    output, scopes = run()
    assert output == (STAMP + " " + _checkpoint_field("reads.jsonl", data) + "\n").encode()
    assert scopes == ["begin:community/plaza/reads.jsonl.lock", "end:community/plaza/reads.jsonl.lock"]


def test_checkpoint_digest_and_size_belong_to_the_locked_read_log_snapshot(checkpoint_harness):
    plaza, run = checkpoint_harness
    data = b'{"label":"guest:levadura","snapshot":"before release"}\n'
    (plaza / "reads.jsonl").write_bytes(data)
    output, scopes = run(mutate_reads=True)
    assert (plaza / "reads.jsonl").read_bytes() == b"changed after snapshot release\n"
    assert output == (STAMP + " " + _checkpoint_field("reads.jsonl", data) + "\n").encode()
    assert scopes == ["begin:community/plaza/reads.jsonl.lock", "end:community/plaza/reads.jsonl.lock"]
