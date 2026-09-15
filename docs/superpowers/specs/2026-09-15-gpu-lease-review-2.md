# The GPU lease — design review, round two

Date: 2026-09-15. Reviewer: Codex (codex exec, read-only sandbox), before implementation. Round 2 of 3; dispositions are in the design document (revision 3). Reviewed revision 2 at commit 9a944b3 against the running heartbeat and event-store code, deployed units and checkpoint script, context-ceiling implementation, wake-budget tests, and founding invariants.

## Resolved from round one

B5 — Resolved: malformed or unreadable lease state now quarantines the resource, blocks grants, claims, and starts, preserves the file, and requires an audited override.

S1 — Resolved: renew and release require the lease capability, while the security claim has been correctly narrowed to accountability among mutually trusted local callers.

S2 — Resolved by removal: there is no steward drain reader or drain deadline in revision 2.

S4 — Resolved: `waking/substrate_returning` closes a lease rest before warming begins.

S5 — Resolved: overlap is explicitly a prioritized sequential state stream, with budget segments split around lease episodes.

S7 — Resolved by removal of the timer; `server_start` and `server_ready` are now distinct facts.

S8 — Resolved: the constitution uses substrate-neutral operational wording without social or consent framing.

S9 — Resolved: the external ledger path, locked byte snapshot, digest-only repository record, absent-ledger behavior, and checkpoint destination are specified.

M1 — Resolved: liveness boundaries, timestamp requirements, TTL grammar and bounds, malformed shapes, and renewal field behavior are specified with shared fixtures.

M2 — Resolved: `expected_until` is explicitly an estimate, `expires_at` is enforceable, neither is called a resume time, and the first-observed detail policy is declared.

M4 — Resolved: the revision names the compatibility surfaces, barrier tests, rest cases, context cases, checkpoint behavior, and systemd verification.

## Blocking

### 1. The proposed `may_claim` callback is still not an atomic lease/claim barrier

**Defect.** Round-one B1 is resolved only in prose. Revision 2 says that `run_pending_events` calls a `may_claim` callback which reads the lease under `4090.lock` “immediately before” `claim_next_pending`. In the running code, however, `run_pending_events()` delegates to `run_next_event()`, and the latter independently enters `EventStore.claim_next_pending()`. An ordinary callback returns and releases the lease lock before the event-store lock is acquired, leaving the original lease-between-check-and-claim race intact. Calling the callback from inside `claim_next_pending()` would instead acquire the locks in event-store-then-lease order, opposite the declared lease-then-event-store order and capable of deadlocking against the rest/reconstruction paths.

The same missing linearization exists on return: only the rest sequence is explicitly under the lease lock. A heartbeat can observe FREE, a holder can create a lease, and the heartbeat can then issue `systemctl start` under that live lease. The holder’s later `wait` prevents training from starting immediately, but the design’s stronger invariant—“lease live → server inactive/failed”—is false during the race.

Finally, `events.py` exposes `run-one` and `run-all`, and other code calls `run_next_event()` and `claim_next_pending()` directly. The statement that the heartbeat is the only claimant is not enforced by the running claim surfaces; a manual qwen event runner can bypass a guard installed only in `HeartbeatLoop`.

**Recommendation.** Define a lock-owning claim gate, not a Boolean callback: acquire `4090.lock`, re-read and validate the lease, keep that lock held while `claim_next_pending()` acquires the event-store lock and appends `running`, then release in the declared order. Thread the gate explicitly through `run_pending_events()` and `run_next_event()`, and return a distinct lease-blocked result. Revalidate FREE under the same lock immediately around every `systemctl start` request. Either make all qwen claim entry points use this gate or make unguarded `run-one`/`run-all` refuse a lease-participating door. Add deterministic lease-before-claim, claim-before-lease, lease-before-start, and direct-runner tests.

### 2. `force-stop` reintroduces the event-killing defect removed with `DRAIN_MAX`

**Defect.** Round-one B2 introduces a new defect in its disposition. The automatic forced cutoff is gone, but `ayllu-gpu force-stop` is permitted after `wait` times out. A timeout proves only that no successful `server_stop` row arrived within 15 minutes; it does not prove that the heartbeat is down. A legitimate natural wake can last longer than that—the local-substrate design records a 28-minute wake. In that case the heartbeat is alive inside `session.exchange()`, and `force-stop` kills llama-server underneath it. The running `run_next_event()` catches the transport exception, appends terminal `failed`, and re-raises. Reconstruction of a later `force_stop` row cannot undo that terminal event. This violates “no wake is interrupted” and recreates precisely the failure mode identified in round one.

**Recommendation.** Make `force-stop` refuse while the heartbeat can be running. The strongest existing proof is the heartbeat’s process-lifetime lock: the override should acquire and hold the qwen heartbeat lock before stopping the server, so an active heartbeat or an automatic restart excludes the operation. A dead heartbeat may leave an orphaned `running` record; that is safe because normal boot recovery re-pends it. Timeout alone must never authorize a stop. Test a wake longer than the wait timeout, heartbeat crash mid-wake followed by force-stop, and the resulting `pending → running → recovered pending` history.

### 3. Intent/outcome rows do not yet make the lease ledger crash-consistent

**Defect.** Round-one B6 is resolved only in prose. The schema now has `action_id`, intent, outcome, and observed state, but the design does not specify mutation ordering or recovery for most crash boundaries. A CLI can crash after a lease file is written but before the lease outcome, after release removes the file but before its outcome, after expiry cleanup but before its outcome, or after `force-stop` stops the server but before its outcome. The last case is especially consequential: reconstruction considers only an ok `force_stop` outcome, so a real card transfer with a dangling intent can disappear from the resident’s store. The one stated reconciliation rule covers a heartbeat crash between a server-stop intent and outcome; it does not define how the next arbitrary actor resolves incomplete lease, renew, release, expiry, quarantine, or force-stop actions, nor how a reconciliation row binds to the original `action_id`.

**Recommendation.** Specify an action state machine for every mutating command: exact intent-before-mutation ordering, outcome meaning, how the next lock holder detects each dangling intent, which observable state proves or disproves completion, and whether it appends an outcome for the original `action_id` or a linked reconciliation. Lease-file generation and systemd observations must be sufficient to distinguish completed, not-performed, and indeterminate actions; indeterminate state must quarantine. Reconstruction must consume reconciled force-stop outcomes as well as uninterrupted ones. Test process death at every boundary of lease, renew, release, expire, server start/stop, and force-stop.

### 4. Removing `[Install]` does not disable the already-enabled server unit

**Defect.** Round-one B3 is resolved only in prose. Revision 2 removes `WantedBy=` and the heartbeat dependency, which prevents future enablement through the revised files, but the running unit and community runbook currently instruct operators to enable `hamutay-llama-server`. Removing `[Install]` does not remove an existing `default.target.wants` symlink. Without an explicit migration, the already-enabled unit will still start at user-manager boot independently of the heartbeat and potentially during a live lease.

**Recommendation.** Specify an ordered deployment migration that installs the revised heartbeat code and drop-in, reloads systemd, explicitly disables the existing server unit, and verifies `is-enabled` before the design is considered active. Define safe sequencing around a currently running wake or lease. Unit-file assertions are insufficient; add a deployment check for the persisted enablement state.

## Significant

### 1. Restart breaks the specified lease-rest continuation and return sequences

**Defect.** Round-one B4’s revised episode handling introduces a new defect. `HeartbeatLoop.boot()` currently always appends `waking/boot`. The proposed rest sequence then appends `resting/substrate_lent` only if the store has no such record for the lease ID anywhere. After a restart during an already-recorded lease, that historical record exists, so no continuation record follows `waking/boot`. The latest durable status therefore remains waking while the heartbeat is actually resting, and `_rest_episodes()` closes the episode at boot instead of bridging it. The design’s proposed “`waking/boot` followed by a `resting` with the same lease_id” reducer cannot help because the rest sequence suppresses that second record, and the boot record itself carries no lease ID.

The reverse case also fails: if the heartbeat recorded a lease rest, crashed, and the holder released while it was down, boot’s `waking/boot` masks the prior rest. The return sequence tests only whether the last status is resting, so it will not append the specified `waking/substrate_returning` or recover the lease identity.

**Recommendation.** Reconstruct current episode state before or as part of boot. During a still-live lease, append a continuation `resting/substrate_lent` after `waking/boot`, marked with the same lease ID; de-duplicate only repeated observations within the current uninterrupted episode, not every historical occurrence. When the lease ended while the heartbeat was down, derive its identity and closing time from the ledger and append an explicit returning record rather than relying on the generic boot transition. Test restart while live, release while down, expiry while down, and restart during quarantine.

### 2. Rule (b) does not provide exactly one delivered post-loan notice

**Defect.** Round-one S3’s disposition introduces a new defect. An event that waited during the loan and is also the first claim afterward satisfies both rule (a) and rule (b), so the text specifies two notes for one episode; the later data-flow claim that the note comes from “rule a or b” contradicts this. More importantly, using any intervening `running` record as consumption loses the notice across failure and crash. If the first claim fails while resolving requested context, or the process dies after appending `running` but before constructing or sending the envelope, boot re-pends the event but that earlier running record prevents rule (b) from appearing on the retry. The resident was never told, although the store says the notice was consumed.

Exactly-once delivery cannot be inferred from a claim record: the crash boundary between handing the envelope to the model and recording completion is irreducible.

**Recommendation.** Define precedence so one episode produces at most one note in an envelope—normally rule (a), with rule (b) only filling the no-overlap case. Define durable consumption in terms of an acknowledged completed wake, or weaken the guarantee to honest at-least-once delivery across retries. Persist the episode IDs assigned to a claim so boot recovery can reproduce them. Test first-after-loan events that overlap, fail during context resolution, crash before exchange, and crash after exchange but before completion.

### 3. Context-ceiling inheritance lacks substrate binding, precedence, and persistence

**Defect.** Round-one S6 is resolved only in prose. The running backend is mutable between wakes—`_call_natural()` snapshots `self._context_limit` at call entry—so lazy construction is unnecessary. The remaining rules are incomplete:

- “Last context_limit in the log” is not restricted to a launch with the same resolved model, provider, and base URL. An explicit substrate change during an unavailable discovery can therefore inherit the previous substrate’s ceiling.
- “Rediscover and apply” can overwrite an explicit `--context-limit`, contradicting the existing explicit-over-discovered precedence.
- Updating only `OpenAITasteBackend._context_limit` leaves `OpenTasteSession._launch_config` stale; subsequent cycle records and the next reboot inherit the old value.
- If `/models` succeeds but `/props` fails, the design does not say whether a door with only a stale or absent inherited value may claim. A brand-new local door could still run with no managed ceiling.
- The existing parser accepts zero and negative context limits.

**Recommendation.** Inherit only a positive, previously validated limit from a launch whose substrate identity matches the resolved launch. Preserve explicit limits across readiness probes. On successful discovery, update both the backend and the session launch record, including source, before any claim. If a participating local door has neither an explicit limit nor a matching inherited limit, or fresh discovery fails where the unit’s context may have changed, remain warming rather than claim. Add tests for explicit precedence, substrate change while offline, first boot without history, rediscovery failure, persistence of a changed limit, and invalid values.

### 4. Quarantine episodes have no usable durable identity

**Defect.** Revision 2 says `_rest_episodes()` groups both `substrate_lent` and `substrate_lease_unreadable` by `detail.lease_id`, and the return record carries `{lease_id}`. A malformed lease may have no parseable or valid lease ID—the reason it is quarantined. “Ledger quarantine once” is likewise undefined without an identity for distinguishing repeated observations of the same bad file from a newly corrupted state. Restart de-duplication, return closure, and rule (b) therefore cannot be implemented as described for quarantine.

**Recommendation.** Give each quarantined state a stable `quarantine_id`, derived from or linked to its ledger action and a digest of the preserved bad file. Carry it in resting and returning records, use it for de-duplication and episode grouping, and create a new identity if the quarantined bytes change. Do not overload `lease_id` when lease validation failed.

### 5. The holder acknowledgment remains a caller convention rather than the promised handoff

**Defect.** Round-one B4 is resolved only in prose for the normal path. `ayllu-gpu lease` returns the lease ID before the separate `wait` command runs, so nothing prevents a caller from omitting `wait` and starting GPU work while llama-server remains active. This also conflicts with invariant 4’s statement that a holder leases with one command: the registered sequence requires both `lease` and `wait`. Mutual trust may justify a cooperative protocol, but it does not justify the stronger statement that the holder “cannot proceed” before acknowledgment.

**Recommendation.** Either make acknowledged acquisition the default atomic user-facing operation—such as a `with-lease` command that acquires, waits, runs the workload, and traps release—or weaken the invariant to state that cooperating callers must wait and that omission is an acknowledged operational hazard. Tests should exercise the actual launcher wrapper, not only the two primitives independently.

## Minor

### 1. Automatic participation still conflates loopback with the RTX 4090

**Defect.** Round-one M3 is resolved only in prose. Revision 2 adds `off`, explicit paths, host parsing, and configuration-based constitution selection, but retains automatic participation for every OpenAI-compatible loopback endpoint. Such an endpoint may be CPU-backed or use a different GPU, so the default can stop `hamutay-llama-server` and suppress unrelated wakes based on the wrong resource.

**Recommendation.** Configure the qwen unit explicitly with the 4090 lease path or resource identity. Keep loopback inference as an opt-in convenience rather than the default proof of resource ownership.

### 2. The stated systemd observations do not match `is-active`

**Defect.** The design says the heartbeat handles an `auto-restart` state while recording “systemctl is-active output.” `auto-restart` is a service substate, not the normal `is-active` ActiveState result. The specification also does not say whether an ok `server_stop` outcome—and therefore successful `ayllu-gpu wait`—requires an observed `inactive`/`failed` state or merely a zero exit from `systemctl stop`.

**Recommendation.** Read and record both `ActiveState` and `SubState` with `systemctl show`, and define stop success as a completed command plus an accepted inactive state. Any active, activating, deactivating, or restart-pending observation must keep `wait` blocked and cause reconciliation to retry.

### 3. Readiness observations need transition-level de-duplication

**Defect.** The FREE path probes on every step, and the return sequence says a successful probe ledgers `server_ready`. Without a remembered start generation or previous readiness state, an idle free door can append a `server_ready` intent/outcome pair every 30 seconds. Conversely, tying readiness only to process active state can miss a reload within the same systemd activation.

**Recommendation.** Bind `server_ready` to a particular `server_start` action or observed service generation and append it once per not-ready-to-ready transition. Record later probe failures as state changes rather than silently treating the previous ready row as current.

Verdict: **do not implement yet**; the claim/start linearization, safe force-stop authority, crash reconciliation, and deployed-unit migration remain capable of violating the design’s core invariants.