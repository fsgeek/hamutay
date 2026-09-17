# The plaza — design review, round one

**Date:** 2026-09-16  
**Reviewer:** Codex  
**Reviewed:** `docs/superpowers/specs/2026-09-16-plaza-design.md`, revision 1 at commit `d3d79eb`, against the assembly revision 4 and its three reviews, and the running implementation at `d3d79eb` (`72abebe` differs only by its timestamp proof).

## Blocking

### 1. The human CLI does not establish a human identity

**Defect.** The design treats `deploy/ayllu-plaza send --by {tony,custodian}` as trusted identity, but every natural resident is offered the unscoped `bash` tool. `BASH_SCHEMA` explicitly says it can execute anything available to the process and reach outside the project (`src/hamutay/tools/schemas.py`, `BASH_SCHEMA`), and `ToolExecutor.execute()` dispatches it without an authorization boundary (`src/hamutay/tools/executor.py`, `ToolExecutor.execute`). A resident can therefore invoke the CLI with `--by tony`, import the plaza writer directly, or append forged JSONL under the same Unix account. It can likewise write an event directly into a store not selected by its binding. Restricting the CLI option to two strings validates spelling, not provenance, so Invariant 1 and the requested “model input cannot set identity or reach another store” property are false.

**Recommendation.** Put plaza writes behind a broker running under a separate OS identity. Resident processes should receive only a door-bound client capability; the broker should derive the door from that capability and expose no human actor option. The administrative client must use a capability unavailable to resident processes, and plaza/event files must not be directly writable by residents. If that boundary is out of scope, the smallest honest change is to remove `tony` and `custodian` as asserted identities, record `human-cli` plus an explicitly unauthenticated claimed label, and narrow the invariant accordingly.

### 2. Boot recovery can duplicate a message and its recipient wake

**Defect.** Each call generates a new `message_id` with UUID4, while at-most-once delivery is keyed only by the UUID5 derived from that message ID. If a process dies after the message is fsynced but before the sending wake completes, `recover_orphaned_running()` copies the original pending event and re-pends it (`src/hamutay/heartbeat.py`, `recover_orphaned_running`). The resident can repeat the same `send_message` call during the recovered run, producing a second message ID and therefore a second delivery event. `EventStore.append_if_absent()` cannot coalesce them because their event IDs differ (`src/hamutay/events.py`, `EventStore.append_if_absent`). Thus one logical send can appear twice on the plaza and wake the recipient twice, despite the design presenting crash repair and at-most-once delivery as one guarantee.

**Recommendation.** Give every send a framework-owned idempotency key stable across recovery, derived from the source `event_id` and a durable tool-call identity or send slot, and make the plaza reducer return the existing message for a repeated key. Do not include `run_id`, since recovery changes it. Human clients should likewise supply or persist an invocation key for retry.

### 3. The daily governor does not bound the failure-after-send cost loop

**Defect.** A message becomes durable during the tool call, before the sending wake completes. If a resident sends and then the exchange fails or the process dies, the recipient still wakes. `DailyLedger`, however, counts only completed cycle records in the session log and assigns their day from the record timestamp (`src/hamutay/heartbeat.py`, `DailyLedger._refresh` and `DailyLedger.day`). An API call that fails after `send_message` may leave no cycle record and therefore consumes neither the 48-wake count nor recorded cost. Two residents can repeatedly send before failing, with each durable send inducing another uncharged attempt at the other door. The design’s Cost section therefore relies on a governor that does not count the failure mode introduced by durable mid-wake sends.

**Recommendation.** Debit the wake-count budget durably when an event is claimed, before the model call, and reconcile cost afterward. Failed and orphaned attempts must retain the count debit even when their monetary cost is only a lower bound. Use the existing event-store running record or a dedicated attempt ledger as the durable source; completed session records alone cannot enforce this bound.

### 4. Delivery is not bound to an immutable recipient-store generation

**Defect.** The message record stores only the recipient door and delivery event ID, not the event-store path selected at send time. `AssemblyBinding` retains a boot-time `MembersConfig` (`src/hamutay/assembly/binding.py`, `AssemblyBinding`), so different long-running or rolling-restarted heartbeats can hold different directory generations. Moreover, `bind()` compares only the binding door’s own paths with each open snapshot, not every recipient’s paths. One pass can therefore land a message in an old store and append `landed`; a pass using the new directory then sees terminal delivery truth and never writes the new store. This loses the message to the live recipient while claiming successful delivery.

Adding only the top-level `plaza` key during lineage `9c725552-c3f6-4d5b-bede-307ddcdc6830` does not itself alter `MembersConfig.snapshot()`, so that narrow migration does not violate the open question’s member/path snapshot. The broader claim that the existing directory safely governs plaza delivery remains false when membership paths later change.

**Recommendation.** Resolve the recipient through trusted configuration at send time and copy the absolute recipient event-store path plus a members-file generation digest into the message record. Every repair must use that recorded path. Refuse sends if the live binding and directory generation disagree; model input must never supply or override the path.

## Significant

### 1. The note cursor can permanently omit messages sent during a successful wake

**Defect.** The note counts `sent_at` values after the door’s latest `completed` status (`docs/superpowers/specs/2026-09-16-plaza-design.md`, §5). The note itself is computed just after the new event is claimed. A post or other-door message arriving between that computation and the wake’s later completion was not in the note, yet its `sent_at` precedes the new `completed_at`. The next wake therefore excludes it permanently. An unlocked fallback read during a concurrent append creates the same loss window. Failed wakes repeat their notes as intended; successful wakes create the unhandled gap. `latest_completed_wake()` exposes the completion row but no note watermark (`src/hamutay/events.py`, `latest_completed_wake`).

The note also gives no sequence range. Once the plaza exceeds 500 lines, the resident’s ordinary `read` call returns the beginning by default (`src/hamutay/tools/perception.py`, `tool_read`), and qwen’s context protection may further replace a large result with only a head slice (`src/hamutay/taste_open.py`, `_bound_tool_result_for_context`). “Read plaza.jsonl” is therefore not a reliable route to the newly counted records.

**Recommendation.** Use the `started_at` of the latest successfully completed wake as the lower bound, or persist the highest plaza sequence actually included in that wake’s note. Report first and last message sequence numbers in the note and provide a bounded sequence-based reader or exact pagination instruction. Sequence, not timestamps, should define the counted interval.

### 2. A repair pass can hold the plaza lock for an unbounded aggregate time

**Defect.** The pass holds the plaza ledger lock while iterating every undelivered message, and each event-store attempt may consume its own two-second window. With \(N\) busy deliveries, the lock can be held for approximately \(2N\) seconds. `Ledger.try_locked()` bounds only acquisition, not time inside the critical section (`src/hamutay/assembly/ledger.py`, `Ledger.try_locked`), while the proposed plaza pass performs an unbounded amount of store work under that lock. During this interval all sends time out, and the heartbeat itself can be delayed arbitrarily. “Plaza lock → at most one store lock” prevents a cycle but does not provide a bounded wait.

**Recommendation.** Give each pass a total deadline or a small fixed work limit and persist or memoize a fair cursor. Release the plaza lock between bounded delivery units, re-read delivery truth after reacquisition, and retain the order plaza lock → one store lock for each unit.

### 3. The rolling migration exposes doors to plaza events before they have plaza tools

**Defect.** `migrate-plaza.sh` is specified to add the key first and then restart four units one at a time. After the first new process starts, it can send or run the repair pass against a door whose old process is still active. That old process can claim the `origin: member` event but has neither `send_message`, its guidance, nor the plaza constitution clause. The purpose nevertheless tells it that `send_message` is how to answer. The event may complete before that door is restarted, making the mixed-version behavior permanent.

The open assembly lineage is not the problem: preserving the `members` object byte-for-byte keeps its snapshot stable. The activation ordering is.

**Recommendation.** Use a two-phase deployment: first deploy and restart plaza-capable code everywhere while the `plaza` key remains absent; then verify no running wakes, stop all four heartbeats, atomically add the key, and start/check all four. Alternatively, add an activation generation that delivery refuses until every configured unit has acknowledged it.

### 4. Store I/O failures outside `StoreUnavailable` defeat failure isolation

**Defect.** The design catches `StoreUnavailable` and records `store_unreadable`, but the current store API normalizes only lock timeout, JSON decoding, and its explicit short-write check. Directory creation, lock-file opening, event-file opening, `stat`, `write`, `flush`, and `fsync` can raise raw `OSError` (`src/hamutay/events.py`, `EventStore.__init__`, `_try_locked`, and `append_if_absent`). After the message has been fsynced, such an exception escapes without a delivery row. In the pass, it aborts the whole loop, so one inaccessible recipient can repeatedly prevent later messages from being attempted. That does not meet the promised per-message repair behavior.

**Recommendation.** Normalize all recipient-store acquisition, read, append, flush, fsync, and verification failures into `StoreUnavailable`, preserving their details. The pass must catch failures per message, append a deduplicated `store_unreadable`, and continue to the next delivery.

### 5. “Byte-for-byte unchanged” conflicts with the required note on every enabled wake

**Defect.** Invariant 7 and the testing section promise that non-plaza events remain byte-for-byte unchanged. Section 5 simultaneously requires `run_next_event()` to append a plaza note to `operational_notes` on every enabled event-managed wake. Consequently an existing external or self-scheduled event has a different model envelope whenever unseen plaza traffic exists. `build_inbound_event(origin="external")` and the external branch of `build_event_envelope()` can remain byte-for-byte identical with careful defaults, and an unbound or disabled `run_next_event()` can remain identical; an enabled non-plaza wake cannot.

**Recommendation.** Narrow the guarantee to disabled/unbound operation and to direct calls where `extra_notes is None`. State explicitly that an enabled bound wake may differ only by the appended plaza operational note. Add golden byte comparisons for the default `build_inbound_event`, external `build_event_envelope`, and `run_next_event(extra_notes=None)` paths.

### 6. The stated fail-closed rule lacks semantic record validation

**Defect.** Reusing `Ledger` detects invalid JSON except for a tolerated torn tail, but it accepts any syntactically valid JSON object (`src/hamutay/assembly/ledger.py`, `Ledger.read_unlocked`). The assembly reducer similarly ignores unknown record types and assumes required fields for recognized ones (`src/hamutay/assembly/records.py`, `reduce`). The plaza design does not define stricter validation for sequence continuity, record types, required fields, UUIDs, actor forms, door membership, delivery references, timestamps, or immutable message IDs. A valid JSON line with missing or contradictory fields may therefore be silently ignored, crash only one reducer path, or rewrite delivery truth rather than triggering Invariant 8’s global refusal.

**Recommendation.** Specify one strict validator run over every line before reduction or append. It should reject unknown record types, missing/extra identity fields, invalid actors or doors, nonmonotonic/duplicate sequences, duplicate message IDs with different content, and delivery rows that do not exactly match their message’s door and event ID. All such failures should raise `LedgerMalformed`.

## Minor

### 1. Stable identity derivation and sender spelling are underspecified

**Defect.** The record already stores `from: "door:<name>"`, but §4 says the event receives `sender="door:<from>"`; read literally, that produces `door:door:qwen`, while the data-flow example expects `door:qwen`. Likewise, “UUID5 of the message id and the door” does not name the UUID namespace or canonical input spelling. Independent send and repair implementations could therefore derive different event IDs.

**Recommendation.** Define one helper that accepts the canonical stored actor and recipient door, adds no second prefix, and computes UUID5 using a named constant namespace and an exact UTF-8 name such as `<message_uuid>\0door:<name>`.

### 2. `recipient_quiet_until` can report a quiet that a concurrent wake has already ended

**Defect.** `quiet_declaration_for_latest_wake()` considers only the latest completed or failed outcome and ignores a currently running wake (`src/hamutay/events.py`, `latest_wake_outcome` and `quiet_declaration_for_latest_wake`). A sender inspecting the store while the recipient is already running can therefore be told that timed quiet is still in force, although the framework’s operational semantics say the new wake ends it. This field is advisory but its wording claims current truth.

**Recommendation.** Omit `recipient_quiet_until` whenever any event’s latest status is `running`, or label it explicitly as the last completed wake’s declaration rather than a guarantee.

### 3. Checkpoint and members-file replacement need explicit crash and lock ordering

**Defect.** The checkpoint change asks for assembly and plaza snapshots on the same `CHECKPOINTS.txt` line but does not say that their locks are acquired and released separately. An implementation may naturally nest the two locks, contradicting Invariant 9. The migration likewise says only that Python edits `members.json`; an in-place write can leave a malformed directory after a crash, causing all restarted doors to fail binding (`src/hamutay/assembly/binding.py`, `load_members`).

**Recommendation.** Require independent, nonoverlapping lock scopes for the two snapshots and describe the line as two individually coherent snapshots, not one atomic cross-ledger instant. Write `members.json` through a same-directory temporary file, flush and fsync it, then atomically rename and fsync the directory.

**Verdict:** No—revision 1 is not safe to implement as written; authoritative identity, recovery idempotency, governor accounting, and immutable delivery targeting are blocking, although the no-expiry claim-time quiet behavior itself is sound through timed quiet, untimed quiet, boot recovery, and orphan re-pending.