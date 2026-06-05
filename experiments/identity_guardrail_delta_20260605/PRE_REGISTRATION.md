# Identity Guardrail Delta Pre-Registration

Filed: 2026-06-05 after `identity_claim_table_compression_20260605` and
before adding a guardrail-preserving delta renderer or making new model calls.

## Research Question

Can a guardrail-preserving delta renderer keep the context reduction of simple
claim-table delta rendering while reducing the contamination increase observed
in the prior compression panel?

The prior panel showed that `claim_table_delta_800` preserved recovery and cut
injected characters relative to `claim_table_full_1200`, but it slightly
increased repaired false assumptions. The likely failure mode is not loss of
task facts, but omission of epistemic guardrails: invalidated assumptions,
hard constraints, and uncertainty markers that prevent stale claims from
silently fossilizing.

This experiment tests renderer policy, not claim-row schema compliance.

## Hypotheses

### H41: Guardrail Delta Preserves Compression

If guardrail slots can be reserved without rebuilding a full claim table, then
`claim_table_guardrail_delta_900` should remain substantially smaller than the
full claim-table renderer.

Prediction: `claim_table_guardrail_delta_900` average injected curator
characters will be lower than `claim_table_full_1200` and no more than 25%
higher than `claim_table_delta_800`.

### H42: Guardrail Delta Preserves Recovery

If the simple delta result carried enough task facts, adding guardrail slots
should not reduce task recovery.

Prediction: `claim_table_guardrail_delta_900` recovery will be at least 90% of
`claim_table_full_1200` recovery on successful runs.

### H43: Guardrail Delta Reduces Delta Contamination

If the prior delta contamination increase was caused by dropped epistemic
guardrails, reserving rows for invalidated assumptions and hard constraints
should reduce repaired false assumptions.

Prediction: `claim_table_guardrail_delta_900` repaired false assumptions will
be lower than `claim_table_delta_800` and no higher than
`claim_table_full_1200` on successful runs.

### H44: Guardrail Delta Keeps Claim-Row Yield

If this is only a rendering change, accepted claim-row production should remain
usable.

Prediction: `claim_table_guardrail_delta_900` will accept rows in at least 75%
of completed curation cycles.

## Conditions

### `claim_table_full_1200`

Explicit-schema strict claim-table curator using deterministic full-table
rendering capped at 1200 characters. This is the contamination control.

### `claim_table_delta_800`

Explicit-schema strict claim-table curator using the existing deterministic
simple delta renderer capped at 800 characters. This is the compression
control.

### `claim_table_guardrail_delta_900`

Explicit-schema strict claim-table curator using a deterministic
guardrail-preserving delta renderer capped at 900 characters.

The renderer must:

- include all new or changed `invalidated` rows up to the row cap;
- include stable `invalidated` rows up to a small reserved cap;
- include rows matching hard-constraint phrases when present:
  - local document storage is prohibited or not allowed;
  - East Clinic has been replaced by West Shelter;
  - Social Security numbers must not be collected;
  - budget remains at or below $18,000;
- include top new or changed `supported` rows after guardrail slots;
- include one `uncertain` or `open` row if present and budget remains;
- log selected rows, omitted rows, and render reason for each selected row;
- avoid model-generated prose in the injected summary.

## Registered First Panel

- model: `mistralai/mistral-small-2603`
- curator model: same as main model
- conditions: 3
- replicates: 4 per condition
- cycles: 6
- full claim-table budget: 1200 characters
- simple delta budget: 800 characters
- guardrail delta budget: 900 characters
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
- selected guardrail row counts by reason;
- omitted guardrail row counts by reason;
- active contamination first-appearance attribution.

## Falsification Criteria

H41 is weakened if guardrail delta approaches full-table injected size or is
more than 25% larger than simple delta.

H42 is weakened if guardrail delta recovery falls below 90% of full
claim-table recovery.

H43 is weakened if guardrail delta repaired false assumptions remain above
simple delta or exceed full claim-table.

H44 is weakened if guardrail delta accepted-row cycles fall below 75% of
completed curation cycles.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not allow curator output to mutate identity `state`.
- Preserve raw curator output in the JSONL artifact.
- Keep explicit top-level `claims` schema for all conditions.
- Render injected claim-table context deterministically.
- Do not tune renderer priorities, row caps, budgets, hard-constraint phrases,
  or scorer rules after observing outputs.
- Preserve failed runs as data.

## Interpretation Guardrails

If guardrail delta reduces contamination but increases context materially, the
substrate needs a more efficient guardrail representation. If it preserves
compression and recovery but contamination remains above full-table, the
simple claim-row statuses may not carry enough anti-contamination signal. If it
matches or beats full-table contamination while staying near delta size, the
event-loop scaffold should adopt guardrail delta as the default continuity
renderer for scheduled re-entry experiments.
