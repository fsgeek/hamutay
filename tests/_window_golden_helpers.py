"""Shared helpers for capturing and replaying the window-aware golden fixtures.

`scripts/` is not an importable package under pytest (no `__init__.py`, and
`testpaths = ["tests"]` in pyproject.toml keeps pytest from adding it to
sys.path), so the helpers shared between `scripts/capture_window_golden.py`
and `tests/test_window_golden.py` live here instead. The capture script
imports from this module; the test module does too.

Task 1 of docs/superpowers/plans/2026-09-17-window-aware-wakes.md.
"""
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession
from hamutay.tools.schemas import DECLARE_QUIET_SCHEMA, TOOL_SCHEMAS, UPDATE_STATE_SCHEMA

# The real `clock` tool call (exercised by the natural wake loop below) reads
# wall time via `datetime.now(timezone.utc)` in three modules: taste_open
# (session_start, set once in OpenTasteSession.__init__), hamutay.tools.
# perception (tool_clock's `now`), and hamutay.tools.executor (the activity
# log entry's own `timestamp`, set independently of tool_clock's `now`).
# Every fixture's payloads and activity-log entries embed those values (and
# a result_hash over them), so an unfrozen clock makes every capture run
# non-deterministic — confirmed by running the capture script twice and
# diffing the output (first pass caught taste_open/perception; a second
# diff caught executor's separate timestamp). Freeze all three to a fixed
# instant for the duration of a capture/replay so the fixtures are
# reproducible byte-for-byte.
_FROZEN_NOW = datetime(2026, 9, 17, 0, 0, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return _FROZEN_NOW if tz is not None else _FROZEN_NOW.replace(tzinfo=None)


@contextmanager
def frozen_clock():
    with patch("hamutay.taste_open.datetime", _FrozenDatetime), \
         patch("hamutay.tools.perception.datetime", _FrozenDatetime), \
         patch("hamutay.tools.executor.datetime", _FrozenDatetime):
        yield


def _tool_call(name, args, call_id="c1"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def _turn(content=None, tool_calls=None, finish="stop", prompt_tokens=100, completion_tokens=10):
    return {"choices": [{"finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "tool_calls": tool_calls}}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}}


def _tools():
    return [TOOL_SCHEMAS["read"], TOOL_SCHEMAS["clock"], TOOL_SCHEMAS["bash"],
            TOOL_SCHEMAS["schedule_event"], UPDATE_STATE_SCHEMA, DECLARE_QUIET_SCHEMA]


def _backend(script, **kw):
    b = OpenAITasteBackend(api_key="k", wake_mode="natural", **kw)
    b.payloads = []

    def fake_post(payload):
        b.payloads.append(json.loads(json.dumps(payload)))
        nxt = script.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt
    b._post_chat = fake_post
    return b


def _session(tmp, backend):
    log = tmp / "session.jsonl"
    s = OpenTasteSession(model="m", backend=backend, log_path=str(log), experiment_label="golden",
                         enable_tools=True, project_root=tmp)
    s.seed_state({"cycle": 3, "note": "golden", "_activity_log": [
        {"cycle": 3, "timestamp": "2026-09-01T00:00:00+00:00", "tool": "clock", "reason": "r",
         "parameters": {"x": 1}, "result_summary": "clock: cycle 3", "result_hash": "h", "duration_ms": 1}]}, 3)
    return s, log
