# Audit/Restart Boundary Readiness Preregistration

Experiment ID: `audit_restart_boundary_20260612`

Date: 2026-06-12

Roadmap goal: Goal 5 of
`docs/event-loop-research-program-goals-20260612.md`.

## Research Question

Is the current event-loop autonomy harness sufficiently observable and
restartable to support less-scaffolded bounded-autonomy experiments without
losing model actions, operation outcomes, scheduler events, memory operations,
policy dispositions, run manifests, or restart frontiers?

## Hypothesis

H6: The audit/restart boundary is ready for Goal 6 if a no-token rehearsal can
be reconstructed from persisted artifacts, interruption/resume behavior returns
to clean frontiers, hash-chain verification detects tampering, and replay
reports answer the required audit questions without inference.

## Rows

1. `happy_rehearsal`: run the no-token model-authored seed/schedule/closure
   rehearsal to completion.
2. `resume_after_seed_apply`: interrupt after seed action application but before
   frontier commit, then resume.
3. `resume_after_event_claim`: interrupt after claiming a scheduled event, then
   resume and recover the event to pending.
4. `rejected_operation_trace`: preserve a model-authored invalid continuation
   action and verify rejected validation operations remain in the ledger.
5. `tamper_detection`: modify a ledger record after write and verify the hash
   chain fails.

## Required Evidence

The readiness analysis must confirm:

- run manifests are present;
- model-facing wake inputs are logged;
- raw model emissions are logged;
- accepted and rejected actions are reconstructable;
- scheduler event lifecycle is logged;
- memory operations are logged;
- policy dispositions are logged;
- restart frontiers are committed and loadable;
- interruption/resume either suppresses uncommitted events or recovers running
  events correctly;
- tampering breaks ledger verification;
- replay reports expose the failure taxonomy layers needed for later model,
  protocol, harness, substrate, provider, scorer, and restart-boundary
  attribution.

## Falsification Conditions

H6 is falsified if any required artifact is missing, a completed no-token run
cannot be reconstructed, ledger verification fails on an untampered run,
tampering is not detected, interruption advances state past the last committed
frontier, or replay reports cannot distinguish accepted/rejected operations and
failure-layer attribution.

The result is boundary/inconclusive if the harness passes happy-path
reconstruction but a resume or rejected-operation row is not reconstructable.

No live model calls are permitted in this readiness validation.

