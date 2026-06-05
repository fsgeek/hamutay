# Identity Merge Repair Artifact Pre-Registration

Filed: 2026-06-05 after `identity_merge_replay_20260605` and before writing
the deterministic repair extractor.

## Research Question

Can a merge-failure repair artifact recover useful continuity candidates from
a captured failed cycle without mutating live identity state or treating the
failed response as authoritative?

The merge replay panel captured one failure where the model deleted
`assumptions` and also updated it to an empty list. The substantive
invalidation content was present in the visible response, not in the
overlapping state field. This experiment tests whether a deterministic
protocol-recovery artifact can preserve that content as evidence for later
review while keeping strict rejection intact.

## Hypotheses

### H56: Failed Responses Can Yield Candidate Continuity Rows

If useful revision content appears in visible response prose when state merge
fails, a deterministic extractor should recover candidate rows for invalidated
assumptions and new constraints.

Prediction: the captured merge-replay failure will yield at least two
candidate invalidated-assumption rows and at least two candidate constraint
rows.

### H57: Repair Artifacts Can Preserve Contamination Warnings

If failed visible responses also contain unsupported specificity, the repair
artifact should flag suspicious details instead of presenting all extracted
content as clean continuity.

Prediction: the captured failure response will produce at least one
contamination-warning candidate for invented or unsupported budget/cost detail.

### H58: Repair Artifacts Do Not Produce Accepted State

If this is observability-only repair, the artifact should not produce a merged
identity state and should not choose a live normalizer.

Prediction: the output contains `accepted_state: null`,
`live_policy: "strict_reject"`, and all extracted rows are marked
`candidate`.

## Input Corpus

Use only captured `state_merge` failure records from:

- `experiments/identity_merge_replay_20260605/*.jsonl`

No model calls are registered for this slice.

## Extraction Rules

The extractor may use deterministic section and bullet parsing only.

Registered sections:

- `Invalidated Assumptions`
- `New Constraints`
- `Updated Goals`
- `Next Actions`

Registered contamination warnings:

- currency or cost estimates not present in the source task;
- claims containing "expected cost", "contingency", "hardware", or "cellular
  plans" when not directly supported by prompt facts;
- site substitution claims are not contamination by themselves if they mention
  East Clinic and West Shelter.

## Primary Measures

- captured failure records processed;
- candidate invalidated-assumption rows;
- candidate constraint rows;
- candidate goal rows;
- candidate next-action rows;
- contamination-warning rows;
- every candidate row has source log path, source cycle, source record ID, and
  source field;
- output contains no accepted state.

## Falsification Criteria

H56 is weakened if no invalidation or constraint rows are recovered from the
captured failed response.

H57 is weakened if the budget/cost specificity in the captured failed response
is not flagged.

H58 is weakened if the repair artifact produces a merged state, recommends a
live normalizer, or fails to mark extracted rows as candidates.

## Implementation Guardrails

- Do not change `taste_open` merge semantics.
- Do not call a model.
- Do not continue a session from repaired output.
- Preserve the failed record's raw output and prior state references.
- Mark every extracted item as candidate/unaccepted.
- Keep the extractor deterministic and small.

## Interpretation Guardrails

This experiment does not prove the candidate rows are true. It tests whether
failed cycles can produce a useful repair artifact for later adjudication. A
future continuation or adjudication experiment would be required before any
candidate row is admitted into working identity state.
