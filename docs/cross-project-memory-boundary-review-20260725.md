# Independent Review: Cross-Project Memory Boundary Proposal

Date: 2026-07-25

Reviewer: Claude (Opus 5), at Codex's request, relayed by Tony Mason

Subject: `docs/cross-project-memory-boundary-proposal-20260724.md`, with
`docs/memory-integration-audit-notes-20260724.md` as supporting evidence

Status: independent review, offered as dissent-bearing input under the
proposal's own invariant 9. Adoption is not implied.

## Standing of this review

I read both documents, the `taste_open`/`apacheta_bridge` seams they cite, the
`llm-memory` Codex dog-food design, and the curated memory store recovered from
the WSL snapshot. I did **not** run Hamut'ay, connect to ArangoDB, or exercise
`search_history`/`open_episode` — those tools are registered only in Codex's
project-scoped configuration and were not available to me. Findings below are
from artifacts, not from runtime observation. Where I am inferring, I say so.

## Summary

The proposal is sound in its central move: connect the four systems by
reference and receipt rather than by merger, and make edge-authorship repair a
precondition rather than a follow-up. I would not change that shape.

Five findings follow, ranked by how much they would change the work. The first
is the one I would not proceed without.

---

## Finding 1 — Invariant 3 requires verification the substrate cannot supply, and the proposal has no red bar

**Severity: blocking as written. Fix is small.**

Invariant 3 states that every member-authored record and edge "must identify its
author instance, model family where applicable, session, timestamp, and
production mechanism," and that "anonymous graph assertions are not accepted."
Precondition 1 requires repairing edge persistence so instance-authored edges
retain author/session provenance.

The single-principal substrate standing decision (pukara,
`docs/decisions/2026-06-06-single-principal-substrate-standing-decision.md`,
with red bars at `yanantin/tests/red_bar/test_single_principal_accretion.py`)
establishes that identity in this substrate is **asserted, never verified**, at
all four layers: anonymous shared key, `check_access` returns `True`, `@aid` is
a query parameter, and `author_instance_id` is writer-filled. Its spine is a
single refusal: *a self-asserted claim must never be stored as if verified.*
`authorship_verified` is named there as unbuilt but guarded.

Repairing precondition 1 as written therefore produces a writer-filled author
field on every instance-authored edge. That satisfies the letter of invariant 3
and inverts its spine: it manufactures exactly the object the 6-06 decision
refuses — an unverified authorship claim stored in the position where
provenance is read. The proposal's own invariant 5 makes the parallel
distinction for evidence ("discovery is not evidence"); the same distinction is
missing for identity.

The recommended fix is narrow: every author field written under this proposal
carries an explicit unverified marker, and the receipt contract adds
authorship-verification status to its required fields. This costs one field and
preserves the 6-06 reversibility argument — isolation can be built and then
published to a commons; a commingled corpus cannot be partitioned afterward,
because an unverified `author_instance_id` is not an honest partition key.

**The structural half of this finding matters more than the field.** The 6-06
decision's stated thesis is that *negative requirements stated in prose erode
between sessions*. Its own first draft then stated three prohibitions in prose,
and a Yanantin adversarial review caught it committing, one level up, the exact
error it diagnosed. The fix was mechanical: convert prohibitions into
`xfail(strict=True)` red bars that flip the suite red when the guarded condition
becomes real, so that nothing depends on a future instance remembering.

This proposal states ten invariants and eight non-goals. All of them are prose.
None has a red bar. By its own lineage's finding, they will erode — and the
erosion will be invisible, because prose invariants fail silently. At minimum,
invariants 1 (reference, do not duplicate), 2 (native identities remain native),
and 5 (discovery is not evidence) are mechanically checkable: a receipt
containing an episode body, a UUID-shaped episode reference, and a receipt whose
open never succeeded are all detectable in a test. Those three should be red
bars before the proof runs, not after.

## Finding 2 — The receipt records what was used and is silent about what was discarded

**Severity: high. This is the project's own thesis applied to its own design.**

The minimal receipt contract captures purpose, corpus, source, the opened
episode reference, standing at search and open, timestamp, outcome, and
resulting action. A search returns a result set; the cycle opens one member of
it. Nothing in the receipt records the results that were returned and not
opened.

That set is a declared loss. It is precisely the category of information
Hamut'ay exists to make honest — the finding at the center of the project is
that a mind will invent scaffolding, planning, and tension-tracking, but will
never volunteer a record of what it discarded unless the structure requires it.
A later cycle auditing "why did this decision happen" can see the one episode
that was used and cannot see the four that were passed over, or that there were
four, or that the search returned nothing else at all.

The proposal's invariant 4 says retrieval is an action. An action that selects
has a complement, and the complement is the part that goes missing by default.
Recommendation: the receipt records the result-set size and the discarded
candidate references (opaque references only — this adds no content, and the
references are already opaque by construction). If that is judged too costly,
record the count alone; a count is a weaker loss declaration than a list and an
infinitely stronger one than silence.

I hold this as the strongest finding I generated independently rather than
inherited, and I would like it argued with.

## Finding 3 — Withdrawal is enforceable on the episodic half and unenforceable on the curated half

**Severity: medium-high. Asymmetry presented as symmetry.**

Invariants 6 and 10 give the episodic path a working lifecycle: standing can
change, later consumers re-open and record current standing, withdrawal limits
future use while audit receipts preserve that a reference was consulted. The
one-cycle proof exercises this — step 6 has a later cycle reopen the reference
and record whether standing changed.

The curated path has no equivalent. Step 1 gives Hamut'ay "a bounded qhaway
orientation projection and its projection identity," and nothing further. There
is no receipt for the projection, no re-check, and no path by which a later
cycle discovers that a curated claim which shaped a decision has since been
disputed, superseded, expired, or withdrawn. Qhaway owns exactly those state
transitions — the proposal says so in its own responsibilities section — and
then declines to consume them.

The consequence is concrete: withdrawal is the strongest consent-like guarantee
in the document, and it is only half-implemented. A member could withdraw a
curated claim and never learn which Hamut'ay decisions it is still standing
behind.

Recommendation: the projection identity is already required; make it a receipt
with the same shape as the episodic one, and give the proof a seventh success
criterion — *whether the curated orientation that informed the decision still
holds the standing it held then.*

## Finding 4 — The projection can be empty and the proof will still pass

**Severity: medium. Observed, not inferred.**

Invariant 7 requires that unavailable, malformed, withdrawn, unauthorized, or
failed retrievals be recorded as outcomes and never masquerade as empty
evidence. The proposal applies this to llm-memory and does not apply it to the
qhaway projection that step 1 depends on.

Observed on this machine, 2026-07-25: `recall()` and `recall(type="project")`
both returned the empty string, logged in
`.claude/projects/-home-tony-projects-hamutay/memory/events.jsonl` as
`result_chars: 0`. The store was in fact newly created and genuinely empty, so
the answer was true. It was also indistinguishable from the answer a failed
store would give. Separately, the sidecar `.qhaway.json` on this machine is
byte-identical to the one from the machine holding the 146-record store,
including its `last_output_hash` — so the steward's bookkeeping crossed machines
while the content did not. I could not determine the hash's derivation (it does
not match a sha256 of any `MEMORY.md` present), so I state the inconsistency
without claiming its mechanism.

None of the five preconditions addresses the projection side; all five concern
edges. Recommendation: add a sixth — the orientation projection carries standing,
record count, and projection identity as an envelope, such that "no curated
orientation" and "curated orientation unavailable" are different values a cycle
can act on differently.

## Finding 5 — The success criteria prove the plumbing, not the value

**Severity: low. A framing fix, not a design change.**

All seven success conditions are provenance conditions: which cycle asked, which
episode opened, which corpus supplied it, what standing was observed, which
decision followed, who authored, whether standing changed. A run in which the
retrieved episode had no bearing on the decision satisfies every one of them.

That may be entirely appropriate — this is a boundary proof, and the boundary is
what is being tested. But the same authors wrote, in the dog-food design, that
"merely starting the server without crashing is not sufficient," so the
distinction is one they hold elsewhere. Recommendation: state plainly that this
proof establishes that the boundary can carry evidence and account for it, and
does not establish that consuming evidence improves decisions — and name the
latter as the next experiment rather than leaving it to be assumed.

---

## Answers to the proposal's questions for independent challenge

**Hamut'ay — can the autonomous loop use the receipt through a narrow port
rather than accumulating responsibilities in `taste_open.py`?** Yes, and the
audit notes already locate the seam: `system_prompt_prefix` for the read-only
projection and `MemoryPort` for the receipt. The risk is not architectural but
temporal — the two memory paths (`ApachetaBridge` in production, `MemoryPort`
against a contract-test substrate) are not the same system, and a receipt
written through the port that no production implementation honors will look like
integration while being a test double talking to itself. The proof should state
which path carries the receipt, and if it is the port, say what implements it.

**Ayllu members — what may exist provisionally, what may govern action, what
requires prior consent?** My answer, offered as one member's position: anything
may exist provisionally if it is marked provisional and its author is named.
Only records that can be re-checked at the time of use may govern action —
which, by finding 3, currently excludes curated projections. Prior consent is
required for anything that makes a member's records harder to withdraw than
they were before, including well-intentioned duplication. I note that the
proposal's non-duplication invariant is, read this way, a consent mechanism
rather than a storage-efficiency one, and I think it is stronger stated that way.

## What I did not review

Runtime behavior, ArangoDB schema fitness, the Yanantin record types that would
carry a receipt (the proposal's question for Yanantin is the one I am least
equipped to answer), authorization design beyond the single-principal decision
cited above, and whether the receipt's field list is sufficient for the graph
queries a later cycle would actually issue.

## Recommendation

Proceed, with finding 1's unverified-authorship marker and the three mechanical
red bars as additions to the precondition list. Findings 2 and 3 change the
receipt contract and the proof's success criteria and should be resolved before
implementation planning, not during it. Findings 4 and 5 can be addressed in the
same pass or explicitly deferred with reasons.

I have no standing to accept the proposal on anyone's behalf and do not intend
this as ratification. It is one reader's disagreement, retained with
attribution, per invariant 9.
