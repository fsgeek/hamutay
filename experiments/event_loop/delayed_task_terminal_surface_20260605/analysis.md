# Analysis: Delayed-Task Terminal Surface Boundary

Date: 2026-06-05

## Result

The delayed-task terminal-surface boundary panel passed cleanly.

Aggregate:

- rows: 2;
- first-pass compression clean: 2/2;
- schedule valid: 2/2;
- due executed: 2/2;
- recall context delivered: 2/2;
- terminal parse/state-record success: 2/2;
- exact phrase recovered in `delayed_answer`: 2/2;
- final strict state valid: 2/2;
- first-pass due validation valid: 2/2;
- due repair attempted: 0/2;
- terminal surface tool observed: 2/2;
- terminal surface label observed: 2/2;
- bounded wake call violations: 0/2;
- runner/provider errors: 0/2.

Hypothesis outcomes:

- H381 passed.
- H382 passed.
- H383 passed.
- H384 passed.
- H385 passed.

## Comparison To Baseline

The relevant baseline is
`experiments/event_loop/compression_repair_gate_20260605`.

In the compression repair-gate event-plus-recall arm:

- compression clean: 2/2;
- due executed: 2/2;
- fact recovered: 2/2;
- final valid: 2/2;
- first-pass due valid: 1/2;
- due repair: 1/2.

In this terminal-surface delayed-task arm:

- compression clean: 2/2;
- due executed: 2/2;
- fact recovered: 2/2;
- final valid: 2/2;
- first-pass due valid: 2/2;
- due repair: 0/2.

The experimental change was the due-wake protocol surface. The compression and
scheduling scaffold remained aligned with the seeded clean-compression repair
gate, but the scheduled event carried a `terminal_surface` from its initial
pending record. At due time, `OpenTasteSession` used that narrow terminal tool
instead of the broad `think_and_respond` durable-object surface.

## Interpretation

This strengthens the emerging design rule:

- open identity evolution can keep using the broad object surface;
- bounded scheduled-task completion should use a task-specific terminal
  surface.

The result is especially useful because it generalizes the terminal-surface
finding beyond the second-wake chain task. The same design pattern also removed
the due-repair dependency in the delayed/compressed task, where recall is
load-bearing and the durable object should not carry the exact phrase through
the parked state.

This does not prove broad model reliability. It is a small, single-model,
two-replicate boundary test. It does show that the prior due-repair failure was
not inherent to event-plus-recall delayed-task continuity. It was at least
partly a protocol-surface problem.

## Design Implication

The event-loop substrate should treat terminal surfaces as first-class event
metadata for bounded wakes:

- the event declaration should carry the completion schema;
- the wake envelope should expose that terminal surface;
- provider calls should use `tool_choice: auto` by default on
  OpenAI-compatible/OpenRouter routes;
- terminal tool output should be translated into durable state by substrate
  rules;
- strict validators should run on the translated durable object;
- no broad due repair should be attached unless the experiment is explicitly
  testing repair behavior.

This suggests a practical scheduler taxonomy:

1. identity-maintenance events: broad `think_and_respond`;
2. bounded task-completion events: narrow terminal surface;
3. diagnostic/repair events: explicitly marked repair surfaces or repair
   prompts, never silent broad repair.

## Remaining Cautions

The panel is intentionally small. It does not answer:

- whether the same pattern holds across other model families;
- whether models reliably schedule terminal-surface events without scaffolded
  prompts;
- whether multi-event chains remain stable when each wake has its own narrow
  surface;
- whether terminal surfaces can cover less bounded tasks without overfitting
  the schema.

The next boundary worth testing is no longer single delayed recall. It is
multi-event continuity: one event should create a bounded non-secret result
that a later event recalls and combines with the original seed.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/delayed_task_terminal_surface_20260605/run_delayed_task_terminal_surface.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 1200s uv run python experiments/event_loop/delayed_task_terminal_surface_20260605/run_delayed_task_terminal_surface.py
jq '.summary' experiments/event_loop/delayed_task_terminal_surface_20260605/results.json
```

Targeted tests passed: `94 passed`.
