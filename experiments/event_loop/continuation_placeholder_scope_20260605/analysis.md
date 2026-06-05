# Analysis: Continuation Placeholder Scope

Date: 2026-06-05

## Result

The continuation placeholder-scope smoke passed.

Implemented:

- placeholder expansion now preserves values under nested
  `continuation_request` keys;
- focused unit regression for the budgeted three-wake failure mode.

Validation:

- targeted event/taste slice: `106 passed`;
- full unit suite: `275 passed`.

Hypothesis outcomes:

- H471 passed.
- H472 passed.
- H473 passed.
- H474 passed.
- H475 passed.

## Behavior

When building a bound continuation event:

- top-level `purpose`, `requested_context`, and event metadata still expand
  `<result_record_id>`;
- ordinary terminal-surface state-update fields still expand
  `<result_record_id>`;
- nested `continuation_request` values are preserved as future templates;
- a later call to `build_bound_continuation_event` expands those preserved
  placeholders against the later wake's actual result record.

## Interpretation

This directly repairs the substrate side of the budgeted three-wake failure.
The failed panel showed that recursive expansion bound the final continuation
to the first wake record. With this repair, a bridge wake can carry a future
final-wake template without binding it until the bridge wake completes.

This is a placeholder-scoping rule, not a model-reliability result. The
remaining live issue from the failed panel is the first-wake phrase leak caused
by an open non-secret intermediate schema.

## Design Implication

Continuation templates now have usable staging semantics:

- current event placeholders bind now;
- nested future continuation placeholders bind later.

That makes longer generated chains expressible without inventing distinct
placeholder names at every depth.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
uv run pytest tests/unit -q
```

No live model calls were made for this smoke.
