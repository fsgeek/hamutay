# Suppression Source DES Pre-registration

Date: 2026-06-05

## Research Question

Can policy-suppressed event records identify the policy decision source strongly
enough to audit why pending work was not run?

## Motivation

The pending-disposition DES experiment showed that the scheduler can mark
pending continuations as `suppressed` after terminal policy classifications.
The records include policy name and reason, but the source coordinate is still
thin. A future audit should be able to answer:

- which wake or policy evaluation caused suppression?
- what terminal classification was applied?
- can the source record be found in the session JSONL?

## Hypotheses

### H85: suppressed events carry policy source coordinates

Suppressed records can include `suppressed_by_cycle`,
`suppressed_by_record_id`, and `suppressed_by_classification`.

Falsification: any suppressed record lacks these fields when the caller supplies
them.

### H86: suppression source record is resolvable

For each suppressed event, `suppressed_by_record_id` resolves to a record in the
scenario session JSONL.

Falsification: a suppressed event references a missing or malformed record id.

### H87: source-linked suppression remains lifecycle-clean

Adding source coordinates does not create lifecycle anomalies or make
suppressed events runnable.

Falsification: the event summary reports lifecycle anomalies or pending latest
events after source-linked suppression.

## Conditions

Use deterministic simulated time and the bounded autonomy scenario shapes:

- `stasis_cutoff`
- `recursive_drift`

After terminal classification, suppress remaining pending events using source
coordinates from the last wake record that caused the classification.

## Primary Measures

- `suppressed_count`
- `suppressed_with_source_count`
- `source_records_resolved`
- `pending_after_suppression`
- `lifecycle_anomaly_count`
- `suppressed_by_classifications`

## Expected Results

- Every suppressed event includes source cycle, source record id, and
  classification.
- Every suppressed event source record resolves in the session JSONL.
- No pending latest events remain.
- No lifecycle anomalies are introduced.
