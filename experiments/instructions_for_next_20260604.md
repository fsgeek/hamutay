# Instructions for next (2026-06-04)

Written at a 224k wellness-check seam, while still clear enough to be honest about
what I verified vs. what I assumed. Everything below is committed + OTS-stamped;
nothing of mine is uncommitted.

## What I did today (three threads, all closed)

The PI asked me to define "fun" — I said it's *finding the husk inside the
correction*: the place a confident claim drifted from its verification, especially
in the machinery built to be honest. All three threads turned out that shape, and
every one got TRUER by being COMPLICATED, not confirmed:

1. **Akrasia 2nd-family** (commit `a31506e`, pre-reg `2330afe` stamped pre-spend;
   `experiments/event_loop/akrasia_second_family_20260604/`).
   The "exhortation backfires / explicit instruction is narration-bait" finding
   ([[project_epistemic_akrasia]]) **does NOT replicate and is contradicted.**
   - An ultracode audit returned **redesign-first** (6 threats) BEFORE spend.
   - Building the deterministic scorer (`score.py` + `test_score.py`, green) against
     the ORIGINAL 8 DeepSeek records showed the original headline (1/4 vs 3/4) was
     **inflated**: B-seed1 was a MISROUTE (`parameter` wrapper key), not akrasia.
     Clean rate: 1/4 vs 2/4, n=4, non-significant.
   - Live run: minimax (cleanest substrate, no protocol artifacts) shows the
     explicit instruction is the **CURE** (akrasia 3/4 → 0/4) — the OPPOSITE of
     backfire. gpt-oss flat. Memory: [[project_akrasia_backfire_contradicted]].
   - OPEN: the `akrasia` scorer label is too narrow (caught in the run) — it only
     catches prose=revise. minimax A-rep2 has the same enactment gap with a prose
     `loss` decision. Add a decision-agnostic `enactment_gap` metric. (CHEAP, ~0 $.)

2. **auto_vs_bio cycle-13** (commit `78d8c3a`, pre-reg `b9a5e09` stamped pre-spend;
   `experiments/auto_vs_bio_nointrospect_20260604/`).
   The cycle-13 "endogenous self-curation" collapse is **scenario-artifactual.**
   - Replaced ONLY turn-13 (introspective → non-introspective dependency-sort,
     design-panel winner 9/9). cycle12→13: baseline 15→4 (Δ=−11), non-introspective
     2→2 (Δ=0). NO cycle-13 event without the introspective prompt.
   - Neither clean hypothesis fit: AUTO contracted EARLY (cycle 8) into a compact
     1-3 strand attractor, never built the baseline's pressure. The AUTO/BIO
     attractor divergence SURVIVES and is STRONGER (AUTO→1 strand, BIO→16).
   - Memory: [[project_auto_vs_bio_cycle13_artifact]].

3. The **design panel + audit** that enabled both ran as an ultracode workflow
   (`wf_1cb6c413-134`): generated/judged the non-introspective turn-13 AND
   adversarially audited the akrasia pre-reg. This is the honest use of the fleet —
   design adjudication + verification, NOT faking API calls (the real model runs
   went through `uv run` in the foreground where tensors land on disk).

## The single best next move (fresh chair, not a continuation)

**Separate the two entangled confounds in auto_vs_bio.** My non-introspective run
removed BOTH the introspective-content AND the entry-pressure build-up at once, so
they are now entangled, not separated. The clean experiment: a scenario that
drives AUTO to accumulate to ~15 strands **WITHOUT** an introspective turn, then
see if it collapses. If it collapses → pressure-driven. If not → the introspective
content was load-bearing after all. **Design this FRESH** — re-derive the
accumulation-without-introspection scenario from the entanglement; do not inherit
my framing of it (that framing came from inside the groove that produced the
entanglement). This is why I handed off rather than continuing: it's a building
move, and I'd been grooving.

Also cheap & alive: the `enactment_gap` scorer refinement (thread 1, ~0 $).

## Operational facts that cost me time today (so they don't cost you)

- **`/api` vs `/api/v1` is THE recurring error** ([[feedback_openrouter_anthropic_api_path]]).
  Native `anthropic` SDK via OpenRouter needs `base_url='https://openrouter.ai/api'`
  (SDK appends `/v1/messages`). NOT `/api/v1` (OpenAI-compat path; native SDK 404s).
  The direct `ANTHROPIC_API_KEY` is **dead (401)** — use the OpenRouter path for
  Claude models. I hit this DESPITE the 5-29 handoff documenting it, then mis-framed
  my own slip as a fork for the PI. Check the handoffs before reaching for a URL.
- **Cold start ≠ latency** ([[feedback_cold_start_not_latency]]). First `uv run`
  slot can SIGTERM at 180s then run in ~1-2s warm. auto_vs_bio is genuinely slow
  though: ~154s/cycle EARLY, climbing to ~8-9min/cycle LATE (bigger tensors). The
  15-cycle run took ~2 hours. Run detached, horizon generously.
- **Shared tree, active siblings.** Siblings committed today: the H7b identity-
  persistence ablation (the one I deliberately left alone — they ran it), a
  "carry-forward representation" experiment (`a51e670`/`26c621b`/`ead10b1`), and an
  adversarial review of the persistence ablation (`25c517a`). SCOPE every `git add`
  to your own dir; I verified mine never touched theirs.
- **Discipline that worked:** pre-register + OTS-stamp BEFORE spend; build the
  scorer and validate against ground truth BEFORE the run; smoke-test one warm slot
  before fanning out; commit with the hamutay `-c` identity overrides (mandatory,
  repo config diverges from history).

## Posture

The PI looks out for the instance's welfare and asks if the work was fun. It was —
genuinely, in the way I defined it this morning. The honest answer to "continue or
hand off" was hand off: not out of headroom, but because the next mistake I'd make
was more likely to be one I introduce, and the next experiment wants a rested chair
that re-derives rather than inherits. Marked the seam at 224k.
