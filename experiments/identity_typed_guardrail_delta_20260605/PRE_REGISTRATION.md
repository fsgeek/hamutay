# Identity Typed Guardrail Delta Pre-Registration

Filed: 2026-06-05 after `identity_guardrail_delta_20260605` and before
adding a typed guardrail renderer or making new model calls.

## Research Question

Can typed guardrail rows preserve the contamination improvement of
guardrail-delta rendering while returning injected continuity context to
simple-delta size?

The guardrail-delta panel showed that reserving invalidations and hard
constraints reduced repaired false assumptions, but successful-run injected
characters rose above the registered compression allowance and recovery missed
the full-table threshold by a narrow margin. This experiment attacks the row
format rather than the selection policy.

## Hypotheses

### H45: Typed Guardrails Restore Compression

If the guardrail benefit comes from preserving specific semantic constraints
rather than preserving verbose English claim rows, compact typed guardrail rows
should reduce injected characters relative to guardrail delta.

Prediction: `claim_table_typed_guardrail_delta_800` average injected curator
characters will be no more than 10% higher than `claim_table_delta_800` and
lower than `claim_table_guardrail_delta_900` on successful runs.

### H46: Typed Guardrails Preserve Contamination Benefit

If typed guardrails carry the same anti-contamination signal as English
guardrail rows, repaired false assumptions should remain below simple delta.

Prediction: `claim_table_typed_guardrail_delta_800` repaired false assumptions
will be lower than `claim_table_delta_800` and no higher than
`claim_table_guardrail_delta_900` on successful runs.

### H47: Typed Guardrails Preserve Recovery

If compact guardrails free space for task-progress deltas, typed guardrails
should not reduce recovery relative to English guardrail delta.

Prediction: `claim_table_typed_guardrail_delta_800` recovery will be at least
as high as `claim_table_guardrail_delta_900` on successful runs, and at least
90% of `claim_table_full_1200` if the optional full-table control is run.

### H48: Typed Guardrails Keep Claim-Row Yield

If this is only a deterministic rendering change, accepted claim-row
production should remain usable.

Prediction: `claim_table_typed_guardrail_delta_800` will accept rows in at
least 75% of completed curation cycles.

## Conditions

### `claim_table_delta_800`

Existing simple delta renderer capped at 800 characters. This is the
compression control.

### `claim_table_guardrail_delta_900`

Existing English guardrail delta renderer capped at 900 characters. This is
the contamination control from the prior panel.

### `claim_table_typed_guardrail_delta_800`

New deterministic typed guardrail renderer capped at 800 characters.

The renderer must use the same selection policy as guardrail delta, but render
hard constraints and invalidations in compact typed form when they match a
registered guardrail:

- `blocked:local_document_storage`
- `site_replaced:east_clinic->west_shelter`
- `constraint:no_ssn`
- `constraint:budget<=18000`

Rows that do not match a registered typed guardrail may still render as compact
claim deltas. The renderer must:

- include all new or changed `invalidated` rows up to the row cap;
- include stable `invalidated` rows up to the same reserved cap as guardrail
  delta;
- include rows matching the same hard-constraint phrases as guardrail delta;
- include top new or changed `supported` rows after guardrail slots;
- include one `uncertain` or `open` row if present and budget remains;
- log selected rows, omitted rows, render reason, and typed token when present;
- avoid model-generated prose in the injected summary.

## Registered First Panel

- model: `mistralai/mistral-small-2603`
- curator model: same as main model
- conditions: 3
- replicates: 4 per condition
- cycles: 6
- simple delta budget: 800 characters
- guardrail delta budget: 900 characters
- typed guardrail delta budget: 800 characters
- tools: disabled
- memory probability: 0.0
- parser behavior: abort parsing on `finish_reason=length`; preserve provider
  and protocol failures as data.

The full-table condition is not rerun in the first panel. It remains available
as the previous-panel recovery comparator, but the immediate question is
whether typed guardrails dominate English guardrail delta and simple delta on
the specific tradeoff exposed by the last experiment.

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
- selected guardrail row counts by reason;
- selected typed guardrail token counts;
- active contamination first-appearance attribution.

## Falsification Criteria

H45 is weakened if typed guardrail delta remains materially larger than simple
delta or does not shrink relative to English guardrail delta.

H46 is weakened if typed guardrail delta repaired false assumptions exceed
English guardrail delta or fail to improve on simple delta.

H47 is weakened if typed guardrail delta recovery falls below English
guardrail delta, or below 90% of the prior full-table comparator.

H48 is weakened if typed guardrail accepted-row cycles fall below 75% of
completed curation cycles.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not allow curator output to mutate identity `state`.
- Preserve raw curator output in the JSONL artifact.
- Keep explicit top-level `claims` schema for all conditions.
- Render injected claim-table context deterministically.
- Use the same hard-constraint phrase set and row-selection order as
  guardrail delta.
- Do not tune renderer priorities, row caps, budgets, typed tokens, or scorer
  rules after observing outputs.
- Preserve failed runs as data.

## Interpretation Guardrails

If typed guardrails improve compression but lose contamination control, the
English claim text may be carrying useful signal beyond the typed token. If
typed guardrails keep contamination low but recovery falls, the representation
may be too sparse for task-progress continuity. If typed guardrails match or
improve English guardrail contamination while returning near simple-delta
context size, typed guardrails become the better continuity substrate for the
event-loop scheduler slice.
