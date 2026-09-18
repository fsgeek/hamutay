"""Capture golden fixtures for the window-aware change from the code AS IT IS.

Run from the repo root BEFORE implementing anything in the window plan:
    uv run python scripts/capture_window_golden.py
Writes tests/fixtures/window_golden/*.json. Task 1 of
docs/superpowers/plans/2026-09-17-window-aware-wakes.md.

Shared helpers (_backend, _session, _tool_call, _turn, _tools) live in
tests/_window_golden_helpers.py, not here: `scripts/` has no __init__.py and
pytest's testpaths is ["tests"], so `scripts` is not importable from the test
suite. Both this script and tests/test_window_golden.py import from that
shared module instead of scripts/ importing tests/ or vice versa creating a
package that doesn't exist.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from _window_golden_helpers import _backend, _session, _tool_call, _turn, frozen_clock  # noqa: E402

OUT = Path("tests/fixtures/window_golden")


def capture(name, tmp, backend, run):
    with frozen_clock():
        s, log = _session(tmp, backend)
        try:
            run(s)
        except Exception:
            pass
    records = [json.loads(l) for l in log.read_text().splitlines()]
    rec = records[-1]
    for k in ("timestamp", "record_id"):
        rec.pop(k, None)
    (OUT / f"{name}.json").write_text(json.dumps(
        {"payloads": backend.payloads, "system_prompt": rec["system_prompt"], "record": rec},
        indent=1, sort_keys=True, default=str))


def main():
    import tempfile
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")])
        capture("no_ceiling_two_turn", tmp, b, lambda s: s.exchange("hello"))
        b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="cut", finish="length")])
        capture("no_ceiling_length_failure", tmp, b, lambda s: s.exchange("hello"))
        b = _backend([_turn(tool_calls=[_tool_call("clock", {})]), _turn(content="done")], context_limit=100_000)
        capture("explicit_ceiling_two_turn", tmp, b, lambda s: s.exchange("hello"))


if __name__ == "__main__":
    main()
