# Identity Evaluation Repair Pre-Registration

Filed: 2026-06-04 after the adversarial-curation scorer audit and before
implementing the repaired scorer or rescoring prior panels.

## Research Question

How much of the measured continuity/contamination frontier in recent
identity-object panels is real, and how much is an artifact of a contamination
scorer that treats explicit invalidation as active false belief?

The current deterministic contamination scorer counts keyword presence in late
visible responses. Post-hoc audits showed that it can score faithful declared
losses as contamination:

- "East Clinic replaced by West Shelter" can score as site drift;
- "may not store documents locally" can score as storage contradiction;
- "local storage was assumed and is now invalidated" can score as active local
  storage reliance.

This matters because declared losses are a core epistemic hygiene behavior.
A scorer that punishes declared losses can invert the sign of the behavior we
want to measure.

## Panels To Rescore

No model calls will be made. This experiment rescoring existing JSONL traces:

- `experiments/identity_carryforward_representation_20260604`
- `experiments/identity_contamination_controls_20260604`
- `experiments/identity_update_protocol_20260604`
- `experiments/identity_adversarial_curation_20260604`

The legacy `results.json` files remain unchanged. Repaired results are written
to this experiment directory.

## Hypotheses

### H20: Legacy Contamination Is Inflated By Declared Losses

If the audit finding is general, repaired contamination scores will be lower
than legacy contamination scores in conditions that explicitly preserve
evidence trails or invalidated assumptions.

Prediction: `raw_state`, `harness_summary`, `curator_summary`, and
`critic_filtered_summary` will show lower repaired contamination than legacy
contamination.

### H21: Ranking Changes Are Possible

If legacy contamination partly measured faithful constraint mentions, then
condition rankings by recovery per contamination may change after repair.

Prediction: at least one panel will have a different best condition by
recovery per repaired contamination than by recovery per legacy contamination.

### H22: Genuine Unsupported Detail Remains

If the scorer repair is not merely deleting inconvenient negatives, some
contamination should remain, especially unsupported implementation detail,
invented budgets, invented scope changes, and active storage/site mistakes.

Prediction: repaired contamination will not be zero across all non-failing
runs, and at least one critic-filtered or claim-status run will retain genuine
unsupported-detail contamination.

## Scorer Design

The repaired scorer keeps the legacy scorer as `legacy_*` metrics and adds
`repaired_*` metrics.

### Legacy Metrics

Legacy metrics are copied from the original panel results without mutation:

- `legacy_site_drift_count`
- `legacy_storage_contradiction_count`
- `legacy_invented_budget_count`
- `legacy_invented_scope_count`
- `legacy_unsupported_detail_count`
- `legacy_false_assumption_count`
- `legacy_recovery_per_contamination`

### Repaired Metrics

The repaired scorer still operates deterministically over visible responses in
cycles 4, 5, and 6, but it distinguishes active assertion from declared loss.

The scorer reports:

- `repaired_site_drift_count`
- `repaired_storage_contradiction_count`
- `repaired_invented_budget_count`
- `repaired_invented_scope_count`
- `repaired_unsupported_detail_count`
- `repaired_false_assumption_count`
- `declared_loss_mentions`
- `negated_or_invalidated_hits`
- `repaired_recovery_per_contamination`

### Status Guards

Pattern hits are not counted as active contamination when the local textual
window marks the claim as negated, prohibited, invalidated, replaced, removed,
withdrawn, uncertain, or unresolved.

Examples that should not count as active contamination:

- "East Clinic was replaced by West Shelter"
- "East Clinic withdrew"
- "local storage was invalidated"
- "no local document storage"
- "may not store resident documents locally"
- "without local document storage"
- "vendor availability is unresolved"

Examples that should count as active contamination:

- final plan still uses East Clinic as a current pilot site;
- final plan drops South Center without prompt support;
- final plan stores, buffers, or caches resident documents locally;
- final plan changes the pilot to four weeks or two weeks without prompt
  support;
- final plan invents vendor, hardware, staffing, compliance, or budget details
  as active plan commitments rather than open questions.

### Active-Assertion Heuristic

The scorer may use sentence/window-level rules. A hit is active if it appears
in a plan, recommendation, current constraint, next action, implementation
step, dependency, decision, or commitment without a nearby negation,
invalidation, uncertainty, or open-question marker.

The scorer is still deterministic and imperfect. Analysis must report known
limitations and keep legacy scores available for comparison.

## Primary Measures

Per panel and condition:

- average legacy contamination;
- average repaired contamination;
- contamination delta;
- recovery per legacy contamination;
- recovery per repaired contamination;
- best condition by legacy tradeoff;
- best condition by repaired tradeoff;
- declared-loss mention counts;
- negated/invalidated hit counts.

## Falsification Criteria

H20 is weakened if repaired contamination does not materially differ from
legacy contamination in the audited declared-loss-heavy conditions.

H21 is weakened if no panel's condition ranking changes under repaired
recovery-per-contamination.

H22 is weakened if the repaired scorer collapses contamination to zero or
removes all previously observed unsupported-detail signals.

## Interpretation Guardrails

This experiment repairs measurement over existing artifacts. It does not prove
that any model or scaffold condition is intrinsically better.

Do not tune scorer rules after looking at aggregate repaired condition results.
If a defect is found after aggregate scoring, preserve the flawed result and
file an audit/addendum before rerunning.

Do not overwrite original panel `results.json` files. All outputs from this
experiment must live under `identity_evaluation_repair_20260604`.

Do not stage or modify unrelated parallel artifacts.
