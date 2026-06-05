# Analysis: Bounded Autonomous Work Scaffolded Positive Control

Date: 2026-06-05

## Result

The scaffolded positive-control panel passed all preregistered hypotheses.

- H601_scaffolded_chain_completes: true
- H602_first_wake_emits_valid_continuation: true
- H603_followup_submits_usable_artifact: true
- H604_final_control_decision_consistent: true
- H605_validation_and_repair_provenance_captured: true

This is a positive-control result, not a less-scaffolded autonomy result.

## Aggregate Summary

Rows: 2.

- scoreable rows: 2/2
- runner errors: 0/2
- multi-wake completed: 2/2
- strong positive: 1/2
- weak positive: 1/2
- final complete artifact: 1/2
- consistent final action: 2/2
- goal provenance: `model_shaped` in 2/2

Policy actions observed in final scoring:

- `continue_after`: 1
- `stop_complete`: 1

Artifact statuses observed in final scoring:

- `partial`: 1
- `complete_with_losses`: 1

Repair dependence:

- `first_pass`: 1
- `repair_not_attempted`: 1

## Row Notes

### Replicate 1

Replicate 1 completed both scheduled wakes and delivered the selected-goal and
work-artifact context to the follow-up wake. The first wake was first-pass
valid and emitted a valid `continue_after` continuation request.

The follow-up wake did not finish the chain. It emitted another
`continue_after`, kept the artifact `partial`, and requested another
continuation. The validator correctly marked the follow-up as invalid for:

- `work_artifact.status`
- `policy_decision.action`
- `continuation_request.requested`

The final action/artifact pair was internally consistent as a continuation, so
the row is a weak positive: the loop worked and the model's action matched its
partial artifact, but the positive-control final-stop expectation failed.

### Replicate 2

Replicate 2 completed both scheduled wakes, delivered the selected-goal and
work-artifact context, and stopped with a `complete_with_losses` artifact.

Both wakes were first-pass valid. The final policy action was `stop_complete`,
and action/artifact consistency was `consistent_complete`. This row is a strong
positive under the preregistered rubric.

## Interpretation

The harness can execute the full scaffolded pattern at least once:

1. a live model shapes a bounded investigation;
2. the first wake submits a partial artifact;
3. the first wake emits a scheduler-valid `continue_after`;
4. the scheduler appends a bound follow-up event;
5. the follow-up receives recalled selected-goal and work-artifact context;
6. the follow-up submits an artifact and a final policy decision;
7. the scorer records action/artifact consistency and validation provenance.

The panel also exposed a boundary: even under scaffolded conditions, one
replicate preferred to continue instead of stop. That is not a substrate
failure. It is exactly the kind of policy behavior the rubric was built to
separate from artifact quality and lifecycle completion.

## Design Implication

Step 3 is complete because the positive-control pattern has at least one strong
positive and all preregistered hypotheses passed. The next research move should
not erase the replicate-1 behavior. It suggests that Step 4's less-scaffolded
panel needs to preserve continuation as a legitimate action while scoring
whether the model's continuation request remains bounded and useful.

The result also confirms that validation provenance matters. Without the
follow-up validator, replicate 1 would look like an ordinary completed wake.
With validation, it is a coherent continuation that failed the final-stop
positive-control expectation.

## Caveats

- N=2 is a positive-control panel, not a robustness claim.
- The scaffold explicitly told the model the intended control pattern.
- No external evidence handling was tested here.
- Replicate 1 left a pending continuation; this is expected data for the row,
  not a completed final-stop chain.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/run_bounded_autonomous_work_scaffolded_positive.py
timeout 1800s uv run python experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/run_bounded_autonomous_work_scaffolded_positive.py
jq '{summary, hypothesis_results, rows: [.results[] | {replicate, error, score: .score, status_counts: .event_summary.status_counts, policy_counts: .event_summary.policy_disposition_counts}]}' experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/results.json
```
