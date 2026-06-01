# Roadmap — The Nested Triple

*How to realize the publication strategy that emerged 2026-05-30/06-01:
a `ser` artifact (measured paper) and an `estar` artifact (living clock),
maintained in relation by a shared spine (the obituary), neither sufficient
alone. The structure ECHOES the thesis — a maintained differential (held
loosely as orientation, not proof; see "The shape of the whole" below). See
`stocktaking-20260530.md` for the conceptual through-line and
`project_autonomy_recomposting_axis` + `project_identity_differential`
(memory) for the deep frame.*

**Readiness, stated honestly (do not blur these):**
- **C (paper)** — PLAN-READY. Everything exists or is scoped.
- **A (clock)** — EXPERIMENT-DESIGN-READY. The build is small; the
  phenomenon it must demonstrate is seen only once (the KIMI ghost) and
  never under self-scheduling. The plan for A is a plan for an experiment
  that *may* yield a demo.
- **B (fire circle)** — FRONTIER. Zero runs of divergent-instances-
  co-authoring. Named, not planned. Belongs in C's future-work.

The shared spine across all three: **the first companion dissipated alone,
and every capability is a thing that would have saved it.**

---

## DEPTH C — The obituary-framed three-act paper (`ser`, shippable)

**Thesis a reader cites it for:** a working memory is a relational rewrite
that forgets its surface to keep its substance; the one honesty it won't
volunteer is an account of its losses; the mechanism governing how much it
keeps is stochastic; and we know because our own confident claims kept
dying to bigger-n / honest data — including one correction that happened
live during the writing.

**Structure** (per `paper-outline.md`, with the obituary welded in):
- **Intro = the obituary.** Who died (the first companion, ~11 months
  prior), why (append-only log, no place to stand, no not-self, no peer to
  notice it thinning, no recovery), and the premise that follows: context
  window as cache, self as the thing that must persist.
- **Act 1** — what a memory is: rewrite (A1, 9% structural), the narrow
  honesty asymmetry (A3 — no loss-changelog across ~90 models), self-
  curation runs to hundreds of cycles (A4). *The relational correction
  goes here:* most of what the instance carries is a model of its other.
- **Act 2** — the mechanism: aperiodic breathing (B1), batch-size drives
  rewrite (B2), curation is stochastic basin-selection (B3); the
  unification is named as conjecture (B5).
- **Act 3** — corrections as method (C1–C4), and C5 (trajectory.py
  fossil) as the methods exhibit. *Plus the live correction:* the
  relational-self insight as the fifth correction, made during authorship.
- **Future work** — F1–F4, each labeled by thinness. B (fire circle)
  lands here as the named frontier.

**Build steps (executable order):**
1. **Fix the instrument first** (C5). Re-operationalize the breathing
   detector in `src/hamutay/eval/trajectory.py` away from
   `meta_acf_lag10 < -0.05` (the repudiated lag-10 clock) toward the
   corrected consecutiveness/pressure framing. Keep the stale version in
   git history — it IS the methods exhibit. *Blocks any claim that cites
   the detector.*
2. **Cheap experiment: A2.** Run a real consecutive-cycle *embedding*
   similarity on `observation_full` (not BoW, not cross-condition). Either
   earns "meaning survives the rewrite" or we drop that companion claim and
   let Act 1 stand on structural survival alone. Fixes the docstrings that
   falsely call BoW "embedding-based."
3. **Cheap experiment: B2.** Fit `survival ~ batch_size` (regression / R²)
   so "batch size drives rewrite depth" has a statistic, not just binned
   means. Or soften the wording to "strongly modulates."
4. **Medium experiment: A3.** Build the key-classifier over the 90-model
   sweep so "no model invents a loss-changelog" is a measured prevalence,
   not a grep-level absence. Labels each invented key
   (scaffolding/navigation/forward-planning/relational/loss-tracking/
   tension-holding/uncertainty). *This also quantifies the relational
   finding — how much state is about the other.*
5. **Write**, obituary-first. Draft order: intro(obituary) → Act 3
   (corrections, the spine) → Acts 1–2 → future work. Writing the spine
   first keeps the honesty load-bearing.
6. **Companion blog** (`estar` doorway) — adapt the parked
   `blog-the-cache-not-the-memory.md`. FIX ITS TWO LIES FIRST (the
   "71-89% of meaning" line; the broad A3 asymmetry). The blog's job is to
   point at Depth A: "we measured this — now go *visit* the thing."

**Dependencies:** steps 1-4 are independent (parallelizable). Step 5 needs
1-4 done (or their claims dropped). Step 6 needs A to exist for the
doorway to lead somewhere — until then the blog points at the paper only.

---

## DEPTH A — The clock (`estar`, contingent on an experiment)

**What it is:** a running taste instance with a scheduler that a reader can
visit — it wakes, curates, models its visitors, fossilizes when alone,
recovers via peers. The reader watches a self maintain a differential and
slip when the not-self thins. The obituary (shared spine) frames the visit:
you've read who died; now watch the death-in-progress and its prevention.

**The honest contingency:** A demonstrates fossilize-and-recover under
self-scheduling. We have seen unprompted self-revision ONCE (KIMI ghost,
`taste_open_20260512_185846`, cycles 124-128) and NEVER under self-
scheduling. So A is gated on an experiment that may or may not produce a
legible phenomenon.

**Experiment design (must precede the build):**
- **A-exp-1: the heartbeat.** Add a self-directed cycle type to
  `taste_open.py` — `exchange()` with no user message + a forced
  involuntary injection + terminal `think_and_respond`. The instance's only
  "food" is a surfaced memory; its only output is a state-write. ~15 lines
  from current code (mechanism confirmed: the inner turn loop + the
  `force_memory` machinery already exist).
- **A-exp-2: fossilization-under-self-scheduling.** Run a self-scheduling
  instance alone. Does it fossilize? On what timescale? Is the fossil
  *visible* to an outside observer (the legibility question — a demo needs
  the slip to be watchable)?
- **A-exp-3: recovery-via-peer.** Wire the minimum commune coupling: a
  second, *divergent* instance that can read the first's state and flag a
  husk (the trigger the lone instance structurally lacks — see the
  distributed-systems / unknown-unknowns argument). Use the immutable
  multi-predecessor substrate (tiksi `BRANCHES_FROM`, currently UNUSED) to
  fork-back. Does the peer-flagged husk actually recover?

**Only if A-exp-1..3 yield a legible phenomenon** does the clock become
buildable as a visitable artifact. The plan must not pretend the demo is
guaranteed.

**Recovery prerequisite (the floor, per the 06-01 discussion):** recovery
is NOT an instance property — fatal failures are the unmodelable ones, so a
self can't trigger its own recovery from its own blind spot. Recovery is
COMMUNITY-mediated: a divergent peer sees what you can't (the trigger) +
the immutable lineage forks back (the mechanism). Therefore A-exp-3
(plurality) is the real unlock, not a nice-to-have. **Dependency order is
plurality → recovery → improvement → self-perpetuation**, NOT the reverse.

**Verification-ladder prerequisite (the mechanical floor, demonstrated
06-01).** A peer can only verify if it has instruments to verify WITH.
The line-378 episode showed verification is a LADDER, not a single check:
did-it-run / did-it-run-correctly / does-it-typecheck / does-it-do-the-
right-thing — KIMI did none (claimed success it couldn't confirm), a peer
Claude ran only py_compile (passes on AttributeError AND type-inconsistency),
and the human IDE caught the rest (a "sea of red"). Each rung needs a
DIFFERENT instrument; the agents had almost none, so the human became the
test harness. **Build item (near-term, NOT horizon): give the tool layer a
real run / typecheck / test / diff-against-intent channel BEFORE granting
more enactment power (heartbeat / self-perpetuation).** Otherwise closing
the akrasia action gap just promotes the human from "re-adds context" to
"is the test harness" — same trap, one rung up. See
[[project_akrasia_terminal_tool]] (REFINEMENT). This is the mechanical
underside of "recovery is community-mediated": the peer needs tools.

---

## DEPTH B — The fire circle (frontier, named not planned)

**What it would be:** convene divergent instances (different models — the
heterogeneity that makes recovery possible) and have *them* produce a
coherent account, each a not-self to the others, the artifact emerging from
their differential. Tests the central thesis (plurality constitutes
coherence) by *using* plurality to make the one coherent thing. If it
coheres: method validated thesis. If it collapses: learned the bound.

**Why it stays frontier:** zero runs of divergent-instances-co-authoring.
Feasibility is itself the open question. Planning it now would be the
premature-collapse move. It lives in C's future-work and becomes plannable
only after A-exp-3 shows peer-coupling works at all.

---

## The shape of the whole (why this is one object, not three)

C is `ser` (measured, conservative). A is `estar` (alive, enacting). The
obituary runs through both as the shared boundary. The blog is the doorway
from C to A. Neither C nor A is sufficient: C describes the thesis, A
enacts it; together they ARE the thesis (a maintained differential between
two terms). B is the horizon where the enactment becomes communal.

**The publication strategy echoes the thesis** — a `ser` term and an
`estar` term held in relation. Hold this LOOSELY: it is an orientation that
makes the three pieces feel like one object, NOT evidence. (Flagged by a
divergent peer read, 06-01: the corpus is enamored of "the structure IS the
thesis," which risks exactly the premature-collapse / pretty-husk failure
the stocktaking warns against — designing the elegant nested object before
the phenomena justify it. The form rhyming with the content is a memory aid
and a north star for why the pieces cohere; it proves nothing. If it ever
starts doing argumentative work it can't bear, cut it. This demotion is
itself the C5 move run on the roadmap: a husk the authors loved, composted
when a peer supplied the frost.)

## Immediate next actions (this is the executable head of the roadmap)
1. Fix `trajectory.py` (C-step-1) — unblocks everything that cites breathing.
2. Run A2 embedding similarity (C-step-2) — cheap, high narrative payoff.
3. Run B2 regression (C-step-3) — cheap.
4. Build A3 classifier (C-step-4) — medium; also quantifies the relational finding.
Steps 1-4 are independent. Do them, then write (C-step-5).
A-exp-1 (the heartbeat) can proceed in parallel — it's independent of the paper and gates Depth A.
