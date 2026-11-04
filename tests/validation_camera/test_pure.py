"""Blind contract tests for camera r6; no root, services, or database.

Imports are deliberately deferred to fixture setup so the absent implementation
reports an import error for each case and the root tests can still report skips.
See ASSUMPTIONS.md for the few contracts r6 leaves open.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import stat
from types import SimpleNamespace

import pytest


UTC = timezone.utc
T = datetime(2026, 11, 3, 12, 34, 10, 123456, tzinfo=UTC)
GEN = "019a4871-1000-7000-8000-000000000001"
GEN2 = "019a4871-1000-7000-8000-000000000002"
MANAGER = "/user.slice/user-1000.slice/user@1000.service/"
CGROUP = MANAGER + r"app.slice/app-hamutay\x2dheartbeat.slice/hamutay-heartbeat@elder.service"
HOMES = {"elder": "/h/community/elder", "fable": "/h/community/fable"}


@pytest.fixture
def camera():
    # Import every public interface named by r6, without supplying a substitute.
    from hamutay.camera import (
        Coalescer, GateTracker, Spool, attribution_state, coverage_version,
        encode_message, is_self_read, read_reader, scribe_gap_on_start,
        split_coverage, window_of,
    )

    return SimpleNamespace(**locals())


def reader(**changes):
    result = {
        "pid": 42, "start_time": 123456, "reused": False, "uid": 1000,
        "exe": "/usr/bin/cat", "comm": "cat", "cgroup": CGROUP,
        "cwd": "/h/community/elder", "ancestors": [],
        "proc_readable": True, "start_time_before": 123456,
        "start_time_after": 123456, "attribution": "complete",
    }
    result.update(changes)
    return result


def opened(*, t=T, seq=0, gen=GEN, path="/h/community/elder/note", **changes):
    result = {
        "v": 1, "kind": "open", "gen": gen, "seq": seq, "t": t,
        "path": path, "path_sha256": hashlib.sha256(path.encode()).hexdigest(),
        "door": "elder", "reader": reader(), "truncated": False,
    }
    result.update(changes)
    return result


def beat(*, t=T, seq=0, gen=GEN, **changes):
    result = {
        "v": 1, "kind": "beat", "gen": gen, "seq": seq, "t": t,
        "opened": 7, "self_reads": 2, "answered": 7, "dropped": 1,
        "coverage_version": "a" * 64, "marks_count": 2,
    }
    result.update(changes)
    return result


@pytest.mark.parametrize("cgroup", [
    CGROUP,
    MANAGER + "app.slice/hamutay-heartbeat@elder.service",
    MANAGER + "hamutay-heartbeat@elder.service",
])
def test_is_self_read_accepts_manager_prefix_and_exact_last_component(camera, cgroup):
    assert camera.is_self_read(reader(cgroup=cgroup), HOMES["elder"] + "/note", HOMES) is True


@pytest.mark.parametrize("changes,path", [
    ({"uid": 0}, "/h/community/elder/note"),
    ({"uid": 1001}, "/h/community/elder/note"),
    ({"cgroup": CGROUP.replace("user-1000.slice", "user-1001.slice")}, "/h/community/elder/note"),
    ({"cgroup": CGROUP.replace("user@1000", "user@1001")}, "/h/community/elder/note"),
    ({"cgroup": "/other" + CGROUP}, "/h/community/elder/note"),
    ({"cgroup": CGROUP + "/child.scope"}, "/h/community/elder/note"),
    ({"cgroup": CGROUP + ".extra"}, "/h/community/elder/note"),
    ({"cgroup": CGROUP.replace("@elder", "@fable")}, "/h/community/elder/note"),
    ({"cgroup": MANAGER + "app.slice/hamutay-viewer.service"}, "/h/community/elder/note"),
    ({"cgroup": MANAGER + "app.slice/llama-server.service"}, "/h/community/elder/note"),
    ({"cgroup": MANAGER + "session-1.scope"}, "/h/community/elder/note"),
    ({}, "/h/community/fable/note"),
    ({}, "/h/community/elder-copy/note"),
    ({}, "/other/community/elder/note"),
    ({}, "/h/community/unknown/note"),
])
def test_is_self_read_rejects_wrong_identity_unit_or_home(camera, changes, path):
    assert camera.is_self_read(reader(**changes), path, HOMES) is False


@pytest.mark.parametrize("field", ["pid", "uid", "cgroup", "exe", "comm", "cwd", "start_time"])
@pytest.mark.parametrize("missing", [True, False], ids=["absent", "null"])
def test_is_self_read_never_exempts_incomplete_attribution(camera, field, missing):
    r = reader()
    if missing:
        r.pop(field)
    else:
        r[field] = None
    assert camera.is_self_read(r, HOMES["elder"] + "/note", HOMES) is False


def test_is_self_read_rejects_unknown_home_and_reused_reader(camera):
    assert camera.is_self_read(reader(), HOMES["elder"] + "/note", {}) is False
    assert camera.is_self_read(reader(reused=True, attribution="partial"), HOMES["elder"] + "/note", HOMES) is False


def proc_stat(pid, parent, start, comm="cat"):
    # Fields 3..52; deliberately different numbers make off-by-one errors visible.
    tail = ["S", str(parent)] + [str(9000 + n) for n in range(5, 53)]
    tail[22 - 3] = str(start)
    return f"{pid} ({comm}) " + " ".join(tail) + "\n"


def make_pid(root, pid=42, parent=1, start=123456, comm="cat"):
    d = root / str(pid)
    d.mkdir(parents=True)
    (d / "stat").write_text(proc_stat(pid, parent, start, comm))
    (d / "status").write_text("Name:\tcat\nUid:\t1000\t2000\t3000\t4000\n")
    (d / "comm").write_text(comm + "\n")
    (d / "cgroup").write_text("7:cpu:/wrong/legacy\n0::" + CGROUP + "\n")
    # readlink must work even when the targets do not exist in the fixture.
    (d / "exe").symlink_to("/usr/bin/cat")
    (d / "cwd").symlink_to("/h/community/elder")
    return d


def test_read_reader_complete_snapshot_real_uid_and_symlinks(camera, tmp_path):
    make_pid(tmp_path)
    got = camera.read_reader(42, proc_root=tmp_path)
    for key, value in reader().items():
        assert got[key] == value, key
    assert "cmdline" not in got and "environ" not in got


@pytest.mark.parametrize("comm", ["reader with spaces", "a (reader) with ) and ( parens)"])
def test_read_reader_stat_comm_uses_final_closing_parenthesis(camera, tmp_path, comm):
    make_pid(tmp_path, parent=17, start=887766, comm=comm)
    make_pid(tmp_path, pid=17, start=111)
    got = camera.read_reader(42, proc_root=tmp_path)
    assert got["start_time"] == got["start_time_before"] == got["start_time_after"] == 887766
    assert got["comm"] == comm
    assert got["ancestors"][0]["pid"] == 17
    assert got["attribution"] == "complete"


@pytest.mark.parametrize("filename,field", [
    ("stat", "start_time"), ("status", "uid"), ("exe", "exe"),
    ("comm", "comm"), ("cgroup", "cgroup"), ("cwd", "cwd"),
])
def test_read_reader_missing_file_is_null_and_partial(camera, tmp_path, filename, field):
    d = make_pid(tmp_path)
    (d / filename).unlink()
    got = camera.read_reader(42, proc_root=tmp_path)
    assert got["proc_readable"] is True
    assert got[field] is None
    assert got["attribution"] == "partial"


def test_read_reader_missing_pid_is_lost(camera, tmp_path):
    got = camera.read_reader(404, proc_root=tmp_path)
    assert got["pid"] == 404
    assert got["proc_readable"] is False
    assert got["attribution"] == "lost"
    for field in ("start_time", "start_time_before", "start_time_after", "uid", "exe", "comm", "cgroup", "cwd"):
        assert got[field] is None
    assert got["ancestors"] == []


def test_read_reader_unreadable_file_is_null_and_partial(camera, tmp_path):
    p = make_pid(tmp_path) / "cgroup"
    p.chmod(0)
    try:
        got = camera.read_reader(42, proc_root=tmp_path)
        assert got["cgroup"] is None
        assert got["uid"] == 1000
        assert got["proc_readable"] is True
        assert got["attribution"] == "partial"
    finally:
        p.chmod(0o600)


def test_read_reader_unreadable_pid_directory_is_lost(camera, tmp_path):
    d = make_pid(tmp_path)
    d.chmod(0)
    try:
        # No sudo: these fixtures are expressly for an ordinary user.
        assert os.geteuid() != 0, "run the pure tests as the house user"
        got = camera.read_reader(42, proc_root=tmp_path)
        assert got["proc_readable"] is False
        assert got["attribution"] == "lost"
    finally:
        d.chmod(0o700)


def test_read_reader_between_revalidates_pid_identity(camera, tmp_path):
    d = make_pid(tmp_path)
    calls = []

    def between():
        calls.append(True)
        (d / "stat").write_text(proc_stat(42, 1, 999999))

    got = camera.read_reader(42, proc_root=tmp_path, between=between)
    assert calls == [True]
    assert got["start_time_before"] == got["start_time"] == 123456
    assert got["start_time_after"] == 999999
    assert got["reused"] is True
    assert got["attribution"] == "partial"


def test_read_reader_disappearing_between_stat_reads_is_partial(camera, tmp_path):
    d = make_pid(tmp_path)
    got = camera.read_reader(42, proc_root=tmp_path, between=lambda: (d / "stat").unlink())
    assert got["start_time_before"] == 123456
    assert got["start_time_after"] is None
    assert got["attribution"] == "partial"


@pytest.mark.parametrize("stop", ["pid1", "missing", "unreadable", "four_levels"])
def test_read_reader_ancestor_chain_is_nearest_first_and_bounded(camera, tmp_path, stop):
    chain = [42, 40, 30, 20, 10, 5, 1]
    for i, pid in enumerate(chain):
        make_pid(tmp_path, pid=pid, parent=chain[i + 1] if i + 1 < len(chain) else 0, start=pid * 100)
    blocked = tmp_path / "30"
    if stop == "pid1":
        (tmp_path / "40/stat").write_text(proc_stat(40, 1, 4000))
    elif stop == "missing":
        (blocked / "stat").unlink()
    elif stop == "unreadable":
        blocked.chmod(0)
    try:
        got = camera.read_reader(42, proc_root=tmp_path)
    finally:
        blocked.chmod(0o700)
    want = [40, 30, 20, 10] if stop == "four_levels" else [40]
    assert got["ancestors"] == [
        {"pid": pid, "start_time": pid * 100, "exe": "/usr/bin/cat", "comm": "cat"}
        for pid in want
    ]
    assert got["attribution"] == "complete"


def test_attribution_state_complete_without_ancestors(camera):
    assert camera.attribution_state(reader()) == "complete"


@pytest.mark.parametrize("field", ["uid", "exe", "comm", "cgroup", "cwd", "start_time_before", "start_time_after"])
def test_attribution_state_any_null_required_field_is_partial(camera, field):
    assert camera.attribution_state(reader(**{field: None})) == "partial"


def test_attribution_state_changed_identity_is_partial(camera):
    assert camera.attribution_state(reader(start_time_after=123457)) == "partial"


def test_attribution_state_unreadable_proc_takes_precedence(camera):
    assert camera.attribution_state(reader(proc_readable=False)) == "lost"


def test_attribution_state_equal_missing_start_times_are_partial(camera):
    assert camera.attribution_state(reader(start_time_before=None, start_time_after=None)) == "partial"


def test_attribution_state_accepts_readable_falsy_fields(camera):
    assert camera.attribution_state(reader(uid=0, comm="", cwd="")) == "complete"


@pytest.mark.parametrize("t,want", [
    (T, datetime(2026, 11, 3, 12, 34, tzinfo=UTC)),
    (datetime(2026, 11, 3, 12, 34, 59, 999999, tzinfo=UTC), datetime(2026, 11, 3, 12, 34, tzinfo=UTC)),
    (datetime(2026, 11, 3, 12, 35, tzinfo=UTC), datetime(2026, 11, 3, 12, 35, tzinfo=UTC)),
    (datetime(2026, 11, 4, tzinfo=UTC), datetime(2026, 11, 4, tzinfo=UTC)),
])
def test_window_of_floors_to_utc_minute(camera, t, want):
    assert camera.window_of(t) == want


def compact(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()


def decoded(camera, msg):
    raw = camera.encode_message(msg)
    assert isinstance(raw, bytes)
    assert len(raw) <= 8192
    result = json.loads(raw.decode("utf-8"))
    assert raw in (compact(result), json.dumps(result, separators=(",", ":"), ensure_ascii=True).encode())
    return result


def test_encode_message_preserves_small_message_and_utc_timestamp(camera):
    msg = opened(path="/h/community/elder/qué 🦙")
    got = decoded(camera, msg)
    expected = deepcopy(msg)
    expected["t"] = got["t"]
    assert got == expected
    assert datetime.fromisoformat(got["t"]) == T
    assert ".123456" in got["t"]


@pytest.mark.parametrize("size", [8191, 8192, 8193])
def test_encode_message_non_open_exact_byte_limit(camera, size):
    msg = beat(t=T.isoformat(), padding="")
    msg["padding"] = "x" * (size - len(compact(msg)))
    assert len(compact(msg)) == size
    if size > 8192:
        with pytest.raises(ValueError):
            camera.encode_message(msg)
    else:
        assert camera.encode_message(msg) == compact(msg)


@pytest.mark.parametrize("kind", ["beat", "coverage", "unknown"])
def test_encode_message_never_truncates_non_open_kinds(camera, kind):
    with pytest.raises(ValueError):
        camera.encode_message({"v": 1, "kind": kind, "gen": GEN, "seq": 0, "padding": "é" * 8192})


def test_encode_message_removes_ancestors_from_end_before_paths(camera):
    msg = opened()
    msg["reader"]["ancestors"] = [
        {"pid": i, "start_time": i, "exe": "/" + str(i) * 2900, "comm": str(i)}
        for i in (1, 2, 3)
    ]
    got = decoded(camera, msg)
    assert got["truncated"] is True
    assert got["reader"]["ancestors"] == msg["reader"]["ancestors"][:2]
    assert got["path"] == msg["path"]
    assert got["reader"]["cwd"] == msg["reader"]["cwd"]
    assert got["path_sha256"] == msg["path_sha256"]


def test_encode_message_cuts_path_from_left_after_all_ancestors(camera):
    msg = opened(path="/" + "é🦙" * 3000 + "/unique-tail")
    msg["reader"]["ancestors"] = [{"pid": 1, "start_time": 1, "exe": "/bin/init", "comm": "init"}]
    got = decoded(camera, msg)
    assert got["truncated"] is True
    assert got["reader"]["ancestors"] == []
    assert got["path"] != msg["path"] and msg["path"].endswith(got["path"])
    assert got["path"].endswith("/unique-tail")
    assert got["reader"]["cwd"] == msg["reader"]["cwd"]
    assert got["path_sha256"] == hashlib.sha256(msg["path"].encode()).hexdigest()


def test_encode_message_cuts_cwd_from_left_when_path_cannot_suffice(camera):
    msg = opened(path="/h/community/elder/tail")
    msg["reader"]["cwd"] = "/" + "界" * 6000 + "/cwd-tail"
    got = decoded(camera, msg)
    assert got["truncated"] is True
    assert got["reader"]["cwd"] != msg["reader"]["cwd"]
    assert msg["reader"]["cwd"].endswith(got["reader"]["cwd"])
    assert got["reader"]["cwd"].endswith("/cwd-tail")
    assert got["path_sha256"] == msg["path_sha256"]


def test_coverage_version_exact_spec_vector(camera):
    marks = [[66, 1001, "/h/community/elder"], [66, 1002, "/h/community/fable"]]
    unmarked = [["/h/community/x", "not_a_directory"]]
    assert camera.coverage_version(marks, unmarked) == "fffdbb29a61c16a2e906a95b6f2c3304f89c2685816fe0c32b2afbf51d0dfae8"
    assert camera.coverage_version(marks[::-1], unmarked) == "fffdbb29a61c16a2e906a95b6f2c3304f89c2685816fe0c32b2afbf51d0dfae8"


def test_coverage_version_canonical_utf8_sorting_and_both_lists(camera):
    marks = [[2, 9, "/界"], [1, 3, "/é"]]
    unmarked = [["/z", "limit"], ["/á", "not_a_directory"]]
    canonical = json.dumps({"marks": sorted(marks), "unmarked": sorted(unmarked)}, separators=(",", ":"), ensure_ascii=False, sort_keys=True).encode("utf-8")
    assert camera.coverage_version(marks, unmarked) == hashlib.sha256(canonical).hexdigest()
    assert camera.coverage_version(marks, unmarked) != camera.coverage_version(marks, unmarked[:1])


@pytest.mark.parametrize("n_marks,n_unmarked", [(0, 0), (2, 1), (300, 300), (0, 400), (400, 0)])
def test_split_coverage_full_envelopes_fit_and_round_trip(camera, n_marks, n_unmarked):
    marks = [[66, i, f"/h/community/界/{i:04}/" + "m" * 120] for i in reversed(range(n_marks))]
    unmarked = [[f"/h/community/é/{i:04}/" + "u" * 120, "limit"] for i in reversed(range(n_unmarked))]
    parts = camera.split_coverage(marks, unmarked, gen=GEN, seq_start=999998, t=T)
    assert parts  # Even empty coverage must be announceable as a complete version.
    if n_marks + n_unmarked >= 300:
        assert len(parts) > 1
    all_marks, all_unmarked = [], []
    seen_unmarked = False
    for i, part in enumerate(parts):
        assert part["v"] == 1 and part["kind"] == "coverage"
        assert part["gen"] == GEN and part["seq"] == 999998 + i
        assert part["t"] == T
        assert part["part"] == i and part["parts"] == len(parts)
        assert part["coverage_version"] == camera.coverage_version(marks, unmarked)
        wire = decoded(camera, part)
        assert wire["marks"] == part["marks"] and wire["unmarked"] == part["unmarked"]
        assert datetime.fromisoformat(wire["t"]) == T
        if seen_unmarked:
            assert part["marks"] == []
        seen_unmarked |= bool(part["unmarked"])
        all_marks.extend(part["marks"])
        all_unmarked.extend(part["unmarked"])
    assert all_marks == sorted(marks)
    assert all_unmarked == sorted(unmarked)


@pytest.mark.parametrize("marks,unmarked", [
    ([[66, 1, "/" + "界" * 8192]], []),
    ([], [["/" + "界" * 8192, "limit"]]),
])
def test_split_coverage_refuses_single_oversized_row(camera, marks, unmarked):
    with pytest.raises(ValueError):
        camera.split_coverage(marks, unmarked, gen=GEN, seq_start=0, t=T)


def test_coalescer_windows_and_first_last_follow_event_time(camera):
    c = camera.Coalescer()
    early = T.replace(second=1, microsecond=0)
    late = T.replace(second=59, microsecond=999999)
    next_minute = T.replace(minute=35, second=0, microsecond=0)
    for t in (late, early, next_minute):
        assert c.add(opened(t=t)) == []
    records = sorted(c.flush(), key=lambda r: r["window_start"])
    assert len(records) == 2
    a, b = records
    assert (a["window_start"], a["first"], a["last"], a["count"], a["coalesced"]) == (T.replace(second=0, microsecond=0), early, late, 2, True)
    assert (b["window_start"], b["first"], b["last"], b["count"], b["coalesced"]) == (next_minute, next_minute, next_minute, 1, False)
    assert c.flush() == []


@pytest.mark.parametrize("change", ["gen", "pid", "start_time", "path_sha256"])
def test_coalescer_key_preserves_each_identity_component(camera, change):
    a, b = opened(), opened(seq=1)
    if change == "gen":
        b["gen"] = GEN2
    elif change == "path_sha256":
        # Same displayed suffix after truncation, different full original paths.
        b["path_sha256"] = "b" * 64
    else:
        b["reader"][change] += 1
    c = camera.Coalescer()
    c.add(a)
    c.add(b)
    assert sorted(r["count"] for r in c.flush()) == [1, 1]


def test_coalescer_records_have_entries_fields_without_storage_fields(camera):
    c = camera.Coalescer()
    msg = opened()
    c.add(msg)
    r, = c.flush()
    assert {"gen", "window_start", "first", "last", "count", "coalesced", "door", "path", "path_sha256", "truncated", "reader", "attribution"} <= r.keys()
    assert not {"_key", "session", "spooled"} & r.keys()
    for field in ("gen", "door", "path", "path_sha256", "truncated"):
        assert r[field] == msg[field]
    for field in ("pid", "start_time", "reused", "uid", "exe", "comm", "cgroup", "cwd", "ancestors"):
        assert r["reader"][field] == msg["reader"][field]
    assert r["attribution"] == "complete"


def test_coalescer_max_keys_one_exact_spec_example(camera):
    c = camera.Coalescer(max_keys=1)
    a = opened()
    b = opened(path="/h/community/elder/other", seq=1)
    assert c.add(a) == []
    flushed = c.add(b)
    assert len(flushed) == 1
    assert flushed[0]["path_sha256"] == a["path_sha256"] and flushed[0]["count"] == 1
    remaining, = c.flush()
    assert remaining["path_sha256"] == b["path_sha256"] and remaining["count"] == 1


def test_coalescer_cap_flushes_all_keys_and_all_windows(camera):
    c = camera.Coalescer(max_keys=2)
    a = opened()
    b = opened(path="/h/community/elder/b")
    assert c.add(a) == []
    assert c.add(b) == []
    assert c.add(opened(t=T + timedelta(minutes=1))) == []  # Same identity key.
    flushed = c.add(opened(path="/h/community/elder/c"))
    assert len(flushed) == 3
    assert sorted(r["count"] for r in flushed) == [1, 1, 1]
    assert {r["path_sha256"] for r in flushed} == {a["path_sha256"], b["path_sha256"]}
    assert len(c.flush()) == 1


def test_coalescer_existing_key_at_capacity_accumulates(camera):
    c = camera.Coalescer(max_keys=1)
    assert c.add(opened()) == []
    assert c.add(opened(seq=1)) == []
    r, = c.flush()
    assert r["count"] == 2 and r["coalesced"] is True


def test_coalescer_flush_before_is_strict_by_window_start(camera):
    c = camera.Coalescer()
    boundary = T.replace(minute=35, second=0, microsecond=0)
    c.add(opened())
    c.add(opened(t=boundary))
    older, = c.flush(before=boundary)
    assert older["window_start"] == T.replace(second=0, microsecond=0)
    assert c.flush(before=boundary) == []
    newer, = c.flush()
    assert newer["window_start"] == boundary


def test_scribe_gap_first_start_has_no_invented_history(camera):
    assert camera.scribe_gap_on_start(None, T) is None


@pytest.mark.parametrize("kind,cause", [("down", "stopped"), ("alive", "unknown")])
@pytest.mark.parametrize("delay", [timedelta(microseconds=1), timedelta(hours=1)])
def test_scribe_gap_always_records_previous_session_boundary(camera, kind, cause, delay):
    last = {"kind": kind, "at": T, "session": "previous"}
    gap = camera.scribe_gap_on_start(last, T + delay)
    assert gap["kind"] == "gap" and gap["scope"] == "scribe"
    assert gap["gap_from"] == T and gap["gap_to"] == T + delay
    assert gap["cause"] == cause


def test_gate_tracker_counts_seq_gaps_across_all_message_kinds(camera):
    tracker = camera.GateTracker()
    assert tracker.lost_in_channel == 0
    assert tracker.observe(beat(seq=0), now=T) == []
    tracker.observe(opened(seq=3), now=T)
    assert tracker.lost_in_channel == 2
    coverage = {"v": 1, "kind": "coverage", "gen": GEN, "seq": 6, "t": T, "coverage_version": "a" * 64, "part": 0, "parts": 1, "marks": [], "unmarked": []}
    tracker.observe(coverage, now=T)
    assert tracker.lost_in_channel == 4
    tracker.observe(beat(seq=8), now=T)
    assert tracker.lost_in_channel == 5
    for seq in (8, 4, 0, 9):
        tracker.observe(opened(seq=seq), now=T)
        assert tracker.lost_in_channel == 5


@pytest.mark.parametrize("first_kind", ["beat", "open", "coverage"])
def test_gate_tracker_short_generation_restart_always_has_closed_gap(camera, first_kind):
    tracker = camera.GateTracker()
    tracker.observe(beat(seq=0, t=T - timedelta(seconds=1), opened=1, self_reads=0,
                         answered=1, dropped=0), now=T - timedelta(seconds=1))
    old = beat(seq=1)
    tracker.observe(old, now=T)
    newer = T + timedelta(seconds=1)
    msg = beat(gen=GEN2, seq=0, t=newer)
    if first_kind == "open":
        msg = opened(gen=GEN2, seq=0, t=newer)
    elif first_kind == "coverage":
        msg = {"v": 1, "kind": "coverage", "gen": GEN2, "seq": 0, "t": newer, "coverage_version": "a" * 64, "part": 0, "parts": 1, "marks": [], "unmarked": []}
    statuses = tracker.observe(msg, now=newer)
    restarts = [s for s in statuses if s["kind"] == "gate_restart"]
    gaps = [s for s in statuses if s["kind"] == "gap"]
    assert len(restarts) == len(gaps) == 1
    assert restarts[0]["counts"] == {k: old[k] for k in ("opened", "self_reads", "answered", "dropped")}
    gap, = gaps
    assert gap["scope"] == "gate" and gap["gap_id"]
    assert gap["gap_from"] == T and gap["gap_to"] == newer
    assert tracker.lost_in_channel == 0
    tracker.observe(beat(gen=GEN2, seq=2, t=newer), now=newer)
    assert tracker.lost_in_channel == 1


def test_gate_tracker_silence_uses_arrival_clock_and_only_beats_close_it(camera):
    tracker = camera.GateTracker()
    assert tracker.tick(T) == []  # No invented last beat.
    event_time = T - timedelta(hours=1)
    tracker.observe(beat(t=event_time), now=T)
    assert tracker.tick(T + timedelta(seconds=10)) == []  # "exceeds", not >=.
    tracker.observe(opened(t=event_time, seq=1), now=T + timedelta(seconds=9))
    gap, = tracker.tick(T + timedelta(seconds=10, microseconds=1))
    assert gap["kind"] == "gap" and gap["scope"] == "gate"
    assert gap["gap_from"] == event_time and gap["gap_to"] is None
    assert tracker.tick(T + timedelta(seconds=20)) == []
    assert tracker.observe(opened(seq=2), now=T + timedelta(seconds=21)) == []
    closed, = tracker.observe(beat(seq=3, t=T), now=T + timedelta(seconds=22))
    assert closed["gap_id"] == gap["gap_id"]
    assert closed["gap_from"] == event_time and closed["gap_to"] == T
    assert tracker.tick(T + timedelta(seconds=23)) == []
    assert tracker.observe(beat(seq=4, t=T), now=T + timedelta(seconds=24)) == []


def test_gate_tracker_custom_silence_threshold(camera):
    tracker = camera.GateTracker(silence=timedelta(seconds=3))
    tracker.observe(beat(), now=T)
    assert tracker.tick(T + timedelta(seconds=3)) == []
    assert len(tracker.tick(T + timedelta(seconds=3, microseconds=1))) == 1


def test_gate_tracker_lost_count_survives_generation_change(camera):
    tracker = camera.GateTracker()
    tracker.observe(beat(seq=0), now=T)
    tracker.observe(opened(seq=3), now=T)
    assert tracker.lost_in_channel == 2
    tracker.observe(beat(gen=GEN2, seq=0), now=T)
    tracker.observe(opened(gen=GEN2, seq=2), now=T)
    assert tracker.lost_in_channel == 3


def test_gate_tracker_restart_during_silence_closes_same_gap_without_double_gap(camera):
    tracker = camera.GateTracker()
    tracker.observe(beat(), now=T)
    gap, = tracker.tick(T + timedelta(seconds=11))
    end = T + timedelta(seconds=12)
    statuses = tracker.observe(beat(gen=GEN2, t=end), now=end)
    assert len([s for s in statuses if s["kind"] == "gate_restart"]) == 1
    closed = [s for s in statuses if s["kind"] == "gap"]
    assert len(closed) == 1
    assert closed[0]["gap_id"] == gap["gap_id"]
    assert closed[0]["gap_from"] == T and closed[0]["gap_to"] == end
    assert tracker.tick(end + timedelta(seconds=1)) == []


def spool_record(key):
    return {"_key": key, "kind": "alive", "at": T.isoformat(), "session": "validation"}


def test_spool_append_is_jsonl_private_and_survives_reopening(camera, tmp_path):
    path = tmp_path / "spool.jsonl"
    a, b = spool_record("a"), spool_record("b")
    spool = camera.Spool(path, max_bytes=4096)
    assert spool.append(a) is True
    assert spool.append(b) is True
    assert spool.refused == 0
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.read_bytes().endswith(b"\n")
    assert [json.loads(line) for line in path.read_text().splitlines()] == [a, b]
    seen = []
    result = camera.Spool(path, max_bytes=4096).replay(lambda r: seen.append(r) or "stored")
    assert seen == [a, b]
    assert result == {"stored": 2, "conflict": 0, "torn": 0, "remaining": 0}


def test_spool_cap_refusal_keeps_existing_bytes_and_counts_each_refusal(camera, tmp_path):
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=512)
    assert spool.append(spool_record("a")) is True
    previous = path.read_bytes()
    huge = {"_key": "b", "payload": "x" * 600}
    assert spool.append(huge) is False
    assert spool.append(huge) is False
    assert spool.refused == 2
    assert path.read_bytes() == previous
    assert path.stat().st_size <= 512


def test_spool_append_filesystem_failure_is_counted_without_raising(camera, tmp_path):
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=4096)
    # A directory at the file path makes an append fail without relying on uid.
    if path.exists():
        path.unlink()
    path.mkdir()
    assert spool.append(spool_record("a")) is False
    assert spool.refused == 1


def test_spool_cap_allows_exact_fit_then_refuses_another_byte(camera, tmp_path):
    record = spool_record("a")
    sizing_path = tmp_path / "sizing.jsonl"
    assert camera.Spool(sizing_path, max_bytes=4096).append(record) is True
    row_bytes = sizing_path.stat().st_size
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=row_bytes)
    assert spool.append(record) is True
    assert path.stat().st_size == row_bytes
    assert spool.append(record) is False
    assert spool.refused == 1
    assert path.stat().st_size == row_bytes


def test_spool_append_fsyncs_each_line_before_returning(camera, tmp_path, monkeypatch):
    events = []
    real_fsync = os.fsync

    def fsync(fd):
        info = os.fstat(fd)
        events.append((info.st_ino, info.st_size))
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=4096)
    for key in "ab":
        events.clear()
        assert spool.append(spool_record(key)) is True
        assert (path.stat().st_ino, path.stat().st_size) in events


def test_spool_retirement_fsyncs_empty_replacement_then_directory(camera, tmp_path, monkeypatch):
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=4096)
    assert spool.append(spool_record("a")) is True
    events = []
    real_fsync = os.fsync

    def fsync(fd):
        info = os.fstat(fd)
        events.append((stat.S_ISDIR(info.st_mode), info.st_size, info.st_ino, path.stat().st_ino))
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    assert spool.replay(lambda r: "stored")["remaining"] == 0
    replacement = path.stat().st_ino
    empty_sync = next(i for i, e in enumerate(events) if not e[0] and e[1] == 0 and e[2] == replacement)
    directory_sync = next(i for i, e in enumerate(events) if e[0] and e[3] == replacement)
    assert empty_sync < directory_sync


def test_spool_conflict_counts_are_disjoint(camera, tmp_path):
    spool = camera.Spool(tmp_path / "spool.jsonl", max_bytes=4096)
    assert spool.append(spool_record("a")) is True
    assert spool.replay(lambda r: "conflict") == {"stored": 0, "conflict": 1, "torn": 0, "remaining": 0}


def test_spool_replay_stops_at_failed_preserves_order_and_retries_with_same_keys(camera, tmp_path):
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=4096)
    rows = [spool_record(key) for key in "abcd"]
    for row in rows:
        assert spool.append(row) is True
    before = path.stat().st_ino
    calls = []
    outcomes = iter(["stored", "conflict", "failed"])

    def insert(row):
        calls.append(row)
        return next(outcomes)

    assert spool.replay(insert) == {"stored": 1, "conflict": 1, "torn": 0, "remaining": 2}
    assert calls == rows[:3]
    assert path.stat().st_ino == before  # No retirement while remaining > 0.
    assert path.stat().st_size > 0
    seen = []
    already = {"a", "b"}

    def retry(row):
        seen.append(row)
        return "conflict" if row["_key"] in already else "stored"

    result = camera.Spool(path, max_bytes=4096).replay(retry)
    # R8 permits a retained acknowledged prefix; idempotent replay handles it.
    assert seen in (rows, rows[2:])
    assert result["stored"] == 2 and result["remaining"] == 0 and result["torn"] == 0
    assert result["conflict"] == len(seen) - 2
    assert path.stat().st_ino != before
    assert path.read_bytes() == b""


def test_spool_torn_last_line_is_discarded_and_counted(camera, tmp_path):
    path = tmp_path / "spool.jsonl"
    row = spool_record("a")
    path.write_bytes(compact(row) + b'\n{"_key":"torn')
    seen = []
    result = camera.Spool(path, max_bytes=4096).replay(lambda r: seen.append(r) or "stored")
    assert seen == [row]
    assert result == {"stored": 1, "conflict": 0, "torn": 1, "remaining": 0}
    assert path.read_bytes() == b""


def test_spool_success_retires_by_replace_leaving_old_open_file_intact(camera, tmp_path):
    path = tmp_path / "spool.jsonl"
    spool = camera.Spool(path, max_bytes=4096)
    assert spool.append(spool_record("a")) is True
    with path.open("rb") as old_file:
        old_bytes = old_file.read()
        inode = os.fstat(old_file.fileno()).st_ino
        assert spool.replay(lambda r: "stored")["remaining"] == 0
        assert path.stat().st_ino != inode
        assert path.read_bytes() == b""
        old_file.seek(0)
        assert old_file.read() == old_bytes  # In-place truncation fails this.
    assert path.stat().st_mode & 0o777 == 0o600
    assert spool.append(spool_record("b")) is True
    assert [json.loads(line) for line in path.read_text().splitlines()] == [spool_record("b")]
