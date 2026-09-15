# The GPU lease — design review, round four

Date: 2026-09-15. Reviewer: Codex (codex exec, read-only sandbox), before implementation. Round 4 of 5; dispositions are in the design document (revision 5). Reviewed revision 4 at commit `12f9fb3` against all prior reviews, the running event, heartbeat, and session code, the deployed units, and installed systemd 249.11 semantics.

## Resolved from round three

R3 B1 — Resolved by mechanism: `door.json` makes participation independent of session history, and store-level `LeaseGateRequired` enforcement closes the ordinary CLI and library bypasses.

R3 B2 — Resolved by mechanism: `4090.door`, canonical absolute path resolution, the heartbeat’s lock-path assertion, and the pre-stop store append establish the same-inode and record-before-stop guarantees.

R3 B3 — New defect: `mutation_id` correctly distinguishes renewals and readiness is correctly observational, but quarantine entry and `release_force` reconciliation remain incomplete (Blocking 3).

R3 B4 — New defect: systemd scopes provide the required cgroup lifetime and kill behavior, but cleanup is not a prerequisite for the next grant and the proposed supervisor timing can still cross expiry (Blocking 1 and 2).

R3 S1 — Resolved by mechanism: one episode-keyed `_transition`, hydrated from the latest durable heartbeat status, removes the conflicting de-duplication state.

R3 S2 — New defect: the durable observation is compatible with the session log, but the ready-edge/discovery crash boundary and the proposed setter’s ownership remain unresolved (Significant 1).

R3 S3 — Resolved by mechanism: `ensure_stopped` supplies an episode-specific acknowledgment even when the server was already inactive or failed; its use by `run` still needs live-lease validation (Blocking 2).

R3 S4 — Resolved by mechanism: disable-before-replacement, explicit installation, `static`, symlink removal, dependency inspection, and shared `AYLLU_STATE_DIR` now match systemd 249; the cutover itself has a new race (Significant 2).

R3 M1 — Resolved by mechanism: readiness is recorded per edge and per `InvocationID`, with durable state reconstructed at boot.

R3 M2 — Resolved by mechanism: `lease_blocked` is excluded from `ran`, stops the batch, and becomes the scheduler stop reason.

## Blocking

### 1. An expired scope is not a barrier to the next workload

**Defect.** The systemd premise is sound: on installed systemd 249 a scope lives while any process remains in it, independently of one designated main process; `systemctl stop` uses the default `KillMode=control-group` and terminates the whole cgroup; and `--collect` applies to scopes and unloads them after inactive or failed completion.

The lease protocol does not use those guarantees soon enough. Any next lock holder may process an expired lease, remove `4090.lease`, and grant a new lease. Only the heartbeat’s later FREE return sequence checks the expired lease’s scope, and it checks only the “most recent” expired or released lease. If a new lease arrives first, the heartbeat takes the LEASE_LIVE rest path, emits `ensure_stopped` based solely on the llama-server unit, and the new `run` starts while the expired scope may still contain the old workload. The same violation follows from a heartbeat crash after the expire outcome but before scope cleanup. Two holder workloads can therefore share the card.

The reconciliation observation is also insufficient for `--collect`: the specified `systemctl show` properties omit `LoadState`, although a collected scope is expected to become not-loaded.

**Recommendation.** Make cleanup of the lease’s recorded scope part of expiry itself and a prerequisite for declaring the resource free or granting another lease. Persist an uncleared-scope tombstone until `LoadState=not-found` or `ActiveState ∈ {inactive, failed}` is observed; every grant, `ensure_stopped`, server start, and force-clear must resolve all such tombstones, not merely the latest ledger episode. Include `LoadState` in scope observations and quarantine if termination cannot be established.

### 2. The registered `run` path can start after its lease expires

**Defect.** `systemd-run --user --scope` is synchronous on systemd 249: it returns when the command finishes. Read literally, step 2 prevents the Bash wrapper from reaching the renewal loop in step 3. Running it in the background can supply the intended concurrency, but that process arrangement, exit-status collection, signal handling, and scope-registration acknowledgment are not specified.

Even with that correction, `run` does not renew while waiting, and `wait` requires only a historical `ensure_stopped` outcome plus a currently inactive server. It does not require that the same lease is still live. With the allowed one-minute TTL and a thirty-minute wait timeout—or after suspend—the lease can expire before `wait` returns and the workload can then launch without a lease. Rechecking immediately before launch is still racy because expiry and server restart may occur before the command is registered in its named scope.

The failure schedule also cannot meet its promise for short TTLs: the kill threshold is only `ttl/6` before expiry, retries may be a minute apart, and the design grants a 60-second TERM grace before `stop`. For TTLs at or below six minutes, termination may begin or finish after expiry.

**Recommendation.** Start lease supervision at acquisition, including during `wait`. Specify `systemd-run` as a background child whose PID and status are collected, and establish an under-`4090.lock` handoff that proves the lease is live with sufficient remaining margin and the named scope is registered before it may execute workload code. Make `wait` reject an absent, expired, replaced, or quarantined lease. Derive retry and termination deadlines from the actual grace and systemd stop allowance, or raise the minimum TTL so complete cgroup death is guaranteed before expiry.

### 3. Quarantine and forced-clear reconciliation still violate the action invariant

**Defect.** Entering quarantine as the outcome of an existing failed action solves the recursive-intent problem only when such an action exists. A claim gate or heartbeat that merely discovers a malformed or unreadable lease has no preceding mutating action and therefore no valid `source_action_id`; creating `4090.quarantine` in that path is an un-intented mutation under invariant 7.

The dangling table also says that `release_force` completed when the lease is absent or its “`mutation_id` [is] newer than the intent’s `generation`,” which compares unlike fields and does not inspect the quarantine file. In the ordinary quarantine-only state, the lease is already absent. A crash immediately after the `release_force` intent but before either deletion would therefore be reconciled as completed while the quarantine remains. Removing the lease and quarantine files is two mutations, so the intermediate states must be explicitly recoverable.

**Recommendation.** Define a non-recursive quarantine-entry transaction for unsolicited malformed/unreadable observations, with its own intent or another explicitly durable precursor and exact reconciliation by `source_action_id` and `quarantine_id`. Define `release_force` completion against both files and their expected identities, compare generation only with generation, and have reconciliation finish or safely retry a partial two-file clear before recording success.

## Significant

### 1. Context discovery can be permanently skipped after a readiness crash

**Defect.** The proposed stateless `substrate_observation` is compatible with `_resume_from_log()`, which already skips records without `state`, and a separate append-order scan can read it. The sequence is not crash-consistent, however: revision 4 appends `server_ready` before discovery and the substrate observation. If the heartbeat crashes between those writes, boot restores “ready” for that `InvocationID` and emits no new edge. Discovery is therefore not retried. The implementation must then either remain warming forever or violate the fresh-per-invocation rule by claiming with inherited context.

The named API also conflicts with the current object graph. `OpenAITasteBackend` owns `_context_limit`, while `OpenTasteSession` owns `_launch_config`; the backend has no session reference. A backend method with the stated signature cannot update both without an additional back-reference or callback, and `_log_entry()` is a full-cycle writer rather than an API for appending the new stateless record.

**Recommendation.** Track context validation separately from readiness edges. Whenever the current invocation is ready but lacks a matching durable positive `substrate_observation`, retry discovery regardless of whether `server_ready` was already recorded, and permit claims only after that observation is durable. Put the coordinating setter/append operation on `OpenTasteSession` or explicitly inject a callback/shared metadata object so it updates the backend, launch metadata, and session log through a dedicated append method.

### 2. The migration can interrupt a wake and its dependency scan is incomplete

**Defect.** Revision 4 writes `door.json` and then restarts the heartbeat after polling the store for no `running` event. The running old process constructed its `EventStore` before `door.json` existed and therefore remains unbound. It can claim between the migration’s observation and `systemctl restart`, causing the migration to terminate an active wake and boot recovery to re-pend it. That contradicts the no-interrupted-wake invariant and the claim that the binding exists before any claim can happen.

The final static/disable assertions themselves are correct for systemd 249. The “any installed unit” assertion is still narrower than stated: scanning only `~/.config/systemd/user` misses dormant units and enablement links in other effective user-unit search paths such as `/etc/systemd/user` and `/usr/lib/systemd/user`. Runtime reverse properties cover only the loaded dependency graph.

**Recommendation.** Quiesce the old heartbeat atomically with the event store—for example, hold the event-store lock while confirming no running event and stopping the old service—before exposing `door.json` or the lease command, then install and start the bound implementation. Inspect all effective user-unit search paths and enablement symlinks, while retaining the runtime dependency assertions and exact `static` check.

## Minor

None.

Verdict: **do not implement revision 4 yet**; the systemd primitives are suitable, but stale-scope grant ordering, the non-linearized supervisor launch, and incomplete quarantine reconciliation can still violate the no-overlap and crash-consistency invariants.