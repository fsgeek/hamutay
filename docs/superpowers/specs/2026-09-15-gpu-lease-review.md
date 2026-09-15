# The GPU lease — design review

Date: 2026-09-15. Reviewer: Codex (codex exec, read-only sandbox), before implementation. Reviewed the design at commit 751531b. Round 1 of 2; dispositions are in the design document (revision 2).

Reviewed the proposed design against the running heartbeat and event-store code, deployed systemd units and checkpoint script, founding invariants, wake-budget mechanism, local-substrate design, community runbook, and existing heartbeat test shapes.

## Blocking

### 1. Lease acquisition is not atomic with wake claiming or steward action

**Defect.** `HeartbeatLoop.step()` would read the lease before calling `EventStore.next_pending()`, but the authoritative claim happens later inside `events.py::run_next_event` through `EventStore.claim_next_pending()`. The lease lock and event-store lock are unrelated. A heartbeat can read “free,” a holder can create a lease, the steward can observe no `running` event, and then the heartbeat can append `running` just as the steward stops the server. The reverse steward/holder race also exists: reconcile can decide to start the server while no lease exists, then a holder can acquire one before `systemctl start`. Under `--no-daily-budget`, `run_pending_events` may claim up to ten events after the single lease check, so a lease arriving between wakes is ignored until the batch ends. This violates the live-lease-wins invariant.

**Recommendation.** Define one synchronization protocol shared by lease, steward, and event claiming. Establish a lock order, such as lease lock before event-store lock, and make every `claim_next_pending` operation recheck lease liveness while that coordination lock is held. The steward must likewise revalidate the same lease generation immediately before every start or stop action. Add deterministic barrier tests for lease-before-claim, claim-before-lease, release-before-start, and a lease arriving between two unbudgeted batch claims.

### 2. The forced drain does not invoke boot recovery; it terminally fails the event

**Defect.** The design says stopping the server after `DRAIN_MAX` invokes the crash-only contract and boot recovery re-pends the orphan. With the proposed `Wants=`, however, the heartbeat remains alive. Killing llama-server during `session.exchange()` produces a connection or transport exception; `events.py::run_next_event` catches it and calls `EventStore.append_failed()`. `failed` is terminal, and `heartbeat.py::recover_orphaned_running()` only re-pends an event whose latest status remains `running`, during a heartbeat boot. The loan therefore manufactures exactly the failed event forbidden by invariant 2, and the wake is not retried.

**Recommendation.** Do not force-stop the server while the heartbeat remains inside a wake. Either remove the forced cutoff, define a new recoverable interruption lifecycle, or have the steward explicitly stop the heartbeat first, wait for it to exit with the event still `running`, stop the server, and restart the heartbeat so normal boot recovery re-pends it. Specify the exact sequence and test that the resulting history is `pending → running → recovered pending`, never `failed`.

### 3. Replacing `Requires=` with `Wants=` still lets actors other than the steward start the server

**Defect.** `Wants=hamutay-llama-server.service` causes systemd to start the server whenever `hamutay-heartbeat@qwen` is activated. Independently, `deploy/hamutay-llama-server.service` is enabled through `WantedBy=default.target`, and both its comments and `community/README.md` instruct operators to enable it. Thus a heartbeat restart or user-manager startup can load the 4090 during a live lease without any steward decision. `Restart=always` does correctly exclude a completed explicit `systemctl stop`, but an already pending automatic restart can also escape the steward’s binary active/inactive table.

**Recommendation.** Give the qwen heartbeat only `After=`, not `Wants=` or `Requires=`, and stop enabling the server under `default.target`. Enable only the steward timer; it should bring the server up when reconciliation says the resource is free. Define behavior for `activating`, `deactivating`, `failed`, and `auto-restart`, not just active/inactive, and issue an explicit stop under a live lease whenever a restart job could still launch the process.

### 4. A loan can complete without any record in the resident’s store

**Defect.** The steward stops the server as soon as it sees a live lease and no running event; it does not wait for `HeartbeatLoop._rest_if_substrate_lent()` to append `resting/substrate_lent`. With two independent 30-second polls, the steward can stop immediately, the holder can finish and release a short job, and the server can restart before the heartbeat ever observes the lease. A heartbeat outage spanning the lease loses the record for the same reason. `_transition` de-duplication only suppresses duplicate observations; it cannot recover an episode never observed. This contradicts invariant 3 and the claim that every loan is present in the door’s own store.

**Recommendation.** Make a matching heartbeat acknowledgment part of handoff: the steward must not stop the server, and `ayllu-gpu wait` must not succeed, until the event store contains `resting/substrate_lent` for that `lease_id`. As defense in depth, define how heartbeat boot reconstructs missed episodes from the lease ledger. Specify what happens when acknowledgment cannot be obtained and distinguish an acquired-but-never-activated lease from a completed card loan.

### 5. Malformed or unreadable lease state fails in the unsafe direction

**Defect.** Both the heartbeat and steward treat an unreadable or malformed lease as no lease. The heartbeat may then claim work and the steward may start llama-server while a holder is actively using the GPU. Moving the file aside destroys the only active coordination state before anyone establishes that the card is free. This contradicts “a live lease always wins” at precisely the point where liveness cannot be determined.

**Recommendation.** Fail closed. A malformed, unreadable, or schema-invalid lease must quarantine the resource: do not claim a local wake, start the server, or grant another lease. Preserve the bad file and emit a durable error record. Recovery should require a validated reconstruction or an explicit force operation that records who overrode the uncertainty.

### 6. The “every transition is a record” guarantee has no crash-consistent implementation

**Defect.** Updating `4090.lease`, appending `4090.ledger.jsonl`, and invoking systemd are separate state changes. A crash can leave a live lease without its `lease` row, a deleted lease without `release`, a stopped server without `server_stop`, or a ledger row claiming an action whose external change never occurred. On the next tick, rows such as live-lease/server-inactive map to “nothing,” so the missing transition cannot necessarily be inferred. The ledger schema also has no outcome, error, observed state, or stable action identifier despite error handling requiring failed actions to be recorded.

**Recommendation.** Specify a recoverable transition protocol with stable action IDs, intent and outcome records, ordering, and reconciliation rules for every crash boundary. Reconcile ledger state against both the lease file and systemd state and append explicit recovered/inferred outcomes where necessary. Define whether `server_start` means requested, process spawned, or ready; those are different facts with the current `Type=simple` service.

## Significant

### 1. “Same holder only” cannot be enforced by the proposed CLI

**Defect.** `renew` and `release` take neither `--holder` nor a lease capability. Reading the holder string from the lease merely tells the caller what value to claim; any process under the same Unix account can renew or release another project’s lease. `--force` has no defined authorization or audit distinction. A mistaken foreign release can cause the steward to start llama-server on top of the real holder.

**Recommendation.** Return a lease capability—at minimum the unpredictable `lease_id`—and require it for renew and release, with the caller also supplying the expected holder for useful diagnostics. Define and durably record forced overrides. If the design intentionally provides accountability without ownership enforcement, remove the “same holder only” claim and state that all local callers are mutually trusted.

### 2. The drain reader is underspecified and unsafe against concurrent appends

**Defect.** “The latest status for any event is `running`” must mean the latest append-order `event_status` for each `event_id`. Searching for any historical running row waits forever; examining only the last global status can miss a running event; including `heartbeat_status` rows corrupts the reduction. Unlike `EventStore.latest_by_event_id()`, a bash/jq reader will not automatically use the event-store flock, and `EventStore._read_records_unlocked()` itself assumes complete JSON lines. Reading during an append can therefore fail or produce an incomplete view that causes an unsafe stop. The service’s working directory or absolute qwen store path is also not specified.

**Recommendation.** Define the drain operation exactly as a locked snapshot followed by append-order reduction of `record_type == "event_status"` keyed by non-null `event_id`. Use the existing `.events.jsonl.lock`, treat malformed or incomplete snapshots as “possibly running,” and configure an absolute event-log path in the steward service. Define whether `DRAIN_MAX` begins at lease `since`, first steward observation, or a durable drain-request record.

### 3. The existing envelope path does not tell the next wake after every loan

**Defect.** `events.py::operational_notes_for_event()` includes a rest only when its interval intersects the event’s pending interval. `tests/test_wake_budget.py::test_no_envelope_note_for_a_rest_that_ended_before_the_event_existed` explicitly enforces that an event created after a rest receives no note. If no event waited during a GPU loan, the resident’s next later wake is therefore not told about it, contradicting invariant 3, the constitution sentence, and the declared loss saying residents are told afterward. The proposed open-episode test is not representative: a correct lease-aware heartbeat cannot claim an event while a live lease keeps the episode open.

**Recommendation.** Choose one contract explicitly. If only events that actually waited are told, narrow all “next wake” language accordingly. If the first wake after every loan must be told, add a separate unconsumed-lease-note rule independent of the event’s `created_at`, with durable identity-based de-duplication so exactly one later wake carries it. Test the no-pending-during-loan case end to end through `run_next_event`.

### 4. “Server warming is not a rest” is inconsistent with the stored episode

**Defect.** `_rest_episodes()` ends a rest at the next non-resting heartbeat status. The design says a failed readiness probe sleeps without transitioning, so the last durable status remains `resting/substrate_lent` throughout server startup. The eventual envelope consequently counts warming time as part of the substrate-lent episode, despite the lease already having ended and the design explicitly saying warming is not a rest. If ingress lands after `HeartbeatLoop.step()`’s `next_pending()` precheck, the batch can also claim before an `active` transition closes that episode.

**Recommendation.** Append an explicit non-rest transition when the lease ends—for example `waking/substrate_returning`—and decide whether warming delay gets its own operational note. Define probe timeout, accepted HTTP statuses, and the return state from a warming step. Ensure the authoritative claim path closes or snapshots the episode before building the envelope, including the ingress-during-step race.

### 5. Budget rest and lease rest cannot be represented as specified when they overlap

**Defect.** The heartbeat status stream carries one current reason. If a daily-budget rest begins, a lease then starts, and the lease ends before midnight, the lease record closes the budget episode and the resumed budget record later creates another segment. The existing `_rest_episodes()` only merges adjacent same-day budget records or a `waking/boot` bridge; it cannot express that the budget rest continued throughout the loan. The design does not say whether the envelope should show one budget episode plus one overlapping lease episode, three sequential segments, or suppress the lower-priority reason. Two implementers will produce different records and wait durations.

**Recommendation.** Define overlap semantics before extending `_rest_episodes`: whether reasons are independent intervals, strictly prioritized states, or one primary reason with secondary causes. Specify expected records and ordered envelope notes for budget-before-lease, lease-before-budget, midnight during a lease, and restart during both. If independent intervals are required, a single transition stream needs an identity-based reducer rather than the current sequential scanner.

### 6. A heartbeat restart during a lease loses the local context ceiling

**Defect.** In `heartbeat.py::main`, `resolve_context_limit()` runs before the backend, session, loop, boot recovery, or proposed lease check. `After=` only orders process startup; `hamutay-llama-server.service` is `Type=simple` and is considered started before its model is ready. If the heartbeat starts while the server is stopped for a lease or still loading, discovery returns `None`, and `OpenAITasteBackend` runs for the life of that process without the 65,536-token ceiling. The later `/models` probe cannot repair that configuration. This reintroduces the exact over-context failure documented in the local-substrate design.

**Recommendation.** Preserve and inherit the last validated local context limit when discovery is temporarily unavailable, or defer final backend/session construction until the lease is absent and readiness discovery succeeds. Test heartbeat boot with a live lease, release plus warm-up, and the first post-release wake retaining the recorded 65,536-token limit.

### 7. The timer and restart claims do not match systemd semantics

**Defect.** “Every 30 s” does not define a timer: systemd timer accuracy defaults to one minute unless `AccuracySec` is tightened, and a monotonic `OnUnitActiveSec` timer needs a separate first activation. `Persistent=` only supplies catch-up semantics for calendar timers, so it cannot substitute for `OnStartupSec` on a monotonic design. Separately, `Restart=always` retries llama-server internally; the steward does not issue or ledger “each attempt,” and `systemctl start` on a `Type=simple` unit returns before the 22 GB model is ready.

**Recommendation.** Specify the actual `[Timer]` contract, such as immediate `OnStartupSec`, a 30-second interval measured from service completion or activation, and an explicit small `AccuracySec`. State missed-tick behavior. Treat `server_start` as a requested systemd transition unless readiness is separately observed and recorded; do not claim that steward ledger rows enumerate systemd’s internal restart attempts.

### 8. The constitution sentence introduces a social and consent prior

**Defect.** The founding spec permits operational facts but forbids new cognitive priors. “Another member of the house,” “lent,” and “borrowed” tell the resident how to construe the other workload and frame a non-veto allocation as a consensual social loan. The fields are also self-declared holder and purpose strings, not verified facts about “who” and “why.” Saying the sentence contains no advice does not make that framing operationally neutral.

**Recommendation.** Use substrate-neutral wording, such as: “The heartbeat may pause while the local GPU is allocated to another workload; its lease record carries a declared holder and purpose, pending events remain pending, and affected wakes receive an operational note.” Avoid “member,” “house,” “lent,” “borrowed,” ownership language, or any implication that the resident consented.

### 9. The checkpoint change needs an explicit external-ledger path and locking rule

**Defect.** `deploy/checkpoint-community-log.sh` discovers only `community/*/` directories containing local `*.jsonl` files. An external `${AYLLU_STATE_DIR}/gpu/4090.ledger.jsonl` will never enter that loop, and `community/gpu/` containing only `CHECKPOINTS.txt` will not be discovered as a door. The design does not say whether the external ledger is copied into the repository, merely hashed, skipped when absent, or snapshotted under `4090.lock`. Those choices have different privacy and valid-prefix consequences.

**Recommendation.** Specify that the script resolves the exact external ledger path, acquires the lease/ledger lock while taking a byte snapshot, and appends only its filename, digest, and byte count to `community/gpu/CHECKPOINTS.txt`; the ledger contents should remain outside git. Define absent-ledger behavior, directory creation, `AYLLU_STATE_DIR` resolution, and how the new checkpoint file joins the existing signed commit.

## Minor

### 1. Lease liveness and renewal semantics are not defined consistently across Bash and Python

**Defect.** The holder and steward are plain Bash/jq while the heartbeat and proposed tests imply Python parsing. “Past `expires_at`” leaves the equality boundary, required timezone, fractional seconds, invalid types, zero or negative TTLs, and maximum enforcement unspecified. Same-holder re-leasing is called a renewal but the design does not say whether it preserves `lease_id`, `since`, purpose, and `expected_until`. The phrase “canonical JSON” likewise has no defined serialization contract.

**Recommendation.** Publish shared conformance fixtures and exact validation rules: timezone-bearing UTC instants, `now >= expires_at` expiry, accepted TTL grammar and bounds, immutable fields for a lease ID, and precise same-holder re-lease behavior. Define canonicalization only if byte identity matters; otherwise require a valid normalized JSON object rather than “canonical JSON.”

### 2. `expected_until` and `resumes_at` overstate what is known

**Defect.** `expected_until` is declared informational, yet heartbeat detail sets `resumes_at` to it in preference to the enforceable `expires_at`. It may be later than expiry, earlier than an eventual renewal, or earlier than server reload completion. Renewals with the same `lease_id` are de-duplicated, so the heartbeat record may retain stale timing. `_rest_episodes()` currently keeps the first record’s detail when merging an episode.

**Recommendation.** Keep `expected_until` labelled as the holder’s estimate and keep `expires_at` as the enforceable deadline; do not call either a guaranteed resume time. Define whether renewal appends a heartbeat update and whether episode rendering uses first, latest, or merged detail.

### 3. Automatic lease-file selection is too broad and lacks an explicit off switch

**Defect.** `provider == "openai"` plus a loopback `base_url` does not prove that the endpoint uses the house’s 4090; it could be CPU-backed or use another GPU. The design also does not define loopback parsing, whether `${AYLLU_STATE_DIR}` replaces the ayllu root or GPU directory, or how to disable auto-selection. “Only for a door with a lease file” is ambiguous because the file is absent whenever the configured resource is free.

**Recommendation.** Bind the qwen service explicitly to resource `4090` or an explicit lease path, while preserving a no-lease setting. Base constitution selection on configured lease participation, not current file existence. Define environment-path expansion and accepted loopback hosts if autodetection remains as a convenience.

### 4. The test inventory omits the existing compatibility surfaces and decisive races

**Defect.** `tests/test_heartbeat.py` and `tests/test_wake_budget.py` construct `HeartbeatLoop` through shared helpers and assert the current parser and one-argument `build_constitution()` contracts. The proposed files do not mention preserving no-lease behavior, updating those helpers, or exercising the real `run_next_event` claim/envelope ordering. A fake `systemctl` harness alone cannot detect dependency pull-in, timer accuracy, or `Restart=always` behavior.

**Recommendation.** Add compatibility tests for hosted doors and explicitly disabled leasing; resolved launch/base-URL lease selection; boot with a live lease; ingress between `next_pending` and claim; lease arrival between batch claims; short loans; malformed state; restart-continuation and overlapping rests; forced-drain lifecycle; context-limit retention; and checkpointing the external ledger. Validate unit files with systemd’s unit verifier and assert dependency directives directly.

Verdict: **do not implement yet**; the lease/claim handshake, forced-drain lifecycle, systemd ownership, durable loan acknowledgment, fail-closed behavior, and crash-consistent ledger must be specified before the design can preserve its own invariants.