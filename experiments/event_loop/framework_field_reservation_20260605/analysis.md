# Framework Field Reservation Analysis

Date: 2026-06-05

## Result

The deterministic reservation gate passed.

- H173 unprotected merge permits `cycle` overwrite/delete: passed.
- H174 protected merge blocks protected-field overwrite/delete: passed.
- H175 protected merge preserves unprotected overlap rejection: passed.
- H176 protected merge allows ordinary unprotected changes: passed.

No provider calls were needed.

## What Changed

`taste_open._apply_updates` now accepts an opt-in `protected_fields` argument.
When supplied, model-authored updates and deletions for those fields are ignored
before overlap detection and before applying state changes.

This means the substrate can preserve framework-owned fields without needing a
post-hoc validator repair. The current default remains unchanged because callers
that do not pass `protected_fields` still use the prior permissive behavior.

## Evidence

Targeted tests showed:

- unprotected output can still overwrite `cycle`;
- unprotected output can still delete `cycle`;
- protected output cannot overwrite or delete `cycle`;
- protected output cannot overwrite or delete `_activity_log`;
- protected output still updates ordinary model-owned fields;
- protected output still deletes ordinary model-owned fields;
- protected output still rejects update/delete overlap for ordinary fields.

Regression coverage:

- `uv run pytest tests/test_taste_open.py::TestApplyUpdatesKeyPresence -q`
  returned 9 passed;
- `uv run pytest tests/unit tests/test_taste_open.py -q` returned 287 passed;
- `uv run python -m py_compile src/hamutay/taste_open.py tests/test_taste_open.py`
  passed.

## Interpretation

The previous scheduled-wake experiments showed two distinct classes of
continuity protection:

- validators can detect and repair state damage after a model turn;
- reservation can make selected framework-owned damage impossible at merge
  time.

This experiment supports the second mechanism in the narrow deterministic
case. It does not yet enable hard reservation in live `OpenTasteSession`
exchanges. That should remain a separate live experiment because it changes the
actual event-loop substrate behavior and should be measured against scheduled
wake logs.

## Next Boundary

The next live gate should enable protected fields for scheduled wakes and test
whether:

- first-pass evidence failures remain visible;
- framework-owned fields are no longer deleted or overwritten;
- strict validator repairs are still bounded;
- ignored protected-field attempts are observable enough for research data.

The last point is important. Hard reservation should not become manufactured
silence. If the substrate ignores model attempts to damage framework fields, it
should also record that it did so.
