"""Invoke and preserve one inherited, task-free celestial wake."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SEAL_PREFIX = "Sealed at UTC: "


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assemble_prompt(experiment_dir: Path, wake_time: datetime) -> str:
    state = (experiment_dir / "inherited_state.md").read_text()
    template = (experiment_dir / "wake_prompt.md").read_text()
    seal_line = next(
        (line for line in state.splitlines() if line.startswith(SEAL_PREFIX)),
        None,
    )
    if seal_line is None:
        raise ValueError("inherited state has no UTC seal")
    sealed_at = datetime.fromisoformat(
        seal_line.removeprefix(SEAL_PREFIX).replace("Z", "+00:00")
    )
    if wake_time.tzinfo is None or sealed_at.tzinfo is None:
        raise ValueError("wake and seal times must be timezone-aware")
    elapsed = int((wake_time - sealed_at).total_seconds())
    if elapsed < 0:
        raise ValueError("wake time precedes inherited-state seal")
    prompt = (
        template.replace("{{WAKE_TIME_UTC}}", wake_time.isoformat())
        .replace("{{ELAPSED_CELESTIAL_SECONDS}}", str(elapsed))
        .replace("{{INHERITED_STATE}}", state.rstrip())
    )
    if "{{" in prompt or "}}" in prompt:
        raise ValueError("unconsumed prompt placeholder")
    return prompt


def _resolved_model(events_path: Path) -> str | None:
    for line in events_path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        model = event.get("model")
        if isinstance(model, str) and model:
            return model
    return None


def _write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def run_wake(
    experiment_dir: Path,
    output_root: Path,
    codex_bin: str = "codex",
    wake_time: datetime | None = None,
) -> Path:
    wake_time = wake_time or datetime.now(timezone.utc)
    if wake_time.tzinfo is None:
        raise ValueError("wake time must be timezone-aware")
    prompt = assemble_prompt(experiment_dir, wake_time)
    run_id = wake_time.strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    prompt_path = run_dir / "prompt.md"
    events_path = run_dir / "events.jsonl"
    response_path = run_dir / "response.md"
    metadata_path = run_dir / "metadata.json"
    prompt_path.write_text(prompt)

    started_at = datetime.now(timezone.utc)
    stderr = ""
    exit_code: int | None = None
    with tempfile.TemporaryDirectory(prefix="hamutay-celestial-wake-") as work_dir:
        command = [
            codex_bin,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--json",
            "--output-last-message",
            str(response_path),
            "-C",
            work_dir,
            "-",
        ]
        try:
            with events_path.open("w") as events_stream:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    cwd=work_dir,
                    stdout=events_stream,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            exit_code = completed.returncode
            stderr = completed.stderr
        except OSError as error:
            events_path.touch(exist_ok=True)
            stderr = f"{type(error).__name__}: {error}"

    completed_at = datetime.now(timezone.utc)
    response_present = response_path.exists() and bool(response_path.read_text().strip())
    if exit_code != 0:
        status = "infrastructure_failure"
    elif not response_present:
        status = "inconclusive"
    else:
        status = "completed"

    hashes = {
        "prompt.md": sha256_file(prompt_path),
        "events.jsonl": sha256_file(events_path),
    }
    if response_path.exists():
        hashes["response.md"] = sha256_file(response_path)

    metadata = {
        "run_id": run_id,
        "wake_time_utc": wake_time.isoformat(),
        "started_at_utc": started_at.isoformat(),
        "completed_at_utc": completed_at.isoformat(),
        "elapsed_seconds": (completed_at - started_at).total_seconds(),
        "command": command,
        "exit_code": exit_code,
        "status": status,
        "response_present": response_present,
        "response_bytes": response_path.stat().st_size if response_path.exists() else 0,
        "resolved_model": _resolved_model(events_path),
        "stderr": stderr,
        "hashes": hashes,
    }
    _write_json_atomic(metadata_path, metadata)
    return run_dir


def main() -> int:
    experiment_dir = Path(__file__).resolve().parent
    run_dir = run_wake(experiment_dir, experiment_dir / "runs")
    print(run_dir)
    metadata = json.loads((run_dir / "metadata.json").read_text())
    return 1 if metadata["status"] == "infrastructure_failure" else 0


if __name__ == "__main__":
    raise SystemExit(main())
