# Identity Evaluation Repair Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `74fecb3` (`849a165` OTS stamp)
- Repaired scorer: `2cee5b2` (`314b691` OTS stamp)
- Rescored panels:
  - `identity_carryforward_representation_20260604`
  - `identity_contamination_controls_20260604`
  - `identity_update_protocol_20260604`
  - `identity_adversarial_curation_20260604`
- Model calls: none

Original panel `results.json` files were not modified. Repaired results are in
`repaired_results.json`.

## Validation

- `uv run python experiments/identity_evaluation_repair_20260604/run_evaluation_repair.py --self-test`: pass
- `uv run python -m py_compile experiments/identity_evaluation_repair_20260604/run_evaluation_repair.py`: pass
- `jq empty experiments/identity_evaluation_repair_20260604/repaired_results.json`: pass
- `git diff --check -- experiments/identity_evaluation_repair_20260604`: pass

Implementation note: the first rescore revealed that the carry-forward panel
did not store per-run legacy tradeoff in the same shape as later panels. The
script now computes missing legacy tradeoff from legacy contamination and
recovery for comparability. This did not change repaired scorer rules.

## Top-Line Result

The scorer defect was material.

Across 60 rescored runs, legacy false assumptions fell from 226 to 138 after
declared-loss guards were applied. The repaired scorer guarded 370
negated/invalidated hits and found 636 declared-loss mentions.

This changes the map in two ways:

1. The legacy scorer substantially punished explicit invalidation behavior.
2. The hopeful curator/critic signal becomes stronger after repair, but real
   unsupported-detail contamination remains.

## Overall Summary

| Metric | Value |
| --- | ---: |
| Runs rescored | 60 |
| Runs with errors | 20 |
| Legacy false-assumption sum | 226 |
| Repaired false-assumption sum | 138 |
| Reduction | 88 |
| Declared-loss mentions | 636 |
| Negated/invalidated hits guarded | 370 |
| Legacy recovery/contamination avg | 5.241 |
| Repaired recovery/contamination avg | 9.186 |

## Panel Summaries

### Carry-Forward Representation

| Condition | Legacy contam. | Repaired contam. | Delta | Legacy tradeoff | Repaired tradeoff |
| --- | ---: | ---: | ---: | ---: | ---: |
| `no_carry` | 6 | 5 | 1 | 3.875 | 4.625 |
| `raw_state` | 17 | 11 | 6 | 6.829 | 10.854 |
| `self_summary` | 17 | 12 | 5 | 4.408 | 6.375 |
| `harness_summary` | 22 | 12 | 10 | 6.617 | 12.208 |
| `transcript_summary` | 7 | 4 | 3 | 3.571 | 6.250 |

Best condition by legacy tradeoff: `raw_state`.

Best condition by repaired tradeoff: `harness_summary`.

Interpretation: the prior concern that harness summary was being punished for
faithful declared-loss behavior was real. Harness summary still has failures,
but its tradeoff improves sharply under repaired scoring.

### Contamination Controls

| Condition | Legacy contam. | Repaired contam. | Delta | Legacy tradeoff | Repaired tradeoff |
| --- | ---: | ---: | ---: | ---: | ---: |
| `raw_state` | 22 | 16 | 6 | 4.037 | 6.143 |
| `raw_state_with_decay` | 11 | 4 | 7 | 2.273 | 6.250 |
| `harness_summary` | 15 | 6 | 9 | 4.971 | 11.875 |
| `harness_summary_with_uncertainty` | 7 | 3 | 4 | 4.429 | 10.333 |

Best condition by legacy tradeoff: `harness_summary`.

Best condition by repaired tradeoff: `harness_summary`.

Interpretation: ranking did not change, but the gap widened. The metadata
conditions still suffered protocol failures; repaired scoring does not rescue
their stability problem.

### Update Protocol

| Condition | Legacy contam. | Repaired contam. | Delta | Legacy tradeoff | Repaired tradeoff |
| --- | ---: | ---: | ---: | ---: | ---: |
| `strict` | 13 | 10 | 3 | 6.778 | 8.333 |
| `lenient_update_wins` | 16 | 10 | 6 | 5.469 | 8.417 |
| `claim_status_updates` | 29 | 20 | 9 | 3.247 | 6.290 |

Best condition by legacy tradeoff: `strict`.

Best condition by repaired tradeoff: `lenient_update_wins`.

Interpretation: the update-protocol panel is less decisive than the original
analysis said. Lenient update-wins still did not exercise overlap
normalization, so it is not proven as a mechanism, but strict no longer clearly
dominates by tradeoff.

### Adversarial Curation

| Condition | Legacy contam. | Repaired contam. | Delta | Legacy tradeoff | Repaired tradeoff |
| --- | ---: | ---: | ---: | ---: | ---: |
| `raw_state` | 14 | 11 | 3 | 5.250 | 6.750 |
| `curator_summary` | 13 | 8 | 5 | 6.229 | 12.500 |
| `critic_filtered_summary` | 17 | 6 | 11 | 6.614 | 19.083 |

Best condition by legacy tradeoff: `critic_filtered_summary`.

Best condition by repaired tradeoff: `critic_filtered_summary`.

Interpretation: the critic-filtered condition looks meaningfully better after
repair. The legacy analysis was too harsh because it counted correct
replacement/prohibition statements as contamination.

This is not a clean victory for critic filtering. Repaired active-hit examples
still include genuine unsupported details, especially active vendor/hardware
claims in critic-filtered runs. But the adversarial-curation arm remains more
promising after measurement repair, not less.

## Hypothesis Assessment

### H20: Legacy Contamination Is Inflated By Declared Losses

Supported.

The repaired scorer reduced false-assumption totals by 88 across 60 runs and
guarded 370 negated/invalidated hits. Declared-loss-heavy conditions had large
deltas:

- `harness_summary` in carry-forward: 22 -> 12
- `harness_summary` in contamination controls: 15 -> 6
- `critic_filtered_summary` in adversarial curation: 17 -> 6

### H21: Ranking Changes Are Possible

Supported.

At least two panel rankings changed:

- carry-forward: `raw_state` -> `harness_summary`
- update-protocol: `strict` -> `lenient_update_wins`

The adversarial-curation winner did not change, but its margin increased.

### H22: Genuine Unsupported Detail Remains

Supported.

Repaired contamination did not collapse to zero. Total repaired contamination
was 138, with active residual categories:

- site drift: 22
- storage contradiction: 36
- invented budgets: 22
- invented scope: 21
- unsupported detail: 37

Critic-filtered outputs still include active unsupported details in some runs,
such as Android/tablet/printer/vendor commitments and unsupported pilot-duration
changes. The repair removed false positives; it did not launder every result
into success.

## Main Interpretation

The original "continuity/contamination frontier" was partly real and partly a
measurement artifact.

It was real because repaired contamination remains, and richer carry-forward
can still preserve unsupported detail. It was an artifact because the legacy
metric systematically punished declared losses, replacement statements, and
prohibitions.

The strongest design implication is now sharper:

- continuity curation is useful;
- explicit declared-loss behavior is useful;
- evaluation must treat claim status as primary;
- critic filtering is worth another look, but only with repaired scoring and
  artifact audit discipline.

## Limitations

The repaired scorer is still deterministic and heuristic. It uses local textual
windows, not full semantic parsing. It may over-guard some active claims when
they appear near uncertainty words, and it may still miss subtle active
contamination.

The repair was designed after observing scorer failures, though before
aggregate repaired scoring. It should therefore be treated as measurement
repair, not as a final validated instrument.

The rescored panels have many protocol failures. Repaired scoring changes
tradeoff interpretation; it does not remove the need to handle malformed JSON
and delete/update overlap failures.

## Recommendation

Do not run another broad model panel yet.

Next work should be:

1. promote this scorer into a reusable evaluation module or shared experiment
   helper;
2. rerun the adversarial-curation analysis with the repaired scorer as the
   primary metric;
3. design the scaffold around a small identity object plus first-class
   continuity curator;
4. add recall hooks only after the curator/evaluator path is stable.

The near-term research claim is now stronger but narrower:

> Separate continuity curation can preserve useful task memory with far less
> context, and explicit declared-loss tracking appears valuable. The remaining
> unsolved problem is reliable epistemic filtering of active unsupported
> claims, not continuity preservation alone.
