# The GPU lease — design review, round six

Date: 2026-09-15. Reviewer: Codex (codex exec, read-only sandbox), before implementation. Round 6 of 6; dispositions are in the design document (revision 7), which closed the loop. Reviewed revision 6 against round five and the stated invariants.

## Resolved from round five

R5 B1 — Resolved by mechanism: a bound store rejects every non-heartbeat claim path; the single-threaded heartbeat is the sole gate holder, and its process-lifetime lock excludes `force-stop` during a wake.

R5 B2 — New defect: complete FREE, the expanded observation schema, and tombstone-aware predicates are concrete mechanisms, but tombstone resolution still has actionless and contradictory paths (Blocking 1). The lease schema also still permits a state its completion predicate cannot represent (Significant 1).

R5 B3 — Resolved by mechanism: registration failure establishes scope death before release, and the six-minute deadline is derived from the stated detection and termination allowances with a 15-minute minimum TTL.

R5 B4 — New defect: parent/child actions were removed, but the replacement alternately describes tombstone cleanup as a standalone `workload_killed` action and as un-intented inline work, including inside the actionless claim gate (Blocking 1).

R5 B5 — New defect: escrow renames provide identity for unreadable files and the order is now consistent, but the completion predicate can be true before either rename occurs (Blocking 2).

R5 S1 — New defect: the single-descriptor helper and explicit symlink enumeration resolve the reported defects by mechanism, but the migration cannot both deploy a committed `door.json` and defer that file until after quiescence (Significant 3).

## Blocking

### 1. Complete-FREE enforcement still performs mutations without a flat action

**Defect.** The tombstone section says to “run `workload_killed`,” while the flat-state-machine section says that `lease`, `server_start`, the claim gate, and `release_force` perform the same stop, observation, and removal inline with no separate intent. The claim gate has no enclosing action at all. The return sequence can likewise resolve tombstones while the server is already active and therefore never create a `server_start` intent. A conforming implementation can consequently kill a scope or remove its tombstone with no prior intent and no outcome. A crash after removal leaves nothing from which that mutation or killed workload can be reconciled, violating invariant 7.

**Recommendation.** Give every tombstone resolution exactly one flat transaction. For example, complete a standalone `workload_killed` action under the already-held lock before continuing the claim, lease, force-clear, or start decision. Define its outcome predicate as scope dead and that specific tombstone absent; do not also describe the same work as un-intented inline side effects.

### 2. `release_force` can reconcile as successful before clearing anything

**Defect.** Immediately after a `release_force` intent, before either target is renamed, there is no action-specific escrow file. If no tombstones exist, the stated predicate—no escrow for this action and no recorded tombstone—is already true even though the original lease and quarantine files remain. Recovery therefore writes a reconciled `ok` outcome without performing the override. This violates invariant 7’s requirement that the outcome be determined from all intended side effects.

**Recommendation.** Record which original entries were present in the intent and require each targeted original and its action-specific escrow to be absent before completion. Under the lock and dangling-intent-first protocol, an original name encountered during reconciliation cannot be legitimate successor state; rename it to this action’s escrow, delete it, and only then record `ok`.

## Significant

### 1. A schema-valid lease can have no satisfiable lease predicate

**Defect.** `4090.lease` permits `scope_unit` to be absent, while the `lease` action always writes a tombstone for `scope_unit` and completes only when that tombstone is present. `release` and `expire` separately acknowledge the no-scope case with “or none recorded.” The primitive `lease` command has no scope parameter, so conforming implementations can reject a schema-valid lease, invent the deterministic `run` scope, or omit the tombstone and use an unstated predicate. Those choices produce incompatible state and recovery behavior.

**Recommendation.** Make `scope_unit` mandatory for every newly granted lease and define its deterministic value, or define a distinct no-scope lease form with its own completion, expiry, and safety contract. Align the schema, CLI, action table, and fixtures on that single choice.

### 2. `force-stop` has two incompatible action identities

**Defect.** The action schema and completion table define `force_stop`, but the command sequence writes an `ensure_stopped` intent. Boot reconciliation accepts either form, whereas `wait` accepts only an ok `ensure_stopped` outcome. One conforming implementation can therefore ledger `force_stop` and leave `wait` blocked; another can ledger `ensure_stopped` and never use the declared `force_stop` action.

**Recommendation.** Select one canonical action identity. Specify that identity consistently in the command sequence, action table, `wait`, boot reconciliation, tests, and ledger schema.

### 3. The migration cannot defer a committed participation file

**Defect.** The deployment surface says `community/qwen/door.json` is committed, while migration steps 5–7 require deploying the code without that file and creating it only after successful quiescence. In the live project path, deploying a commit containing the file materializes the binding before the helper runs; a timeout therefore cannot abort “before `door.json` is written.” The existing heartbeat retains its previously unbound `EventStore` while configuration now says the door participates, allowing unguarded claims during that interval and contradicting invariant 8.

**Recommendation.** Make the active `door.json` solely a post-quiescence migration artifact, with any committed content stored as a template elsewhere, or quiesce the old heartbeat before installing a revision that contains the active file. The timeout path must verifiably leave the active door file absent.

## Minor

### 1. The scheduler contract still requires two incompatible results

**Defect.** The participation section says `step_pending_events` on a bound store refuses with `LeaseGateRequired` and is never offered a gate. The test inventory still requires `lease_blocked` to be surfaced as the scheduler stop reason. An unguarded scheduler cannot both refuse and return that result, while an unbound scheduler can never observe the lease gate.

**Recommendation.** Remove the obsolete scheduler-stop assertion or identify a heartbeat-owned scheduler entry point that receives the gate and is specifically required to return `lease_blocked`.

Verdict: **do not implement revision 6 yet**; force-clear recovery and tombstone resolution still violate the action invariant, and the remaining schema and cutover contradictions permit incompatible implementations.