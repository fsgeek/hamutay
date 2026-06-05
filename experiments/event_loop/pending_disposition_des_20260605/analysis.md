# Pending Disposition DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed.

- H81 policy suppression is a distinct terminal event status: passed.
- H82 stasis suppression drains pending continuations: passed.
- H83 drift suppression drains forked continuations: passed.
- H84 suppression is lifecycle-clean: passed.

The event sidecar can now distinguish policy-disposed work from both failed work
and expired work.

## Implementation Result

`EventStore.suppress_pending(...)` was added as a first-class policy primitive.
It appends `status: "suppressed"` records for all events whose latest status is
currently `pending`.

Suppressed records include:

- `suppressed_at`
- `suppressed_by_policy`
- `suppression_reason`
- optional `suppressed_by_record_id`

`suppressed` is now a terminal lifecycle status. The event summary and human
report both surface suppressed events.

## Scenario Results

### stasis_cutoff

Before suppression, the bounded loop left one pending continuation after
classifying stasis. After suppression:

- completed: 2
- suppressed: 1
- pending: 0
- lifecycle anomalies: 0
- suppression reason: `stasis cutoff`

This means the loop can now stop due to no-progress policy and take explicit
ownership of the continuation it chose not to run.

### recursive_drift

Before suppression, the bounded loop left two pending branch continuations after
classifying recursive scheduling drift. After suppression:

- completed: 1
- suppressed: 2
- pending: 0
- lifecycle anomalies: 0
- suppression reason: `recursive scheduling drift`

This preserves the fork attempt as evidence without letting unexpected branches
remain runnable.

## Interpretation

This closes the main policy ownership gap from the bounded-autonomy DES run. The
scheduler is now more than a passive queue: a policy runner can decide not to
run pending work and record that decision durably without mislabeling it as a
failure or expiry.

The research arm remains active. The next high-value questions are:

1. Should suppression record the policy decision source more richly, such as the
   wake cycle, state record id, or policy-evaluation artifact?
2. Should branch/fork become an explicit allowed mode with budgeted join
   semantics, rather than being classified as drift?
3. Can the same bounded policy contract survive live-provider execution once
   calls are supervised by subprocess-level timeouts?

## Recommendation

The next engineering step should be to preserve the policy decision source in
suppressed records. That would make later audit easier: not merely "this event
was suppressed", but "this policy evaluation, after this wake, suppressed this
event for this reason."
