# Fork/Join Policy Runner DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed.

- H100 runner-applied branch execution preserves private context: passed.
- H101 runner-driven success completes branches and join: passed.
- H102 runner-driven failure suppresses siblings with source coordinates:
  passed.
- H103 runner telemetry is sufficient for later evaluation: passed.

## Scenario Results

### fork_join_runner_success

Classification: `joined`

The coordinator scheduled `branch-a` and `branch-b`. Both branches were executed
through `ForkJoinPolicyRunner.run_branch()`, which seeded each session through
`BranchContextPolicy`. The runner then scheduled the join event from selected
branch outputs and executed it through `run_join()`.

Observed:

- branch-private violations: 0
- sidecar audit preserved: true
- completed branch events: 2
- failed branch events: 0
- suppressed branch events: 0
- join completed: true
- joined findings: 2
- pending after policy: 0
- branch result records present: 2
- join result record present: true

### fork_join_runner_failure

Classification: `branch_failed`

Branch A was executed through the runner and intentionally failed strict merge.
The runner returned a structured failed branch result with the terminal event
record and failure error, then suppressed pending sibling work using
`suppress_pending_after_failure()`.

Observed:

- branch-private violations: 0
- sidecar audit preserved: true
- completed branch events: 0
- failed branch events: 1
- suppressed branch events: 1
- accepted state advanced after failure: false
- failure classification logged: true
- protocol recovery logged: true
- suppression source resolved: true
- pending after policy: 0
- suppression records present: true

## Interpretation

The event-loop scaffold now has three separable layers:

1. `events.py`: append-only event storage, claiming, context resolution, event
   envelope construction, and single-event execution.
2. `BranchContextPolicy`: branch-visible projection, sidecar audit projection,
   and explicit join event construction.
3. `ForkJoinPolicyRunner`: reusable branch execution, join scheduling/execution,
   failure suppression, and structured orchestration telemetry.

This is materially better than the prior hand-orchestrated experiment runners.
The scheduler can now express the fork/join pattern without each experiment
re-implementing privacy, audit, join, and suppression behavior.

The result is still deterministic DES work. It does not settle live-provider
runtime supervision, concurrent branch execution, retry policy, or durable
cross-session branch records. It does show that the local architecture can carry
bounded autonomy and branch composition as explicit policy rather than ad hoc
script behavior.

## Design Implication

The next architectural pressure point is durable branch identity. The runner
currently returns structured telemetry and uses separate session logs, but it
does not yet mint a first-class fork/run record that ties coordinator, branch,
join, and suppression records into one durable object. That may be the next
needed substrate before live-provider or long-horizon fork work.

## Verification

Command run:

```bash
uv run pytest tests/unit/test_event_policies.py tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py
```

Result: 74 passed.
