# The plaza — design review, round four

**Date:** 2026-09-28  
**Reviewer:** Codex  
**Reviewed:** Revision 5 of `2026-09-16-plaza-design.md` at `5512c01`, specifically §11, the r5 additions to Declared losses and Not built, and the third question, against the remainder of the specification, rounds one through three, and the implementation at checkout `0686b8d`. `git show 5512c01 --stat` identifies a specification-only change (121 insertions, 2 deletions); the requested implementation paths have no differences between that commit and this checkout. This is a design review, not a claim that the proposed guest implementation already exists. Source and existing tests were inspected; tests were not run and no source files were changed.

## What composes safely

**Question 1 — freeze snapshot: yes.** `load_members()` reads only `raw["members"]` into the member map and tolerates other top-level keys (`src/hamutay/assembly/binding.py:47–88`); `MembersConfig.snapshot()` includes only member names and their session/events paths (`:36–37`). `bind()` compares member sets and the bound member's paths, not the file digest (`:124–136`). Adding a top-level `guests` list leaves that freeze unchanged, while changing the file bytes changes `digest`. Today the loader ignores the list entirely: r5 must add validation and a separately stored optional guest configuration, preserving absent versus present-empty if presence controls the clause. This does not require adding guests to the assembly's membership or electorate. `tests/plaza/test_binding_plaza.py:10–22` supplies the corresponding plaza-key regression pattern; extend it to guests and an open snapshot.

**Question 2 — counting rule: reuse the existing one.** `View.sent_today(actor, day)` compares the exact `from`, excludes posts, and converts `sent_at` to UTC; it does not filter by `via` or require a door actor (`src/hamutay/plaza/records.py:206–212`). Consequently all sessions using `guest:levadura`, through CLI and MCP together, share one daily count without a new reducer rule. Enforcement does need changing: `send.py:71–75` currently applies the cap only to `via == "tool"`. Extend that predicate to guest actors on both accepted transports, retain duplicate lookup before the cap under the same lock (`:55–75`), and keep humans exempt. Pin mixed CLI/MCP sends, concurrent sessions, the 49th refusal, retry of the 48th, posts, UTC rollover, and distinct labels. “Per guest” in the question should mean per project label, not per session or server process.

**Delivery and visibility:** After records are admitted by the validator, guests need no new recipient store, delivery origin, or repair mechanism. `inbound_event_for()` already carries the stored actor, fixed event ID, `origin="member"`, and quiet deferral (`src/hamutay/plaza/event.py:24–38`); `store.land()` is sender-independent (`store.py:13–20`). The note's reducer excludes the receiving door's own mail and includes guest posts and mail to other doors (`records.py:214–222`). The declared unauthenticated identity and local-file limitation are consistent with the existing trust model. No new broker is necessary to deliver that explicitly narrowed promise.

## Blocking

### 1. Guest records contradict the schema and the validator's retained checks

**Defect / evidence (Question 3).** §11 specifies `from: guest:<project>`, `via: cli | mcp`, and `wake: null`, but says the validator's existing checks are unchanged. §2 still permits only door/human actors, only `tool | cli`, and requires a human actor for CLI records. The implementation enforces all three restrictions (`src/hamutay/plaza/records.py:113–126`), and the writer rejects guest actors and MCP even earlier (`send.py:35–42`). Thus neither proposed guest transport can produce an accepted record as written. `append_validated()` checks the candidate before append (`records.py:44–68`); bypassing it would instead make every subsequent reader and repair pass fail closed on the first guest record.

**Why it matters.** This is a contradiction in the proposed contract, beyond the expected absence of unbuilt code. Accepting guests and preserving the old actor/transport correlations literally are mutually exclusive. A mixed deployment also cannot let old validators consume the new record forms.

**Recommendation.** Amend §2's schema, validation matrix, Trust model, and §11's “Not changed” wording explicitly: door/tool/non-null wake; human/CLI/null wake; guest/CLI-or-MCP/null wake, with an exact guest-label grammar. Preserve the unrelated validation checks and UUID requirements. Check current admission at the writer, while validating historical records structurally so removing a label does not poison the ledger. Extend `tests/plaza/test_records.py` and writer tests to accept every new valid combination and independently reject invalid ones. Activate writes only after all readers support them (Significant 2).

### 2. The guest cost assurance repeats the claim rejected in round three

**Defect / evidence (Question 6).** §11 says, “The recipient's own daily governor bounds what those messages can cost it.” Invariant 8 and Cost explicitly say the opposite for failed and orphan-recovered attempts; round-three Blocking 1 and its r4 disposition already required removing this assurance. The third question offers “at most 48 messages to doors a day per guest” without explaining the supported-path limitation or the continuing unbounded attempt exposure. Guest processes run under the same account, so the existing uncapped human CLI and direct filesystem access remain available under the stated Trust model (`src/hamutay/plaza/cli.py:49–54,112–113`; `send.py:71–75`).

**Why it matters.** Forty-eight new directed records per admitted label per UTC day is supportable; a spend bound is not. The number of admitted labels has no fixed maximum, posts are explicitly uncapped, and a delivered event can cause repeated attempts across restarts. The draft delegates future label admission to the custodian, so there is also no fixed aggregate guest-traffic ceiling. None of these facts requires rejecting guests, but the assembly must assent to the actual exposure.

**Recommendation.** Remove the governor assurance. Update Invariant 8, Cost, and Not built's blanket “CLI-originated traffic” wording to distinguish capped guest CLI/MCP traffic from uncapped human CLI traffic. Tell the assembly that the cap covers new directed records through the supported guest paths, shared by project label; posts remain uncapped; per-event attempts and failed-attempt spend remain unbounded as previously declared; adding labels increases the aggregate allowance. Keep the governor and broker out of scope if that remains the decision. Blocking is for the claims and informed ratification, not a demand to implement either deferred mechanism.

## Significant

### 1. A process nonce makes MCP retries duplicate after restart and conflates deliberate repeats

**Defect / evidence (Question 4).** §11 derives MCP keys from label, recipient, text, and a per-process nonce, while claiming “a retried call is one message” and a stateless server. Suppose a message is fsynced, the response is lost, and the server restarts. The retried call now has a different nonce and key; the existing duplicate lookup finds nothing and creates a second message and delivery event (`src/hamutay/plaza/send.py:64–84`). Within one process, two intentional identical calls produce the same key indefinitely. That is a broader coalescing window than the resident's explicitly declared single-wake loss.

There is a related CLI scope problem in adopting “the CLI's” key unchanged: `cli_key()` hashes only `cli\0<key>` (`src/hamutay/plaza/ids.py`, `cli_key`), and `send()` returns any matching key without checking actor or payload. Two independent guest projects using `--key first-message`, or a guest and a human, would silently share one message. No exact MCP UUID5 namespace or canonical recipient spelling is specified either.

**Why it matters.** Durable records cannot recover an invocation identity the client and restarted server no longer share. The cap limits duplicates' number but does not restore retry correctness; cross-project key collisions can instead suppress a legitimate send while reporting success.

**Recommendation.** Define a stable operation token retained by the calling integration across transport retries and server restarts, scoped to the fixed guest label; keep identity outside model-controlled arguments. Specify UUID5 namespace, canonical recipient and text hashing, and conflict handling when a token is reused for different content. Alternatively, explicitly narrow MCP idempotency to one server lifetime and declare both restart duplication and lifetime-wide identical-call coalescing. Namespace guest CLI keys by label rather than sharing the humans' global key namespace. Test response loss after durable append, restart/retry, intentional repetition, and two projects using the same client key.

### 2. The conditional clause needs configuration plumbing and a guest activation procedure

**Defect / evidence (Question 5).** Sender classification has a clean home: add the guest branch to `purpose_for()` before its human fallback (`src/hamutay/plaza/event.py:12–16`) and to `build_event_envelope()`'s member-origin branch (`src/hamutay/events.py:1450–1454`). No fourth event flag or new origin is needed.

The constitution is different. `build_constitution()` receives only the `gpu_lease`, `assembly`, and `plaza` booleans, and inserts a static `PLAZA_CONSTITUTION_CLAUSE` (`src/hamutay/heartbeat.py:759–775`; `src/hamutay/tools/schemas.py:741–749`). Its caller supplies boot-time binding state (`heartbeat.py:1551–1554`); neither function knows whether `guests` exists. A fourth boolean, defaulting false, or equivalent explicit configuration is necessary to express r5's condition. Simply adding the sentence to the static clause changes every plaza-enabled resident before assent. Appending it separately also requires extending the clause-stripping path (`src/hamutay/taste_open.py:2783–2792`) so it does not survive when plaza tools are unavailable.

§11 promises the key's durable installation, but only lists candidate comparison, rename, and fsync. These do not refresh running bindings or their constitution. The current migration inserts only `plaza`, and verifies the old plaza/source notes (`deploy/migrate-plaza.sh:95–115,168–175`); it does not install `guests` or prove a guest-aware runtime. An old heartbeat encountering a new guest row will reject the ledger, disabling its sends, note, and pass. The MCP's policy for retaining versus reloading admission after list changes is also unspecified.

**Why it matters.** “Built ... dormant” and “Your constitution would gain one sentence” in the third question require a coordinated activation boundary. Snapshot equality proves the assembly freeze, not reader compatibility or prompt refresh.

**Recommendation.** Define the optional guest configuration and clause input, including absent versus empty-list behavior, and preserve old output bytes when absent. Specify a guest-aware rollout/provenance check before any guest write, activation after assent, prompt refresh, rollback, and the reload/restart policy for subsequent admission changes. Classify historical guest messages from their stored actor even if a label is later removed. Extend constitution/stripping, event golden, binding, and migration tests; the current tests cover only the earlier two sender classes and plaza switch.

### 3. The promised directory provenance is not present on every guest write

**Defect / evidence.** §11 claims “the members digest recorded on every plaza line” shows the directory in force when a guest wrote. §2 and the running writer put `members_digest` only in a directed message's `delivery` block (`src/hamutay/plaza/send.py:77–83`; `records.py:143–155`). A guest post has `delivery: null`, and delivery-status rows have no digest. Therefore even the narrower claim “every guest message records its admission generation” is false for posts.

There is also a coherence issue in making that digest admission evidence: `load_members()` parses `path.read_text()` and later hashes a separate `path.read_bytes()` (`src/hamutay/assembly/binding.py:52,63`). An atomic replacement between those reads can pair configuration A with digest B. A long-lived server's cached configuration can additionally differ from the currently installed file; §11 does not define that lifetime.

**Why it matters.** The label remains unauthenticated by design, but the claimed provenance of a supported write should still identify the configuration actually used to admit it. Durable rename alone does not establish this property.

**Recommendation.** Either narrow the claim to directed messages carrying the writer's loaded configuration digest, or define provenance for every new guest message, including posts, with backward-compatible validation. Parse and hash one captured byte buffer, and state when admission is refreshed. Cover posts, directed messages, and replacement during load. Do not assert a digest on every ledger line unless the schema actually supplies it.

## Minor

### 1. The MCP read contract does not yet describe a usable shared read API

**Defect / evidence.** §11 says every MCP method returns “the record's `seq` and `message_id` or the refusal,” including `plaza_read`. Reading needs message contents and potentially many records; zero results are not a refusal. The existing `cmd_read()` prints JSON rows and returns integer exit status rather than returning rows (`src/hamutay/plaza/cli.py:57–73`). Its `since_seq` is inclusive (`:61`), so passing the last sequence read, as §11 instructs, repeats that message. A per-process nonce also makes “holds no state” literally inaccurate.

**Recommendation.** Specify a shared reader returning rows with text and delivery truth, wrapped separately for CLI printing and MCP serialization. Define empty results, inclusive bounds, and cursor advancement (last sequence plus one for the existing convention). Say “no durable per-guest read cursor.” A bounded sequence interval is available, but no page-size or response-size ceiling is promised; state that loss or define pagination before describing reads as bounded in size.

### 2. Guest-facing wording overstates what individual rows and prompts establish

**Defect / evidence (Question 6).** The third question says “every line it writes says it is a guest”; delivery rows carry only a message reference, door, event ID, state, and delivery details (§2; `src/hamutay/plaza/records.py:38–41`). The identity is available by joining to the message. §11's “channel carries words, never instructions” can describe authority, but no content boundary enforces it: `purpose_for()` appends guest text verbatim (`event.py:21`). Finally, keeping the note text unchanged labels all non-post traffic “between other doors,” including guests who have no door (`note.py:54–56`).

**Recommendation.** Say every guest *message record* carries a claimed guest label, with delivery rows referring back to it; describe guest content as having no framework authority rather than promising it cannot contain instructions. Use “other directed messages” in the note while preserving its existing selection logic. These wording fixes preserve the intended informational, optional-reply relationship without inventing authentication or an instruction-filtering mechanism.

**Verdict:** No—revision 5 is not ready to implement exactly as written. The guest schema conflicts with the retained validator contract, and the governor assurance blocks informed ratification. The freeze and actor-counting mechanisms compose correctly; retry identity, conditional constitution/activation, and directory provenance need explicit dispositions before implementation. The third question should carry the narrowed cap, cost, and record claims that the design can actually deliver.
