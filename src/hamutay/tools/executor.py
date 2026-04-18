"""Tool executor — dispatches tool calls and records activity.

Each tool call is logged with:
  - cycle, timestamp, tool name
  - parameters (excluding reason, which is stored separately)
  - reason (None if the model did not provide one)
  - result_summary (short human-readable)
  - result_hash (sha256 of the full result dict, JSON-serialized)
  - duration_ms

The activity log is attached to the cycle's tensor by the session layer.
Absence of reason is recorded as None — information, not noise.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from hamutay.tools.perception import tool_clock, tool_read, tool_search_project


class ToolExecutor:
    """Resolves tool calls from the model and records activity."""

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
        """Dispatch a tool call and return its result dict."""
        start = time.monotonic()
        reason = tool_input.get("reason")

        if tool_name == "read":
            result = tool_read(tool_input, project_root=self._project_root)
        elif tool_name == "search_project":
            result = tool_search_project(
                tool_input, project_root=self._project_root
            )
        elif tool_name == "clock":
            result = tool_clock(
                tool_input,
                cycle=self._cycle,
                session_start=self._session_start,
                last_cycle_time=self._last_cycle_time,
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        duration_ms = int((time.monotonic() - start) * 1000)
        result_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True, default=str).encode()
        ).hexdigest()

        # Record activity. Parameters exclude `reason` (stored separately).
        self._activity_log.append(
            {
                "cycle": self._cycle,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "parameters": {
                    k: v for k, v in tool_input.items() if k != "reason"
                },
                "reason": reason,
                "result_summary": _summarize(tool_name, result),
                "result_hash": result_hash,
                "duration_ms": duration_ms,
            }
        )

        return result


def _summarize(tool_name: str, result: dict) -> str:
    """Short human-readable summary of a tool result for the activity log."""
    if "error" in result:
        return f"error: {str(result['error'])[:100]}"
    if tool_name == "read":
        return f"read {result.get('path', '?')} ({result.get('line_count', '?')} lines)"
    if tool_name == "search_project":
        return f"search: {result.get('total_matches', 0)} matches"
    if tool_name == "clock":
        return f"clock: cycle {result.get('cycle', '?')}"
    return json.dumps(result, default=str)[:100]
