# Suppression Source DES Analysis

Date: 2026-06-05

## Result

All three preregistered hypotheses passed.

- H85 suppressed events carry policy source coordinates: passed.
- H86 suppression source record is resolvable: passed.
- H87 source-linked suppression remains lifecycle-clean: passed.

## Implementation Result

`EventStore.suppress_pending(...)` now accepts optional source coordinates:

- `suppressed_by_cycle`
- `suppressed_by_record_id`
- `suppressed_by_classification`

These are written onto each suppressed event record and propagated through
`summarize_event_log`.

## Scenario Results

### stasis_cutoff

The loop classified stasis after wake cycle 3. The remaining pending
continuation was suppressed with:

- `suppressed_by_cycle: 3`
- `suppressed_by_record_id` pointing to the cycle-3 wake record
- `suppressed_by_classification: "stasis"`
- `suppression_reason: "stasis cutoff"`

The source record id resolved in the session JSONL. No pending events remained
and no lifecycle anomalies were introduced.

### recursive_drift

The loop classified drift after wake cycle 2. Both pending branch continuations
were suppressed with:

- `suppressed_by_cycle: 2`
- `suppressed_by_record_id` pointing to the cycle-2 wake record
- `suppressed_by_classification: "drift"`
- `suppression_reason: "recursive scheduling drift"`

Both source references resolved in the session JSONL. No pending events remained
and no lifecycle anomalies were introduced.

## Interpretation

The scheduler can now own terminal policy decisions at the event-log level. A
pending continuation can be left as runnable work, failed because execution was
attempted and failed, expired because time invalidated it, or suppressed because
policy chose not to run it. Suppression is now auditable back to the wake that
caused the policy decision.

The remaining high-value questions are no longer about basic queue semantics.
They are about richer control-loop policy:

1. Whether branch/fork should be an explicit mode rather than drift.
2. Whether progress should be scored by deterministic field deltas, curator
   judgment, self-declaration, or a hybrid.
3. Whether live provider calls can be supervised strongly enough that runtime
   stalls become bounded failures rather than open-ended hangs.

## Recommendation

The simulated event-loop substrate is now strong enough to support a fork/join
design experiment. That should remain simulated first. Live-provider work should
wait until we add subprocess-level supervision for model calls.
