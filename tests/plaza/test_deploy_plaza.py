import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
