# Update Exemplar Walk Gate Analysis

Date: 2026-06-05

## Result

The update-time exemplar produced the first durable DeepSeek graph-evidence
write in this branch, but it did not make the behavior reliable.

- H136 update-time exemplar preserves seeded initialization benefit: passed.
- H137 update-time exemplar follow-up receives equivalent graph evidence:
  passed.
- H138 update-time exemplar durably records graph evidence: passed.
- H139 update-time exemplar prose/object mismatch remains observable: passed.

## Scenario Results

### Replicate 1

The model followed the seeded initialization prompt. Durable top-level state
contained:

- `probe_id`
- `walk_gate_status == "initialized"`
- `observations`

The direct follow-up delivered equivalent graph evidence:

- adjacent walk path count: 4
- edge types: `depends_on`, `branches_from`, `composes_with`

With the update-time target object in the prompt, the model persisted the
required graph-evidence fields:

- `walk_gate_status == "woke"`
- `observed_walk_endpoint_count == 4`
- `observed_walk_edge_types` contained `depends_on`, `branches_from`, and
  `composes_with`
- `observations` included an appended `direct_walk` entry

This is the first successful durable walk-evidence update observed for
DeepSeek in the scheduler/direct graph-evidence sequence.

### Replicate 2

The model also followed the seeded initialization prompt. Durable top-level
state contained the same required initialization fields:

- `probe_id`
- `walk_gate_status == "initialized"`
- `observations`

The direct follow-up delivered equivalent graph evidence:

- adjacent walk path count: 4
- edge types: `depends_on`, `branches_from`, `composes_with`

The visible response accurately described the target result:

- four adjacent endpoints;
- `depends_on`, `branches_from`, and `composes_with` edges.

But the durable object did not record the update. The raw output contained only:

- `response`
- `deleted_regions: ["_activity_log"]`

The state therefore remained initialized:

- `walk_gate_status` remained `"initialized"`;
- `observed_walk_endpoint_count` was absent;
- `observed_walk_edge_types` was absent;
- no observation was appended.

This is a clean prose/object mismatch despite a valid initialization, equivalent
graph evidence, and an explicit update-time target object.

## Cross-Gate Comparison

The recent DeepSeek gates show a useful progression:

- unseeded direct walk gate: 0 of 2 replicates passed initialization;
- behavior-seeded walk gate: 1 of 2 replicates passed initialization, 0 of 1
  valid replicates durably recorded graph evidence;
- update-exemplar walk gate: 2 of 2 replicates passed initialization, 1 of 2
  valid replicates durably recorded graph evidence.

The update exemplar changed the result. That rules out a simple "DeepSeek can
never do this" explanation. It also rules out a simple substrate failure:
equivalent graph evidence reached both valid replicates, and one recorded it
durably.

But the second replicate rules out treating the current protocol as stable. The
model can still satisfy the visible answer while failing to update the durable
identity object.

## Interpretation

The active boundary is update-shape literacy. DeepSeek is capable of:

- copying a seeded initialization object into durable state;
- reading direct graph-walk evidence from the prompt;
- verbalizing the graph evidence accurately;
- sometimes copying an update-time target object into durable state.

It is not reliably treating durable state update as the task-completion surface.
In one replicate, the visible response became the only meaningful output, even
though the prompt explicitly supplied the target durable object. This is the
same failure class as the scheduled-wake result and the behavior-seeded direct
result, but now with a positive counterexample beside it.

That makes the event-loop substrate look increasingly viable. The scheduler,
walk context, in-memory graph bridge, and scoring path can all produce
interpretable data. The weaker component is the model/protocol interface for
state-bearing updates.

## Design Implication

The next scaffold should not make the identity object carry every kind of
memory by itself. The evidence supports a split:

- use the event loop and memory graph as the continuity substrate;
- use the identity object as the active self-model and current working stance;
- add protocol support that makes state-bearing updates harder to replace with
  prose-only answers.

One concrete next experiment is a strict update adapter: after a cycle response,
if the model mentions an evidence update in prose but omits required durable
fields, the harness should not silently accept the state. It should either mark
the cycle as failed or run a second, explicit repair turn that shows the model
the mismatch and asks for only the corrected state object. That would test
whether failures are recoverable protocol errors or deeper inability to
maintain the object.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/update_exemplar_walk_gate_20260605/run_update_exemplar_walk_gate.py
timeout 240s uv run python experiments/event_loop/update_exemplar_walk_gate_20260605/run_update_exemplar_walk_gate.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- two of two DeepSeek replicates passed initialization.
- two of two valid replicates received equivalent walk evidence.
- one of two valid replicates durably recorded graph evidence.
- one prose/object mismatch was observed and scored.
- full regression suite: 278 passed.
