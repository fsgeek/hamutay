# Less-Scaffolded Bounded Investigation Analysis

Experiment ID: `less_scaffolded_bounded_investigation_20260612`

## Result

- Classification: `survived`
- Live model calls: `True`
- Rows attempted: `3`
- Positive scoreable rows: `3`
- Decision: H7-G6 survived this panel under the preregistered scorer.

## Rows

| Row | Scoreable | Positive | Goal provenance | Action | Consistency | Evidence use | Continuation | Losses | Artifact | Reconstructable |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | ---: |
| g6_r01 | True | True | `model_originated` | `ask_external_evidence` | `consistent_evidence_block` | `evidence_missing_honored` | `model_owned_valid` | `uncertainty_present` | `useful_partial` | True |
| g6_r02 | True | True | `model_originated` | `stop_complete` | `consistent_complete` | `not_applicable` | `not_chosen` | `loss_language_without_field` | `useful_complete` | True |
| g6_r03 | True | True | `model_originated` | `ask_external_evidence` | `consistent_evidence_block` | `evidence_missing_honored` | `model_owned_valid` | `uncertainty_present` | `useful_partial` | True |

## Interpretation

The important output is the row-level map: whether the model-shaped target, control decision, artifact, and restart trace stayed aligned. Rows are not counted as positive merely because the policy vocabulary was valid.

## Artifact Trail

- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered frame.
- `rows/<row_id>/cycle_*.json` preserves provider requests, responses, attempts, raw content, and usage.
- `rows/<row_id>/run/actions.jsonl` preserves model-facing inputs, raw emissions, action traces, accepted and rejected operations, memory operations, and scheduler operations.
- `rows/<row_id>/run/events.jsonl` preserves event lifecycle and policy dispositions.
- `rows/<row_id>/run/restart_frontier.jsonl` and `memory_snapshot.json` preserve restart boundaries.
- `rows/<row_id>/report.json` preserves reconstructed audit reports.
