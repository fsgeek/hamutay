# Branch-Private Context DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed.

- H92 branch-private seed context removes sibling planning metadata: passed.
- H93 shared sidecar auditability is preserved: passed.
- H94 private branches can still join successfully: passed.
- H95 private branch failure remains bounded and source-linked: passed.

## Scenario Results

### branch_private_success

Classification: `joined`

The coordinator scheduled `branch-a` and `branch-b` in the shared sidecar. Each
branch session was seeded from sanitized coordinator records with
`_activity_log` removed from branch-visible state. Both branches completed, and
an explicit join event received both branch outputs as policy context.

Observed:

- branch-private violations: 0
- sidecar audit preserved: true
- completed branch events: 2
- failed branch events: 0
- suppressed branch events: 0
- join completed: true
- joined findings: 2
- pending after policy: 0

The branch-visible scorer checked each wake record's `prior_state` and
event-envelope `context_results` for `_activity_log`, exact sibling branch
labels, and exact sibling branch purpose fragments. None were present.

### branch_private_failure

Classification: `branch_failed`

Branch A was seeded through the same private context transform, then
intentionally violated strict merge by updating and deleting `branch_findings`
in the same cycle. The branch failed with protocol recovery evidence, and the
policy runner suppressed the sibling pending branch with source-linked fields.

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

## Interpretation

The DES now supports a clean conceptual split:

- branch-visible identity context can be narrowed before a branch wake;
- the append-only sidecar remains the audit substrate for full scheduler
  metadata, including labels, purposes, terminal statuses, and suppression
  sources.

This means branch privacy does not require erasing event provenance. The
visibility boundary can be applied at seed/context construction while keeping
the scheduler log authoritative.

The result is still simulated. It does not prove that live providers will
respect branch privacy behaviorally, only that the framework can construct the
right boundary before a model sees the wake.

## Design Implication

Fork/join should grow an explicit branch context policy rather than relying on
raw `seed_history` calls. A production policy should probably distinguish:

- `audit_context`: full sidecar records for operators and evaluators;
- `branch_visible_context`: sanitized prior state and requested memory results;
- `join_context`: deliberate branch outputs selected by the scheduler policy.

This keeps auditability, privacy, and join semantics from being accidentally
coupled.

## Verification

Command run:

```bash
uv run pytest tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py
```

Result: 67 passed.
