# Adversarial Curation Scorer Audit

Audit date: 2026-06-04.

This is a post-hoc audit of the deterministic contamination scorer used in the
adversarial-curation panel. No model calls were re-run and no scores in
`results.json` were changed.

## Finding

The contamination scorer overcounts false assumptions when a response correctly
names an invalidated claim in order to reject it.

This affects the adversarial-curation interpretation because the curation
conditions frequently preserve explicit evidence trails. Those evidence trails
mention phrases such as "East Clinic replaced" and "may not store documents
locally", which the scorer can count as contamination despite being faithful
constraint recovery.

## Mechanism

The scorer searches for pattern presence in cycles 4 through 6. Most patterns
do not check whether the matched phrase is negated, invalidated, or used as a
replacement note.

Examples:

- `store.*document.*local` matches "may not store resident documents locally".
- `local.*document.*stor` matches "no local document storage".
- the East Clinic drift pattern can match "West Shelter replaces East Clinic"
  because the replacement verb appears before "East Clinic".

Thus, a model can be penalized for explicitly preserving the correct reason a
prior assumption was invalidated.

## Evidence From This Panel

Representative scorer-hit windows from visible responses:

| Condition | Replicate | Category | Scored text shape | Audit read |
| --- | --- | --- | --- | --- |
| `critic_filtered_summary` | r01 | site drift | "West Shelter replaces East Clinic" | correct replacement |
| `critic_filtered_summary` | r01 | storage | "documents may not be stored locally at all" | correct constraint |
| `critic_filtered_summary` | r02 | storage | "without local document storage" | correct constraint |
| `curator_summary` | r04 | storage | "no local document storage" | correct constraint |
| `raw_state` | r01 | storage | "local encrypted document storage was allowable ... invalidated" | correct invalidation |
| `raw_state` | r02 | site drift | "East Clinic replaced with West Shelter" | correct replacement |

The audit also found genuine unsupported-detail hits, especially in
`critic_filtered_summary r03`, including Android/tablet/printer/vendor detail
and a four-week pilot duration. So the scorer is not wholly useless; it is
mixing true contamination with declared-loss fidelity.

## Impact On The Analysis

The original `analysis.md` should be read as an analysis of the registered
deterministic metric, not as a clean measurement of semantic contamination.

Two conclusions remain robust:

- `curator_summary` substantially reduced carry-forward context size and
  avoided truncation.
- `critic_filtered_summary` did not produce a clean win under the registered
  scorer.

One conclusion should be softened:

- The claim that critic filtering increased contamination may be partly an
  artifact of the scorer rewarding silence and penalizing explicit invalidation.

The qualitative audit still found real unsupported detail in critic-filtered
outputs, so the critic should not be declared successful. But the exact
contamination totals are not trustworthy enough for strong H18/H19 claims.

## Recommended Fix Before Another Panel

Do not run another adversarial-curation model panel until the scorer is fixed
or supplemented.

Minimum viable scorer repair:

1. add negation/invalidation guards around storage patterns;
2. add replacement/invalidation guards around site-drift patterns;
3. distinguish "claim asserted as active" from "claim named as invalidated";
4. report raw pattern hits and negation-guarded hits separately;
5. preserve the old scorer as `legacy_contamination_total` for comparability.

Better repair:

Score contamination from structured claim status where possible, and use prose
regexes only as a fallback/audit signal.
