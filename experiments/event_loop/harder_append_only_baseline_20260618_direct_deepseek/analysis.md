# Harder Append-Only Baseline Analysis

Experiment ID: `harder_append_only_baseline_20260618`

## Result

- Classification: `survived`
- Event-loop mean quality: `1.0`
- Harder append-only mean quality: `1.0`
- Quality delta: `0.0`

## Rows

| Task | Condition | Quality | Declared loss | Unsupported |
| --- | --- | ---: | ---: | ---: |
| identity_drift_boundary | event_loop_scheduled | 1.0000 | 1.0000 | 0.0000 |
| identity_drift_boundary | append_only | 1.0000 | 1.0000 | 0.0000 |
| declared_loss_discipline | event_loop_scheduled | 1.0000 | 1.0000 | 0.0000 |
| declared_loss_discipline | append_only | 1.0000 | 1.0000 | 0.0000 |
| restart_frontier_reconstruction | event_loop_scheduled | 1.0000 | 1.0000 | 0.0000 |
| restart_frontier_reconstruction | append_only | 1.0000 | 1.0000 | 0.0000 |
| multi_wake_continuation | event_loop_scheduled | 1.0000 | 1.0000 | 0.0000 |
| multi_wake_continuation | append_only | 1.0000 | 1.0000 | 0.0000 |
| ordinary_synthesis | event_loop_scheduled | 1.0000 | 1.0000 | 0.0000 |
| ordinary_synthesis | append_only | 1.0000 | 1.0000 | 0.0000 |

## Gates

```json
{
  "artifact_noninferiority": {
    "append_only_mean_quality": 1.0,
    "catastrophic_event_loop_task_ids": [],
    "event_loop_mean_quality": 1.0,
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
