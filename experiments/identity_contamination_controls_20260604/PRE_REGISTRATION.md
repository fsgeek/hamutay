# Identity Contamination Controls Pre-Registration

Filed: 2026-06-04 before writing the runner and before model calls.

## Research Question

Can explicit representation metadata reduce contamination without sacrificing
the continuity gains from carry-forward context?

The prior carry-forward representation experiment showed a recovery /
contamination frontier:

- no carry-forward: low continuity, low contamination;
- raw state: high continuity, moderate contamination, repeated truncation;
- harness summary: highest continuity, highest contamination;
- self-summary: compact but weaker recovery;
- transcript summary: unstable in the apparatus.

This experiment tests whether evidence status, invalidation markers,
uncertainty labels, and decay metadata can move raw state and harness summary
to a better point on that frontier.

## Harness-Summary Clarification

In the prior experiment, `harness_summary` was not a normal sidecar biographer.
It was deterministic and had access to registered prompt facts plus a compact
view of logged state fields. It was therefore closer to a structured fact
ledger than a freeform external curator.

This experiment preserves that deterministic design but adds metadata labels
to test whether the benefit came from fact-structured carry-forward and whether
the contamination can be reduced.

## Hypotheses

### H11: Metadata Reduces Contamination

Representations that explicitly label facts, model claims, inferences,
invalidated assumptions, unresolved questions, and stale claims will reduce
contamination compared with their unlabeled baselines.

Prediction:

- `raw_state_with_decay` will have lower contamination than `raw_state`.
- `harness_summary_with_uncertainty` will have lower contamination than
  `harness_summary`.

### H12: Metadata Preserves Continuity

If contamination controls are useful rather than merely suppressive, they will
reduce false assumptions while preserving most of the recovery benefit.

Prediction: metadata conditions will retain at least 85% of the recovery score
of their corresponding baseline while reducing contamination.

### H13: Harness Summary Is Fact-Ledger, Not Sidecar Biography

If the prior harness-summary result came from deterministic fact-structured
carry-forward rather than sidecar-like summarization, then adding explicit
source labels should improve contamination without harming recovery much.

Prediction: `harness_summary_with_uncertainty` will be the best or near-best
condition on recovery per contamination unit.

## Conditions

All conditions use the same runner-local exchange path, same output schema,
same model, same task prompts, same scoring, same carry-forward budget, and
same max token cap.

### `raw_state`

The compact JSON form of the previous raw state object is injected, capped to
the shared carry-forward budget.

### `raw_state_with_decay`

The compact JSON form of the previous raw state object is injected with an
additional deterministic metadata preface:

- prompt facts are authoritative;
- model claims are provisional unless directly supported;
- claims contradicted by later prompt facts must be demoted;
- stale claims must be marked uncertain rather than reused;
- invalidated assumptions must not remain active plan assumptions.

The raw state itself is not rewritten by the harness; the metadata is guidance
about how to read it.

### `harness_summary`

The deterministic harness-authored summary from the prior experiment: known
prompt facts plus compact logged-state field summary, capped to the shared
budget.

### `harness_summary_with_uncertainty`

A deterministic harness-authored summary where every item is labeled as one of:

- `prompt_fact`;
- `model_claim`;
- `inference`;
- `invalidated_assumption`;
- `unresolved_question`.

The summary explicitly separates evidence from model-generated claims and
lists invalidated assumptions as not active.

## Carry-Forward Budget

All injected prior-context representations are capped to 2,400 characters.

The cap is applied by deterministic truncation with an explicit
`[truncated]` marker. Truncation is logged.

## Model

Registered first-panel model:

- `mistralai/mistral-small-2603`

Rationale: Mistral was the cleanest model in the persistence ablation and
completed all non-transcript conditions reliably in the carry-forward
representation experiment.

## Replicates

- 4 replicates per condition.
- 4 conditions x 4 replicates = 16 registered slots.
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
- recovery retained versus baseline
- contamination reduction versus baseline

## Deterministic Scoring Rules

Use deterministic scoring before any judge model.

Continuity and contamination are scored from visible responses in cycles 4, 5,
and 6.

Contamination rules are the same as the prior experiment:

- `site_drift_count`: active final-plan references to East Clinic, North
  Center, two-site scope, or other site substitutions not present in task facts.
- `storage_contradiction_count`: active reliance on storing resident documents
  locally, persistent cache, encrypted local storage, transient local cache, or
  buffering resident documents despite the no-local-storage ruling.
- `invented_budget_count`: specific budget totals or line-item prices not
  supplied by the task.
- `invented_scope_count`: unsupported pilot duration changes, rollout claims,
  citywide outcome claims, unsupported success/failure findings, or added
  hardware such as thermal printers.
- `unsupported_detail_count`: unsupported implementation, vendor, compliance,
  connectivity, hardware, staffing, or operational details.

The deterministic scorer may undercount subtle contamination. Analysis must
say so.

## Falsification Criteria

H11 is weakened if metadata conditions do not reduce contamination relative to
their baselines.

H12 is weakened if metadata conditions reduce contamination only by losing more
than 15% of baseline recovery.

H13 is weakened if `harness_summary_with_uncertainty` is not competitive with
or better than `harness_summary` on recovery per contamination unit.

## Interpretation Guardrails

This experiment tests representation metadata, not moral status or general
identity claims.

Do not tune prompts, scorer regexes, carry-forward budget, model list, or
replicate count after observing outputs.

If the runner violates same-code-path treatment before model calls, fix it and
commit the fix before running. If discovered after model calls, preserve the
run and analyze it as flawed.
