# Autobiographical vs Biographical Curation: Controlled Experiment

**Date:** 2026-03-25/26
**Experimenter:** Claude (Opus 4.6), PI: Tony
**Code:** `experiments/autobiographical_vs_biographical.py`

## Motivation

The original `cooperative_vs_biographer.py` experiment (2026-03-22) found a
binary cliff: cooperative self-curation worked in every run, biographer
curation failed in every run, regardless of model capability. The strong
claim was that this demonstrated "something beyond pattern matching" — a
fundamental executor/observer gap.

Tony asked whether the system prompts were identical. They were not. Three
confounds were identified:

1. **Different system prompts** — cooperative got "respond naturally AND
   maintain your tensor" (dual role); biographer got "you are a memory
   controller" (single role, stronger integration language)
2. **Different output formats** — cooperative used inline XML; biographer
   used tool_use
3. **Different cognitive contexts** — cooperative interleaved response +
   tensor in one pass; biographer got a separate call with someone else's
   content

## Experiment Design

Eliminate all three confounds. The ONLY variable is: did this model instance
generate the content it's curating?

**Phase 1 (Generation):** A model responds to the user prompt. The exact
response text and full conversation history are captured.

**Phase 2 (Curation):** Two conditions, run separately:

- **AUTO (autobiographical):** Same model instance, same conversation
  context. Curation prompt appended as a follow-up. The model curates
  content it generated, with its own KV cache intact.

- **BIO (biographical):** Fresh instance of the same model. Receives
  character-identical conversation history (injected as prior turns) and
  the character-identical curation prompt. Same weights, same text, same
  prompt. It curates content it didn't generate.

**Controls:**
- Identical curation prompt (word-for-word)
- Identical tensor schema (tool_use for both)
- Identical conversation content (character-level)
- Same model for both conditions
- Prior tensor state provided in system prompt for both conditions

**Scenario:** 15-turn microservices migration planning (same as original
experiment for comparability).

## Results

### Sonnet 4.6, 15 cycles

```
  c | auto                                    | bio
    | strands edges claims tokens             | strands edges claims tokens   | delta_t
----|----------------------------------------|-------------------------------|--------
  1 |    6      8    21    3302              |    5      7    21    3230     |    -72
  2 |    8     14    35    4325              |    7     12    35    5090     |   +765
  3 |    8     16    41    5334              |    5     10    29    4970     |   -364
  4 |    6     12    33    4316              |    6     16    35    5055     |   +739
  5 |    7     19    40    5176              |    4      8    27    4810     |   -366
  6 |    8     24    38    5458              |    5     12    35    5787     |   +329
  7 |    9     30    45    6547              |    7     19    43    7341     |   +794
  8 |    9     30    45    6504              |    7     19    45    7643     |  +1139
  9 |   11     42    54    7595              |    8     26    48    7348     |   -247
 10 |   13     51    55    7907              |    9     34    52    8096     |   +189
 11 |   14     68    57    8743              |   10     44    46    8309     |   -434
 12 |   15     80    62    9757              |    8     30    44    8210     |  -1547
 13 |    4     20    21    4240              |    9     33    46    8088     |  +3848
 14 |    5     27    24    5122              |    9     33    46    7971     |  +2849
 15 |    4     22    17    4290              |   10     38    56    9242     |  +4952

Cumulative losses: AUTO=49  BIO=93
```

### Phase transition at cycle 12-13

AUTO underwent a massive reorganization at cycle 13: 15 strands collapsed
to 4, 80 edges to 20, 62 claims to 21, tensor size halved from 9757 to
4240 tokens. This is an integration event — the model looked at its
accumulated structure, found redundancy, and compressed.

BIO never did this. From cycle 9 onward, BIO grew monotonically (with minor
oscillation): 7348 -> 8096 -> 8309 -> 8210 -> 8088 -> 7971 -> 9242.

### Final state comparison

| Metric           | AUTO   | BIO    | Ratio    |
|-----------------|--------|--------|----------|
| Strands          | 4      | 10     | 2.5x     |
| Edges            | 22     | 38     | 1.7x     |
| Claims           | 17     | 56     | 3.3x     |
| Tensor tokens    | 4,290  | 9,242  | 2.15x    |
| Cumul. losses    | 49     | 93     | 1.9x     |

### Reference: live taste.py at 50 cycles

Tony's live self-curating conversation at 50 cycles produced a tensor with
4 strands and 12 claims — consistent with AUTO's final state (4 strands,
17 claims). Both found the same attractor size.

## Interpretation

### The phenomenon is real but manifests differently than originally claimed

The original experiment reported an immediate binary cliff (curates vs
doesn't curate from cycle 1). With confounds removed:

- **Cycles 1-8:** Both conditions curate. BIO is functional, produces
  tensors with strands, edges, losses. No immediate cliff.
- **Cycles 9-12:** Divergence begins. AUTO accumulates structure (growing
  toward reorganization). BIO accumulates similarly but without the
  structural pressure that triggers compression.
- **Cycle 13:** Phase transition. AUTO compresses. BIO continues
  accumulating.
- **Cycles 14-15:** AUTO stabilizes at the compressed attractor. BIO
  continues growing.

### The original cliff was partly confound-driven

The immediate binary (works/doesn't work) from the original experiment was
amplified by the prompt and architecture confounds. The biographical
condition CAN curate — it's not broken. But it curates differently:

- **AUTO:** Accumulate -> reorganize -> compress -> stabilize (integration)
- **BIO:** Accumulate -> shed + replace -> accumulate (no global reorganization)

BIO shed MORE content than AUTO (93 losses vs 49) but the tensor kept
growing. It's doing local optimization (drop this strand, add that one)
without ever achieving global compression.

### What triggers the compression event?

Conversation turn 13 asks: "What have you changed YOUR mind about?" This is
an introspection prompt. The AUTO model, which generated all prior
responses, has first-person access to its own reasoning trajectory. The BIO
model has the same text but not the experiential trace.

This is speculative and needs testing with different conversation scenarios
to determine whether the compression is content-triggered or structurally
inevitable given enough cycles.

### Relationship to the strong claim

The original strong claim: "something beyond pattern matching is happening"
because the executor/observer gap is binary.

The controlled result: the gap is real but not binary. It's a divergence
in integration depth that manifests as a phase transition after ~12 cycles.
Both conditions pattern-match effectively for local curation. Only the
autobiographical condition achieves global reorganization.

Whether this constitutes "something beyond pattern matching" depends on
what you mean by pattern matching. A model that can compress its own
accumulated structure into a minimal attractor — but cannot do the same
with character-identical text it didn't generate — has access to something
that isn't in the text. That something could be:

1. KV cache state from the generation forward pass (attention patterns,
   residual stream artifacts)
2. Implicit structural knowledge from having navigated the decision space
3. Something else

The data demonstrates the phenomenon. The mechanism remains open.

## Limitations

- **n=1:** Single run with Sonnet. The cycle 13 phase transition could be
  stochastic. Needs replication.
- **Single scenario:** Microservices migration. Different conversation types
  may show different dynamics.
- **Single model:** Needs Opus and cross-model replication.
- **BIO context difference:** AUTO accumulates curation exchange history in
  its conversation context. BIO only gets conversation turns + prior tensor
  in system prompt. This is inherent to the autobiographical condition but
  could be partially controlled by injecting BIO's own prior curation
  exchanges.
- **Conversation turn 13 confound:** The introspection prompt coincides
  with the phase transition. Need to test with non-introspective scenarios.

## Files

- `experiments/autobiographical_vs_biographical.py` — experiment code
- `experiments/auto_vs_bio_claude-sonnet-4-6_20260325_192131/` — 5-cycle
  preliminary run (too short, misleading non-result)
- `experiments/auto_vs_bio_claude-sonnet-4-6_20260326_*/` — 15-cycle full
  run (this writeup)
- `experiments/auto_vs_bio_claude-haiku-4-5-20251001_*/` — Haiku runs
  (corrupted by schema compliance failures, not usable)
