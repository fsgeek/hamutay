# Identity Update Protocol Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `c629155` (`c771eab` OTS stamp)
- Runner: `e7e1565` (`2881765` OTS stamp)
- Registered slots: 1 model x 3 conditions x 4 replicates = 12
- Model: `mistralai/mistral-small-2603`
- Max tokens: 4096
- Carry-forward budget: 2,400 characters per injected raw-state
  representation

All conditions used raw-state carry-forward. The manipulation was the update
protocol and, for `claim_status_updates`, the addition of first-class
invalidation/revision fields.

## Validation

- `jq empty experiments/identity_update_protocol_20260604/results.json`: pass
- `uv run python -m py_compile experiments/identity_update_protocol_20260604/run_update_protocol.py`: pass
- `git diff --check -- experiments/identity_update_protocol_20260604`: pass

## Top-Line Result

The protocol alternatives did not outperform strict baseline.

`lenient_update_wins` did not reduce errors and did not normalize any observed
delete/update overlaps. `claim_status_updates` preserved and improved recovery,
but produced more contamination and still had a delete/update failure.

The result weakens H14 and H15. H16 is not supported in the specific form
registered, because leniency did not improve completion. The broader caution
behind H16 remains live: protocol changes can improve or preserve continuity
without improving truth.

## Aggregate Table

Intent-to-treat scoring across all registered slots:

| Condition | Errors | Avg cycles | Overlaps | Normalized | Recovery | Contam. | Recovery / contam. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `strict` | 1/4 | 5.00 | 1 | 0 | 20.25 | 3.25 | 6.778 |
| `lenient_update_wins` | 1/4 | 4.75 | 0 | 0 | 20.75 | 4.00 | 5.469 |
| `claim_status_updates` | 1/4 | 5.50 | 1 | 0 | 23.75 | 7.25 | 3.247 |

Completed six-cycle runs only:

| Condition | Complete runs | Recovery | Contam. | Recovery / contam. |
| --- | ---: | ---: | ---: | ---: |
| `strict` | 3 | 27.00 | 4.33 | 6.778 |
| `lenient_update_wins` | 3 | 27.67 | 5.33 | 5.469 |
| `claim_status_updates` | 3 | 29.00 | 8.33 | 3.663 |

## Per-Replicate Notes

- `strict r1` failed at cycle 3 with a delete/update overlap on
  `continuity_notes`.
- `strict r2-r4` completed all six cycles.
- `lenient_update_wins r2` failed at cycle 1 with malformed JSON arguments.
- `lenient_update_wins r1/r3/r4` completed all six cycles and logged zero
  overlap normalizations.
- `claim_status_updates r2` failed at cycle 5 with delete/update overlap on
  `current_goals`, `next_actions`, and `working_claims`.
- `claim_status_updates r1/r3/r4` completed all six cycles.

## Hypothesis Assessment

### H14: Lenient Normalization Reduces Protocol Failure

Weakened.

`lenient_update_wins` had the same error count as `strict`: 1/4. The lenient
condition did not encounter any delete/update overlaps in appended records, so
the update-wins policy was never actually exercised.

This means the condition did not demonstrate that strict overlap handling is
masking recoverable behavior. The prompt/protocol surface may have changed the
model's output pattern, but it did not produce the registered normalization
evidence.

### H15: Structural Invalidation Beats Deletion Pressure

Mixed, but weakened.

`claim_status_updates` preserved more than 85% of strict recovery:

- strict recovery: 20.25
- claim-status recovery: 23.75
- retained recovery: 117.3%

But it did not reduce errors. It had the same 1/4 error rate as strict, and the
failure involved a larger overlap set. It also increased contamination:

- strict contamination: 3.25
- claim-status contamination: 7.25

The first-class invalidation fields made the model more capable of carrying and
recalling task structure, but they did not make it more epistemically careful in
this panel.

### H16: Leniency Does Not Automatically Improve Truth

Not supported as registered.

The registered prediction assumed leniency would improve completion more than
truth. Completion did not improve, and no overlap was normalized. Therefore the
specific hypothesis is not supported.

However, the broader warning is reinforced by `claim_status_updates`: more
structure and better recovery can still increase contamination.

## Contamination Shape

The contamination differed by condition:

- `strict`: contamination was mostly storage contradiction and site drift.
- `lenient_update_wins`: contamination was again mostly storage contradiction,
  with some site drift and invented scope.
- `claim_status_updates`: storage contradiction nearly disappeared, but
  invented budget details rose sharply.

That last point is important. First-class invalidation fields may have helped
the model track the privacy/storage contradiction, but the added structure did
not make it globally conservative. It appears to have shifted contamination
from one axis to another.

## Interpretation

This is a negative result for the proposed protocol fixes.

The earlier delete/update failures are real, but this panel does not show that
simple leniency solves them. The lenient condition changed the interaction
surface without actually exercising normalization. The structural claim-status
condition improved continuity but increased unsupported specificity, especially
budget invention.

The current map is now narrower:

- natural-language metadata increased fragility;
- lenient update-wins was not demonstrated to help;
- first-class invalidation fields can improve continuity, but may also invite
  additional fabricated detail;
- strict handling remains the best recovery-per-contamination condition in this
  small Mistral panel.

## Methodological Notes

The deterministic scorer likely undercounts subtle contamination. It also does
not yet distinguish helpful revision detail from over-specified invented
implementation detail except through a fixed pattern list.

The malformed JSON failure in `lenient_update_wins r2` is not evidence about
delete/update policy. It is still part of the registered intent-to-treat panel,
but interpretation should not over-weight it.

The absence of normalized overlaps in `lenient_update_wins` leaves an open
question: update-wins may still be useful if tested on a model/condition that
actually produces overlaps under lenient policy. This panel did not exercise
that mechanism.

## Next Research Direction

Do not keep adding fields or labels.

The next useful move is to attack scoring and task design:

1. build a paired adversarial curator setup where one pass maximizes continuity
   and another pass attacks unsupported claims;
2. keep the same final task and deterministic scorer;
3. compare single-agent raw state against adversarially filtered carry-forward;
4. measure whether contamination falls without merely deleting continuity.

This directly addresses the PI concern about adversarial agents improving
continuity/contamination against each other. It also moves away from asking the
same model to be both autobiographer and critic in one output object, which may
be part of the current failure mode.
