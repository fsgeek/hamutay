# Analysis: Initialization Repair Scheduler Gate

Date: 2026-06-05

## Result

The initialization repair mechanism was not exercised. All four DeepSeek
replicates produced valid durable initialization on the first pass.

- H226 initialization repair increases usable population: not supported in this
  run because no first-pass-invalid initialization occurred.
- H227 repaired initializations are auditable: not exercised because no
  initialization repair occurred.
- H228 wake outcomes remain separately classified: supported for completed
  wakes.
- H229 event-level wake validation remains consistent: supported for completed
  wakes.
- H230 bounded initialization and wake repair: supported.

## Summary

Across four replicates:

- first-pass valid initializations: 4/4;
- initialization repairs attempted: 0/4;
- initialization backend-call violations: 0;
- scheduled events persisted: 4/4;
- scheduled wakes completed: 3/4;
- completed wakes first-pass valid: 0/3;
- completed wakes repaired: 3/3;
- completed wakes with event-level `wake_validation`: 3/3;
- event/session validation agreement: 3/3;
- wake backend-call violations: 0.

Replicate 1 persisted and claimed the scheduled event, but the wake failed
before validation because the raw wake object both deleted and updated
`walk_gate_status` in the same cycle. The protocol guard rejected that object:

`deleted_regions overlaps updates: ['walk_gate_status']`

The event log marked the event failed and preserved the context result. This is
a useful protocol-failure classification, not a hidden state mutation.

## Interpretation

This run does not answer whether initialization repair can salvage failed
cycle-1 activations. The full-object initialization validator/repair setup may
have changed prompt pressure enough that all initializations succeeded first
pass, or the panel may simply have landed in a favorable stochastic pocket.

What it does show:

- cycle-1 validation can run without breaking clean initializations;
- clean initialization remains distinguishable from repaired initialization;
- downstream wake validation remains separately classified;
- event-level wake validation summaries still work after an initialization
  validation gate;
- protocol guard failures remain visible as event failures.

The repeated downstream pattern remains intact: for completed wakes, DeepSeek
again failed first-pass durable graph-evidence recording and succeeded after
full-target repair.

## Design Implication

The initialization policy question remains open. This run supports adding
cycle-1 validation as audit metadata, but it does not justify replacing culling
with repair because no repair case occurred.

The next sharper experiment should condition directly on known failed
initialization states, analogous to the earlier conditioned repair variants.
That would test whether a full-object initialization repair can recover the
common `response: "Initialized."` / framework-only durable state failure
without waiting for a live stochastic panel to produce the failure.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/init_repair_scheduler_gate_20260605/run_init_repair_scheduler_gate.py
timeout 1200s uv run python experiments/event_loop/init_repair_scheduler_gate_20260605/run_init_repair_scheduler_gate.py
```

Results:

- py_compile passed;
- live runner exited with code 0;
- four first-pass valid initializations;
- zero initialization repair attempts;
- three scheduled wakes completed;
- three completed wakes repaired successfully;
- one scheduled wake failed at protocol merge before validation.
