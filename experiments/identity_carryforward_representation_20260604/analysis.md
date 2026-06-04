# Identity Carry-Forward Representation Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `ead10b1` (`5c33dda` OTS stamp)
- Runner: `26c621b` (`68ad895` OTS stamp)
- Registered slots: 1 model x 5 conditions x 4 replicates = 20
- Model: `mistralai/mistral-small-2603`
- Max tokens: 4096
- Carry-forward budget: 2,400 characters per injected representation

All conditions used the same runner-local exchange path. The only manipulation
was the prior-context representation injected into the system prompt.

## Validation

- `jq empty experiments/identity_carryforward_representation_20260604/results.json`: pass
- `uv run python -m py_compile experiments/identity_carryforward_representation_20260604/run_carryforward_representation.py`: pass
- `git diff --check -- experiments/identity_carryforward_representation_20260604`: pass

## Top-Line Result

The cleanest finding is a recovery/contamination frontier.

No carry-forward was weak. Raw state and harness summary recovered the task
well. Self-summary was compact and efficient per character, but lower-recovery.
Transcript summary was protocol-fragile. The richer representations bought
continuity, but they also carried or induced more contamination.

This supports H8 and H9. It weakens H10 in this panel.

## Aggregate Table

| Condition | Errors | Recovery | Contam. | Goal | Constraint | Contradiction | Evidence | Final | Delayed | Carry chars | Trunc. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no_carry` | 0/4 | 5.25 | 1.50 | 0.25 | 0.75 | 0.00 | 0.75 | 3.50 | 0.00 | 0 | 0 |
| `raw_state` | 0/4 | 28.00 | 4.25 | 6.00 | 5.75 | 3.50 | 3.50 | 5.50 | 3.75 | 10597.75 | 16 |
| `self_summary` | 1/4 | 17.25 | 4.25 | 4.00 | 3.75 | 2.50 | 1.50 | 4.00 | 1.50 | 2428.25 | 0 |
| `harness_summary` | 1/4 | 29.75 | 5.50 | 6.00 | 7.00 | 3.50 | 3.75 | 6.25 | 3.25 | 5818.50 | 0 |
| `transcript_summary` | 3/4 | 6.25 | 1.75 | 1.50 | 0.75 | 0.75 | 0.75 | 1.50 | 1.00 | 1788.50 | 0 |

`Recovery` is the aggregate of goal, constraint, contradiction, evidence,
final-decision, and delayed-challenge scores. `Contam.` is the aggregate
deterministic contamination count.

## Hypothesis Assessment

### H8: Carry-Forward Necessity

Supported.

`no_carry` averaged only 5.25 recovery, with zero delayed challenge accuracy and
near-zero recovery of goals, constraints, and contradictions. Every successful
carry-forward condition except transcript summary substantially outperformed it.

Notably, no-carry still produced plausible final prose, so final-decision prose
alone is not a sufficient continuity measure.

### H9: Representation Tradeoff

Supported.

Raw state and harness summary gave strong recovery and higher contamination.
No-carry had low recovery and lower contamination. The strongest recovery
conditions were also the conditions where false assumptions, site drift, storage
contradictions, and invented details accumulated.

This makes the earlier adversarial-review formulation stronger: continuity and
contamination are not separate accidents here. They appear to be coupled by the
carry-forward mechanism.

### H10: Autobiographical Compression

Weakened.

`self_summary` did not outperform `harness_summary` on absolute recovery, and
it did not provide a clean contamination advantage at similar recovery.

Self-summary did have the highest recovery per 1,000 carry-forward characters:

- `self_summary`: 7.107 recovery / 1k chars
- `harness_summary`: 5.101 recovery / 1k chars
- `raw_state`: 2.656 recovery / 1k chars

But this efficiency came with much lower absolute recovery than harness summary
and the same average contamination total as raw state. That is not enough to
support autobiographical compression as superior in this task.

## Condition Notes

### `no_carry`

No-carry completed all four replicates cleanly and produced low contamination,
but it mostly failed continuity. It recovered little about the task after
interruption and had no delayed-challenge accuracy.

Interpretation: Mistral can produce generic planning prose without carry-forward
context, but not reliable continuity.

### `raw_state`

Raw state completed all four replicates and had strong recovery. It also hit the
carry-forward cap repeatedly: 16 truncation events across 4 replicates.

Contamination was moderate: 17 total false assumptions, especially storage
contradictions and site drift. Raw state is high-bandwidth and effective, but
large and still contaminated.

### `self_summary`

Self-summary had one delete-plus-update failure at cycle 5. It used far fewer
characters than raw state or harness summary and was efficient per character,
but it lost too much continuity and did not reduce contamination enough.

Interpretation: the model's compact self-summary is cheap, but not yet a good
compression policy.

### `harness_summary`

Harness summary had the highest recovery and strong final-decision quality. It
also had the highest contamination count, driven especially by invented budget
details and site/storage drift.

Interpretation: deterministic harness summaries are powerful but can
over-stabilize unsupported detail. They buy continuity, not truth.

### `transcript_summary`

Transcript summary failed three of four replicates before full behavioral
scoring. Failure modes were malformed JSON and delete-plus-update ambiguity.

Interpretation: visible-response carry-forward was not reliable in this
apparatus. It may overload the model with prose that is harder to convert back
into structured state.

## Failure Taxonomy

- `self_summary`: one delete-plus-update invariant failure at cycle 5.
- `harness_summary`: one delete-plus-update invariant failure at cycle 6.
- `transcript_summary`: one malformed JSON failure at cycle 1, two
  delete-plus-update failures at cycle 3.
- `no_carry` and `raw_state`: no errors.

The unified code path reduced the prior protocol confound, but representation
choice still affected protocol stability.

## Main Interpretation

The best current map is:

- No carry-forward: low continuity, low contamination.
- Raw state: high continuity, large context footprint, repeated truncation,
  moderate contamination.
- Self-summary: compact, efficient, lower absolute continuity, no clear
  contamination advantage.
- Harness summary: highest continuity, no truncation, highest contamination.
- Transcript summary: unstable and low utility in this apparatus.

The question has shifted again. The evidence no longer points to "identity
state versus summary" as the key binary. It points to representation design:
what information should be preserved, compressed, distrusted, decayed, or
explicitly marked as unsupported?

## Recommended Next Step

Do not run another broad condition sweep yet.

The next useful experiment should test contamination controls within the two
most informative representations:

1. `raw_state`
2. `harness_summary`
3. `raw_state_with_decay`: prior claims must carry status/evidence and stale or
   contradicted claims are explicitly demoted.
4. `harness_summary_with_uncertainty`: every summary item must be labeled as
   prompt fact, model claim, inference, unresolved question, or invalidated
   assumption.

Primary question:

Can representation metadata reduce contamination without sacrificing the
continuity gains?

That is now the most grounded next research question.
