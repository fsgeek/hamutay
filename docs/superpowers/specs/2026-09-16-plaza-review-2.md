# The plaza — design review, round two

**Date:** 2026-09-16  
**Reviewer:** Codex  
**Reviewed:** `docs/superpowers/specs/2026-09-16-plaza-design.md`, revision 2 at commit `89084ba`, against round one, the running implementation at `f0e8339` (`f0e8339` differs only by the timestamp proof), the assembly implementation and tests, and open lineage `9c725552-c3f6-4d5b-bede-307ddcdc6830`.

## Resolved from round one

**Blocking 1:** Resolved by narrowing rather than enforcement. The trust section now plainly says that neither resident nor human identity is tamper-proof, calls `--by` an unauthenticated label, and limits Invariant 1 to the framework tool path; that is an honest and sufficient disposition for the narrowed identity claim.

**Blocking 2:** Resolved. The key is stable across `recover_orphaned_running()` because recovery preserves the source `event_id` while changing `run_id`; canonical `to` removes spelling ambiguity, and the text digest makes exact recovered repeats coalesce. A deliberate exact repeat within one source wake also coalesces, but revision 2 explicitly declares that loss.

**Blocking 4:** Resolved for the revised claim. The recorded absolute events path and members-file digest preserve the sender’s boot-time directory generation, and every repair uses that path. The design openly declares that a later path change does not retarget an old message.

**Significant 5:** Resolved. Byte identity is now limited to disabled/unbound behavior and the `extra_notes=None` path, while enabled wakes are allowed the stated plaza-note difference.

**Minor 1:** Resolved. The actor spelling, namespace, canonical inputs, and delivery-event derivation are now exact.

**Minor 2:** Resolved. The quiet field is omitted when a wake is running and is labelled as the latest completed wake’s declaration rather than present truth.

**Minor 3:** Resolved. The checkpoint specifies separate, nonoverlapping assembly and plaza lock scopes, and the migration specifies temporary-file durability, atomic replacement, and directory fsync.

## Blocking

### 1. The send cap bounds message records, not the induced wake cost the design claims

**Defect.** Blocking 3’s disposition is honest about not repairing `DailyLedger`, and the plaza cap does bound unique directed records created through `send_message`, including when the sending wake later fails or is orphan-recovered. It does not, however, establish Invariant 8’s broader “bounded induced cost” or the Cost section’s “a directed message costs the recipient one wake.” A delivered event may itself reach `running`, consume an API call, crash before terminalization, and be re-pended by `recover_orphaned_running()` repeatedly. Those attempts create no additional plaza message and consume no send-cap entry, while the unchanged governor may record none of them. One message can therefore induce an unbounded number of recipient attempts under the stated crash model.

The stated trust model creates a second hole in the same claim: every resident can invoke the uncapped human CLI through `bash`. Revision 2 correctly treats those records as unauthenticated `via: cli`, but the resulting directed events still cost recipient wakes. Thus the cap bounds one framework tool path, not what a resident process or one plaza message can induce. The disposition is sufficient only for the narrower claim “at most 48 new directed plaza records per door actor per UTC day through `send_message`.”

**Recommendation.** Either debit the existing wake governor durably at claim, retaining the debit across failure and orphan recovery, or narrow Invariant 8 and the Cost section to unique delivery events created through the resident tool and expressly disclaim a bound on attempts, spend, and CLI-originated traffic. If bounded spend remains a deployment safety property, the claim-time governor fix cannot remain outside this design.

### 2. Phase one cannot perform its required version check from the heartbeat’s launch record

**Defect.** Revision 2 says `check-plaza.sh --phase-one` can confirm that every current invocation runs a commit at or after the plaza merge because “the heartbeat’s launch notes already print the commit.” They do not. `heartbeat.py main()` emits launch configuration, budget, capabilities, context ceiling, transport timeout, assembly binding, and GPU-lease notes, but no Git revision. Neither the systemd unit nor `deploy/run-heartbeat.sh` supplies one. An invocation ID establishes which process emitted a journal line, not which source revision that process loaded. Moreover, “at or after” is not a valid Git relation unless it means the plaza merge is an ancestor of the recorded revision.

This makes phase one’s completion condition unanswerable, so phase two cannot safely distinguish four plaza-capable processes from the mixed-version deployment that round one identified.

**Recommendation.** At process launch, record the exact source commit and whether the tree was dirty in a journal line scoped to the current systemd invocation. Have the phase-one check require the intended plaza merge to be an ancestor of each recorded clean revision, not compare timestamps or lexical hashes. Phase two must refuse when any current invocation lacks that evidence.

## Significant

### 1. The human idempotency-key writer can produce a record its validator rejects

**Defect.** The validator rejects every non-UUID ID, but the CLI accepts `--key K` and places that value directly in `idempotency_key` without specifying that `K` must be a UUID. A normal human retry key such as `--key migration-announcement` therefore constructs a message that the design’s own mandatory pre-append validation rejects. This is exactly the writer/validator inconsistency the strict validator was meant to prevent.

**Recommendation.** Either define `--key` as a UUID and validate it before record construction, or accept an arbitrary nonempty string and derive a UUID5 from its exact UTF-8 value. Pin both accepted and rejected forms in the CLI tests.

### 2. The strict validator still permits records that break its own reducer and paging invariants

**Defect.** Round one’s semantic-validation finding is only partly resolved. “Non-monotonic or duplicate” sequence rejection still accepts gaps such as `1, 3`; once accepted, `seq` no longer equals line number and the note’s offset calculation is false. The duplicate rule also appears to reject a repeated idempotency key only when its content differs, permitting two same-content message rows for one key and making `by_key()` ambiguous.

The listed conditions do not require `delivery` to be null exactly for posts and non-null exactly for directed messages; do not require its path to be absolute or its digest to be a SHA-256 value; and do not correlate `via`, actor, and wake shape (`via: tool` with `tony`, or `via: cli` with a door actor and non-null wake, can pass). Those contradictions would remain “valid” lines despite Invariant 10’s fail-closed claim.

**Recommendation.** Require `seq == one-based line number`; reject every second `message_id` and every second `idempotency_key`, regardless of content; validate the delivery/path/digest relationships; and enforce `tool ↔ door actor plus non-null wake` and `cli ↔ human label plus null wake`. Validate UUID versions and deterministic delivery IDs where the record contains enough information to recompute them.

### 3. The bounded pass can exceed six seconds and can retry the same message repeatedly in one pass

**Defect.** The pass improves round one’s unbounded \(2N\) lock hold, but its exact mechanics remain inconsistent. A two-second store attempt begun just before the six-second deadline can finish near eight seconds, so checking the budget only between units does not satisfy “six seconds, whichever comes first.” The disposition says “per-unit release,” while §6 describes one plaza-lock scope around validation and all four attempts.

The fair cursor also lacks a full-circuit stopping rule. With one or two undelivered messages, wrapping can select the same stuck message repeatedly until four units or the time budget is consumed. That does not starve later messages, but it loops within the pass and turns one store failure into repeated lock waits. The cursor is only in process memory, so frequent heartbeat restarts also repeatedly begin at the front despite the unconditional “cannot starve” wording.

**Recommendation.** Define one delivery unit as one plaza-lock scope, with release and reacquisition between units. Do not begin a store attempt unless its full lock window fits within the remaining total budget, or define the bound as six seconds plus one store window. Track the set examined during the current pass and stop after one full circuit. Qualify fairness as applying while the memo survives, or persist the cursor if restart-safe fairness is required.

### 4. The plaza note’s advertised read range is not the set it counted

**Defect.** The lower bound itself is sound if the implementation joins the latest `completed` record to its matching `running` record by both `event_id` and `run_id`; `latest_completed_wake()` alone cannot supply `started_at`, because completed rows contain only `completed_at`. Using that joined start avoids the original permanent-omission window.

The advertised paging instruction is nevertheless false. Message records are interleaved with delivery records, and counted messages can be separated by messages excluded because they are from or addressed to the current door. Reading lines `a..b` therefore returns delivery rows and excluded messages as well as the \(N\) counted messages. It does not “show exactly those lines” in the sense asserted by the note or its validation test.

There is also a residual omission window unless `sent_at` is minted while holding the plaza lock: a sender can timestamp a message, wait behind the note’s read, then append it after that read with a timestamp before the completed wake’s lower bound.

**Recommendation.** Specify the completed-to-running join explicitly. Mint `sent_at` only after acquiring the plaza lock. Report either the exact message sequences, multiple contiguous ranges, or a sequence interval described honestly as containing the messages, and provide a reader that filters message records and the door exclusions rather than promising a raw line slice is exact.

### 5. Store-error normalization does not cover every exception the current store constructor emits

**Defect.** Wrapping `OSError` and `StoreUnavailable` covers the raw filesystem paths identified in round one, but constructing `EventStore(recorded_path)` also reads the adjacent `door.json`. A malformed or unreadable lease binding is converted into `LeaseGateRequired`, not either promised exception. It can therefore escape a send after the plaza message is durable and can abort the whole pass before later messages are attempted, contrary to the per-message isolation claim.

**Recommendation.** Normalize every expected failure from both `EventStore` construction and `append_if_absent`, including `LeaseGateRequired` caused by recipient metadata, into the plaza’s per-message unavailable result. Keep programming errors outside that normalization so the heartbeat guard can still report genuine defects.

### 6. Cap evaluation order and UTC-day atomicity are underspecified

**Defect.** The cap is mechanically capable of enforcing 48 directed tool messages per actor and UTC day because sends serialize on the plaza lock, but the stated refusal list leaves unclear whether `sent_today` is checked before entering that lock. An outside check races concurrent sends. A cap check before idempotency lookup also causes a recovery retry of an already-recorded 48th message to return “cap reached” instead of the promised duplicate success. Finally, timezone-bearing instants are not enough by themselves: counting must convert `sent_at` to UTC before taking its date.

**Recommendation.** Under the plaza lock, validate and look up the idempotency key first; only a genuinely new directed message should then count against the cap. Generate `sent_at` there, normalize every parsed instant to UTC, count the UTC date, and append before releasing the same lock.

## Minor

### 1. The invariant title overstates the deliberate-repeat semantics

**Defect.** “One send, one message” suggests two intentional calls produce two messages, while the actual rule is one idempotency key per message. Two exact same-text calls to the same recipient in one source event intentionally collapse. The Declared losses section is honest about this, so it is not a safety defect, but the invariant’s short form is misleading.

**Recommendation.** Rename it to “One idempotency key, one message” and retain the explicit instruction that a deliberate repeat in one wake must differ in text.

### 2. “Members object byte-for-byte unchanged” is stronger than the assembly requires and easy to violate accidentally

**Defect.** The open lineage freezes the semantic `MembersConfig.snapshot()`—member names and absolute session/event paths—not the JSON source bytes. A normal Python load/modify/dump migration can preserve that snapshot while changing whitespace and key formatting, contradicting revision 2’s byte-for-byte wording even though lineage `9c725552` remains valid.

**Recommendation.** Make equality of the pre- and post-migration `MembersConfig.snapshot()` the required check. If literal source preservation is also desired, require a format-preserving insertion and test the exact `members` source slice separately.

### 3. Assembly compatibility is a required regression constraint, not yet explicit in the data-class change

**Defect.** Adding `plaza` and `digest` to `MembersConfig` is compatible with the assembly only if `snapshot()` remains exactly member-only and absent-key construction preserves existing behavior. The design says the snapshot is unaffected, and the open lineage confirms that adding the top-level key is safe, but it does not require defaults or regression coverage for existing binding, outbox, constitution, and validation callers.

**Recommendation.** Require `plaza=None` compatibility, keep `digest` outside `snapshot()`, and run the existing `tests/assembly/` and `tests/assembly_validation/` suites unchanged in addition to the new plaza suites. Pin that lineage `9c725552` still binds and closes against its original four-member path snapshot after the top-level key is added.

**Verdict:** No—revision 2 is substantially more honest and repairable, but it is not safe to implement as written until the induced-cost claim is narrowed or durably enforced and phase one gains an actual per-invocation source-revision proof.