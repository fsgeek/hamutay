"""The heartbeat persists every cycle to Apacheta, as taste_open by hand always did.

Since the founding (2026-08-26) the doors wrote JSONL only: the heartbeat
built its session without a bridge. The JSONL is the backup; the database
is the record of truth for the ayllu. A door running without the database
says so loudly in its launch note.
"""

from __future__ import annotations

import json
from uuid import uuid4



class FakeBridge:
    def __init__(self):
        self.resumed_after = None
        self.stored = []

    def resume_after(self, record_id):
        self.resumed_after = record_id

    def store_open_state(self, state, cycle, record_id, timestamp):
        self.stored.append((cycle, record_id))


def _args(log_path, *extra):
    from hamutay.heartbeat import build_parser

    return build_parser().parse_args([
        "--log-path", str(log_path), "--provider", "openrouter", "--model", "m",
        "--api-key", "test-key", *extra,
    ])


def test_parser_persists_to_arango_by_default():
    args = _args("x.jsonl")
    assert args.persist == "arango"
    assert args.no_persist is False


def test_resolve_persistence_names_the_backend_and_the_door(tmp_path):
    from hamutay.heartbeat import resolve_persistence

    calls = []
    fake = FakeBridge()

    def factory(persist, *, session_id, model):
        calls.append((persist, session_id, model))
        return fake

    log = tmp_path / "community" / "elder" / "session.jsonl"
    bridge, note = resolve_persistence(_args(log), bridge_factory=factory)
    assert bridge is fake
    assert calls == [("arango", "elder", "m")]
    assert note == "persistence: ArangoDB (via Apacheta), session elder"


def test_resolve_persistence_duckdb_path_is_named(tmp_path):
    from hamutay.heartbeat import resolve_persistence

    fake = FakeBridge()
    log = tmp_path / "community" / "qwen" / "session.jsonl"
    db = tmp_path / "x.duckdb"
    bridge, note = resolve_persistence(
        _args(log, "--persist", str(db)), bridge_factory=lambda p, **kw: fake
    )
    assert bridge is fake
    assert note == f"persistence: DuckDB at {db}, session qwen"


def test_resolve_persistence_is_loud_when_the_database_is_unreachable(tmp_path):
    from hamutay.heartbeat import resolve_persistence

    def factory(persist, *, session_id, model):
        raise ConnectionError("no route to 8529")

    log = tmp_path / "community" / "fable" / "session.jsonl"
    bridge, note = resolve_persistence(_args(log), bridge_factory=factory)
    assert bridge is None
    assert note == "!!! persistence: unavailable (ConnectionError: no route to 8529); JSONL only"


def test_resolve_persistence_is_loud_when_disabled_by_flag(tmp_path):
    from hamutay.heartbeat import resolve_persistence

    def factory(persist, **kw):
        raise AssertionError("no bridge must be built under --no-persist")

    log = tmp_path / "community" / "heartbeat" / "session.jsonl"
    bridge, note = resolve_persistence(_args(log, "--no-persist"), bridge_factory=factory)
    assert bridge is None
    assert note == "!!! persistence: disabled by --no-persist; JSONL only"


def test_build_session_hands_the_bridge_to_the_session(tmp_path, monkeypatch):
    from hamutay import heartbeat as hb

    fake = FakeBridge()
    monkeypatch.setattr(hb, "_default_bridge_factory", lambda p, **kw: fake)
    notes = []
    monkeypatch.setattr(hb.HeartbeatLoop, "_emit", staticmethod(lambda d: notes.append(d)))
    log = tmp_path / "community" / "elder" / "session.jsonl"
    session, backend, launch_config = hb.build_session(_args(log))
    assert session._bridge is fake
    assert fake.resumed_after is None  # a fresh log has no prior record
    assert any(n.get("note") == "persistence: ArangoDB (via Apacheta), session elder" for n in notes)


def test_build_session_resumes_the_bridge_chain_from_the_last_record(tmp_path, monkeypatch):
    from hamutay import heartbeat as hb

    log = tmp_path / "community" / "elder" / "session.jsonl"
    log.parent.mkdir(parents=True)
    last = uuid4()
    with open(log, "w") as f:
        for cycle, rid in ((1, uuid4()), (2, last)):
            f.write(json.dumps({
                "timestamp": f"2026-09-2{cycle}T00:00:00+00:00", "cycle": cycle,
                "record_id": str(rid), "experiment_label": "taste_open", "model": "m",
                "user_message": "hi", "state": {"cycle": cycle},
                "raw_output": {"response": "ok"},
            }) + "\n")
    fake = FakeBridge()
    monkeypatch.setattr(hb, "_default_bridge_factory", lambda p, **kw: fake)
    monkeypatch.setattr(hb.HeartbeatLoop, "_emit", staticmethod(lambda d: None))
    session, backend, launch_config = hb.build_session(_args(log))
    assert session._bridge is fake
    assert fake.resumed_after == last


def test_apacheta_bridge_resume_after_continues_the_refines_chain():
    from datetime import datetime, timezone

    from hamutay.apacheta_bridge import ApachetaBridge

    bridge = ApachetaBridge.from_memory(session_id="elder", model="m")
    prior = uuid4()
    bridge.resume_after(prior)
    new = uuid4()
    bridge.store_open_state({"cycle": 2}, 2, new, datetime.now(timezone.utc))
    edges = bridge.query_edges_by_endpoint(new)
    assert [(e["from_record"], e["to_record"], e["relation_type"]) for e in edges] == [(prior, new, "refines")]
