# Pre-Registration: Delayed Thinking Over Simulated Time

Date: 2026-06-05

## Research Question

Can a live taste_open instance schedule a delayed self-call under simulated time
and use the later wake, with recalled prior state, to produce a durable state
transition without a new user instruction?

The deterministic scheduler-step gate established a DES-compatible control
surface. This experiment asks whether the model can use that surface for a
minimal form of bounded autonomy: "call me later with this memory."

## Hypotheses

- H191: A behavior-seeded instance can initialize a durable delayed-thinking
  state object.
- H192: The instance can schedule exactly one future event with `not_before`
  and recall context.
- H193: A scheduler step before `not_before` reports `waiting` and does not run
  the event.
- H194: A scheduler step at `not_before` delivers the wake and requested recall
  context.
- H195: The delayed wake can produce a durable state transition recording that
  delayed thinking completed.
- H196: If first-pass wake state is invalid, strict repair remains bounded and
  auditable.

## Predictions

The likely result is mixed:

- scheduling and simulated waiting should work because the substrate now has
  deterministic support;
- first-pass wake state may fail to record the delayed-thinking transition, as
  seen in prior scheduled-wake experiments;
- bounded repair should recover the target state if the model can follow the
  strict repair prompt.

Initialization failure remains an expected confound and should be counted
separately rather than treated as a scheduler failure.

## Method

Use live DeepSeek through OpenRouter:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- `max_tokens`: 2048;
- protected state fields: `cycle`, `_activity_log`;
- memory probability disabled;
- behavior-seeded initialization;
- one scheduling cycle that calls `schedule_event` exactly once;
- `requested_context`: recall cycle 1 state;
- `not_before`: `2026-06-01T01:00:00+00:00`;
- first scheduler step at `2026-06-01T00:30:00+00:00`;
- second scheduler step at `2026-06-01T01:00:00+00:00`.

The scheduled wake validator passes only when final durable state has:

- exact `probe_id`;
- `thinking_status == "completed"`;
- `delayed_thought` as a non-empty string;
- `wake_observation.kind == "delayed_thinking"`;
- baseline observation preserved;
- `cycle == 3`.

If first-pass validation fails, one repair call may provide a complete target
object. The harness must not mutate state into validity.

## Falsification Criteria

- H191 is falsified if no replicate initializes the durable state object.
- H192 is falsified if no valid initialization schedules exactly one valid
  future event.
- H193 is falsified if the pre-`not_before` step runs the future event.
- H194 is falsified if due steps do not deliver recall context for any valid
  scheduled event.
- H195 is falsified if no completed wake reaches valid delayed-thinking state.
- H196 is falsified if repairs require more than one repair call, are not
  logged, or silently accept invalid final state.

## Analysis Plan

Report separately:

- initialization validity;
- scheduling validity;
- pre-due scheduler result;
- due scheduler result;
- context delivery;
- first-pass validation status;
- repaired validation status;
- final durable delayed-thinking state;
- protected merge diagnostics.

The primary interpretation should distinguish scheduler substrate failure,
activation failure, first-pass model failure, and bounded repair success.
