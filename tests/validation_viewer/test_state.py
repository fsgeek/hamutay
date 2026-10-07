import builtins
import io
import json
from datetime import timedelta
from pathlib import Path

import pytest

from hamutay.viewer import state

from .conftest import NOW, SECRETS, STAMP, closing, event, message, question, write_jsonl


def qwen(view):
    return next(d for d in view["doors"] if d["name"] == "qwen")


def keys_in(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys_in(child)


def snapshot(root):
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
            for p in root.rglob("*") if p.is_file()}


def test_gather_shows_public_records_guests_and_only_door_metadata(community):
    view = state.gather(community.root, NOW)
    assert view["at"] == STAMP
    assert [d["name"] for d in view["doors"]] == ["elder", "fable", "qwen"]
    assert view["guests"] == ["levadura", "visitor-two"]
    assert view["plaza_error"] is None
    assert [(m["seq"], m["text"], m["truth"]["state"]) for m in view["plaza"]] == [
        (1, "Public plaza post", "post"), (2, "Public directed message", "landed")]
    assert set(view["plaza"][0]) == {"seq", "from", "to", "text", "sent_at", "truth"}
    d = qwen(view)
    assert d["running"] == ["awake"]
    assert d["pending"] == 1
    assert d["last_wake"]["status"] == "completed"
    assert d["wakes"][0]["error"] == "Public failure details"
    assert d["wakes"][0]["error_type"] == "RuntimeError"
    assert d["now_status"] == {"status": "resting", "reason": "quiet_hours", "created_at": STAMP}
    assert d["quiet"]["reason"] == "Public quiet reason"
    assert d["week"] == {"completed": 1, "failed": 1, "spend_usd_reconciled": 1.75}
    q = view["assembly"][0]
    assert q["text"] == "Public assembly question\nSecond public line"
    assert q["positions"][0]["reasons"] == "Public position reasons"
    assert q["testimony"][0]["text"] == "Public testimony body"
    assert q["closing"]["outcome"] == "assented"
    assert q["execution"]["what"] == "Public execution details"
    serialized = json.dumps(view)
    assert all(secret not in serialized for secret in SECRETS)
    assert not set(keys_in(view)) & {"response_text", "session", "authored_state", "raw_output", "raw"}


def test_no_private_home_file_is_even_opened(community, monkeypatch):
    opened = []

    def guard(original):
        def checked(file, *args, **kwargs):
            if isinstance(file, (str, bytes, Path)):
                path = Path(file).resolve()
                opened.append(path)
                assert path not in community.private_files, f"Viewer opened private home: {path}"
            return original(file, *args, **kwargs)
        return checked

    monkeypatch.setattr(builtins, "open", guard(builtins.open))
    monkeypatch.setattr(io, "open", guard(io.open))
    view = state.gather(community.root, NOW)
    assert "error" not in view
    assert view["plaza_error"] is None  # also catch an accidentally swallowed guard assertion
    assert community.events() in opened
    assert community.cfg.plaza in opened
    assert community.cfg.ledger in opened
    assert not set(opened) & community.private_files


def test_gather_writes_nothing_including_lock_files(community):
    before = snapshot(community.root)
    state.gather(community.root, NOW)
    assert snapshot(community.root) == before


def test_gather_never_requests_write_access_even_with_an_existing_lock(community, monkeypatch):
    community.cfg.plaza.with_suffix(".jsonl.lock").touch()
    writes = []
    original_open, original_mkdir = io.open, Path.mkdir

    def track_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            writes.append(("open", str(file), mode))
        return original_open(file, mode, *args, **kwargs)

    def track_mkdir(path, *args, **kwargs):
        writes.append(("mkdir", str(path)))
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(io, "open", track_open)
    monkeypatch.setattr(Path, "mkdir", track_mkdir)
    view = state.gather(community.root, NOW)
    assert view["plaza_error"] is None
    assert writes == []


@pytest.mark.parametrize("name", ["events", "billing", "assembly"])
@pytest.mark.parametrize("bad", [b'{"torn":', b"not json", b"\xff", b"null", b"[1,2]"])
def test_bad_jsonl_lines_are_skipped_without_losing_good_records(community, name, bad):
    path = {"events": community.events(), "billing": community.billing(),
            "assembly": community.cfg.ledger}[name]
    good = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(good[0] + bad + b"\n" + b"".join(good[1:]) + b'{"unfinished":')
    before = path.read_bytes()
    view = state.gather(community.root, NOW)
    assert qwen(view)["week"] == {"completed": 1, "failed": 1, "spend_usd_reconciled": 1.75}
    assert qwen(view)["last_wake"]["event_id"] == "finished"
    assert view["assembly"][0]["execution"]["what"] == "Public execution details"
    assert path.read_bytes() == before


@pytest.mark.parametrize("name", ["events", "billing", "assembly"])
def test_parseable_unterminated_tail_is_still_a_torn_append(community, name):
    paths = {"events": community.events(), "billing": community.billing(),
             "assembly": community.cfg.ledger}
    tails = {"events": event("torn-event", "completed"),
             "billing": {"generation_id": "torn-generation", "usage_usd": 50, "created_at": STAMP},
             "assembly": question("torn-question", seq=7)}
    path = paths[name]
    path.write_bytes(path.read_bytes() + json.dumps(tails[name]).encode())
    before = path.read_bytes()
    view = state.gather(community.root, NOW)
    assert qwen(view)["week"] == {"completed": 1, "failed": 1, "spend_usd_reconciled": 1.75}
    assert qwen(view)["last_wake"]["event_id"] == "finished"
    assert [q["question_id"] for q in view["assembly"]] == ["question-1"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("bad", [b"not json", b"\xff", b"null", b'{"record_type":"unknown"}'])
def test_malformed_plaza_line_is_skipped_and_good_messages_remain(community, bad):
    first = message(1, text="Before malformed line")
    second = message(3, text="After malformed line")
    community.cfg.plaza.write_bytes(json.dumps(first).encode() + b"\n" + bad + b"\n"
                                    + json.dumps(second).encode() + b"\n")
    before = community.cfg.plaza.read_bytes()
    view = state.gather(community.root, NOW)
    assert view["plaza_error"] is None
    assert [m["text"] for m in view["plaza"]] == ["Before malformed line", "After malformed line"]
    assert community.cfg.plaza.read_bytes() == before


def test_torn_plaza_tail_is_skipped_and_never_repaired(community):
    community.cfg.plaza.write_bytes(community.cfg.plaza.read_bytes() + b'{"unfinished":')
    before = community.cfg.plaza.read_bytes()
    view = state.gather(community.root, NOW)
    assert view["plaza_error"] is None
    assert len(view["plaza"]) == 2
    assert community.cfg.plaza.read_bytes() == before


def test_plaza_read_failure_is_reported_and_other_sections_survive(community, monkeypatch):
    read = Path.read_bytes

    def unreadable(path):
        if path == community.cfg.plaza:
            raise PermissionError("Plaza access denied for validation")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    view = state.gather(community.root, NOW)
    assert view["plaza"] == []
    assert "PermissionError" in view["plaza_error"]
    assert "Plaza access denied" in view["plaza_error"]
    assert len(view["doors"]) == 3
    assert len(view["assembly"]) == 1
    assert view["guests"] == ["levadura", "visitor-two"]


def test_unconfigured_root_is_a_read_only_error(tmp_path):
    before = list(tmp_path.iterdir())
    view = state.gather(tmp_path, NOW)
    assert "members.json" in view["error"]
    assert view["at"] == STAMP
    assert list(tmp_path.iterdir()) == before


@pytest.mark.parametrize("guests", [None, []])
def test_missing_or_empty_guest_list_and_disabled_plaza_are_supported(community, guests):
    path = community.root / "community/plaza/members.json"
    cfg = json.loads(path.read_text())
    cfg.pop("plaza")
    if guests is None:
        cfg.pop("guests")
    else:
        cfg["guests"] = guests
    path.write_text(json.dumps(cfg))
    view = state.gather(community.root, NOW)
    assert view["guests"] == []
    assert view["plaza"] == []
    assert view["plaza_error"] is None


def test_latest_status_replaces_pending_and_running_counts(community):
    write_jsonl(community.events(), [
        event("finished", "pending"), event("finished", "running"), event("finished", "completed"),
        event("failed", "running"), event("failed", "failed"),
        event("awake", "pending"), event("awake", "running"), event("waiting", "pending"),
        event("expired", "pending"), event("expired", "expired"),
    ])
    d = qwen(state.gather(community.root, NOW))
    assert d["pending"] == 1
    assert d["running"] == ["awake"]
    assert d["week"]["completed"] == d["week"]["failed"] == 1


def test_week_cutoff_and_wake_history_are_independent(community):
    week_start = NOW - timedelta(days=7)
    rows = [event("older", "completed", completed_at=(week_start - timedelta(seconds=1)).isoformat()),
            event("boundary", "failed", failed_at=week_start.isoformat())]
    rows += [event(f"new-{i}", "completed", wake_cycle=i, response_text=SECRETS[3]) for i in range(15)]
    write_jsonl(community.events(), rows)
    d = qwen(state.gather(community.root, NOW))
    assert d["week"]["completed"] == 15
    assert d["week"]["failed"] == 1
    assert len(d["wakes"]) == 12
    assert [w["event_id"] for w in d["wakes"]] == [f"new-{i}" for i in range(3, 15)]
    assert SECRETS[3] not in json.dumps(d)


def test_billing_uses_later_reconciliation_and_week_boundary(community):
    write_jsonl(community.billing(), [
        {"generation_id": "same", "usage_usd": 10, "created_at": STAMP},
        {"generation_id": "same", "usage_usd": 1.23456, "created_at": STAMP},
        {"generation_id": "boundary", "usage_usd": .1,
         "created_at": (NOW - timedelta(days=7)).isoformat()},
        {"generation_id": "old", "usage_usd": 90,
         "created_at": (NOW - timedelta(days=7, seconds=1)).isoformat()},
    ])
    assert qwen(state.gather(community.root, NOW))["week"]["spend_usd_reconciled"] == 1.3346


def test_configured_events_name_does_not_change_session_billing_location(community):
    config_path = community.root / "community/plaza/members.json"
    cfg = json.loads(config_path.read_text())
    new_events = community.root / "community/qwen/wake-events.jsonl"
    new_events.write_bytes(community.events().read_bytes())
    cfg["members"]["qwen"]["events"] = str(new_events.relative_to(community.root))
    config_path.write_text(json.dumps(cfg))
    assert qwen(state.gather(community.root, NOW))["week"]["spend_usd_reconciled"] == 1.75


def test_assembly_is_newest_first_and_orphan_records_do_not_crash(community):
    write_jsonl(community.cfg.ledger, [
        {"record_type": "position", "question_id": "unknown", "stance": "assent"},
        *community.assembly_records, question("question-2", seq=7)])
    view = state.gather(community.root, NOW)
    assert [q["question_id"] for q in view["assembly"]] == ["question-2", "question-1"]
    assert view["assembly"][0]["closing"] is None


def test_embedded_extension_round_and_its_public_records_are_visible(community):
    parent = question()
    child = {"question_id": "question-2", "round": 2, "opened_at": STAMP,
             "closes_at": (NOW + timedelta(days=1)).isoformat(), "text": parent["text"],
             "proposal": parent["proposal"], "governing": parent["governing"], "members": parent["members"]}
    write_jsonl(community.cfg.ledger, [parent, closing(outcome="extended", next_question=child),
        {"record_type": "position", "question_id": "question-2", "member": "door:elder",
         "stance": "dissent", "reasons": "Child round reasons", "seq": 6, "created_at": STAMP},
        {"record_type": "testimony", "question_id": "question-2", "by": "tony",
         "text": "Child round testimony", "seq": 7, "created_at": STAMP}])
    questions = state.gather(community.root, NOW)["assembly"]
    assert [q["question_id"] for q in questions] == ["question-2", "question-1"]
    assert questions[0]["round"] == 2
    assert questions[0]["closing"] is None
    assert questions[0]["convener"] == "tony"
    assert questions[0]["positions"][0]["reasons"] == "Child round reasons"
    assert questions[0]["testimony"][0]["text"] == "Child round testimony"


@pytest.mark.parametrize("later_status", ["completed", "failed"])
def test_old_quiet_declaration_does_not_author_a_later_wakes_quiet(community, later_status):
    write_jsonl(community.events(), [
        event("old", "completed", result_record_id="old-cycle"),
        {"record_type": "quiet_declaration", "declared_by_record_id": "old-cycle",
         "declared_by_cycle": 1, "reason": "Old choice", "created_at": STAMP,
         "until": (NOW + timedelta(days=1)).isoformat()},
        event("new", later_status, result_record_id="new-cycle")])
    assert qwen(state.gather(community.root, NOW))["quiet"] is None


def test_orphan_quiet_declaration_has_no_authority(community):
    write_jsonl(community.events(), [
        event("old", "completed", result_record_id="old-cycle"),
        {"record_type": "quiet_declaration", "declared_by_record_id": "never-completed",
         "declared_by_cycle": 2, "reason": "Orphan choice", "created_at": STAMP,
         "until": (NOW + timedelta(days=1)).isoformat()}])
    assert qwen(state.gather(community.root, NOW))["quiet"] is None
