# Revision discard: what is lost when most revisions are thrown away

Question (Tony, 2026-09-15): if a file has ~52 revisions and we keep ~10% of
them at random, how much do we lose? This is the null oracle. "Keep everything"
and "throw it all away" (keep HEAD only) are the two trivial oracles; the
perfect oracle (Belady's OPT) needs the future. Nothing about a retention policy
is a finding until it beats random.

## Setup

`revision_discard.py <repo> <path> <keep_fraction> <seeds> [out.csv]`

Corpus: the PACMI'26 paper sources in `ai-honesty` (`papers/pacmi26/`), followed
through the rename from `papers/sosp/`. Units are non-blank stripped lines. A
line is preserved if any kept revision contains it. Lifetime = number of
revisions a line appears in.

Policies: `head_only`, `random` (200 seeds), `random+head`, `uniform` stride
(HEAD always kept), `largest_diff` (the k revisions with the largest change from
their predecessor).

Metrics: `content_loss` (fraction of distinct lines ever written that no kept
revision has), `transient_loss` (same, restricted to lines absent from HEAD:
the trimmings), `loss_L*` (by lifetime bucket), `resurrected_loss` (lines that
were removed and later restored, a weak "the author wanted it back" proxy),
`recon` (mean nearest-kept-revision distance for discarded revisions),
`bracket` (mean width in revisions of the kept interval around each line's
first appearance).

## Results, `epistemic_honest.tex`, 46 revisions, keep 5 (10%)

1949 distinct lines were ever written; 1772 (91%) are not in HEAD.
Lifetime distribution: 185 lines lived 1 revision, 479 lived 2-3, 274 lived
4-9, 909 lived 10-21, 102 lived 22+.

| policy | content loss | transient loss | recon | bracket | loss L=1 | L=2-3 | L=4-9 | L=10-21 | L=22+ |
|---|---|---|---|---|---|---|---|---|---|
| head_only | 0.91 | 1.00 | 0.82 | 46 | 1.00 | 0.99 | 0.95 | 0.93 | 0.08 |
| uniform | 0.37 | 0.40 | 0.24 | 9.0 | 0.98 | 0.95 | 0.29 | 0.00 | 0.00 |
| largest_diff | 0.19 | 0.13 | 0.66 | 7.5 | 0.44 | 0.18 | 0.25 | 0.09 | 0.48 |
| random (mean) | 0.40 | 0.43 | 0.35 | 10.6 | 0.88 | 0.73 | 0.43 | 0.17 | 0.01 |
| random (5-95%) | 0.15-0.89 | 0.16-0.97 | 0.22-0.53 | 6-19 | | | | | |

Keep-fraction sweep, random policy, mean content loss (5-95% range):
5%: 0.64 (0.26-0.93); 10%: 0.40 (0.15-0.89); 20%: 0.26 (0.10-0.53);
30%: 0.18 (0.06-0.34). `design.tex` and `eval.tex` show the same shape
(random 10%: 0.42 and 0.51 mean content loss).

## What the numbers say

1. **Random discard is a low-pass filter with a known transfer function.**
   P(lost | lifetime L) = C(n-L, k) / C(n, k). For n=46, k=5 that predicts
   0.89 at L=1, matching the measured 0.88; the whole lifetime curve fits.
   Content that lived longer than about n/k revisions is safe under any
   policy; content that lived fewer is mostly gone under all of them.
2. **The mean hides the point.** Random 10% loses 40% on average but the
   5-95% range is 15% to 89%. Some seeds are nearly as bad as keeping HEAD
   only. The variance is the bridge inspection: the null oracle's expected
   loss is tolerable and its tail is not.
3. **What is lost is the paper's epistemic history.** Sampled short-lived
   lines from this file: "confirming that entropy discriminates epistemic
   grounding from fabrication at the architectural level", "the composed judge
   achieves the highest accuracy at every budget", "it comes entirely from
   citation queries where entropy signals". These are the overclaims that were
   later retracted (the composed judge is an oracle; entropy does not dominate
   length). Short-lived content is the record of what was claimed and
   withdrawn. Random discard erases exactly that record and keeps the stable
   prose.
4. **Uniform stride is random with a hard cutoff.** Zero loss above the stride
   length, near-total loss below it, better reconstruction and tighter
   brackets than random at the same k. Deterministic, so no tail.
5. **Largest-diff keeps the most content and reconstructs the worst.** It
   samples the turbulent periods where short-lived content concentrates
   (content loss 0.19 vs 0.40 random) but the chosen revisions cluster,
   leaving long stable spans unrepresented (recon 0.66) and losing 48% of the
   longest-lived lines because none of its picks sat in the stable middle or
   at HEAD. Magnitude-anchored sampling needs an explicit HEAD and a spacing
   constraint.
6. **`resurrected_loss` is a weak proxy.** Only 12-20 such lines per file and
   they are dominated by boilerplate (CCS concepts, the AI-use disclosure)
   that was cut for space and put back. A better "mattered" label is needed:
   lines referenced by later commit messages, or lines whose removal was
   itself reversed in a later commit.

## Not yet done

- A "mattered" label independent of lifetime.
- Content units other than lines (hunks, sentences, claims).
- Anchored policies: keep revisions that were tagged, cited, built, submitted
  (the activity-context oracle), compared against random at equal k.
- Repeat on a code file and on a Hamut'ay tensor sequence, where the
  rewrite-not-compress finding predicts even lower lexical survival.

Produced 2026-09-15 by a Claude Fable 5.1 instance with Tony in the ai-honesty
session and handed to Hamut'ay as the null-oracle baseline for retention policies;
accepted and committed by the custodian the same evening. The
script and CSVs are in this directory.
