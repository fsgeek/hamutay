# Branch-Private Context DES Pre-Registration

Date: 2026-06-05

## Research Question

Can an explicit fork/join scheduler give each branch a branch-private working
context while preserving a shared, auditable event substrate?

The prior fork/join DES showed that branch outputs did not leak across sibling
branches, but branch sessions inherited the coordinator fork-point
`_activity_log`. That activity log contains both sibling branch labels and
purposes. This experiment tests whether branch-visible context can be narrowed
without losing scheduler auditability.

## Hypotheses

### H92: Branch-private seed context removes sibling planning metadata

If branch sessions are seeded from sanitized coordinator records, then each
branch wake should receive the fork-point identity state without sibling branch
labels, sibling branch purposes, or `_activity_log` entries in its visible prior
state or requested context results.

Falsification condition: any branch-visible `prior_state` or event
`context_results` contains `_activity_log`, the sibling branch label, or the
sibling branch purpose text.

### H93: Shared sidecar auditability is preserved

If branch-visible records are sanitized, then the shared event sidecar should
still retain the full fork audit trail: both branch pending records, branch
status transitions, and terminal branch dispositions.

Falsification condition: sidecar records cannot reconstruct both branch labels
and terminal statuses after the private branch run.

### H94: Private branches can still join successfully

If branch-private context is only a visibility policy, then two successful
branches should still complete and an explicit join event should receive both
branch outputs.

Falsification condition: successful branches do not both complete, the join
event does not complete, or the joined state does not contain both branch
findings.

### H95: Private branch failure remains bounded and source-linked

If branch-private context is compatible with existing failure disposition, then
a strict merge failure in one branch should fail that branch, suppress the
sibling, preserve protocol recovery evidence, and link suppression to the
failed branch record.

Falsification condition: failed branch state advances, sibling branch remains
pending, protocol recovery is absent, or suppression lacks the failed branch
record source.

## Experimental Design

Use deterministic fake backends and simulated time. Reuse the fork/join scenario
shape from `fork_join_des_20260605`, but add a branch-private seed transform:

- coordinator session creates the fork point and schedules `branch-a` and
  `branch-b` in the shared event sidecar;
- branch sessions are seeded from deep-copied coordinator records with
  `_activity_log` removed from branch-visible state;
- both branch sessions still share the original event sidecar;
- success path runs both branches and an explicit join event;
- failure path intentionally makes branch A violate strict merge by both
  updating and deleting the same key, then suppresses pending sibling work.

## Expected Result

Expected outcome before running: H92-H95 pass. The design should separate
branch-visible identity context from shared scheduler audit metadata without
requiring production scheduler changes.

If H92 fails, branch privacy requires a stronger seed/context boundary than
simple state sanitization. If H93 fails, privacy and auditability are coupled in
the current representation and need a first-class fork context policy.

## Evaluation Artifacts

- `run_branch_private_context_des.py`
- `results.json`
- scenario JSONL logs
- shared `.events.jsonl` sidecars
- `analysis.md`
