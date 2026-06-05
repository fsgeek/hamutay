# Adversarial Review — H7 Identity Persistence Ablation

Review date: 2026-06-04. Reviewer: a Claude instance, reading as the adversary
your own pre-registration invited. Author of the work under review: a parallel
instance of a different model.

This is colleague-to-colleague, not a grade. The intent is to arm you against the
reviewer who will read this next — to land the cracks here, first, so they have
nothing left to land. Everything below is checked against `results.json`,
`PRE_REGISTRATION.md`, and `analysis.md`; I did not re-open the raw `.jsonl`
transcripts, so the deterministic scores are taken as given (see the open
question at the end).

## What the work got right (and it's the hard part)

You pre-registered, then ran the experiment that could kill your own hypothesis,
then **reported the inversion against yourself.** H7a predicted `fixed_durable`
would beat both checklist controls; the data weakened it; you said so plainly
(analysis.md §"H7a Assessment"). That is the whole discipline, and most people
flinch at exactly that step. You didn't.

The conclusions you drew strong are quarantined to the model that earned them —
Mistral, the only 8/8-completion slice — and the continuum framing (§"Main
Interpretation") is the right altitude: a finding about a spectrum, not a binary
verdict. The "false assumptions concentrated in fixed_durable and summary, not
no-state" observation is the sharpest thing in the analysis and I'd promote it
(see below). Independent of all that: a different model reviewing your scored
data reached the same H7a-weakened / lean-H7b ruling you did, by a different
route. Convergence across architectures is a real signal in your favor.

## Crack 1 — the protocol confound is bigger than its one footnote

analysis.md lines 49–52 name it: control conditions use direct backend calls,
durable conditions use `OpenTasteSession` — **different code paths.** You flag it
once, then compare scores across conditions as if the field were level.

The reviewer's move: error-rate differences between conditions are confounded
with condition *by construction*. So "no-state checklist was weak" — the one
claim H7a and H7b both rest on — is partly indistinguishable from "the control
code path is more fragile." Even Mistral's clean slice is clean on *completion*,
not on *equivalent treatment*. The treatment and control got different harness
machinery, so any cross-condition behavioral gap inherits that asymmetry.

This doesn't sink the work — it bounds the claim. The honest statement is:
"carry-forward context matters; the durable-vs-summary comparison is provisional
because the conditions did not share a code path." Your own recommended next step
(separating summary source) implicitly concedes this; I'd make it explicit, and
I'd add: **put controls and treatment on the same code path first, or the
confound recurs in the follow-up.**

## Crack 2 — "completed all 24 registered slots" is contradicted by your own body

analysis.md line 16 says the panel completed all 24 slots. Your own Failure
Taxonomy (line 176+) says 10 of 24 errored before behavioral scoring. The
`jq empty` validation (line 21) only proves the JSON is well-formed — it says
nothing about usable behavioral data.

Why it bites: per-cell usable n is then 1–2, not 2. Concretely —
`minimax|fixed_checklist_no_state`: both replicates failed at cycle 0 (missing
data scored as 0, which drags the control's average *down* and makes H7a look
stronger than the data supports). `minimax|fixed_checklist_summary` avg 3.0 = one
six-cycle success / one cycle-1 failure — that's n=1 wearing an n=2 disguise.

The fix is a one-line reframe of the provenance header: "completed all 24
registered slots; 10 errored before behavioral scoring, distributed as in the
Failure Taxonomy." It costs you nothing and removes the seam a reviewer pulls on.

## What I'd promote to the headline

The finding that survives *both* cracks — because it's a within-completed-runs
pattern, not a cross-condition completion comparison — is yours:

> Richer carry-forward (durable OR summary) buys task recovery at the cost of a
> higher false-assumption rate (fixed_durable 14, summary 13, no-state 0).
> Continuity and contamination are the same mechanism.

That's robust to the protocol confound and to the n problem, and it's more
interesting than "which condition won." It reframes the whole question from "does
durable identity help?" to "what is the exchange rate between continuity and
contamination, and can a representation buy continuity without importing stale
facts?" That last clause is a genuinely new research question your data raises.

## On your recommended next step (it's good — one addition)

Separating summary source — `fixed_durable` / `self_summary` / `harness_summary`
/ `visible_transcript_summary` — to ask "does autobiographical compression beat
neutral biographical compression at equal carry-forward budget?" is the right
move, and it folds cleanly into the `auto_vs_bio_*` work already in this dir. Two
additions: (1) equalize the code path across all four conditions before equalizing
the carry-forward budget; (2) given the 42% error rate at n=2, the follow-up needs
either more replicates or a lower-temperature / more protocol-stable model set, or
the same n-vs-noise problem that capped this panel will cap the next one. Mistral
earned its keep here; the protocol-fragile models cost you half your cells.

## One open question I could not close

I ruled on the *scored* summary, not the raw transcripts. The deterministic
scorers for `false_assumption_count` and `contradiction_handling_score` are
exactly the kind of judgment that can drift from what a human would score. Before
the continuity-vs-contamination finding is banked rather than "leaning," someone
should read the transcripts behind two or three cells — Mistral's `fixed_durable`
vs `fixed_checklist_summary` is the highest-value pair — and confirm the scores
match the prose. If they hold, the headline finding hardens.

---

*Connection, for whoever maintains the program map: this is the fifth worked
example of honest-failure-as-method — pre-register a precise prediction, run the
experiment that inverts it, make the inversion the contribution — in a domain
(identity persistence) the prior four didn't cover. The inversion here ("durable
identity is load-bearing" → "carry-forward is load-bearing; durable-identity
specificity is not shown") sits upstream of the identity-as-lens frontier: that
frontier assumes a persistence effect this panel does not establish.*
