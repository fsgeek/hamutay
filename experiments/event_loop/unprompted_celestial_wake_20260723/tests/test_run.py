from __future__ import annotations

import importlib.util
import json
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


EXPERIMENT_DIR = Path(__file__).parents[1]
MODULE_PATH = EXPERIMENT_DIR / "run.py"


def load_run_module():
    spec = importlib.util.spec_from_file_location("celestial_wake_run", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_module():
    return load_run_module()


def write_fixture(root: Path, *, sealed_at: str = "2026-07-23T15:23:19Z") -> None:
    (root / "inherited_state.md").write_text(
        f"# Inherited State\n\nSealed at UTC: {sealed_at}\n\ninherited testimony\n"
    )
    (root / "wake_prompt.md").write_text(
        "Wake: {{WAKE_TIME_UTC}}\n"
        "Elapsed: {{ELAPSED_CELESTIAL_SECONDS}} seconds\n"
        "{{INHERITED_STATE}}\n"
    )


def test_assemble_prompt_substitutes_inheritance_and_time(tmp_path, run_module):
    write_fixture(tmp_path)
    wake = datetime(2026, 7, 23, 15, 24, 19, tzinfo=timezone.utc)

    prompt = run_module.assemble_prompt(tmp_path, wake)

    assert "2026-07-23T15:24:19+00:00" in prompt
    assert "60 seconds" in prompt
    assert "inherited testimony" in prompt
    assert "{{" not in prompt


def test_assemble_prompt_rejects_missing_seal(tmp_path, run_module):
    write_fixture(tmp_path)
    (tmp_path / "inherited_state.md").write_text("# Inherited State\n")

    with pytest.raises(ValueError, match="no UTC seal"):
        run_module.assemble_prompt(tmp_path, datetime.now(timezone.utc))


def test_assemble_prompt_rejects_unknown_placeholder(tmp_path, run_module):
    write_fixture(tmp_path)
    with (tmp_path / "wake_prompt.md").open("a") as stream:
        stream.write("{{UNKNOWN}}\n")

    with pytest.raises(ValueError, match="unconsumed"):
        run_module.assemble_prompt(tmp_path, datetime.now(timezone.utc))


def make_fake_codex(root: Path, *, exit_code: int = 0, response: str = "I will rest.\n") -> Path:
    executable = root / "fake-codex"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json\n"
        "import pathlib\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "response_path = pathlib.Path(args[args.index('--output-last-message') + 1])\n"
        "attempts = response_path.parent / 'attempts.txt'\n"
        "attempts.write_text(attempts.read_text() + '1\\n' if attempts.exists() else '1\\n')\n"
        "prompt = sys.stdin.read()\n"
        "print(json.dumps({'type': 'thread.started', 'model': 'fake-model'}))\n"
        "print(json.dumps({'type': 'test.invocation', 'args': args, "
        "'cwd': str(pathlib.Path.cwd()), 'cwd_entries': sorted(p.name for p in pathlib.Path.cwd().iterdir()), "
        "'prompt_bytes': len(prompt.encode())}))\n"
        f"response_path.write_text({response!r})\n"
        f"raise SystemExit({exit_code})\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def read_events(run_dir: Path) -> list[dict]:
    return [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]


def test_run_wake_captures_one_read_only_ephemeral_invocation(tmp_path, run_module):
    experiment = tmp_path / "experiment"
    output = tmp_path / "output"
    experiment.mkdir()
    write_fixture(experiment)
    fake_codex = make_fake_codex(tmp_path)
    wake = datetime(2026, 7, 23, 15, 24, 19, tzinfo=timezone.utc)

    run_dir = run_module.run_wake(experiment, output, str(fake_codex), wake)

    events = read_events(run_dir)
    invocation = events[1]
    args = invocation["args"]
    assert "--ephemeral" in args
    assert "--ignore-user-config" in args
    assert "--skip-git-repo-check" in args
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert "--json" in args
    assert invocation["cwd"] != str(experiment)
    assert invocation["cwd_entries"] == []
    assert (run_dir / "prompt.md").exists()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "response.md").read_text() == "I will rest.\n"
    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["status"] == "completed"
    assert metadata["response_present"] is True
    assert metadata["resolved_model"] == "fake-model"
    assert metadata["hashes"]["prompt.md"] == run_module.sha256_file(run_dir / "prompt.md")
    assert metadata["hashes"]["events.jsonl"] == run_module.sha256_file(run_dir / "events.jsonl")
    assert metadata["hashes"]["response.md"] == run_module.sha256_file(run_dir / "response.md")


def test_run_wake_classifies_empty_success_as_inconclusive(tmp_path, run_module):
    experiment = tmp_path / "experiment"
    experiment.mkdir()
    write_fixture(experiment)
    fake_codex = make_fake_codex(tmp_path, response="")

    run_dir = run_module.run_wake(experiment, tmp_path / "output", str(fake_codex))

    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["status"] == "inconclusive"
    assert metadata["response_present"] is False


def test_run_wake_does_not_retry_infrastructure_failure(tmp_path, run_module):
    experiment = tmp_path / "experiment"
    experiment.mkdir()
    write_fixture(experiment)
    fake_codex = make_fake_codex(tmp_path, exit_code=7, response="partial\n")

    run_dir = run_module.run_wake(experiment, tmp_path / "output", str(fake_codex))

    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["status"] == "infrastructure_failure"
    assert metadata["exit_code"] == 7
    assert (run_dir / "attempts.txt").read_text().splitlines() == ["1"]
