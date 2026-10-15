# TurboQuant R1: prediction before the registered run

Date: 2026-10-13. Written by the hamutay custodian (Claude Opus 5.5) before
Task 9's registered command was run, and committed so its OpenTimestamps stamp
predates the evidence. The plan and spec were designed with a Codex instance
as researcher; this note adds a prediction, it changes no gate, tolerance,
sample count or code.

## What the prediction rests on

The only bias-equivalence evidence before this run is one development record
(`docs/superpowers/validation/2026-09-18-turboquant-clean-collective/corrected-1-replay-artifacts/development/cli_no_author_1400cef5cf/qualification.json`):
8,000 samples, bit widths 1 and 2 only, author differential not run.

| bits | mean | 98.75% interval | bound (±0.02·RMSE) | 95% interval |
|---|---|---|---|---|
| 1 | 0.00021 | [-0.00376, 0.00335] | ±0.00219 | [-0.00229, 0.00249] |
| 2 | 0.00131 | [0.00017, 0.00269] | ±0.00132 | [0.00056, 0.00211] |

At 1 bit the failure is width: the interval is wider than the region, with a
mean near zero. At one million samples the half-width shrinks by about
sqrt(8000/1e6) ≈ 0.09, to roughly ±0.0003. At 2 bits the mean sits at the
bound and the ordinary 95% interval excludes zero; 9 of 10 block means are
positive. The row-orthogonalized sensitivity form shows no such shift
(mean -0.00032, 95% [-0.00098, 0.00060]).

## Predictions

1. Determinism, scalar distortion (analytic and published scale), and QJL
   distortion scale pass.
2. Author-code differential passes (it passed on the 4090 on 09-18).
3. Bias equivalence passes at 1 bit.
4. **Bias equivalence at 2 bits: I expect it to fail** (about 60%). If the
   8,000-sample shift is real, a mean near 0.0013 against a bound near 0.0013
   with a ±0.0003 interval will not fit inside the region.
5. 3 and 4 bits: no prior evidence; I expect them to pass, with low confidence.
6. Overall: more likely `No qualified experiment` than a pass.

A failure is a blocked experiment, not a negative TurboQuant result (spec,
"Algorithm Qualification Gate"). If gate 3 fails at 2 bits, the open question
is whether the shift is in this implementation or in the paper-literal iid
estimator itself; the run alone cannot say which.
