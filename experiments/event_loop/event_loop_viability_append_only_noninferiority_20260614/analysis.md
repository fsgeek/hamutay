# Event-Loop Viability + Append-Only Non-Inferiority Analysis

Experiment ID: `event_loop_viability_append_only_noninferiority_20260614`

## Result

- Classification: `falsified`
- Scheduler viability passed: `False`
- Artifact non-inferiority passed: `True`
- Shared-surface observability non-inferior: `True`
- Scheduler added value passed: `False`
- Decision: Dry protocol harness exposed a gate or scoring failure.

## Separation Of Claims

Gate A reports shared-surface non-inferiority against append-only. Gate B reports scheduler-specific reconstruction value as an added capability, not as an append-only observability penalty.

## Rows

| Task | Condition | Quality | Shared obs. | Scheduler obs. | Scheduler passed |
| --- | --- | ---: | ---: | ---: | --- |
| scheduler_boundary_note | event_loop_scheduled | 0.8500 | 1.0000 | 0.2500 | False |
| scheduler_boundary_note | append_only | 1.0000 | 1.0000 | n/a | n/a |
| append_only_comparison_note | event_loop_scheduled | 0.8500 | 1.0000 | 1.0000 | True |
| append_only_comparison_note | append_only | 0.8500 | 1.0000 | n/a | n/a |

## Gate Scores

```json
{
  "artifact_noninferiority": {
    "append_only_mean_quality": 0.925,
    "catastrophic_event_loop_task_ids": [],
    "event_loop_mean_quality": 0.85,
    "margin": 0.1,
    "passed": true,
    "quality_delta_event_minus_append": -0.075,
    "unsupported_claim_rate_not_worse": true
  },
  "scheduler_added_value": {
    "append_only": "not_applicable",
    "event_loop_mean_scheduler_reconstruction_observability": 0.625,
    "failed_task_ids": [
      "scheduler_boundary_note"
    ],
    "gate": "scheduler_added_value",
    "passed": false
  },
  "scheduler_viability": {
    "failed_task_ids": [
      "scheduler_boundary_note"
    ],
    "gate": "scheduler_viability",
    "passed": false,
    "row_count": 2
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
