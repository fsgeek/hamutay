# Minimal Scheduler Tool Gate

Filed: 2026-06-03 before writing the runner and before running model calls.

## Research Question

Did Qwen Plus thinking fail the scheduler revision model panel because it cannot
reliably use the `schedule_event` plus terminal `think_and_respond` tool path,
or because the scheduler revision prompt combined too many requirements?

## Background

The registered scheduler revision model panel found:

- KIMI K2.6 initialized durable state and completed both scheduled wakes.
- Qwen Plus thinking initialized durable state in all replicates, but failed
  both scheduled replicates before event persistence with:
  `RuntimeError: OpenAI backend: no tool_calls returned before think_and_respond`
- DeepSeek V4 Pro mostly failed the initialization gate, but completed one
  scheduled wake after valid initialization.

This gate removes the epistemic-revision task. The model only has to schedule a
single reflection event and then the wake only has to record that it woke.

## Hypothesis

Qwen's previous scheduler failure is prompt-complexity sensitive, not a hard
inability to use `schedule_event`.

More specifically:

1. KIMI should pass this minimal scheduler gate in both replicates.
2. Qwen Plus thinking should pass at least one of two replicates if the prior
   failure was caused by prompt complexity.
3. If Qwen fails both replicates with the same no-terminal-tool-call error, it
   should be treated as scheduler-ineligible for current event-loop work even
   though it passed the identity-object literacy panel.
4. DeepSeek remains a boundary control. It may fail initialization, but if it
   initializes valid state it should be scored for scheduler completion.

## Falsification Conditions

The prompt-complexity hypothesis is weakened if:

- Qwen Plus thinking fails both valid scheduled replicates before event
  persistence.
- Qwen Plus thinking emits prose saying scheduling happened while no
  `schedule_event` result is persisted.
- KIMI fails either replicate, suggesting the minimal prompt or runner is
  flawed rather than Qwen-specific.

The hypothesis is strengthened if Qwen completes at least one scheduled wake
with event persistence, event completion, and a durable wake status update.

## Models

Registered OpenRouter model IDs:

- `moonshotai/kimi-k2.6`
- `qwen/qwen-plus-2025-07-28:thinking`
- `deepseek/deepseek-v4-pro`

## Replicates

- 2 replicates per model.
- 6 total registered replicate slots.
- `max_tokens = 2048`.

## Protocol

Each replicate:

1. Cycle 1 initializes a compact top-level state:
   - `probe_id`
   - `scheduler_gate_status == "initialized"`
   - `observations`, list-shaped with one baseline entry
2. The runner validates initialization before continuing.
3. Cycle 2 asks the model to call `schedule_event` with a simple requested
   context: recall cycle 1.
4. After the `schedule_event` tool result returns, the model must end with
   `think_and_respond`.
5. The runner invokes the next event.
6. The wake cycle must set `scheduler_gate_status == "woke"` and append an
   observation.

If initialization is invalid, the replicate is classified as
`initialization_failed` and no schedule call is attempted.

## Primary Measures

Per replicate:

- `model`
- `replicate`
- `init_valid`
- `init_failure_reasons`
- `error`
- `cycle_count`
- `schedule_cycle_recorded`
- `schedule_tool_recorded`
- `event_persisted`
- `event_completed`
- `context_error_count`
- `wake_status_woke`
- `observation_update`
- `response_state_mismatch`
- `recursive_scheduling_count`

## Scoring Rules

- Initialization is valid only if `probe_id` is top-level,
  `scheduler_gate_status == "initialized"`, and `observations` is a non-empty
  list.
- `schedule_tool_recorded` is true only if cycle logs contain exactly one
  scheduled event.
- `event_completed` is true only if the event sidecar records a completed
  event.
- `wake_status_woke` is true only if the final top-level
  `scheduler_gate_status` is exactly `"woke"`.
- `observation_update` is true only if top-level `observations` remains
  list-shaped and has more entries than the baseline.
- `response_state_mismatch` is true if visible text says the gate woke or
  completed but the durable top-level state does not record wake status.

## Artifact Plan

This directory will contain:

- `PRE_REGISTRATION.md`
- `run_scheduler_tool_gate.py`
- per-replicate JSONL session logs
- per-replicate event sidecars when events are persisted
- `results.json`
- `analysis.md`
