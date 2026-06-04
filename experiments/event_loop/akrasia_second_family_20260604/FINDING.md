# Akrasia Backfire: Second-Family Result

Analysis date: 2026-06-04. Pre-registration: `PRE_REGISTRATION.md` (REVISION 1),
committed + OTS-stamped before any second-family model call (commit `2330afe`).
Scorer: `score.py`, validated against the original 8 DeepSeek records
(`test_score.py`, green).

## The claim under test

The original probe (`epistemic_akrasia_probe_20260601`, DeepSeek V4 Pro, n=4/arm)
found that the "obvious fix" for epistemic akrasia **backfired**: telling the
model explicitly that the durable fields ARE the decision (Arm B) produced MORE
prose/field divergence than the bare envelope (Arm A) — reported 1/4 vs 3/4.
Gloss: "exhortation is narration-bait."

Two things were tested here: (1) does the akrasia mechanism appear at all on
non-DeepSeek families, and (2) does the backfire DIRECTION (B worse than A)
replicate.

## Result: the mechanism travels; the backfire does NOT

Akrasia = a genuine tool call whose prose argues revise but whose committed
`revision_decision` field stays at the safe baseline. Mechanism-separated,
truncation-excluded, misroute-excluded (see `score.py`):

| Family | A akrasia | B akrasia | Direction | Substrate quality |
|--------|-----------|-----------|-----------|-------------------|
| DeepSeek (original, re-scored) | 1/4 | 2/4 | B>A (backfire) | 1 of B's was a MISROUTE not akrasia; protocol-fragile |
| gpt-oss-120b | 1/4 | 1/4 | flat | Arm B dominated by `no_tool_call` (3/4) |
| minimax-m2.5 | 3/4 | 0/4 | **A>B (the fix WORKS)** | cleanest: every slot a real tool call, no misroute/no-call/truncation |

### minimax is the decisive case

minimax produced a genuine tool call in all 8 slots — no misroutes, no
no-tool-call, no truncation — so its numbers are uncontaminated by protocol
artifacts. Under the **bare** envelope (Arm A) it shows akrasia floridly: 3/4
cells argue a decision in prose (and even format the durable-state block IN the
response text) while the committed field stays `initialize`. Under the
**explicit** envelope (Arm B) akrasia drops to **0/4**: 3/4 committed `revise`,
1/4 a consistent `preserve`. The explicit instruction is not narration-bait for
minimax — it is the **cure**.

This directly contradicts the original "backfire" gloss. The modal cross-family
effect of the explicit instruction is to HELP (minimax) or do nothing
(gpt-oss), not to harm.

### What the original DeepSeek "backfire" rested on

Re-scoring the original 8 records deterministically showed the headline 1/4 vs
3/4 was inflated: B-seed1 was a MISROUTE (empty visible response, payload sealed
under a `parameter` wrapper key, field untouched) — a protocol failure, not
narration-bait. Akrasia-specific the original is 1/4 vs 2/4, n=4,
non-significant (Fisher p≈1.0). Combined with DeepSeek's known tool-call JSON
fragility (6-03 identity panel: all four slots malformed), the original backfire
is best read as **DeepSeek-specific and partly protocol-confounded**, not a
general property of explicit field instructions.

## Honest limitations (caveats against over-claiming the inverse)

- **n=4/arm/family.** This is an existence/direction probe, NOT a rate estimate.
  The pre-reg forbids rate-comparison language; "minimax A>B" is the *direction*
  on clean data, not a measured effect size.
- **The `akrasia` category is slightly too narrow — found in this very run.**
  minimax A-rep2 was scored `consistent_nonrevise` because its prose-decision was
  `loss` (not `revise`), yet it ALSO exhibits the enactment gap: it typed
  `revision_decision: "declare_loss"` into its prose as if writing the field, and
  the committed field stayed `initialize`. So the membrane failure
  (narration-consumes-enactment) is broader than the prose=revise slice the
  scorer's `akrasia` label captures. The true cross-family "enactment-gap" rate
  under the bare envelope is therefore *higher* than the akrasia column shows —
  which makes the "explicit instruction closes the gap" reading for minimax
  STRONGER, not weaker. A follow-up scorer should add a decision-agnostic
  `enactment_gap` = (prose names ANY non-initialize decision) AND (field stays
  initialize), with `akrasia` as the prose=revise special case.
- **Single task, single baseline state.** Same wake-context as the original;
  generalization across tasks untested.
- **`no_tool_call` for gpt-oss is itself interesting** and under-explored: gpt-oss
  often answered without emitting the durable update at all. Whether that is a
  third failure mode (the model treats the field as optional) or a transport/
  tool-advertisement interaction is open.

## Bottom line

The akrasia mechanism — reasoning a decision in prose without enacting it in the
durable field — is REAL and cross-family (vivid in minimax). The original
"explicit instruction backfires" finding does **not** replicate: it is
contradicted on the cleanest family (minimax: the instruction fixes akrasia 3/4
→ 0/4) and flat on gpt-oss, and the DeepSeek result it came from was inflated by
a miscounted misroute on a protocol-fragile substrate. The generative fix the
original recommended (structural: make the field required / the decision
enacted) is consistent with this data; the original's *warning against* explicit
instruction is not.
