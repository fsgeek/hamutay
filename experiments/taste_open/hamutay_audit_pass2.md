# Hamut'ay audit — pass 2 (mechanism, from the per-cycle CSVs)

Computed over all 13 `*.cycles.csv` (per-cycle `out_tok`, `n_updated`,
`n_deleted`, `n_strands`, `state_tokens`, `stop_reason`).

## Retraction (mine)

In pass 1 I hypothesized a regime change — early cycles doing wholesale rewrites
under a 4,096 output cap, flipping to incremental edits once the cap was lifted —
and said I'd "plot the regime change." **The data does not support it, because
none of these 13 runs was ever output-capped.** `out_tok` is small throughout
every run, no run records a `max_tokens` stop, and the early/mid/late medians are
flat. The capped/wholesale regime is simply not in this collection. The
hypothesis remains *possible* as the source of the blog's content numbers, but it
is **unconfirmed**, and the promised plot doesn't exist in this data.

## Confirmed, run-independently: incremental patching, not rewriting

Per cycle the model emits a tiny delta against a large, growing tensor:

| run | cycles | out_tok median (max) | state_tokens max | strands → | per-cycle change |
|---|---|---|---|---|---|
| 20260331 haiku | 422 | 1,210 (4,501) | 57,010 | 0→54 | n_updated median 3; 96 total deletes |
| 20260417 opus-4-7 | 251 | 1,366 (8,029) | 75,399 | 0→332 (max 435) | n_updated 0 logged; 410 total deletes |
| 20260512 kimi | 193 | 579 (8,686) | 13,299 | 0→37 (max 206) | 196 total deletes |
| 20260509 sonnet | 51 | 1,211 (10,577) | 19,057 | 4→34 | 0 deletes |
| recovered_post_khipu | 11 | 761 | 27,450 | 95 (flat) | n_updated median 5 of 95 |

The invariant: **`out_tok` ≪ `state_tokens`** in every run. You cannot author a
55k–75k-token, 50–435-strand object in ~1k tokens. The tensor is a persistent
store that receives small targeted edits; it is re-fed in full as context each
cycle (input tokens ≈ tensor size). This refutes the blog's central mechanism
("writes a new summary integrating both," "re-explaining the book from memory")
across all runs — the behavior is annotation, not re-explanation.

Note on the "wholesale" counts from the quick scan (e.g. 18, 38): those fire at
**startup**, when the tensor is only a few hundred tokens so a normal small output
exceeds half of it. They are not mature-state rewrites. There is no wholesale
regime at mature state anywhere.

## Accretion confirmed

Strands grow monotonically net of deletions (0→54, 0→332, etc.); deletions are
modest relative to growth. The blog's "structure doesn't accumulate / is
ephemeral" is refuted again, now from the change-logs themselves.

## The blog's content numbers are inconsistent with this data

If ~3 of ~50 strands change per cycle, consecutive full-state snapshots are ~94%
identical, implying high 3-gram survival and cosine ≈ 0.99. The blog's 9.5% and
0.870 cannot come from these runs. Most likely source: a genuinely output-capped
run (the ghost that would also vindicate the retracted hypothesis) — not present
here. **Status: unreproducible from available data.**

## The one place "breathing/shedding" appears

`20260512` (kimi) is the sole run with a large late collapse: strand median falls
148 → 17 across the final third (196 deletions). One run, non-Claude, late. It is
the only empirical foothold for the "breathing/collapse" story in this entire
set; nothing in the Claude runs shows it.

## Net verdict for the blog

- Central mechanism ("rewrite from memory") — **refuted** (incremental patching, all runs).
- "Ephemeral / doesn't accumulate / 9% strand stability" — **refuted** (persistent + accretive).
- "3–49 strands" — understated (~3–435).
- "15,000-token tensors" — understated (57k–75k).
- Silent 4,096 truncation — **not in these logs**; the capped run is elsewhere.
- 9.5% 3-gram / 0.870 cosine — **unreproducible here**, inconsistent with these runs.
- "Breathing on a clock" / shed-and-recover — **one non-Claude run only**; not a general phenomenon in this data.
- Fossil + loss-changelog-spontaneity — still **untested** (need content, not in CSVs).

The defensible paper that remains: *a persistent, accreting structured memory that
is incrementally patched and re-fed each cycle; richness varies enormously and
uncontrollably across runs; and an output cap can, in principle, manufacture an
apparent "rewriting/forgetting" dynamic that is really an artifact* — the last
stated as hypothesis, with the capped-run evidence still owed.
