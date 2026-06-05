# Analysis: Delayed Thinking Wake Example Variant

Date: 2026-06-05

## Result

The wake-specific durable update example did not improve first-pass durable
state use.

Summary:

- replicates: 4;
- schedules valid: 4/4;
- pre-due waiting behavior: 4/4;
- due events completed: 4/4;
- recall context delivered: 4/4;
- first-pass valid wake states: 0/4;
- repaired wake states: 4/4;
- final valid wake states: 4/4;
- bounded wake call violations: 0;
- ignored protected update attempts: 10.

## Hypothesis Outcomes

- H211 preserved scheduler behavior: supported.
- H212 improved first-pass validity over the previous best baseline of 1/4:
  falsified.
- H213 bounded repair remained auditable: supported.
- H214 the example was recorded in event logs and shown in wake envelopes:
  supported.
- H215 protected merge diagnostics remained available: supported.

## Failure Pattern

The example was not absent. It was present in each pending event record and in
each wake envelope. The negative result is therefore not explained by delivery
failure.

First-pass validation failures:

- r1: `thinking_status_not_completed`, `delayed_thought_missing`,
  `wake_observation_missing`;
- r2: `thinking_status_not_completed`, `delayed_thought_missing`,
  `wake_observation_missing`;
- r3: `thinking_status_not_completed`, `delayed_thought_missing`,
  `wake_observation_missing`;
- r4: `thinking_status_not_completed`, `delayed_thought_missing`,
  `wake_observation_missing`, `baseline_observation_missing`.

Every replicate repaired successfully in one bounded repair turn. Repair also
attempted to write protected `cycle`; those attempts were ignored and recorded.

## Methodology Note

The first run completed r1 but the runner crashed while inspecting whether the
wake envelope contained the example because it tried to parse every
`user_message` as JSON. The wrapper was fixed to treat non-JSON user messages as
non-matches and to reconstruct completed-but-unsummarized replicates from their
preserved logs. The r1 logs were not deleted or overwritten.

## Interpretation

This falsifies the specific idea that merely showing a wake-shaped durable
object example is enough to improve DeepSeek first-pass scheduled-wake state
evolution. The result is stronger than the contract variant in one way: it rules
out both abstract contract delivery and concrete example delivery as sufficient
prompt-level interventions for this model under this gate.

The scheduler substrate remains sound in this slice. The active boundary is now
model activation at wake time, not event timing, event persistence, recall
delivery, or repair auditability.

## Next Research Implication

Further prompt-shape variants are unlikely to be the highest-value next move
unless they introduce a materially different mechanism. The sharper research
directions are:

- treat bounded repair as part of the continuity substrate and test whether it
  preserves useful autonomy without silently manufacturing state;
- test model/training boundaries directly, especially models that already show
  stronger state-object behavior;
- return to event-loop substrate work with repair/validation as explicit
  observability features rather than as ad hoc experiment harness behavior.
