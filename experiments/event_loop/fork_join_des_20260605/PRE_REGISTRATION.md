# Fork/Join DES Pre-registration

Date: 2026-06-05

## Research Question

Can the Hamut'ay simulated event-loop policy support explicit branch/fork/join
semantics, rather than treating multiple same-cycle continuations as drift?

## Motivation

The bounded-autonomy DES experiment classified multiple continuations from one
wake as `drift`. That was correct for a single-continuation policy, but it
leaves a larger design question: can multiple continuations become an explicit
fork mode with bounded branch budgets and a join step?

The central confound is branch isolation. If branch events run in one mutable
linear session, later branches inherit earlier branch state. That is not a real
fork. This experiment therefore treats fork/join as a policy runner behavior:
branch wakes run in isolated sessions seeded from the fork point, then a join
wake receives the branch outputs as explicit context.

## Hypotheses

### H88: explicit fork mode processes branches without classifying drift

Given a fork wake that schedules two branch continuations, a fork-aware policy
runner will process both branches under a fork policy and classify the scenario
as `joined`, not `drift`.

Falsification: multiple branch continuations remain classified as drift in the
explicit fork condition, or branch events remain pending after successful join.

### H89: branch execution is isolated from sibling branch state

Each branch wake receives the same fork-point seed state and does not see
durable fields introduced by sibling branches.

Falsification: a branch wake record contains prior sibling branch findings in
its `prior_state` or event context.

### H90: join receives all successful branch outputs

The join wake receives explicit branch outputs and produces a durable
`joined_findings` field containing both branch contributions.

Falsification: the join wake lacks either branch output or final state lacks a
joined contribution from both branches.

### H91: branch failure is bounded and suppresses siblings

If one branch fails strict merge, accepted branch state does not advance, the
failed branch sidecar records failure diagnostics, and still-pending sibling
branches are suppressed with source-linked policy records.

Falsification: branch failure mutates accepted branch state, the sibling remains
pending/runnable, or suppression lacks source coordinates.

## Conditions

Two deterministic simulated scenarios:

1. `fork_join_success`: fork schedules branch A and branch B; both branches
   complete in isolated branch sessions; join combines outputs.
2. `fork_branch_failure`: fork schedules branch A and branch B; branch A fails
   strict merge; branch B is suppressed by policy before execution.

No live model calls. Simulated time only. Use real `OpenTasteSession`,
`EventStore`, `schedule_event`, `run_next_event`, strict merge, protocol
recovery, and sidecar suppression primitives.

## Primary Measures

- `classification`
- `fork_event_count`
- `branch_completed_count`
- `branch_failed_count`
- `branch_suppressed_count`
- `join_completed`
- `joined_findings_count`
- `branch_isolation_violations`
- `failure_classification_logged`
- `protocol_recovery_logged`
- `suppression_source_resolved`
- `pending_after_policy`

## Expected Results

- `fork_join_success` classifies `joined`.
- `fork_join_success` completes two isolated branches and one join.
- `fork_join_success` has zero branch isolation violations.
- `fork_branch_failure` classifies `branch_failed`.
- `fork_branch_failure` records strict failure diagnostics for the failed branch.
- `fork_branch_failure` suppresses the unrun sibling branch with source-linked
  policy records.

If these pass, fork/join becomes a viable explicit scheduler mode to explore
before live-provider experiments.
