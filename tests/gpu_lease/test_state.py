import json, os, shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from hamutay.gpu_lease.state import (
    MalformedState, paths, locked, write_atomic, read_lease, read_quarantine,
    list_tombstones, parse_instant, parse_ttl, scope_unit_for,
)

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "gpu_lease"
NOW = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)

@pytest.fixture
def p(tmp_path, monkeypatch):
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    return paths()

def test_paths_follow_env_and_create_nothing(p, tmp_path):
    assert p.dir == tmp_path / "state" / "gpu"
    assert p.lease.name == "4090.lease" and p.tombstones.name == "4090.tombstones"
    assert not p.dir.exists()

@pytest.mark.parametrize("name,kind", json.loads((FIX / "verdicts.json").read_text()).items())
def test_fixture_verdicts(p, name, kind):
    p.dir.mkdir(parents=True)
    shutil.copy(FIX / name, p.lease)
    assert read_lease(p, NOW).kind == kind

def test_absent_lease(p):
    assert read_lease(p, NOW).kind == "absent"

def test_expiry_boundary_is_inclusive(p):
    p.dir.mkdir(parents=True)
    data = json.loads((FIX / "live.json").read_text())
    data["expires_at"] = NOW.isoformat()
    write_atomic(p.lease, data)
    assert read_lease(p, NOW).kind == "expired"
    assert read_lease(p, NOW - timedelta(seconds=1)).kind == "live"

def test_malformed_keeps_raw_bytes(p):
    p.dir.mkdir(parents=True)
    shutil.copy(FIX / "malformed_json.json", p.lease)
    view = read_lease(p, NOW)
    assert view.kind == "malformed" and view.raw.startswith(b'{"resource"')

def test_parse_instant_requires_offset():
    assert parse_instant("2026-09-20T15:00:00Z") == NOW
    with pytest.raises(ValueError):
        parse_instant("2026-09-20T15:00:00")

@pytest.mark.parametrize("s,secs", [("1m", 60), ("6h", 21600), ("3d", 259200), ("72h", 259200)])
def test_parse_ttl_grammar(s, secs):
    assert parse_ttl(s) == timedelta(seconds=secs)

@pytest.mark.parametrize("s", ["0m", "73h", "4d", "1.5h", "90", "h"])
def test_parse_ttl_rejects(s):
    with pytest.raises(ValueError):
        parse_ttl(s)

def test_write_atomic_replaces_whole_file(p):
    write_atomic(p.lease, {"a": 1})
    write_atomic(p.lease, {"b": 2})
    assert json.loads(p.lease.read_text()) == {"b": 2}
    assert not list(p.dir.glob("*.tmp*"))

def test_locked_creates_dir_and_is_exclusive(p):
    with locked(p):
        assert p.lock.exists()
        import fcntl
        with p.lock.open("a") as other:
            with pytest.raises(BlockingIOError):
                fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

def test_quarantine_and_tombstones(p):
    assert read_quarantine(p) is None and list_tombstones(p) == []
    write_atomic(p.quarantine, {"quarantine_id": "q1", "reason": "malformed_lease"})
    p.tombstones.mkdir(parents=True, exist_ok=True)
    (p.tombstones / "ayllu-gpu-x.scope").write_text("")
    assert read_quarantine(p)["quarantine_id"] == "q1"
    assert list_tombstones(p) == ["ayllu-gpu-x.scope"]
    p.quarantine.write_text("{nope")
    with pytest.raises(MalformedState):
        read_quarantine(p)

def test_scope_unit_is_deterministic():
    assert scope_unit_for("abc") == "ayllu-gpu-abc.scope"
