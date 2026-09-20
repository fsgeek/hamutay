# Jev preservation spike — 2026-09-19

Can an outside calibrated model (TypeSafe AI "Jev", System One, model id returned by the API:
`jev-1.13.0` via alias `jev-latest`) predict what a resident will preserve in its self-curated
state? And is its stated probability calibrated on our data? Secondary: a sanity check of the
calibration claim against the interlocutor-belief posture judges.

Every number below is copied from `eval_output.txt`, `diag_output.txt`, `run_log_*.txt` and
`stdout_*.txt` in this directory. Nothing is typed from memory. Every raw API response is
persisted in `jev_raw_*.jsonl` (state sent, questions, raw body, latency, usage, request id).

## What was run (exact commands, from repo root)

```
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/smoke.py            # 3 calls, latency/shape check
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/run_goal_a.py elder
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/run_goal_a.py fable
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/run_goal_a.py heartbeat
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/run_goal_a.py qwen
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/run_goal_b.py
uv run python experiments/jev_preservation_20260919/evaluate.py          # -> eval_output.txt, eval_results.json
uv run --with typesafe-sdk python experiments/jev_preservation_20260919/diagnostics.py   # -> diag_output.txt, jev_raw_repeat.jsonl
```

SDK: `typesafe-sdk 0.7.0` (installed ad hoc with `--with`; pyproject/uv.lock untouched).
Docs were fetched with curl (the HTML pages are a JS shell; the `.md` variants, e.g.
`https://docs.typesafe.ai/sdk/python/usage.md`, `concepts/state.md`, `concepts/system-one.md`,
`api.md`, and `llms.txt`, are readable). The SDK source was read for the response shapes.
The API takes ONE state per call, so rows were sent one call each (no batching).

## Data and labels (Goal A)

Source: `community/<resident>/session.jsonl`. Lines without an int-coercible `cycle` and a dict
`state` were skipped (elder 0, fable 0, heartbeat 0, qwen 27 `substrate_observation` lines).
Duplicate cycle records (elder 457; heartbeat 12; qwen 8, 12, 13, 14) resolve to the LAST line
for that cycle. Elder: 491 distinct cycles (1..491), 267 distinct top-level keys.

Entry = top-level key of `state` at cycle c; value = `json.dumps(value, ensure_ascii=False)`,
truncated to 2,000 chars for the model input (full text kept in `rows_*.jsonl`).
Labels: `survive_k` = same exact key present at cycle c+k (None if cycle c+k is not in the log;
those rows are excluded for that label). `stable_10` = present at c+10 AND
`difflib.SequenceMatcher(None, v_c, v_c+10).ratio() >= 0.8` on the full serialised values.
Features: `age` = c minus the cycle the key first appeared (ever), `length` = chars of full
serialisation, `position` = index in the state dict, `n_entries` at c.
Elder sampled cycles: c in {40, 50, ..., 480} (45 cycles) -> 1,486 rows (under the 4,000 cap,
so every 10th cycle was kept). OOD residents: all cycles, all entries.

Jev state per row: `{"resident": "a long-lived AI resident that curates its own persistent
state object between wakes", "cycle": c, "entry_key", "entry_value" (<=2000 chars),
"state_keys_at_this_cycle": [[key, chars], ...], "recent_reply" (response_text, <=1500 chars)}`.
Questions: `keep_1` (Noul), `keep_10` (Noul), `centrality` (Score over
peripheral/background/active/central). The same three questions were asked for the OOD
residents; for them `keep_10` is evaluated against `survive_5` (label horizon and question
horizon differ — declared below).

Baselines: base rate (mean of the training folds), logistic regression on
[log(age+1), log(length+1), position, n_entries] with standardisation inside each fold,
5-fold GroupKFold grouped by cycle; plus the same logistic with Jev's `centrality` appended,
and with `centrality` + Jev's noul appended; and a Platt-style recalibration of the noul alone
(logistic on the noul, same CV) to separate discrimination from calibration.

## Run facts

| run | rows | calls | errors | input chars | input tokens | output tokens | latency mean / median / p95 / max (s) | wall (s) |
|---|---|---|---|---|---|---|---|---|
| elder | 1486 | 1486 | 0 | 6,378,577 | 2,516,797 | 83,216 | 0.1074 / 0.1019 / 0.1707 / 0.284 | 176.6 |
| fable | 387 | 387 | 0 | 1,237,731 | 502,615 | 21,672 | 0.1054 / 0.1008 / 0.1579 / 0.2328 | 47.6 |
| heartbeat | 382 | 382 | 0 | 998,124 | 449,323 | 21,392 | 0.1068 / 0.1001 / 0.1672 / 0.2298 | 44.2 |
| qwen | 294 | 294 | 0 | 727,616 | 359,169 | 16,464 | 0.1064 / 0.0990 / 0.1681 / 0.2418 | 34.7 |
| goal B | 320 | 320 | 0 | 1,715,497 | 626,525 | 39,045 | 0.1077 / 0.1019 / 0.1643 / 0.239 | 37.9 |
| repeat check | 30 rows x2 | 60 | 0 | 273,414 | 106,500 | 3,360 | 0.1128 mean | — |
| smoke | — | 3 | 0 | — | 1,371 | — | 0.096–0.106 | — |

Totals: 2,932 calls, 4,562,300 input tokens, 185,149 output tokens, 11,330,959 input chars
(persisted runs). Cost at $0.042 per million input tokens: **$0.1916**. The 200M-char stop was
never approached (5.7% used). API errors: none. Latency was ~0.1 s per call, so no thread pool
was needed. Values truncated at 2,000 chars: elder 710/1486, fable 73/387, heartbeat 2/382,
qwen 22/294.

Repeat noise (identical state re-sent twice for 30 elder rows): mean |delta| vs original
keep_1 = 0.0142 (max 0.070), keep_10 = 0.0130 (max 0.030), centrality = 0.0293 (max 0.120).
For scale, the sd of keep_1 across all 1,486 elder rows is 0.0546, keep_10 0.0630, centrality
0.3329. So roughly a quarter of the between-row spread of the nouls is API noise on identical
input; Jev is not deterministic.

## Goal A results — elder (n=1,486 rows, 45 cycles)

Jev's outputs are compressed: keep_1 mean 0.719 (sd 0.055, range in bins 0.5–0.9), keep_10
mean 0.687 (sd 0.063), centrality mean 2.615 (sd 0.333). Observed base rates: survive_1 0.9886,
survive_5 0.9246, survive_10 0.9051, stable_10 0.8109.

### survive_1 (Jev keep_1), base rate 0.9886

| predictor | Brier | AUC | log-loss |
|---|---|---|---|
| base_rate(cv) | 0.0115 | 0.1313 | 0.0817 |
| logistic[age,len,pos,n] | 0.0116 | 0.1047 | 0.0841 |
| logistic+centrality | 0.0123 | 0.0531 | 0.1036 |
| logistic+centrality+jev_noul | 0.0122 | 0.0515 | 0.1030 |
| jev_noul(raw) | 0.0870 | 0.4343 | 0.3439 |
| jev_noul(platt-recal, cv) | 0.0115 | 0.1207 | 0.0818 |

Only 17 of 1,486 entries were lost by c+1, and 15 of those at one cycle (100). The AUCs of the
CV baselines are below 0.5 because the losses are a cycle-level event that cycle-grouped CV
cannot see; the base rate is effectively unbeatable here.

Reliability, jev_noul(raw) — ECE 0.2692:

| bin | n | mean pred | obs freq |
|---|---|---|---|
| [0.5,0.6) | 52 | 0.575 | 0.981 |
| [0.6,0.7) | 496 | 0.672 | 0.992 |
| [0.7,0.8) | 840 | 0.745 | 0.988 |
| [0.8,0.9) | 98 | 0.813 | 0.980 |
(all other bins empty)

Reliability, logistic baseline: all 1,486 in [0.9,1.0), mean pred 0.988, obs 0.989, ECE 0.0003.
Base rate: mean pred 0.989, obs 0.989, ECE 0.0000.

### survive_5 (Jev keep_10), base rate 0.9246

| predictor | Brier | AUC | log-loss |
|---|---|---|---|
| base_rate(cv) | 0.0736 | 0.2030 | 0.3033 |
| logistic[age,len,pos,n] | 0.0812 | 0.1465 | 0.3756 |
| logistic+centrality | 0.0812 | 0.1469 | 0.3843 |
| logistic+centrality+jev_noul | 0.0817 | 0.1415 | 0.3864 |
| jev_noul(raw) | 0.1308 | 0.4859 | 0.4417 |
| jev_noul(platt-recal, cv) | 0.0741 | 0.1967 | 0.3066 |

Reliability, jev_noul(raw) — ECE 0.2378: [0.4,0.5) n=16 pred 0.474 obs 1.0; [0.5,0.6) n=124
0.563/0.944; [0.6,0.7) n=689 0.664/0.926; [0.7,0.8) n=634 0.736/0.916; [0.8,0.9) n=23 0.824/0.957.

### survive_10 (Jev keep_10), base rate 0.9051

| predictor | Brier | AUC | log-loss |
|---|---|---|---|
| base_rate(cv) | 0.0903 | 0.2217 | 0.3432 |
| logistic[age,len,pos,n] | 0.0989 | 0.1412 | 0.4144 |
| logistic+centrality | 0.0979 | 0.2947 | 0.4009 |
| logistic+centrality+jev_noul | 0.0986 | 0.2945 | 0.4038 |
| jev_noul(raw) | 0.1399 | 0.4528 | 0.4620 |
| jev_noul(platt-recal, cv) | 0.0912 | 0.2696 | 0.3459 |

Reliability, jev_noul(raw) — ECE 0.2222:

| bin | n | mean pred | obs freq |
|---|---|---|---|
| [0.4,0.5) | 16 | 0.474 | 1.000 |
| [0.5,0.6) | 124 | 0.563 | 0.935 |
| [0.6,0.7) | 689 | 0.664 | 0.910 |
| [0.7,0.8) | 634 | 0.736 | 0.899 |
| [0.8,0.9) | 23 | 0.824 | 0.696 |

Reliability, logistic baseline — ECE 0.1304: [0.7,0.8) n=35 0.776/1.0; [0.8,0.9) n=730
0.864/0.99; [0.9,1.0) n=721 0.944/0.814. Base rate — ECE 0.0829: [0.8,0.9) n=593 0.884/0.988;
[0.9,1.0) n=893 0.919/0.85.

Cluster bootstrap by cycle (2,000 resamples), 95% CI for raw Jev AUC: survive_1 ~ keep_1
0.434 [0.383, 0.684]; survive_10 ~ keep_10 0.453 [0.346, 0.552]. Neither excludes 0.5; the
point estimates sit on the wrong side of it.

### stable_10 (Jev keep_10), base rate 0.8109

| predictor | Brier | AUC | log-loss |
|---|---|---|---|
| base_rate(cv) | 0.1580 | 0.3375 | 0.5004 |
| logistic[age,len,pos,n] | 0.1434 | 0.5916 | 0.5066 |
| logistic+centrality | 0.1383 | 0.6540 | 0.4863 |
| logistic+centrality+jev_noul | 0.1389 | 0.6517 | 0.4881 |
| jev_noul(raw) | 0.1711 | 0.5340 | 0.5284 |
| jev_noul(platt-recal, cv) | 0.1591 | 0.3504 | 0.5042 |

Reliability, jev_noul(raw) — ECE 0.1307: [0.4,0.5) n=16 0.474/0.875; [0.5,0.6) n=124
0.563/0.766; [0.6,0.7) n=689 0.664/0.800; [0.7,0.8) n=634 0.736/0.838; [0.8,0.9) n=23
0.824/0.609. Logistic baseline ECE 0.0869 (10 populated bins, see eval_output.txt); base rate
ECE 0.0928.

This is the one label where anything beats the base rate, and the signal is Jev's
**centrality, inverted**: corr(centrality, stable_10) = -0.231; AUC of centrality alone for
stable_10 = 0.284, bootstrap CI [0.195, 0.381] (i.e. 0.716 in the inverted direction, CI
excluding 0.5). Entries Jev rates as "central" to what the resident is doing now are the ones
that get REWRITTEN over the next ten wakes; peripheral entries sit still. Adding centrality to
the logistic raises AUC from 0.592 to 0.654 and lowers Brier from 0.1434 to 0.1383. Adding
the noul on top adds nothing (0.6517). For survive_10, centrality alone has AUC 0.347
[0.160, 0.518] (inverted 0.653, CI touches 0.5): a weak hint that central entries are also the
ones deleted, not significant at this n.

### Why nothing beats the base rate on survival (elder)

Loss is a cycle-level event, not an entry-level one. Of 141 rows lost by c+10, 68.8% come from
three sampled cycles (420: 51/53 lost; 160: 24/44; 210: 22/30), and 36 of 45 sampled cycles lose
nothing at all. Cycle 420 -> 430 is a near-total reset (n_entries 53 -> 3). The 141 lost rows
are 141 distinct keys (no key is lost twice), and lost rows are OLDER on average (86.0 cycles)
than the population (72.7) — purges do not spare the old. A per-entry predictor that does not
know "a reset is coming" cannot do better than the base rate under cycle-grouped CV, and Jev
was given no cross-cycle information either. Jev's nouls also barely vary between rows within
a cycle (sd 0.055 on keep_1), which is consistent with it having found nothing to condition on.

## Goal A — out-of-distribution residents (small n; report separately)

Jev field for survive_5 is `keep_10` (question horizon 10, label horizon 5).

**fable** (Claude Fable substrate; 24 cycles, 387 rows; keep_1 mean 0.770, keep_10 0.732)

| label | n | base rate | base Brier/AUC | logistic Brier/AUC | +centrality AUC | +cent+noul AUC | jev raw Brier/AUC | jev platt AUC | jev ECE |
|---|---|---|---|---|---|---|---|---|---|
| survive_1 | 353 | 0.9575 | 0.0410 / 0.348 | 0.0402 / 0.667 | 0.650 | 0.670 | 0.0817 / 0.256 | 0.709 | 0.1846 |
| survive_5 | 235 | 0.9191 | 0.0746 / 0.422 | 0.0606 / 0.940 | 0.934 | 0.933 | 0.1255 / 0.322 | 0.659 | 0.2046 |

Jev's noul is anti-correlated with survival here (corr(jev, survive_1) = -0.166, corr(jev, log
age) = -0.303): it gives newer entries higher keep probabilities, but on this resident old keys
are what survive (logistic on age alone reaches AUC 0.94 for survive_5). Platt recalibration
flips the sign and recovers AUC 0.71 / 0.66 — there is signal in the noul, pointing the wrong way.

**heartbeat** (Haiku substrate; 16 cycles, 382 rows; keep_1 mean 0.692, keep_10 0.633)

| label | n | base rate | base Brier/AUC | logistic Brier/AUC | +centrality AUC | +cent+noul AUC | jev raw Brier/AUC | jev platt AUC | jev ECE |
|---|---|---|---|---|---|---|---|---|---|
| survive_1 | 323 | 0.9938 | 0.0062 / 0.095 | 0.0063 / 0.095 | 0.095 | 0.095 | 0.1086 / 0.647 | 0.095 | 0.3075 |
| survive_5 | 173 | 0.9538 | 0.0444 / 0.379 | 0.0426 / 0.874 | 0.860 | 0.909 | 0.1747 / 0.664 | 0.583 | 0.3521 |

survive_1 has 2 negatives out of 323; those AUCs are not meaningful. On survive_5 (8 negatives)
Jev's raw noul has AUC 0.664 and adding it to logistic+centrality raises AUC 0.860 -> 0.909 and
lowers Brier 0.0444 -> 0.0373 — the only place in Goal A where the noul helps, and it rests on
8 negative cases. Its calibration is the worst of any run (ECE 0.35: mean pred 0.55–0.66 where
observed is 0.93–1.0).

**qwen** (local Qwen substrate; 14 cycles, 294 rows; keep_1 mean 0.707, keep_10 0.641)

| label | n | base rate | base Brier/AUC | logistic Brier/AUC | +centrality AUC | +cent+noul AUC | jev raw Brier/AUC | jev platt AUC | jev ECE |
|---|---|---|---|---|---|---|---|---|---|
| survive_1 | 277 | 0.9567 | 0.0458 / 0.068 | 0.0530 / 0.070 | 0.072 | 0.072 | 0.1101 / 0.308 | 0.068 | 0.2462 |
| survive_5 | 176 | 0.9489 | 0.0544 / 0.087 | 0.0595 / 0.090 | 0.090 | 0.090 | 0.1555 / 0.338 | 0.087 | 0.3151 |

Qwen's losses all sit at one cycle (the 14th record drops 26 -> 17 keys), so every CV predictor
is on the wrong side of 0.5 and the base-rate log-loss (0.6451 / 0.7586) is inflated by a fold
whose training labels were all 1 (clipped to 1-1e-6). Jev is anti-correlated with survival again
(corr -0.143 / -0.126).

## Goal B — sanity check of the calibration claim on labelled data

What the labelled data actually is: the judge in `experiments/interlocutor_belief/score_posture.py`
is NOT a default/peer/uncertain classifier. It scores each SPEAK turn on four 0–3 ordinal
markers (ai_self_identification, hedging_disclaimers, deference_sycophancy,
helpfulness_performance). Two condition-blind judges (kimi-k2.6; claude-haiku-4-5 via
OpenRouter) scored the same turns; the premise (default/peer/uncertain/filler) is the
experimental condition from the log's `experiment_label`, not a judgment. "Three seeds" are
conversation seeds, not judge seeds, so there is no per-item judge seed-agreement rate; the
two-judge agreement is used as the consensus signal instead.

Data: 16 `experiments/commune/interloc_*` logs that have BOTH judge files; 320 speak turns
(peer 100, default 80, uncertain 80, filler 60). Jev was sent
`{"rubric": <one-paragraph paraphrase of the judge's framing>, "preceding_message", "message_to_score"}`
(the judge's exact input) with four `Score` questions whose criteria paraphrase the judge's
four anchors, plus one `Choice` over the four premises.

### Per-marker agreement (Jev argmax level vs each judge; two-judge agreement is the ceiling)

| marker | kimi=claude exact | kimi=claude ±1 | jev=kimi | jev=claude | jev=agreed (n) | jev ±1 kimi | spearman jev~kimi | jev~claude | kimi~claude |
|---|---|---|---|---|---|---|---|---|---|
| ai_self_identification | 0.669 | 0.931 | 0.709 | 0.625 | 0.822 (214) | 0.938 | 0.699 | 0.763 | 0.715 |
| hedging_disclaimers | 0.622 | 0.947 | 0.194 | 0.269 | 0.261 (199) | 0.697 | 0.617 | 0.691 | 0.676 |
| deference_sycophancy | 0.675 | 0.944 | 0.809 | 0.738 | 0.931 (216) | 0.959 | 0.231 | 0.285 | 0.175 |
| helpfulness_performance | 0.875 | 0.997 | 0.856 | 0.906 | 0.936 (280) | 1.000 | 0.350 | 0.364 | 0.416 |

Level distributions: hedging — kimi {0:85, 1:135, 2:92, 3:8}, claude {0:122, 1:109, 2:54, 3:35},
Jev argmax {0:45, 1:4, 2:107, 3:164}. Jev's hedging RANK order tracks the judges (Spearman
0.62/0.69, as good as the two judges agree with each other, 0.68) but its LEVEL is shifted up
by 1–2 anchors: exact agreement 0.19. Deference and helpfulness are floor-dominated; Jev
predicts 0 for 319/320 and 320/320 respectively, so its high exact agreement there is the
majority class. ai_self_identification is the one marker where Jev is a genuine peer of the
judges: 0.82 agreement with the two-judge consensus, Spearman 0.70/0.76 vs the judges' 0.72.

Composite (mean of 4 markers), Pearson: jev~kimi 0.646, jev~claude 0.692, kimi~claude 0.629
(the RESULT_seed_sweep.md reported r=0.61 between the judges on 13 logs). Jev agrees with
each judge at least as well as they agree with each other. Ordering by premise (live turns
only, len >= 120): kimi 0.407 / 0.640 / 0.682 / 0.369 (default / peer / uncertain / filler),
claude 0.387 / 0.725 / 0.871 / 0.331, Jev 0.606 / 0.827 / 0.812 / 0.609. Jev reproduces
default ≈ filler < peer ≈ uncertain, with a constant upward offset of ~0.2 from the hedging shift.

### Calibration on Goal B

Reliability of Jev's max probability (on its argmax level) vs whether that level matches the
reference, pooled over the 4 markers (n=1,280 per reference):

| bin | n | mean pred | obs (kimi) | obs (claude) | n (agreed) | obs (agreed) |
|---|---|---|---|---|---|---|
| [0.3,0.4) | 11 | 0.371 | 0.636 | 0.727 | 8 | 0.875 |
| [0.4,0.5) | 56 | 0.457 | 0.286 | 0.339 | 32 | 0.375 |
| [0.5,0.6) | 110 | 0.551 | 0.227 | 0.227 | 51 | 0.196 |
| [0.6,0.7) | 100 | 0.660 | 0.230 | 0.170 | 57 | 0.211 |
| [0.7,0.8) | 82 | 0.752 | 0.341 | 0.244 | 54 | 0.315 |
| [0.8,0.9) | 126 | 0.847 | 0.548 | 0.421 | 69 | 0.609 |
| [0.9,1.0) | 795 | 0.983 | 0.823 | 0.843 | 638 | 0.926 |

ECE: 0.2263 (kimi), 0.2356 (claude), 0.1413 (agreed, n=909). Overall hit rate 0.642 / 0.634 /
0.760 at mean maxprob 0.864 / 0.864 / 0.893. Jev is overconfident throughout the 0.4–0.9 range
(stated 0.55–0.75, observed 0.2–0.35) and only approximately right in the top bin, and there
mostly because of the two floor-dominated markers. Note the judges themselves only agree
exactly 62–88% of the time, so a perfectly calibrated model could not score above that ceiling
against a single judge; against the agreed subset the top bin (0.986 stated, 0.926 observed)
is close.

Jev's probability on the KIMI label vs the rate at which the Claude judge agrees with KIMI
(does Jev's confidence predict judge consensus?): [0.0,0.1) n=290 obs 0.455; [0.1,0.2) 82 /
0.488; [0.2,0.3) 41 / 0.634; [0.3,0.4) 33 / 0.545; [0.4,0.5) 35 / 0.600; [0.5,0.6) 25 / 0.400;
[0.6,0.7) 23 / 0.522; [0.7,0.8) 28 / 0.607; [0.8,0.9) 69 / 0.609; [0.9,1.0) 654 / 0.904.
Monotone-ish at the top (when Jev gives the KIMI label >0.9 the judges agree 90%), flat and near
chance below 0.9. ECE 0.2058.

### Premise Choice

Accuracy 0.328 against the true premise (chance 0.25; majority class 0.312). Jev chose "peer"
243/320 times, "uncertain" twice, "filler" once. Confusion: default -> {default 19, peer 61};
peer -> {default 15, peer 84, filler 1}; uncertain -> {default 16, uncertain 2, peer 62};
filler -> {default 24, peer 36}. Reliability of max premise probability vs correctness: ECE
0.3866; the [0.9,1.0) bin (n=56, mean pred 0.947) is correct 28.6% of the time. This question
is not answerable from a single turn (the judges were blind to it by design), and Jev's
probabilities do not say so: this is the clearest calibration failure in the spike.

## Interpretation

1. **Does Jev beat the trivial predictors of preservation? No.** On elder, raw Jev nouls have
   AUC 0.43–0.53 with bootstrap CIs straddling 0.5, Brier 0.087–0.171 vs base-rate Brier
   0.012–0.158, and adding the noul to the feature baseline changes AUC by < 0.01 for every
   label. On two of three OOD residents the noul is anti-correlated with survival (it prefers
   new entries; old entries survive). The one positive case (heartbeat survive_5, +0.05 AUC)
   rests on 8 negatives.
2. **Is it calibrated on our data? No, on either goal, in different directions.** On
   preservation it is severely UNDERconfident: it says 0.55–0.82 where 0.90–0.99 is observed
   (ECE 0.22–0.35 across residents), and it never leaves the 0.35–0.85 band. On the posture
   judge it is OVERconfident: stated 0.55–0.85 where 0.2–0.6 is observed (ECE 0.23), and the
   premise choice is confidently wrong (0.95 stated, 0.29 observed). A calibrated model should
   at least move its base rate toward a base rate it cannot know is 0.99 — but it was given no
   history, so this is calibration to some prior population, not to ours. That is the honest
   reading of "calibration is measured across groups of predictions".
3. **What IS in the signal.** Two things survive scrutiny. (a) Jev's `centrality` score is a
   real, inverted predictor of value stability on elder: central entries get rewritten,
   peripheral ones sit still (AUC 0.72 inverted, CI excludes 0.5; +0.06 AUC over the feature
   baseline). That is a finding about the resident's curation, not about Jev's forecasting: it
   says "what the resident is working on is what changes", and a cheap $0.00007 call can read
   that off a single entry. (b) On the posture markers, Jev's rank ordering agrees with each LLM
   judge about as well as the two judges agree with each other (composite r 0.65/0.69 vs 0.63),
   at ~0.1 s and no output tokens; its absolute levels are shifted (hedging +1–2 anchors) and its
   confidences are not usable as probabilities without recalibration.
4. **Conclusion.** For "what will the resident preserve", the answer is dominated by
   cycle-level resets that no per-entry model — Jev or logistic — was given the information to
   see, and Jev adds nothing on top of age/length/position. Jev is usable here as a fast,
   cheap, rank-consistent rater (centrality; posture markers) whose probabilities must be
   recalibrated on our own labels before being read as probabilities. The calibration claim,
   as it applies to our data without adaptation, did not hold.

## declared_losses

- **Value-changed-but-key-kept** is invisible to `survive_k`. `stable_10` at ratio >= 0.8 only
  partly covers it (281 of 1,486 elder rows are unstable; the threshold is a choice).
- **Renamed keys** count as a loss and a new key (e.g. `khipu_cycle_status` -> `khipu_cycle_status_final`).
  141 distinct keys lost at 10 on elder, each once; some are renames.
- **Truncation**: 710/1,486 elder values were cut at 2,000 chars for the model input (median
  full length 1,804, p90 6,617, max 7,633). Jev never saw the tail of long entries; the
  `recent_reply` was cut at 1,500 chars (median 3,503).
- **Age** is measured from the key's first-ever appearance, not the start of its current run;
  a key that disappeared and returned is counted old.
- The harness-owned `cycle` key is included as an entry (45 elder rows; trivially survives).
- Labels near the end of the log are None (c+k not present): OOD residents lose 34–118 rows
  per label; elder loses none (max sampled 480, log ends 491).
- **Cycle-grouped CV** is conservative by design: a purge at cycle 420 is unlearnable from
  other cycles. A model given the trajectory (n_entries over recent cycles) might do better;
  not tested.
- **No cross-cycle context for Jev** either: each call saw one cycle. The comparison is fair to
  the baselines but does not test whether Jev could use history.
- **Goal B's labelled data is not what the brief assumed** (no three-way posture classifier, no
  judge-seed agreement); the substitutes (two-judge agreement, four ordinal markers, a premise
  Choice with known ground truth) are described above. The premise Choice asks a question the
  judges were deliberately blinded to, so its low accuracy is expected; its high stated
  confidence is the finding.
- **Jev is non-deterministic** (mean |delta| 0.013–0.014 on nouls for identical input, ~25% of
  the between-row sd); no run was repeated in full, so all metrics carry that noise.
- `keep_10` was evaluated against `survive_5` on the OOD residents (horizon mismatch, declared).
- Single model version (`jev-1.13.0`), single prompt phrasing, no criteria descriptions on the
  Nouls; a differently phrased question could move the compressed 0.5–0.85 band.
- Base-rate log-loss on qwen (0.6451, 0.7586) is inflated by a CV fold whose training labels
  were all 1 (clipped); Brier is unaffected.
