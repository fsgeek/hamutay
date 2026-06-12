# Audit/Restart Boundary Readiness Analysis

Experiment ID: `audit_restart_boundary_20260612`

## Result

- Classification: `survived`
- Ready for Goal 6: `True`
- Live model calls: `False`
- Rows: `5`
- Decision: Audit/restart boundary is ready for less-scaffolded no-token or tiny-token autonomy panels.

## Rows

| Row | Passed | Key evidence |
| --- | ---: | --- |
| happy_rehearsal | True | all readiness checks passed |
| resume_after_seed_apply | True | all readiness checks passed |
| resume_after_event_claim | True | all readiness checks passed |
| rejected_operation_trace | True | rejected operations: 1 |
| tamper_detection | True | tamper detected by hash-chain verification |

## Interpretation

Audit/restart boundary is ready for less-scaffolded no-token or tiny-token autonomy panels.

The readiness rows preserve model-facing wake inputs, raw model emissions, accepted/rejected action traces, scheduler event lifecycle records, memory operations, policy dispositions, run manifests, restart frontiers, and replay reports. Tampering with the action ledger is detected by hash-chain verification.

## Artifact Trail

- `PRE_REGISTRATION.md` fixes H6 and falsification conditions.
- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.
- `rows/<row_id>/report.json` preserves replay reports for rehearsal rows.
- `rows/<row_id>/run/actions.jsonl`, `events.jsonl`, `restart_frontier.jsonl`, and `memory_snapshot.json` preserve persisted run state.
- `rows/rejected_operation_trace/action_trace.json` preserves a rejected first-pass action.
- `rows/tamper_detection/tampered_actions.jsonl` preserves the mutated ledger used for tamper detection.
