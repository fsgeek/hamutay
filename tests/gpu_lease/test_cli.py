import json, fcntl
from datetime import datetime, timedelta, timezone
from hamutay.gpu_lease import cli, ledger
from hamutay.gpu_lease.state import read_lease

NOW = datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)

def _main(argv, sd, now=NOW, capsys=None):
    return cli.main(argv, systemd=sd, now=lambda: now)

def test_lease_prints_id_and_refuses_second_holder(p, sd, capsys):
    assert _main(["lease", "--holder", "yupi", "--purpose", "t", "--ttl", "1h"], sd) == 0
    lease_id = capsys.readouterr().out.strip()
    assert read_lease(p, NOW).data["lease_id"] == lease_id
    assert _main(["lease", "--holder", "tq", "--purpose", "t"], sd) == 2

def test_renew_and_release_need_lease_id(p, sd, capsys):
    _main(["lease", "--holder", "yupi", "--purpose", "t", "--ttl", "1h"], sd)
    lease_id = capsys.readouterr().out.strip()
    assert _main(["renew", "--lease-id", "wrong", "--ttl", "2h"], sd) == 2
    assert _main(["renew", "--lease-id", lease_id, "--ttl", "2h"], sd) == 0
    assert read_lease(p, NOW).data["generation"] == 2
    assert _main(["release", "--lease-id", lease_id], sd) == 0
    assert read_lease(p, NOW).kind == "absent"

def test_wait_needs_ack_and_live_lease(p, sd, capsys):
    _main(["lease", "--holder", "yupi", "--purpose", "t", "--ttl", "1h"], sd)
    lease_id = capsys.readouterr().out.strip()
    assert _main(["wait", "--lease-id", lease_id, "--timeout", "0s"], sd) == 3
    ledger.append(p, {"action_id": "e1", "phase": "outcome", "action": "ensure_stopped",
                      "episode_id": lease_id, "outcome": "ok", "by": "heartbeat:qwen", "at": NOW.isoformat()})
    sd.units["hamutay-llama-server.service"] = {"active_state": "inactive", "sub_state": "dead", "load_state": "loaded", "invocation_id": ""}
    assert _main(["wait", "--lease-id", lease_id, "--timeout", "0s"], sd) == 0
    # expired lease: refused even with the ack
    assert _main(["wait", "--lease-id", lease_id, "--timeout", "0s"], sd, now=NOW + timedelta(hours=2)) == 3

def test_status_reports_free(p, sd, capsys):
    assert _main(["status"], sd) == 0
    assert "free" in capsys.readouterr().out

def test_force_stop_refuses_while_heartbeat_holds_lock(p, sd, tmp_path, capsys):
    door = tmp_path / "door"; door.mkdir()
    p.dir.mkdir(parents=True, exist_ok=True); p.door.write_text(str(door))
    _main(["lease", "--holder", "yupi", "--purpose", "t", "--ttl", "1h"], sd)
    lease_id = capsys.readouterr().out.strip()
    hb_lock = door / "session.jsonl.events.jsonl.heartbeat.lock"
    with hb_lock.open("w") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert _main(["force-stop", "--lease-id", lease_id, "--by", "tony", "--reason", "r"], sd) == 4
    sd.units["hamutay-llama-server.service"] = {"active_state": "active", "sub_state": "running", "load_state": "loaded", "invocation_id": "i"}
    assert _main(["force-stop", "--lease-id", lease_id, "--by", "tony", "--reason", "r"], sd) == 0
    store_lines = (door / "session.jsonl.events.jsonl").read_text().splitlines()
    rest = json.loads(store_lines[0])
    assert rest["status"] == "resting" and rest["reason"] == "substrate_lent" and rest["detail"]["source"] == "force_stop"
    order = [c[0] for c in sd.calls if c[0] == "stop"]
    assert order == ["stop"]
    assert any(r["action"] == "force_stop" and r.get("outcome") == "ok" for r in ledger.rows(p))
