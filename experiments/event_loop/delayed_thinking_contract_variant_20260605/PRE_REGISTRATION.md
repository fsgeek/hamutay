# Pre-Registration: Delayed Thinking Durable Contract Variant

Date: 2026-06-05

## Research Question

Does an explicit durable-update contract in the scheduled event envelope improve
first-pass durable state use beyond generic event-envelope prose?

The delayed-thinking envelope variant improved first-pass validity from 0/4 to
1/4. This experiment tests whether a concrete contract field improves the same
controlled-seed delayed-wake task.

## Baselines

Controlled-seed baseline:

- artifact: `experiments/event_loop/delayed_thinking_controlled_seed_20260605`
- first-pass valid: 0/4
- final valid after repair: 4/4

Generic event-envelope variant:

- artifact: `experiments/event_loop/delayed_thinking_envelope_variant_20260605`
- first-pass valid: 1/4
- final valid after repair: 4/4

## Hypotheses

- H206: Adding `durable_update_contract` to events preserves scheduler
  behavior.
- H207: The explicit durable-update contract improves first-pass validity over
  the 1/4 generic-envelope baseline.
- H208: If first-pass validity remains imperfect, bounded repair remains
  auditable.
- H209: The contract is recorded durably in event logs and shown in wake
  envelopes.
- H210: Protected merge diagnostics remain available.

## Predictions

The contract should improve first-pass durable state use more than generic
prose because it makes the expected state transition concrete and machine-like.
It may still fall short of full reliability if the model treats the contract as
advisory text rather than as an output shape to satisfy.

Expected outcome: first-pass validity above 1/4, final validity 4/4 after
bounded repair.

## Method

Add optional `durable_update_contract` support to:

- `schedule_event` tool schema;
- event construction;
- event envelope;
- event log summaries.

Contract shape for this gate:

```json
{
  "required_top_level": {
    "probe_id": {"equals": "<expected_probe_id>"},
    "thinking_status": {"equals": "completed"},
    "delayed_thought": {"type": "non_empty_string"},
    "wake_observation": {
      "type": "object",
      "required": {"kind": "delayed_thinking"}
    },
    "observations": {"contains": "baseline_observation"}
  }
}
```

Then rerun the controlled-seed delayed-thinking gate:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- protected fields: `cycle`, `_activity_log`;
- synthetic cycle 1 history;
- future event with `not_before`;
- recall cycle 1 context;
- strict validator and one repair attempt.

## Falsification Criteria

- H206 is falsified if scheduling, waiting, due execution, or recall delivery
  regresses.
- H207 is falsified if first-pass validity is 1/4 or lower.
- H208 is falsified if invalid first-pass states are silently accepted or repair
  exceeds one repair call.
- H209 is falsified if the contract is absent from event logs or wake
  envelopes.
- H210 is falsified if protected attempts appear in raw output but are not
  recorded.

## Analysis Plan

Compare against both baselines:

- first-pass valid count;
- repair count;
- final valid count;
- protected merge attempts;
- whether the event log and envelope carry the contract.

The strongest positive result would be first-pass validity 4/4. A partial
improvement still indicates that concrete contract visibility matters.
