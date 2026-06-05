# Pending Disposition DES Pre-registration

Date: 2026-06-05

## Research Question

When a bounded autonomy loop reaches a terminal policy classification before
all scheduled continuations have run, can the scheduler explicitly dispose of
the remaining pending events without confusing suppression with failure or
expiry?

## Motivation

The bounded autonomy DES experiment showed that the policy runner can classify:

- `complete`
- `stasis`
- `drift`
- `failed`

It also showed that terminal policy classifications can leave pending
continuations in the sidecar. That is observable, but it means the scheduler has
not taken ownership of work it chose not to run.

## Hypotheses

### H81: policy suppression is a distinct terminal event status

The event sidecar can represent policy-disposed pending work with
`status == "suppressed"`, distinct from `failed` and `expired`.

Falsification: suppressed events appear as failed/expired/pending in the latest
event summary.

### H82: stasis suppression drains pending continuations

After a `stasis` classification, all pending continuations for the scenario are
marked `suppressed` with a stasis reason.

Falsification: the stasis scenario still has latest pending events after policy
suppression, or suppressed records lack the policy/reason fields.

### H83: drift suppression drains forked continuations

After a `drift` classification caused by multiple same-cycle continuations, all
pending branch continuations are marked `suppressed` with a drift reason.

Falsification: the drift scenario still has latest pending events after policy
suppression, or fewer suppressed events are recorded than pending branches.

### H84: suppression is lifecycle-clean

Suppressed histories should not trigger lifecycle anomalies merely because a
pending event became suppressed without a running record.

Falsification: suppressed event histories are reported as lifecycle anomalies
under the normal event summary.

## Conditions

Use deterministic fake backends and simulated time. Reuse the bounded autonomy
scenario shapes:

- `stasis_cutoff`: two no-progress wakes leave one pending continuation.
- `recursive_drift`: one wake schedules two pending branch continuations.

After classification, call the new policy disposition primitive to suppress
remaining pending events.

## Primary Measures

- `classification`
- `pending_before_suppression`
- `suppressed_count`
- `pending_after_suppression`
- `status_counts`
- `suppression_reasons`
- `lifecycle_anomaly_count`

## Expected Results

- `stasis_cutoff` suppresses exactly 1 pending continuation.
- `recursive_drift` suppresses exactly 2 pending continuations.
- Latest status counts contain `suppressed` and no remaining `pending`.
- Suppressed events have `suppressed_at`, `suppressed_by_policy`, and
  `suppression_reason`.
- Suppressed events do not introduce lifecycle anomalies.

If this passes, terminal policy ownership should become part of the scheduler
loop contract before returning to live provider experiments.
