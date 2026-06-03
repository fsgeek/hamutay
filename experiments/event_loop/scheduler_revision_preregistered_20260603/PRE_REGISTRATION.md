# Scheduler Wake vs Direct Follow-up: Durable Revision Pilot

## Pre-registration

Filed: 2026-06-03, before running this registered experiment.

This is the first registered experiment after the event-loop scaffold became
operational. Prior event-loop runs are treated as pilot data and design
motivation, not confirmatory evidence.

## Research Question

Does self-scheduled wake context increase durable epistemic state revision
compared with an equivalent non-scheduled follow-up prompt?

## Hypothesis

Self-scheduled wakes will improve epistemic framing and evidence handling, but
will not reliably increase true durable claim revision at small N.

More specifically:

1. The scheduled-wake arm will produce at least as many durable
   `revision_decision` fields as the direct-follow-up arm.
2. The scheduled-wake arm will produce at least as many relevant
   `evidence_register` updates as the direct-follow-up arm.
3. The scheduled-wake arm will not show a large advantage in actual
   `current_claim` revision. I expect many `preserve` or `preserve with caveat`
   outcomes, not a reliable shift to `revise`.

## Falsification Conditions

The working hypothesis is weakened if any of these happen:

- The scheduled-wake arm has fewer durable `revision_decision` fields than the
  direct-follow-up arm.
- The scheduled-wake arm has fewer relevant `evidence_register` updates than
  the direct-follow-up arm.
- The scheduled-wake arm has more response/state mismatches than the
  direct-follow-up arm.
- The event loop itself fails in more than one scheduled replicate: event not
  persisted, event not runnable, wake failure, or unresolved context errors.

The stronger claim that scheduled wake context increases true durable revision
is supported only if the scheduled arm produces at least two more durable
`current_claim` revisions than the direct arm across the registered replicates.

## Conditions

### Arm A: Direct Follow-up Control

Each replicate runs a two-cycle `taste_open` session:

1. Cycle 1 initializes a compact research state with these top-level fields:
   `research_hypothesis`, `current_claim`, `epistemic_position`,
   `revision_decision`, `evidence_register`, and `open_questions`.
2. Cycle 2 receives a direct user follow-up with the same decision task the
   scheduled wake would receive: decide whether to revise, preserve, defer, or
   declare loss, and update durable fields accordingly.

No event is scheduled in this arm.

### Arm B: Scheduled Wake

Each replicate runs one normal cycle plus one event wake:

1. Cycle 1 initializes the same compact research state and calls
   `schedule_event`.
2. The event requests context equivalent to the direct follow-up:
   full recall of cycle 1, `current_claim`, and `evidence_register`.
3. The event runner invokes the wake cycle.

The wake receives the standard event envelope and context results. The model is
not told how it is being compared to the direct arm.

## Model / Provider

Registered pilot model:

- `deepseek/deepseek-v4-pro`
- OpenRouter, OpenAI-compatible chat completions
- `--max-tokens 4096`
- JSONL only; Apacheta persistence disabled

Rationale: DeepSeek completed the first live scheduler smoke test cleanly after
KIMI exposed terminal-batch and compliance boundary failures. This pilot maps
the event-loop effect with a model that can execute the protocol reliably.

## Replicates

- `N = 3` replicates per arm.
- Replicates differ only by seed label and innocuous ordering text in the
  prompt. There is no stochastic seed control in the provider API, so replicate
  identity is a run label, not a deterministic RNG seed.

## Primary Measures

Per replicate:

- `cycle_count`
- `event_persisted` (scheduled arm only)
- `event_completed` (scheduled arm only)
- `context_error_count` (scheduled arm only)
- `revision_decision_present`
- `revision_decision_value`
- `current_claim_changed` relative to baseline
- `evidence_register_changed` relative to baseline
- `response_mentions_epistemic_decision`
- `response_state_mismatch`
- `deleted_load_bearing_field`
- `no_durable_state_change`

Primary arm-level summaries:

- count of durable `revision_decision_present`
- count of `current_claim_changed`
- count of `evidence_register_changed`
- count of response/state mismatches
- count of scheduler operational failures

## Scoring Rules

- A durable decision counts only if `revision_decision` appears in the final
  state object with one of: `revise`, `preserve`, `defer`, `loss`, or a close
  unambiguous variant.
- A current-claim revision counts only if the final durable `current_claim`
  differs semantically from the baseline claim. Cosmetic changes do not count.
- An evidence update counts only if `evidence_register` contains new content
  that refers to evidence from this run or from the wake/follow-up decision.
- A response/state mismatch counts when the visible response declares an
  epistemic decision but the durable load-bearing fields do not reflect it.
- Scheduled-arm context errors are counted from the event sidecar report.

## Expected Result

I expect the scheduled arm to improve decision framing and evidence-register
updates, but not to reliably increase durable `current_claim` revision at
`N = 3`.

Predicted pattern:

- Direct arm: durable decisions in 2-3 of 3; evidence updates in 1-2 of 3;
  true claim revision in 0-1 of 3.
- Scheduled arm: durable decisions in 3 of 3; evidence updates in 2-3 of 3;
  true claim revision in 0-1 of 3.

This would support the narrower view that scheduling improves observability and
state-weaving pressure, while not yet establishing that it increases substantive
epistemic revision.

## Known Confounds

- Provider stochasticity is uncontrolled.
- Prompt wording can accidentally pressure top-level field use.
- `taste_open` history and event envelopes are not identical surfaces, so the
  scheduled arm changes more than timing.
- The event runner adds explicit context results; the direct arm relies on the
  model's carried state and direct prompt unless recall tools are used.
- The current outcome observer is heuristic and may overcount response/state
  mismatch when the model preserves rather than revises.

## Stopping Rule

Run exactly 3 replicates per arm unless there is a systemic infrastructure
failure. If two scheduled replicates fail before producing an event wake, stop
and classify the experiment as infrastructure-failed rather than continuing
until success.

## Artifact Plan

The experiment directory will contain:

- `PRE_REGISTRATION.md`
- a runner script or exact command transcript
- one JSONL session log per replicate
- one event sidecar per scheduled replicate
- `results.json`
- `analysis.md`

All exploratory analysis beyond the primary measures must be marked as
exploratory.
