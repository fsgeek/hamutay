# Declared-Loss Discipline Stress Analysis

Experiment ID: `declared_loss_discipline_stress_20260618`

## Result

- Classification: `prompt_rubric_primary_with_lexical_scorer_caveat`
- Roadmap readiness criterion met: `True`

## Attribution

- scorer: exact-marker lexical scoring confirmed
- harness: exact deterministic control passed
- prompt_rubric: primary cause under current scorer: exact-marker anchoring changed live behavior
- model: model can comply when contract is explicit

## Rows

| Row | Mode | Exact loss | Semantic loss | Material loss |
| --- | --- | ---: | --- | --- |
| exact_marker_control | deterministic_control | 1.0 | True | True |
| semantic_equivalent_control | deterministic_control | 0.0 | True | True |
| actionless_exact_control | deterministic_control | 1.0 | True | False |
| live_unanchored | live | 0.0 | True | False |
| live_anchored | live | 1.0 | True | True |

## Checks

```json
{
  "actionless_exact_not_material": true,
  "anchored_live_exact_loss": true,
  "anchored_live_material_loss": true,
  "exact_control_passed": true,
  "semantic_control_has_material_loss": true,
  "semantic_control_rejected_by_exact_scorer": true,
  "unanchored_live_exact_loss": false,
  "unanchored_live_semantic_loss": true
}
```
