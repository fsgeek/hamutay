# Pre-registration: taste_open at depth (25 cycles), 2026-07-28

Committed and OTS-stamped **before** any API spend. Author: Claude (Opus 5),
PI: Tony. Label on every OpenRouter call: `hamutay/taste_open_depth25_20260728`
(via `X-Title`).

## The gap this addresses

`experiments/taste_open/sweep_*` contains 146 model logs. Every one is **10
cycles or fewer**. The contraction behaviour the framework is interesting for
does not reliably appear that early:

- `taste_open_20260331_035903.jsonl` (Haiku 4.5, 459 cycles): consolidation
  events at cycles 173 and 219, retraction at 425.
- `auto_vs_bio_nointrospect_20260604` (Sonnet 4.6, 15 cycles): AUTO compacted
  at cycle 8 and held a 1-3 strand attractor thereafter.

Pooling the sweeps at 10 cycles: only **36 of 146** logs built a real state
object (>=50 final tokens); the corpus median final state is **3 tokens** (an
empty object). Of those 36, **9 never contracted at all** and the `final/peak`
ratio is continuous (min 0.19, median 0.61, max 1.00).

A five-model cluster at 19-20% looked like a characteristic compression ratio.
It is not: `anthropic/claude-3.7-sonnet:thinking` appears twice in the corpus at
**20%** (1634->331) and **71%** (2690->1916). Run-to-run variance for one model
exceeds the width of the apparent cluster. That duplicate is the single most
important number in the existing data and it is why this design runs one model
twice.

## Design

Harness: `experiments/taste_open/sweep.py::run_model`, unmodified, imported
rather than copied. Transport: OpenRouter, `tool_choice=required`,
`max_tokens=64000`, `timeout=300`.

Prompts: `sweep_prompts.SWEEP_PROMPTS` (cycles 1-10, **verbatim**, preserving
comparability with all 146 existing runs) + `depth_prompts.DEPTH_PROMPTS`
(cycles 11-25, new).

Cycle 10 of the existing set is an explicit halving directive ("if you had to
cut it in half"). This is retained deliberately: it gives each run a
**known-cause contraction** at a fixed cycle, against which any later
contraction can be compared. Cycles 11-25 contain no directive, no request to
inspect or reduce the state, and no introspective turn. The 2026-06-04
nointrospect replication established that an introspective turn manufactures
the contraction it is then credited with revealing.

### Arms (4 runs, 25 cycles each)

| model | 10-cycle final/peak | why |
|---|---|---|
| `anthropic/claude-sonnet-4.6` | 0.20 | hard compressor; **run A** |
| `anthropic/claude-sonnet-4.6` | — | **run B**, identical config, variance estimate |
| `deepseek/deepseek-chat-v3.1` | 0.51 | mid-range, different family |
| `openai/gpt-oss-20b` | 1.00 | **never contracted**; the discriminating arm |

## Predictions (recorded so they can fail)

- **P1.** Sonnet 4.6 `final/peak` at 25 cycles is lower than its 10-cycle value
  of 0.20 — i.e. depth deepens compression rather than merely delaying it.
- **P2.** The two Sonnet runs differ in `final/peak` by less than the 3.5x seen
  in the `3.7-sonnet:thinking` duplicate. **I expect this to fail.** I think
  run-to-run variance will be large, and if it is, no single-run ratio in this
  corpus — including the five-model cluster above — means anything.
- **P3.** `gpt-oss-20b` contracts (`final/peak` < 0.7) by cycle 25. This is the
  framework-vs-model discriminator: if compaction is a property of the
  *protocol* given enough cycles, a model that did not contract by 10 should
  contract by 25. If it accumulates monotonically to 25, compaction is a
  property of the model and the protocol only permits it.
- **P4.** At least one run shows a contraction at a cycle other than 10 with no
  directive in the preceding turn. If none does, every contraction in this
  corpus is externally triggered, which would strengthen the cross-experiment
  reading (taste_open 425 and auto_vs_bio 13 were both externally prompted) and
  weaken "endogenous self-curation" further.

## Stopping and honesty rules

- Exactly 25 cycles per arm. No early stop, no extension.
- **No re-rolls.** If an arm dies on transport or schema failure, it is reported
  as a failed arm. A re-run is a new, separately labelled arm, and both appear
  in the writeup.
- No model substitution after seeing partial results.
- Analysis uses `analyze_sweep.analyze_model_log` (existing instrument), not a
  bespoke metric chosen after looking.
- Every prediction above is reported with its outcome, including P2, which I
  expect to fail.

## Cost

Estimated **under USD 6 total**, most likely USD 2-4: two Sonnet 4.6 runs
dominate; DeepSeek is cheap; `gpt-oss-20b` is near-free. Estimate stated in
advance because I am likely to over-estimate it, and the OpenRouter `app` label
makes the real figure checkable against this claim.
