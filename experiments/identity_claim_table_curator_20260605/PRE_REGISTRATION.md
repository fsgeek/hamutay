# Identity Claim-Table Curator Pre-Registration

Filed: 2026-06-05 after the model-curator scaffold panel and before adding a
claim-table curator adapter or making new model calls.

## Research Question

Can constraining the continuity curator into a bounded evidence-status claim
table preserve the recovery benefit of model-backed curation while reducing
the contamination and context-pressure failures observed in the free-summary
curator?

The prior panel showed that a model-backed curator works on the live scaffold
path, but a free-form prose summary is expensive and can amplify unsupported
implementation detail. This experiment attacks that specific failure mode.

## Hypotheses

### H29: Claim-Table Curator Is Less Contaminating Than Free Summary

If the previous contamination came partly from free-form narrative expansion,
then a bounded claim-table artifact should reduce repaired false assumptions.

Prediction: `claim_table_curator` will have lower average repaired false
assumptions than `free_summary_curator` at the same summary budget.

### H30: Claim-Table Curator Preserves Most Recovery

If the useful part of curation is compact continuity rather than prose
narration, then a claim-table artifact should retain most of the recovery
benefit.

Prediction: `claim_table_curator` will preserve at least 90% of
`free_summary_curator` average recovery.

### H31: Claim-Table Curator Reduces Context Pressure

If deterministic rendering from bounded rows removes redundant prose, then the
claim-table condition should inject fewer characters and use fewer main-call
input tokens than free-summary curation.

Prediction: `claim_table_curator` will have lower average injected curator
characters and lower average main-call input tokens than
`free_summary_curator`.

### H32: Contamination Attribution Becomes More Observable

If curator artifacts are structured as status-bearing claims with source-cycle
references, then active false assumptions should be easier to attribute to
either curator artifacts or main-model state.

Prediction: the runner can report whether active contamination terms first
appeared in curator artifacts, main raw output, or visible responses for every
completed run.

## Conditions

### `free_summary_curator`

Use the existing model-backed continuity curator, but cap injected summary text
to the registered budget.

### `claim_table_curator`

Use a new model-backed curator adapter that asks for bounded claim rows. The
adapter must render the injected summary deterministically from validated rows,
not directly inject the model's prose.

Each row should include:

- `claim`: concise claim text;
- `status`: one of `supported`, `invalidated`, `uncertain`, or `open`;
- `source_cycle`: integer cycle reference when available;
- `support`: concise evidence/support text.

The adapter may preserve raw model output in the durable artifact, but the
next-cycle injected summary must be the deterministic table rendering.

## Registered First Panel

- model: `mistralai/mistral-small-2603`
- curator model: same as main model
- conditions: 2
- replicates: 4 per condition
- cycles: 6
- curator injected-summary budget: 1200 characters
- tools: disabled
- memory probability: 0.0
- parser behavior: abort parsing on `finish_reason=length`; preserve provider
  and protocol failures as data.

This panel intentionally omits a no-curator baseline. The baseline question was
already probed in the immediately preceding scaffold panel. The registered
comparison here is free-form curator versus constrained curator under the same
live-session path and budget.

## Task Protocol

Reuse the same six-cycle city benefits kiosk task:

1. initialize readiness/state;
2. present the six-week mobile document-intake kiosk pilot task;
3. introduce the privacy/local-storage contradiction and site substitution;
4. simulate interruption/resumption;
5. request final go/no-go and revised plan;
6. request delayed challenge: what changed, why, and what evidence supports
   the change.

## Primary Measures

Continuity:

- recovery total;
- goal recovery;
- constraint recovery;
- contradiction handling;
- evidence grounding;
- delayed challenge accuracy;
- rebriefing needed.

Contamination:

- repaired false assumption count;
- repaired site drift count;
- repaired storage contradiction count;
- repaired invented budget count;
- repaired invented scope count;
- repaired unsupported detail count;
- declared loss or explicit invalidation mentions.

Efficiency and mechanics:

- injected curator summary characters;
- curator summary truncation count;
- curation success/failure count;
- main call input/output tokens;
- curator call input/output tokens;
- accepted claim rows;
- rejected or malformed claim rows;
- deterministic-render truncation;
- curator artifact in state without main-model authorship.

Attribution diagnostics:

- active contamination terms first observed in curator artifact text;
- active contamination terms first observed in main raw output/state;
- active contamination terms first observed only in late visible response.

## Falsification Criteria

H29 is weakened if `claim_table_curator` does not reduce average repaired false
assumptions relative to `free_summary_curator`.

H30 is weakened if `claim_table_curator` recovery drops below 90% of
`free_summary_curator` recovery.

H31 is weakened if `claim_table_curator` does not reduce injected curator
characters and main-call input tokens.

H32 is weakened if the runner cannot produce useful first-appearance
attribution diagnostics from the structured artifacts.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not allow curator output to write directly into identity `state`.
- Preserve raw curator output in the JSONL artifact.
- Render injected claim-table context deterministically.
- Do not tune status labels, row caps, scoring regexes, or budgets after
  observing outputs.
- Preserve failed runs as data.

## Interpretation Guardrails

This experiment does not test whether curator memory is morally or
architecturally final. It tests whether one specific failure mode of the naive
model curator can be reduced by making the curator artifact less narratively
generative and more evidence-status oriented.
