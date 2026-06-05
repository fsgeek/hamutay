# Pre-Registration: Controlled-Seed Delayed Thinking

Date: 2026-06-05

## Research Question

If activation is removed as a confound by seeding cycle 1 history directly, can
a live taste_open instance schedule and use a delayed simulated-time wake to
produce a durable state transition?

The behavior-seeded delayed-thinking gate failed 0/4 at initialization. This
follow-up asks the scheduler question directly by providing the initial durable
state as controlled history.

## Hypotheses

- H197: With controlled cycle 1 history, the model can schedule exactly one
  future recall event.
- H198: A scheduler step before `not_before` reports `waiting` and does not run
  the event.
- H199: A scheduler step at `not_before` delivers the event and recall context.
- H200: The delayed wake can produce a durable delayed-thinking transition.
- H201: If first-pass wake state is invalid, bounded strict repair remains
  auditable.

## Predictions

This should perform better than the behavior-seeded gate because the initial
state object and recallable cycle 1 record are already present. The likely
remaining failure mode is first-pass wake state failing to persist the delayed
thinking fields, as in prior scheduled-wake gates. If so, bounded repair should
recover the state if the model follows the repair prompt.

## Method

Use live DeepSeek through OpenRouter:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- `max_tokens`: 2048;
- protected fields: `cycle`, `_activity_log`;
- synthetic cycle 1 history seeded with `seed_history`;
- one scheduling cycle at cycle 2;
- scheduled event `not_before == 2026-06-01T01:00:00+00:00`;
- requested context: `recall(cycle=1)`;
- pre-due scheduler step at `2026-06-01T00:30:00+00:00`;
- due scheduler step at `2026-06-01T01:00:00+00:00`;
- strict wake validator and one repair attempt.

## Falsification Criteria

- H197 is falsified if no replicate schedules exactly one valid future recall
  event.
- H198 is falsified if any pre-due step runs the future event.
- H199 is falsified if no due step completes with recall context.
- H200 is falsified if no completed wake reaches valid delayed-thinking state.
- H201 is falsified if invalid first-pass wakes are silently accepted, repairs
  are not logged, or wakes use more than one repair call.

## Analysis Plan

Report:

- scheduling validity;
- pre-due step result;
- due step result;
- recall context delivery;
- first-pass validation;
- repair status;
- final durable delayed-thinking state;
- protected merge diagnostics.

Interpret the result as scheduler/delayed-wake evidence only, not as activation
evidence.
