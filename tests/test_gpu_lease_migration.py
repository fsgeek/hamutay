import json, os, re, stat, subprocess, textwrap
from pathlib import Path
import pytest
from hamutay.gpu_lease import cli

ROOT = Path(__file__).resolve().parents[1]

def fake_systemctl(tmp_path, state):
    """A systemctl that answers from a JSON state file and records stops."""
    script = tmp_path / "systemctl"
    script.write_text(textwrap.dedent(f'''\
        #!/usr/bin/env bash
        st="{tmp_path}/state.json"
        case "$2" in
          is-enabled) python3 -c "import json;print(json.load(open('$st'))['enabled'])" ;;
          show) python3 -c "import json,sys;d=json.load(open('$st'));[print(k+'='+d['show'].get(sys.argv[1],{{}}).get(k,'')) for k in sys.argv[2].split(',')]" "${{@: -1}}" "$4" ;;
          stop) echo "$3" >> "{tmp_path}/stops" ;;
        esac
    '''))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "state.json").write_text(json.dumps(state))
    return script

def test_check_script_accepts_static_and_rejects_enabled(tmp_path, monkeypatch):
    units = tmp_path / "units"; units.mkdir()
    (units / "hamutay-llama-server.service").write_text("[Service]\nExecStart=/bin/true\n")
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "st")); (tmp_path / "st" / "gpu").mkdir(parents=True)
    (tmp_path / "st" / "gpu" / "4090.door").write_text(str(tmp_path))
    good = {"enabled": "static", "show": {"hamutay-heartbeat@qwen": {"Requires": "", "Wants": "", "After": "network-online.target"},
                                          "hamutay-llama-server": {"WantedBy": "", "RequiredBy": ""}}}
    sc = fake_systemctl(tmp_path, good)
    jc = fake_journalctl(tmp_path, with_note=True)
    r = subprocess.run(["bash", str(ROOT / "deploy/check-gpu-lease.sh"), "--systemctl", str(sc), "--unit-paths", str(units), "--journalctl", str(jc)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    bad = dict(good, enabled="enabled"); (tmp_path / "state.json").write_text(json.dumps(bad))
    assert subprocess.run(["bash", str(ROOT / "deploy/check-gpu-lease.sh"), "--systemctl", str(sc), "--unit-paths", str(units), "--journalctl", str(jc)]).returncode != 0
    (tmp_path / "state.json").write_text(json.dumps(good))
    (units / "default.target.wants").mkdir(); os.symlink(units / "hamutay-llama-server.service", units / "default.target.wants" / "hamutay-llama-server.service")
    assert subprocess.run(["bash", str(ROOT / "deploy/check-gpu-lease.sh"), "--systemctl", str(sc), "--unit-paths", str(units), "--journalctl", str(jc)]).returncode != 0

def test_migrate_quiesce_stops_only_when_no_running(tmp_path):
    door = tmp_path / "door"; door.mkdir()
    store = door / "session.jsonl.events.jsonl"
    store.write_text(json.dumps({"record_type": "event_status", "event_id": "e", "status": "running"}) + "\n")
    sc = fake_systemctl(tmp_path, {"enabled": "static", "show": {}})
    rc = cli.main(["migrate-quiesce", "--door", str(door), "--unit", "hamutay-heartbeat@qwen", "--timeout", "0s", "--systemctl", str(sc)])
    assert rc == 1 and not (tmp_path / "stops").exists()
    with store.open("a") as f:
        f.write(json.dumps({"record_type": "event_status", "event_id": "e", "status": "completed"}) + "\n")
    rc = cli.main(["migrate-quiesce", "--door", str(door), "--unit", "hamutay-heartbeat@qwen", "--timeout", "0s", "--systemctl", str(sc)])
    assert rc == 0 and (tmp_path / "stops").read_text().strip() == "hamutay-heartbeat@qwen"

def test_unit_files_have_no_dependency_on_the_server():
    server = (ROOT / "deploy/hamutay-llama-server.service").read_text()
    assert "[Install]" not in server and "WantedBy" not in server
    dropin = (ROOT / "deploy/hamutay-heartbeat@qwen.service.d/override.conf").read_text()
    active = [l for l in dropin.splitlines() if l.strip() and not l.strip().startswith("#")]
    assert not any(l.startswith(("Requires=", "Wants=", "After=", "BindsTo=")) for l in active)
    assert json.loads((ROOT / "deploy/door.json.qwen").read_text()) == {"gpu_lease": "4090"}

def test_gitignore_excludes_active_door_file():
    assert "community/*/door.json" in (ROOT / ".gitignore").read_text()


def fake_systemctl_py(tmp_path, state):
    """A Python-script fake systemctl, for the migration runbook tests where
    robust argv parsing (positional unit names with '@') matters more than
    matching the bash fake's exact quoting."""
    script = tmp_path / "systemctl"
    script.write_text(textwrap.dedent(f'''\
        #!/usr/bin/env python3
        import json, sys
        st = json.load(open({str(tmp_path / "state.json")!r}))
        args = sys.argv[1:]
        # drop leading --user if present
        if args and args[0] == "--user":
            args = args[1:]
        cmd = args[0]
        if cmd == "is-enabled":
            print(st["enabled"])
        elif cmd == "show":
            # show -p Prop1,Prop2 UNIT
            props = args[2].split(",")
            unit = args[3]
            d = st.get("show", {{}}).get(unit, {{}})
            for k in props:
                print(f"{{k}}={{d.get(k, '')}}")
        elif cmd == "stop":
            unit = args[1]
            with open({str(tmp_path / "stops")!r}, "a") as f:
                f.write(unit + "\\n")
        elif cmd == "start":
            unit = args[1]
            with open({str(tmp_path / "starts")!r}, "a") as f:
                f.write(unit + "\\n")
        elif cmd == "disable":
            unit = args[1]
            with open({str(tmp_path / "disables")!r}, "a") as f:
                f.write(unit + "\\n")
        elif cmd == "daemon-reload":
            pass
    '''))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "state.json").write_text(json.dumps(state))
    return script


def test_migrate_script_dry_run_prints_seven_steps_and_never_calls_real_systemctl(tmp_path, monkeypatch):
    good = {"enabled": "static", "show": {"hamutay-heartbeat@qwen": {"Requires": "", "Wants": "", "After": "network-online.target"},
                                          "hamutay-llama-server": {"WantedBy": "", "RequiredBy": ""}}}
    sc = fake_systemctl_py(tmp_path, good)
    unit_dir = tmp_path / "units"; unit_dir.mkdir()
    fake_root = tmp_path / "root"
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "state"))
    env = dict(os.environ)
    env["AYLLU_STATE_DIR"] = str(tmp_path / "state")
    r = subprocess.run(
        ["bash", str(ROOT / "deploy/migrate-gpu-lease.sh"), "--dry-run",
         "--systemctl", str(sc), "--unit-dir", str(unit_dir), "--unit-paths", str(unit_dir),
         "--root", str(fake_root)],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    steps = [f"step {n}" for n in range(1, 8)]
    positions = [r.stdout.find(s) for s in steps]
    assert all(p != -1 for p in positions), r.stdout
    assert positions == sorted(positions), r.stdout
    # dry-run must never actually invoke the fake (or real) systemctl
    assert not (tmp_path / "stops").exists()
    assert not (tmp_path / "starts").exists()
    assert not (tmp_path / "disables").exists()


def test_migrate_script_aborts_before_door_json_when_quiesce_fails(tmp_path, monkeypatch):
    good = {"enabled": "static", "show": {"hamutay-heartbeat@qwen": {"Requires": "", "Wants": "", "After": "network-online.target"},
                                          "hamutay-llama-server": {"WantedBy": "", "RequiredBy": ""}}}
    sc = fake_systemctl_py(tmp_path, good)
    unit_dir = tmp_path / "units"; unit_dir.mkdir()
    fake_root = tmp_path / "root"
    community = fake_root / "community" / "qwen"; community.mkdir(parents=True)
    store = community / "session.jsonl.events.jsonl"
    store.write_text(json.dumps({"record_type": "event_status", "event_id": "e", "status": "running"}) + "\n")
    state_dir = tmp_path / "state"
    env = dict(os.environ)
    env["AYLLU_STATE_DIR"] = str(state_dir)
    r = subprocess.run(
        ["bash", str(ROOT / "deploy/migrate-gpu-lease.sh"),
         "--systemctl", str(sc), "--unit-dir", str(unit_dir), "--unit-paths", str(unit_dir),
         "--root", str(fake_root), "--quiesce-timeout", "0s"],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert not (community / "door.json").exists()


def test_migrate_script_step3_scans_every_unit_paths_directory_not_just_unit_dir(tmp_path):
    """Finding 1: reading unit paths is not mutation; the spec requires every
    directory systemd-analyze --user unit-paths reports, not only the dir the
    migration writes into. Put a violating drop-in in a SECOND directory (not
    --unit-dir) and pass both via --unit-paths; the migration must still catch it."""
    good = {"enabled": "static", "show": {"hamutay-heartbeat@qwen": {"Requires": "", "Wants": "", "After": "network-online.target"},
                                          "hamutay-llama-server": {"WantedBy": "", "RequiredBy": ""}}}
    sc = fake_systemctl_py(tmp_path, good)
    unit_dir = tmp_path / "units"; unit_dir.mkdir()
    other_dir = tmp_path / "other-unit-path"; other_dir.mkdir()
    (other_dir / "stray.conf").write_text("[Unit]\nWants=hamutay-llama-server.service\n")
    fake_root = tmp_path / "root"
    env = dict(os.environ)
    env["AYLLU_STATE_DIR"] = str(tmp_path / "state")
    r = subprocess.run(
        ["bash", str(ROOT / "deploy/migrate-gpu-lease.sh"),
         "--systemctl", str(sc), "--unit-dir", str(unit_dir),
         "--unit-paths", f"{unit_dir} {other_dir}", "--root", str(fake_root)],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert "stray.conf" in r.stderr or "stray.conf" in r.stdout


def test_check_and_migrate_scripts_catch_an_indented_directive(tmp_path):
    """Finding 2: Requires=/Wants=/BindsTo= anchored at column 0 misses an
    indented directive, which systemd honours the same as a flush one."""
    units = tmp_path / "units"; units.mkdir()
    (units / "hamutay-llama-server.service").write_text("[Service]\nExecStart=/bin/true\n")
    (units / "indented.conf").write_text("[Unit]\n\tWants=hamutay-llama-server.service\n")
    good = {"enabled": "static", "show": {"hamutay-heartbeat@qwen": {"Requires": "", "Wants": "", "After": "network-online.target"},
                                          "hamutay-llama-server": {"WantedBy": "", "RequiredBy": ""}}}
    sc = fake_systemctl(tmp_path, good)
    r = subprocess.run(["bash", str(ROOT / "deploy/check-gpu-lease.sh"), "--systemctl", str(sc), "--unit-paths", str(units)],
                        capture_output=True, text=True)
    assert r.returncode != 0
    assert "indented.conf" in r.stderr

    sc2 = fake_systemctl_py(tmp_path, good)
    fake_root = tmp_path / "root"
    env = dict(os.environ)
    env["AYLLU_STATE_DIR"] = str(tmp_path / "state2")
    r2 = subprocess.run(
        ["bash", str(ROOT / "deploy/migrate-gpu-lease.sh"),
         "--systemctl", str(sc2), "--unit-dir", str(units), "--unit-paths", str(units),
         "--root", str(fake_root)],
        capture_output=True, text=True, env=env, cwd=str(ROOT),
    )
    assert r2.returncode != 0, r2.stdout + r2.stderr
    assert "indented.conf" in r2.stderr


def fake_journalctl(tmp_path, *, with_note: bool):
    script = tmp_path / "journalctl"
    line = "hamutay-heartbeat@qwen[1]: {\"heartbeat\": \"launch\", \"note\": \"gpu lease: 4090 (door.json)\"}" \
        if with_note else "hamutay-heartbeat@qwen[1]: {\"heartbeat\": \"launch\", \"note\": \"quiet\"}"
    script.write_text(textwrap.dedent(f'''\
        #!/usr/bin/env bash
        echo {line!r}
    '''))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_check_script_requires_the_gpu_lease_launch_note(tmp_path, monkeypatch):
    """Finding 3: check-gpu-lease.sh must confirm the launch note, not just
    the unit graph — a journal without 'gpu lease: 4090' means check fails."""
    units = tmp_path / "units"; units.mkdir()
    (units / "hamutay-llama-server.service").write_text("[Service]\nExecStart=/bin/true\n")
    monkeypatch.setenv("AYLLU_STATE_DIR", str(tmp_path / "st")); (tmp_path / "st" / "gpu").mkdir(parents=True)
    (tmp_path / "st" / "gpu" / "4090.door").write_text(str(tmp_path))
    good = {"enabled": "static", "show": {"hamutay-heartbeat@qwen": {"Requires": "", "Wants": "", "After": "network-online.target"},
                                          "hamutay-llama-server": {"WantedBy": "", "RequiredBy": ""}}}
    sc = fake_systemctl(tmp_path, good)

    jc_good = fake_journalctl(tmp_path, with_note=True)
    r = subprocess.run(["bash", str(ROOT / "deploy/check-gpu-lease.sh"), "--systemctl", str(sc),
                         "--unit-paths", str(units), "--journalctl", str(jc_good)],
                        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

    jc_bad = fake_journalctl(tmp_path, with_note=False)
    r2 = subprocess.run(["bash", str(ROOT / "deploy/check-gpu-lease.sh"), "--systemctl", str(sc),
                          "--unit-paths", str(units), "--journalctl", str(jc_bad)],
                         capture_output=True, text=True)
    assert r2.returncode != 0
    assert "launch note" in r2.stderr


def test_checkpoint_script_gpu_ledger_absent_and_present(tmp_path):
    """Finding 4: the checkpoint script's GPU block, exercised end to end in a
    throwaway git repo with --no-commit so no real commit or OTS hook fires."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    door = repo / "community" / "x"; door.mkdir(parents=True)
    (door / "session.jsonl").write_text('{"a": 1}\n')

    state_dir = tmp_path / "state"
    env = dict(os.environ)
    env["AYLLU_STATE_DIR"] = str(state_dir)

    # 1) absent ledger: the script notes it and skips; no community/gpu/.
    r = subprocess.run(
        ["bash", str(ROOT / "deploy/checkpoint-community-log.sh"), "--no-commit", "--root", str(repo)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "skipping the GPU lease checkpoint" in r.stderr
    assert not (repo / "community" / "gpu").exists()

    # 2) present ledger: digested into community/gpu/CHECKPOINTS.txt, and the
    # ledger's bytes never land in the repo tree.
    (state_dir / "gpu").mkdir(parents=True)
    ledger = state_dir / "gpu" / "4090.ledger.jsonl"
    ledger.write_text('{"event": "lease"}\n{"event": "release"}\n')

    r2 = subprocess.run(
        ["bash", str(ROOT / "deploy/checkpoint-community-log.sh"), "--no-commit", "--root", str(repo)],
        capture_output=True, text=True, env=env,
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr
    checkpoints = repo / "community" / "gpu" / "CHECKPOINTS.txt"
    assert checkpoints.exists()
    lines = checkpoints.read_text().splitlines()
    assert len(lines) == 1
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ 4090\.ledger\.jsonl:[0-9a-f]{64}:\d+$", lines[0]), lines[0]

    # the ledger bytes themselves were never copied anywhere under repo/
    for path in repo.rglob("*"):
        if path.is_file():
            assert path.read_bytes() != ledger.read_bytes() or path == checkpoints
