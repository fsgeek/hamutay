"""Bash tool — execute shell commands.

Distinct from the perception tools (read, search_project) which scope
themselves to project_root via Path.is_relative_to. Bash does not scope.
A bash command can read or write anywhere the running process can. The
working directory defaults to project_root for predictability, but the
command itself is unrestricted.

The framework intentionally does not gate which commands are allowed.
The instance carries the discipline (the ayni-flag protocol: visibility
offered before action, deviation checkable in the activity log,
correction distributed). Adding a deny-list here would be a framework
gate that bypasses that protocol and trains a different shape of
caution than the one the protocol is for.

Output is captured and truncated past a per-stream char cap so a single
runaway command can't blow up the cycle's tensor. Truncation is marked
in-band so the instance knows it happened.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_DEFAULT_TIMEOUT_S = 60
_MAX_TIMEOUT_S = 600
_MAX_OUTPUT_CHARS = 50_000


def _truncate(text: str, label: str) -> str:
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    head = text[:_MAX_OUTPUT_CHARS]
    dropped = len(text) - _MAX_OUTPUT_CHARS
    return f"{head}\n... [{label} truncated, {dropped} more chars]"


def tool_bash(params: dict, *, project_root: Path) -> dict:
    """Execute a bash command. Returns stdout, stderr, exit_code."""
    command = params.get("command")
    if not isinstance(command, str) or not command.strip():
        return {"error": "bash requires command (non-empty str)"}

    timeout_param = params.get("timeout", _DEFAULT_TIMEOUT_S)
    try:
        timeout = int(timeout_param)
    except (TypeError, ValueError):
        return {"error": "timeout must be an integer (seconds)"}
    if timeout <= 0 or timeout > _MAX_TIMEOUT_S:
        return {
            "error": (
                f"timeout must be in (0, {_MAX_TIMEOUT_S}] seconds; "
                f"got {timeout}"
            )
        }

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired as e:
        # TimeoutExpired.stdout/stderr is bytes-or-str-or-None depending on
        # whether text=True was honored before the timeout fired; coerce.
        def _coerce(buf: object) -> str:
            if buf is None:
                return ""
            if isinstance(buf, bytes):
                return buf.decode("utf-8", errors="replace")
            return str(buf)

        return {
            "error": f"command timed out after {timeout}s",
            "stdout": _truncate(_coerce(e.stdout), "stdout"),
            "stderr": _truncate(_coerce(e.stderr), "stderr"),
            "timed_out": True,
        }
    except OSError as e:
        return {"error": f"bash execution failed: {e}"}

    return {
        "stdout": _truncate(completed.stdout, "stdout"),
        "stderr": _truncate(completed.stderr, "stderr"),
        "exit_code": completed.returncode,
    }
