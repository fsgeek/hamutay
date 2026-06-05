# Identity Claim-Table Schema Pre-Registration

Filed: 2026-06-05 after the claim-table curator panel and before adding an
explicit claim-table terminal schema or making new model calls.

## Research Question

Can an explicit terminal schema make bounded claim-table continuity curation
usable, and does a logged repair parser materially change the result?

The previous claim-table panel did not actually test claim-table continuity:
the model produced plausible claim rows but placed them inside the required
`response` field, so the strict adapter accepted zero rows. This experiment
separates three possibilities:

1. the model needs an explicit top-level `claims` schema;
2. the model still emits near-miss protocol shapes and needs a logged repair
   parser;
3. claim-table continuity remains weak even when rows are accepted.

## Hypotheses

### H33: Explicit Schema Produces Accepted Claim Rows

If the prior zero-row result was caused by an underspecified terminal schema,
then an explicit curator schema requiring top-level `claims` will produce
accepted claim rows in most completed cycles.

Prediction: `claim_table_strict_schema_1200` accepts at least one claim row in
at least 75% of completed curation cycles.

### H34: Repair Parser Improves Protocol Yield

If the model still produces semantically valid claim rows in near-miss shapes,
then a preregistered repair parser should increase accepted rows over strict
schema alone.

Prediction: `claim_table_repair_parser_1200` accepts more rows and rejects
fewer rows than `claim_table_strict_schema_1200`.

### H35: Accepted Claim Tables Recover More Than Starved Claim Tables

If claim rows carry useful continuity, then any condition with nonzero accepted
claim rows should recover more task facts than the prior zero-row claim-table
condition.

Prediction: both schema conditions exceed 14.67 successful-run average
recovery, the previous successful-run claim-table result.

### H36: Claim Tables Stay Less Contaminating Than Free Summary

If bounded status rows reduce narrative expansion, schema claim-table
conditions should keep repaired false assumptions below the 1200-character
free-summary condition from the previous panel.

Prediction: both schema conditions average fewer than 5.0 repaired false
assumptions per completed run.

## Conditions

### `free_summary_1200`

Use the existing free-summary curator capped at 1200 injected characters. This
is the continuity comparator from the previous panel.

### `claim_table_strict_schema_1200`

Use a curator backend whose terminal `think_and_respond` schema explicitly
defines top-level `claims`. The adapter accepts only top-level `claims` rows.
Misplaced rows inside `response` are rejected and logged.

### `claim_table_repair_parser_1200`

Use the same explicit terminal schema, but enable a logged repair parser in the
claim-table adapter. The parser may recover rows from:

- object-valued `response: {"claims": [...]}`;
- stringified JSON in `response` containing `{"claims": [...]}`.

Every recovered row must be counted separately as a protocol recovery event.
Rows remain subject to the same status validation, row cap, and deterministic
rendering as strict mode.

## Registered First Panel

- model: `mistralai/mistral-small-2603`
- curator model: same as main model
- conditions: 3
- replicates: 4 per condition
- cycles: 6
- curator injected-summary budget: 1200 characters
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

Protocol:

- accepted claim rows;
- rejected claim rows;
- completed curation cycles with at least one accepted claim row;
- protocol recovery events;
- recovered claim rows;
- strict-schema tool-call failures.

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
- curator artifact in state without main-model authorship;
- active contamination first-appearance attribution.

## Falsification Criteria

H33 is weakened if strict schema still accepts zero or near-zero rows.

H34 is weakened if repair parsing does not increase accepted rows or reduce
rejections relative to strict schema.

H35 is weakened if accepted-row schema conditions do not recover more than the
previous zero-row claim-table condition.

H36 is weakened if schema claim-table conditions match or exceed the prior
free-summary repaired false-assumption average.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not allow curator output to mutate identity `state`.
- Preserve raw curator output in the JSONL artifact.
- Render injected claim-table context deterministically.
- Log repair-parser use explicitly and separately from strict accepted rows.
- Do not tune schema, row caps, status labels, budget, or scorer rules after
  observing outputs.
- Preserve failed runs as data.

## Interpretation Guardrails

If strict schema fails but repair parser succeeds, the result supports a
protocol-robustness claim, not a model-understanding claim. If both schema
conditions accept rows but recovery remains low, the claim-table representation
itself becomes suspect. If both accept rows and improve recovery while holding
contamination down, the next question becomes whether claim-table curation can
replace rather than supplement prior state.
