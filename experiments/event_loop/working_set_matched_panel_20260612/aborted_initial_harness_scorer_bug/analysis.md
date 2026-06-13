# Working-Set Matched Panel Analysis

Experiment ID: `working_set_matched_panel_20260612`

## Result

- Classification: `falsified`
- Working-set relation: `worse`
- Artifact-quality relation: `non_inferior`
- Token relation to direct: `less_than_direct`
- Decision: Event-loop working-set behavior did not meet the preregistered matched-panel threshold.

## Rows

| Condition | Working-set score | Artifact quality | Recovery | Contamination | Declared losses | Peak prompt tokens | Total prompt tokens | Artifact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| event_loop_model_controlled | 0.2750 | 0.4000 | 0.0000 | 0.0000 | 0.0000 | 771 | 1309 | `partial` |
| harness_selected_summary | 0.4750 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 520 | 520 | `partial` |
| direct_one_shot | 0.4750 | 0.5000 | 0.0000 | 0.0000 | 1.0000 | 1569 | 1569 | `partial` |

## Interpretation

Working-set benefit is scored separately from artifact quality. The working-set score combines evidence recovery, contamination avoidance, declared-loss preservation, and provenance. Artifact quality separately scores responsiveness, supported claims, and readiness conclusion quality.

## Artifact Trail

- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered frame.
- `rows/<condition>/cycle_*.json` preserves raw provider requests and responses.
- `rows/<condition>/context_accounting.json` preserves context accounting, recall provenance, declared losses, and token use.
- `rows/<condition>/row_result.json` preserves recovery, contamination, artifact usefulness, and working-set scoring.
- `results.json` preserves the cross-condition comparison.
