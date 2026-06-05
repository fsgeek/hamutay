# Identity Claim-Table Compression Pre-Registration

Filed: 2026-06-05 after the explicit-schema claim-table panel and before
adding a delta/prioritized renderer or making new model calls.

## Research Question

Can a prioritized delta renderer reduce claim-table continuity context while
preserving the recovery and contamination advantages of explicit-schema
claim-table curation?

The explicit-schema panel showed that strict claim tables accepted rows
reliably and preserved nearly all free-summary recovery while reducing repaired
false assumptions. It did not reduce injected context because the renderer
often hit the 1200-character cap. This experiment attacks renderer
compression, not schema compliance.

## Hypotheses

### H37: Delta Rendering Reduces Injected Context

If repeated full-table rendering is the main source of context pressure, then
a delta/prioritized renderer should inject fewer characters and use fewer main
input tokens than the full claim-table renderer.

Prediction: `claim_table_delta_800` will reduce average injected curator
characters and average main-call input tokens relative to
`claim_table_full_1200`.

### H38: Delta Rendering Preserves Most Recovery

If stable constraints plus new/changed claims carry the useful continuity, then
delta rendering should preserve most of full-table recovery.

Prediction: `claim_table_delta_800` recovery will be at least 90% of
`claim_table_full_1200` recovery on successful runs.

### H39: Delta Rendering Does Not Increase Contamination

If delta rendering removes redundant prose rather than dropping epistemic
status, it should not increase repaired false assumptions.

Prediction: `claim_table_delta_800` repaired false assumptions will be no
higher than `claim_table_full_1200` on average.

### H40: Delta Rendering Keeps Claim-Row Yield

If compression is only a rendering change, then accepted claim-row production
should remain comparable between full and delta conditions.

Prediction: `claim_table_delta_800` will accept rows in at least 75% of
completed curation cycles.

## Conditions

### `free_summary_1200`

Existing free-summary curator capped at 1200 injected characters. Comparator
for continuity/recovery and contamination.

### `claim_table_full_1200`

Explicit-schema strict claim-table curator using deterministic full-table
rendering capped at 1200 characters. This is the positive claim-table control.

### `claim_table_delta_800`

Explicit-schema strict claim-table curator using deterministic prioritized
delta rendering capped at 800 characters.

The delta renderer should:

- preserve new or changed rows since the prior curator artifact;
- preserve a small stable set of active constraints;
- preserve a small stable set of invalidated assumptions;
- prioritize statuses in this order: `invalidated`, `supported`, `uncertain`,
  `open`;
- log selected rows, omitted rows, and rendering reason for each selected row;
- avoid model-generated prose in the injected summary.

## Registered First Panel

- model: `mistralai/mistral-small-2603`
- curator model: same as main model
- conditions: 3
- replicates: 4 per condition
- cycles: 6
- free-summary budget: 1200 characters
- full claim-table budget: 1200 characters
- delta claim-table budget: 800 characters
- tools: disabled
- memory probability: 0.0
- parser behavior: abort parsing on `finish_reason=length`; preserve provider
  and protocol failures as data.

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
- main call input/output tokens;
- curator call input/output tokens;
- accepted claim rows;
- rejected claim rows;
- completed curation cycles with at least one accepted row;
- selected delta rows;
- omitted delta rows;
- delta summary truncation;
- active contamination first-appearance attribution.

## Falsification Criteria

H37 is weakened if delta rendering does not reduce injected characters and
main-call input tokens.

H38 is weakened if delta recovery falls below 90% of full claim-table recovery.

H39 is weakened if delta repaired false assumptions exceed full claim-table
false assumptions.

H40 is weakened if delta accepted-row cycles fall below 75% of completed
curation cycles.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not allow curator output to mutate identity `state`.
- Preserve raw curator output in the JSONL artifact.
- Keep explicit top-level `claims` schema for claim-table conditions.
- Render injected claim-table context deterministically.
- Do not tune renderer priorities, row caps, budgets, or scorer rules after
  observing outputs.
- Preserve failed runs as data.

## Interpretation Guardrails

If delta reduces context but loses recovery, full-table continuity may require
redundancy or broader stable context. If delta preserves recovery but increases
contamination, compression may be removing uncertainty/invalidated status. If
delta preserves recovery and lowers context without more contamination, the
event-loop scaffold has a stronger candidate continuity substrate.
