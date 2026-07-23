# Offline Pytest Collection Design

Date: 2026-07-23

Status: approved.

## Problem

Pytest's default filename patterns include both `test_*.py` and `*_test.py`.
That causes `experiments/taste/pressure_test.py` to execute eight live Anthropic
exchanges during collection. Supplying `ANTHROPIC_API_KEY` would turn an offline
test command into an unexpected paid experiment rather than fix the boundary.

## Decision

Configure pytest in `pyproject.toml` to collect only `test_*.py` files. The
legacy `pressure_test.py` experiment is the repository's only suffix-named
`*_test.py` file that does not also begin with `test_`, so this policy disables
only that accidental collection today. The file remains runnable explicitly
and can be renamed or restored to collection later if useful.

## Verification

- `uv run pytest --collect-only -q` must exit successfully without attempting
  an Anthropic call.
- `uv run pytest -q` must run the offline suite successfully.
- Explicit experiment-local tests named `test_run.py` and `test_score.py` must
  remain discoverable.

No credential installation or live model invocation is part of this change.
