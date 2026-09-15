import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import write_json


ROOT = Path(__file__).resolve().parents[2]
MIGRATE = ROOT / "deploy" / "migrate-gpu-lease.sh"
CHECK = ROOT / "deploy" / "check-gpu-lease.sh"


def _executable(path, text):
    path.write_text("#!/bin/sh\nset -eu\n" + text)
    path.chmod(0o755)


def fake_commands(tmp_path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    _executable(fakebin / "systemctl", r'''
printf '%s\n' "$*" >> "$FAKE_SYSTEMCTL_LOG"
case "$*" in
  *WorkingDirectory*)
    if printf '%s' "$*" | grep -q -- '--value'; then
      printf '%s\n' "${FAKE_WORKING_DIRECTORY:-}"
    else
      printf 'WorkingDirectory=%s\n' "${FAKE_WORKING_DIRECTORY:-}"
    fi ;;
  *is-enabled*) printf '%s\n' "${FAKE_ENABLED_STATE:-static}" ;;
  *Requires*|*Wants*|*After*|*WantedBy*|*RequiredBy*) printf '%s\n' "${FAKE_DEPENDENCIES:-}" ;;
esac
exit 0
''')
    _executable(fakebin / "systemd-analyze", 'printf "%s\\n" "$FAKE_UNIT_PATH"\n')
    _executable(fakebin / "journalctl", 'printf "%s\\n" "${FAKE_JOURNAL:-}"\n')
    _executable(fakebin / "uv", 'printf "%s\\n" "$*" >> "$FAKE_UV_LOG"\nexit "${FAKE_UV_EXIT:-0}"\n')
    _executable(fakebin / "git", 'exit 0\n')
    return fakebin


def sandbox_env(tmp_path, fakebin, *, working_directory=""):
    home = tmp_path / "home"
    unit_path = tmp_path / "units"
    state = tmp_path / "state"
    home.mkdir(exist_ok=True)
    unit_path.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update({
        "PATH": str(fakebin) + os.pathsep + env["PATH"],
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "AYLLU_STATE_DIR": str(state),
        "FAKE_SYSTEMCTL_LOG": str(tmp_path / "systemctl.log"),
        "FAKE_UV_LOG": str(tmp_path / "uv.log"),
        "FAKE_UNIT_PATH": str(unit_path),
        "FAKE_WORKING_DIRECTORY": working_directory,
    })
    return env, unit_path


def fixture_root(tmp_path):
    root = tmp_path / "root"
    (root / "deploy" / "hamutay-heartbeat@qwen.service.d").mkdir(parents=True)
    (root / "community" / "qwen").mkdir(parents=True)
    for relative in [
        "deploy/hamutay-llama-server.service",
        "deploy/hamutay-heartbeat@qwen.service.d/override.conf",
        "deploy/door.json.qwen",
    ]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return root


def run_script(script, args, env):
    return subprocess.run(["bash", str(script), *map(str, args)], env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)


def test_migration_dry_run_uses_only_injected_systemctl(tmp_path):
    fakebin = fake_commands(tmp_path)
    env, unit_path = sandbox_env(tmp_path, fakebin)

    result = run_script(MIGRATE, ["--dry-run", "--root", ROOT, "--unit-paths", unit_path, "--no-commit"], env)

    assert result.returncode == 0, result.stdout
    log = Path(env["FAKE_SYSTEMCTL_LOG"])
    assert not log.exists() or "systemctl" not in log.read_text().lower()


def test_migration_refuses_root_that_differs_from_unit_working_directory(tmp_path):
    fakebin = fake_commands(tmp_path)
    other = tmp_path / "installed-root"
    other.mkdir()
    env, unit_path = sandbox_env(tmp_path, fakebin, working_directory=str(other))

    result = run_script(MIGRATE, ["--root", ROOT, "--unit-paths", unit_path, "--no-commit"], env)

    assert result.returncode != 0
    assert "WorkingDirectory" in result.stdout or "working directory" in result.stdout.lower()


def test_step_six_timeout_aborts_before_door_json_exists(tmp_path):
    fakebin = fake_commands(tmp_path)
    root = fixture_root(tmp_path)
    env, unit_path = sandbox_env(tmp_path, fakebin, working_directory=str(root))
    env["FAKE_UV_EXIT"] = "1"

    result = run_script(MIGRATE, ["--root", root, "--unit-paths", unit_path, "--no-commit"], env)

    assert result.returncode != 0
    assert not (root / "community" / "qwen" / "door.json").exists()


def _prepare_check(tmp_path):
    fakebin = fake_commands(tmp_path)
    root = fixture_root(tmp_path)
    env, unit_path = sandbox_env(tmp_path, fakebin, working_directory=str(root))
    door = root / "community" / "qwen"
    write_json(door / "door.json", {"gpu_lease": "4090"})
    state_gpu = Path(env["AYLLU_STATE_DIR"]) / "gpu"
    state_gpu.mkdir(parents=True)
    (state_gpu / "4090.door").write_text(str(door) + "\n")
    return root, env, unit_path


def test_check_rejects_indented_wants_directive(tmp_path):
    root, env, unit_path = _prepare_check(tmp_path)
    (unit_path / "stray.service").write_text("[Unit]\n    Wants=hamutay-llama-server.service\n")
    env["FAKE_JOURNAL"] = "gpu lease: 4090 (door.json)"

    result = run_script(CHECK, ["--root", root, "--unit-paths", unit_path, "--journalctl", "journalctl"], env)

    assert result.returncode != 0


def test_check_rejects_stray_dependency_symlink(tmp_path):
    root, env, unit_path = _prepare_check(tmp_path)
    wants = unit_path / "default.target.wants"
    wants.mkdir()
    (wants / "hamutay-llama-server.service").symlink_to("../hamutay-llama-server.service")
    env["FAKE_JOURNAL"] = "gpu lease: 4090 (door.json)"

    result = run_script(CHECK, ["--root", root, "--unit-paths", unit_path, "--journalctl", "journalctl"], env)

    assert result.returncode != 0


def test_check_rejects_missing_launch_note(tmp_path):
    root, env, unit_path = _prepare_check(tmp_path)
    env["FAKE_JOURNAL"] = "heartbeat booted without participation note"

    result = run_script(CHECK, ["--root", root, "--unit-paths", unit_path, "--journalctl", "journalctl"], env)

    assert result.returncode != 0

