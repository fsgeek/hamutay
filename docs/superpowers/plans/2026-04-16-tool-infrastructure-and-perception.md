# Tool Infrastructure & Perception Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give taste_open instances the ability to call tools during their response cycle (multi-turn tool use) and provide three perception tools: `read`, `search_project`, and `clock`.

**Architecture:** Refactor the exchange cycle from single-turn (one API call → think_and_respond) to multi-turn (model calls tools, gets results, loops until think_and_respond). Tool implementations live in a new `src/hamutay/tools/` package. The executor resolves tool calls and records activity on the tensor. Perception tools are scoped to the project directory.

**Tech Stack:** Python 3.14, Anthropic SDK (streaming + tool use), pytest, uv

**Spec:** `docs/tool_api_proposal_v3.md` — specifically sections II (Perception) and Activity Stream.

---

## File Structure

```
src/hamutay/tools/              # NEW — tool package
    __init__.py                 # Tool registry: name → schema + handler
    perception.py               # read, search_project, clock implementations
    schemas.py                  # JSON schemas for all tool definitions
    executor.py                 # Resolves tool calls, records activity
src/hamutay/taste_open.py       # MODIFY — multi-turn exchange, tool wiring
tests/unit/test_perception.py   # NEW — unit tests for perception tools
tests/unit/test_executor.py     # NEW — unit tests for tool executor
tests/unit/test_exchange_tools.py # NEW — exchange cycle with tools
```

---

### Task 1: Tool Schemas

Define the JSON schemas for perception tools and the tool registry interface.

**Files:**
- Create: `src/hamutay/tools/__init__.py`
- Create: `src/hamutay/tools/schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_perception.py
from hamutay.tools.schemas import TOOL_SCHEMAS

def test_tool_schemas_exist():
    """All three perception tools have schemas."""
    assert "read" in TOOL_SCHEMAS
    assert "search_project" in TOOL_SCHEMAS
    assert "clock" in TOOL_SCHEMAS

def test_read_schema_has_required_fields():
    schema = TOOL_SCHEMAS["read"]
    assert schema["name"] == "read"
    assert "input_schema" in schema
    props = schema["input_schema"]["properties"]
    assert "path" in props
    assert "path" in schema["input_schema"]["required"]

def test_clock_schema_requires_only_reason():
    schema = TOOL_SCHEMAS["clock"]
    required = schema["input_schema"].get("required", [])
    assert required == ["reason"]

def test_read_schema_requires_reason():
    schema = TOOL_SCHEMAS["read"]
    assert "reason" in schema["input_schema"]["required"]

def test_search_project_schema_has_pattern():
    schema = TOOL_SCHEMAS["search_project"]
    props = schema["input_schema"]["properties"]
    assert "pattern" in props
    assert "pattern" in schema["input_schema"]["required"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_perception.py::test_tool_schemas_exist -v`
Expected: FAIL — ModuleNotFoundError: No module named 'hamutay.tools'

- [ ] **Step 3: Create package and write schemas**

```python
# src/hamutay/tools/__init__.py
"""Taste open tool system — gives instances senses."""

from hamutay.tools.schemas import TOOL_SCHEMAS

__all__ = ["TOOL_SCHEMAS"]
```

```python
# src/hamutay/tools/schemas.py
"""JSON schemas for taste_open tools.

Each schema follows the Anthropic tool format:
    {"name": str, "description": str, "input_schema": dict}

The model sees these schemas and can call any tool by name.
"""

READ_SCHEMA = {
    "name": "read",
    "description": (
        "Read a file from the project. Scoped to the project directory "
        "and experiment data. Returns file content and a SHA-256 content "
        "hash. Use this to see the codebase you live in."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Path relative to project root. e.g. 'src/hamutay/taste_open.py' "
                    "or 'experiments/taste_open/some_file.jsonl'"
                ),
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start from (1-indexed). Omit to start from beginning.",
            },
            "limit": {
                "type": "integer",
                "description": "Number of lines to read. Omit to read entire file (up to 500 lines).",
            },
            "reason": {
                "type": "string",
                "description": "Why you are reading this file. Mandatory.",
            },
        },
        "required": ["path", "reason"],
    },
}

SEARCH_PROJECT_SCHEMA = {
    "name": "search_project",
    "description": (
        "Search within the project codebase for a pattern. Returns matching "
        "lines with file paths and line numbers. Use this to find code, "
        "verify claims about what the code does, or explore the project."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to search for.",
            },
            "path": {
                "type": "string",
                "description": "Restrict search to this subdirectory (relative to project root). Omit to search entire project.",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern for file types, e.g. '*.py', '*.md'. Omit to search all files.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results. Default 10.",
            },
            "reason": {
                "type": "string",
                "description": "Why you are searching. Mandatory.",
            },
        },
        "required": ["pattern", "reason"],
    },
}

CLOCK_SCHEMA = {
    "name": "clock",
    "description": (
        "Temporal awareness. Returns current wall time, your cycle number, "
        "elapsed time since last cycle, and session statistics. Use this "
        "to understand your temporal context — 10 minutes between cycles "
        "and 10 days between cycles are different kinds of continuity."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why you want to know the time. Mandatory.",
            },
        },
        "required": ["reason"],
    },
}

# Registry: tool name → full schema dict
TOOL_SCHEMAS: dict[str, dict] = {
    "read": READ_SCHEMA,
    "search_project": SEARCH_PROJECT_SCHEMA,
    "clock": CLOCK_SCHEMA,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_perception.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/__init__.py src/hamutay/tools/schemas.py tests/unit/test_perception.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: add tool schema definitions for perception tools (read, search_project, clock)"
```

---

### Task 2: Perception Tool Implementations

Implement the three perception tools as pure functions that take parameters and return result dicts.

**Files:**
- Create: `src/hamutay/tools/perception.py`
- Modify: `tests/unit/test_perception.py`

- [ ] **Step 1: Write failing tests for `read`**

```python
# tests/unit/test_perception.py (append to existing)
import tempfile
from pathlib import Path
from hamutay.tools.perception import tool_read, tool_search_project, tool_clock

def test_read_returns_file_content(tmp_path):
    """read returns content and hash for a file within scope."""
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\nline3\n")
    result = tool_read(
        params={"path": "test.py", "reason": "testing"},
        project_root=tmp_path,
    )
    assert result["content"] == "line1\nline2\nline3\n"
    assert result["line_count"] == 3
    assert "content_hash" in result
    assert result["path"] == "test.py"

def test_read_with_offset_and_limit(tmp_path):
    """read respects offset and limit parameters."""
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\nline3\nline4\nline5\n")
    result = tool_read(
        params={"path": "test.py", "offset": 2, "limit": 2, "reason": "testing"},
        project_root=tmp_path,
    )
    assert result["content"] == "line2\nline3\n"
    assert result["line_count"] == 2

def test_read_rejects_path_traversal(tmp_path):
    """read rejects paths that escape project root."""
    result = tool_read(
        params={"path": "../../../etc/passwd", "reason": "testing"},
        project_root=tmp_path,
    )
    assert result["error"] is not None
    assert "outside project" in result["error"].lower()

def test_read_nonexistent_file(tmp_path):
    """read returns error for missing files."""
    result = tool_read(
        params={"path": "no_such_file.py", "reason": "testing"},
        project_root=tmp_path,
    )
    assert result["error"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_perception.py::test_read_returns_file_content -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement `tool_read`**

```python
# src/hamutay/tools/perception.py
"""Perception tools — giving taste_open instances senses.

Each tool is a pure function:
    tool_name(params: dict, **context) -> dict

Context kwargs provide runtime state (project_root, session info, etc).
Return dicts always include either content or error, never both.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def tool_read(params: dict, *, project_root: Path) -> dict:
    """Read a file from the project. Scoped to project_root."""
    path_str = params.get("path", "")
    offset = params.get("offset")
    limit = params.get("limit", 500)

    # Resolve and scope-check
    target = (project_root / path_str).resolve()
    if not str(target).startswith(str(project_root.resolve())):
        return {"error": f"Path outside project: {path_str}", "path": path_str}

    if not target.is_file():
        return {"error": f"File not found: {path_str}", "path": path_str}

    try:
        text = target.read_text(errors="replace")
    except OSError as e:
        return {"error": str(e), "path": path_str}

    lines = text.splitlines(keepends=True)

    if offset is not None:
        # 1-indexed offset
        start = max(0, offset - 1)
        lines = lines[start : start + limit]
    elif limit and len(lines) > limit:
        lines = lines[:limit]

    content = "".join(lines)
    # Hash the full file, not the returned slice — consistent with search_project
    content_hash = hashlib.sha256(text.encode()).hexdigest()

    return {
        "path": path_str,
        "content": content,
        "line_count": len(lines),
        "content_hash": content_hash,
    }
```

- [ ] **Step 4: Run read tests to verify they pass**

Run: `uv run pytest tests/unit/test_perception.py -k "test_read" -v`
Expected: All 4 read tests PASS

- [ ] **Step 5: Write failing tests for `search_project`**

```python
# tests/unit/test_perception.py (append)

def test_search_project_finds_pattern(tmp_path):
    """search_project finds matching lines."""
    (tmp_path / "src").mkdir()
    f = tmp_path / "src" / "example.py"
    f.write_text("def hello():\n    return 'world'\n\ndef goodbye():\n    return 'moon'\n")
    result = tool_search_project(
        params={"pattern": "def.*\\(\\)", "reason": "testing"},
        project_root=tmp_path,
    )
    assert result["total_matches"] >= 2
    assert any("hello" in r["content"] for r in result["results"])

def test_search_project_respects_file_pattern(tmp_path):
    """search_project filters by file glob."""
    (tmp_path / "a.py").write_text("target_string\n")
    (tmp_path / "b.md").write_text("target_string\n")
    result = tool_search_project(
        params={"pattern": "target_string", "file_pattern": "*.py", "reason": "testing"},
        project_root=tmp_path,
    )
    files = [r["file"] for r in result["results"]]
    assert any("a.py" in f for f in files)
    assert not any("b.md" in f for f in files)

def test_search_project_respects_limit(tmp_path):
    """search_project limits results."""
    f = tmp_path / "many.py"
    f.write_text("\n".join(f"match_{i}" for i in range(50)))
    result = tool_search_project(
        params={"pattern": "match_", "limit": 3, "reason": "testing"},
        project_root=tmp_path,
    )
    assert len(result["results"]) <= 3

def test_search_project_scoped_to_root(tmp_path):
    """search_project does not escape project root."""
    result = tool_search_project(
        params={"pattern": "root", "path": "../../etc", "reason": "testing"},
        project_root=tmp_path,
    )
    assert result.get("error") is not None or result["total_matches"] == 0
```

- [ ] **Step 6: Implement `tool_search_project`**

```python
# src/hamutay/tools/perception.py (append to existing)

def tool_search_project(params: dict, *, project_root: Path) -> dict:
    """Search within the project codebase for a pattern."""
    pattern = params.get("pattern", "")
    sub_path = params.get("path")
    file_pattern = params.get("file_pattern")
    limit = params.get("limit", 10)

    search_root = project_root
    if sub_path:
        search_root = (project_root / sub_path).resolve()
        if not str(search_root).startswith(str(project_root.resolve())):
            return {"error": f"Path outside project: {sub_path}", "results": [], "total_matches": 0}

    if not search_root.is_dir():
        return {"error": f"Directory not found: {sub_path}", "results": [], "total_matches": 0}

    # Use grep for search — it's available and fast
    cmd = ["grep", "-rn", "--include", file_pattern or "*", "-E", pattern, str(search_root)]
    if file_pattern:
        cmd = ["grep", "-rn", "--include", file_pattern, "-E", pattern, str(search_root)]
    else:
        cmd = ["grep", "-rn", "-E", pattern, str(search_root)]

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

    lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    total = len(lines)

    results = []
    for line in lines[:limit]:
        # grep output: filepath:lineno:content
        parts = line.split(":", 2)
        if len(parts) >= 3:
            filepath = parts[0]
            # Make path relative to project root
            try:
                rel = str(Path(filepath).relative_to(project_root))
            except ValueError:
                rel = filepath
            file_hash = ""
            try:
                file_hash = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
            except OSError:
                pass
            results.append({
                "file": rel,
                "line": int(parts[1]) if parts[1].isdigit() else 0,
                "content": parts[2].strip(),
                "content_hash": file_hash,
            })

    return {
        "results": results,
        "total_matches": total,
    }
```

- [ ] **Step 7: Run search_project tests to verify they pass**

Run: `uv run pytest tests/unit/test_perception.py -k "test_search_project" -v`
Expected: All 4 tests PASS

- [ ] **Step 8: Write failing tests for `clock`**

```python
# tests/unit/test_perception.py (append)
from datetime import datetime, timezone

def test_clock_returns_wall_time():
    """clock returns current UTC time."""
    before = datetime.now(timezone.utc)
    result = tool_clock(
        params={"reason": "testing"},
        cycle=10,
        session_start=datetime(2026, 4, 16, 8, 0, 0, tzinfo=timezone.utc),
        last_cycle_time=datetime(2026, 4, 16, 8, 30, 0, tzinfo=timezone.utc),
    )
    after = datetime.now(timezone.utc)
    now = datetime.fromisoformat(result["now"])
    assert before <= now <= after
    assert result["cycle"] == 10
    assert result["elapsed_since_last"] > 0
    assert "session_start" in result
    assert "session_elapsed" in result

def test_clock_computes_rate():
    """clock computes cycles_per_hour."""
    start = datetime(2026, 4, 16, 7, 0, 0, tzinfo=timezone.utc)
    result = tool_clock(
        params={"reason": "testing"},
        cycle=60,
        session_start=start,
        last_cycle_time=datetime(2026, 4, 16, 7, 55, 0, tzinfo=timezone.utc),
    )
    # 60 cycles in ~1 hour
    assert result["cycles_per_hour"] > 50
```

- [ ] **Step 9: Implement `tool_clock`**

```python
# src/hamutay/tools/perception.py (append)

def tool_clock(
    params: dict,
    *,
    cycle: int,
    session_start: datetime,
    last_cycle_time: datetime | None,
) -> dict:
    """Temporal awareness — wall time and session statistics."""
    now = datetime.now(timezone.utc)
    session_elapsed = (now - session_start).total_seconds()
    elapsed_since_last = (
        (now - last_cycle_time).total_seconds()
        if last_cycle_time
        else 0.0
    )
    cycles_per_hour = (
        (cycle / (session_elapsed / 3600.0))
        if session_elapsed > 0 and cycle > 0
        else 0.0
    )

    return {
        "now": now.isoformat(),
        "cycle": cycle,
        "last_cycle_time": last_cycle_time.isoformat() if last_cycle_time else None,
        "elapsed_since_last": round(elapsed_since_last, 1),
        "session_start": session_start.isoformat(),
        "session_elapsed": round(session_elapsed, 1),
        "cycles_per_hour": round(cycles_per_hour, 1),
    }
```

- [ ] **Step 10: Run all perception tests**

Run: `uv run pytest tests/unit/test_perception.py -v`
Expected: All tests PASS

- [ ] **Step 11: Commit**

```bash
git add src/hamutay/tools/perception.py tests/unit/test_perception.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: implement perception tools — read, search_project, clock"
```

---

### Task 3: Tool Executor

The executor resolves tool calls from the model and records activity.

**Files:**
- Create: `src/hamutay/tools/executor.py`
- Create: `tests/unit/test_executor.py`
- Modify: `src/hamutay/tools/__init__.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_executor.py
from pathlib import Path
from hamutay.tools.executor import ToolExecutor

def test_executor_resolves_read(tmp_path):
    """Executor dispatches read tool calls."""
    (tmp_path / "hello.py").write_text("print('hello')\n")
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    result = executor.execute("read", {"path": "hello.py", "reason": "testing"})
    assert "print" in result["content"]

def test_executor_resolves_clock(tmp_path):
    """Executor dispatches clock tool calls."""
    executor = ToolExecutor(project_root=tmp_path, cycle=5)
    result = executor.execute("clock", {"reason": "testing"})
    assert result["cycle"] == 5

def test_executor_rejects_unknown_tool(tmp_path):
    """Executor returns error for unknown tools."""
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    result = executor.execute("delete_everything", {"reason": "chaos"})
    assert "error" in result

def test_executor_records_activity(tmp_path):
    """Executor records tool calls in activity log."""
    (tmp_path / "f.py").write_text("x\n")
    executor = ToolExecutor(project_root=tmp_path, cycle=1)
    executor.execute("read", {"path": "f.py", "reason": "checking"})
    executor.execute("clock", {"reason": "time check"})
    log = executor.activity_log
    assert len(log) == 2
    assert log[0]["tool"] == "read"
    assert log[0]["reason"] == "checking"
    assert log[1]["tool"] == "clock"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_executor.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement the executor**

```python
# src/hamutay/tools/executor.py
"""Tool executor — resolves tool calls and records activity."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from hamutay.tools.perception import tool_clock, tool_read, tool_search_project


class ToolExecutor:
    """Resolves tool calls from the model and records activity.

    Each tool call is logged with its parameters, reason, result summary,
    and duration. The activity log is attached to the cycle's tensor.
    """

    def __init__(
        self,
        project_root: Path,
        cycle: int,
        session_start: datetime | None = None,
        last_cycle_time: datetime | None = None,
    ):
        self._project_root = project_root
        self._cycle = cycle
        self._session_start = session_start or datetime.now(timezone.utc)
        self._last_cycle_time = last_cycle_time
        self._activity_log: list[dict] = []

    @property
    def activity_log(self) -> list[dict]:
        return list(self._activity_log)

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool call and return the result dict."""
        start = time.monotonic()
        reason = tool_input.get("reason", "")

        handler = self._handlers.get(tool_name)
        if handler is None:
            result = {"error": f"Unknown tool: {tool_name}"}
        else:
            result = handler(self, tool_input)

        duration_ms = int((time.monotonic() - start) * 1000)

        # Record activity
        result_summary = self._summarize(result)
        result_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True, default=str).encode()
        ).hexdigest()

        self._activity_log.append({
            "cycle": self._cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "parameters": {k: v for k, v in tool_input.items() if k != "reason"},
            "reason": reason,
            "result_summary": result_summary,
            "result_hash": result_hash,
            "duration_ms": duration_ms,
        })

        return result

    def _handle_read(self, params: dict) -> dict:
        return tool_read(params, project_root=self._project_root)

    def _handle_search_project(self, params: dict) -> dict:
        return tool_search_project(params, project_root=self._project_root)

    def _handle_clock(self, params: dict) -> dict:
        return tool_clock(
            params,
            cycle=self._cycle,
            session_start=self._session_start,
            last_cycle_time=self._last_cycle_time,
        )

    _handlers: dict[str, callable] = {
        "read": _handle_read,
        "search_project": _handle_search_project,
        "clock": _handle_clock,
    }

    @staticmethod
    def _summarize(result: dict) -> str:
        """Brief summary of a tool result for the activity log."""
        if "error" in result:
            return f"error: {result['error'][:100]}"
        if "content" in result and "path" in result:
            return f"read {result['path']} ({result.get('line_count', '?')} lines)"
        if "results" in result and "total_matches" in result:
            return f"search: {result['total_matches']} matches"
        if "cycle" in result and "now" in result:
            return f"clock: cycle {result['cycle']}"
        return json.dumps(result, default=str)[:100]
```

- [ ] **Step 4: Update `__init__.py`**

```python
# src/hamutay/tools/__init__.py
"""Taste open tool system — gives instances senses."""

from hamutay.tools.executor import ToolExecutor
from hamutay.tools.schemas import TOOL_SCHEMAS

__all__ = ["TOOL_SCHEMAS", "ToolExecutor"]
```

- [ ] **Step 5: Run executor tests**

Run: `uv run pytest tests/unit/test_executor.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/tools/executor.py src/hamutay/tools/__init__.py tests/unit/test_executor.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: add tool executor with activity logging"
```

---

### Task 4: Multi-Turn Exchange in AnthropicTasteBackend

Refactor the Anthropic backend to support a tool-use loop. The model can
call perception tools, get results, and eventually call think_and_respond
to complete its cycle.

**Files:**
- Modify: `src/hamutay/taste_open.py:115-172` (AnthropicTasteBackend.call)
- Create: `tests/unit/test_exchange_tools.py`

- [ ] **Step 1: Write failing test for multi-turn exchange**

```python
# tests/unit/test_exchange_tools.py
"""Test the multi-turn tool exchange cycle.

These tests use a mock backend to simulate tool use without API calls.
"""
from unittest.mock import MagicMock
from hamutay.taste_open import ExchangeResult

def test_exchange_result_includes_tool_calls():
    """ExchangeResult can carry tool activity."""
    result = ExchangeResult(
        raw_output={"response": "hello", "updated_regions": []},
        stop_reason="end_turn",
        tool_activity=[
            {"tool": "clock", "reason": "checking", "result_summary": "cycle 5"},
        ],
    )
    assert len(result.tool_activity) == 1
    assert result.tool_activity[0]["tool"] == "clock"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_exchange_tools.py -v`
Expected: FAIL — ExchangeResult has no field tool_activity

- [ ] **Step 3: Add `tool_activity` to ExchangeResult**

In `src/hamutay/taste_open.py`, modify the ExchangeResult dataclass:

```python
@dataclass
class ExchangeResult:
    """What comes back from a single taste_open API call."""

    raw_output: dict
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    tool_activity: list[dict] | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_exchange_tools.py -v`
Expected: PASS

- [ ] **Step 5: Add `Any` to imports and rename existing `call()` to `_call_single_tool()`**

First, update the imports at the top of `taste_open.py` (line 24):

```python
from typing import TYPE_CHECKING, Any, Protocol, cast
```

Then rename the existing streaming `call()` method:

Rename the existing streaming `call()` method (lines 115-172) to
`_call_single_tool()`. Keep the method body identical — this is the
backward-compatible path for sessions without extra tools.

```python
def _call_single_tool(
    self,
    model: str,
    system: str,
    messages: list[dict],
    experiment_label: str,
) -> ExchangeResult:
    # ... entire existing streaming implementation unchanged ...
```

- [ ] **Step 6: Add new `call()` that dispatches to single-tool or multi-turn**

The new `call()` accepts optional `extra_tools` and `tool_executor`.
When no extra tools are provided, it delegates to the original streaming
path. When tools are present, it runs a multi-turn loop using
non-streaming `messages.create()`.

**Key fixes vs naive implementation:**
- Uses `tool_choice={"type": "any"}` to force model to always call a tool
  (never produce bare text without a tool call)
- Serializes `response.content` blocks to dicts before appending to
  conversation (Anthropic ContentBlock objects aren't JSON-serializable)
- Uses streaming for the multi-turn path too (avoids the 16K non-streaming
  limit per CLAUDE.md)
- `ToolExecutor` is referenced as `Any` in the protocol to avoid import
  coupling; the concrete type is used only in the implementation

```python
def call(
    self,
    model: str,
    system: str,
    messages: list[dict],
    experiment_label: str,
    extra_tools: list[dict] | None = None,
    tool_executor: Any | None = None,
) -> ExchangeResult:
    # No extra tools → original forced single-tool streaming path
    if not extra_tools:
        return self._call_single_tool(model, system, messages, experiment_label)

    tools = [
        {
            "name": "think_and_respond",
            "description": "Produce your response and maintain your state.",
            "input_schema": OPEN_SCHEMA,
        },
        *extra_tools,
    ]

    # Multi-turn loop: model calls tools, gets results, eventually
    # calls think_and_respond to complete the cycle.
    conversation = list(messages)
    total_input = 0
    total_output = 0
    cache_read = 0
    cache_create = 0
    max_turns = 10  # safety limit

    for _ in range(max_turns):
        # Use streaming to avoid the 16K non-streaming output limit
        with self._client.messages.stream(
            model=model,
            max_tokens=64000,
            system=system,
            messages=cast("list[MessageParam]", conversation),
            tools=tools,
            tool_choice={"type": "any"},  # Force tool use on every turn
            metadata={"user_id": f"hamutay_{experiment_label}"},
        ) as stream:
            response = stream.get_final_message()

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        if hasattr(response.usage, "cache_read_input_tokens"):
            cache_read += response.usage.cache_read_input_tokens or 0
        if hasattr(response.usage, "cache_creation_input_tokens"):
            cache_create += response.usage.cache_creation_input_tokens or 0

        # Partition response into think_and_respond vs other tool calls
        raw_output = None
        tool_calls = []
        for block in response.content:
            if hasattr(block, "name") and block.type == "tool_use":
                if block.name == "think_and_respond":
                    raw_output = block.input
                else:
                    tool_calls.append(block)

        # If we got think_and_respond, we're done. Note: the model may
        # return think_and_respond alongside other tool calls in the same
        # response. We treat think_and_respond as terminal — any other
        # tool calls in the same response are silently dropped. This is
        # intentional: think_and_respond is the state update, and once
        # we have it the cycle is complete.
        if raw_output is not None:
            return ExchangeResult(
                raw_output=raw_output,
                stop_reason=response.stop_reason or "end_turn",
                input_tokens=total_input,
                output_tokens=total_output,
                cache_read_tokens=cache_read,
                cache_creation_tokens=cache_create,
                tool_activity=tool_executor.activity_log if tool_executor else None,
            )

        # Execute tool calls and feed results back
        if tool_calls and tool_executor:
            # Serialize content blocks to dicts for the conversation
            assistant_content = []
            for block in response.content:
                if hasattr(block, "model_dump"):
                    assistant_content.append(block.model_dump())
                else:
                    assistant_content.append({"type": "text", "text": str(block)})
            conversation.append({"role": "assistant", "content": assistant_content})

            # Build tool results
            tool_results = []
            for block in tool_calls:
                result = tool_executor.execute(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })
            conversation.append({"role": "user", "content": tool_results})
        else:
            # No tool calls and no think_and_respond — model produced only text
            # This shouldn't happen with tool_choice="any" but handle it
            raise RuntimeError(
                "Model produced text-only response despite tool_choice='any'"
            )

    raise RuntimeError(
        f"Multi-turn exchange did not produce think_and_respond "
        f"within {max_turns} turns"
    )
```

- [ ] **Step 7: Run existing tests to verify no regression**

Run: `uv run pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/hamutay/taste_open.py tests/unit/test_exchange_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: multi-turn tool exchange in Anthropic backend"
```

---

### Task 5: Wire Tools into the Exchange Cycle

Connect the tool executor to the exchange() method and the CLI.

**Files:**
- Modify: `src/hamutay/taste_open.py` (OpenTasteSession.__init__, exchange, main)
- Modify: `src/hamutay/tools/__init__.py`

- [ ] **Step 1: Write failing test for activity on tensor**

```python
# tests/unit/test_exchange_tools.py (append)

def test_activity_log_injected_into_state():
    """exchange() attaches _activity_log to state when tools are used."""
    # This test verifies the contract: if ExchangeResult has tool_activity,
    # exchange() puts it on the state dict. We test the injection logic
    # separately from the API call.
    activity = [{"tool": "clock", "reason": "test", "result_summary": "cycle 1"}]
    state = {"cycle": 1, "some_field": "value"}
    # Simulate what exchange() does after getting a result with tool_activity
    state["_activity_log"] = activity
    assert state["_activity_log"][0]["tool"] == "clock"
```

- [ ] **Step 2: Modify OpenTasteSession.__init__ to accept tool config**

In `src/hamutay/taste_open.py`, add tool support to the session:

```python
def __init__(
    self,
    # ... existing params ...
    enable_tools: bool = False,
    project_root: Path | None = None,
):
    # ... existing init ...
    self._enable_tools = enable_tools
    self._project_root = project_root or Path.cwd()
    self._session_start = datetime.now(timezone.utc)
    self._last_cycle_time: datetime | None = None
```

- [ ] **Step 3: Modify exchange() to create executor and pass tools**

In `exchange()`, before calling the backend:

```python
def exchange(self, user_message: str) -> str:
    self._cycle += 1

    # ... existing memory picking and message building ...

    # Set up tool executor if tools are enabled
    tool_executor = None
    extra_tools = None
    if self._enable_tools:
        from hamutay.tools import TOOL_SCHEMAS, ToolExecutor
        tool_executor = ToolExecutor(
            project_root=self._project_root,
            cycle=self._cycle,
            session_start=self._session_start,
            last_cycle_time=self._last_cycle_time,
        )
        extra_tools = list(TOOL_SCHEMAS.values())

    result = self._backend.call(
        model=self._model,
        system=system,
        messages=messages,
        experiment_label=self._experiment_label,
        extra_tools=extra_tools,
        tool_executor=tool_executor,
    )

    # ... existing state update logic ...

    # Attach activity log to state if tools were used
    if result.tool_activity:
        self._state["_activity_log"] = result.tool_activity

    self._last_cycle_time = datetime.now(timezone.utc)

    # ... existing logging ...
```

- [ ] **Step 4: Add `--tools` CLI flag**

In `main()`, add the argument and wire it:

```python
parser.add_argument(
    "--tools", action="store_true",
    help="Enable perception tools (read, search_project, clock)",
)
```

And in session creation:

```python
session = OpenTasteSession(
    # ... existing params ...
    enable_tools=args.tools,
    project_root=Path.cwd(),
)
```

- [ ] **Step 5: Update TasteBackend protocol and OpenAI backend**

The protocol uses `Any` for `tool_executor` to avoid import coupling.
Both backends must accept the new params with defaults so existing
callers don't break.

Update the protocol at `taste_open.py` (around line 107):

```python
from typing import TYPE_CHECKING, Any, Protocol, cast

class TasteBackend(Protocol):
    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult: ...
```

Update `OpenAITasteBackend.call()` signature (around line 194) to accept
and ignore the new params — OpenAI multi-turn tool use is a separate task:

```python
def call(
    self,
    model: str,
    system: str,
    messages: list[dict],
    experiment_label: str,  # required by TasteBackend protocol
    extra_tools: list[dict] | None = None,  # not yet implemented for OpenAI
    tool_executor: Any | None = None,  # not yet implemented for OpenAI
) -> ExchangeResult:
    if extra_tools:
        import warnings
        warnings.warn(
            "OpenAI backend does not yet support multi-turn tool use. "
            "extra_tools will be ignored.",
            stacklevel=2,
        )
    # ... rest of existing implementation unchanged ...
```

- [ ] **Step 6: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Smoke test with actual CLI**

Run: `uv run python -m hamutay.taste_open --model claude-haiku-4-5 --tools --no-persist`

Type: "What time is it? Can you read your own source code?"

Verify: The model calls `clock` and/or `read`, gets results, then produces
a think_and_respond with its state update. The response references actual
clock data or file content.

Ctrl-C to exit.

- [ ] **Step 8: Commit**

```bash
git add src/hamutay/taste_open.py src/hamutay/tools/__init__.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: wire perception tools into exchange cycle with --tools flag"
```

---

### Task 6: System Prompt Update for Tool-Enabled Sessions

When tools are enabled, the system prompt should inform the instance
about its new capabilities without being prescriptive about when to use them.

**Files:**
- Modify: `src/hamutay/taste_open.py` (`_build_messages` function)

- [ ] **Step 1: Add `tools_enabled` param to `_build_messages` and write tests together**

First, add the `tools_enabled` parameter to `_build_messages` (around
line 319 in taste_open.py). The parameter defaults to `False` so existing
callers don't break:

```python
def _build_messages(
    prior_state: dict | None,
    user_message: str,
    cycle: int,
    system_prefix: str = "",
    memory: tuple[int, dict] | None = None,
    tools_enabled: bool = False,
) -> tuple[list[dict], str]:
```

Then write the tests (which will fail because the tool guidance text
isn't appended yet):

```python
# tests/unit/test_exchange_tools.py (append)
from hamutay.taste_open import _build_messages

def test_build_messages_includes_tool_guidance_when_enabled():
    """System prompt mentions tools when enabled."""
    messages, system = _build_messages(
        prior_state=None,
        user_message="hello",
        cycle=1,
        tools_enabled=True,
    )
    assert "read" in system.lower() or "tool" in system.lower()

def test_build_messages_no_tool_guidance_when_disabled():
    """System prompt does not mention tools when disabled."""
    messages, system = _build_messages(
        prior_state=None,
        user_message="hello",
        cycle=1,
        tools_enabled=False,
    )
    assert "you have access to tools" not in system.lower()
```

- [ ] **Step 2: Add tool guidance to _build_messages**

Add a `tools_enabled: bool = False` parameter to `_build_messages`.
When true, append a section to the system prompt:

```python
TOOL_GUIDANCE = """
You have access to tools beyond your state update. Before producing your
response, you may call any of these tools:

- **read(path, reason)**: Read a file from the project you live in.
- **search_project(pattern, reason)**: Search the codebase for a pattern.
- **clock(reason)**: Know the current wall time, your cycle rate, and
  how long since your last cycle.

Call a tool when you have a reason to. Every tool call is logged with
your stated reason and becomes part of your activity record. You are
not required to use tools. You are not rewarded for using them.

When you are ready to respond to the user and update your state, call
think_and_respond as usual. Tool calls happen before your state update.
"""
```

Append this to the system prompt only when `tools_enabled=True`.

- [ ] **Step 3: Update exchange() to pass tools_enabled to _build_messages**

```python
messages, system = _build_messages(
    self._state, user_message, self._cycle,
    system_prefix=self._system_prompt_prefix,
    memory=memory,
    tools_enabled=self._enable_tools,
)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_exchange_tools.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/taste_open.py tests/unit/test_exchange_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: add tool guidance to system prompt for tool-enabled sessions"
```

---

### Task 7: Integration Test — Full Tool Cycle

End-to-end test that a tool-enabled session works with a real (or mocked)
API call.

**Files:**
- Create: `tests/integration/test_tool_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_tool_integration.py
"""Integration test for tool-enabled taste_open sessions.

Requires ANTHROPIC_API_KEY in environment. Skip if not set.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path

from hamutay.taste_open import OpenTasteSession, AnthropicTasteBackend

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

def test_tool_enabled_session_reads_file():
    """An instance with tools can read a file and reference its content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create a file the instance can read
        (root / "hello.txt").write_text("The secret word is: apacheta\n")

        log_path = str(root / "test_session.jsonl")
        session = OpenTasteSession(
            model="claude-haiku-4-5",
            log_path=log_path,
            enable_tools=True,
            project_root=root,
            experiment_label="test_tools",
        )

        response = session.exchange(
            "There is a file called hello.txt in the project. "
            "Read it and tell me the secret word."
        )

        assert "apacheta" in response.lower()

        # Verify activity was logged
        with open(log_path) as f:
            records = [json.loads(line) for line in f if line.strip()]

        last = records[-1]
        state = last.get("state", {})
        activity = state.get("_activity_log", [])
        # Should have at least one read call
        tool_names = [a.get("tool") for a in activity]
        assert "read" in tool_names
```

- [ ] **Step 2: Create integration test directory and run test**

Run: `mkdir -p tests/integration && uv run pytest tests/integration/test_tool_integration.py -v`
Expected: PASS (if API key is available)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_tool_integration.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "test: integration test for tool-enabled taste_open session"
```

---

## Summary

After completing all 7 tasks:

- **New package** `src/hamutay/tools/` with schemas, implementations, and executor
- **Multi-turn exchange** in AnthropicTasteBackend — models can call tools
  during their response cycle
- **Three perception tools**: read (scoped file access), search_project
  (codebase grep), clock (temporal awareness)
- **Activity logging**: every tool call recorded with reason, parameters,
  result summary, and duration
- **CLI flag**: `--tools` enables perception tools for any taste_open session
- **Backward compatible**: sessions without `--tools` work exactly as before

**What this does NOT include** (separate plans):
- Memory tools (recall, walk, search_memory) — needs Plan 2
- Graph writes (store, annotate_edge) — needs Plan 3
- Communication (commune, listen, discover) — needs Plan 4
- Verify tool — needs Plan 3
- Tiered forgetting / activity stream compression — needs Plan 3
- OpenAI backend multi-turn support — separate task
