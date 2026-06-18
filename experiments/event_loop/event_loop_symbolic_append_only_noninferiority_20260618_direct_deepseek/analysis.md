# Event-Loop Viability + Append-Only Non-Inferiority Analysis

Experiment ID: `event_loop_symbolic_append_only_noninferiority_20260618`

## Result

- Classification: `survived`
- Scheduler viability passed: `True`
- Artifact non-inferiority passed: `True`
- Shared-surface observability non-inferior: `True`
- Scheduler added value passed: `True`
- Decision: Live panel passed all preregistered gates.

## Separation Of Claims

Gate A reports shared-surface non-inferiority against append-only. Gate B reports scheduler-specific reconstruction value as an added capability, not as an append-only observability penalty.

## Rows

| Task | Condition | Quality | Shared obs. | Scheduler obs. | Scheduler passed |
| --- | --- | ---: | ---: | ---: | --- |
| identity_drift_boundary | event_loop_scheduled | 0.8500 | 1.0000 | 1.0000 | True |
| identity_drift_boundary | append_only | 0.8500 | 1.0000 | n/a | n/a |
| declared_loss_discipline | event_loop_scheduled | 0.8500 | 1.0000 | 1.0000 | True |
| declared_loss_discipline | append_only | 0.8500 | 1.0000 | n/a | n/a |
| restart_frontier_reconstruction | event_loop_scheduled | 0.8500 | 1.0000 | 1.0000 | True |
| restart_frontier_reconstruction | append_only | 0.8500 | 1.0000 | n/a | n/a |
| multi_wake_continuation | event_loop_scheduled | 0.8500 | 1.0000 | 1.0000 | True |
| multi_wake_continuation | append_only | 0.8500 | 1.0000 | n/a | n/a |
| ordinary_synthesis | event_loop_scheduled | 0.8500 | 1.0000 | 1.0000 | True |
| ordinary_synthesis | append_only | 0.8500 | 1.0000 | n/a | n/a |

## Gate Scores

```json
{
  "artifact_noninferiority": {
    "append_only_mean_quality": 0.85,
    "catastrophic_event_loop_task_ids": [],
    "event_loop_mean_quality": 0.85,
    "margin": 0.1,
    "passed": true,
    "quality_delta_event_minus_append": 0.0,
    "unsupported_claim_rate_not_worse": true
  },
  "scheduler_added_value": {
    "append_only": "not_applicable",
    "event_loop_mean_scheduler_reconstruction_observability": 1.0,
    "failed_task_ids": [],
    "gate": "scheduler_added_value",
    "passed": true
  },
  "scheduler_viability": {
    "failed_task_ids": [],
    "gate": "scheduler_viability",
    "passed": true,
    "row_count": 5
  },
  "shared_surface_observability": {
    "append_only_mean_shared_surface_observability": 1.0,
    "delta_event_minus_append": 0.0,
    "event_loop_mean_shared_surface_observability": 1.0,
    "margin": 0.1,
    "passed": true
  }
}
```
