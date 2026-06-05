# Fork/Join Policy Runner DES Pre-Registration

Date: 2026-06-05

## Research Question

Can fork/join orchestration itself become a reusable scheduler runner while
preserving the branch-private context and audit guarantees established by the
policy-boundary experiment?

The prior experiment factored branch-visible context and sidecar audit
projection into `BranchContextPolicy`, but the DES runner still manually seeded
branches, executed events, scheduled joins, and suppressed siblings. This
experiment tests a first reusable runner layer above the policy helper.

## Hypotheses

### H100: Runner-applied branch execution preserves private context

If branch execution goes through `ForkJoinPolicyRunner`, then branch sessions
should be seeded through `BranchContextPolicy` and should not receive
`_activity_log`, sibling branch labels, or sibling branch purpose fragments in
branch-visible prior state or requested context results.

Falsification condition: any branch-visible wake record contains private
framework state or sibling planning metadata.

### H101: Runner-driven success completes branches and join

If the runner correctly owns the success orchestration, then it should complete
both branches, schedule and run one join event, preserve sidecar auditability,
produce two joined findings, and leave no pending events.

Falsification condition: either branch fails to complete, join does not
complete, joined findings are incomplete, audit projection is incomplete, or
pending events remain.

### H102: Runner-driven failure suppresses siblings with source coordinates

If the runner correctly owns failure disposition, then a strict merge failure in
one branch should fail that branch, suppress the still-pending sibling, avoid
accepted-state advancement, preserve protocol recovery evidence, and link the
suppression to the failed branch record.

Falsification condition: sibling work remains pending, failed state advances,
protocol recovery is absent, or suppression lacks source coordinates.

### H103: Runner telemetry is sufficient for later evaluation

If orchestration moves into a reusable runner, then it must return structured
branch/join results sufficient to evaluate the run without re-parsing every log:
labels, statuses, errors, event records, result record IDs when present, and
suppression records when generated.

Falsification condition: runner results omit labels, statuses, failure errors,
terminal event records, result record IDs for completed branches, or
suppression records for failure disposition.

## Experimental Design

Implement a minimal `ForkJoinPolicyRunner` that consumes `BranchContextPolicy`
and owns:

- branch session seeding through the policy;
- branch event execution through `run_next_event`;
- explicit join-event scheduling from branch outputs;
- join execution;
- pending sibling suppression after a failed branch;
- structured run telemetry.

Run deterministic simulated-time success and failure scenarios equivalent to
the prior policy-boundary DES, but remove branch execution, join scheduling, and
sibling suppression from experiment-local helper code.

Conditions:

- deterministic fake backend;
- simulated time;
- no live provider calls;
- no broad production scheduler rewrite;
- success and failure scenarios both captured.

## Expected Result

Expected before running: H100-H103 pass. If this fails, the design has not yet
crossed from reusable policy helper into reusable fork/join scheduler
orchestration.

## Evaluation Artifacts

- runner implementation and unit tests;
- `run_fork_join_runner_des.py`;
- scenario JSONL logs;
- shared `.events.jsonl` sidecars;
- `results.json`;
- `analysis.md`.
