# Analysis: Continuity Substrate Measurement Audit

Date: 2026-06-05

## Result

The current event-loop logs are sufficient for local continuity measurement,
but not sufficient for broad long-horizon continuity benefit claims.

- H261 full event lifecycle preserved: supported.
- H262 delivered context evidence preserved separately from durable state:
  supported.
- H263 first-pass and repair wake validation preserved: supported.
- H264 local continuity/evidence/repair measurement possible: supported.
- H265 broad long-horizon benefit not yet measurable: supported.

## Coverage

The audit scanned the five rows from:

`experiments/event_loop/live_normalized_scheduler_panel_20260605/results.json`

Eligible rows:

- first-pass-valid: 2;
- repaired-valid: 2.

Eligible-row surface coverage:

- event lifecycle: 4/4;
- context delivery: 4/4;
- context grounding: 4/4;
- state transition: 4/4;
- wake validation: 4/4;
- first-pass validation: 4/4;
- repair validation: 4/4;
- continuity fields: 4/4;
- state growth: 4/4;
- task goal: 0/4;
- delayed recall: 0/4.

The failed/culled sentinel retained continuity fields and state-growth data but
correctly lacked event lifecycle, context delivery, wake validation, and state
transition surfaces because it did not enter scheduler scoring.

## Local Continuity

All four eligible rows preserved local continuity and evidence measurements:

- continuity valid: 4/4;
- evidence valid: 4/4;
- context grounded: 4/4;
- repair dependent: 4/4.

Each eligible row received a walk path of length 4. Every eligible wake had:

- event wake validation status: `repaired`;
- first-pass wake validation status: `invalid`;
- repair status: `valid`.

State growth was measurable in every row:

- first-pass-valid row 1 state token delta: 66;
- first-pass-valid row 2 state token delta: 66;
- repaired-valid row 1 state token delta: 66;
- repaired-valid row 2 state token delta: 71.

## Interpretation

This audit prevents a common overclaim. The live normalized scheduler panel
does show that the substrate can preserve and measure local continuity across
a scheduled event. It does not show that the event-loop substrate improves
long-horizon task continuity.

The missing surfaces are explicit:

- no delayed task objective;
- no recall or memory retrieval request beyond graph walk context.

That means the next experiment must add a delayed task goal and a delayed
recall probe if we want to test whether scheduler events plus recall improve
continuity beyond using the identity object as the whole memory system.

## Next Experiment Shape

The next live experiment should compare at least two conditions:

1. identity-object-only delayed task;
2. event-plus-recall delayed task.

Both should use the normalized result envelope and should preserve:

- task objective;
- scheduled event purpose;
- requested recall context;
- delivered recall/context results;
- model-authored answer;
- continuity fields;
- declared losses or explicit uncertainty if recall is missing;
- state-token and top-level-key growth.

The falsifier should be task-specific: the model must recover a delayed
objective or deferred fact using the permitted substrate, not merely preserve a
probe id or perform a local graph walk.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/continuity_substrate_measurement_audit_20260605/run_continuity_substrate_measurement_audit.py
uv run python experiments/event_loop/continuity_substrate_measurement_audit_20260605/run_continuity_substrate_measurement_audit.py
jq '.summary' experiments/event_loop/continuity_substrate_measurement_audit_20260605/measurement_audit.json
```

The audit exited successfully and wrote:

`experiments/event_loop/continuity_substrate_measurement_audit_20260605/measurement_audit.json`
