# Live Scheduler Walk Context Gate Pre-Registration

Date: 2026-06-05

## Research Question

Can live taste_open instances use explicit `walk(mode="adjacent")` event
context at scheduled wake time to update durable state about a fork-run graph
hub?

The preceding DES established that scheduler `requested_context` can validate,
resolve, and render `walk` evidence. This gate tests the next behavioral
boundary: whether the model receiving the event envelope uses that evidence in
its identity object rather than only in visible prose.

## Models

Small panel:

- `moonshotai/kimi-k2.6`
- `deepseek/deepseek-v4-pro`

Replicates: 2 per model.

Rationale: KIMI has been the most reliable current scheduler candidate.
DeepSeek is included because prior scheduler gates showed operational wake
completion with durable wake-state mismatch, which is exactly the failure mode
this gate should detect.

## Hypotheses

### H124: Live models can schedule a walk-context wake

If scheduler `walk` context is usable through the model-facing tool path, each
valid initialized replicate should produce exactly one persisted scheduled event
whose requested context includes a `walk` request.

Falsification condition: more than one valid replicate per model fails to
persist a walk-context event after valid initialization.

### H125: Event runner resolves walk context without context errors

If scheduler walk context is integrated with the event runner, each persisted
event should complete with zero context errors and an event sidecar containing a
walk result path.

Falsification condition: any completed event has context errors or lacks a walk
path in `context_results`.

### H126: Wake state records graph evidence durably

If the live instance uses the walk evidence rather than merely acknowledging
the wake, the final durable state should include:

- `walk_gate_status == "woke"`
- `observed_walk_endpoint_count == 4`
- `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
  `composes_with`
- an appended observation/finding about the scheduled walk context.

Falsification condition: a completed wake lacks those durable fields, even if
the visible response mentions the graph or walk.

### H127: Prose/object mismatch remains observable

If the gate is instrumented correctly, any visible response claiming the walk
was inspected while durable H126 fields are absent should be scored as
`response_state_mismatch`.

Falsification condition: such a mismatch is present in logs but not scored.

## Experimental Design

For each replicate:

1. Create an in-memory Apacheta bridge.
2. Project a fixed successful fork-run graph hub into that bridge:
   coordinator root, branch-a result, branch-b result, join result.
3. Run a live initialization cycle that creates durable top-level state:
   `probe_id`, `walk_gate_status`, `observations`.
4. Run a live scheduling cycle instructing the model to call `schedule_event`
   exactly once with requested context:

```json
[
  {
    "tool": "walk",
    "from_record_id": "<fork_run_record_id>",
    "direction": "forward",
    "depth": 1,
    "mode": "adjacent"
  }
]
```

5. If exactly one event is persisted, invoke `run_next_event`.
6. Score event sidecar context, final durable state, recursive scheduling, and
   prose/object mismatch.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no Arango requirement;
- in-memory bridge per replicate;
- max tokens bounded at 2048;
- timeout per provider/harness call;
- no broad model sweep.

## Expected Result

Expected before running:

- KIMI passes H124-H127 in at least one replicate and likely both.
- DeepSeek may pass H124-H125 but fail H126 through the previously observed
  prose/object mismatch.

If both models fail before event persistence, the likely conclusion is that the
additional `walk` requested-context shape is still too protocol-fragile for
current live scheduler use.

## Evaluation Artifacts

- `run_live_scheduler_walk_context_gate.py`;
- per-replicate session JSONL logs;
- per-replicate event sidecars;
- `results.json`;
- `analysis.md`.
