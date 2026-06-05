# Identity Merge Replay Pre-Registration

Filed: 2026-06-05 after merge-failure capture instrumentation and before
writing the replay runner or making new model calls.

## Research Question

Can captured strict merge-failure payloads be replayed offline to distinguish
candidate delete-plus-update merge policies without changing live session
semantics?

Recent panels repeatedly failed when the model listed a top-level key in both
`deleted_regions` and same-cycle updates. The harness now captures those
failed raw outputs as JSONL records. This experiment tests whether those
captured records are sufficient to evaluate candidate merge semantics offline.

## Hypotheses

### H52: Strict Capture Produces Replayable Merge Failures

If the overlap failure mode remains active after instrumentation, a strict
panel using a previously fragile condition should produce at least one
captured `state_merge` failure record.

Prediction: a 6-replicate `claim_table_guardrail_delta_900` panel will produce
at least one JSONL record with `status: "failed"` and
`failure_classification.failure_stage: "state_merge"`.

### H53: Update-Wins Preserves More Authored Structure Than Delete-Wins

If overlap usually means "replace this field" rather than "remove this field",
then offline `update_wins` replay should preserve more model-authored
top-level structure than `delete_wins`.

Prediction: across captured failures, `update_wins` will retain every overlap
key with its same-cycle value, while `delete_wins` will drop those keys. The
aggregate retained-overlap-key count will be higher under `update_wins`.

### H54: Delete-Then-Update Is an Alias of Update-Wins for Top-Level Fields

For the current top-level identity-state protocol, applying deletions before
same-cycle updates yields the same final state as update-wins.

Prediction: `delete_then_update` and `update_wins` replay states will be
identical for all captured top-level overlap failures.

### H55: Replay Data Is Not Enough To Pick A Live Policy

Offline replay can show structural consequences, but it cannot prove that a
normalized state remains behaviorally truthful without continuing the session
from that state.

Prediction: replay analysis will classify policy consequences and candidate
risks, but will not recommend changing live merge semantics solely from this
offline slice.

## Registered Capture Panel

- model: `mistralai/mistral-small-2603`
- curator model: same as main model
- condition: `claim_table_guardrail_delta_900`
- replicates: 6
- cycles: 6
- tools: disabled
- memory probability: 0.0
- parser behavior: abort parsing on `finish_reason=length`; preserve provider
  and protocol failures as data.

Rationale: the prior typed-guardrail panel produced three strict merge
failures in four `claim_table_guardrail_delta_900` replicates. The goal is not
to compare renderer quality; it is to collect captured failed payloads for
offline replay.

## Replay Policies

### `strict_reject`

Current live behavior. Any overlap remains a failure. No normalized state is
produced.

### `update_wins`

For overlap keys, keep the same-cycle update value and ignore the overlapping
delete. Non-overlapping deletions still remove keys.

### `delete_wins`

For overlap keys, apply the delete and discard the same-cycle update.
Non-overlapping updates still apply.

### `delete_then_update`

Apply all deletions first, then all same-cycle updates. Under the current
top-level protocol this is expected to be equivalent to `update_wins`; it is
included to make that equivalence explicit.

## Primary Measures

Capture:

- total runs;
- completed runs;
- captured `state_merge` failure records;
- overlap keys by run and cycle;
- failed raw outputs preserved;
- prior states preserved.

Replay:

- retained overlap keys by policy;
- dropped overlap keys by policy;
- final top-level key count by policy;
- equality of `delete_then_update` and `update_wins` replay states;
- state JSON byte size by policy;
- policy consequence records for each failed payload.

Risk classification:

- whether overlap key names are central task fields;
- whether deleting the key would remove all current representation of goals,
  constraints, assumptions, evidence, next actions, or continuity notes;
- whether update-wins keeps explicit invalidation/revision language when
  present.

## Falsification Criteria

H52 is weakened if no captured `state_merge` failures occur.

H53 is weakened if `update_wins` does not retain more overlap-key structure
than `delete_wins`.

H54 is weakened if `delete_then_update` and `update_wins` differ for any
captured top-level overlap.

H55 is weakened only if replay data alone establishes an unambiguous policy
choice with no behavioral-continuation uncertainty. The expected result is
that replay informs but does not settle live semantics.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not normalize live session failures.
- Do not continue failed live runs from normalized states in this experiment.
- Preserve failed records as data.
- Replay policies must operate only on captured JSONL payloads.
- Do not tune policies, replicate count, or risk categories after observing
  captured failures.

## Interpretation Guardrails

This experiment is a bridge from observability to policy design. It can show
what state each candidate policy would produce, but it cannot by itself show
whether the instance would behave better or worse after normalization. A later
continuation experiment would be needed before adopting a live normalizer.
