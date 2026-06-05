# Analysis: Auto-Continuation New-Output Gate

Date: 2026-06-05

## Result

The new-output gate smoke passed.

Implemented:

- `OpenTasteSession._last_raw_output`;
- scheduler auto-continuation gating on just-committed raw output rather than
  merged durable state;
- inherited-continuation regression test.

Validation:

- targeted event/taste slice: `103 passed`;
- full unit suite: `272 passed`.

Hypothesis outcomes:

- H431 passed.
- H432 passed.
- H433 passed.
- H434 passed.
- H435 passed.

## Interpretation

The live auto-continuation panel failed because default-stable state preserved
`continuation_request` after the first wake. The scheduler then treated the
inherited request as newly actionable after every later wake.

The repair changes the action boundary:

- merged durable state remains default-stable;
- inherited `continuation_request` may remain visible to the instance;
- scheduler auto-continuation only honors `continuation_request` if the current
  cycle emitted it in raw output.

That is a substrate consumption rule without requiring the model to delete the
field. It aligns with the recurring research finding that relying on the model
to manage protocol cleanup is fragile.

## Remaining Caution

This is still a unit smoke. The next test must rerun the generated-chain
auto-continuation panel with the new-output gate in place and verify that the
chain completes once, then quiesces.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py src/hamutay/taste_open.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
uv run pytest tests/unit -q
```

No live model calls were made for this smoke.
