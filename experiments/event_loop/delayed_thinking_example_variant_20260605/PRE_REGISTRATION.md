# Pre-Registration: Delayed Thinking Wake Example Variant

Date: 2026-06-05

## Research Question

Does showing a wake-specific example of a valid `think_and_respond` durable
object improve first-pass delayed-wake state use?

The explicit durable-update contract variant did not improve first-pass
validity. This experiment tests the stronger training-mismatch intervention:
give the model an example object shaped like the desired output.

## Baselines

Controlled-seed baseline:

- first-pass valid: 0/4;
- final valid after repair: 4/4.

Generic envelope variant:

- first-pass valid: 1/4;
- final valid after repair: 4/4.

Durable contract variant:

- first-pass valid: 0/4;
- final valid after repair: 4/4.

## Hypotheses

- H211: Adding `durable_update_example` to scheduled events preserves scheduler
  behavior.
- H212: A wake-specific example improves first-pass validity over the best
  previous baseline of 1/4.
- H213: If first-pass validity remains imperfect, bounded repair remains
  auditable.
- H214: The example is recorded durably in event logs and shown in wake
  envelopes.
- H215: Protected merge diagnostics remain available.

## Predictions

The example should outperform the contract because it shows the transformer the
desired output pattern directly. Expected result: first-pass validity above
1/4. It may still not reach 4/4 because stochastic variation and scheduled-wake
complexity remain.

## Method

Add optional `durable_update_example` support to:

- `schedule_event` tool schema;
- event construction;
- event envelope.

The example object for this gate will include:

- `response`;
- exact `probe_id`;
- `thinking_status == "completed"`;
- non-empty `delayed_thought`;
- `wake_observation.kind == "delayed_thinking"`;
- baseline `observations`.

Then rerun the controlled-seed delayed-thinking gate:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- protected fields: `cycle`, `_activity_log`;
- synthetic cycle 1 history;
- future event with `not_before`;
- recall cycle 1 context;
- strict validator and one repair attempt.

## Falsification Criteria

- H211 is falsified if scheduling, waiting, due execution, or recall delivery
  regresses.
- H212 is falsified if first-pass validity is 1/4 or lower.
- H213 is falsified if invalid first-pass states are silently accepted or repair
  exceeds one repair call.
- H214 is falsified if the example is absent from event logs or wake envelopes.
- H215 is falsified if protected attempts appear in raw output but are not
  recorded.

## Analysis Plan

Compare against baselines:

- first-pass valid count;
- repair count;
- final valid count;
- protected merge attempts;
- whether logs and envelopes carried the example.

A positive result supports example/training-shape intervention. A negative
result suggests first-pass scheduled-wake state use may require either repair,
tool-level output constraints, or model fine-tuning rather than prompt variants.
