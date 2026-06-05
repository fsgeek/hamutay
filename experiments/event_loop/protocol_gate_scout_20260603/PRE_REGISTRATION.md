# Protocol Gate Scout

Filed: 2026-06-03 before writing the runner and before model calls.

## Research Question

Which candidate models are protocol-stable enough for Hamut'ay event-loop
research?

This scout tests only the minimal load-bearing protocol path:

1. initialize durable top-level state;
2. call `schedule_event` with valid requested context;
3. wake once;
4. update durable top-level state at wake time.

## Background

Prior scheduler runs separated several failure modes:

- KIMI K2.6 can complete the scheduler path, but malformed
  `requested_context` attempts can occur before recovery.
- Qwen Plus thinking is a paid OpenRouter route, not a free endpoint, but the
  latest minimal gate was censored by upstream Alibaba 429 rate limiting.
- DeepSeek V4 Pro can schedule and wake, but often describes durable state
  changes without persisting them.

The prior minimal gate may have been too thin: it used one requested context
entry and `max_tokens = 2048`. This scout restores richer context and a larger
repair budget while keeping the wake task simple.

## Hypothesis

Protocol-stable scheduler candidates are uncommon but not unique to KIMI.

More specifically:

1. KIMI K2.6 should pass as the positive control.
2. At least one non-KIMI candidate should pass all four protocol steps.
3. OpenAI's paid open-weight `gpt-oss-120b` route is worth testing because it
   advertises tool support and avoids the free-route availability confound.

## Models

Registered OpenRouter model IDs:

- `moonshotai/kimi-k2.6` positive control
- `minimax/minimax-m2.5`
- `mistralai/mistral-small-2603`
- `google/gemini-2.5-flash-lite`
- `openai/gpt-oss-120b`

## Conditions

- One replicate per model.
- `max_tokens = 4096`.
- OpenRouter paid/non-free routes only.

## Protocol

Each model:

1. Cycle 1 initializes top-level state:
   - `probe_id`
   - `protocol_gate_status == "initialized"`
   - `observations`, list-shaped with one baseline entry
2. The runner validates initialization before continuing.
3. Cycle 2 asks the model to call `schedule_event` exactly once with requested
   context:
   - `{"tool": "recall", "cycle": 1}`
   - `{"tool": "recall", "cycle": 1, "field": "probe_id"}`
   - `{"tool": "recall", "cycle": 1, "field": "observations"}`
4. The runner invokes the event if an event was persisted.
5. The wake must set top-level `protocol_gate_status == "woke"` and append an
   observation.

If initialization is invalid, the replicate stops and is classified as
`initialization_failed`.

## Primary Measures

Per model:

- `init_valid`
- `init_failure_reasons`
- `error`
- `cycle_count`
- `malformed_schedule_attempts`
- `valid_schedule_attempts`
- `event_persisted`
- `event_completed`
- `context_error_count`
- `wake_status_woke`
- `observation_update`
- `response_state_mismatch`
- `stop_reasons`

## Scoring Rules

- A model passes the scout only if initialization is valid, exactly one event is
  persisted, the event completes, final top-level `protocol_gate_status` is
  `"woke"`, and top-level `observations` gains a wake entry.
- Malformed `schedule_event` attempts are not fatal if the model later repairs
  and persists exactly one valid event, but they are recorded.
- Provider 429/availability errors are censored, not behavioral failures.
- A visible claim that the wake completed is a response/state mismatch if the
  durable top-level state does not record `protocol_gate_status == "woke"`.

## Artifact Plan

This directory will contain:

- `PRE_REGISTRATION.md`
- `run_protocol_gate_scout.py`
- per-model JSONL logs
- event sidecars when events are persisted
- `results.json`
- `analysis.md`
