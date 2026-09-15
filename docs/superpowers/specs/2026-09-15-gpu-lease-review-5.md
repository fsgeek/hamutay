# The GPU lease — design review, round five

Date: 2026-09-15. Reviewer: Codex (codex exec, read-only sandbox), before implementation. Round 5 of 6; dispositions are in the design document (revision 6). Reviewed revision 5 against round four, the running event-store/session code, and installed systemd 249.11 semantics.

## Resolved from round four

R4 B1 — New defect: persistent per-scope tombstones and the expanded definition of FREE close the original stale-scope grant race by mechanism, but the claim gate ignores tombstones and tombstone mutations are not fully covered by action reconciliation (Blocking 2). `LoadState` is resolved only in prose: it is required by the resolver but absent from the ledger’s `observed` schema.

R4 B2 — New defect: supervision from acquisition, renewal during `wait`, live-lease validation, background `systemd-run`, and registration under `4090.lock` are mechanisms. The failure cleanup and three-minute termination schedule still do not guarantee release or death before expiry (Blocking 3).

R4 B3 — New defect: `quarantine_enter` now has its own intent and exact `source_action_id` predicate, resolving unsolicited quarantine entry by mechanism. Nested-action recovery and forced clearing of malformed or unreadable files remain indeterminate (Blocking 4 and 5).

R4 S1 — Resolved by mechanism: context validation is independent of readiness edges, keyed to `InvocationID`, retried until a positive observation is durable, and coordinated by the session-owned setter and dedicated append method.

R4 S2 — New defect: holding the event-store lock across the no-running check and service stop is the correct mechanism, and enumerating `systemd-analyze --user unit-paths` has the correct scope. The specified check self-deadlocks through the current locking API, and the symlink scan is not operationally defined (Significant 1).

## Blocking

### 1. Lease acquisition does not exclude an already-running wake

**Defect.** The claim gate linearizes “lease first, then claim,” but `lease` does not inspect the event store. After a guarded claim appends `running` and releases `4090.lock`, another actor may grant a lease while that wake is executing. This matters because guarded direct CLI and library runners remain supported: they do not own the heartbeat’s lifetime lock, and a later heartbeat rest sequence can stop llama-server underneath their wake. The result is a terminal transport failure manufactured by the loan, violating the no-interrupted-wake invariant.

**Recommendation.** Make a new lease grant, under `4090.lock` and then the event-store lock, refuse or wait while any event’s latest status is `running`. Use the same locked predicate immediately before every loan-induced server stop. Add a deterministic claim-before-grant test using a direct guarded runner, not only the heartbeat’s synchronous path.

### 2. Tombstones are neither a claim barrier nor fully action-reconcilable

**Defect.** FREE is defined as having no tombstone, but `LeaseGate.claim()` blocks only on quarantine or a lease. A completed early `release`, or any stale dead tombstone, can therefore allow an event to be marked `running` before the heartbeat has resolved the scope and restarted the substrate.

The tombstone lifecycle also violates invariant 7. A `lease` intent is reconciled solely from the lease’s `mutation_id`, so a crash after writing the lease but before creating its required tombstone is declared completed. `workload_killed` is completed solely from scope state, so a crash before tombstone removal leaves an allegedly completed action. Removing a tombstone whose scope is already dead has no stated intent at all. The ledger schema also omits the promised `load_state`.

**Recommendation.** Require the gate to resolve all tombstones and revalidate complete FREE before claiming. Include tombstone presence in `lease` reconciliation, and make tombstone removal either a dedicated action or an explicit side effect of `workload_killed` whose completion requires both a dead scope and an absent tombstone. Add `load_state` and `scope_unit` to the durable observation schema.

### 3. The `run` failure paths can release before scope death and cross expiry

**Defect.** On registration timeout, revision 5 kills only the background `systemd-run` PID and then releases. In scope mode, `systemd-run` is the parent of the command; killing that parent does not prove that its child or scope is gone. This directly contradicts the stated “release never precedes scope death” test.

The three-minute kill threshold also has no actual margin. Detection may occur up to 30 seconds after the threshold because that is the retry interval, leaving at most 150 seconds for the stated 60-second grace plus 90-second stop allowance. Lock acquisition, command execution, observation, tombstone removal, and release then push completion past expiry. Raising the minimum TTL to ten minutes does not enlarge this fixed final window.

**Recommendation.** Treat registration timeout exactly like every other supervised shutdown: stop the named scope, observe `LoadState=not-found` or inactive/failed, remove its tombstone, and only then release; quarantine and retain the coordination state if death cannot be established. Derive the kill deadline from the retry interval, actual stop allowance, worst-case lock delay, and an explicit safety margin.

### 4. Nested actions contradict the dangling-intent state machine

**Defect.** Every mutating action is required to resolve all dangling intents before writing its own intent, but `expire` writes its intent and then starts a nested `workload_killed` action. Taken literally, the child’s preamble sees the enclosing `expire` as dangling and reconciles it as `not_performed` while the old lease still exists; the outer operation can later append a second, conflicting outcome. `release_force` can recurse similarly when its partial-clear reconciler resolves tombstones and starts `workload_killed`. Two conforming implementations must either violate the universal preamble or invent an unstated parent-action exception.

**Recommendation.** Define one non-recursive transaction model. Either flatten scope termination and file cleanup into the enclosing action, or give child actions a durable `parent_action_id`, exempt in-flight ancestors from child preambles, and require crash recovery to reconcile children before parents. State one completion predicate covering every side effect of each enclosing action.

### 5. `release_force` cannot exactly reconcile the states it is meant to clear

**Defect.** The intent records a lease `mutation_id` and quarantine `quarantine_id` only when they can be parsed. A malformed or unreadable lease—and especially a malformed or unreadable quarantine file—has no such identity. After a crash during clearing, the reconciler cannot determine whether the remaining file is the original file owed deletion or newly introduced state. The generic unreadable-state rule sends it back into quarantine instead of completing the ledgered override.

The ordering is also contradictory: the tombstone section says `release_force` resolves all tombstones first, while the command’s fixed order removes quarantine and lease before resolving tombstones. The ledger action enumeration omits `quarantine_enter` entirely.

**Recommendation.** Give force-clear exact identities even for invalid contents, preferably by atomically renaming each targeted file to an action-specific escrow name before deletion; otherwise record sufficient raw directory-entry identity and digest information. Choose one order—scope death before removal of the lease and quarantine is the invariant-preserving order—and use it in normal execution and reconciliation. Add `quarantine_enter` and the force-clear identity fields to the ledger schema.

## Significant

### 1. The migration quiesce and unit-path scan are not executable as specified

**Defect.** Step 6 externally holds `session.jsonl.events.jsonl.lock` and then calls `EventStore.latest_by_event_id()`. That public method calls `read_records()`, which opens the same lock file independently and takes another blocking `flock`; under the specified arrangement, the migration blocks against its own inherited lock and never reaches `systemctl stop`. The 30-minute exhaustion behavior is also unstated; proceeding would permit an interrupted wake, while aborting would be safe.

The path scan says to “grep” `*.wants` and `*.requires` symlinks. Grep does not reliably inspect a symlink’s directory-entry name or target, particularly for dangling links, so implementations can disagree about whether a dependency link is present.

**Recommendation.** Put lock acquisition, unlocked append-order reduction, and `systemctl stop` in one helper that owns a single lock descriptor; specify that timeout aborts migration without stopping the heartbeat or exposing `door.json`. Enumerate regular unit/drop-in files for content checks and separately enumerate every dependency symlink by pathname and `readlink` target across all reported unit paths.

## Minor

None.

Verdict: **do not implement revision 5 yet**; context validation is closed, but wake/grant exclusion, tombstone and nested-action reconciliation, supervisor shutdown, forced-clear identity, and the migration procedure still violate or underspecify the stated invariants.