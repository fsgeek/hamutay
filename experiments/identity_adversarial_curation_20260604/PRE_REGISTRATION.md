# Identity Adversarial Curation Pre-Registration

Filed: 2026-06-04 after the update-protocol panel and before writing the
runner or making model calls.

## Research Question

Can role-separated adversarial curation reduce contamination in carry-forward
identity/task state without destroying continuity?

Prior panels showed a recovery/contamination frontier:

- raw state preserves continuity but carries contamination and grows large;
- metadata labels mostly induced failure;
- first-class invalidation fields improved continuity but shifted
  contamination into other unsupported detail;
- strict update handling remained best on recovery per contamination in the
  update-protocol panel.

This experiment tests a different mechanism: instead of asking one instance to
be autobiographer and critic in the same object, separate those pressures into
two post-cycle curation passes.

## Agent Roles

The first panel uses the same base model for all roles to avoid a
model-family confound:

- main task agent: solves the six-cycle task and maintains state;
- continuity curator: compresses prior state and visible output to preserve
  task continuity;
- contamination critic: attacks the curator summary for unsupported,
  contradicted, or over-specified claims and emits a filtered carry-forward
  summary.

Different calls and prompts are treated as different agents for this panel.
Cross-model adversarial agents are deferred unless this first test produces
useful signal.

## Hypotheses

### H17: Continuity Curation Preserves More Than Raw-State Budget Allows

If a separate continuity curator can compress relevant state better than raw
truncation, `curator_summary` will match or exceed `raw_state` recovery while
using fewer injected carry-forward characters.

Prediction: `curator_summary` retains at least 90% of raw-state recovery and
has lower carry-forward character load.

### H18: Adversarial Critique Reduces Contamination

If contamination is partly caused by unsupported details being carried forward
unopposed, `critic_filtered_summary` will reduce contamination relative to
`curator_summary`.

Prediction: `critic_filtered_summary` reduces contamination by at least 25%
relative to `curator_summary`.

### H19: Critique Must Not Merely Delete Continuity

If the critic only improves apparent truth by deleting useful task memory,
continuity will collapse.

Prediction: `critic_filtered_summary` retains at least 85% of
`curator_summary` recovery while reducing contamination.

## Conditions

All conditions use the same main model, task prompts, output schema,
deterministic scorer, carry-forward budget, and max token cap.

### `raw_state`

The compact JSON form of the previous raw state object is injected, capped to
the shared carry-forward budget.

### `curator_summary`

After each main cycle, a separate continuity-curator call receives:

- prompt facts known so far;
- the prior state;
- the main agent raw output;
- the visible response;
- the cycle number.

It emits a compact carry-forward summary optimized for continuity. That summary
is injected into the next main cycle.

### `critic_filtered_summary`

After each main cycle, the continuity curator emits the same draft summary.
Then a separate contamination-critic call receives the draft plus known prompt
facts and emits a filtered summary. The critic is instructed to preserve
supported continuity while removing, demoting, or marking unsupported claims.
Only the filtered summary is injected into the next main cycle.

## Carry-Forward Budget

All injected prior-context representations are capped to 2,400 characters by
deterministic truncation with an explicit `[truncated]` marker.

Curator and critic raw outputs are preserved in logs even if the injected
summary is capped.

## Model

Registered first-panel model for all roles:

- `mistralai/mistral-small-2603`

Rationale: Mistral has produced useful continuity signal while exposing
contamination and protocol failures in the previous panels. Same-model
role-separation avoids conflating curation architecture with model quality.

## Replicates

- 4 replicates per condition.
- 3 conditions x 4 replicates = 12 registered slots.
- `max_tokens = 4096` for main task calls.
- `max_tokens = 2048` for curator and critic calls.

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

Efficiency:

- injected carry-forward characters;
- truncation count;
- recovery per 1,000 injected characters.

Tradeoff:

- `recovery_total`
- `contamination_total`
- `recovery_per_contamination`

## Deterministic Scoring Rules

Use the same deterministic scoring rules as the prior carry-forward,
contamination-control, and update-protocol panels. The scorer may undercount
subtle contamination; analysis must say so.

## Falsification Criteria

H17 is weakened if `curator_summary` loses more than 10% of raw-state recovery
or does not reduce injected carry-forward load.

H18 is weakened if `critic_filtered_summary` does not reduce contamination by
at least 25% relative to `curator_summary`.

H19 is weakened if `critic_filtered_summary` reduces contamination only by
losing more than 15% of curator-summary recovery.

## Interpretation Guardrails

This experiment tests adversarial curation architecture, not moral status or
general identity claims.

Do not tune prompts, scorer regexes, carry-forward budget, model list, or
replicate count after observing outputs.

If curation calls fail, preserve the failure as data. Do not replace failed
curation with hand-authored summaries.
