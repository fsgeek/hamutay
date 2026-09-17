"""Byte-identity guards for the window-aware change (spec 'What stays byte-identical').

Fixtures were captured from commit b7ab196's parent code by
scripts/capture_window_golden.py BEFORE any window change landed.

Shared helpers (_backend, _session, _tool_call, _turn, frozen_clock) live in
tests/_window_golden_helpers.py rather than scripts/capture_window_golden.py:
`scripts/` has no `__init__.py` and pytest's `testpaths` is `["tests"]`, so
`scripts` is not importable as a package from this test module (confirmed:
`import scripts` raises ModuleNotFoundError under `uv run pytest`). Neither
`tests/` nor `scripts/` has an `__init__.py` (rootless import mode), so both
this module and the capture script import the helpers module bare
(`_window_golden_helpers`, added to sys.path by the capture script;
resolved directly by pytest's rootdir-relative import here).
"""
import json
from pathlib import Path

import pytest

from _window_golden_helpers import _backend, _session, _tool_call, _turn, frozen_clock

FIX = Path("tests/fixtures/window_golden")


def _load(name):
    return json.loads((FIX / f"{name}.json").read_text())


def _run(tmp_path, backend, exc=None):
    with frozen_clock():
        s, log = _session(tmp_path, backend)
        if exc is None:
            s.exchange("hello")
        else:
            with pytest.raises(exc):
                s.exchange("hello")
    rec = json.loads(log.read_text().splitlines()[-1])
    for k in ("timestamp", "record_id"):
        rec.pop(k, None)
    return json.loads(json.dumps(backend.payloads, sort_keys=True)), rec


def test_no_ceiling_two_turn_wake_is_byte_identical(tmp_path):
    g = _load("no_ceiling_two_turn")
    b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")])
    payloads, rec = _run(tmp_path, b)
    assert payloads == g["payloads"]
    assert rec["system_prompt"] == g["system_prompt"]
    assert json.loads(json.dumps(rec, sort_keys=True, default=str)) == g["record"]


def test_explicit_ceiling_without_tokenizer_is_byte_identical(tmp_path):
    g = _load("explicit_ceiling_two_turn")
    b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")], context_limit=100_000)
    payloads, rec = _run(tmp_path, b)
    assert payloads == g["payloads"]
    assert rec["system_prompt"] == g["system_prompt"]


def test_no_ceiling_length_failure_differs_only_in_the_four_declared_places(tmp_path):
    g = _load("no_ceiling_length_failure")
    b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="cut", finish="length")])
    payloads, rec = _run(tmp_path, b, exc=RuntimeError)
    assert payloads == g["payloads"]
    old, new = g["record"], json.loads(json.dumps(rec, sort_keys=True, default=str))
    allowed = {"usage", "interim_text", "failure_classification"}
    for k in set(old) | set(new):
        if k in allowed:
            continue
        assert old.get(k) == new.get(k), k
    fc_old, fc_new = old["failure_classification"], new["failure_classification"]
    for k in set(fc_old) | set(fc_new):
        if k in ("error_type", "truncated_reply", "error"):
            continue
        assert fc_old.get(k) == fc_new.get(k), k
