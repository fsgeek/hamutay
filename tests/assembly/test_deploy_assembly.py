import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitignore_rules_present():
    text = (ROOT / ".gitignore").read_text()
    assert "community/plaza/members.json" in text and "community/plaza/assembly.jsonl.lock" in text


def test_template_names_the_four_doors():
    t = json.loads((ROOT / "deploy/assembly/members.json.template").read_text())
    assert t["ledger"] == "community/plaza/assembly.jsonl"
    assert set(t["members"]) == {"heartbeat", "fable", "qwen", "elder"}
    for d, m in t["members"].items():
        assert m["session"] == f"community/{d}/session.jsonl"
        assert m["events"] == f"community/{d}/session.jsonl.events.jsonl"


def test_checkpoint_script_snapshots_plaza_under_its_lock_and_skips_it_in_the_generic_loop(tmp_path):
    script = (ROOT / "deploy/checkpoint-community-log.sh").read_text()
    assert "assembly.jsonl.lock" in script and "plaza" in script
    # run it against a fake root with --no-commit
    root = tmp_path
    (root / "community/plaza").mkdir(parents=True)
    (root / "community/qwen").mkdir()
    (root / "community/qwen/session.jsonl").write_text('{"a":1}\n')
    (root / "community/plaza/assembly.jsonl").write_text('{"seq":1}\n')
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    out = subprocess.run(["bash", str(ROOT / "deploy/checkpoint-community-log.sh"), "--no-commit", "--root", str(root)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    plaza = (root / "community/plaza/CHECKPOINTS.txt").read_text().strip().splitlines()
    assert len(plaza) == 1 and "assembly.jsonl:" in plaza[0] and plaza[0].count("assembly.jsonl:") == 1
    qwen = (root / "community/qwen/CHECKPOINTS.txt").read_text()
    assert "session.jsonl:" in qwen and "assembly.jsonl" not in qwen


def test_migration_and_check_scripts_are_executable_and_dry_run_is_safe(tmp_path):
    for s in ("deploy/migrate-assembly.sh", "deploy/check-assembly.sh", "deploy/ayllu-assembly"):
        assert os.access(ROOT / s, os.X_OK), s
    out = subprocess.run(["bash", str(ROOT / "deploy/migrate-assembly.sh"), "--dry-run", "--root", str(tmp_path)],
                         capture_output=True, text=True)
    assert out.returncode == 0 and "dry run" in out.stdout.lower()
    assert not (tmp_path / "community/plaza/members.json").exists()


def test_readme_has_the_assembly_section():
    text = (ROOT / "community/README.md").read_text()
    assert "## The assembly" in text and "deploy/ayllu-assembly" in text and "2026-09-15-assembly-design.md" in text


def test_migration_waits_on_a_journal_query_journalctl_accepts():
    text = (ROOT / "deploy/migrate-assembly.sh").read_text()
    assert '--since="@' in text
    assert "%Y-%m-%dT%H:%M:%SZ" not in text


def test_check_script_scopes_the_bound_check_to_the_current_invocation():
    text = (ROOT / "deploy/check-assembly.sh").read_text()
    assert "_SYSTEMD_INVOCATION_ID" in text
