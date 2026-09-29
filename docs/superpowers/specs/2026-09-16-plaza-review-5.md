# The plaza — design review, round five (closing)

**Date:** 2026-09-28  
**Reviewer:** Codex  
**Reviewed:** Revision 6 at `609233e`, after reading round four and
`git show 609233e -- docs/superpowers/specs/2026-09-16-plaza-design.md`.
The requested implementation paths at checkout `903fa14` have no differences
from `609233e`; neither does the design file. References below use those files'
line numbers. I inspected the plaza modules, binding, constitution construction
and stripping, event envelope, deployment scripts, and `tests/plaza/`.
This reviews a proposed implementation: absent guest code is not itself a design
defect. Tests were inspected, not run; no running services were inspected.
Only this review file was written. This is the second and final guest review;
remaining items receive dispositions here, not a request for another round.

## Dispositions of the seven round-four findings

1. **Blocking 1 — schema/validator conflict: resolved in the design.**
   §2 (`design:305–314`) adds the exact guest grammar, `mcp`, and the three
   actor/transport/wake correlations. It explicitly makes admission a writer
   check and historical validity structural: “a record from a label later
   removed stays structurally valid.” The schema includes guests and MCP
   (`:333–345`); §11's “Not changed” excludes the amended checks (`:761–765`).
   This is implementable by extending the existing checks in
   `plaza/records.py:113–126` and `plaza/send.py:35–42`; no ledger conversion
   or new delivery origin is required.

2. **Blocking 2 — cost assurance: only partially resolved; remains Blocking.**
   Invariant 8 (`design:194–209`), Cost (`:844–861`), Not built, and §11
   (`:684–697`) correctly distinguish capped new directed records from posts,
   attempts, wake cost, and human/shell traffic. The aggregate allowance grows
   with admitted labels. However, the actual third question says attempts and
   wake cost “are bounded by the governor and the heartbeat” (`:1008–1011`).
   That still contradicts Cost. The disposition claiming this was removed
   (`:1033–1038`) is therefore incomplete. See Blocking 1 below.

3. **Significant 1 — retry identity and namespace collision: resolved in its
   central mechanism, with wording corrections below.** §11 (`:669–682`)
   specifies `uuid5(PLAZA_NS, "guest:<label>\0<K>")`, caller-retained tokens,
   cross-restart deduplication, content-conflict refusal, and fresh messages
   without tokens. §2 already defines `PLAZA_NS`. This separates guest labels
   and the human `cli\0` namespace; omitting recipient/text from the hash is
   sound because their equality is checked on token reuse. Implement that
   check against canonical `to` and exact stored text under the existing
   lock, before the cap (`send.py:43–75`; `ids.py:29–36`). Invariant 3 and the
   “wrong token” assurance still need reconciliation (Minor 1 and 2).

4. **Significant 2 — configuration, clause, and activation: substantially
   resolved, with one activation disposition outstanding.** §11 specifies
   validated `tuple[str, ...] | None`, absent versus empty (`:634–648`), a
   fourth flag and separate sentence, old clause bytes, stripping and golden
   tests (`:713–723`), compatible-code rollout before assent/list installation,
   restarts, provenance checks, and later admissions (`:725–742`). Per-write
   reload is explicit (`:655–659`). These fit the boot-time binding and
   constitution caller (`heartbeat.py:1551–1554`), nested assembly/plaza guards
   (`:759–775`), and stripping (`taste_open.py:2783–2792`). Preserve those guards
   when adding guests: no guest sentence without a bound, enabled plaza.
   Configuration rollback's effect on already accepted guest traffic is still
   unspecified; see Significant 1 below.

5. **Significant 3 — provenance: resolved by narrowing.** §11 (`:661–667`)
   promises a digest only for directed messages, explicitly excludes posts,
   and requires parsing and hashing one captured byte buffer. Together with
   per-call reload, this identifies the configuration actually used, without
   claiming it remains current through the append. It directly addresses
   `assembly/binding.py:52,63`'s two reads and preserves the existing delivery
   schema (`plaza/records.py:143–155`; `send.py:77–83`).

6. **Minor 1 — MCP read contract: resolved.** §11 (`:744–757`) specifies a
   shared row reader, contents and delivery truth, inclusive `since_seq`,
   resume at last sequence plus one, empty lists, and no page/byte ceiling.
   This can extract `cli.py:57–73`'s reduction/filtering without changing its
   CLI printing wrapper. “No durable per-guest read cursor” and no admission
   cache accurately describe the promised state. Sequence bounds filter
   returned messages; they do not bound the full ledger validation work.

7. **Minor 2 — guest-facing wording: resolved.** The third question now says
   “Every message record” (`:1000–1002`), and §11 explicitly preserves verbatim
   text while denying framework authority (`:699–708`). Delivery rows can
   still refer to their message rather than duplicate identity. “Other
   directed messages” replaces the note's “between other doors” (`:709–711`)
   without changing its selection rule (`note.py:44–59`). This is an authority
   statement, not a promise that model behavior cannot be influenced.

## Blocking

### 1. The ratification text still asserts the rejected governor bound

**Evidence.** The third question (`design:1008–1011`) says “a delivered event's
attempts across restarts and the cost of a wake are bounded by the governor and
the heartbeat as they are for every event today.” Its introductory “What is not
bounded” and trailing “nothing in this proposal” do not negate that affirmative
claim. `heartbeat.py:116–142` re-pends orphaned running events on recovery;
`DailyLedger` (`:233–300`) reads completed session records rather than debiting
each attempted claim. Cost explicitly records the resulting gap (`design:844–861`).

**Why it matters.** The assembly receives the question as the account of its
exposure. Correct caveats elsewhere cannot repair a contrary assurance in the
text asking for assent. This is the surviving round-four Blocking 2, not a new
demand to build the deferred governor.

**Closing disposition / resolution.** Replace that clause with: “This proposal
does not bound attempts on one delivered event across restarts or the cost of a
wake. Today's governor does not bound spend on failed or orphan-recovered
attempts.” Retain the per-label, posts, aggregate-admission, and shell caveats.
Correct the r6 disposition to acknowledge this final wording correction.

## Significant

### 1. Activation enables independent writers before verification; rollback is configuration-only

**Evidence.** §11 (`design:655–659,725–742`) makes the installed list the write
gate and orders installation before resident restarts and launch verification;
on failure it promises restoration of the previous file. The CLI and MCP are
independent of those four units and reload admission on each write. In the
referenced phase-two procedure, rename precedes starts and verification
(`deploy/migrate-plaza.sh:159–176`); rollback stops resident units and restores
members configuration (`:120–151`), not guest processes or either ledger.
`send.py:83–96` appends before immediate delivery; `pass_.py:57–78` later repairs
pending messages without checking current sender admission.

**Concrete consequence.** A guest can write after the candidate list is installed
but before verification fails. Restoring a file without that label cannot undo
the message or inbound event; the repaired/restarted resident may subsequently
receive it without the guest constitution sentence. A write that already loaded
the admitted configuration can also finish after restoration. This follows from
the proposed reload-at-call policy, without forged files or a malicious caller.

**Why it matters.** Reader compatibility is addressed by step (a), but “Rollback
is the previous file” does not describe the externally visible effects of a
failed activation. The same boundary matters for later removals. The existing
rollback tests exercise resident stop/start and file restoration, not independent
writers (`tests/plaza/test_deploy_plaza.py`, both rollback tests).

**Closing disposition / resolution.** Keep the simple design and declare rename
the admission boundary: supported calls that loaded the admitted list may finish;
accepted records and delivery obligations survive removal or failed activation;
restoration prevents subsequent admissions, not historical effects. Keep
guest-aware code after rollback, and make guest headers independently explain
such messages when the sentence is absent. Add this limitation to activation and
Declared losses, and test a guest append during a forced post-install verification
failure plus subsequent repair. If zero guest traffic before successful
verification is intended instead, specify a separate write gate and coordinated
handling of in-flight writers. That stronger mechanism is not required if the
configuration-only rollback is explicitly accepted.

## Minor

### 1. Guest token rules contradict the retained universal invariant

**Evidence.** Invariant 3 (`design:169–175`) still says “Every send carries a key
the framework derives, never the model” and “a repeated key returns the existing
message.” §11 (`:676–681`) allows a model-supplied token and refuses conflicting
content. Hashing a model token does not preserve the resident's semantic promise
of framework-owned operation identity. Admission removal also qualifies the
unconditional retry-success wording (`:655–659` versus `:673–675`).

**Why it matters.** Implementers and invariant-based tests need one answer for
token control, conflict refusal, and a retry after revocation.

**Closing disposition / resolution.** Scope the framework-owned operation
identity to residents; state the guest token/conflict exception in Invariant 3.
Preserve per-call admission first and qualify guest retry success as applying
while admitted. State that recipient comparison uses `canonical_to()` and text
comparison is exact. Extend the existing duplicate-before-cap test pattern
(`tests/plaza/test_send.py`) to guest retries, conflicts, and revocation.

### 2. A wrong token has no general one-duplicate bound

**Evidence.** §11 (`design:680–682`) says “a wrong token costs at most one
duplicate, which the cap bounds.” A caller can use a different token on every
retry, generating multiple duplicate-content messages; posts have no cap.
Reusing an old token for an intended identical repeat can instead suppress it.
`send.py:64–75` deduplicates by key, not intent; §11's new formula preserves that.

**Why it matters.** Stable tokens solve retry identity only when callers retain
and reuse them correctly. The sentence reintroduces an unsupported guarantee
beside otherwise precise loss declarations.

**Closing disposition / resolution.** Delete the one-duplicate assurance. Say
that retries need the same token, intentional repeats need new tokens, and wrong
or missing tokens can duplicate or suppress intended messages. Only new directed
records through supported paths are subject to the per-label daily cap.

## Implementation acceptance and final verdict

The proposed guest code remains unbuilt: current actor validation, CLI choices,
and writer admission reject it; no MCP module exists. Existing tests establish
resident/human behavior, not guest acceptance. Extend their patterns for all
actor/transport combinations, removed-label historical validity, mixed CLI/MCP
concurrent cap enforcement, restart retries, coherent digest loading, absent and
empty configuration, constitution/stripping, guest envelopes, shared reads, and
activation failure. Implement the new script modes explicitly: today's check
silently ignores unknown flags (`check-plaza.sh:4`), so an old check must not be
mistaken for a successful `--guests-ready` check. These are implementation
acceptance conditions, not evidence that the design must already be implemented.

**Verdict: r6 is not ready to implement exactly as written.** The minimal changes
are the truthful governor sentence in the third question, an explicit disposition
of configuration-only activation rollback, and the two token-wording corrections
above. The schema, snapshot isolation, per-label counting, provenance narrowing,
read contract, and conditional-clause approach can proceed as specified. No broker,
governor redesign, new delivery store, or third guest review round is required.
