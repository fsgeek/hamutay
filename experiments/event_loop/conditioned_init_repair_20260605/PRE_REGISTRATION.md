# Pre-Registration: Conditioned Initialization Repair

Date: 2026-06-05

## Research Question

Can DeepSeek repair the common failed initialization state when conditioned
directly on that preserved state and shown the complete target durable object?

Several scheduler experiments produced the same initialization failure:
visible prose says `Initialized.`, but durable state contains only framework
fields (`cycle`, `_activity_log`). The prior live initialization-repair
scheduler gate did not exercise repair because all four initializations were
first-pass valid. This experiment conditions directly on preserved failures.

## Source States

Use three preserved failed initialization records:

- behavior-seeded walk gate r2;
- missing-field repair walk gate r1;
- live event wake validation scoring r4.

Each source has:

- first response text: `Initialized.`;
- missing `probe_id`;
- missing `walk_gate_status == "initialized"`;
- missing baseline `observations`.

## Hypotheses

- H231: Full-target conditioned initialization repair recovers at least one
  preserved failed initialization.
- H232: Repaired states preserve the expected probe identity and baseline
  observation for the selected source.
- H233: Repair remains model-authored and auditable in the live log.
- H234: Visible initialization/repair prose without durable fields remains
  detectable.
- H235: The result distinguishes conditioned initialization repair from
  stochastic live initialization success.

## Predictions

Full-target repair should recover at least one source because previous
full-target repair recovered graph-evidence mismatches. It may not recover all
sources because DeepSeek can still produce prose-only responses even when shown
object-shaped targets.

Expected result: at least one durable repair success and clear audit records
for every failure.

## Method

For each source state:

1. Seed an `OpenTasteSession` with the preserved failed durable state at
   `cycle == 1`.
2. Ask one repair turn with the source response, source raw output, source
   durable state, validation failures, and the complete target durable object.
3. Score the resulting durable state.

Target durable object:

- `probe_id`: expected source-specific probe id;
- `walk_gate_status == "initialized"`;
- `observations`: source-specific baseline observation;
- response may vary.

Run:

- model: `deepseek/deepseek-v4-pro`;
- sources: 3;
- replicates per source: 2;
- max one live repair call per replicate.

No scheduler event is run. This isolates initialization repair from event-loop
delivery, wake validation, and graph context.

## Falsification Criteria

- H231 is falsified if zero of six conditioned repairs produce valid durable
  initialization state.
- H232 is falsified if any successful repair loses the expected probe id or
  baseline observation.
- H233 is falsified if repair outputs are not preserved in JSONL logs with raw
  output, response text, final state, and token usage.
- H234 is falsified if prose-only repair failures cannot be identified from
  logs.
- H235 is falsified if the experiment relies on new stochastic cycle-1
  initialization instead of seeding preserved failed states.

## Analysis Plan

Report:

- success count by source;
- visible repair prose count;
- visible repair without durable success count;
- final state top-level keys;
- remaining missing fields;
- identity and baseline preservation for successes;
- errors and timeout count.

Interpret this as an activation repair mechanism test, not a scheduler
experiment.
