# Fork/Join DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed after correcting two scorer false
positives.

- H88 explicit fork mode processes branches without classifying drift: passed.
- H89 branch execution is isolated from sibling branch state: passed.
- H90 join receives all successful branch outputs: passed.
- H91 branch failure is bounded and suppresses siblings: passed.

The preserved `scorer_bug_*` and `scorer_bug2_*` artifacts document the scorer
corrections. The first scorer treated fork-point scheduling metadata as sibling
branch leakage. The second matched `branch_b` inside `branch_budget`. The final
scorer checks for actual sibling branch output fields, not scheduler metadata.

## Scenario Results

### fork_join_success

Classification: `joined`

The coordinator fork wake scheduled two branch events. The fork-aware policy
runner then executed each branch in an isolated session seeded from the same
fork-point state while sharing one event sidecar. Both branches completed, then
the policy runner appended a join event with explicit branch outputs in the join
purpose.

Observed:

- fork branch events: 2
- completed branch events: 2
- failed branch events: 0
- suppressed branch events: 0
- join completed: true
- joined findings: 2
- pending after policy: 0
- branch isolation violations: 0

The join wake produced durable `joined_findings` containing both branch
contributions.

### fork_branch_failure

Classification: `branch_failed`

Branch A intentionally violated strict merge by updating and deleting
`branch_findings` in the same cycle. The failure was recorded as a failed event,
with failure classification and protocol recovery in the branch session JSONL.
The policy runner then suppressed the still-pending branch B event with
source-linked policy fields.

Observed:

- fork branch events: 2
- completed branch events: 0
- failed branch events: 1
- suppressed branch events: 1
- accepted state advanced after failure: false
- failure classification logged: true
- protocol recovery logged: true
- suppression source resolved: true
- pending after policy: 0

This preserves the invariant that failed branch output is evidence, not accepted
state evolution, and that sibling work is explicitly disposed of.

## Interpretation

Fork/join is viable as an explicit scheduler mode under simulated time. The
key distinction is that multiple continuations are only drift under a
single-continuation policy. Under a fork-aware policy, multiple pending branches
can be run, joined, or suppressed with auditable sidecar records.

The result also exposed a design nuance. Branch sessions do not see sibling
branch outputs, but they do inherit the fork-point `_activity_log`, which
contains both scheduled branch labels and purposes. That means branch isolation
currently means "no sibling branch state/output leakage," not "branch-private
knowledge of the fork plan." A stricter branch privacy policy would need to
strip or transform `_activity_log` when seeding branch sessions.

## Recommendation

The next simulated question should be branch-private fork context:

- Can branch sessions be seeded from the same fork point while suppressing
  sibling branch scheduling metadata?
- Does stripping `_activity_log` preserve enough provenance elsewhere in the
  sidecar to keep the run auditable?

This should still be tested in DES before live-provider work. Live-provider
runtime supervision remains a separate engineering layer.
