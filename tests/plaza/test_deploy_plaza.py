import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _git(root, *args, check=True):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=check)


def _init_repo_with_members(root: Path) -> str:
    """A tmp_path git repo with a committed community/plaza/members.json (no plaza key),
    doors present but idle, and no other uncommitted changes -- everything migrate-plaza.sh's
    live phase-two path checks for before it touches anything. Returns the HEAD sha (used as
    a trivially-valid --merge, since a commit is its own ancestor)."""
    _git(root, "init", "-q")
    (root / "community/plaza").mkdir(parents=True)
    for d in ("heartbeat", "fable", "elder", "qwen"):
        (root / f"community/{d}").mkdir()
    (root / "community/plaza/members.json").write_text(json.dumps({
        "ledger": "community/plaza/assembly.jsonl",
        "members": {d: {"session": f"community/{d}/session.jsonl",
                         "events": f"community/{d}/session.jsonl.events.jsonl"}
                    for d in ("heartbeat", "fable", "elder", "qwen")},
    }))
    _git(root, "add", "community")
    _git(root, "-c", "user.email=a@b.c", "-c", "user.name=x", "commit", "-q", "--no-gpg-sign", "-m", "c1")
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _write_shim(bin_dir: Path, name: str, body: str):
    p = bin_dir / name
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def test_gitignore_and_shims():
    text = (ROOT / ".gitignore").read_text()
    assert "community/plaza/plaza.jsonl\n" in text and "community/plaza/plaza.jsonl.lock" in text
    for s in ("deploy/migrate-plaza.sh", "deploy/check-plaza.sh", "deploy/ayllu-plaza"):
        assert os.access(ROOT / s, os.X_OK), s


def test_checkpoint_digests_the_plaza_under_its_own_lock_in_a_separate_scope(tmp_path):
    script = (ROOT / "deploy/checkpoint-community-log.sh").read_text()
    a, b = script.index("assembly.jsonl.lock"), script.index("plaza.jsonl.lock")
    assert a < b
    between = script[a:b]
    assert "flock" in between and between.count("flock") >= 1     # the assembly scope closes before the plaza's opens
    (tmp_path / "community/plaza").mkdir(parents=True)
    (tmp_path / "community/plaza/assembly.jsonl").write_text('{"seq":1}\n')
    (tmp_path / "community/plaza/plaza.jsonl").write_text('{"seq":1}\n')
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    out = subprocess.run(["bash", str(ROOT / "deploy/checkpoint-community-log.sh"), "--no-commit", "--root", str(tmp_path)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    line = (tmp_path / "community/plaza/CHECKPOINTS.txt").read_text().strip()
    assert "assembly.jsonl:" in line and "plaza.jsonl:" in line and line.count("\n") == 0


def test_migration_dry_runs_and_phase_two_never_installs_a_changed_snapshot(tmp_path):
    for s in ("--phase-one", "--phase-two"):
        out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), s, "--dry-run", "--root", str(tmp_path)],
                             capture_output=True, text=True)
        assert out.returncode == 0 and "dry run" in out.stdout.lower(), out
    script = (ROOT / "deploy/migrate-plaza.sh").read_text()
    for needle in ("snapshot()", "os.replace", "fsync", "merge-base --is-ancestor", "systemctl --user stop",
                   "plaza: door", "source: commit"):
        assert needle in script, needle
    assert "sed" not in script.replace("used", "")            # the JSON edit is Python, never sed


def test_readme_has_the_plaza_section():
    text = (ROOT / "community/README.md").read_text()
    assert "## The plaza" in text and "deploy/ayllu-plaza" in text and "--through-seq" in text


def test_readme_states_the_cli_by_is_a_claimed_unauthenticated_label():
    text = (ROOT / "community/README.md").read_text()
    assert "unauthenticated" in text and "via: cli" in text


def test_dry_run_previews_the_real_decision_for_a_non_ancestor_merge(tmp_path):
    _init_repo_with_members(tmp_path)
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), "--phase-two", "--dry-run",
                           "--root", str(tmp_path), "--merge", "0" * 40],
                          capture_output=True, text=True)
    assert out.returncode == 0, out
    low = out.stdout.lower()
    assert "would refuse:" in low and "descend" in low


def test_dry_run_previews_ok_for_a_valid_ancestor_merge(tmp_path):
    head = _init_repo_with_members(tmp_path)
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), "--phase-two", "--dry-run",
                           "--root", str(tmp_path), "--merge", head],
                          capture_output=True, text=True)
    assert out.returncode == 0, out
    assert "ok:" in out.stdout.lower()
    assert f"descends from {head}" in out.stdout


def test_idleness_two_pass_refuses_before_touching_anything_when_a_later_door_is_busy(tmp_path):
    _init_repo_with_members(tmp_path)
    (tmp_path / "community/qwen/session.jsonl.events.jsonl").write_text(
        json.dumps({"record_type": "event_status", "event_id": "e1", "status": "running"}) + "\n")
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), "--phase-one", "--root", str(tmp_path)],
                          capture_output=True, text=True)
    assert out.returncode != 0, out
    assert "running wake" in out.stdout
    assert "restart" not in out.stdout.lower()      # qwen (busy) sorts last in DOORS: nothing was restarted
    # members.json is untouched -- the up-front pass ran before anything else was touched.
    members = json.loads((tmp_path / "community/plaza/members.json").read_text())
    assert "plaza" not in members


def test_phase_two_idleness_two_pass_also_refuses_before_touching_anything(tmp_path):
    """Same as above, for phase two's live run: the up-front idleness pass runs (and
    refuses on a busy door) before any door is stopped. Needs journalctl/systemctl shims
    so the earlier phase-one-completeness gate is satisfied and idleness is actually reached."""
    root = tmp_path / "root"
    root.mkdir()
    head = _init_repo_with_members(root)
    (root / "community/qwen/session.jsonl.events.jsonl").write_text(
        json.dumps({"record_type": "event_status", "event_id": "e1", "status": "running"}) + "\n")
    _git(root, "add", "community")
    _git(root, "-c", "user.email=a@b.c", "-c", "user.name=x", "commit", "-q", "--no-gpg-sign", "-m", "busy")
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "systemctl.log"
    _write_shim(bin_dir, "systemctl", f"""#!/usr/bin/env bash
echo "$*" >> {log}
if [ "$1" = "--user" ] && [ "$2" = "show" ]; then echo "InvocationID=deadbeef"; exit 0; fi
if [ "$1" = "--user" ] && [ "$2" = "is-active" ]; then exit 0; fi
exit 0
""")
    _write_shim(bin_dir, "journalctl", f"""#!/usr/bin/env bash
echo "source: commit {head} clean"
""")
    env = dict(os.environ); env["PATH"] = f"{bin_dir}:{env['PATH']}"
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), "--phase-two",
                           "--root", str(root), "--merge", head],
                          capture_output=True, text=True, env=env)
    assert out.returncode != 0, out
    assert "running wake" in out.stdout
    assert not log.exists() or "stop" not in log.read_text()   # nothing was stopped
    members = json.loads((root / "community/plaza/members.json").read_text())
    assert "plaza" not in members


def test_rollback_restores_members_json_and_restarts_only_the_doors_it_stopped(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    head = _init_repo_with_members(root)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "systemctl.log"
    _write_shim(bin_dir, "systemctl", f"""#!/usr/bin/env bash
echo "$*" >> {log}
if [ "$1" = "--user" ] && [ "$2" = "show" ]; then echo "InvocationID=deadbeef"; exit 0; fi
if [ "$1" = "--user" ] && [ "$2" = "is-active" ]; then exit 0; fi
if [ "$*" = "--user stop hamutay-heartbeat@elder" ]; then
  echo "simulated failure" >&2; exit 1
fi
exit 0
""")
    _write_shim(bin_dir, "journalctl", f"""#!/usr/bin/env bash
echo "source: commit {head} clean"
""")
    env = dict(os.environ); env["PATH"] = f"{bin_dir}:{env['PATH']}"
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), "--phase-two",
                           "--root", str(root), "--merge", head],
                          capture_output=True, text=True, env=env)
    assert out.returncode != 0, out
    members = json.loads((root / "community/plaza/members.json").read_text())
    assert "plaza" not in members            # restored: the candidate (with the key) was never kept
    calls = log.read_text().splitlines()
    stopped = {c.rsplit("@", 1)[1] for c in calls if c.startswith("--user stop ")}
    started = {c.rsplit("@", 1)[1] for c in calls if c.startswith("--user start ")}
    assert stopped == {"heartbeat", "fable", "elder"}      # elder's stop is the one that failed
    assert started == {"heartbeat", "fable"}               # only the doors actually stopped come back


def test_rollback_stops_the_doors_it_started_when_verification_fails(tmp_path):
    """Spec §9: 'If any unit fails either check the script stops all four units,
    restores the previous members.json, starts the four units again, exits non-zero.'
    The journalctl stub withholds the `plaza: door <d> may send` note, so every door
    fails its post-start verification; every door the install started must be stopped
    again before the final restarts, and members.json must be back without the key."""
    root = tmp_path / "root"
    root.mkdir()
    head = _init_repo_with_members(root)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "systemctl.log"
    _write_shim(bin_dir, "systemctl", f"""#!/usr/bin/env bash
echo "$*" >> {log}
if [ "$1" = "--user" ] && [ "$2" = "show" ]; then echo "InvocationID=deadbeef"; exit 0; fi
if [ "$1" = "--user" ] && [ "$2" = "is-active" ]; then exit 0; fi
exit 0
""")
    # the source note is present (phase one passes) but the plaza note never is,
    # so the post-start verification loop times out on the first door.
    _write_shim(bin_dir, "journalctl", f"""#!/usr/bin/env bash
echo "source: commit {head} clean"
""")
    env = dict(os.environ); env["PATH"] = f"{bin_dir}:{env['PATH']}"
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-plaza.sh"), "--phase-two",
                           "--root", str(root), "--merge", head],
                          capture_output=True, text=True, env=env, timeout=600)
    assert out.returncode != 0, out
    assert "rolling back" in out.stdout, out.stdout
    members = json.loads((root / "community/plaza/members.json").read_text())
    assert "plaza" not in members            # restored to the pre-migration file

    calls = [c for c in log.read_text().splitlines() if c.startswith("--user stop ")
             or c.startswith("--user start ")]
    starts = [i for i, c in enumerate(calls) if c.startswith("--user start ")]
    stops = [i for i, c in enumerate(calls) if c.startswith("--user stop ")]
    # the install's four starts, then a stop of every started door, then the final starts
    first_start = starts[0]
    started_doors = {c.rsplit("@", 1)[1] for c in calls[first_start:first_start + 4]}
    assert started_doors == {"heartbeat", "fable", "elder", "qwen"}
    rollback_stops = [i for i in stops if i > first_start]
    assert rollback_stops, f"no door was stopped after the install starts: {calls}"
    stopped_again = {calls[i].rsplit("@", 1)[1] for i in rollback_stops}
    assert stopped_again == started_doors        # every started door is stopped again
    final_starts = [i for i in starts if i > max(rollback_stops)]
    assert final_starts, "the rollback never restarted the doors it stopped"
    assert max(rollback_stops) < min(final_starts)   # stopped before the final starts


def test_readme_carries_the_spec_seven_caveat_on_events_send_and_cross_references_it():
    """M8: spec §7 -- `events send` is byte-for-byte unchanged and still writes only
    to one door's store, 'it is now the wrong tool for anything a resident should be
    able to see, and the README says so'. The operations line carries the caveat and
    the plaza section cross-references it."""
    text = (ROOT / "community/README.md").read_text()
    ops = text.index("python -m hamutay.events send")
    plaza = text.index("## The plaza")
    assert ops < plaza
    caveat = "the wrong tool for anything a resident should be able to see"
    assert text.count(caveat) >= 2                     # on the ops line and in the plaza section
    assert caveat in text[ops:plaza]                   # the operations line carries it
    assert caveat in text[plaza:]                      # the plaza section cross-references it
    assert "hamutay.events send" in text[plaza:]
