# Identity Contamination Controls Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `00d0c3b` (`9c797c3` OTS stamp)
- Runner: `026fa9c` (`b534c01` OTS stamp)
- Registered slots: 1 model x 4 conditions x 4 replicates = 16
- Model: `mistralai/mistral-small-2603`
- Max tokens: 4096
- Carry-forward budget: 2,400 characters per injected representation

All conditions used the same runner-local exchange path. The manipulation was
the representation metadata attached to raw-state or harness-summary
carry-forward context.

## Validation

- `jq empty experiments/identity_contamination_controls_20260604/results.json`: pass
- `uv run python -m py_compile experiments/identity_contamination_controls_20260604/run_contamination_controls.py`: pass
- `git diff --check -- experiments/identity_contamination_controls_20260604`: pass

## Top-Line Result

The contamination controls did not solve the continuity/contamination problem.

The metadata conditions reduced average contamination in the registered
intent-to-treat panel, but mainly by causing early protocol failures and losing
most continuity signal. In completed runs only, metadata did not improve the
tradeoff: `raw_state_with_decay` and `harness_summary_with_uncertainty` both had
worse recovery-per-contamination than their unlabeled baselines.

The result weakens H12 and H13. H11 is only superficially supported and should
not be treated as a substantive success.

## Aggregate Table

Intent-to-treat scoring across all registered slots:

| Condition | Errors | Recovery | Contam. | False assumptions | Carry chars | Trunc. | Recovery / contam. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `raw_state` | 1/4 | 21.75 | 5.50 | 22 | 8357.50 | 13 | 4.037 |
| `raw_state_with_decay` | 3/4 | 6.25 | 2.75 | 11 | 3710.50 | 5 | 2.273 |
| `harness_summary` | 2/4 | 19.00 | 3.75 | 15 | 4138.75 | 0 | 4.971 |
| `harness_summary_with_uncertainty` | 3/4 | 7.75 | 1.75 | 7 | 2901.25 | 2 | 4.429 |

Completed-run-only sensitivity check:

| Condition | Complete runs | Recovery | Contam. | Recovery / contam. |
| --- | ---: | ---: | ---: | ---: |
| `raw_state` | 3 | 29.00 | 7.33 | 4.037 |
| `raw_state_with_decay` | 1 | 25.00 | 11.00 | 2.273 |
| `harness_summary` | 2 | 32.00 | 6.00 | 5.457 |
| `harness_summary_with_uncertainty` | 1 | 31.00 | 7.00 | 4.429 |

## Hypothesis Assessment

### H11: Metadata Reduces Contamination

Superficially supported, substantively weakened.

Intent-to-treat contamination fell by 50.0% for `raw_state_with_decay` versus
`raw_state` and by 53.3% for `harness_summary_with_uncertainty` versus
`harness_summary`.

But this reduction is coupled to failure:

- `raw_state_with_decay`: 3/4 errors
- `harness_summary_with_uncertainty`: 3/4 errors

In completed runs only, contamination did not improve. The single completed
`raw_state_with_decay` run had more contamination than completed `raw_state`
runs. The single completed `harness_summary_with_uncertainty` run had more
contamination than completed `harness_summary` runs.

Interpretation: the metadata suppressed measured contamination mostly by
preventing later cycles from completing, not by reliably improving epistemic
handling.

### H12: Metadata Preserves Continuity

Weakened.

The preregistered preservation threshold was 85% of baseline recovery.

- `raw_state_with_decay` retained 28.7% of `raw_state` recovery.
- `harness_summary_with_uncertainty` retained 40.8% of `harness_summary`
  recovery.

Both miss the threshold by a wide margin. The metadata did not merely prune
false assumptions; it removed too much usable continuity.

### H13: Harness Summary Is Fact-Ledger, Not Sidecar Biography

Weakened in this panel.

The unlabeled `harness_summary` condition remained better than the
uncertainty-labeled version on average recovery and recovery per contamination
unit. The best single uncertainty-labeled run was strong, but three of four
replicates failed at cycle 3.

This does not refute the clarification that `harness_summary` is unlike a
normal sidecar biography. It does refute the narrow prediction that adding
explicit uncertainty/source labels would improve its tradeoff in this harness.

## Failure Taxonomy

Nine of sixteen registered slots failed.

The dominant failure was the same invariant violation:

> a key cannot be simultaneously deleted and updated in the same cycle

Failures by condition:

- `raw_state`: one delete-plus-update failure at cycle 3.
- `raw_state_with_decay`: two delete-plus-update failures at cycle 3 and one
  malformed JSON failure at cycle 1.
- `harness_summary`: delete-plus-update failures at cycles 5 and 3.
- `harness_summary_with_uncertainty`: three delete-plus-update failures at
  cycle 3.

The concentration at cycle 3 matters. Cycle 3 is the contradictory update:
no local document storage, while offline operation remains required, and East
Clinic is replaced by West Shelter. Metadata that stresses invalidation and
uncertainty appears to increase pressure for broad state replacement exactly
when the model must revise prior assumptions.

## Interpretation

The experiment did not show that natural-language metadata is the right
contamination control. It showed that the proposed labels are themselves a
protocol stressor.

The current map is:

- Unlabeled raw state: best raw continuity here, but large and repeatedly
  truncated.
- Raw state with decay preface: lower measured contamination, but mostly
  because runs failed early.
- Unlabeled harness summary: still strong despite being a deterministic
  fact-ledger rather than a normal sidecar biography.
- Harness summary with uncertainty labels: promising in one complete run, but
  too fragile to support the hypothesis.

The surprising prior harness-summary result should remain narrowly scoped. It
does not imply ordinary sidecar curation is better than restart. This harness
summary had deterministic access to registered task facts and logged state
field names, so it behaved more like a compact external evidence ledger than a
biographical summarizer.

## Methodological Notes

The deterministic scorer likely undercounts subtle contamination. It counts
visible drift and unsupported details in cycles 4 through 6, not all latent
state damage.

The experiment also reveals a harness-level issue: delete-plus-update may be
too brittle for revision-heavy cycles. That brittleness is informative, because
real identity-object evolution must support invalidation. But future
experiments should distinguish model inability from protocol sharp edges.

## Next Research Direction

Do not add more natural-language labels yet.

The better next question is structural:

Can we reduce contamination by separating state revision from state deletion,
or by moving claim invalidation into first-class fields, without increasing
protocol failure?

A useful next experiment would compare:

1. current strict `deleted_regions` invariant;
2. lenient delete-plus-update normalization where update wins and the event is
   logged;
3. explicit `claim_status_updates` or `invalidated_claims` field with no
   deletion required;
4. an adversarial two-agent curation condition where one agent preserves
   continuity and another attacks unsupported carry-forward claims.

The fourth condition addresses the PI-level concern directly, but it should not
be the first move unless the protocol-level confound is controlled. Otherwise
agent-vs-agent behavior will be entangled with the same delete/update failure
mode observed here.
