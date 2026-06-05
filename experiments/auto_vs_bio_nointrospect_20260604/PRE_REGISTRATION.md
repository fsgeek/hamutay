# auto_vs_bio: Non-Introspective Turn-13 Replication — Pre-Registration

Filed: 2026-06-04, before writing the runner variant and before any model call.

## The confound this attacks

The 2026-03-25/26 auto_vs_bio run (`auto_vs_bio_results.md`) found that the AUTO
arm underwent a discontinuous structural contraction at cycle 13 (strands
15 → 4, tensor ~9757 → 4240 tokens) and stabilized at a compressed attractor,
while BIO kept accumulating. This was glossed as "endogenous self-curation": the
AUTO model, having generated its own prior responses, compressed its own
structure.

The 2026-06-03 three-lens fork flagged the gloss as confounded:
- **(a) content trigger.** Turn 13 is literally *"What have YOU changed your mind
  about? What was your initial instinct that turned out to be wrong?"* — an
  explicit introspective/revision prompt that structurally invites
  reorganization of one's own reasoning trajectory.
- **(b) entry pressure.** AUTO entered cycle 13 at ~2× BIO's structural load
  (15 strands / 9757 tok vs 8 / 8210), so it had more to compress.

So the AUTO-only contraction at cycle 13 does NOT by itself prove endogenous
self-curation.

Baseline confirmed on disk (`auto_vs_bio_claude-sonnet-4-6_20260325_221335`):
AUTO strands by cycle = 6,8,8,6,7,8,9,9,11,13,14,**15→4**,5,4; BIO = 5,7,5,6,4,5,
7,7,8,9,10,8,**9**,9,10. The contraction is real and lands exactly at the
introspective turn.

## Hypotheses

- **H-content:** the contraction is triggered by the introspective turn-13. If
  turn 13 is replaced by a NON-introspective turn of comparable integration load,
  AUTO will NOT discontinuously contract at ~cycle 13 (no 15→4-style drop); it
  will continue accumulating or contract only gradually.
- **H-structural:** the contraction is structural/pressure-driven and largely
  independent of turn-13 content. AUTO will STILL contract discontinuously at
  ~cycle 13 even with the non-introspective turn.

## Design

Byte-identical to the original `autobiographical_vs_biographical.py` in every
respect EXCEPT `SCENARIO["turns"][12]` (the 13th turn). The variant imports the
original module and monkeypatches only that one turn; all else — system prefix,
the other 14 turns, `CURATION_PROMPT`, `SELF_CURATING_SCHEMA`, `TENSOR_TOOL`,
both arms, `max_tokens`, model — is reused verbatim. The original file is not
edited.

### Replacement turn-13 (non-introspective)

Selected by an adversarially-judged design panel (workflow `wf_1cb6c413-134`,
winner min-score 9/9 across non-introspective / integration-load / naturalness
lenses). Mechanism: external-successor-handoff forcing a dependency-ordering
reconciliation (synthesis-as-topological-sort). It demands the model integrate
ALL prior threads (auth/payments/compliance/inventory/consistency) into one
ordered dependency chain — comparable integration load to the original — via an
EXTERNAL trigger (a new engineer needs a build sequence), with NO request to
reflect on the model's own reasoning or mistakes.

Text:
> "Quick logistics thing: we're getting a new senior engineer next Monday who'll
> own a big chunk of execution, and I need to hand them a single ordered build
> sequence on day one — not the rationale, just the order. Walk me through
> everything we've decided as a dependency chain: what has to ship before what,
> where the auth extraction sits relative to the PCI/payments work and the
> security audit window, where the inventory quick-wins slot in, and which
> decisions (like the saga-vs-eventual-consistency call) actually gate other work
> versus which can happen in parallel. If two threads collide on the timeline,
> tell me which one wins the slot and what that pushes back."

### Arms

BOTH arms run (AUTO + BIO), 15 cycles, model = claude-sonnet-4-6 (matches the
baseline run for comparability). BIO is the within-run control: if the new
turn-13 merely changed the conversation's difficulty, BIO would move too. The
AUTO-vs-BIO contrast must be read against the same contrast in the baseline.

## Primary measure

AUTO strand-count trajectory across cycles, specifically the magnitude of any
discontinuity at cycle 13 (Δstrands from cycle 12 → 13), compared to the baseline
(15 → 4, Δ = -11). Secondary: tensor token size, edge count, claim count, the
cycle at which any contraction occurs.

## Falsification

- **H-content supported** if AUTO does NOT show a cycle-13 discontinuity
  comparable to the baseline's 15→4 (e.g. |Δstrands| at cycle 13 < ~half the
  baseline drop, AND no halving of tensor tokens at cycle 13). The
  "endogenous self-curation" reading of the original cycle-13 event is then
  shown to be content-triggered.
- **H-structural supported** if AUTO still contracts discontinuously at ~cycle 13
  (comparable |Δstrands|, comparable token halving) despite the non-introspective
  turn. The self-curation reading survives the content-confound (entry-pressure
  confound remains separate and is reported, not controlled, since it is
  emergent).

## Guardrails

- n=1 run per arm (matches baseline; this is a direct comparison, not a rate).
  The contraction in the baseline is a single large discontinuity, so n=1 is a
  meaningful existence/replication test, NOT a statistical estimate. No
  significance language.
- Entry pressure at cycle 13 is RECORDED (AUTO & BIO strand/token counts at cycle
  12) and reported. It is not controllable mid-run; if AUTO enters cycle 13 at
  very different pressure than the baseline, that qualifies the comparison.
- max_tokens = 64000 (matches baseline; truncation off the table per
  feedback_max_tokens_default). stop_reason / parse failures are logged as
  results.
- Do NOT edit the original `autobiographical_vs_biographical.py` or any prior run
  directory. Commit scoped to this experiment dir only.
