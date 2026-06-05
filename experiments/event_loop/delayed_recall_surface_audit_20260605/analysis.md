# Analysis: Delayed Recall Surface Audit

Date: 2026-06-05

## Result

The existing delayed-thinking panels contain the missing delayed task and
delayed recall surfaces, but they do not contain the matched identity-only
control needed for a continuity-benefit claim.

- H266 delayed goals and future events preserved: supported.
- H267 pre-due waiting and due wake execution preserved: supported.
- H268 delayed recall context delivered: supported.
- H269 successful panels remain repair-dependent: supported.
- H270 no matched identity-only control: supported.

## Panel Counts

Five panels were audited:

- `delayed_thinking_simtime_20260605`;
- `delayed_thinking_controlled_seed_20260605`;
- `delayed_thinking_contract_variant_20260605`;
- `delayed_thinking_envelope_variant_20260605`;
- `delayed_thinking_example_variant_20260605`.

The original simtime panel remains an activation-failure boundary:

- valid activation: 0/4;
- schedule valid: 0/4;
- event completed: 0/4;
- recall delivered: 0/4.

The four later panels all succeeded on scheduler substrate mechanics:

- valid activation: 16/16;
- schedule valid: 16/16;
- pre-due waiting: 16/16;
- due event completed: 16/16;
- recall requested: 16/16;
- recall delivered: 16/16;
- final state valid: 16/16.

## Repair Dependence

The successful panels still depended on repair for durable wake state:

- controlled seed: first-pass valid 0/4, repair valid 4/4;
- contract variant: first-pass valid 0/4, repair valid 4/4;
- envelope variant: first-pass valid 1/4, repair valid 3/4;
- example variant: first-pass valid 0/4, repair valid 4/4.

This matches the broader pattern: the scheduler substrate can deliver the
right wake and context, while the model often fails to commit the required
durable state on first pass.

## What This Proves

The delayed-thinking artifacts are enough to show that the event-loop
substrate can support:

1. delayed task preservation;
2. future self-scheduled events;
3. simulated-time pre-due waiting;
4. due-time wake execution;
5. delayed recall context delivery;
6. auditable repair and final valid state.

That is stronger than the strict scheduler panel for long-horizon mechanics.

## What This Does Not Prove

The artifacts do not prove event-loop continuity benefit over
identity-object-only continuity. None of the audited panels contains a matched
identity-only control arm.

The missing comparison is now precise:

- same delayed task;
- same initialization policy;
- same model and replicate budget;
- identity-object-only condition with no scheduled recall;
- event-plus-recall condition with scheduled wake and delivered recall;
- normalized result envelope or equivalent provenance fields.

## Research Consequence

We do not need another mechanics-only delayed recall panel. The substrate has
already shown the needed mechanics under controlled activation.

The next live experiment should be a matched delayed-task continuity comparison:

1. identity-object-only delayed task, no scheduled recall;
2. event-plus-recall delayed task;
3. optional repair-enabled and repair-disabled scoring layers.

The primary endpoint should be delayed task recovery and grounded use of the
deferred fact, not merely event completion.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/delayed_recall_surface_audit_20260605/run_delayed_recall_surface_audit.py
uv run python experiments/event_loop/delayed_recall_surface_audit_20260605/run_delayed_recall_surface_audit.py
jq '.summary.hypothesis_results' experiments/event_loop/delayed_recall_surface_audit_20260605/delayed_recall_surface_audit.json
```

The audit exited successfully and wrote:

`experiments/event_loop/delayed_recall_surface_audit_20260605/delayed_recall_surface_audit.json`
