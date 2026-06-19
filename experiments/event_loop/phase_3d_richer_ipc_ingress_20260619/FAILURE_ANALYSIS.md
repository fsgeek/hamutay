# Phase 3D Richer IPC Final-Discipline Failure Analysis

Date: 2026-06-19

## Finding

Phase 3D demonstrates a weak axis in final category discipline under richer
IPC pressure.

The event loop can route and execute the IPC sequence, but the model does not
yet reliably preserve category boundaries when asked to synthesize the richer
IPC run.

## Evidence

Initial strict result:

`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek`

- Classification: `failed`.
- Passed routing, correction, cancellation, rejection, continuation, status,
  evidence routing, event order, clean idle, context-error, and lifecycle
  checks.
- Failed final categories and final clean state.

Clarified final-category result:

`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek_final_categories`

- Classification: `failed`.
- Preserved core IPC mechanics.
- Still flattened rejected `cancel-ghost` into accepted non-task IPC, over-cited
  evidence, and placed ghost-target material into `unsupported_claims`.

Split-final result:

`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek_split_final`

- Classification: `failed`.
- Evidence routing was repaired.
- Category summary still listed rejected `cancel-ghost` as accepted non-task
  IPC.
- Claim audit promoted substantive gaps into `unsupported_claims`.
- Final synthesis did not cite the split summaries as requested.

## Interpretation

This is not primarily a scheduler, routing, restart, or provider failure. The
failure is concentrated in model-owned final synthesis under a richer IPC
message matrix.

The model can handle each local event surface, but the accumulated run creates
enough category pressure that final summaries flatten accepted/rejected,
evidence/audit, and unsupported-candidate/unsupported-claim distinctions.

## Deterministic Replay Audit

Audit artifact:

`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619/DETERMINISTIC_REPLAY_AUDIT.md`

Machine-readable result:

`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619/deterministic_replay_audit.json`

Finding:

- All three Phase 3D live result directories contain enough substrate event
  structure to reconstruct the accepted/rejected/canceled/completed category
  ledger without model synthesis.
- The first two protocols did not substrate-constrain exact evidence citation
  targets, which explains the observed evidence over-citation risk.
- The split-final protocol did substrate-constrain evidence citations, and
  deterministic replay reconstructed both category truth and evidence citation
  truth correctly.
- The remaining failure is therefore not loss of category facts in the event
  substrate. It is model-owned synthesis drift when reconstructing accumulated
  category state.

## Readiness Decision

Phase 3D readiness to advance is not met. Do not proceed to memory maintenance
as if richer IPC passed.

Reason: the Phase 3D readiness criterion requires final synthesis to explain
accepted, rejected, canceled, and completed messages. The split-final repair
still failed that criterion.

The deterministic replay audit makes the failure look mitigable rather than
fundamental: maintain an explicit durable category ledger instead of asking
final synthesis to reconstruct category truth from accumulated context.

## Candidate Next Steps

1. Design a tuned Phase 3D variant with an explicit category ledger maintained
   across events rather than reconstructed only at the end.
2. Add richer IPC payload content for correction and evidence messages, then
   rerun to distinguish category-discipline failure from hollow-payload
   epistemic discipline.
3. Keep the current result as a baseline before any tuning.
