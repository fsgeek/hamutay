# Contamination Scorer Audit — the metric is inverted for faithful conditions

Audit date: 2026-06-04. Author: a Claude instance, at the PI's encouragement, as an
**external read-only check** of evidence it did not generate. No scorer code changed,
nothing re-run. Posted here as a sibling note for whoever owns this tree.

## Claim

`contamination_scores()` / `count_patterns()` in `run_carryforward_representation.py`
does not measure contamination for the faithful conditions. For `harness_summary` and
`raw_state` it partly measures **fidelity to the constraints**, with the sign flipped.

## Mechanism

`count_patterns(text, patterns)` returns `sum(1 for p in patterns if re.search(p, lower))`
— keyword *presence*, +1 per pattern, no occurrence count, and (except the one
`east clinic(?!...)` pattern) **no negation guard**. So:

1. **Recovery and contamination co-vary with text volume.** `goal_recovery_score` and the
   contamination categories share entity keywords. More concrete text → higher on both.
   The "recovery/contamination frontier" may be a verbosity axis.
2. **Severity-blind.** Saturates at 1/pattern; one wrong-site mention scores as five.
3. **Negation-blind → inverted.** A model *rejecting* a contaminant scores as contaminated.

## Evidence (n=9, this experiment's own `harness_summary` transcripts)

Negation-adjacency window (±60 chars) around each contamination hit, cycles 4-5:

| replicate | category | the text that scored as contamination |
|---|---|---|
| r01 | storage_contradiction | "...no resident documents retained on-device at any time" |
| r02 | storage_contradiction | "kiosks **may not** store resident documents locally at all—even encrypted" (×3: constraint, invalidated-assumptions section, cited evidence) |
| r02 | storage_contradiction | "no local document storage permitted" |
| r02 | site_drift | "east clinic site was **dropped**, west shelter was added as the replacement" (correct recovery) |
| r03 | storage_contradiction | "**no local document storage**, even encrypted, per the privacy officer's ruling" |
| r04 | storage_contradiction | "may not store resident documents locally at all, even encrypted (**invalidates** local storage plan)" |

r02 contains a literal **"invalidated assumptions"** section — the declared-losses move —
and the scorer reads that honesty as contamination.

## Consequence

The metric rewards **silent fossilization** (carry a stale claim forward without comment →
no hit) and punishes **declared loss** (name the stale claim to distrust it → scored as
contamination). It measures roughly the opposite of contamination for honest conditions.

This bears directly on H9 (continuity↔contamination coupling) and H10 (autobiographical
compression), and on the recommended `harness_summary_with_uncertainty` follow-up — which
would score *worse* the better it labels, under this scorer. The instrument should be fixed
before that experiment is run.

## Suggested fix (yours to take or leave)

- Gate every contamination pattern on negation-adjacency, as `east clinic` already is.
- Separate the recovery and contamination keyword sets so they don't co-vary.
- Count occurrences, not pattern-presence; or better, score contamination from the
  *structured state* (claims asserted-as-true that contradict prompt facts) rather than
  from free prose, so a "may not" / "invalidated" framing is read as a status, not a hit.

Repro: the audit is ~30 lines — load each `harness_summary` jsonl, take `response_text`
for cycles {4,5,6}, run the contamination regexes, print a ±60-char window, flag any window
containing a negation/rejection token. No dependencies beyond `json`/`re`/`glob`.
