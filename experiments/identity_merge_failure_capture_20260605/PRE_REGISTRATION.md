# Identity Merge Failure Capture Pre-Registration

Filed: 2026-06-05 after `identity_typed_guardrail_delta_20260605` showed five
strict merge failures and before changing merge-failure logging code.

## Research Question

Can the taste_open substrate preserve analyzable raw model output on strict
state-merge failure without changing merge semantics?

The current strict merge rule rejects any cycle where a key appears in both
`deleted_regions` and same-cycle updates. Recent panels show this is a
recurring failure mode. However, the current session path raises before
writing the cycle JSONL record, so the raw output that caused the failure is
not preserved. That prevents later replay, adjudication, or preregistered
normalizer experiments from using the actual failed payload.

This experiment is an observability/instrumentation slice, not a leniency
change.

## Hypotheses

### H49: Merge Failures Can Be Captured Without Accepting Them

If the failure occurs after a complete backend response and before state merge,
the harness should be able to write a diagnostic JSONL record and still raise
the same exception.

Prediction: a delete-plus-update overlap produces a durable log record with
raw output, prior state, usage, failure classification, and merge error, while
`exchange()` still raises.

### H50: Failure Capture Does Not Advance Durable State

If capture is observability-only, failed cycles must not mutate working state,
append prior states, persist bridge records, commit scheduled events, or run
continuity curation.

Prediction: after a captured merge failure, the next successful exchange uses
the same cycle number and prior state as before the failed cycle.

### H51: Successful Cycle Logs Are Unchanged

If the instrumentation is scoped to merge failure, existing successful-cycle
records should remain structurally compatible with current logs.

Prediction: existing taste_open, exchange-tool, event, and continuity curator
tests continue to pass.

## Conditions

No model panel is registered for this slice.

Implementation and validation use deterministic fake backends:

- `strict_overlap_failure`: fake backend returns a raw output with
  `deleted_regions` overlapping a top-level update.
- `success_after_failure`: fake backend then returns a valid update.
- existing successful-cycle tests provide regression coverage for unchanged
  behavior.

## Primary Measures

Failure record:

- record is appended to JSONL;
- `record_type` or status field identifies a merge failure;
- raw output is preserved exactly enough to inspect overlap;
- prior state is preserved;
- usage is preserved;
- failure classification contains error type, message, and overlap keys.

State/cycle behavior:

- `exchange()` raises on the failed cycle;
- session cycle rolls back through existing `exchange()` rollback;
- next success uses the same cycle number;
- prior state is not changed by the failed raw output;
- no continuity curation record is produced for the failed cycle;
- no scheduled event is committed for the failed cycle.

## Falsification Criteria

H49 is weakened if the failed raw output is still absent from JSONL or if the
error is swallowed.

H50 is weakened if failed output mutates state, advances `_prior_states`, or
causes the next successful exchange to skip a cycle.

H51 is weakened if existing successful-cycle tests fail or successful log
record shape changes unnecessarily.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not normalize delete-plus-update overlaps.
- Do not run continuity curation on failed merges.
- Do not append bridge records, prior states, or scheduled events on failed
  merges.
- Preserve raw output and usage in a failure record before re-raising.
- Keep the code path small enough to support future replay/normalizer
  experiments.

## Interpretation Guardrails

This slice does not answer whether update-wins or delete-then-update is the
right merge policy. It only makes the failed payload observable. If capture
works, the next protocol experiment can use real failed raw outputs rather
than inferring from exception messages.
