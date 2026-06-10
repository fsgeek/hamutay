# Live Autonomy Pilot Run Analysis

Run ID: `c39ba9a3-9dda-48f2-82f6-cb90f8229bae`

Date: 2026-06-10

Preregistration: `experiments/live_autonomy_pilot_20260609/PRE_REGISTRATION.md`

## Outcome

Status: failed, classified.

Layer: `model`

Code: `model_action_missing`

The provider call succeeded and returned a JSON action object. The action
object included `response` and one `schedule_request`, but the required
`open_item` action was rejected because `open_items[0].kind` was missing.

The harness did not infer the missing field and did not apply the partial
schedule. The run stopped after cycle 1 with the failure preserved in
`evaluation.json` and `run_result.json`.

## Budget

Observed usage from the provider response:

- prompt tokens: 272
- completion tokens: 197
- total tokens: 469
- reported cost: USD 0.0008114

This is below the preregistered budget.

## Evidence

- `cycle_01_provider_request.json`
- `cycle_01_provider_response.json`
- `actions.jsonl`
- `evaluation.json`
- `run_result.json`
- `run_manifest.json`
- `sandbox_manifest.json`
- `token_cycle_budget.json`
- `failure_taxonomy.json`

No cycle-2 wake occurred because the required cycle-1 open item was not
accepted.
