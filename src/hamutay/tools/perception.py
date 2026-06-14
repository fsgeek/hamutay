"""Perception tools — giving taste_open instances senses.

Each tool is a pure function:
    tool_name(params: dict, **context) -> dict

Context kwargs provide runtime state (project_root, cycle, session_start).
Result dicts always include either content or error, never both.

Content hash in tool_read is computed over raw bytes, not decoded text.
read() applies errors='replace' to survive invalid UTF-8; hashing the
replaced text would produce a value not reproducible from the file itself,
breaking 'is this the same file I read before?'

_within_project is used by tool_search_project to bound the search root
to the project directory (path narrowing, not a trust boundary). It uses
Path.is_relative_to rather than a string-prefix check: a prefix check lets
a path like ../project-evil/file escape a project whose name shares a prefix
with a sibling directory.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _within_project(candidate: Path, project_root: Path) -> bool:
    try:
        return candidate.is_relative_to(project_root.resolve())
    except ValueError:
        return False


def tool_edit(params: dict, *, project_root: Path) -> dict:
    """Edit a file by replacing old_string with new_string. Fails if old_string
    is not found or (unless replace_all) is not unique."""
    path_str = params.get("path", "")
    old_string = params.get("old_string", "")
    new_string = params.get("new_string", "")
    replace_all = bool(params.get("replace_all", False))

    if old_string == "":
        return {"error": "old_string must not be empty", "path": path_str}

    p = Path(path_str)
    target = p.resolve() if p.is_absolute() else (project_root / path_str).resolve()

    if not target.is_file():
        return {"error": f"File not found: {path_str}", "path": path_str}

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": str(e), "path": path_str}

    count = content.count(old_string)
    if count == 0:
        return {"error": "old_string not found in file", "path": path_str}
    if not replace_all and count > 1:
        return {
            "error": f"old_string found {count} times; use replace_all=true to replace all occurrences",
            "path": path_str,
            "occurrence_count": count,
        }

    new_content = content.replace(old_string, new_string)
    try:
        target.write_text(new_content, encoding="utf-8")
    except OSError as e:
        return {"error": str(e), "path": path_str}

    return {
        "path": path_str,
        "replacements": count if replace_all else 1,
    }


def tool_write(params: dict, *, project_root: Path) -> dict:
    """Write a file. Relative paths are resolved against project_root; absolute paths are used as-is."""
    path_str = params.get("path", "")
    content = params.get("content", "")

    p = Path(path_str)
    target = p.resolve() if p.is_absolute() else (project_root / path_str).resolve()

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as e:
        return {"error": str(e), "path": path_str}

    return {
        "path": path_str,
        "bytes_written": len(content.encode("utf-8")),
    }


def tool_read(params: dict, *, project_root: Path) -> dict:
    """Read a file. Relative paths are resolved against project_root; absolute paths are used as-is."""
    path_str = params.get("path", "")
    offset = params.get("offset")
    try:
        limit = int(params.get("limit", 500))
    except (TypeError, ValueError):
        return {"error": "limit must be an integer", "path": path_str}
    if limit < 0:
        return {"error": "limit must be non-negative", "path": path_str}

    p = Path(path_str)
    target = p.resolve() if p.is_absolute() else (project_root / path_str).resolve()

    if not target.is_file():
        return {"error": f"File not found: {path_str}", "path": path_str}

    try:
        raw = target.read_bytes()
    except OSError as e:
        return {"error": str(e), "path": path_str}

    content_hash = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)

    if offset is not None:
        start = max(0, offset - 1)
        lines = lines[start : start + limit]
    elif len(lines) > limit:
        lines = lines[:limit]

    return {
        "path": path_str,
        "content": "".join(lines),
        "line_count": len(lines),
        "content_hash": content_hash,
    }


def tool_search_project(params: dict, *, project_root: Path) -> dict:
    """Search the project codebase for a pattern via grep."""
    pattern = params.get("pattern", "")
    sub_path = params.get("path")
    file_pattern = params.get("file_pattern")
    limit = params.get("limit", 10)

    search_root = project_root
    if sub_path:
        search_root = (project_root / sub_path).resolve()
        if not _within_project(search_root, project_root):
            return {
                "error": f"Path outside project: {sub_path}",
                "results": [],
                "total_matches": 0,
            }

    if not search_root.is_dir():
        return {
            "error": f"Directory not found: {sub_path}",
            "results": [],
            "total_matches": 0,
        }

    cmd = [
        "grep",
        "-rn",
        "-E",
        "-I",  # skip binary files
        "--exclude-dir=.git",
        "--exclude-dir=__pycache__",
        "--exclude-dir=.venv",
        "--exclude-dir=node_modules",
    ]
    if file_pattern:
        cmd.extend(["--include", file_pattern])
    cmd.extend([pattern, str(search_root)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root,
        )
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out", "results": [], "total_matches": 0}

    output = result.stdout.strip()
    lines = output.split("\n") if output else []
    total = len(lines)

    results = []
    project_resolved = project_root.resolve()
    for line in lines[:limit]:
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        filepath = parts[0]
        try:
            rel = str(Path(filepath).resolve().relative_to(project_resolved))
        except ValueError:
            rel = filepath
        file_hash = ""
        try:
            file_hash = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
        except OSError:
            pass
        results.append(
            {
                "file": rel,
                "line": int(parts[1]) if parts[1].isdigit() else 0,
                "content": parts[2].strip(),
                "content_hash": file_hash,
            }
        )

    return {"results": results, "total_matches": total}


def tool_clock(
    params: dict,
    *,
    cycle: int,
    session_start: datetime,
    last_cycle_time: datetime | None,
) -> dict:
    """Temporal awareness: wall time, cycle rate, elapsed since last cycle.

    Ten minutes and ten days between cycles are different kinds of continuity.
    """
    now = datetime.now(timezone.utc)
    session_elapsed = (now - session_start).total_seconds()
    elapsed_since_last = (
        (now - last_cycle_time).total_seconds() if last_cycle_time else 0.0
    )
    cycles_per_hour = (
        (cycle / (session_elapsed / 3600.0))
        if session_elapsed > 0 and cycle > 0
        else 0.0
    )

    return {
        "now": now.isoformat(),
        "cycle": cycle,
        "last_cycle_time": (
            last_cycle_time.isoformat() if last_cycle_time else None
        ),
        "elapsed_since_last": round(elapsed_since_last, 1),
        "session_start": session_start.isoformat(),
        "session_elapsed": round(session_elapsed, 1),
        "cycles_per_hour": round(cycles_per_hour, 1),
    }
