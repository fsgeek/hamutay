# Live Scheduler Smoke - DeepSeek - 2026-06-03

Purpose: validate the scheduled-event loop against a live OpenRouter model after
adding scheduler observability.

Model/provider:
- `deepseek/deepseek-v4-pro` via OpenRouter
- JSONL only; Apacheta persistence disabled

Result:
- Cycle 1 called `schedule_event` once and waited for the tool result.
- The event sidecar recorded one pending event:
  `4e2385be-9cfa-4c64-95f5-bc57f5ebef00`.
- `hamutay.events run-next` claimed and completed the event as cycle 2.
- The final event report showed:
  - `completed=1`
  - `context_errors=2`
  - one outcome warning: `response/state mismatch`

Findings:
- End-to-end scheduling, event persistence, claiming, wake execution, context
  delivery, and outcome observation worked.
- Field-specific recall failed for `current_claim` and `evidence_register`
  because the cycle-1 model wrapped durable fields under a nested `state`
  object. Full-cycle recall still delivered the data.
- That nested-field issue was fixed in commit `44c0bbf` by allowing recall to
  resolve exact top-level fields first, dotted paths second, and model-nested
  `state` fields as a fallback.
