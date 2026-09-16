# The assembly — design review, round two

Date: 2026-09-15. Reviewed revision 2 at commit `c89c3ef` against the current heartbeat, event-store, session-commit, tool, checkpoint, quiet-declaration, and GPU-lease mechanisms.

## Round-one findings, verified

| Finding | Status | Why |
|---|---|---|
| B1 — quorum can terminate or overrule dissent | closed | §2 defines the highest-`seq` eligible position across the lineage as active, and §8 checks active `dissent`/`defer` before quorum. Silence no longer replaces an objection. |
| B2 — a position is not joined to a completed wake | paper-only | The completion join and `late_position` exist, but the grace watches only the question-delivery event, permits unrestricted post-deadline positions, and can still assent while an objection is buffered in a running wake. |
| B3 — closing fence loses delivery; extension is not idempotent | paper-only | Stable event IDs and `append_if_absent` repair one crash window, but the child is still a separately planned question, so normal and crash recovery can deliver it independently of—and before—the merged closing. |
| B4 — Empty Chair cannot represent observed states | closed | The schema now covers pending, running, expired, failed, suppressed, completed-without-position, unreadable, and not-delivered states without attributing motives. |
| B5 — convene-time quiet sampling races claims | paper-only | Flagged events can be rechecked at claim time, but a delivery permanently marked `skipped` has no event to re-evaluate if a later wake ends the quiet early. |
| B6 — ratification lacks a durable transition | paper-only | Procedure records and payloads now exist, but activation is appended before its closing and is neither atomic with nor recoverably derived from that closing. |
| I1 — no authoritative member/binding configuration | paper-only | `AssemblyBinding` derives door identity, but questions snapshot only names, not store paths, and hosted heartbeats may still poll a custom `--event-log-path` different from the outbox target. |
| I2 — closing omits actual tally inputs | closed | `seq`, active position IDs, quorum, objection/assent sets, and the evaluation trace are recorded. |
| I3 — cost omits closing wakes | paper-only | The intended merged design gives four wakes, but the specified child delivery produces separate child events too, restoring six worst-case wakes. |
| I4 — execution is not bound to the decision | open | The CLI checks for an assented closing, but `execution.what` remains unrelated free text and the execution record contains no canonical decision payload or digest. |
| I5 — required reasons contradict “offered” | closed | Position reasons are optional and the assembly wording is descriptive. |
| I6 — canonical paths, lock order, checkpoint | paper-only | The lock order is adequate, but the existing broad checkpoint loop would still copy `community/plaza/assembly.jsonl` unlocked unless plaza is excluded or handled specially. |
| I7 — testimony/withdrawal cutoff unspecified | closed | Acceptance is under the ledger lock and requires `now < closes_at`; refused attempts do not enter the tally ledger. |
| I8 — one unreadable store can abort closing | paper-only | The design says to continue, but current `EventStore._locked()` blocks indefinitely; no nonblocking or bounded lock mechanism is specified. |
| M1 — closing delivery permits an unexplained absence | closed | The closing delivery schema now requires an event delivery. |
| M2 — naive timestamps accepted | closed | Assembly entry points are specified to use strict timezone-bearing wrappers. |
| M3 — test assumes four question events | closed | Tests now require one delivery outcome per member. |
| M4 — cross-ledger report appears atomic | closed | `events report` is explicitly observational. |

## Blocking

1. The extension transition still creates two deliveries for the next round.

   **Mechanism.** Section 7 step 5 writes the deterministic child question with its own deliveries in state `planned`; step 7 separately writes the parent closing with another planned event per member; the outbox processes every planned `question` and `closing`. The closing event also embeds the child question.

   **Why it fails.** In the normal path, the outbox lands both a standalone child-question event and a closing-plus-child event. A member may wake twice and replace its position twice. A crash after writing the child but before writing the parent closing is worse: the next pass sees the child’s planned deliveries and can send round 2 before the round-1 closing exists. This is precisely the ordering failure round one identified. It also invalidates the four-wake cost estimate. A merged non-expiring closing event cannot simultaneously have the child question’s expiring delivery lifecycle without an explicit virtual-delivery rule.

   **Smallest change.** Give an extended child no independent outbox work. Its per-member delivery must reference the parent closing event ID, with a state such as `carried_by_closing`, and the outbox must ignore it as a standalone question. Represent parent closing plus child creation as one recoverable ledger transition, or make a child dormant until a parent closing containing its complete payload exists. No recovery path may expose or deliver the child first.

2. “Landed” does not establish that a question was offered before it closes.

   **Mechanism.** The outbox runs before closing. It changes a delivery from effective `planned` to `landed`, after which closing step 1 tests whether any delivery is still planned. A store unreadable for 60 minutes is allowed to become `not_delivered`.

   **Why it fails.** If a daemon was down or a store becomes readable only after `closes_at`, the same pass can land the question and immediately close it: after the outbox writes its `delivery: landed` record, no delivery remains planned. The member had zero opportunity to claim it. If a store remains unreadable through the grace, two other members can assent to and mechanically activate the bootstrap procedure even though that door was never offered the question. Later outbox repair also delivers the already-closed stale question before or beside its closing.

   The embedded delivery state is immutable JSON, so the design also needs an explicit reducer over later `delivery` records; otherwise every source `question.delivery` remains literally `planned`.

   **Smallest change.** Define the delivery reducer and record `landed_at`. A question must not assent or activate if any non-quiet member was not landed before its deadline. A late repair must either extend/reopen the question with a new deadline or force the current result to `unresolved`; it cannot count as timely offer. When a question closes with a delivery never landed, cancel that question delivery durably and repair only its closing.

3. Procedure activation can precede, duplicate, or name a closing that never exists.

   **Mechanism.** Section 7 step 6 appends the `procedure(status: active)` record, including `activated_by_closing_id`; step 7 then writes the closing. The closing ID is not specified as deterministic. The active procedure is simply the highest-`seq` active record.

   **Why it fails.** A crash between steps 6 and 7 leaves an active procedure without an assented closing. Recovery sees the question as unclosed, recomputes it, and can append a second activation naming a different closing ID. Nothing requires the active record’s payload and artifact digest to match the provisional record proposed by the question. Nor is the governing selector defined when no active procedure exists but several provisional bootstrap versions do. Consequently the first question can be written, but it cannot safely perform the self-ratification effect it describes.

   **Smallest change.** Preassign a deterministic closing ID. Write the closing before activation, then make activation a repairable, idempotent derivation keyed by `(procedure_id, closing_id)`, refusing activation unless that exact assented closing exists and proposes the same immutable payload/artifact digest. Define procedure-ID and version uniqueness and the governing selector: a fixed built-in bootstrap rule while none is active, otherwise the active procedure snapshotted at convene.

4. The membership snapshot does not snapshot delivery identity.

   **Mechanism.** `members.json` maps doors to session-log paths, `AssemblyBinding` resolves it at boot, and each question stores only `members: ["heartbeat", ...]`.

   **Why it fails.** The running heartbeat accepts `--event-log-path` independently of `--log-path` in `heartbeat.main()` (`src/hamutay/heartbeat.py:1080-1089`). Except for the GPU-bound door’s separate canonical-path check, a bound hosted heartbeat can therefore poll one event store while the assembly derives and writes another. After a membership-path change, different heartbeats retain different boot-time maps; whichever heartbeat obtains the assembly lock may deliver an old question to the new path. The question contains no old path with which to honor §579’s promise that a removed member still receives its closing.

   **Smallest change.** Snapshot, per member, the canonical session path and event-store path in every question. Require a bound heartbeat’s actual `EventStore.path` to equal the configured path, or put the explicit event-store path in `members.json`. All outbox and close work for that question must use its immutable snapshot, never the caller’s current boot-time map.

5. Quiet declarations that initially outlast a question are never re-evaluated.

   **Mechanism.** Convening permanently records `delivery.state: skipped` when the current joined quiet has `until >= closes_at`. Claim-time deferral applies only to events that were created.

   **Why it fails.** `quiet_declaration_for_latest_wake()` deliberately ends a declaration when a later wake completes (`src/hamutay/events.py:188-207`). If an unrelated event ends that quiet before the assembly deadline, there is no pending assembly event to become claimable. The convene-time snapshot—not the claim-time predicate—therefore remains authoritative for exactly the case revision 2 says is dynamic.

   For deliveries that do exist, modifying only `EventStore.next_pending()` and `claim_next_pending()` is also insufficient. `HeartbeatLoop.step()` derives its sleep and active state from `summarize_event_log()` (`src/hamutay/heartbeat.py:606-624`), whose pending classification still uses only `is_due()` and `is_expired()` (`src/hamutay/events.py:1608-1624`). A quiet-deferred event would be reported runnable and can drive a zero-sleep spin.

   **Smallest change.** Always create the preassigned question event. Use one assembly-only effective-claim predicate, based on the same locked record snapshot, in `next_pending`, `claim_next_pending`, and event summarization. If the currently joined quiet still outlasts expiry, terminalize it as `expired/skipped_by_quiet` without a wake; if another wake ended the declaration, it becomes claimable. The predicate must be gated solely by `defer_to_declared_quiet`, leaving all non-assembly events byte-for-byte unchanged.

6. The 60-minute grace can still overrule an objection.

   **Mechanism.** Closing waits only while that member’s question-delivery event is `running`. `take_position` is offered on bound event-managed natural wakes generally, buffers its result until cycle commit, and does not reject merely because `now >= closes_at`.

   **Why it fails.**

   - A member can call `take_position` during another event. Its question delivery may already be `completed`, so the close pass does not see the position-bearing wake as running and can close before commit.
   - While one delivery keeps the question open during grace, other members can submit new positions after `closes_at`; no deadline predicate excludes them.
   - After grace, the rule may return `assented` while a question wake is still running. If that wake has already called `take_position(dissent)` but not completed, commit converts it to `late_position`. The system has then recorded and ignored the objection after telling the resident its tool call succeeded.

   The completion join in `events.run_next_event()` occurs only after `OpenTasteSession._exchange_impl()` returns and `append_completed_atomic()` runs (`src/hamutay/events.py:2044-2087`). The ledger cannot infer the buffered stance from the question event’s `running` status.

   **Smallest change.** Bind every position to its source `event_id`, `run_id`, and `started_at`, and enforce the cutoff at commit: after `closes_at`, accept only a position from the question’s already-running delivery and only inside the grace. Either persist a provisional position intent when the tool succeeds, or prohibit `assented` whenever an eligible member’s delivery remains running at cutoff; use `extended`/`unresolved` instead. A recorded objection attempt must never coexist with an assented closing that ignored it.

## Important

1. The durable-outbox guarantee is process-crash idempotence, not durable exactly-once delivery. `EventStore._append_unlocked()` performs an ordinary text append without `fsync` (`src/hamutay/events.py:519-527`). A power loss can lose or tear the store append after the ledger records `landed`, and later passes inspect only planned work. State the failure model, or fsync the store before appending `landed` and re-verify even landed deliveries. `append_if_absent` should require the original pending event record, not merely any lifecycle row with the same ID.

2. Per-door failure isolation needs a bounded lock operation. `EventStore._locked()` uses blocking `flock(LOCK_EX)` (`src/hamutay/events.py:509-517`). While `assembly.pass_` holds the assembly lock, one wedged store-lock holder can stall every other delivery, every closing, and every position commit. Add a nonblocking or timed read/append API for the assembly pass and define its evidence-backed `store_unreadable` result.

3. Procedure activation cannot update the constitution as described. `heartbeat.main()` calls `build_constitution()` once and passes the resulting string into `OpenTasteSession` (`src/hamutay/heartbeat.py:1175-1187`). A later activation does not remove the provisional sentence from any running session. Either make the assembly paragraph’s dynamic portion resolve per exchange, add an explicit session-prefix refresh on each pass, or keep the constitution temporally neutral and put procedure status only in event envelopes.

4. Assembly tool descriptions require the same per-wake gating already used for `declare_quiet`. `_build_messages()` explicitly removes the quiet clause when that tool is unavailable (`src/hamutay/taste_open.py:2253-2280`). The proposed assembly paragraph always names `take_position` and `convene`, including terminal-mode, direct, and terminal-surface wakes where those tools are absent. Define an assembly constitution clause that is removed whenever the assembly tools are not offered, and decide whether terminal-shape members can participate at all.

5. Execution remains a report, not proof that the assented action was executed. The closing reference proves which question was cited, but `execution.what` can still describe anything. Put an immutable `decision_payload` or digest in actionable questions and copy that exact value into execution records; otherwise narrow Invariant 8 to say the custodian reports an action against an assented closing.

6. The checkpoint change must account for the existing broad glob. `deploy/checkpoint-community-log.sh:33-52` copies every `community/*/*.jsonl` without per-log locks. Once plaza exists, that loop includes `assembly.jsonl` before any proposed special locked snapshot. Exclude plaza from the generic loop or acquire `assembly.jsonl.lock` at that point; do not produce both an unlocked generic digest and a locked special digest.

7. The stated wake cost is not true until Blocking 1 is fixed. As written, three rounds produce three question events, two merged extension events, and the final closing: six wakes per participating member, not four. Separately, every bound heartbeat runs the pass before the GPU and budget gates on every `step()` (`src/hamutay/heartbeat.py:552-565`). At a 30-second poll, four idle doors can execute up to 11,520 full-ledger passes per day. Specify indexed/reduced in-memory state or at least measure the repeated whole-JSONL scans and lock hold time.

8. Store-failure absence terminology is inconsistent. Section 7 step 1 says an unreadable delivery closes as `not_delivered`; step 4 says `store_unreadable`; Error handling uses both. Choose one lifecycle reason and carry the underlying read/lock error in `detail`. Repeated failures should not append a new identical `delivery: store_unreadable` row every 30 seconds indefinitely.

9. Position commit needs a stated failure result. `_exchange_impl()` first commits the session record, then event-store effects, and only afterward can return to `run_next_event()` for the completed status (`src/hamutay/taste_open.py:3110-3141`). Adding a third assembly-ledger append means an I/O or malformed-ledger failure after the tool returned success can terminalize the source event as `failed` with no position. Specify whether this is accepted declared loss, a retryable event failure, or a durable position intent repaired from the session record.

## Minor

1. `members.json` is not currently ignored by `.gitignore`; only `community/*/door.json` and `community/*/*.jsonl` are covered. Add the intended rule explicitly.

2. `build_inbound_event()` always generates its own UUID (`src/hamutay/events.py:290-330`). Add a validated optional `event_id` parameter instead of constructing an event and mutating its identity afterward.

3. A closing cannot both contain position records “verbatim” and add `eligible: false` directly to those records. Store `{record: <verbatim>, eligible: bool}` or a separate eligibility map.

4. `closing.delivery.not_before` is unnecessary unless closing deliveries use a convene-time snapshot. Claim-time quiet deferral supplies the effective delay and avoids persisting a stale value.

5. Define whether the 60-minute unreadable-store grace and running-wake grace are one constant or two independently named policy values.

## Questions the implementer must answer

1. What exact failure model supports “exactly once per store”: process kill, kernel crash, or power loss? Where are the required flush/fsync boundaries?

2. What durable fact proves that a member was offered a question in time, and can a procedure activate when any non-quiet member was never offered it?

3. Does an extended child have its own event ID, or does its delivery reference the parent closing event? Which lifecycle status supplies that child’s Empty Chair evidence?

4. May an outcome be `assented` while any question delivery or position-bearing wake is still `running` at the cutoff?

5. Which positions committed after `closes_at` are eligible, and how is eligibility bound to a wake that began before the deadline?

6. When no procedure is active but several provisional versions exist, which rule governs ordinary questions and the next bootstrap question? How are procedure IDs, version numbers, payloads, and artifact digests made immutable?

7. Does a question snapshot door names only, or the exact session and event-store paths? What happens when heartbeats restart against different generations of `members.json`?

8. How does a running session learn that the procedure became active so its constitution stops saying it is provisional?

9. What timeout or nonblocking rule turns an unavailable event-store lock into `store_unreadable` without holding the assembly ledger indefinitely?

10. Is `execution` intended to prove performance of the assented payload or merely record a custodian’s claim? The current schema can support only the latter.