"""Spec test 7: execute the real deployment check with isolated infrastructure."""
import os
import shutil
import subprocess
import sys

import pytest

from .helpers import REPO

SHA = "a" * 40


def executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


@pytest.fixture
def rollout(house_guests):
    root, cfg, _ = house_guests
    deploy = root / "deploy"
    deploy.mkdir()
    shutil.copyfile(REPO / "deploy/check-plaza.sh", deploy / "check-plaza.sh")
    shutil.copyfile(REPO / "deploy/checkpoint-community-log.sh", deploy / "checkpoint-community-log.sh")
    shutil.copyfile(REPO / ".gitignore", root / ".gitignore")
    cfg.plaza.write_text("")
    executable(deploy / "ayllu-plaza", "#!/bin/sh\nexit 0\n")
    bin_dir = root / "stub-bin"
    bin_dir.mkdir()
    executable(bin_dir / "systemctl", "#!/bin/sh\ncase \"$*\" in *InvocationID*) echo invocation;; *) exit 0;; esac\n")
    executable(bin_dir / "journalctl", f'''#!/bin/sh
echo "source: commit {SHA} ${{TEST_SOURCE_STATE:-clean}}"
for d in heartbeat fable elder qwen; do
  echo "plaza: door $d may send"
done
echo "guests 1"
''')
    executable(bin_dir / "git", '#!/bin/sh\nexit "${TEST_ANCESTRY_RC:-0}"\n')
    executable(bin_dir / "uv", f'#!/bin/sh\n[ "$1" = run ] && shift\n[ "$1" = python ] && shift\nexec "{sys.executable}" "$@"\n')
    # Stub only the readiness function for the shell's Python subprocess.
    # The real function's census behavior is independently tested separately.
    support = root / "python-stubs"
    support.mkdir()
    (support / "sitecustomize.py").write_text('''import os
from pathlib import Path
from hamutay.plaza import mcp
def carrier_unready(root, **kwargs):
    Path(os.environ["TEST_READY_CALLED"]).write_text(str(root))
    mode = os.environ.get("TEST_READY_MODE", "ready")
    if mode == "crash":
        raise RuntimeError("readiness-crash-sentinel")
    if mode == "unready":
        return ["guest:levadura pid 101 start 98765: readiness-unready-sentinel"]
    return []
mcp.carrier_unready = carrier_unready
''')
    env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
           "PYTHONPATH": str(support) + os.pathsep + str(REPO / "src"),
           "PYTHONDONTWRITEBYTECODE": "1", "TEST_READY_CALLED": str(root / "readiness-called")}
    return root, env


def check(rollout, **updates):
    root, env = rollout
    return subprocess.run(["bash", str(root / "deploy/check-plaza.sh"), "--carrier-ready", "--merge", SHA],
                          cwd=root, env={**env, **updates}, capture_output=True, text=True, timeout=15)


def test_carrier_ready_script_passes_with_clean_descendant_launches_and_ready_servers(rollout):
    root, _ = rollout
    result = check(rollout)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "readiness-called").read_text().rstrip("/") in (str(root), ".")


@pytest.mark.parametrize("mode,sentinel", [("unready", "readiness-unready-sentinel"), ("crash", "readiness-crash-sentinel")])
def test_script_fails_when_readiness_returns_failures_or_cannot_run(rollout, mode, sentinel):
    root, _ = rollout
    result = check(rollout, TEST_READY_MODE=mode)
    assert (root / "readiness-called").exists(), "script did not call carrier_unready"
    assert result.returncode != 0
    assert sentinel in result.stdout + result.stderr


@pytest.mark.parametrize("updates", [{"TEST_SOURCE_STATE": "dirty"}, {"TEST_ANCESTRY_RC": "1"}])
def test_script_still_requires_clean_phase_a_descendant_launches(rollout, updates):
    result = check(rollout, **updates)
    assert result.returncode != 0
    assert "source" in result.stdout and "FAIL" in result.stdout
    assert "unknown flag" not in result.stdout + result.stderr


def test_gate_and_reader_evidence_are_gitignored_including_future_paths(tmp_path):
    shutil.copyfile(REPO / ".gitignore", tmp_path / ".gitignore")
    init = subprocess.run(["git", "init", "-q", str(tmp_path)], capture_output=True, text=True, timeout=10)
    assert init.returncode == 0, init.stderr
    paths = ["community/plaza/carrier.enabled", "community/plaza/readers/mcp-101.json"]
    result = subprocess.run(["git", "check-ignore", "--no-index", *paths], cwd=tmp_path,
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == paths
