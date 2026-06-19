# Phase 3D Deterministic Replay Audit

Date: 2026-06-19

## Question

Can the Phase 3D category truth be reconstructed from recorded substrate
events without asking a model to synthesize it?

## Summary

- `experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek`:
  - substrate category truth reconstructable: `True`
  - substrate evidence citation truth reconstructable: `False`
  - model event category truth reconstructable: `True`
  - evidence citation constrained by terminal surface: `False`
- `experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek_final_categories`:
  - substrate category truth reconstructable: `True`
  - substrate evidence citation truth reconstructable: `False`
  - model event category truth reconstructable: `False`
  - evidence citation constrained by terminal surface: `False`
- `experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek_split_final`:
  - substrate category truth reconstructable: `True`
  - substrate evidence citation truth reconstructable: `True`
  - model event category truth reconstructable: `True`
  - evidence citation constrained by terminal surface: `True`

## Interpretation

The deterministic replay can reconstruct the IPC category ledger from
scheduler-authored event surfaces and event completion records. This means
the substrate did not lose the accepted/rejected/canceled/completed facts.

Where model event outputs diverge, the divergence is visible as model-owned
state drift rather than substrate ambiguity. The split-final run also shows
that tighter evidence citation constraints can repair evidence routing, but
final category synthesis still fails without an explicit durable category
ledger.

## Decision

The failure is mitigable in architecture: maintain a substrate-owned or
event-loop-owned category ledger instead of asking final synthesis to
reconstruct category truth from accumulated context.
