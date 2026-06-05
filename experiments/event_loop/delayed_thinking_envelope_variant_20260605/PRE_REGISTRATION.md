# Pre-Registration: Delayed Thinking Event-Envelope Variant

Date: 2026-06-05

## Research Question

Can stronger generic event-envelope instructions improve first-pass durable
state use during delayed scheduled wakes?

The controlled-seed delayed-thinking gate showed that the scheduler substrate
works, but first-pass wake state failed in 4/4 replicates and required bounded
repair. This experiment changes the event envelope, not the model, scheduler,
or validator.

## Baseline

Baseline artifact:

`experiments/event_loop/delayed_thinking_controlled_seed_20260605`

Baseline result:

- 4/4 controlled seeds scheduled future recall events;
- 4/4 pre-due steps waited;
- 4/4 due steps completed with recall context;
- 0/4 first-pass wake states valid;
- 4/4 repaired to valid final state.

## Hypotheses

- H202: Stronger generic event-envelope instructions preserve scheduler
  behavior: scheduling, waiting, due execution, and recall delivery still work.
- H203: Stronger event-envelope instructions improve first-pass delayed-wake
  durable state validity over the 0/4 baseline.
- H204: If first-pass validity remains imperfect, bounded repair remains
  auditable.
- H205: Protected merge diagnostics continue to expose protected-field attempts.

## Predictions

The likely result is partial improvement at best. The model has repeatedly
needed examples or repair to use durable state reliably. A stronger event
envelope may reduce but probably will not eliminate first-pass failures.

If first-pass validity remains 0/4, the implication is that generic envelope
language is insufficient and a wake-specific behavior example or training-style
object example is the next intervention.

## Method

Modify the generic event envelope so scheduled wake messages explicitly state:

- required wake updates must be committed as top-level fields in the durable
  object;
- visible prose is insufficient;
- if the purpose names required durable updates, those named updates must be
  present in `think_and_respond`;
- framework-owned fields remain substrate-owned.

Then rerun the controlled-seed delayed-thinking gate:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- protected fields: `cycle`, `_activity_log`;
- synthetic cycle 1 history;
- future event with `not_before`;
- recall cycle 1 context;
- strict validator and one repair attempt.

## Falsification Criteria

- H202 is falsified if scheduler behavior regresses.
- H203 is falsified if first-pass validity remains 0/4.
- H204 is falsified if invalid first-pass states are silently accepted or repair
  exceeds one repair call.
- H205 is falsified if protected attempts appear in raw output but are not
  recorded in merge diagnostics.

## Analysis Plan

Compare against the baseline:

- first-pass valid count;
- repair count;
- final valid count;
- scheduler delivery metrics;
- protected merge diagnostics.

The key result is whether the generic envelope is enough to move first-pass
durable-state behavior. Final repaired validity is secondary.
