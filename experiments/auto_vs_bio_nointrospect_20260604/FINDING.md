# auto_vs_bio: the cycle-13 contraction is scenario-artifactual

Analysis date: 2026-06-04. Pre-registration: `PRE_REGISTRATION.md`, committed +
OTS-stamped before the run (commit `b9a5e09`). Run: `run_sonnet/log.jsonl`,
15 cycles, both arms, `anthropic/claude-sonnet-4.6` via OpenRouter native path.

## What was tested

The 2026-03-25/26 auto_vs_bio run found the AUTO arm collapsed discontinuously at
**cycle 13** (strands 15 → 4, tokens ~9757 → 4240) while BIO kept accumulating;
this was glossed as "endogenous self-curation." The 2026-06-03 fork flagged two
confounds: turn 13 is an *introspective* prompt ("what have YOU changed your mind
about?"), and AUTO entered cycle 13 at ~2× BIO's structural pressure.

This run replaces ONLY turn 13 with a non-introspective turn of comparable
integration load (a successor-handoff dependency topological-sort; design-panel
winner, 9/9). Everything else is byte-identical to the original apparatus.

## Result: no cycle-13 contraction; AND a different attractor entirely

AUTO strand trajectory, this run (non-introspective) vs the baseline
(introspective turn-13):

```
cyc    1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
NI    7  7  7  7  7  7  8  2  3  4  3  2  2  3  1     <- non-introspective AUTO
base  6  8  8  6  7  8  9  9 11 13 14 15  4  5  4     <- baseline AUTO
```

**The cycle-12→13 discontinuity:**

| | strands 12→13 | tokens 12→13 |
|---|---|---|
| Baseline (introspective) | 15 → 4 (Δ = **−11**) | ~9757 → 4240 (**halved**) |
| Non-introspective | 2 → 2 (Δ = **0**) | 4691 → 4749 (**flat**) |

There is **no cycle-13 event** without the introspective turn. The dramatic
collapse the original finding was named for does not occur.

**But contraction still happened — earlier and from a lower height.** The
non-introspective AUTO contracted sharply at **cycle 8** (8 → 2 strands, tokens
8316 → 5102) and then lived in a compact 1–3 strand attractor for the entire back
half. It never accumulated the baseline's 15-strand structure, so there was
nothing to collapse at 13.

## Which hypothesis won: neither cleanly — the honest answer

- **H-content** (no contraction without the introspective turn) is supported
  *for the cycle-13 event specifically*: Δ=0 at 12→13, no token halving. The
  original "endogenous self-curation **at cycle 13**" reading is
  **scenario-artifactual** — the cycle-13 *timing* was set by the introspective
  scenario's accumulate-then-collapse curve, not by anything intrinsic to
  autobiographical curation.
- **H-structural** (AUTO still contracts at ~13 after building pressure) is
  **falsified**: AUTO never built the pressure and contracted at cycle 8 instead.
- The phenomenon that survives both: **AUTO compresses to a compact attractor;
  BIO accumulates.** This run is the CLEANEST instance of that divergence in the
  corpus — non-introspective AUTO ended at **1 strand**, non-introspective BIO
  climbed monotonically to **16** (baseline BIO: 16 by cycle 15 too). The
  AUTO/BIO gap is real and large; only the *cycle-13 choreography* was the
  introspective prompt's fingerprint.

## Interpretation

The original write-up's own caution ("needs testing with different conversation
scenarios to determine whether the compression is content-triggered or
structurally inevitable") is now answered: the *specific cycle-13 compression
event* was content-triggered. Two scenarios select two regimes:

- **Introspective scenario:** accumulate (→15) → collapse at the introspective
  turn (→4) → stabilize. The compression is *deferred* until the prompt that asks
  for retrospective integration.
- **Dependency-sort scenario:** compact-organize early (→2 by cycle 8) → hold.
  A forward synthesis demand invites compression from the start, with no late
  dramatic event.

So "AUTO self-curates" is true at the level of *attractor* (compact vs
accumulating) but the headline cycle-13 *transition* was an artifact of which
question the conversation asked, and when.

## Limitations

- **n=1 per scenario.** This is a direct A/B replication of a single large
  discontinuity, not a rate estimate. No significance language. The Δ=−11 vs Δ=0
  contrast is unambiguous at n=1 only because the baseline effect was so large;
  the *early-contraction* timing (cycle 8) could be stochastic and needs a second
  run to confirm it is scenario-driven rather than seed-driven.
- **Entry-pressure confound is now moot for the cycle-13 question** (AUTO never
  built pressure) but means the two confounds the fork raised are entangled: the
  non-introspective scenario removed BOTH the introspective content AND the
  pressure build-up. A scenario that drives accumulation to ~15 *without* an
  introspective turn would separate them; this one does not.
- **Model/transport nuance:** baseline ran direct `claude-sonnet-4-6`; this ran
  `anthropic/claude-sonnet-4.6` via OpenRouter (provider routed as Google). Same
  version family, native tool_use preserved, but not the identical endpoint.
- **Single replacement turn.** One non-introspective turn-13; a different
  non-introspective turn might accumulate differently.

## Bottom line

The auto_vs_bio cycle-13 contraction — the centerpiece "endogenous self-curation"
event — **does not reproduce** when the introspective turn-13 is replaced. It was
scenario-artifactual: the *timing* was the introspective prompt's fingerprint.
The durable phenomenon (AUTO compresses to a compact attractor, BIO accumulates)
is real and was if anything *stronger* here (1 vs 16 strands), but it manifests
as early compact-organization, not a dramatic late collapse, when the
conversation does not ask the model to introspect.
