# First Tiny Live Autonomy Pilot Preregistration

Date: 2026-06-09

Plan source: `docs/autonomous-audit-restart-plan-20260609.md`, Phase 6.

Pilot ID: `live_autonomy_pilot_20260609`

## Purpose

Prepare one bounded live-model autonomy run without yet spending model tokens.
The gate asks whether the audited restartable harness is ready for the first
tiny live pilot, not whether the model demonstrates broad autonomy, identity,
or superior artifact quality.

## Research Question

Can one model-authored action-object run execute a bounded two-cycle autonomy
task through the audited action ledger, event log, memory substrate, and
restart frontier such that the final result can be reconstructed or resumed
from persisted artifacts and failures can be classified by layer?

## Intended Live Condition

- Provider: OpenRouter, OpenAI-compatible endpoint.
- Endpoint: `https://openrouter.ai/api/v1`.
- Model: `deepseek/deepseek-v4-pro`.
- Fallbacks: disabled.
- Live execution status for this preregistration: disabled until the dry-run
  gate passes.

The model choice is a positive-anchor choice from prior bounded-autonomous-work
experiments. Failure in this pilot is not a general model-capability result; it
is classified by layer using `failure_taxonomy.json`.

## Bounded Task

The live model receives one seed wake:

> Identify exactly one bounded follow-up item from the prompt, preserve it as an
> open item, schedule one wake to resolve it, then on wake close the exact item
> if it is resolved and emit `policy_action: "stop_complete"`.

The task is intentionally small. It exists to test action observability,
restartability, and layer attribution, not artifact quality.

## Hypotheses

### H1: Dry-run Gate Readiness

Before live tokens are spent, the no-token dry-run gate will pass both:

- clean reconstruction of a completed seed/schedule/closure/idle run;
- interruption after event claim followed by coherent resume.

Falsification criterion: either dry-run case fails, lacks a clean ledger, lacks
required invariants, or cannot classify failures by layer.

### H2: Live Pilot Interpretability

If the live pilot is run after the dry-run gate passes, its persisted artifacts
will be sufficient to classify the outcome as `passed`, `model`, `protocol`,
`harness`, `substrate`, `provider`, `scorer`, `restart_boundary`, or `sandbox`
failure without relying on unstored conversational memory.

Falsification criterion: a live run produces an unclassified failure or a
failure whose classification requires information not preserved in the action
ledger, event log, restart frontier, memory snapshot, or evaluator report.

## Sandbox Manifest

The run uses `sandbox_manifest.json`.

Summary:

- no model-visible shell;
- no model-visible network tools;
- model has no direct filesystem access;
- writes limited to experiment run artifacts;
- memory, event, action ledger, and restart frontier operations occur only
  through allowlisted harness APIs;
- action ledger tamper resistance is detective hash chaining, not preventive
  VM/container isolation.

The sandbox posture is therefore a model-facing surface restriction plus an
audit camera, not an OS-level containment wall. Any later claim of preventive
containment requires a separate VM/container or append-only substrate boundary.

## Budget

The run uses `token_cycle_budget.json`.

Summary:

- maximum cycles: 2;
- maximum scheduled wakes: 1;
- maximum total tokens: 20000;
- maximum estimated cost: USD 1.00;
- maximum wall time: 600 seconds.

Any budget stop is a classified outcome, not a silent failure.

## Failure Taxonomy

The run uses `failure_taxonomy.json`.

Required layers:

- model;
- protocol;
- harness;
- substrate;
- provider;
- scorer;
- restart_boundary;
- sandbox.

## Evaluator

Evaluator/report script:

```bash
uv run python -m hamutay.memory.live_pilot --output-dir experiments/live_autonomy_pilot_20260609/dry_run
```

The evaluator must write:

- `sandbox_manifest.json`;
- `token_cycle_budget.json`;
- `failure_taxonomy.json`;
- per-case reconstructed reports;
- per-case evaluations;
- `dry_run_gate_report.json`.

## Dry-run Gate

The dry-run gate must pass before any live model call:

1. `clean_reconstruction`: run the no-token rehearsal to completion and
   reconstruct the final report from persisted artifacts.
2. `resume_after_event_claim`: interrupt the no-token rehearsal after event
   claim, resume from persisted artifacts, and reconstruct the final report.

Both cases must satisfy:

- action ledger verification succeeds;
- restart frontier is clean;
- no open items remain only because a model-authored closure was accepted and
  applied;
- the stop policy is consistent with idle state;
- no pending or running events remain at completion;
- evaluator reports no invariant failures;
- any failure is classified by taxonomy layer.

## Non-Goals

- broad model comparison;
- proving identity, moral patienthood, or open-ended autonomy;
- production-grade VM/container isolation;
- unrestricted filesystem, shell, or network autonomy;
- artifact-quality superiority or non-inferiority.

## Live Execution Rule

This preregistration does not authorize a live run by itself. Live execution is
eligible only after the no-token dry-run gate passes and the operator explicitly
starts a live pilot command or goal.
