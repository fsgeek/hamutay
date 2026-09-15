# The GPU lease — design review, round three

Date: 2026-09-15. Reviewer: Codex (codex exec, read-only sandbox), before implementation. Round 3 of 4; dispositions are in the design document (revision 4). Reviewed revision 3 at commit a1ba939 against both prior reviews, the running event/heartbeat/session code, the deployed units, the qwen records, and local systemd 249 semantics.

## Resolved from round two

R2 B1 — Partly resolved by mechanism: holding `4090.lock` across `EventStore.claim_next_pending()` establishes the correct lease-lock → event-store-lock order; participation discovery still permits bypass (Blocking 1).

R2 B2 — Resolved only in prose: the process-lifetime lock is the right exclusion primitive, but the proposed holder does not reliably lock the same inode and does not preserve the pre-stop resident record (Blocking 2).

R2 B3 — Resolved only in prose: revision 3 adds a state machine, but its observations cannot reconcile every declared action or durably represent indeterminate quarantine (Blocking 3).

R2 B4 — Resolved by mechanism: an explicit disable migration exists; its installation and verification assertions are incorrect for the revised static unit (Significant 4).

R2 S1 — Partly resolved by mechanism: reconciliation precedes `HeartbeatLoop.boot()` and supplies ledger-derived closure; the new latest-status rule conflicts with `_transition`’s in-memory de-duplication (Significant 1).

R2 S2 — Resolved by mechanism: rule (a) has per-episode precedence, rule (b) is consumed only by completion, and the guarantee is honestly weakened to at-least-once.

R2 S3 — Resolved only in prose: substrate matching and explicit precedence are stated, but rediscovery updates the wrong runtime object and is not durably recorded (Significant 2).

R2 S4 — Partly resolved by mechanism: `episode_id` generalizes lease and quarantine identity, but indeterminate and repeated quarantine states remain unrepresentable (Blocking 3).

R2 S5 — Resolved by mechanism: `ayllu-gpu run` makes wait-before-work the registered path; its renewal supervision introduces a new safety defect (Blocking 4).

R2 M1 — Resolved by mechanism: participation is explicit configuration, with no loopback inference.

R2 M2 — Resolved by mechanism: `ActiveState`, `SubState`, and `InvocationID` replace `is-active`, and stop success requires an inactive/failed observation; the already-inactive case is newly broken (Significant 3).

R2 M3 — Resolved only in prose: `InvocationID` is the correct generation, but the remembered readiness state is not reconstructed durably and “once per invocation” conflicts with transition recording (Minor 1).

## Blocking

### 1. The gate is atomic once selected, but qwen participation is still not authoritative

**Defect.** `LeaseGate.claim()` now has the correct ownership shape: it can hold `4090.lock` while `EventStore.claim_next_pending()` enters `EventStore._locked()`, appends `running`, and returns. Threading that object through `run_next_event()`, `run_pending_events()`, and `step_pending_events()` also closes the between-batch-claims race.

The bypass has moved to gate selection. Revision 3 says `step_pending_events`, `run-one`—actually `run-next` in the running CLI—and `run-all` discover participation from the latest logged launch configuration. The session file records this under `record["launch"]`, not `launch_config`, and only when `OpenTasteSession._log_entry()` writes a cycle. Starting or restarting the heartbeat writes no launch record. Immediately after migration, all existing qwen records lack `gpu_lease`, and the new setting may remain unrecorded until the next successful or failed exchange. A manual runner in that interval cannot infer that the store is lease-participating. More fundamentally, `run_next_event(..., claim_gate=None)` remains a public unguarded claim path, so any library caller can claim the qwen store directly.

That restores the forbidden sequence: live lease → unguarded `running` append → connection failure against the stopped server → terminal `failed`.

**Recommendation.** Bind lease participation outside cycle history: use explicit CLI/environment configuration shared with the qwen unit, or a durable per-door configuration record written before any claim is possible. An absent `gpu_lease` field in a legacy qwen log must not mean `off`. Make lease-bound stores refuse unguarded `run_next_event`, `run_pending_events`, and `step_pending_events` calls rather than relying on callers to remember a gate. Test a legacy log, a fresh post-migration boot before its first wake, `run-next`, `run-all`, and a direct library call.

### 2. `force-stop` may lock the wrong file and still violates the pre-stop record invariant

**Defect.** The running heartbeat locks `args.lock_path` or `event_log_path + ".heartbeat.lock"`. With the deployed relative log path, that resolves relative to the heartbeat unit’s `WorkingDirectory`. Revision 3 instead gives `ayllu-gpu` the relative literal `community/qwen/session.jsonl.events.jsonl.heartbeat.lock`. The registered caller is Yupi, so invoking the installed command from Yupi’s repository can create and acquire a different inode. A custom heartbeat `--lock-path` has the same problem. `force-stop` would then “prove” the heartbeat absent and kill llama-server during a live exchange.

Even when it acquires the correct lock, `force-stop` stops the server without first appending `resting/substrate_lent` to the resident’s store. Boot may reconstruct the row later, using the post-stop outcome time, but a decommissioned heartbeat may never boot, and invariant 3 explicitly requires the record before the stop.

**Recommendation.** Define one canonical absolute heartbeat-lock path and event-store path in shared configuration consumed by both the unit and `ayllu-gpu`; never derive the exclusion lock from the caller’s working directory. While holding `4090.lock` and that heartbeat lock, `force-stop` should append the episode’s rest record before issuing `systemctl stop`, following the declared GPU-lock → event-store-lock order. Boot reconstruction should cover only a crash after that append. Test different working directories, an overridden heartbeat lock, automatic heartbeat restart during the override, and a force-stop with no later heartbeat boot.

### 3. The action state machine cannot reconcile all of its declared actions

**Defect.** Three holes remain.

First, `renew` preserves `lease_id`, while its reconciliation test accepts any same-ID file whose `expires_at` is at least the intent’s value. If a long existing lease is renewed to a shorter TTL and the process dies before writing, the old file satisfies that test. Changes to `expected_until` are ignored entirely. The ledger can therefore report a renewal that never occurred.

Second, `server_ready` and `server_unready` are declared action values but have no rows in the dangling-intent table. A crash after either intent has no specified resolution.

Third, an indeterminate action is said to create `quarantine_id = sha256(action_id)[:16]`, but no durable state carries it. `4090.lease` accepts only a valid lease or malformed bytes; an absent file reads FREE, while a malformed marker derives its identity from its bytes, not the action ID. A later process therefore cannot reconstruct the action-derived quarantine reliably. Creating that quarantine would itself be another mutation requiring an intent, producing an undefined recursive boundary. Digest-only quarantine also reuses the same episode identity if identical bad bytes are cleared and later reintroduced.

**Recommendation.** Add a lease generation or mutation ID stored atomically in the lease file and require exact agreement with every intended mutable field when reconciling renewals. Either define observable reconciliation for readiness actions or represent readiness as observation facts rather than intent/outcome mutations. Give quarantine a valid durable representation—such as a separate quarantine file or an explicit tagged state object—with an occurrence identity, reason, source action, and observed digest. Specify the one-way transition into it without recursively requiring another unresolved action.

### 4. `ayllu-gpu run` can outlive its lease and collide with the resident

**Defect.** The registered path depends on a background renewal every `ttl/2`, but only the happy path is specified. If renewal fails, the wrapper is killed, the host is suspended across expiry, or a shell child survives its parent, the workload may continue after `expires_at`. The next heartbeat then correctly sees FREE and starts llama-server on the same card. This is not the declared hazard of a caller using the raw primitives incorrectly; it is a failure mode of the registered one-command mechanism itself, especially for the stated 30–40-hour workloads.

An EXIT trap does not handle `SIGKILL`, and releasing merely because the wrapper is exiting is unsafe until the workload and all GPU-using descendants are known to be gone.

**Recommendation.** Specify `run` as a real supervisor. Couple the command’s process group or systemd scope to lease validity; renew with enough safety margin; on renewal failure, terminate and reap the entire workload before the current lease expires; and release only after the workload is gone. Define behavior across signals, parent death, suspend/resume, and failed release. Test renewal failure, killed wrapper, surviving descendants, and resume after wall-clock expiry.

## Significant

### 1. Latest-status de-duplication is incompatible with `HeartbeatLoop._transition`

**Defect.** Revision 3 says substrate rest is de-duplicated by the latest durable `(status, reason, episode_id)`. The running `_transition()` instead suppresses solely by the process-local `(status, reason)` tuple.

Calling `_transition()` for the new records can swallow a second lease with a different episode ID when no FREE heartbeat step occurred between two leases. Appending directly avoids that check but leaves `_last_transition` stale. A later quiet transition can then be suppressed because the process remembers the pre-loan quiet, leaving the durable latest status at `waking/substrate_returning`. More seriously, if a budget rest was active before the loan, `_resting_day` and `_last_transition` can still say that today’s budget rest is current, suppressing the required second budget segment after return.

**Recommendation.** Replace the split de-duplication mechanisms with one transition API whose durable identity includes reason-specific episode identity—`episode_id` for substrate states and day for budget states—and hydrate or verify its state from the store. Boot reconciliation and guard transitions must update that same mechanism. Test consecutive leases with no observed FREE step, quiet → lease → quiet, budget → lease → budget, and restart within each sequence.

### 2. Context rediscovery updates a field the running backend never reads

**Defect.** Revision 3 says readiness rediscovery sets `session._context_limit`. `OpenTasteSession` has no operative `_context_limit`; `OpenAITasteBackend._call_natural()` snapshots `self._context_limit` from the backend at call entry. The rediscovered ceiling can therefore be printed and copied into `session._launch_config` while the actual wake still uses the inherited ceiling.

The persistence claim is also too strong. `_launch_config` is embedded when `_log_entry()` writes an exchange record; readiness itself writes no session record. A rediscovered change can be lost before the next exchange. Finally, the warming rule blocks only when there is no inherited limit. After a new server `InvocationID`, failed `/props` discovery may therefore authorize a claim using a matching-but-stale inherited value even though the unit’s `-c` setting may have changed.

**Recommendation.** Add one explicit backend/session setter that atomically updates `OpenAITasteBackend._context_limit` and the launch metadata. Persist a substrate/context observation immediately at readiness in a form the next boot actually reads. Inheritance may construct the process while the server is unavailable, but after every new server invocation a participating door without an explicit limit should not claim until fresh discovery succeeds. Test that the backend—not merely session metadata—uses a changed ceiling on the next call.

### 3. An already-stopped server can never acknowledge a normal lease

**Defect.** `ayllu-gpu wait` requires an ok `server_stop` outcome for its episode. The rest sequence emits `server_stop` only when `ActiveState` is not `inactive` or `failed`. If the server was already stopped, had failed before acquisition, or remains down between consecutive leases, the heartbeat records the rest and performs no stop action. The card is available, but `wait` can only time out, so the registered `run` command cannot use it.

**Recommendation.** Make “stopped for this episode” an explicit acknowledgment independent of whether a stop mutation was necessary. Either ledger an idempotent ensure-stopped action with `detail.already_inactive=true`, or define a separate acknowledgment row tied to the episode and an under-lock inactive/failed observation. `wait` should consume that row. Test acquisition while inactive, while failed, and immediately after a prior lease before server restart.

### 4. The migration’s systemd assertions cannot pass as written

**Defect.** Removing `[Install]` makes the revised service `static`, not `disabled`; on the installed systemd version, those are distinct `is-enabled` results. Thus the prescribed final assertion of exactly `disabled` conflicts with the intended unit. `disable` is still the correct migration operation—`mask` would prevent the heartbeat’s legitimate explicit starts—but the script must verify absence of enablement symlinks, not demand the wrong label.

The ordered steps also install only the heartbeat drop-in; they never explicitly copy the revised server unit before `daemon-reload`. A git pull changes the repository copy, not `~/.config/systemd/user/hamutay-llama-server.service`. `WantedBy` and `RequiredBy` are valid inverse runtime properties, but they describe the loaded dependency graph and do not prove that no dormant installed unit file can pull the server in. The state-directory step also ignores `AYLLU_STATE_DIR`.

**Recommendation.** Explicitly install both revised unit files, disable the old enablement while its `[Install]` metadata is still available, reload, and accept the expected final `static` state while rejecting `enabled` and `enabled-runtime`. Verify the old target symlink is absent. Use the known qwen unit’s `Requires`/`Wants` plus inverse properties as runtime checks, and narrow or strengthen the “any unit” claim with an installed-unit-file/symlink inspection. Resolve the migration directory from the same `AYLLU_STATE_DIR` rule used by the commands.

## Minor

### 1. Readiness de-duplication is neither durable nor internally consistent

**Defect.** The guard’s “remembered ready `InvocationID`” is process memory. A heartbeat restart while the same server invocation remains healthy forgets it and emits another `server_ready`. Conversely, revision 3 says both “once per InvocationID” and once per not-ready → ready transition. A transient probe failure followed by recovery within one invocation must either produce another ready transition or violate one of those statements.

**Recommendation.** Reconstruct the latest readiness state and invocation from the ledger at boot. Define the contract as one fact per readiness edge, keyed by `InvocationID`; the same invocation may then have ready → unready → ready, while a heartbeat restart without an edge emits nothing.

### 2. `lease_blocked` has no batch or scheduler semantics

**Defect.** Revision 3 says `run_pending_events()` stops on `lease_blocked`, but the running batch counts every result other than `none` as `ran`, while `step_pending_events()` derives its stop reason solely from failures, limits, and remaining queue state. A blocked direct runner can therefore report that it ran work and return `runnable_pending` or `limit_reached` instead of the reason it stopped.

**Recommendation.** Specify `lease_blocked` as non-running and non-terminal throughout the batch summary, with an explicit scheduler stop reason and zero wake count. Test a lease arriving between two unbudgeted claims and a direct CLI invocation blocked before its first claim.

Verdict: **do not implement revision 3 yet**; the remaining gate and force-stop bypasses, incomplete crash reconciliation, and unsupervised lease expiry can still fail resident events or put two workloads on the 4090.