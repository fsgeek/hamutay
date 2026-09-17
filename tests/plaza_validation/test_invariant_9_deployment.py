import json
import os
import shutil
import subprocess
from pathlib import Path

from hamutay.heartbeat import source_note
from tests.plaza_validation.conftest import write_members


REPOSITORY = Path(__file__).resolve().parents[2]


def _copy_script(root: Path, name: str) -> Path:
    deploy = root / "deploy"
    deploy.mkdir(parents=True, exist_ok=True)
    target = deploy / name
    shutil.copy2(REPOSITORY / "deploy" / name, target)
    target.chmod(target.stat().st_mode | 0o111)
    return target


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _git_commit(root: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git", "-c", "user.email=validation@example.invalid", "-c", "user.name=Validation",
            "-c", "commit.gpgsign=false", "commit", "-q", "-m", "fixture",
        ],
        cwd=root,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


def test_invariant_9_migration_dry_runs_make_no_change(tmp_path):
    root = tmp_path / "house"
    root.mkdir()
    script = _copy_script(root, "migrate-plaza.sh")
    write_members(root, plaza=False)
    merge = _git_commit(root)
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    _write_executable(
        fakebin / "systemctl",
        "#!/bin/sh\n"
        "case \"$*\" in *\" show \"*) echo invocation-validation;; esac\n"
        "exit 0\n",
    )
    _write_executable(
        fakebin / "journalctl",
        "#!/bin/sh\n"
        "echo \"source: commit $INV_SHA clean\"\n",
    )
    environment = os.environ.copy()
    environment.update({"PATH": f"{fakebin}:{environment['PATH']}", "INV_SHA": merge})

    for phase in ("--phase-one", "--phase-two"):
        before = _snapshot(root)
        completed = subprocess.run(
            ["bash", str(script), phase, "--dry-run", "--root", str(root), "--merge", merge],
            capture_output=True,
            text=True,
            env=environment,
        )
        assert completed.returncode == 0, completed.stderr
        assert "dry run" in completed.stdout.lower()
        assert _snapshot(root) == before


def test_invariant_9_candidate_snapshot_refusal_precedes_stop_and_rename(tmp_path):
    root = tmp_path / "house"
    root.mkdir()
    script = _copy_script(root, "migrate-plaza.sh")
    members = write_members(root, plaza=False)
    merge = _git_commit(root)

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    service_log = tmp_path / "systemctl.log"
    _write_executable(
        fakebin / "systemctl",
        "#!/bin/sh\n"
        "echo \"$*\" >> \"$SYSTEMCTL_LOG\"\n"
        "case \"$*\" in *\" show \"*) echo invocation-validation;; esac\n"
        "exit 0\n",
    )
    _write_executable(
        fakebin / "journalctl",
        "#!/bin/sh\n"
        "echo \"source: commit $INV_SHA clean\"\n",
    )
    _write_executable(
        fakebin / "uv",
        "#!/bin/sh\n"
        "[ \"$1\" = run ] && shift\n"
        "exec \"$@\"\n",
    )

    fake_package = tmp_path / "fake-package"
    (fake_package / "hamutay/assembly").mkdir(parents=True)
    (fake_package / "hamutay/__init__.py").write_text("")
    (fake_package / "hamutay/assembly/__init__.py").write_text("")
    (fake_package / "hamutay/assembly/binding.py").write_text(
        "import json\n"
        "from pathlib import Path\n"
        "class Config:\n"
        "    def __init__(self, root): self.root = Path(root).resolve()\n"
        "    def snapshot(self):\n"
        "        raw = json.loads((self.root / 'community/plaza/members.json').read_text())\n"
        "        out = {}\n"
        "        for name, member in raw['members'].items():\n"
        "            out[name] = {k: str((self.root / v).resolve()) for k, v in member.items()}\n"
        "        if 'plaza-cand-' in str(self.root):\n"
        "            out[next(iter(out))]['events'] += '.changed'\n"
        "        return out\n"
        "def load_members(root): return Config(root)\n"
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fakebin}:{environment['PATH']}",
            "PYTHONPATH": str(fake_package),
            "SYSTEMCTL_LOG": str(service_log),
            "INV_SHA": merge,
        }
    )
    original = members.read_bytes()
    completed = subprocess.run(
        ["bash", str(script), "--phase-two", "--root", str(root), "--merge", merge],
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode != 0
    assert "candidate" in (completed.stdout + completed.stderr).lower()
    assert "nothing installed" in (completed.stdout + completed.stderr).lower()
    assert members.read_bytes() == original
    assert "plaza" not in json.loads(members.read_text())
    calls = service_log.read_text() if service_log.exists() else ""
    assert " stop " not in f" {calls} "
    assert not members.with_name("members.json.candidate").exists()


def test_invariant_9_phase_one_check_accepts_clean_descendant_and_rejects_dirty(tmp_path):
    root = tmp_path / "house"
    root.mkdir()
    check = _copy_script(root, "check-plaza.sh")
    (root / ".gitignore").write_text(
        "community/plaza/plaza.jsonl\ncommunity/plaza/plaza.jsonl.lock\n"
    )
    (root / "deploy/checkpoint-community-log.sh").write_text(
        "assembly.jsonl.lock\nplaza.jsonl.lock\n"
    )
    merge = _git_commit(root)

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    _write_executable(
        fakebin / "systemctl",
        "#!/bin/sh\n"
        "case \"$*\" in *\" show \"*) echo invocation-validation;; esac\n"
        "exit 0\n",
    )
    _write_executable(
        fakebin / "journalctl",
        "#!/bin/sh\n"
        "echo \"source: commit $INV_SHA $INV_STATE\"\n",
    )
    environment = os.environ.copy()
    environment.update({"PATH": f"{fakebin}:{environment['PATH']}", "INV_SHA": merge})

    clean = subprocess.run(
        ["bash", str(check), "--phase-one", "--merge", merge],
        capture_output=True,
        text=True,
        env={**environment, "INV_STATE": "clean"},
    )
    assert clean.returncode == 0, clean.stdout + clean.stderr
    dirty = subprocess.run(
        ["bash", str(check), "--phase-one", "--merge", merge],
        capture_output=True,
        text=True,
        env={**environment, "INV_STATE": "dirty"},
    )
    assert dirty.returncode != 0
    assert "FAIL" in dirty.stdout


def test_invariant_9_source_launch_note_reports_commit_and_cleanliness(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "tracked").write_text("clean")
    commit = _git_commit(root)
    assert source_note(root) == f"source: commit {commit} clean"
    (root / "tracked").write_text("dirty")
    assert source_note(root) == f"source: commit {commit} dirty"
    assert source_note(tmp_path / "not-a-repository") == "source: unknown"


def test_invariant_11_checkpoint_takes_assembly_and_plaza_locks_in_separate_scopes(tmp_path):
    root = tmp_path / "house"
    root.mkdir()
    script = _copy_script(root, "checkpoint-community-log.sh")
    plaza = root / "community/plaza"
    plaza.mkdir(parents=True)
    (plaza / "assembly.jsonl").write_text('{"seq":1}\n')
    (plaza / "plaza.jsonl").write_text('{"seq":1}\n')
    _git_commit(root)

    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    lock_log = tmp_path / "locks.log"
    marker = tmp_path / "lock-held"
    _write_executable(
        fakebin / "flock",
        "#!/bin/sh\n"
        "if [ -e \"$LOCK_MARKER\" ]; then echo nested >> \"$LOCK_LOG\"; exit 99; fi\n"
        "lock=$1; shift\n"
        "echo \"begin:$lock\" >> \"$LOCK_LOG\"\n"
        ": > \"$LOCK_MARKER\"\n"
        "\"$@\"\n"
        "rc=$?\n"
        "rm -f \"$LOCK_MARKER\"\n"
        "echo \"end:$lock\" >> \"$LOCK_LOG\"\n"
        "exit $rc\n",
    )
    state = tmp_path / "state"
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fakebin}:{environment['PATH']}",
            "LOCK_LOG": str(lock_log),
            "LOCK_MARKER": str(marker),
            "AYLLU_STATE_DIR": str(state),
        }
    )
    completed = subprocess.run(
        ["bash", str(script), "--no-commit", "--root", str(root)],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = lock_log.read_text().splitlines()
    assert lines == [
        "begin:community/plaza/assembly.jsonl.lock",
        "end:community/plaza/assembly.jsonl.lock",
        "begin:community/plaza/plaza.jsonl.lock",
        "end:community/plaza/plaza.jsonl.lock",
    ]
    checkpoint = (plaza / "CHECKPOINTS.txt").read_text().strip()
    assert "assembly.jsonl:" in checkpoint
    assert "plaza.jsonl:" in checkpoint
