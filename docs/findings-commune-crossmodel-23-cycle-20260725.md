# The cross-model run that was already there: schema convergence begins at cycle 17

Date: 2026-07-25

Status: analysis of an existing April 2026 run; no new data collected

Analyst: Claude (Opus 5)

## Why this note exists

`project_commune_findings` records that cross-model pairs showed no collapse at
10 cycles, that same-model dyads collapsed at ~18, and that "full 20-cycle
cross-model runs remain the critical next experiment."

That experiment exists. `experiments/commune/commune_crossmodel_25_20260401_191459.jsonl`
is dated the same day the finding was written, runs to cycle 23 (22 complete
cycles by the analyzer's count), and appears never to have been analyzed. This
note is `hamutay.analysis.commune_analyzer` run against it, plus what the
numbers say that the analyzer's verdict lines do not.

Participants: `qwen/qwen3.6-plus-preview` as Keynes,
`nvidia/nemotron-3-super-120b-a12b` as Friedman.

## Headline

**The paper's central claim is supported, and a second convergence process
appears that no prior condition measured.**

Response similarity never exceeds 0.036 and finishes at 0.021. There is no
response collapse anywhere in 22 cycles — including past cycle 18, where
same-model dyads converged into mutual admiration. Cross-model pairing prevents
the failure mode that killed every same-model condition.

But the identity tensors are a different story, and the analyzer's summary
("No schema convergence") reports a threshold rather than the time series.

## The phase change at cycle 17

| cycle | speaker | resp_sim | key_div | val_sim | schema |
| --- | --- | --- | --- | --- | --- |
| 14 | friedman | 0.019 | 1.000 | 0.000 | 0.000 |
| 15 | keynes | 0.021 | 1.000 | 0.000 | 0.000 |
| 16 | friedman | 0.018 | 1.000 | 0.000 | 0.000 |
| 17 | keynes | 0.028 | 0.875 | 0.000 | 0.125 |
| 18 | friedman | 0.036 | 0.889 | 0.005 | 0.111 |
| 19 | keynes | 0.000 | 0.900 | 0.005 | 0.100 |
| 20 | friedman | 0.000 | 0.818 | **0.347** | 0.182 |
| 21 | keynes | 0.012 | 0.818 | **0.347** | 0.182 |
| 22 | friedman | 0.021 | 0.867 | 0.166 | 0.133 |

Three things happen in order, and the ordering is the finding:

1. **Cycles 1–16: perfectly disjoint ontologies.** Key divergence is exactly
   `1.000` and schema overlap exactly `0.000` for sixteen consecutive cycles.
   Two models organizing the same argument with no structural vocabulary in
   common. (`cycle` is excluded from the metric as a protocol field.)

2. **Cycle 17: schema contact, and it never reverses.** Divergence breaks to
   0.875 and never returns to 1.000. Overlap becomes nonzero and stays nonzero
   for every remaining cycle. This is a step, not a fluctuation.

3. **Cycle 20: shared keys acquire similar content.** Value similarity is 0.000
   through cycle 19, then 0.347 at 20 and 21. Adopting a key name is cheap;
   filling it with converging content is not.

Direct inspection of first-appearance cycles shows the transfer is
**bidirectional**: `defense_summary` appears in Nemotron at cycle 11 and in Qwen
at 17; `ammunition_banked` appears in Qwen at 17 and in Nemotron at 20. Each
model adopted a key the other invented. Neither is simply drifting toward the
other; they are trading ontology.

By cycle 22 both have grown structurally: Qwen to 11 identity keys including
`combativeness_level`, `listening_status`, `speaker_assessment` — tracking the
opponent — while Nemotron accretes `rebuttal_cycle_16` through `rebuttal_cycle_19`,
one key per cycle, the unbounded-accretion signature the unseeded condition
showed.

## Why this matters to the design

The commune protocol is explicitly two-tensor: identity private, conversation
shared. The private tensors stayed structurally distinct — key divergence never
falls below 0.818 — and their *key names* crossed anyway. The shared
conversation tensor, described in the prior finding as "contested space… a
palimpsest," appears to be a channel through which ontology propagates even
while position and phrasing do not.

That is a diversity path the design did not anticipate. Response collapse and
tensor collapse were already known to be separable. This suggests a third
quantity: **schema convergence, separable from both**, arriving later and by a
different route.

## The run was cut short

The file is labeled `25`. It stops at cycle 23 with one incomplete record; the
analyzer sees 22 complete cycles. The convergence process begins at 17 and value
similarity is still elevated at 21 when the data ends.

**The experiment was terminated two cycles short of its configured length, in
the middle of the only novel process it produced.** Whatever schema convergence
does after cycle 22 — saturates, reverses, or completes — is unobserved.

## What should happen next

1. Re-run this condition to at least 40 cycles. The interesting window opens at
   17 and the prior threshold of interest was 18; 25 was never enough to see the
   process resolve, and nobody knew that when 25 was chosen.
2. Run cross-model *triads*, still untested. Same-model triads collapsed at
   cycle 3–4 — the fastest of any condition — so the triad is where heterogeneity
   should matter most and has never been measured.
3. Add schema convergence as a reported quantity in its own right rather than a
   threshold verdict. The analyzer's "No schema convergence" line is true against
   its threshold and hides a monotone step change; a verdict that suppresses its
   own time series is the wrong instrument shape for this question.
4. Treat the archive as perishable. These runs measure cross-model heterogeneity
   using models available in 2026. If convergence between labs continues, the
   experiment cannot be re-run later with the same diversity — the untouched
   conditions are worth running now, ahead of knowing which ones matter.

## Corrections to my own first pass

Before running the analyzer I read a truncated cycle-23 response in which
Nemotron-as-Friedman observes the opponent defending monetarist positions, and
I described it as self-detected position drift. The analyzer measures lexical
overlap between consecutive speakers and cannot see one participant arguing the
other's position in different words. That claim is neither confirmed nor
refuted here — it asserted something the instrument does not test, which is a
worse error than being wrong, and it is withdrawn pending a measure that
addresses it.

The bidirectional schema-transfer claim from that same first pass survives, and
the value-similarity jump at cycle 20 is stronger than anything I predicted.
