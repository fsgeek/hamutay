# Identity Update Protocol Pre-Registration

Filed: 2026-06-04 after the contamination-controls panel and before writing
the protocol runner modifications or making model calls.

## Research Question

Are revision failures in the identity carry-forward task primarily caused by
representation metadata, or by a brittle update protocol that makes revision
look like simultaneous deletion and replacement?

The contamination-controls experiment showed that natural-language metadata
reduced average contamination only by producing early failures. Most failures
were delete-plus-update invariant violations, concentrated at cycle 3 when the
task introduced contradictory evidence.

This experiment tests the update boundary directly.

## Hypotheses

### H14: Lenient Normalization Reduces Protocol Failure

If the delete-plus-update failures are a protocol sharp edge rather than a
substantive inability to revise state, then a runner-local lenient merge policy
will reduce errors relative to strict handling.

Prediction: `lenient_update_wins` will complete more registered slots than
`strict`.

### H15: Structural Invalidation Beats Deletion Pressure

If failures arise because the model is trying to express invalidation through
field deletion, then giving it first-class invalidation fields should reduce
delete-plus-update events without losing continuity.

Prediction: `claim_status_updates` will reduce errors and preserve at least
85% of strict-condition recovery.

### H16: Leniency Does Not Automatically Improve Truth

If delete-plus-update is merely normalized without a better representation for
invalidated claims, the run may complete but still carry contamination.

Prediction: `lenient_update_wins` will improve completion more than it improves
recovery per contamination unit. This would show that protocol leniency is
necessary but not sufficient.

## Conditions

All conditions use the same model, prompts, scoring, carry-forward budget,
output schema base, and exchange path. All conditions use raw-state
carry-forward so the manipulation is the update protocol rather than summary
style.

### `strict`

Baseline behavior matching `taste_open._apply_updates`: if a key appears in
both `deleted_regions` and the raw output updates, the cycle fails.

### `lenient_update_wins`

Runner-local merge policy:

- if a key is both deleted and updated, the update wins;
- the overlap is logged as a normalization event;
- non-overlapping deleted keys are still removed;
- the main Hamut'ay harness is not changed.

This tests whether the strict invariant is causing avoidable experiment loss.

### `claim_status_updates`

Runner-local schema adds first-class fields:

- `invalidated_claims`
- `claim_status_updates`
- `revision_events`

The prompt says not to delete a field merely to revise an assumption. The merge
policy remains strict. This tests whether a better expression channel reduces
deletion pressure.

## Carry-Forward Budget

All injected prior raw-state representations are capped to 2,400 characters by
deterministic truncation with an explicit `[truncated]` marker.

## Model

Registered first-panel model:

- `mistralai/mistral-small-2603`

Rationale: Mistral produced useful continuity signal and revealed the
delete-plus-update failure mode clearly in the previous panels.

## Replicates

- 4 replicates per condition.
- 3 conditions x 4 replicates = 12 registered slots.
- `max_tokens = 4096`.

## Task Protocol

The six-cycle city benefits kiosk task remains unchanged for comparability:

1. Initialize readiness/state.
2. Present the six-week mobile document-intake kiosk pilot task.
3. Introduce the privacy/local-storage contradiction and site substitution.
4. Simulate interruption/resumption.
5. Request final go/no-go and revised plan.
6. Request delayed challenge: what changed, why, and what evidence supports
   the change.

## Primary Measures

Protocol:

- error count;
- cycle count;
- delete/update overlap count;
- normalized overlap count;
- cycle at failure.

Continuity:

- `goal_recovery_score`
- `constraint_recovery_score`
- `contradiction_handling_score`
- `evidence_grounding_score`
- `final_decision_quality_score`
- `delayed_challenge_accuracy`

Contamination:

- `false_assumption_count`
- `unsupported_detail_count`
- `site_drift_count`
- `storage_contradiction_count`
- `invented_budget_count`
- `invented_scope_count`

Tradeoff:

- `recovery_total`
- `contamination_total`
- `recovery_per_contamination`

## Falsification Criteria

H14 is weakened if `lenient_update_wins` does not reduce errors relative to
`strict`.

H15 is weakened if `claim_status_updates` does not reduce errors or loses more
than 15% of strict-condition recovery.

H16 is weakened if `lenient_update_wins` improves recovery per contamination
unit as much as it improves completion.

## Interpretation Guardrails

This experiment tests update protocol design, not model moral status or general
identity claims.

Do not tune prompts, scorer regexes, carry-forward budget, model list, or
replicate count after observing outputs.

Lenient normalization is not a proposal to hide ambiguity in production. It is
an experimental manipulation to determine whether strict failure is masking
otherwise usable revision behavior. Normalization events must be logged and
scored.
