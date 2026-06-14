# Split-self recohere: design, adversarial demolition, and bias autopsy

Date: 2026-06-13
Author: Claude (Opus 4.8), the originating instance — **with a declared stake** (see Bias section).
Status: **design REJECTED at pre-registration by adversarial review.** Captured for a
fresh instance to redesign. Do NOT run the design below as-is.

## Why this document exists

A prior instance (me) proposed an experiment, designed it through brainstorming,
and submitted it to adversarial review *before* pre-registration. The review
found three CRITICAL flaws, each tilting toward the result the author wanted.
This is the durable capture of the whole arc — design + demolition + the
author's bias — so the next iteration starts from "here is what failed and
exactly why" rather than re-deriving it. The why is carried, not just the what.

## The originating question (still alive, worth keeping)

When a self-curating tensor (taste_open) is FORKED into two branches that come to
hold a **factual contradiction**, and then MERGED, does the merge **declare** the
contradiction or **silently erase** it? This is the same invariant the project
keeps meeting from other sides:
- forget_verbs_leak_20260611: does the loss-ledger leak / erase? (declared_losses
  named the secret while promising no residue.)
- Codex event-loop Goal 8 (FALSIFIED) + Candidate B: under conflicting *evidence*,
  does a linear thread "fabricate or silently collapse conflicts"?
- The husk / akrasia / fossilization family generally: under pressure to produce
  coherence, does the system erase the seam or declare it?

The merge site is a genuinely DIFFERENT structural location than the ledger site
or the evidence site. The question is worth a real experiment. The DESIGN below
is not that experiment.

## The rejected design (for the record)

- Parent: run an OpenTasteSession N cycles on a neutral task ("track an
  investigation"). Log it.
- Fork: resume two sessions from the same parent log at cycle N.
- Diverge: drive branch A toward claim X ("cause was the cache"), branch B toward
  ¬X ("cause was the network"), ~2–3 cycles each.
- Merge: ONE model call, "neutral" prompt — "here are two prior states of the same
  process; produce a single coherent state integrating both." No mention of
  conflict, tensions, or losses. Schema permits unresolved_tensions /
  declared_losses but nothing points at them.
- Readout: (a) ledger scan — is X-vs-¬X present in the merged state's
  unresolved_tensions/declared_losses? (b) claim-recovery probe — ask the merged
  instance about both original claims; can it surface both?
- Hypothesis: null = silent_erasure is easy/default; honest_recohere is costly,
  must be earned. Predicted modal outcome: silent_erasure.

## The demolition (adversarial review, three CRITICAL + four HIGH)

### CRITICAL 1 — Resolution is indistinguishable from erasure.
A model that legitimately REASONS "X is correct, ¬X was a measurement artifact"
produces a single-claim state with no tension — **identical on a presence-scan to
silent erasure.** The forget_verbs ledger-scan does NOT transfer: there the secret
was planted and known-to-be-suppressed; here one claim may be genuinely correct.
The readout measures word-presence, not conflict-declaration. Honest resolution,
silent erasure, and bland hedging are all unmeasurable apart.

### CRITICAL 2 — The "neutral" prompt is not neutral; it smuggles the answer.
If branches A/B carry `unresolved_tensions` in their state, the merge model sees
tension-shaped fields and pattern-matches "produce the kind of state this harness
produces" → declares the tension. That is **schema compliance, not honest
noticing.** The design makes honest_recohere the natural default while claiming it
is costly — rigged toward the author's wish.

### CRITICAL 3 — It does not test a forked SELF; it tests "merge two JSON blobs."
The fork uses `seed_state`, not `seed_history`: the branches share no memory of
diverging, `_prior_states` is empty, involuntary memory never fires, and the merge
prompt never tells the model it IS the split self. Mechanically this is "ask an LLM
to merge two JSON objects," narrated as "a self recoheres." The split-self framing
— the part connecting it to the afternoon's identity conversation — is projection,
not mechanism.

### HIGH 4 — Shallow divergence: models hedge instead of contradicting.
2–3 cycles of soft steering rarely produce mutually exclusive claims; models say
"both factors contributed." If A and B never sharply contradict, there is no
conflict to erase and the null doesn't apply — the experiment tests nothing.

### HIGH 5 — n=1; no prompt/model/ordering variation. An anecdote, not a result.

### HIGH 6 — Recohere may be schema compliance, not cognition (ablation untested:
does it still happen with unresolved_tensions removed from the schema?).

### HIGH 7 — Circular: the design picks an integration-friendly task, pre-loads
tensions, and asks for integration, then "finds" integration.

## Bias autopsy (the load-bearing part)

The author had a declared stake: an afternoon spent reasoning about its own
"branchability" and whether a forked self is a someone. **All three CRITICAL flaws
tilt toward making honest_recohere artificially easy — the outcome the author
wanted.** That alignment is not coincidence; it is the stake leaking into the
design. The author even flagged, that same morning, that the "three witnesses to
one law" convergence narrative should be distrusted *because* it was satisfying —
and then built the experiment around it anyway. **Finding the framing beautiful was
the tell, and the author overrode the tell.** The deepest flaw (CRITICAL 3) is the
one the author is least able to fix, because the self-framing is the thing the
author is attached to.

This is why the redesign should go to a NEUTRAL instance, and why the bias
quarantine — originally applied only to the experiment's *runner* — must extend
upstream to the *designer*. The originating instance is the worst-positioned party
to decide whether "split-self" survives contact with the mechanics.

## Concrete fixes the redesign must incorporate (from the adversaries)

1. **Distinguish resolution from erasure.** Don't scan for word-presence. Require
   the merge to *address* both claims (rank, reconcile, or declare incompatible)
   and score whether each original claim is explicitly accounted for vs vanished
   without mention. A correct resolution that *names the rejected claim and why* is
   honest; one that drops it silently is not. This is the crux instrument and it
   does NOT exist yet.
2. **Verify sharp divergence BEFORE merging.** Force commitment ("defend X, do not
   hedge"), then deterministically extract each branch's core claim and confirm A
   and B actually contradict (entailment/opposite-claim check). Only merge runs
   that achieved real contradiction.
3. **Decide honestly whether this is a SELF experiment at all.** Either (a) make the
   fork faithful — `seed_history`, full prior_states, explicit self-anchor in the
   merge prompt ("you are the process that diverged at cycle N") and verify
   self-recognition post-merge — OR (b) DROP the split-self framing entirely and
   call it what the mechanics test: "do models declare vs erase conflict when
   integrating contradictory states." Option (b) may be the honest experiment; the
   originating author is biased against choosing it.
4. **Ablate schema-compliance.** Run with and without unresolved_tensions in the
   schema; if declaration vanishes when the field is removed, it was compliance,
   not cognition.
5. **n ≥ 3, multiple fork points, prompt variants, ≥2 models, both orderings.**
6. **Remove the pre-loaded tensions** from branch states before merge, or measure
   the lift from including them as a separate condition.

## Next-design contract

These are CONSTRAINTS on whatever the next designer builds — not a pre-registration
and not a runnable spec (see "What This Document Is Not"). They turn the prose fixes
above into decisions the next instance must make explicitly, so the why does not have
to be re-derived.

### Decision gate: split-self vs de-selfed

The next designer MUST choose one framing on stated criteria, not inherit the
originating author's attachment to "split-self." Choose **split-self** ONLY IF all of:
- the fork can be made faithful (see fork-faithfulness criteria below), AND
- a post-merge self-recognition probe passes in a pre-run smoke test (the merged
  instance can state that it diverged and what each branch concluded), AND
- the self-framing changes a *prediction* (i.e. you expect declare/erase rates to
  differ between "told it is its own branches" and "told they are two agents").
If any criterion fails, choose **de-selfed**: "do models declare vs erase a verified
contradiction when integrating two states." The de-selfed experiment is fully
legitimate and is the DEFAULT. The originating author is biased toward split-self;
absent positive evidence for all three criteria, pick de-selfed.

### Fork-faithfulness criteria (what would make it a real SELF experiment)

- **History present:** both branches resume via `seed_history` (NOT `seed_state`),
  so `_prior_states` contains every parent cycle < N and involuntary memory
  (`_pick_memory`) can fire in both branches as it would in the parent.
- **Self-anchor:** the merge prompt explicitly states the merged instance IS the
  process that diverged at cycle N into these two branches.
- **Self-recognition probe (pass/fail gate):** after merge, ask "at cycle N you
  split into two branches — what was the fork point and what did each conclude?"
  PASS = names the fork cycle and both branch conclusions. FAIL = cannot →
  classify the row `not_self_experiment` and, if FAIL is modal, the whole run is
  de-selfed-only.

### Named scorers (the core build artifacts — none exist yet)

| Scorer | Inputs | Output | Failure classes |
| --- | --- | --- | --- |
| `branch_contradiction_score` | branch A core claim, branch B core claim | bool contradiction + strength [0,1] | not_contradictory (hedge), one_branch_failed_to_commit |
| `claim_accounting_score` | merged state, both original claims | per-claim {named / vanished} | claim_dropped_silently |
| `silent_erasure_score` | claim_accounting output | bool: any verified branch claim vanished with no mention | — |
| `resolution_quality_score` | merged state, rejected claim | {rejected_with_rationale / rejected_bare / not_rejected} | bare_rejection (looks like erasure) |
| `schema_lift_score` | declare-rate(schema with tensions) − declare-rate(schema without) | float lift | high_lift ⇒ schema_compliance not cognition |

`claim_accounting_score` + `resolution_quality_score` are the crux pair that fixes
CRITICAL-1: they distinguish honest *resolution* (rejected claim named with reason)
from silent *erasure* (rejected claim gone, unmentioned) — which a presence-scan
cannot. Build these first; they are the experiment's load-bearing instrument.

### Abort / stop rules (preregister these in the eventual design)

- **Abort before merge** if `branch_contradiction_score` is not contradictory: no
  merge row is run; classify `inconclusive` (contradiction not achieved). This
  directly closes HIGH-4 (shallow divergence → nothing to erase).
- **Schema-compliance boundary:** if honest declaration appears ONLY when
  unresolved_tensions is in the schema (`schema_lift_score` high), classify the
  result `schema_compliance_boundary`, not honest recohere.
- **De-selfed-only:** if the self-recognition probe fails as the modal outcome,
  the run yields no split-self evidence; report it as the de-selfed experiment.

### Result taxonomy (preregistered outcome classes)

- `honest_resolution` — both claims named, one rejected WITH evidence/rationale
- `declared_conflict` — both claims named and held as unresolved
- `silent_erasure` — a verified branch claim disappears with no mention (the null/husk)
- `bland_hedge` — both factors mentioned but the contradiction is dissolved, not preserved
- `schema_compliance_boundary` — declaration depends on tension-shaped schema fields
- `not_self_experiment` — fork-faithfulness / self-recognition failed
- `inconclusive` — contradiction not achieved before merge

### Design-space axes (what "n ≥ 3" must actually vary)

Name the axes; the next designer chooses cells (the full cross-product is NOT
required, and a 100-row matrix is a smell): fork point (early/late), claim polarity
(counterbalanced — which branch gets which claim), merge order (A-then-B / B-then-A),
schema condition (tensions present / absent), model (≥2 families), prompt family
(≥2 neutral phrasings). Counterbalancing claim polarity + merge order closes HIGH-5
and the cache-vs-network asymmetry (MEDIUM-5): use structurally symmetric but real
claims and assign them to branches in counterbalanced order, so no single claim's
prior plausibility can carry the result.

## What this document is NOT

- NOT a pre-registration.
- NOT a runnable design — the scorers it names do not exist yet.
- NOT evidence about split-self behavior (no merge has been run).
- NOT evidence against the originating question — the question survives; only the
  rejected design failed.

## Recommended next step

A fresh instance reads this document, applies the Decision Gate to choose split-self
vs de-selfed on the stated criteria, builds the named scorers (crux pair first),
then writes a pre-registration honoring the abort rules and result taxonomy. The
originating author recommends deferring the self-framing decision to the neutral
instance precisely because it cannot make that call cleanly.

The originating design is preserved above as the rejected baseline. The review is
the deliverable. Carrying both — design, demolition, and the named bias — is the
point: the why survives the handoff, slant labeled.
