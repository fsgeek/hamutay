# The assembly — design review, round three (final)

Date: 2026-09-16. Reviewed revision 3 at commit `b5584f7` against the running heartbeat, event-store, session-commit, tool, checkpoint, quiet-declaration, and GPU-lease mechanisms.

## Round-two findings, verified

| Finding | Status | Why |
|---|---|---|
| B1 — extension creates two child deliveries | paper-only | The child now has no independent outbox work and rides the parent closing, but “child first, then closing” in one multi-record append is not an atomic process-kill boundary, and the reducer does not explicitly map the child’s delivery truth to the parent closing’s delivery record. |
| B2 — landed does not prove timely offer | closed | The delivery reducer, post-fsync `landed_at`, strict `landed_at < closes_at` test, not-offered cap, and cancellation rule prevent a late or missing offer from producing assent. |
| B3 — activation can precede or outlive its closing | paper-only | Deterministic closing IDs, closing-before-activation, digest matching, idempotent activation keys, and the governing selector are sound; the skip-pass heuristic can nevertheless suppress a still-required activation repair after a transient failure. |
| B4 — member snapshot omits delivery identity | closed | Questions now snapshot canonical session and event-store paths, and a heartbeat binds only when its live store matches the configured path. Position provenance across later path generations remains an Important finding below. |
| B5 — initial quiet skip is never reconsidered | closed | Every question event is created, and one assembly-only predicate is specified for `next_pending`, `claim_next_pending`, and `summarize_event_log`; early-ended quiet can therefore expose the existing event. |
| B6 — grace can overrule an objection | paper-only | Wake start, event, and run identity plus the running-at-cutoff cap close the ordinary race, but an unreadable store and the declared position-commit loss still permit assent without an objection that the resident attempted to record. |
| I1 — outbox durability/failure model | paper-only | Store-before-ledger fsync ordering handles the cross-file direction, but the child/closing transition still relies on non-transactional multi-line append atomicity. |
| I2 — store locks can block the assembly indefinitely | closed | The pass limits each store lock to a two-second nonblocking retry window and releases it before opening the next store. |
| I3 — constitution cannot observe later activation | closed | The constitution is temporally neutral; provisional/active status is supplied by each event envelope. |
| I4 — assembly paragraph appears without tools | closed | Revision 3 gates the clause with the natural-shape assembly tools and excludes terminal-shape members from tool participation. |
| I5 — execution is not proof of the decision’s effect | closed | The invariant is honestly narrowed to a report, and the execution record copies the assented proposal digest. |
| I6 — checkpoint’s broad glob races the assembly ledger | closed | The design excludes `community/plaza/` from the generic loop and gives the assembly one locked snapshot and digest. |
| I7 — cost/pass frequency | paper-only | Four wakes is now the correct three-round maximum, but the proposed skip condition is not equivalent to “no repairable work” and can permanently strand outbox work. |
| I8 — inconsistent store-failure terminology | closed | `store_unreadable` is the single term and identical errors are deduplicated. |
| I9 — position-commit failure has no result | paper-only | A result is declared, but it deliberately loses a successful stance and proposes a framework log entry after the durable cycle record has already been written. |
| M1 — `members.json` ignore rule | closed | The implementation inventory explicitly requires `community/plaza/members.json`. |
| M2 — inbound event cannot accept a stable ID | closed | `build_inbound_event` is specified to gain a validated optional `event_id`. |
| M3 — “verbatim” positions are mutated with eligibility | closed | Closings use `{"record": <verbatim>, "eligible": bool}`. |
| M4 — stale `not_before` on closing delivery | closed | Closing delivery relies on the claim-time quiet predicate, not a persisted quiet snapshot. |
| M5 — two unnamed grace periods | closed | One named constant, `G = 60 min`, governs both cases. |

## Blocking

1. A close-time unreadable store can erase an objection and permit assent.

   **Mechanism.** The pass holds the assembly lock, gives each event store two seconds, and otherwise records `store_unreadable` ([assembly design §1](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-15-assembly-design.md:219)). The not-offered wait applies only when the question delivery itself was not landed. For a previously offered member, §7 step 2 requires a readable store to discover an in-window running wake, while §6 requires that same store to establish the completion join. The only assent caps are `not_offered` and `running_at_cutoff` ([§7 step 5](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-15-assembly-design.md:483)).

   **Why it fails.** Suppose door A has appended a `dissent` position, or is currently running a wake that has called `take_position(dissent)`. Its question was landed on time. At close, its store lock is busy or its JSONL is unreadable. The pass cannot prove the position completed and cannot observe the running wake. A is not `not_offered`, and it cannot be put in `running_at_cutoff`; two other assents can therefore produce `assented`. This is an objection losing because its completion evidence was temporarily unavailable. The current store API is indeed all-or-nothing: `EventStore._locked()` blocks around `_read_records_unlocked()`, whose malformed line raises ([events.py, `EventStore`](/home/tony/projects/hamutay/src/hamutay/events.py:492)).

   **Smallest change that fixes it.** Treat inability to read any snapshotted member store needed for the completion join or running-wake test as an unknown-at-cutoff condition. Wait through `G`; after `G`, cap any otherwise-assented result to `extended` or `unresolved`, exactly like `running_at_cutoff`. Never turn “eligibility unknown” into `eligible: false`.

2. A successful `take_position` may still be discarded and followed by an assented closing.

   **Mechanism.** Revision 3 buffers the stance, first commits the session record containing the successful tool activity, and then attempts the assembly-ledger append. On failure, it completes the wake anyway and declares the position lost ([assembly design §6, “Commit failure”](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-15-assembly-design.md:430)). This follows the current ordering: `_exchange_impl()` writes `_log_entry()`, appends cycle effects, and returns; only then does `run_next_event()` append `completed` ([taste_open.py, `_exchange_impl`](/home/tony/projects/hamutay/src/hamutay/taste_open.py:3127), [events.py, `run_next_event`](/home/tony/projects/hamutay/src/hamutay/events.py:2044)).

   **Why it fails.** A resident can receive a successful tool result for `dissent`; a transient ledger write failure then drops that stance; its wake still becomes `completed`; and the close pass sees `completed_without_position`. Other members can assent. That is exactly a recorded objection attempt being overruled by infrastructure. The proposed `_framework` event is also not durably captured by the current ordering: `tool_activity_full` has already been serialized before a post-commit `ToolExecutor.log_event()` could add it ([taste_open.py, `_log_entry`](/home/tony/projects/hamutay/src/hamutay/taste_open.py:3502); [executor.py, `log_event`](/home/tony/projects/hamutay/src/hamutay/tools/executor.py:125)).

   **Smallest change that fixes it.** Make successful position acceptance durable during the tool call as an append-only provisional position/intention bound to trusted `(event_id, run_id, record_id, wake_started_at)`; it becomes tally-eligible only through the existing completion join, and the highest sequence from that run implements last-call-wins. If the ledger append fails, the tool must return an error, not success. An alternative is a durable repair intent plus an assent cap until repair, but a hand-recoverable session record alone is insufficient.

3. The skip-pass heuristic can permanently disable the durable outbox and activation repair.

   **Mechanism.** A heartbeat skips when ledger size and mtime are unchanged and no known close or grace deadline has arrived ([assembly design §7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-15-assembly-design.md:438)). `store_unreadable` is nonterminal outbox state, and activation is described as a derivation run “at the end of every pass.”

   **Why it fails.** After a failed delivery attempt, the pass appends one deduplicated `store_unreadable` row. On the next poll the ledger is unchanged; if no close deadline is currently due, the heartbeat skips instead of retrying. This delays a question until its deadline and can strand a final closing forever because a terminal closing has no later deadline. The same logic can strand an activation whose append failed transiently after the assented closing existed. Thus “every pass repairs until landed” and “repairable activation” are false under the stated skip condition. The current heartbeat’s thirty-second polling makes that retry the natural recovery mechanism ([heartbeat.py, `HeartbeatLoop.step`](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:552)).

   **Smallest change that fixes it.** Skip only when the reduced ledger is quiescent: no non-landed/non-cancelled outbox entry, no assented procedure closing lacking its activation or rejection derivation, and no due close/grace transition. A `store_unreadable` result must schedule a retry no later than the next poll; unchanged bytes must not suppress it.

4. The child-first multi-record append does not supply the claimed process-kill atomicity.

   **Mechanism.** §7 step 7 writes the child line first and the closing line second in one `append_many`, then asserts there is no state in which the child exists without its closing ([assembly design §7 step 7](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-15-assembly-design.md:494)). The running analogue constructs two JSON lines and sends them through buffered `f.write()` ([events.py, `EventStore.append_many`](/home/tony/projects/hamutay/src/hamutay/events.py:542)).

   **Why it fails.** A file append containing multiple JSON records is not a transaction. A short write, interrupted buffered flush, filesystem error, or process kill during a partial write can leave the child line complete and the closing line absent or torn. With a complete child line, the ledger remains parseable but now contains precisely the forbidden exposed child; with a torn closing line, every later pass fails closed on the malformed ledger. `fsync` establishes durability after completed writes but cannot make two JSON records atomic. The design’s process-kill guarantee therefore exceeds the mechanism.

   **Smallest change that fixes it.** Make extension one ledger record: the closing record should contain the complete child question payload, and reducers should derive the child from that record. If a separate child record is required for indexing, append the closing first and make the deterministic child a repairable derivation from its embedded payload. A missing child can then be recreated; a child can never precede its authority.

## Important

1. The running session does not currently know the event identity in trusted framework state. `run_next_event()` passes an envelope string and `event_managed=True`; `OpenTasteSession.exchange()` accepts no event or running-status object, and `ToolExecutor.__init__()` receives no `event_id`, `run_id`, or `started_at` ([events.py](/home/tony/projects/hamutay/src/hamutay/events.py:2033), [taste_open.py](/home/tony/projects/hamutay/src/hamutay/taste_open.py:2770), [executor.py](/home/tony/projects/hamutay/src/hamutay/tools/executor.py:72)). Do not recover provenance by parsing the model-visible envelope. Pass a framework-owned wake context from the claim through `exchange()` to the executor, and refuse assembly tools when it is absent.

2. Eligibility should join all trusted wake coordinates, not only `record_id`. Revision 3 records `event_id`, `run_id`, and `wake_started_at`, but §6 says only that `record_id == completed.result_record_id` determines eligibility. Require the completed row’s `event_id` and `run_id` to match and require `wake_started_at` to equal that run’s stored `started_at`. Otherwise the newly added bindings are audit decoration rather than predicates.

3. The carried child’s delivery reducer is incomplete. A child plan names `carried_by_closing: <parent closing_id>`, while delivery rows are keyed by `(for, id, door)` and the reducer looks up the child’s own ID ([assembly design §2](/home/tony/projects/hamutay/docs/superpowers/specs/2026-09-15-assembly-design.md:303)). State explicitly that child offer time and lifecycle are reduced through the parent closing’s `(closing_id, door)` delivery row and event ID. Without that rule, a literal implementation considers every child never landed.

4. Path snapshots do not define positions made after a membership-path generation changes. An old question points at the old store, but a restarted heartbeat can be correctly bound to a new configured store and successfully call `take_position` on that old question. Its completion exists only in the new store, so a snapshot-based close cannot join it and cannot see that wake running. Either freeze member paths while lineages are open, or record and govern path-generation transitions so the question can cap rather than ignore a stance.

5. Position eligibility must explicitly exclude doors absent from the question’s member snapshot. `member` is trusted from the current binding, but a newly enrolled door can still name an older open question. `take_position` should refuse it, and tally eligibility should independently require membership in `question.members`; otherwise a later door can enter an earlier tally.

6. Cancellation should cover every non-landed state, not only the word “planned.” After a closing exists, a question whose latest delivery state is `store_unreadable` is still selected by the outbox’s “not landed, cancelled, or carried” rule. The cancellation check must run before any retry and cancel `planned` or `store_unreadable` alike, so an already-closed stale question is never appended.

7. The claim-predicate integration must preserve the original pending event. `summarize_event_log()` currently classifies compact `summarize_event_history()` objects, which omit `defer_to_declared_quiet` and `assembly_question_id` ([events.py, `summarize_event_history`](/home/tony/projects/hamutay/src/hamutay/events.py:1436), [`summarize_event_log`](/home/tony/projects/hamutay/src/hamutay/events.py:1526)). The implementation must either classify from the original pending record or deliberately carry those fields into the summary. `next_pending()` must likewise be refactored to use the same full locked snapshot rather than its present independent `latest_by_event_id()` read.

8. The implementation must flush userspace buffers before each promised `fsync` and verify full writes. This applies to the new assembly ledger and `append_if_absent`; merely calling `os.fsync()` after a buffered text write does not itself define the required boundary.

## Minor

1. The fixed question header says a dissent or deferral “extends the question” even in round three, where it produces `unresolved`. Say “extends while rounds remain; otherwise leaves it unresolved.”

2. `landed_at < closes_at` permits a delivery one instant before the deadline to count as offered. That is deterministic and conservative enough for ledger integrity, but it provides no minimum deliberation interval. If intentional, name it as policy.

3. Set the child’s `opened_at` explicitly to the parent’s `closed_at`; “same duration from `closed_at`” should not leave one timestamp implicit.

4. Describe outbox insertion as idempotent at-most-one creation of the pending event, not “exactly once delivery.” Each event legitimately acquires multiple lifecycle rows, and the model may never claim it.

## Questions the implementer must answer

1. What durable state prevents assent when a snapshotted event store cannot be read at close and position eligibility or an in-window running wake is therefore unknown?

2. At what exact write does `take_position` become entitled to return success, and how is that write repaired without human intervention?

3. What condition makes the skip-pass cache quiescent, and where is the next retry time stored for `store_unreadable`, missing closing delivery, and missing activation?

4. Is the extension transition one physical ledger record, or what repair rule makes a separately encoded child impossible to expose before its closing?

5. What trusted API carries the claimed event, running `run_id`, and `started_at` from `run_next_event()` through `OpenTasteSession` into `ToolExecutor`?

6. For a carried child, which delivery row supplies `landed_at`, and which event history supplies its Empty Chair state?

7. Can member session/event paths change while any lineage is open? If yes, which store or generation governs a position and the running-wake cutoff?

8. Does closing eligibility require the complete `(member, event-store generation, event_id, run_id, result_record_id, started_at)` join, or only `result_record_id`?

9. How does the assembly ledger recover a short or torn final append caused by process kill, given that current JSONL readers reject any malformed line?

## Verdict

No: the first question cannot safely be put on revision 3 exactly as written. The ordinary-path rule, lineage tally, timely-offer cap, deterministic activation, quiet handling, and closing-carried child are now coherent, but four remaining mechanisms cross the final safety threshold: an unreadable member store can erase an objection and allow assent; a successful position can be deliberately lost; the skip heuristic can permanently strand a closing delivery or activation; and the child-first multi-record append does not provide the claimed process-kill atomicity. Once those are disposed with fail-closed assent caps and durable, repairable transitions, the design’s core is sufficient for trustworthy self-ratification.