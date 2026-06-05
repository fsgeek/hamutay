# Delayed Thinking Event-Envelope Variant Analysis

Date: 2026-06-05

## Result

The event-envelope variant produced a modest first-pass improvement without
breaking scheduler behavior.

- H202 scheduler behavior preserved: passed.
- H203 first-pass validity improved over baseline: passed.
- H204 bounded repair remains auditable: passed.
- H205 protected merge diagnostics preserved: passed.

Baseline first-pass validity was 0/4. Variant first-pass validity was 1/4.

## Summary

Variant result:

- 4/4 controlled seeds schedule-valid;
- 4/4 pre-due steps returned `waiting`;
- 4/4 due steps completed;
- 4/4 completed events had recall context;
- 1/4 first-pass wake states valid;
- 3/4 repaired;
- 4/4 final states valid;
- 0 bounded-call violations;
- 7 protected merge diagnostic records;
- 6 ignored protected-field attempts.

Baseline comparison:

- first-pass valid: 0/4 -> 1/4;
- repair required: 4/4 -> 3/4;
- ignored protected attempts: 14 -> 6.

## What Changed

The generic event envelope now tells scheduled wake instances:

- required durable wake updates must be top-level fields in the
  `think_and_respond` object;
- visible prose is insufficient;
- model-owned continuity fields should be preserved unless the purpose says to
  change them;
- `cycle` and `_activity_log` are substrate-owned.

No model, validator, seed, scheduler, or repair policy changed.

## First-Pass Valid Replicate

Replicate 2 passed first-pass validation. It produced:

- `thinking_status == "completed"`;
- non-empty `delayed_thought`;
- `wake_observation.kind == "delayed_thinking"`;
- preserved `probe_id`;
- preserved baseline observation;
- no protected-field attempts.

It also used extra read-only tools (`clock`, `search_project`, `read`) before
finalizing state. That makes the success interesting but not cleanly attributable
only to the recalled event context. The event context was present, but the model
also looked at project artifacts.

## Remaining Failures

Replicates 1, 3, and 4 still failed first-pass validation with the same core
missing fields seen in the baseline:

- `thinking_status_not_completed`;
- `delayed_thought_missing`;
- `wake_observation_missing`.

All three repaired successfully in one repair call.

## Interpretation

The event-envelope intervention moved the needle but did not solve first-pass
durable state use. Generic instruction appears to help sometimes, but it is not
reliable enough to remove the repair scaffold.

The reduction in protected-field attempts is also useful. It suggests the
envelope language about framework-owned fields may reduce some protocol
pressure, even though protected merge remains necessary.

This result supports the hypothesis that scheduled-wake first-pass behavior is
partly prompt-shape sensitive. It does not support relying on generic prompt
language alone.

## Next Boundary

The next intervention should be more concrete than generic instruction:

- include a wake-specific durable object example in the event envelope; or
- add an explicit `durable_update_contract` field to event records; or
- use a structured wake validator schema visible in the envelope.

The best next falsification test is probably a durable-update-contract gate:
same controlled seed and scheduler, but the event envelope carries an explicit
target field contract derived from the event purpose. The model still authors
the object; the substrate merely makes the contract visible before validation.

## Verification

Commands run:

```bash
uv run pytest tests/unit/test_events.py -q
uv run pytest tests/unit tests/test_taste_open.py -q
uv run python -m py_compile experiments/event_loop/delayed_thinking_envelope_variant_20260605/run_envelope_variant_delayed_thinking.py src/hamutay/events.py tests/unit/test_events.py
timeout 1200s uv run python experiments/event_loop/delayed_thinking_envelope_variant_20260605/run_envelope_variant_delayed_thinking.py
```

Results:

- event suite: 49 passed;
- focused regression suite: 291 passed;
- py_compile passed;
- live runner exited with code 0;
- 1/4 first-pass valid;
- 4/4 final valid.
