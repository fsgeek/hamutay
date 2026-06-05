# Pre-Registration: Delayed Recall Surface Audit

Date: 2026-06-05

## Research Question

Do the existing delayed-thinking panels already contain the task-goal and
delayed-recall surfaces missing from the strict scheduler panel, and are they
adequate for testing event-loop continuity benefit claims?

The continuity substrate measurement audit found that the strict scheduler
panel was well-instrumented for local continuity but lacked delayed task goals
and delayed recall. Existing delayed-thinking experiments appear to target
those missing surfaces. This audit determines what they already prove and what
comparison remains missing.

## Hypotheses

- H266: Existing delayed-thinking panels preserve explicit delayed task goals
  and future scheduled events.
- H267: Successful delayed-thinking panels preserve pre-due waiting behavior
  and due-time wake execution under simulated time.
- H268: Successful delayed-thinking panels preserve delayed recall context
  delivery at wake time.
- H269: Successful delayed-thinking panels still depend on bounded repair for
  valid durable wake state.
- H270: Existing delayed-thinking panels are not sufficient to claim event-loop
  continuity benefit over identity-object-only continuity because they lack a
  matched identity-only control arm.

## Method

Run a deterministic local audit over these artifacts:

- `delayed_thinking_simtime_20260605`;
- `delayed_thinking_controlled_seed_20260605`;
- `delayed_thinking_contract_variant_20260605`;
- `delayed_thinking_envelope_variant_20260605`;
- `delayed_thinking_example_variant_20260605`.

For each panel:

- read `results.json`;
- inspect row-level fields;
- inspect event sidecars when present;
- classify activation, scheduling, pre-due waiting, due wake, delayed recall,
  first-pass validity, repair dependence, and final validity;
- report whether the panel has an identity-object-only control arm.

No model calls are permitted. No source artifacts are modified.

## Predictions

The controlled-seed and prompt-variant panels should show:

- valid activation;
- successful future event scheduling;
- pre-due waiting;
- due event completion;
- delayed recall context delivery;
- final valid state after repair.

They should not show reliable first-pass durable state use. They also should
not support a direct continuity-benefit claim because they lack a matched
identity-only delayed-task condition.

The original simtime panel should remain an activation-failure boundary.

## Falsification Criteria

- H266 is falsified if no delayed-thinking panel preserves delayed task goals
  or scheduled future events.
- H267 is falsified if successful panels lack pre-due waiting or due wake
  evidence.
- H268 is falsified if successful panels lack delivered recall context.
- H269 is falsified if successful panels are mostly first-pass valid and do not
  require repair.
- H270 is falsified if the existing delayed-thinking artifacts already include
  a matched identity-object-only control condition.

## Analysis Plan

Report:

- panel-level activation, scheduling, waiting, wake, recall, first-pass, repair,
  and final-valid counts;
- event-sidecar recall-context evidence;
- prompt-variant comparisons;
- whether any panel contains a matched identity-only control arm;
- recommended next experiment if the control arm is absent.

Interpretation will distinguish scheduler substrate function from demonstrated
continuity benefit.
