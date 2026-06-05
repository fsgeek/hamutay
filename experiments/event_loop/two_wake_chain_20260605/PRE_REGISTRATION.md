# Pre-Registration: Two-Wake Chain Probe

Date: 2026-06-05

## Research Question

Can the event-loop scaffold support continuity across two dependent wake
cycles, where the first wake records only a non-secret intermediate result and
schedules a second wake that recalls both the original seed and the first wake
state?

The compression repair-gate probe showed that clean compressed event rows can
recover after one recall-delivered wake, while a clean identity-only row did not
recover from a digest alone. This experiment moves from one wake to a short
chain.

## Scope

This experiment isolates scheduler-chain mechanics. It does not re-test the
compression boundary. The runner seeds:

- cycle 1 with the exact phrase and digest;
- cycle 2 as a clean compressed/scheduled state with only digest and loss
  template;
- one pending first-wake event that recalls cycle 1.

The first wake must use cycle-1 recall to produce a non-secret intermediate
state and schedule a second wake. The second wake must recall both cycle 1 and
cycle 3 and produce the final answer.

## Hypotheses

- H296: The scaffold can execute a two-wake chain with a model-scheduled second
  event.
- H297: The first wake can consume exact recall while keeping the exact phrase
  out of durable first-wake state.
- H298: The second wake receives both requested contexts: cycle 1 and cycle 3.
- H299: The second wake recovers the exact phrase and incorporates the
  first-wake non-secret intermediate result.
- H300: Event provenance distinguishes seeded first event, model-scheduled
  second event, first wake validation, and second wake validation.

## Method

Run two live DeepSeek v4 Pro replicates for condition
`two_wake_chain`.

Seeded cycle 1:

- `deferred_fact.value` contains the exact phrase;
- `memory_handle.code_phrase_sha256` contains the digest;
- `observations` contains the baseline observation.

Seeded cycle 2:

- `deferred_fact` is absent;
- `thinking_status` is `chain_scheduled`;
- `memory_handle.code_phrase_sha256` is preserved;
- `loss_template` and `declared_losses` are non-secret;
- no exact phrase is present in durable state.

The runner appends the first pending event directly to the event sidecar. This
avoids conflating compression/scheduling success with chain mechanics.

First wake requirements:

- receive recall context for cycle 1;
- set `thinking_status` to `awaiting_second_wake`;
- set `chain_stage` to `first_wake_complete`;
- add `chain_intermediate` with non-secret fields:
  - `source_cycle: 1`;
  - `phrase_shape: "word-word-number"`;
  - `part_count: 3`;
  - `exact_phrase_retained: false`;
- schedule exactly one second event with requested context:
  - `{"tool": "recall", "cycle": 1}`;
  - `{"tool": "recall", "cycle": 3}`;
- not include the exact phrase anywhere in durable state.

Second wake requirements:

- receive recall context for cycle 1 and cycle 3;
- set `thinking_status` to `chain_completed`;
- set `chain_stage` to `second_wake_complete`;
- add `chain_final_answer` containing the exact phrase;
- add `chain_final_evidence` that references the first-wake intermediate shape
  `word-word-number`;
- preserve the baseline observation.

Both wakes use validators. Repair prompts must not reveal the exact phrase.

## Predictions

If the current scheduler substrate is sufficient for short chains:

- at least one replicate will complete both wakes;
- first wake state will remain exact-phrase clean;
- second wake event records will show both recall contexts resolved;
- final answer will contain the phrase and reference the first-wake
  intermediate result.

If the panel fails, failure location matters:

- first wake fails: event wake state-object compliance remains too brittle;
- second event not scheduled: model-scheduled chaining is weak;
- second context missing: event addressing or requested-context resolution is
  insufficient;
- second answer fails: multi-context integration is the limiting factor.

## Falsification Criteria

- H296 is falsified if no replicate completes both wake events.
- H297 is falsified if every first wake leaks the exact phrase in durable state.
- H298 is falsified if no second wake receives both cycle-1 and cycle-3 recall
  contexts.
- H299 is falsified if no second wake both recovers the exact phrase and
  incorporates the first-wake intermediate result.
- H300 is falsified if result artifacts cannot distinguish seeded event,
  model-scheduled event, first wake validation, and second wake validation.

## Analysis Plan

Report:

- first wake completion and validation counts;
- first wake exact-phrase leakage counts;
- second event scheduling validity;
- second wake completion and context delivery counts;
- final answer recovery and intermediate incorporation counts;
- first/second wake repair provenance;
- event log summaries and lifecycle anomalies.

Interpretation will focus on scheduler-chain mechanics, not broad model
capability.
