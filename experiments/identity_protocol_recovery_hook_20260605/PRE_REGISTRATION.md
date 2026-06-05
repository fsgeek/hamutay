# Identity Protocol Recovery Hook Pre-Registration

Filed: 2026-06-05 after `identity_merge_repair_artifact_20260605` and before
adding a protocol-recovery hook to `OpenTasteSession`.

## Research Question

Can `OpenTasteSession` attach protocol-recovery artifacts to strict
merge-failure records without accepting failed content into working state?

The prior repair-artifact slice showed that failed merge payloads can yield
useful candidate continuity rows and contamination warnings. The next substrate
step is to give the session harness a first-class side channel for such
artifacts, invoked only after strict merge failure capture.

## Hypotheses

### H59: Recovery Hook Runs On Merge Failure

If a protocol-recovery builder is configured, a strict merge failure should
invoke it with prior state, raw output, visible response, record ID, timestamp,
and failure classification.

Prediction: a deterministic fake backend producing delete-plus-update overlap
will log a failed cycle record containing
`protocol_recovery.status: "success"`.

### H60: Recovery Hook Does Not Accept State

If the hook is observability-only, it must not mutate session state, advance
prior states, commit scheduled events, run continuity curation, or suppress the
merge exception.

Prediction: after the failed exchange, `exchange()` still raises, `session`
cycle rolls back, working state is unchanged, and the next successful exchange
uses the same cycle number.

### H61: Recovery Hook Failure Is Data

If the recovery builder itself fails, that failure should be logged as a
`protocol_recovery.status: "failed"` artifact while the original merge
exception remains the exchange failure.

Prediction: a deterministic failing builder logs its own error type and
message, and `exchange()` still raises the original strict merge error.

## Registered Validation

No model calls are registered.

Use fake backends and fake recovery builders:

- successful recovery builder;
- failing recovery builder;
- existing successful-cycle tests as regression.

## Primary Measures

- failed cycle record contains `protocol_recovery`;
- successful recovery artifact includes source cycle and source record ID;
- failing recovery artifact includes error type and error message;
- failed cycle does not mutate accepted state;
- failed cycle does not run continuity curation;
- successful cycles remain unchanged when no merge failure occurs.

## Falsification Criteria

H59 is weakened if the hook is not invoked or the artifact is not logged.

H60 is weakened if failed content enters accepted state, cycle rollback breaks,
or the strict exception is swallowed.

H61 is weakened if recovery-builder failure masks the original merge error or
disappears silently.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not add a default live normalizer.
- Do not call a model.
- Do not run the continuity curator after failed merge.
- Do not commit scheduled events after failed merge.
- Preserve successful-cycle log shape except for constructor/API additions.

## Interpretation Guardrails

This hook does not decide which repair artifacts are true. It only provides a
durable side channel for candidate repair data. Adjudication and state
admission remain separate future steps.
