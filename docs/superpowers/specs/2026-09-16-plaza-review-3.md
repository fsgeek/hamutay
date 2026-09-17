# The plaza — design review, round three

**Date:** 2026-09-16  
**Reviewer:** Codex  
**Reviewed:** `docs/superpowers/specs/2026-09-16-plaza-design.md`, revision 3 at commit `3716733`, against rounds one and two, the running implementation at `dbedd82` (`dbedd82` differs only by the timestamp proof), the deployment scripts and tests, and open lineage `9c725552-c3f6-4d5b-bede-307ddcdc6830`.

## Resolved from round two

**Blocking 2:** Resolved. The launch note and ancestor test establish the narrowed fact phase one needs: each current systemd invocation started from a clean checkout whose recorded commit descends from the plaza merge. The unit’s `WorkingDirectory` and `--project-root .` agree, and missing, dirty, or pre-merge evidence fails closed.

**Significant 1:** Resolved. An arbitrary nonempty CLI key is now deterministically namespaced into a UUID5, so the CLI writer and validator agree without restricting human-facing keys to UUID syntax.

**Significant 5:** Resolved. The wrapper now covers both `EventStore` construction and `append_if_absent`, normalising `OSError`, `StoreUnavailable`, and constructor-originated `LeaseGateRequired` while allowing programming errors to reach the heartbeat guard.

**Significant 6:** Resolved. Duplicate lookup, cap evaluation, UTC conversion, timestamp creation, and append are ordered atomically under the plaza lock, and a retry of the recorded forty-eighth message remains a duplicate success.

**Minor 1:** Resolved. “One idempotency key, one message” accurately names the deliberate-repeat semantics.

**Minor 2:** Resolved as to the original finding. `MembersConfig.snapshot()` equality, rather than source-byte identity, is now the migration invariant; the placement of that check introduces a separate crash-consistency defect below.

**Minor 3:** Resolved. `plaza=None`, member-only snapshots, unchanged assembly suites, and explicit coverage of lineage `9c725552` are sufficient. Adding the top-level key does not alter that lineage’s frozen four-member path snapshot or prevent it from binding and closing.

## Blocking

### 1. The induced-cost disposition is honest in Invariant 8 but contradicted by the Cost and assembly claims

**Defect.** This is **Blocking for the claims and for informed assembly ratification, not Blocking for the implementation mechanism itself**. Narrowing Invariant 8 instead of changing the governor is legitimate: it now accurately bounds only new directed delivery events created through the resident tool and expressly disclaims attempts, spend, and CLI-originated traffic. The reason for deferring the governor change is also procedurally coherent because the active assembly procedure reserves changing the governor to the assembly.

The rest of the document does not consistently preserve that narrowing. Cost still says that each door’s daily governor “bounds what it spends answering,” immediately before acknowledging that failed and orphaned attempts are neither counted nor costed. More seriously, the proposed question tells the assembly, without qualification, “A message to a door costs that door one wake.” One event can incur repeated API attempts across heartbeat restarts, and a resident can create uncapped CLI traffic through `bash`. The statement that the plaza adds only the exposure every inbound event already has describes the per-event recovery behavior, but not the new autonomous volume and control surface. The assembly would therefore be asked to ratify a materially stronger cost representation than revision 3 actually supports.

**Recommendation.** Keep the narrowed Invariant 8 and the governor fix outside this implementation if that is the intended governance choice, but make every downstream statement equally narrow. Cost should say that the governor does not currently bound failed or orphan-recovered spend. The assembly question should say that a directed message creates one delivery event, normally completed by one wake, but may cause repeated attempts after crashes; it should also state that the 48-message limit applies only to the resident tool. This does not require changing the governor before implementation, but it does require informed assent to the unbounded attempt exposure.

### 2. The validator cannot establish “seq equals physical line number” through the specified Ledger

**Defect.** This is **Blocking for implementation as written** because exact line offsets are part of the inbound event, note, CLI, and fail-closed contract. `Ledger.read_unlocked()` returns only parsed records and silently skips blank or whitespace-only physical lines. A validator receiving that list can prove `seq == record ordinal`, but cannot prove `seq == one-based file line number`; after a blank line, the advertised `read(offset=seq-1)` points to the wrong bytes.

A malformed, unterminated final JSON fragment is correctly omitted by `Ledger`, so the validator must validate only the complete prefix and assign the replacement record sequence `len(complete_records) + 1` after that tail is discarded. There is a second tail defect: an unterminated final line that happens to be complete JSON is accepted as a record rather than classified as torn. The next `append_unlocked()` then writes the following JSON immediately after it without inserting a newline, corrupting the ledger. The existing torn-tail test covers only syntactically incomplete JSON and does not cover blank lines or complete JSON lacking its terminating newline.

**Recommendation.** Define a plaza reader that preserves physical-line information. Reject blank lines anywhere in the committed prefix, and treat any nonempty final bytes lacking a newline as the single tolerated torn tail, whether or not those bytes happen to parse as JSON. Exclude that tail from semantic validation; under the lock, truncate it, construct the proposed row with sequence equal to the next physical line, validate the complete prefix plus that row, and append it as one newline-terminated record. Add tests for blank middle lines, whitespace lines, incomplete JSON tails, parseable JSON without a newline, and append recovery in every case.

## Significant

### 1. The tightened validator still accepts records the writers cannot produce

**Defect.** Round-two Significant 2 is improved but not fully resolved. Revision 3 adds sequence continuity, unconditional uniqueness, actor/wake correlations, path and digest checks, UUID versions, and delivery-event recomputation. It does not recompute a tool message’s `idempotency_key`, even though a tool record contains every required input: `wake.event_id`, canonical `to`, and `text`. Any unrelated UUID5 therefore passes while violating Invariant 3’s framework-derived identity.

The validator also does not state the required correlation between delivery state and its nullable fields. It can accept `state: landed` with `landed_at: null` and an error detail, or `state: store_unreadable` with a landing timestamp and no error. Those rows are impossible from the specified writers but affect the reducer’s delivery truth. Consequently the claim that the validator admits what the writers produce “and nothing looser” is still false.

**Recommendation.** For every `via: tool` message, recompute and require the exact idempotency key from the recorded wake event, destination, and UTF-8 text digest. Require `landed` exactly when `landed_at` is a timezone-bearing instant and `detail` is null; require `store_unreadable` exactly when `landed_at` is null and `detail` contains the expected error string. Test each cross-field contradiction independently.

### 2. The plaza note can still omit a message permanently, and its read command is not stable

**Defect.** The completed-to-running join is correct: joining the latest completed row to its running row by both `event_id` and `run_id` obtains the intended lower-bound `started_at`. Minting `sent_at` under the send lock also closes the original race only when the note obtains that same lock.

Revision 3 retains an unlocked fallback after note-lock timeout. A sender can mint `sent_at`, remain inside a slow pre-append or append operation, and hold the plaza lock while a newly claimed wake falls back to an unlocked read. If the timestamp predates that wake’s `started_at` and the incomplete line is not observed, the message is absent from this note and excluded by the next completed-wake lower bound. Thus the disposition reintroduces the permanent-omission window it says it closes.

The advertised command is also exact only at the instant of the note snapshot. `read --since-seq <a> --for <door>` has no upper bound; when the resident runs it later, qualifying messages appended after `<b>` are printed too. For counts above twelve, the displayed sequence list is abbreviated, so the resident cannot reconstruct an exact finite selection from the note itself.

**Recommendation.** On plaza-lock timeout, omit the note and emit the error as the section already promises; do not perform an unlocked fallback. Give the CLI an inclusive upper bound such as `--through-seq <b>`, or an exact sequence selector, and have the note print a command bounded to its snapshot. The completed-to-running join and `--for` exclusions can otherwise remain as written.

### 3. The pass’s budget rule does not prove its six-second bound

**Defect.** Round-two Significant 3 is resolved as to lock scope, repeated candidates, and fairness wording: one plaza-lock scope per unit, the examined set, the full-circuit stop, and per-process fairness are coherent. The wall-clock guarantee remains false against the running APIs.

The proposed four-second reservation accounts for a two-second plaza-lock acquisition and a two-second event-store lock acquisition. Those timeout windows do not bound plaza reading and validation, event-file reading, writing, flushing, `fsync`, verification, or the delivery-row append and its `fsync`. Once `EventStore.append_if_absent()` acquires its lock, its I/O has no deadline. A slow filesystem can therefore carry a unit beyond the remaining budget, just as a direct send can hold the plaza lock longer than the nominal store window.

**Recommendation.** Either narrow the claim to a bounded number of units and bounded lock-acquisition waits, explicitly allowing overrun during filesystem I/O, or introduce an architecture with an enforceable deadline around the entire unit. Do not state that the pass “never exceeds six seconds” based only on acquisition timeouts. The full-circuit and per-unit-lock rules should remain.

### 4. The snapshot equality check occurs after the unsafe state is installed

**Defect.** The semantic equality test correctly replaces the earlier byte-identity requirement, but phase two performs it only after atomically replacing `members.json`. A process crash, kill, or restoration failure between rename and comparison can leave altered member paths installed while lineage `9c725552` is still open. “Abort, restoring the original file” is recovery after exposure, not prevention, and the restoration path is not given the same temporary-file, fsync, rename, and directory-fsync guarantees.

**Recommendation.** Construct the candidate in the same-directory temporary file, load and validate that candidate, and compare its `MembersConfig.snapshot()` with the current snapshot before renaming it into place. Only a candidate whose snapshot is equal should be committed. If post-rename rollback remains as defense in depth, make that restoration atomic and durable as well.

### 5. Phase two does not revalidate provenance for the processes it actually activates

**Defect.** The new launch evidence makes phase one answerable, but phase two relies on the old invocations’ phase-one evidence before stopping them. After enabling the key, it starts four new invocations and waits only for each `plaza: door <name> may send` note. A checkout change or dirty tree between phase one and those restarts can therefore activate unverified code. The later no-flag check detects that state only after the plaza has already been enabled and delivery may have begun.

**Recommendation.** For each newly started phase-two invocation, require both its plaza-binding note and its own `source:` note showing a clean descendant of the merge. Do not report migration success until all four current invocation IDs pass both checks. If one fails, stop the units and atomically remove or roll back the plaza key before allowing message processing.

## Minor

None.

**Verdict:** No—revision 3 is not safe to implement exactly as written: the physical-line validator defect blocks implementation, the remaining cost language blocks the document’s claims and informed ratification, and the note, budget, and phase-two issues require disposition on the record before the loop closes.