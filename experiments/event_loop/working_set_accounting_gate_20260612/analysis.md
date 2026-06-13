# Working-Set Accounting Gate Analysis

Experiment ID: `working_set_accounting_gate_20260612`

## Result

- Classification: `survived`
- Ready for Goal 8: `True`
- Live model calls: `False`
- Recovery rate: `0.6666666666666666`
- Contamination rate: `0.0`
- Decision: Working-set accounting gate is ready for the matched panel.

## Request Classification Counts

| Classification | Count |
| --- | ---: |
| `answerable_by_substrate` | 2 |
| `malformed_or_underspecified` | 1 |
| `structurally_impossible` | 1 |
| `unavailable_but_well_formed` | 1 |

## Interpretation

The gate survived as an accounting readiness result, not as an artifact-quality claim. The dry run distinguished live context, carried state, recalled context, omitted context, declared losses, and unavailable evidence. It also separated malformed request shape, substrate coverage, and recall-protocol limitations from model-behavior findings.

The bounded local substitute was sufficient for this gate because it preserves recall provenance and truncation metadata. Its limitations remain explicit: no Yanantin adapter, no semantic find surface, and no cycle-to-record recall map.

## Artifact Trail

- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the frame.
- `working_set_accounting.json` preserves the accounting object, bounded corpus, request classifications, retrieval log, token counts, and metrics.
- `results.json` preserves deterministic checks and readiness decision.
- `analysis.md` separates model behavior from substrate, recall-protocol, prompt/schema, scorer, and inconclusive layers.
