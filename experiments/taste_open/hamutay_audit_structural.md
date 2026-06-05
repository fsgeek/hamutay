# Hamut'ay blog draft — structural audit (pass 1)

**Scope of this pass:** structural / name-level only — strand *names* (top-level
`state` keys), strand counts, `state_token_estimate`, and `usage.stop_reason`,
across all 13 `taste_open` run logs. This pass does **not** yet measure content
(the prose inside strands), so it cannot adjudicate the lexical-3-gram, embedding,
loss-paraphrase, or fossil claims — those need a content pass.

**One definitional caveat up front, because it could move everything:** I am
treating a "strand" as a top-level key of the `state` object. If the blog's
analysis counted something else as a strand (e.g. a sub-field, or entries in a
dedicated `strands` region), my numbers measure a different object and the
contradictions below soften. But the contradictions are large (≈99% vs 9%) and
identical across every run, and the blog separately reports a 9.5% *3-gram*
number — so the most likely explanation is that the blog's "strand stability: 9%"
is the **content** churn number wearing a **structural** label. Confirm what the
analysis script counted before publishing either way.

## The headline

The blog's Act-One mechanism is, at the structural level, **backwards.** It says
the structure is "almost entirely ephemeral," "doesn't accumulate," and that
"nearly every named thread is torn down and rebuilt each cycle (9% survive)." The
data says the opposite: **strand scaffolding is ~99% persistent cycle-to-cycle
and strongly accretive** — strand counts climb into the dozens and hundreds over a
run. What churns is the *content inside* the (stable, accumulating) strands. The
true shape is **"a stable, growing skeleton whose flesh is continuously
rewritten,"** not "everything is ephemeral."

That reframe is more defensible *and* still interesting — it's a cleaner statement
of the "semantic rewriter" idea — but it means the mechanism section has to be
rewritten, not polished.

## Claim-by-claim

| Blog claim | Blog number | Data (all runs) | Verdict |
|---|---|---|---|
| Strands torn down/rebuilt each cycle | "stability 9%" | name-survival **0.99–1.00** every run | **Refuted** (as structural). 9% is almost certainly content/3-gram, mislabeled. |
| Structure doesn't accumulate; ephemeral | — | strand counts grow to **54 / 206 / 435** within runs | **Refuted.** Structure accretes monotonically. |
| Curation richness stochastic | "3 to 49 strands" | across-run spread **≈3 to 435** | Qualitative claim (wide, uncontrolled) **holds, stronger**; the "3–49" range is understated ~9x. Also confounded: richness grows with run length, so it's not purely stochastic. |
| 4096 was a config artifact, not a real ceiling | "real tensors → 15,000" | max `state_token_estimate` **57,010 (haiku)**, **75,399 (opus)**; 192/422 and 191/251 cycles ≥15k | "No real ceiling" **supported**; but **15,000 is itself an undercount (~5x low)** — real tensors run to 57k–75k. |
| Silent truncation via the output cap | `max_tokens` stop | **zero** `max_tokens` in any run (all `tool_use`, a couple `end_turn`) | **Not present in these logs.** The truncation incident, if real, lives in an earlier run/config not in this set — unverifiable here. |
| Breathing: shed-and-regenerate, aperiodic | "CV=0.87, Poisson-like" | strand-level shed events ≈**0** (structure accretes, doesn't shed) | **Not reproducible structurally.** If breathing is real it is *intra-strand content* (e.g. a metacognition strand's contents dumped/regrown), invisible to this pass. Needs content pass keyed on that strand. |
| The fossil: false belief held ~170 cycles, caught only by external git check | — | not testable here; **candidate found**: `yanantin_correction` → `yanantin_correction_is_false` strands in the kimi run suggest a held-then-corrected belief | **Pending content pass.** |
| Loss-changelog never spontaneous; must be prescribed | — | `declared_loss`, `refrained_because`, `could_have_done` strands exist in the integrity-test run; spontaneity vs prescription not determinable from names | **Pending content pass** + the empty-schema run's system prompt. |

## Per-run reference (name-survival / strand range / max tokens / stop reasons)

- `20260331` haiku, 422 cyc — survival **0.993**, strands 0–54 (mean 30), max **57,010** tok (192≥15k), stop: tool_use×422
- `20260417` opus-4-7, 251 cyc — survival **0.995**, strands 0–**435** (mean 240), max **75,399** tok (191≥15k), stop: tool_use×250, end_turn×1
- `20260512` kimi, 193 cyc — survival **0.995**, strands 0–206 (mean 78), max 13,299 tok, stop: tool_use×193
- `20260509` sonnet, 51 cyc — survival 1.000, strands 4–34, max 19,057 tok (2≥15k)
- `20260528_001508` kimi (integrity test), 72 cyc — survival 1.000, strands 3–54 (mode 3), max 6,596 tok
- `recovered_post_khipu`, 11 snapshots of a run that reached **cycle 368** — 95 strands constant, 27,450 tok constant
- shorter runs (12–28 cyc): survival 1.000, strands ≤7, tokens ≤4.7k
- (none of the runs is 104 cycles; "104" is a checkpoint window inside a longer run, consistent with Tony's account)

## What survives the structural pass (the defensible spine)

- **Stable, accreting scaffolding + rewritten content** — the corrected mechanism.
- **No fixed token ceiling** — and the real magnitude (57k–75k) is a *better*
  story than the blog's 15k.
- **Huge, uncontrolled variance across runs** (3 to 435 strands) — the
  stochasticity point, stronger than stated, but disentangle it from run-length.
- The Act-Two *ethos* (longer runs / honest data kill overclaims) — which this
  audit just demonstrated again, at the blog's own expense.

## What the content pass must settle (next)

1. Lexical 3-gram survival (~9.5%?) and consecutive content-embedding cosine
   (0.870?) — computed **within** persistent strands, over the matching window.
2. Breathing: define shed on the metacognition strand's *content*, then test
   inter-event intervals for periodicity (a real test, not CV alone).
3. The fossil: track one strand's content across cycles; confirm the persistence
   duration and that the catch came from external reality.
4. Loss-changelog spontaneity: empty-schema run's system prompt vs whether a
   declared-loss strand appeared unprescribed.

**Needed to run it:** the `*.cycles.csv` files here (for windowing), plus a
content-extractor I'll write that pulls per-strand text per cycle for the one or
two runs the blog actually analyzed.
