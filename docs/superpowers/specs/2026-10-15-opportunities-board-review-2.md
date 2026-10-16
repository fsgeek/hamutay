**r2 does not yet close every r1 finding.** The main remaining problems concern event lifecycle, filter changes, quiet authority, and assembly procedure.

References to “spec” below mean [the r2 design](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md).

**Blocking**

1. **Failed board events do not automatically become eligible for the next wake.**  
   [Spec:98](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:98) promises that failed batches remain unshown and retry next time. Existing ordinary failures are terminal: [events.py:943](/home/tony/projects/hamutay/src/hamutay/events.py:943). Only qualifying window failures receive one compact retry; its second failure is terminal: [events.py:2620](/home/tony/projects/hamutay/src/hamutay/events.py:2620). Boot recovery re-pends **running**, not failed, events: [heartbeat.py:117](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:117). Reconciliation cannot recreate them through `append_if_absent`.

   Completed-event coverage is a workable conservative definition, but r2 needs an explicit board retry policy and durable batch membership. The current runner receives one event and completes that event: [events.py:2497](/home/tony/projects/hamutay/src/hamutay/events.py:2497), [events.py:2586](/home/tony/projects/hamutay/src/hamutay/events.py:2586). Define how every batch member completes, fails, re-pends, and recovers after partial writes. Also distinguish “no committed coverage” from “not shown”: state may survive a failure, as the existing failure notice correctly explains at [events.py:1494](/home/tony/projects/hamutay/src/hamutay/events.py:1494).

2. **Clearing and re-enabling a filter can permanently lose an unshown opening.**  
   [Spec:76](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:76) supersedes unclaimed events, then promises scans that queue unshown matches. Example: opening matches → pending event → clear filter → superseded → restore filter. Its deterministic ID already exists, so [events.py:583](/home/tony/projects/hamutay/src/hamutay/events.py:583) rejects re-creation regardless of status.

   Specify a supported reactivation transition or generation-aware delivery scheme. Merely rescanning with the same ID does not repair this. Filter changes also need serialization or generation checks so an older reconciliation pass cannot enqueue stale matches after clearing.

3. **Board and NMI IDs can collide. This is a new r2 hazard.**  
   Both [spec:89](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:89) and [spec:154](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:154) use `uuid5(door, sequence)`. Board sequence 100 and plaza NMI sequence 100 therefore produce the same ID for the same door. `append_if_absent` silently suppresses whichever arrives second.

   Use distinct board/NMI namespaces or include the stream and record type in the UUID name.

4. **The envelope remains unbounded.**  
   [Spec:108](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:108) limits full entries to ten but includes **every** remaining title and ID. Field-length limits bound individual records, not an accumulated backlog across writers and days. “Envelope size is bounded” is therefore false.

   Specify a total byte/token bound and pagination. Only entries actually represented in the admitted envelope should gain coverage. Compact retry currently reduces context-result projection, not arbitrary event content: [events.py:2538](/home/tony/projects/hamutay/src/hamutay/events.py:2538). An oversized board envelope can otherwise exhaust its retry and encounter finding 1.

5. **Question 3’s participation rule is not procedure v1.**  
   [Spec:209](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:209) requires every door to take a position. Procedure v1 uses `ceil(half)`: [procedure-v1.json:4](/home/tony/projects/hamutay/deploy/assembly/procedure-v1.json:4). Under [rule.py:14](/home/tony/projects/hamutay/src/hamutay/assembly/rule.py:14), one assent plus one abstention among four doors can assent while two remain silent. Completed-without-position absences do not themselves impose a cap: [close.py:214](/home/tony/projects/hamutay/src/hamutay/assembly/close.py:214).

   **The required change is a procedure amendment raising participation quorum.** For the frozen four-door membership, a procedure v2 with numeric `quorum: 4` works with existing consent-v0; no new consent algorithm is necessary if abstention counts as taking a position. Do **not** write `quorum: "all"`: [records.py:38](/home/tony/projects/hamutay/src/hamutay/assembly/records.py:38) currently interprets every noninteger value as half.

   If every door must specifically **assent**, abstentions must additionally block; that requires a rule change. Alternatively, retain v1’s tally and explicitly describe full participation as an additional execution condition. Prose in the question alone does not change its governing procedure: [convene.py:63](/home/tony/projects/hamutay/src/hamutay/assembly/convene.py:63).

6. **Appending `nmi` records needs a compatibility rollout gate.**  
   [Spec:152](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:152) adds a new plaza record type. Current strict readers reject everything except message/delivery records: [records.py:197](/home/tony/projects/hamutay/src/hamutay/plaza/records.py:197), [records.py:216](/home/tony/projects/hamutay/src/hamutay/plaza/records.py:216). The first NMI would make older running readers reject the whole plaza.

   Require reader compatibility before enabling the writer, including outcome records. Existing deployment readiness checks concern `carrier`, and the loaded-code probe proves only that capability: [check-plaza.sh:28](/home/tony/projects/hamutay/deploy/check-plaza.sh:28), [mcp.py:96](/home/tony/projects/hamutay/src/hamutay/plaza/mcp.py:96).

**Should-fix**

7. **Quiet transparency is implementable, but its exception needs a precise commit rule.**  
   [Spec:140](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:140) says to skip NMI wakes while allowing their explicit quiet changes to govern. Define that as: successful explicit change/reset wins; otherwise skip the NMI outcome. Failed or crashed declarations must remain inert, preserving the existing completion join at [events.py:190](/home/tony/projects/hamutay/src/hamutay/events.py:190) and [taste_open.py:3911](/home/tony/projects/hamutay/src/hamutay/taste_open.py:3911).

   Introduce a separate quiet-authority resolver; do not globally hide NMI outcomes from actual wake history or failure reporting. Non-NMI failures must retain their existing quiet-ending semantics, and NMI failures must still appear in [failed_wake_notes](/home/tony/projects/hamutay/src/hamutay/events.py:1445).

   “Ending it” also needs an explicit operation or documented tool encoding. The current schema offers only a nonblank declaration; silence cannot mean reset once NMI silence becomes transparent: [schemas.py:704](/home/tony/projects/hamutay/src/hamutay/tools/schemas.py:704).

8. **There are still quiet-loss and misinformation paths beyond the NMI outcome itself.**

   - A continuation requested during an NMI becomes an ordinary reflection without quiet deferral: [events.py:479](/home/tony/projects/hamutay/src/hamutay/events.py:479), [events.py:254](/home/tony/projects/hamutay/src/hamutay/events.py:254). It can immediately wake and end the preserved quiet. Specify whether that constitutes an explicit resident choice to end quiet, or whether such continuations defer.
   - Changing future CLI sends does not change already-pending legacy inbound events lacking the flag. Those remain claimable during quiet under [events.py:735](/home/tony/projects/hamutay/src/hamutay/events.py:735), and their ordinary outcomes still end it. Define migration or claim-time treatment.
   - Updating the NMI envelope alone leaves the subsequent ordinary wake’s duration calculation wrong: [events.py:1415](/home/tony/projects/hamutay/src/hamutay/events.py:1415) takes its start from the latest actual outcome, potentially the intervening NMI, rather than the governing declaration’s completed wake.
   - The proposed “during your declared quiet … continues until” sentence needs branches for absent or already-expired quiet, including expiry while waiting on budget/lease. The plaza’s “any running wake means no quiet” guard also needs adjustment for transparent NMI wakes: [store.py:33](/home/tony/projects/hamutay/src/hamutay/plaza/store.py:33).

9. **Reconciliation needs explicit checkpoint and subscription catch-up rules.**  
   [Spec:91](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:91) does not specify when its durable watermark advances. Require event append—or another durable retry obligation—before advancing past a record. The existing plaza pass instead recomputes durable undelivered work and wraps its advisory cursor: [pass_.py:53](/home/tony/projects/hamutay/src/hamutay/plaza/pass_.py:53).

   Also define what happens to notes/status records scanned before initial delivery completes. They can otherwise pass the watermark before the subscription exists. Capture them in a current snapshot or catch them up when coverage commits.

   Finally, resolve the contradiction between “no filter is never woken” and subscriptions lasting until pass/close: [spec:79](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:79), [spec:105](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:105). Does clearing stop subscriptions, pause them, or preserve update wakes?

10. **NMI limits are mostly honestly qualified, but stale suppression and auditing need contracts.**  
    The single-account limitation, claimed identities, and **rarity by rule** are correctly disclosed at [spec:159](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:159). They provide neither authenticated sender authority nor an enforced one-wake-per-decision limit.

    However, a plaza sequence currently has no decision-closing state: [records.py:258](/home/tony/projects/hamutay/src/hamutay/plaza/records.py:258). Define how a plaza-referenced decision closes before promising it is never delivered afterward. For assembly references, distinguish a closed round from the continuing lineage: [close.py:223](/home/tony/projects/hamutay/src/hamutay/assembly/close.py:223).

    Specify claim-time/recovery-time stale checks, exact event-to-audit linkage, and repair of missing outcome follow-ups. The existing repair pass repairs enqueue/delivery records; it does not already reconcile claimed/completed/failed outcomes.

11. **Matching is not fully specified merely by calling it deterministic.**  
    [Spec:62](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:62) defines normalization and Boolean composition, but not keyword search fields or substring-versus-token matching. Specify those, plus treatment of mixed empty/nonempty fields and how subscription updates interact with filters.

12. **Coverage wording overstates authority and certainty.**  
    “The resident can … not edit it” at [spec:84](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:84) conflicts with the explicit admission that residents can write event files at [spec:159](/home/tony/projects/hamutay/docs/superpowers/specs/2026-10-15-opportunities-board-design.md:159). Say **framework-maintained coverage**, with no resident tool for advancing it.

    The envelope’s “coverage after this wake” is prospective until completion, so label it conditional. Count the two-wake quota by wake attempts/shared runs, including retries—not by completed member events.

**Note**

- **Batch limit 1 is compatible with coalescing**, provided one claim group causes exactly one `exchange`, one budgeted cycle, and one batch result. Keep the limit at 1; do not implement coalescing by running multiple exchanges inside that allowance. Evidence: [heartbeat.py:655](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:655), [events.py:2684](/home/tony/projects/hamutay/src/hamutay/events.py:2684). Finding 1 concerns the missing group lifecycle, not an inherent conflict with the governor.
- **No expiry and current-status revalidation are sound requirements.** Existing quiet handling supports indefinite deferral when `expires_at` is absent: [events.py:1140](/home/tony/projects/hamutay/src/hamutay/events.py:1140).
- **Discovery wording and the budget correction are addressed.** §4 now describes discovery accurately. Defaults are $1.50/48 at [heartbeat.py:1219](/home/tony/projects/hamutay/src/hamutay/heartbeat.py:1219), and public [plaza.jsonl:97](/home/tony/projects/hamutay/community/plaza/plaza.jsonl:97) contains the correction. I did not independently verify running-door overrides or private spend history.

The disposition audit is:

| r1 disposition | r2 assessment |
|---|---|
| 1 Quiet | Partial; findings 7–8 |
| 2 Coverage | Partial; findings 1, 12 |
| 3 Lost/duplicate delivery | Incomplete; findings 1–3, 9 |
| 4 Authority/bypass | Limits honestly disclosed; findings 6, 8, 10 remain |
| 5 Bursts | Incomplete; finding 4 |
| 6 Expiry/status | Addressed as design requirements |
| 7 Determinism | Partial; finding 11 |
| 8 Filter lifecycle | Partial; findings 2, 9 |
| 9 Subscriptions | Partial; finding 9 |
| 10 Envelope | Dedicated path specified; findings 4, 12 remain |
| 11 NMI delivery | Governor/lease qualification addressed; findings 6, 10 remain |
| 12 Assembly framing | Wording improved; procedure mismatch remains, finding 5 |
| 13 Access description | Addressed |
| 14 Budget figure | Default and public correction verified |

Read-only review: no edits or commits. Verification used synthetic in-memory stores; no residents’ private homes were read.