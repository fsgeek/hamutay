"""Tests for hamutay.migrate_log — replaying a taste_open JSONL log into Apacheta."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.migrate_log import (
    AlreadyMigratedError,
    LogFormatError,
    _session_id_from_path,
    iter_log_records,
    legacy_record_id,
    migrate_log,
)


def _write_log(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
    return path


def _cycle_record(cycle, state, *, record_id=None, model="claude-haiku-4-5", ts=None):
    rec = {
        "timestamp": ts or f"2026-05-12T20:0{cycle}:00+00:00",
        "cycle": cycle,
        "experiment_label": "taste_open",
        "model": model,
        "user_message": f"message {cycle}",
        "state": {**state, "cycle": cycle},
        "raw_output": {"response": f"response {cycle}"},
    }
    if record_id is not None:
        rec["record_id"] = str(record_id)
    return rec


def test_session_id_from_filename():
    from pathlib import Path

    assert _session_id_from_path(Path("experiments/taste_open/taste_open_20260512_185846.jsonl")) == "20260512_185846"
    assert _session_id_from_path(Path("/tmp/something_else.jsonl")) == "something_else"


def test_lfs_pointer_is_rejected(tmp_path):
    log = tmp_path / "pointer.jsonl"
    log.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:deadbeef\nsize 12345\n"
    )
    with pytest.raises(LogFormatError, match="Git LFS pointer"):
        list(iter_log_records(log))


def test_invalid_json_is_rejected(tmp_path):
    log = tmp_path / "bad.jsonl"
    log.write_text('{"cycle": 1}\nnot json at all\n')
    with pytest.raises(LogFormatError, match="invalid JSON"):
        list(iter_log_records(log))


def test_migrate_three_cycle_log_into_memory(tmp_path):
    ids = [uuid4(), uuid4(), uuid4()]
    records = [
        _cycle_record(1, {"topic": "state mgmt"}, record_id=ids[0]),
        _cycle_record(2, {"topic": "compression", "note": "two threads"}, record_id=ids[1]),
        _cycle_record(3, {"topic": "synthesis"}, record_id=ids[2]),
    ]
    log = _write_log(tmp_path / "taste_open_20260512_185846.jsonl", records)

    bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
    summary = migrate_log(log, bridge=bridge)

    assert summary["cycles"] == 3
    assert summary["records_written"] == 3
    assert summary["minted_ids"] == 0
    assert summary["first_cycle"] == 1
    assert summary["last_cycle"] == 3
    assert summary["model"] == "claude-haiku-4-5"
    assert summary["session_id"] == "20260512_185846"

    # Every record round-trips, carries its state, and keeps provenance.
    for rid, expected_topic in zip(ids, ["state mgmt", "compression", "synthesis"]):
        got = bridge.retrieve(rid)
        assert got["topic"] == expected_topic
        assert got["provenance"]["author_model_family"] == "claude-haiku-4-5"
        # cycle is stripped from the stored record (it's frame-local metadata)
        assert "cycle" not in got

    # REFINES chain: id[1] <- id[0], id[2] <- id[1]
    fwd_from_0 = bridge.query_edges_by_endpoint(ids[0], direction="forward")
    assert any(e["to_record"] == ids[1] and e["relation_type"] == "refines" for e in fwd_from_0)
    fwd_from_1 = bridge.query_edges_by_endpoint(ids[1], direction="forward")
    assert any(e["to_record"] == ids[2] for e in fwd_from_1)
    # First record has no predecessor edge.
    back_to_0 = bridge.query_edges_by_endpoint(ids[0], direction="backward")
    assert back_to_0 == []


def test_legacy_log_without_record_id_uses_deterministic_surrogate(tmp_path):
    records = [
        _cycle_record(1, {"a": 1}),
        _cycle_record(2, {"a": 2}),
    ]
    log = _write_log(tmp_path / "taste_open_legacy.jsonl", records)

    bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
    summary = migrate_log(log, bridge=bridge)

    assert summary["cycles"] == 2
    assert summary["records_written"] == 2
    assert summary["minted_ids"] == 2
    assert len(bridge.list_open_records()) == 2

    # The surrogate id is derived from (session_id, cycle) — stable, retrievable.
    # Session id is the filename stem with the "taste_open_" prefix stripped.
    assert summary["session_id"] == "legacy"
    rid1 = legacy_record_id("legacy", 1)
    assert bridge.retrieve(rid1)["a"] == 1


def test_reimport_into_same_destination_is_refused(tmp_path):
    """Re-running migration on a populated destination raises rather than
    silently duplicating — true for record_id-bearing and legacy logs alike."""
    for label, mk in (
        ("uuid", lambda: [_cycle_record(1, {"a": 1}, record_id=uuid4()),
                          _cycle_record(2, {"a": 2}, record_id=uuid4())]),
        ("legacy", lambda: [_cycle_record(1, {"a": 1}), _cycle_record(2, {"a": 2})]),
    ):
        log = _write_log(tmp_path / f"taste_open_{label}.jsonl", mk())
        bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
        migrate_log(log, bridge=bridge)  # first import: fine
        with pytest.raises(AlreadyMigratedError):
            migrate_log(log, bridge=bridge)  # second: refused
        assert len(bridge.list_open_records()) == 2  # nothing duplicated


def test_dry_run_skips_already_migrated_guard(tmp_path):
    """A dry run never touches the destination, so the guard doesn't fire."""
    records = [_cycle_record(1, {"a": 1}, record_id=uuid4())]
    log = _write_log(tmp_path / "taste_open_dryguard.jsonl", records)
    bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
    migrate_log(log, bridge=bridge)
    # Even though the record now exists, a dry run is still allowed.
    summary = migrate_log(log, bridge=bridge, dry_run=True)
    assert summary["cycles"] == 1
    assert summary["records_written"] == 0


def test_dry_run_writes_nothing(tmp_path):
    records = [_cycle_record(1, {"a": 1}, record_id=uuid4())]
    log = _write_log(tmp_path / "taste_open_dry.jsonl", records)

    bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
    summary = migrate_log(log, bridge=bridge, dry_run=True)

    assert summary["cycles"] == 1
    assert summary["records_written"] == 0
    assert summary["dry_run"] is True
    assert bridge.list_open_records() == []


def test_record_without_state_is_skipped(tmp_path):
    records = [
        _cycle_record(1, {"a": 1}, record_id=uuid4()),
        {"timestamp": "2026-05-12T20:02:00+00:00", "cycle": 2, "model": "x"},  # no state
        _cycle_record(3, {"a": 3}, record_id=uuid4()),
    ]
    log = _write_log(tmp_path / "taste_open_partial.jsonl", records)

    bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
    summary = migrate_log(log, bridge=bridge)

    assert summary["cycles"] == 2
    assert summary["skipped_no_state"] == 1
    assert summary["records_written"] == 2


def test_graph_write_activity_is_flagged(tmp_path):
    state_with_store = {
        "topic": "x",
        "_activity_log": [
            {"cycle": 2, "tool": "store", "parameters": {"content": {"k": "v"}}},
            {"cycle": 2, "tool": "read", "parameters": {"path": "foo"}},
        ],
    }
    records = [
        _cycle_record(1, {"topic": "a"}, record_id=uuid4()),
        _cycle_record(2, state_with_store, record_id=uuid4()),
    ]
    log = _write_log(tmp_path / "taste_open_graphwrite.jsonl", records)

    bridge = ApachetaBridge.from_memory(model="claude-haiku-4-5")
    summary = migrate_log(log, bridge=bridge)

    assert summary["graph_write_cycles"] == [2]
