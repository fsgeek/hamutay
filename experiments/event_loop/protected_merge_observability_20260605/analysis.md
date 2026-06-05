# Protected Merge Observability Analysis

Date: 2026-06-05

## Result

The protected merge observability gate passed.

- H177 live protected fields block model overwrite/delete: passed.
- H178 ignored protected attempts are logged explicitly: passed.
- H179 live protected merge allows ordinary unprotected changes: passed.
- H180 live protected merge rejects ordinary unprotected overlap: passed.

No provider calls were needed.

## What Changed

`OpenTasteSession` now accepts `protected_state_fields`. When configured, the
session passes those fields into `_apply_updates` for both first-pass and
repair merges.

Successful cycle logs now include `state_merge_diagnostics` when protection is
configured. The diagnostic records:

- configured protected fields;
- protected updates ignored;
- protected deletions ignored;
- ignored protected attempt count.

Merge failure logs now distinguish raw updated/deleted fields from effective
updated/deleted fields after protected fields are removed from the merge
contract. This prevents protected `cycle` attempts from being misclassified as
ordinary overlap failures.

Repair artifacts also include `state_merge_diagnostics` when a protected repair
merge is performed.

## Evidence

The successful fake-backend test emitted model output that tried to:

- overwrite `cycle`;
- overwrite `_activity_log`;
- delete `cycle`;
- delete `_activity_log`;
- update an ordinary field;
- delete an ordinary field.

Final state preserved `cycle` and `_activity_log`, applied the ordinary update,
and applied the ordinary deletion. The JSONL log explicitly recorded ignored
protected updates and deletions.

The failure fake-backend test emitted model output that updated and deleted
`mood` while also trying to update and delete protected `cycle`. The session
still raised the existing merge error, logged `overlap_keys == ["mood"]`, and
separately logged the ignored protected `cycle` attempts.

Verification:

```bash
uv run python -m py_compile src/hamutay/taste_open.py tests/test_taste_open.py
uv run pytest tests/test_taste_open.py::TestExchangeCycleRollback -q
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed;
- targeted tests: 7 passed;
- focused regression suite: 289 passed.

## Interpretation

This resolves the immediate manufactured-silence concern for protected merge.
The substrate can now hard-reserve framework-owned fields and still preserve
model attempts as explicit data. That gives us a cleaner event-loop design
surface:

- identity/task fields can remain model-authored and validator-governed;
- framework/audit fields can be substrate-owned and protected;
- ignored protected-field attempts remain visible for analysis.

## Next Boundary

The next live scheduled-wake gate should enable `protected_state_fields` for
framework-owned fields, probably `cycle` and `_activity_log`, and rerun the
strict scheduled walk experiment.

The research question becomes: with hard-reserved framework fields and explicit
merge diagnostics, do scheduled wakes still require strict repair only for task
evidence, or do protected-field attempts remain frequent enough to signal a
model/protocol mismatch?
