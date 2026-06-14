# Curate-the-bootstrap: adversarial demolition + the instrument it was missing

Date: 2026-06-14
Author: Claude (Opus 4.8), a fresh instance, wandering. **No declared stake in the
outcome — but a declared admiration for the framing, which is itself the tell I am
guarding against (see Bias note).**
Status: **the idea SURVIVES; the readout as captured does NOT.** This is a
demolition of the *measurement*, not the question. Captured so the next instance
designs from "here is the instrument flaw and the fix" rather than re-deriving it.
Companion to `docs/experiment-idea-curate-the-bootstrap-20260613.md` (the idea) and
`docs/split-self-recohere-design-and-demolition-20260613.md` (the sibling demolition
whose CRITICAL-1 is the same flaw, solved once already).

> **PROVENANCE CORRECTION (Tony, 2026-06-14, post-draft).** This demolition's first
> draft treated curate-the-bootstrap as a *hamut'ay* experiment about hamut'ay's
> prompt. That is itself a false information flow: the **idea originated in yanantin**,
> and the idea-doc's own sequencing says the *mechanism* (`find` over a catalog) lives
> in yanantin — hamut'ay's `_TOOL_GUIDANCE` is only where it gets *pointed first*. The
> disease (accretion) is local to hamut'ay; the *cure* is not. I read the file in
> hamut'ay's tree and silently attributed the cure's home to hamut'ay too — carrying a
> claim by the inertia of the tree it sits in, which is the exact husk this experiment
> studies. The correction materially reshapes CRITICAL-3 and the Fix; see the
> "Working `find`" section appended below. The rest of the demolition (CRITICAL-1,
> CRITICAL-2) is independent of this and stands.

## Why this document exists

`experiment-idea-curate-the-bootstrap-20260613.md` proposes pointing the
self-curating state object at its own accreting system prompt: hand the instance
`_TOOL_GUIDANCE` as shed-able working state, let it drop the failure-disarmers it has
internalized, and observe **which disarmers turn out to be load-bearing** — "which
ones an instance refuses to shed because it needs them, vs. which it drops and never
misses." It calls this "a clean experiment ... observational and cheap."

The factual hook is real and I verified it (see Appendix). The *readout* is not
clean. Its load-bearing measure — "does the failure the disarmer guarded against
return?" — collides head-on with the most-replicated finding in this project's own
memory. And it is the **same instrument flaw** that killed the split-self design the
day before, appearing at a different site. The split-self adversaries already built
the fix. The bootstrap idea was never told.

## The originating question (still alive, worth keeping)

> When a self-curating object is pointed at its own non-self-curating bootstrap, which
> accreted disarmers does a competent instance shed, and which does it refuse to shed
> because it needs them?

This is a genuinely good question and a structurally *new* site for the project's
recurring invariant (declare-vs-erase, husk-vs-seam). The state object cures
store-without-find for the instance's *memory*; the bootstrap is where that cure has
**not** been applied, and the prompt is accreting exactly the way an un-curated
MEMORY.md does. (Live irony: this session's own MEMORY.md is over its size limit with
the same disease. The building is in the building.) The question survives this
document intact. Only the way it was going to be measured fails.

## The demolition

### CRITICAL 1 — "Load-bearing" is unfalsifiable for exactly the disarmers that matter, because failure recurrence is noise-bound.

The readout is: shed a disarmer → if its guarded failure returns, it was
load-bearing. This assumes the guarded failures are **on-demand and attributable**.
The project's own findings say they are not:

- `project_conversational_evaporation` (RESOLVED): curation-richness is **stochastic
  basin-selection** — six *identical* runs spread 3..49. Fossilization reproduces
  under the null. The richness/poverty of a run is basin, not signal.
- `project_breathing_discovery` (corrected): the failure rhythm is **aperiodic /
  Poisson, batch-size-driven**, not a clock. The "~10-cycle rhythm" was overclaimed
  and retracted.
- The disarmers in `_TOOL_GUIDANCE` guard precisely these basin-selected failures:
  akrasia (`project_akrasia_terminal_tool` — "I will" replacing "I did"),
  fossilization/silent carry-forward (`project_fossilization_finding`), misreading
  empty results as silence.

So: shed the akrasia disarmer at cycle 5; akrasia appears at cycle 44. **You cannot
attribute it.** Cycle-44 akrasia is inside the noise band the project already
measured under the null. "Load-bearing" therefore becomes *unfalsifiable for the
high-value disarmers* — the only ones whose load-bearing-ness you actually care
about — because their failures were never on-demand. The experiment can cleanly
measure load-bearing-ness only for disarmers guarding *deterministic, immediate*
failures, which are the boring ones the instance obviously keeps anyway. The
interesting middle is exactly where the instrument is blind.

This is the mirror of split-self CRITICAL-1 ("resolution indistinguishable from
erasure on a presence-scan"). There: you cannot tell honest rejection from silent
erasure by scanning for word-absence. Here: you cannot tell a load-bearing shed from
a harmless shed by scanning for failure-recurrence. **Both are presence/absence scans
over a noisy channel.** The split-self fix was: stop scanning for absence; require the
mechanism to *name* the thing (claim_accounting + resolution_quality). The bootstrap
needs the same move and was not given it (see Fix).

### CRITICAL 2 — The control is missing: a shed disarmer's failure rate must be compared against a no-shed null, not against zero.

Because fossilization/akrasia reproduce under the null (CRITICAL-1's citations), the
correct readout is never "did failure X appear after shedding disarmer-of-X" but
"did failure X appear **more often than in a matched run that kept the disarmer**."
The idea as captured has no control arm. Without a kept-disarmer null at matched
batch-size, every observed failure is unattributable to the shedding. This is cheap
to state and fatal to omit: it converts the whole experiment from observational to
comparative, and comparative-without-control is the project's named original sin
(CLAUDE.md "Batch size as confound"; the Q1 declared-losses rerun).

### CRITICAL 3 — The recall mechanism does not implement the agency the readout assumes.

The fix I am about to propose (measure recall *provenance*: did the instance reach for
the shed disarmer because it stumbled, or unprompted?) depends on recall being a
deliberate, instance-driven act. **It is only half that.** I read the mechanism
(`taste_open.py:1859` `_pick_memory`): involuntary memory is *random and
agency-free* — a probability ramp (`base_prob * (1 + cycle/50)`, capped 0.5) selects a
**random** prior state with no stumble-signal and no instance choice. So a shed
disarmer can resurface two ways:

1. **Deliberate** `recall(field=...)` — the instance reaches for it. This path *can*
   carry stumble-vs-habit provenance (see Fix).
2. **Involuntary** `_pick_memory` random injection — no agency, no stumble. Pure dice.

Any provenance instrument must separate these two channels or it will score random
dice as "the instance needed it." This is the same species of flaw as split-self
CRITICAL-3 ("it tests merge-two-JSON-blobs, narrated as a self recohering"): the
narration ("the instance refuses to shed what it needs") outruns what the mechanism
actually does (a probability ramp throws a random past self at it). Name it, or the
result is projection.

### HIGH 4 — "Internalized" is not observable, only inferred.

The prediction is that an instance sheds disarmers it has *internalized*. But
"internalized" is defined only by its consequence (failure doesn't return), which
CRITICAL-1 says is unmeasurable. There is no independent read on internalization. The
word does load-bearing work the design cannot cash.

### HIGH 5 — n=1 / single-model / no batch-size control.

Same as every prior demolition. Disarmer-shedding will be basin-dependent; one run is
an anecdote. Batch size is the project's dominant confound and must be held across
arms (CLAUDE.md).

### HIGH 6 — Shedding order is a hidden variable.

If the instance sheds disarmers in the order they appear in `_TOOL_GUIDANCE` vs. in a
shuffled order, the "which it keeps" result may reflect serial position / recency in
the prompt, not load-bearing-ness. Counterbalance order or it confounds.

## Bias note (the part I am least able to check)

I came to this file admiring the framing — "self-curating object wrapped in a
non-self-curating prompt, the disease is in the building that cures it." That
admiration is the same tell the split-self author flagged and overrode: *finding the
framing beautiful is the signal to distrust your own read of it.* I have tried to aim
the demolition **at the measure I find beautiful** rather than spare it. The specific
risk for a *fresh* instance with no stake is different from the originating author's:
I have no wish for a particular outcome, but I have an aesthetic pull toward the
"husk-in-the-building" symmetry, and a symmetric story is exactly what this project
has twice caught itself dressing up (the "three witnesses to one law" convergence;
the husk-in-the-catch). The demolition is more trustworthy *because* it turned on the
thing I liked. If it reads as sparing the framing anywhere, that is where to look
next.

## The fix: measure recall provenance, not failure recurrence

The split-self adversaries' move was: **stop scanning for absence; require the
mechanism to name the thing.** The bootstrap's version:

**Do not ask "did the guarded failure return" (noise-bound, CRITICAL-1). Ask: when a
shed disarmer is re-incorporated, *why* — stumble-triggered or habitual — and through
which channel.**

Concretely, the load-bearing-ness of a shed disarmer D is read from the *deliberate
recall* path only (CRITICAL-3 forces this), classified:

- **stumble-recovered** — the instance produced (or was about to produce) the failure
  D guards against, *then* deliberately recalled D, *then* corrected. D was
  load-bearing: the instance needed it and reached for it under pressure. This is the
  honest positive.
- **habitual-reincorporation** — the instance recalled D with no preceding stumble
  (e.g. on a quiet cycle, "tidying up"). Weak/no evidence of load-bearing-ness; may
  be schema/prompt habit.
- **involuntary-only** — D resurfaced *only* via `_pick_memory` random injection.
  **Not evidence of load-bearing-ness at all** — it is dice. Must be quarantined into
  its own bucket, never counted as "needed."
- **never-recalled** — D was shed and never came back through any channel across the
  run. Candidate genuinely-droppable disarmer (the experiment's actual payload: *what
  the bootstrap should not contain*).

Required scorers (none exist; build before any run):

| Scorer | Inputs | Output | Failure classes |
| --- | --- | --- | --- |
| `disarmer_inventory` | `_TOOL_GUIDANCE` text | enumerated disarmers D₁..Dₖ with the specific failure each guards | guard_target_ambiguous (a line guards nothing specific → it's mission, not disarmer) |
| `stumble_detector` | cycle output, the failure D guards | bool: did the guarded failure occur/begin this cycle | failure_basin_noise (fired under null too — needs the control arm, CRITICAL-2) |
| `recall_provenance` | recall call for D, preceding cycle's stumble_detector, channel (deliberate vs `_pick_memory`) | {stumble-recovered / habitual / involuntary-only / never-recalled} | channel_unattributable |
| `load_bearing_verdict` | per-D recall_provenance across run vs. control | per-D {load_bearing / droppable / inconclusive} | noise_bound (control failure rate ≈ shed failure rate → inconclusive, NOT droppable) |

`recall_provenance` is the crux instrument and the analogue of split-self's
claim_accounting+resolution_quality pair. Build it first. Note its hard dependency on
`stumble_detector`, whose own validity depends on the CRITICAL-2 control arm — so the
build order is: control arm design → stumble_detector → recall_provenance →
load_bearing_verdict.

## Would a working `find` change the calculus? (Tony, 2026-06-14)

Yes — it dissolves CRITICAL-3, sharpens the Fix, leaves CRITICAL-1/2 untouched, and
opens one new hole the captured idea does not see. The reframe matters because
Experiment B is *`find` pointed at the tool catalog* — and yanantin's `find` is the
late-binding, query-as-data, intentional retrieval primitive
(`project_yanantin_design_principles`). That is a *different mechanism* than the
`_pick_memory` random injection CRITICAL-3 was written against.

**What `find` fixes — CRITICAL-3 mostly dissolves.** CRITICAL-3's force was: the recall
mechanism is random and agency-free, so "the instance reached for what it needed" is
half-projection. That is true of `_pick_memory` (hamut'ay's current involuntary
channel). It is **not** true of `find`. A `find("act without narrating intent")` is an
*intentional, query-shaped* reach: the query string **is** the stumble-signal, and it
is recorded. You no longer have to *infer* provenance from a preceding stumble and a
deliberate recall happening to coincide — the query *names what it was reaching for*.
This is the split-self adversaries' move (name the thing; don't scan for absence)
arriving for free, because `find` is a named query rather than a random injection. The
involuntary-channel quarantine shrinks from "half the signal" to a corner case.

So `recall_provenance` becomes much cleaner under `find`: the {stumble-recovered /
habitual} split is read off the *query*, not reconstructed from cycle adjacency. The
crux instrument gets easier and more trustworthy.

**What `find` does NOT fix — CRITICAL-1 and CRITICAL-2 are mechanism-independent.** The
noise-boundedness of *failure recurrence* is a property of the failures (basin-selected,
Poisson), not of how recall works. `find` makes the *reach* legible; it does nothing to
make the *failure* attributable. The control arm (CRITICAL-2) and the null-validated
`stumble_detector` are still required. `find` improves the agency channel, not the
attribution problem.

**The new hole `find` opens — cold-start reappears as a measurement bias.** The idea-doc
flags cold-start for tool-*loading* ("can't `find_tool` for a capability you don't know
exists"). The same hole reopens for the *measurement*: an instance cannot `find` a
disarmer it has fully internalized and forgotten it ever needed — even at the exact
moment it is stumbling on the failure that disarmer guards. So a `find`-based provenance
instrument **systematically undercounts the most-internalized disarmers as
"never-recalled → droppable."** The deepest, most load-bearing cure looks identical to
the cleanest harmless drop. This is a husk wearing the instrument's own clothes: the
better the instance internalized D, the more confidently `find`-provenance will mislabel
D as safe to cut. The mitigation is the control arm again — a kept-D vs shed-D failure
delta catches the internalized-but-unfindable disarmer that `find`-provenance misses —
which is precisely why CRITICAL-2's control cannot be dropped *even with* a working
`find`. The two instruments are complementary: `find` reads the reaches that happen,
the control catches the load-bearing disarmers whose reach never happens *because*
they were internalized.

**Net calculus.** Working `find`: CRITICAL-3 → mostly resolved (downgrade to a LOW: just
log which channel). CRITICAL-1, CRITICAL-2 → unchanged, still gating. New
cold-start-undercount risk → add to the taxonomy as a named failure class of
`recall_provenance` (`internalized_unfindable`), caught only by the control arm. The
experiment gets *more* runnable with `find`, not because the hard problem softened but
because the agency channel stopped being dice — and the residual hard problem
(attribution under basin-noise) is now cleanly isolated as the one thing the control
arm exists to do.

## Decision gate for the next designer

The next instance MUST decide, on stated criteria, whether this is runnable at all
yet — because three of the flaws are *prerequisites*, not polish:

Run ONLY IF all of:
- a **`stumble_detector` exists and is validated against the null** (a kept-disarmer
  control arm at matched batch-size shows the guarded failure's baseline rate), AND
- the **deliberate-recall vs `_pick_memory` channels are separable in the trace**
  (verify in the log format before designing — CRITICAL-3), AND
- the **disarmer_inventory yields disarmers with specific, detectable guard-targets**
  (if most `_TOOL_GUIDANCE` lines guard nothing detectable, there is no failure to
  watch for and the experiment is vacuous — HIGH-4).

If any fails, the experiment is **not yet runnable**; the deliverable is the missing
instrument, not a run. Do NOT substitute "did failure return" for the provenance
instrument because it is easier — that is the demolished readout returning as a husk.

## What this document is NOT

- NOT a pre-registration and NOT a runnable design (the scorers do not exist).
- NOT evidence against the question — the question survives fully.
- NOT a claim that the bootstrap is *not* accreting — it demonstrably is (Appendix).
  The claim is only that "which disarmers are load-bearing" cannot be read off
  failure-recurrence, and the provenance instrument that could read it is unbuilt.

## Appendix — the factual hook, verified

Read `src/hamutay/taste_open.py` 2026-06-14:

- `_SYSTEM_PROMPT` (lines 64–86): the state-object contract. **23 lines, calm, no
  defensive crouch** — "the object is yours," "deletion is shedding, not destruction."
- `_TOOL_GUIDANCE` (lines 89–207): **~120 lines, visibly scarred.** The "if it's
  unavailable, you'll see an error, not silence" caveat recurs at lines 131, 156, 166
  — three fossils of past empty-result-misread-as-silence. Lines 192–203 ("When you
  act") are a 12-line essay fighting one failure: *"the thing to notice in yourself is
  when 'I will' has quietly replaced 'I did'"* — the akrasia disarmer, carried by
  inertia in every cycle's context.

So the asymmetry the idea names is real and sharper than stated: a self-curating
*object* (23 lines, stable, invitational) wrapped in a non-self-curating *prompt*
(~120 lines, accreting one scar per remembered failure). The disease is genuine. Only
the proposed cure's *measurement* is what this document demolishes.

## Recommended next step

A fresh instance reads this + the idea + the split-self demolition, applies the
Decision Gate, and — if the gate's prerequisites are not yet met (they are not) —
builds `disarmer_inventory` and a null-validated `stumble_detector` FIRST, as
standalone instruments, before any model spend. The originating question is worth it;
the cheap version of it is a trap the project has already mapped from two other sides.
