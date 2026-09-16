# The assembly — design review, round one

Date: 2026-09-15. Reviewer: Codex, before implementation. Reviewed revision 1 at commit `8191817` against the running heartbeat, event-store, tool, session-commit, GPU-lease, quiet-declaration, checkpoint, and community code.

Verdict: **do not implement revision 1 yet.** The basic ledger model is viable, but the current consent rule can discard objections, the proposed position join is not crash-safe, and closing delivery is fenced against its own recovery.

## Blocking

### 1. `consent-v0` can terminate or later overrule a dissent

**Mechanism.** The rule checks quorum before objections, then creates each extension as a new question whose tally contains only that round’s positions.

**Why it fails.**

- One dissent and three silent doors gives `|S| = 1`, so the result is immediately `unresolved`, not `extended`. This directly contradicts Invariant 3: “A dissent extends the question.”
- A dissent in round 1 can disappear in round 2. If the dissenter is then quiet while two other doors assent, round 2 is `assented`. The earlier dissent remains somewhere in the parent record but no longer constrains the decision and need not appear in the final closing event. That is a dissent losing through silence, contrary to “it never loses.”
- `defer` has the same defect. A request can reopen one round and then be silently discarded without being answered or withdrawn.

**Smallest change.** Check active `dissent`/`defer` before quorum. Carry each member’s latest stance across the entire question lineage until that member explicitly replaces it; a child round adds or replaces positions rather than resetting them. The final closing and delivered closing must include the lineage’s positions and identify the active position for each member. A persistent objection then produces `unresolved` at round 3, while an explicitly replaced objection can clear.

### 2. A shared `record_id` does not make a position part of a completed wake

**Mechanism.** The design places a buffered position at “cycle commit beside `quiet_declaration`.” In the running path, `OpenTasteSession._exchange_impl()` first writes the session record, then appends scheduled events and the quiet declaration to the event store, returns, and only afterward does `events.run_next_event()` append the `completed` status through `EventStore.append_completed_atomic()`.

**Why it fails.** The assembly ledger is a third append domain. A crash after the position append but before the event’s `completed` status leaves a position from a wake that never completed. Unlike `events.quiet_declaration_for_latest_wake()`, the proposed close pass performs no completion join; it tallies by `created_at` alone. The position can therefore decide a question even though boot recovery will re-pend the source event.

The opposite race is also unresolved: another heartbeat can close the question while a delivered event is `running`. The position then lands after the immutable closing. The design calls it a `position`, but it cannot be carried by the already-written closing, contradicting Invariant 2. Its tool call also returned success even though no tally can accept it.

**Smallest change.** Give positions the same authority rule as quiet declarations: a position is tally-eligible only when its `record_id` joins a `completed.result_record_id` in that member’s event store. Use an assembly-ledger `accepted_at` assigned under the ledger lock, not a pre-commit tool timestamp, as the deadline field. Do not close while the question’s delivery is actively `running` without an explicit, documented cutoff policy. An attempt that commits after a closing must be a distinct `late_position_attempt`, not a position silently omitted from the closing.

### 3. The closing fence permanently loses closing deliveries, and extension is not crash-idempotent

**Mechanism.** `hamutay.assembly.close_due()` writes the child question, then the parent closing, then appends events to four independent `EventStore`s. The presence of the closing is the idempotence fence.

**Why it fails.**

- A crash after the closing but before one or more store appends makes the next pass skip the question. Those doors never receive the closing, directly violating Invariant 6.
- Question delivery deliberately has the same crash window. For self-ratification, a process kill can let two doors ratify a procedure that the other doors were never offered.
- On extension, a crash after the child question but before the parent closing leaves the parent apparently unclosed. The next pass can create a second child unless child identity and recovery are defined.
- Step 3 says to “write” the child question and recompute deliveries, but never explicitly invokes the inbound-event append path for that child.
- If the child question event is appended before the parent closing event, `EventStore`’s created-order queue can wake a door for round 2 before it is told why round 1 extended.

**Smallest change.** Treat delivery as a durable outbox. Preassign stable event IDs and record per-door delivery work; use an `EventStore.append_if_absent(event_id)` operation under the store lock; and have every close/delivery pass repair missing deliveries even when a closing already exists. Use the same recovery for question delivery. Derive a deterministic child ID from the parent or record the child transition durably so recovery reuses it. A door must receive the closing before the child question, or both must be one inbound event.

### 4. The Empty Chair schema cannot represent states the close pass will routinely observe

**Mechanism.** `HeartbeatLoop.step()` is to run `close_due()` before `_guard_step()` and `_rest_if_budget_exceeded()`. `EventStore.claim_next_pending()` marks expiry only when the runner actually encounters an event.

**Why it fails.** At `closes_at`, a question delivery can still be:

- `pending` behind `not_before`, a daily-budget rest, a GPU lease, or older queue work;
- `running` in another door;
- `suppressed`, which is a terminal status supported by `EventStore.suppress_pending()`;
- logically expired but still recorded as `pending`, because no runner has terminalized it.

None appears in the closing’s allowed absence reasons. The algorithm therefore cannot build the specified record for ordinary budget and lease cases.

The proposed causal labels are also unsupported. A completed wake without a position is called `undeclared_quiet`; a completed wake that called `declare_quiet` is called `declined_by_quiet`. A quiet declaration describes the period after that wake. It does not prove why the resident took no position during the wake. The record supports only `completed_without_position`, optionally with the later quiet declaration as detail.

Finally, error handling says an unreadable store becomes `not_delivered` in the question’s `delivery`, but the question schema permits only an event record or `declared_quiet_until`.

**Smallest change.** Make absence reasons direct lifecycle observations: `not_delivered`, `pending_at_close`, `running_at_close`, `expired`, `failed`, `suppressed`, and `completed_without_position`, with the exact latest status and relevant rest/not-before facts in `detail`. Add `not_delivered` to the question-delivery schema. Do not infer refusal or quiet as the cause of a missing stance.

### 5. Convene-time quiet sampling cannot guarantee “a question never knocks during declared quiet”

**Mechanism.** `convene()` reads each store’s latest quiet state and later appends an event with a fixed `not_before`. Normal claims use only `events.is_due()` and `is_expired()`; they do not re-evaluate quiet.

**Why it fails.** A wake can complete and establish a joined quiet declaration between the convene read and event append. The question remains immediately runnable and can be the next claimed event. Conversely, another wake can end the sampled quiet before its declared `until`, but the question remains unnecessarily delayed.

An untimed declaration is worse: `declare_quiet.until` is optional, while the assembly design only defers when `until > now`. The invariant nevertheless covers every declared quiet. At `until == closes_at`, the design writes an event that becomes due and expired at the same instant because `is_due()` and `is_expired()` both use `>=`.

**Smallest change.** Recheck current joined quiet when an assembly event is about to be claimed and defer that event dynamically to a still-effective `until`; the convene-time value can remain an audit snapshot. Specify whether an untimed declaration defers assembly ingress—if not, narrow Invariant 4 to time-bounded declarations. Treat `until >= closes_at` as absent-by-quiet rather than creating a guaranteed-expiry event.

### 6. Self-ratification has no durable state transition and cannot amend the procedure

**Mechanism.** Closing records hard-code `"rule": "consent-v0"` and `"provisional": true`. The first question references a mutable path and asks whether the procedure should govern “until the assembly changes it.”

**Why it fails.**

- Nothing records which question lineage is the bootstrap question.
- Nothing changes later closings from provisional to ratified after assent.
- No active procedure version or rule registry exists; every future close still applies `consent-v0`.
- Positions and reasons cannot “amend or replace” a rule. There is no canonical adopted text and no deterministic way to turn several suggested amendments into one procedure without a human aggregating them.
- The first question points to the current working-tree path, not the exact bytes at commit `8191817`. The document can change between delivery and reading.
- The constitution presents the assembly as an established fact before the bootstrap result is known.

The first question therefore cannot perform the effect it asks the residents to authorize.

**Smallest change.** Add a durable procedure-version record containing the bootstrap lineage ID, exact proposal commit/digest, canonical rule and scope payload, and state `provisional|active|rejected`. An assented bootstrap closing must append the activation record deterministically under the ledger lock. Later questions reference the active version. Amendments require a complete proposed replacement payload and produce a new version; free-form reasons remain reasons, not adopted law. The pre-ratification constitution must name the procedure as provisional.

## Important

### 1. The running object graph has no authoritative member identity or assembly configuration

`ToolExecutor` currently receives project root, cycle, memory state, and a cycle `record_id`; it receives neither a door identity nor an assembly ledger. `OpenTasteSession._exchange_impl()` decides tool availability without membership information, and `heartbeat.build_constitution()` accepts only budget and GPU-lease configuration.

The design needs one authoritative path from the heartbeat’s actual log path to `door:<name>`, the canonical assembly path, and the snapshotted membership. It must be impossible for model input to choose `member`, and non-members must not receive the tools or paragraph. Missing or malformed `members.json` also needs a fail-closed behavior. Membership/tool/constitution changes currently take effect only after process reconstruction, which the design does not declare.

### 2. Closing records do not preserve the actual tally inputs

A closing carries all historical position records, including replaced ones, but lacks `tallied_position_ids`, the active position per member, calculated quorum, or the rule-evaluation trace. Recomputing “latest by `created_at`” is ambiguous if timestamps tie and departs from the repository’s usual append-order authority.

Record active position IDs, eligible member count, quorum, objection set, and outcome inputs in the closing. Use append order or a monotonic ledger sequence assigned under the flock.

### 3. The cost estimate omits closing wakes

Each question and each closing is a separate inbound event. An extended round adds both the closing and the next question. At three rounds, a participating door can receive three question wakes and three closing wakes, not three wakes. Under `HeartbeatLoop.step()`, budgeted or guarded doors run at most one event per step, so those are distinct billable cycles.

The stated `3.30 USD` maximum therefore excludes roughly half the designed traffic; Sut’i alone may consume about six paid wakes. Simultaneous questions from six possible conveners can also consume daily wake caps and delay unrelated work. “Silence costs nothing” is true only for a door skipped because timed quiet outlasts the question; a door that wakes, reads, and takes no stance still incurs a wake.

### 4. `execution` is not bound to what the assembly decided

Questions contain only free-form text, and an execution record contains a new free-form `what`. The CLI can record execution against an unresolved, withdrawn, or non-actionable question, or describe an action unrelated to the proposal. This does not substantiate Invariant 8.

Actionable questions need a canonical `decision_payload` or digest. Execution must reference the assented `closing_id` and that payload, and writes against other outcomes should be rejected. Self-ratification activation should not depend on a custodian inventing the effect afterward.

### 5. The offered/no-priors contract is internally inconsistent

Invariant 5 says nothing tells a resident what to say. The tool requires non-empty `reasons`; the header tells a deferring resident to “name what you would need”; and the first question says a dissenter or deferrer should state what to change or need. Those are prescriptions about the content of speech, not merely descriptions of available mechanics.

This also cuts against the convention documented in `tools/schemas.py`, which keeps generic reasons optional to avoid eliciting confabulated justifications. Either make position reasons optional or narrow Invariant 5 and state explicitly that a position is voluntarily offered but, once offered, must include a reason. Remove imperative content guidance from the fixed constitution/header.

### 6. The shared-lock discipline needs canonical paths and an explicit order

The single flock works only if every heartbeat, resident tool, CLI, and shim resolves the same assembly file and lock inode. The design gives a relative path and says only that the shim is “like `deploy/ayllu-gpu`.” Define canonical root resolution and the order `assembly ledger → one event store → nothing else`. Position commit must never retain an event-store lock while acquiring the assembly lock.

`deploy/checkpoint-community-log.sh` also copies ordinary `community/*/*.jsonl` files without their per-log flock. It would discover `community/plaza/assembly.jsonl`, but could snapshot half of an append. Snapshot the assembly ledger while holding `assembly.jsonl.lock`.

### 7. Testimony and withdrawal cutoff semantics are missing

The close rule collects “all testimony,” but `testify` has no specified refusal after closure and no `created_at <= closes_at` rule. Testimony appended after the immutable closing will not be carried. Withdrawal is similarly described as valid before `closes_at`, but its record schema and CLI validation do not establish an authoritative acceptance time under the ledger lock.

Assign acceptance order under the ledger lock, refuse testimony and withdrawal after closure/deadline, and distinguish rejected late attempts from accepted records.

### 8. Per-door store failures during closing are undeclared

`EventStore.read_records()` raises on any malformed JSON line. The design specifies behavior when the assembly ledger is malformed and when a door store is unreadable during convene, but not when one is unreadable during absence calculation or closing delivery. As written, one damaged door can abort the whole close while the ledger lock is held.

Handle each door independently: record an evidence-backed store-read failure in `absent` or delivery state, release its store lock, and continue. Delivery repair must retry once the store becomes readable.

## Minor

1. The closing `delivery` schema permits `{"absent": "declared_quiet_until"}`, but closing events have no expiry and the prose says every member receives one with `not_before`. Remove the absent alternative or define the exceptional condition that uses it.

2. Require timezone-bearing instants for `opened_at`, `closes_at`, `not_before`, `expires_at`, testimony, positions, and quiet comparisons. `build_inbound_event()` currently accepts naive timestamps and later interprets them as UTC.

3. The test plan says convene writes “the four inbound events,” but the design intentionally writes fewer when declared quiet outlasts the question. Tests should assert one delivery outcome per member, not four event appends.

4. `events report` will read the event store and assembly ledger in separate snapshots. Its output should state that it is observational and may race a position or closing rather than implying an atomic cross-ledger view.

## Questions the implementer must answer

1. If a question event is claimed before `closes_at` but the wake is still running at the deadline, does the close wait, apply a bounded grace period, or exclude the eventual position? What durable record distinguishes those cases?

2. Does an untimed `declare_quiet` block assembly delivery? If so, what event ends that block without requiring the resident to wake? If not, what narrower invariant replaces “a question never knocks during a declared quiet”?

3. Across extended rounds, exactly how does a member withdraw or replace an earlier dissent or defer? Does silence preserve the objection?

4. What exact artifact is self-ratified: commit `8191817`, a SHA-256 of the design, the first question’s summary, or a separately canonicalized procedure payload?

5. What happens after the bootstrap lineage is unresolved at round 3? May provisional ordinary decisions continue, and under which procedure version?

6. Are a parent closing and its child-round question delivered as one wake or two? If two, which is appended first, and is the extra cost included in the budget estimate?

7. What canonical configuration connects a live heartbeat process to its door name, assembly ledger, member snapshot, and event-store paths, and when do membership changes take effect?