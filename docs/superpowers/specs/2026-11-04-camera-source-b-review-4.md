# Camera Source B r4: Codex review, round four (2026-11-05)

Read-only review of r4 (2fab37d), copied from its report below. r5 should answer it.

## Custodian's note for whoever writes r5 (2026-11-05)
Findings per round: 12, 9, 6, 8. The review is not converging, and most Blocking findings since round two
(aggregate keys, replay regrouping, checkpoint/spool ordering) come from one choice: **coalescing** many audit
lines into one record keyed by its first line, then trying to make that aggregate exactly-once. Proposal for
r5: **drop coalescing in Source B.** One `db_entries` record per audit line, `_key` = hash of (generation, byte
offset). Replay is then idempotent by construction (a conflict means the same line), the spool can hold one
record per line, and the checkpoint becomes an optimization, not a correctness device. Precondition: measure
the read volume on `apacheta` first. The doors' cycle persistence is writes, which are not recorded, so reads
are likely low. Measure it on a throwaway restore of the newest dump with a door-shaped workload, or with a
short audit window after cutover, and keep coalescing out unless the volume forces it back in. Also from this
round: B6′ must disclose possible silent loss from writes after finalization (#2); the "under ten minutes" figure
needs to become a stated target with exceptions or an enforced maximum (#5); and the MAC promise needs
narrowing to offline inspection (#7).

---

**Blocking findings remain:** B5″ leaves spool recovery ambiguous, and B6′ overstates what its deletion rule protects.

The reviewed files match `2fab37d`. I applied r4’s precedence rule throughout. Runtime failure scenarios below are **hypotheses**, not observed incidents.

Round-three dispositions:

- **A — Partly:** UUID generations improve identity, but restart matching still assumes that a reused `(inode, first-line hash)` identifies the old generation. [B5′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:160)
- **B — Partly:** the confirmed Docker Desktop limitation is respected; quiet-based sealing replaces the impossible inspection, but its claimed protection against later writes is unsound. [B6′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:173)
- **C — Partly:** ambiguous bindVars removal is abandoned, and suffix validation improves; damaged input can still supply a matching fake suffix. [B4′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:149)
- **D — Partly:** retention loss now has a detection rule and durable cursor, but scan acknowledgement, timestamp boundaries, and failure recovery remain unspecified. [B7′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:179)
- **E — Resolved:** ledger append and both fsyncs precede capacity deletion; failure prevents deletion and triggers an alert. [B7′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:179)
- **F — Resolved:** the overriding cutover paragraph explicitly installs and checks the mount before step 2. [Cutover ordering](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:187)

The following findings concern r4’s replacement mechanisms; some continue earlier defects rather than introduce wholly new ones.

1. **Blocking — a spooled batch and the database checkpoint lack a recovery protocol.**

   B5″ specifies “one fsync’d spool line holding the whole batch,” followed by resumption from “the last committed checkpoint.” It does not define whether that means the database checkpoint or the latest checkpoint held in the spool, nor require replay before fresh ingestion. [B5″](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:166)

   **Hypothesis:** the database checkpoint precedes A; A is durably spooled; the reader crashes; B arrives in the same window. Recovery reads the database checkpoint and constructs aggregate A+B. Replaying the original A first leaves A+B conflicting on its first-line-derived key. Treating that conflict as already stored loses B; aborting can leave recovery stuck. “Partial windows close at each batch” does not resolve which batch boundaries govern recovery.

   Require an authoritative checkpoint across database and spool, ordered replay before overlapping fresh work, recognition of already committed batches, and checkpoint advancement that cannot regress. One spool line preserves a batch’s representation; it does not establish those rules.

2. **Blocking — B6′ acknowledges uncertainty, then incorrectly promises protection after that uncertainty matters.**

   “This is evidence, not proof” is honest. But “any later growth is still read” is qualified only by keeping the descriptor open **until deletion**. The final EOF check cannot exclude an append after that check or after the reader closes. [B6′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:173)

   **Hypothesis:** one writer retains the old descriptor while another produces the required new-file line. After five quiet minutes, the reader seals, checks EOF, unlinks and closes. The old writer subsequently appends. Linux permits an open file to survive unlinking; those writes can succeed without an audit-write error, while the camera has no remaining reader for them. [Linux `unlink` semantics](https://man7.org/linux/man-pages/man2/unlink.2.html)

   The announcement must explicitly disclose **possible silent loss from writes after finalization**, or finalization needs a stronger writer-exclusion mechanism. The present disclosure does not honestly bound the consequence.

3. **Significant — B5′ confuses an unambiguous present-file match with a proven historical identity.**

   “Two present files can’t share an inode” establishes uniqueness among files currently present. It does not establish continuity with persisted state. “Whose file is gone is closed” works only if absence is observed before replacement. [B5′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:160)

   **Hypothesis:** during reader downtime, an old file disappears and a replacement or remounted filesystem reuses its inode. If its first line also repeats—the content-repetition condition from round-three A—the replacement matches the old generation. Applying the old offset skips new events. UUID assignment does not help when recovery assigns the wrong existing UUID.

   The state-file update also lacks an explicit atomic replacement/fsync contract. Losing an assigned generation after its records commit can instead produce a new UUID and duplicate records.

4. **Significant — the named transaction mechanism needs explicit failure and durability requirements.**

   A stream transaction is suitable for records plus checkpoint on this deployment. However, ArangoDB documents that failed individual operations do **not** automatically abort it. It separately documents delayed durability unless synchronization is required. [Stream transaction error handling](https://docs.arango.ai/arangodb/3.12/develop/transactions/stream-transactions/), [transaction durability](https://docs.arango.ai/arangodb/3.12/develop/transactions/durability/)

   **Hypothesis:** one record insertion fails, but checkpoint insertion and commit succeed; the transaction atomically commits an incomplete application batch. Alternatively, an acknowledged unsynchronized transaction disappears after a host crash, once the raw file or replay copy has been retired.

   B5″ should require checking every operation, aborting on unresolved errors, resolving uncertain commit outcomes, and obtaining durable acknowledgement before retiring recovery material. Those requirements substantiate its “wholly stored” claim.

5. **Significant — the new “under ten minutes” contents promise is not enforced.**

   The announcement promises raw contents exist “for under ten minutes.” B6′ requires a new complete line stamped after HUP, regardless of how long the old file has been quiet. [Contents promise](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:43), [B6′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:173)

   **Hypothesis:** the final sensitive query is logged, rotation succeeds, and the server then remains idle for an hour. No new qualifying line arrives, so the old file remains unsealed and undeletable. Reader downtime also defeats the bound; the retained capacity policy concerns files older than thirty minutes and only acts above 75% usage.

   State a normal-operation target with its exceptions, or specify an enforceable maximum and the associated loss policy.

6. **Significant — B7′ makes the cursor durable without defining durable acknowledgement of its findings.**

   Its explicit write-before-delete ordering covers capacity deletion. No corresponding ordering connects log-derived ledger entries with cursor advancement. [B7′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:179)

   **Hypothesis:** a scan finds `cannot log data`, durably advances its cursor, then crashes before the loss entry becomes durable. The next scan skips those failures; the oldest-line comparison does not detect this because rotation was unnecessary.

   Timestamp-only progress also needs equal-timestamp handling, replay deduplication, container identity, scan-error behavior, and clock-regression policy. **Conditional hypothesis:** a backward clock step produces new messages older than the cursor; timestamp filtering excludes them while the oldest retained line remains older still.

   Docker documents timestamp filtering and RFC3339Nano output, not a unique sequence cursor. Its documented 100 MB default is byte retention, not a minimum time guarantee. The spec’s “far more than a minute” assertion supplies no measured bound. [Docker logs](https://docs.docker.com/reference/cli/docker/container/logs/), [local driver](https://docs.docker.com/engine/logging/drivers/local/)

7. **Significant, conditional — HMAC protects offline guesses, but the stated guarantee also covers an unspecified online oracle.**

   Keeping the key from camera readers addresses offline guessing. The broader statement that readers “cannot test a guessed query or value against the record” needs a threat-model qualification. [B4′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:155)

   **Hypothesis:** a camera reader can submit an audited query such as `RETURN @pin`, then inspect the resulting MAC. Repeating candidate values tests them against an observed MAC without obtaining the key. Because the MAC covers only query-part bytes, the same bytes can match across database users or databases.

   This depends on reader query capabilities, which the spec does not establish. Narrow the promise to passive/offline inspection or specify how this oracle is excluded.

8. **Minor — the anchored suffix cannot identify every damaged record.**

   B4′ says a missing suffix causes rejection, “which is how a damaged or truncated line is treated.” A fake suffix that becomes the end of damaged input still matches. [B4′](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:149)

   For example, input ending with:

   ```text
   RETURN 1 // , id 9, token QRY9, exit code 0, elapsed: 0.1s
   ```

   passes the prescribed regex and produces query part `RETURN 1 // `. I confirmed this mechanically in memory. **Hypothesis:** damage removes the genuine later suffix while leaving this fake boundary as the supplied record’s end. An intact record with a genuine later suffix works correctly.

   Promise rejection of suffix-invalid damage, rather than detection of arbitrary truncation.

**The listed fixtures would not yet make the spec sufficient for complete blind acceptance tests.** They would establish useful parsing examples, but expected outcomes remain undecidable for:

- Database/spool checkpoint authority, replay ordering, uncertain commits, duplicate batches, spool exhaustion and torn tails.
- Durable generation-state recovery and replacement files matching stale identity tuples.
- Canonical record-key serialization, batch boundaries, and ordering across files.
- Seal timing across restarts, missing post-HUP lines, growth after sealing, and accepted loss after deletion.
- Cursor/ledger acknowledgement, equal timestamps, container replacement, scan failure and clock regression.
- MAC-key lifetime, missing-key behavior, and a fixed test key for expected MAC values.

The Tests section also still requires sealing “only after arangod lets go.” That conflicts with B6′’s explicitly observational contract and cannot remain the acceptance oracle. [Tests](/home/tony/projects/hamutay/docs/superpowers/specs/2026-11-04-camera-source-b-design.md:255)

No files were modified. Commands ran as UID 1000; no containers or services were controlled, and no connection to port 8529 was made.

