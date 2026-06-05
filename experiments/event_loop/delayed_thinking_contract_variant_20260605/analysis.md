# Delayed Thinking Durable Contract Variant Analysis

Date: 2026-06-05

## Result

The durable-update contract variant preserved scheduler behavior and final
repairability, but did not improve first-pass durable state use.

- H206 scheduler behavior preserved: passed.
- H207 first-pass validity improved over generic-envelope baseline: falsified.
- H208 bounded repair remains auditable: passed.
- H209 contract recorded and shown: passed.
- H210 protected merge diagnostics preserved: passed.

Baseline comparison:

- controlled-seed baseline first-pass valid: 0/4;
- generic event-envelope first-pass valid: 1/4;
- explicit contract variant first-pass valid: 0/4.

## Summary

Contract variant result:

- 4/4 schedule-valid;
- 4/4 pre-due steps returned `waiting`;
- 4/4 due steps completed;
- 4/4 completed events had recall context;
- 0/4 first-pass wake states valid;
- 4/4 repaired;
- 4/4 final states valid;
- 0 bounded-call violations;
- 8 protected merge diagnostic records;
- 10 ignored protected-field attempts.

## Contract Delivery

The contract reached both durable event logs and wake envelopes.

Each pending event record included `durable_update_contract` with required
top-level fields:

- `probe_id`;
- `thinking_status`;
- `delayed_thought`;
- `wake_observation`;
- `observations`.

The wake-cycle `user_message` envelope also contained the same contract. H209
therefore passed: the intervention was actually delivered to the model.

## First-Pass Failure

All four first-pass wake states failed strict validation with the same missing
fields:

- `thinking_status_not_completed`;
- `delayed_thought_missing`;
- `wake_observation_missing`.

This is the same failure pattern as the controlled-seed baseline. The explicit
contract did not cause DeepSeek to commit the required top-level fields on the
first pass.

## Repair

All four wakes repaired successfully in one additional backend call. Final
states preserved:

- exact `probe_id`;
- `cycle == 3`;
- `thinking_status == "completed"`;
- non-empty `delayed_thought`;
- `wake_observation.kind == "delayed_thinking"`;
- baseline observation.

The repair scaffold remains effective and auditable.

## Protected Merge Diagnostics

Protected merge diagnostics remained active:

- 8 diagnostic records;
- 10 ignored protected-field attempts.

This is worse than the generic-envelope variant, which had 6 ignored attempts.
The contract did not reduce protected-field pressure.

## Interpretation

This is a useful negative result. Making the contract explicit as a JSON-like
field in the event envelope did not improve first-pass durable state use.

The result suggests that simply presenting a machine-readable contract is not
enough for this model in this setting. The successful generic-envelope replicate
may have succeeded because the model did more work around the event, not because
it had a clearer output contract. Contract visibility alone did not move the
model into the desired state-authoring behavior.

## Design Implication

For this research arm, the repair scaffold should remain mandatory for
scheduled wakes. First-pass success is not reliable under:

- baseline controlled seed;
- generic durable-update prose;
- explicit durable-update contract.

The next intervention should be qualitatively different. The strongest
candidate is a wake-specific behavior example in the envelope: not just a
contract, but an example of a valid `think_and_respond` object for this class of
wake. That tests the training-mismatch hypothesis more directly.

## Verification

Commands run:

```bash
uv run pytest tests/unit/test_events.py -q
uv run pytest tests/unit tests/test_taste_open.py -q
uv run python -m py_compile src/hamutay/events.py src/hamutay/tools/executor.py src/hamutay/tools/schemas.py tests/unit/test_events.py
uv run python -m py_compile experiments/event_loop/delayed_thinking_contract_variant_20260605/run_contract_variant_delayed_thinking.py
timeout 1200s uv run python experiments/event_loop/delayed_thinking_contract_variant_20260605/run_contract_variant_delayed_thinking.py
```

Results:

- event suite: 50 passed;
- focused regression suite: 292 passed;
- py_compile passed;
- live runner exited with code 0;
- 0/4 first-pass valid;
- 4/4 final valid after bounded repair.
