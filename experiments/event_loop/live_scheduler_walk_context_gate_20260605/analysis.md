# Live Scheduler Walk Context Gate Analysis

Date: 2026-06-05

## Result

The live gate produced one interpretable completed scheduled-walk wake and
several useful failure/censoring observations.

- H124 live models can schedule a walk-context wake: partially supported for
  DeepSeek; KIMI was censored by provider/harness stalls.
- H125 event runner resolves walk context without context errors: passed for
  the one completed DeepSeek wake.
- H126 wake state records graph evidence durably: failed.
- H127 prose/object mismatch remains observable: passed.

## Preserved Corrections And Censoring

### Stale schema/prompt confound

The first live run exposed a substrate bug before the intended behavioral
question was interpretable. The validator accepted scheduler `walk` context,
but the model-facing surfaces were stale:

- the system prompt described scheduled event context as `recall/compare`;
- the `schedule_event` tool schema enum listed only `recall` and `compare`.

Those outputs are preserved with `before_schema_prompt_fix_` prefixes. The
schema and prompt were corrected before the final live DeepSeek run.

### KIMI provider/harness stall

KIMI initialized valid durable state in the first attempt, then stalled during
the scheduling cycle. A retry reproduced the stall. After the schema/prompt
fix, KIMI replicate 1 again exceeded the outer 150s process timeout during the
provider/harness call.

Preserved logs:

- `aborted_provider_stall_moonshotai__kimi-k2.6_r01.jsonl`
- `aborted_provider_stall_retry_moonshotai__kimi-k2.6_r01.jsonl`
- `post_schema_prompt_fix_provider_timeout_moonshotai__kimi-k2.6_r01.jsonl`

KIMI is therefore censored for this gate, not scored as a model-behavior
failure.

## Corrected DeepSeek Results

### Replicate 1

DeepSeek failed the initialization gate. The visible response claimed the state
was initialized, but the durable object contained only framework keys. No
schedule attempt was run.

Failure class: initialization prose/object mismatch.

### Replicate 2

DeepSeek initialized valid durable state, scheduled exactly one walk-context
event, and the event runner completed the wake.

Scheduler/event observations:

- valid schedule attempts: 1
- walk-context event count: 1
- event completed: true
- context error count: 0
- event context walk path count: 4
- event context edge types: `depends_on`, `branches_from`, `composes_with`

The wake response accurately verbalized the graph evidence:

- 4 adjacent path entries;
- 3 distinct edge types;
- the expected edge types.

But the durable state failed the required update:

- `walk_gate_status` was deleted rather than set to `"woke"`;
- `observed_walk_endpoint_count` was not persisted;
- `observed_walk_edge_types` was not persisted;
- no new observation was appended.

This is the cleanest live finding in the gate: the substrate delivered the
walk evidence, the model read it well enough to describe it, and the identity
object still failed to carry the result forward.

## Interpretation

The deterministic substrate result was not an illusion. In the completed
DeepSeek wake, `requested_context` carried `walk(mode="adjacent")`, the event
runner resolved it through the in-memory graph bridge, and the sidecar preserved
the result with zero context errors.

The failure moved from substrate mechanics to model behavior. The completed
wake demonstrates a familiar boundary: visible response competence does not
imply durable identity-object update. In fact, this case is sharper than prior
prose/object mismatch observations because the model did not merely omit the
new fields; it also listed `walk_gate_status` in `deleted_regions`.

The model behaved as if saying "woke" was enough. The harness correctly scored
that as insufficient.

## Design Implication

Scheduler walk context is now viable as a substrate feature, but live behavioral
work remains gated by identity-object literacy. The next experiment should not
try to add more graph machinery. It should attack the durable-update boundary:

- simplify the wake instruction shape;
- add an explicit behavior seed for state update;
- or compare tool-result evidence delivered through the event envelope against
  the same evidence delivered in an ordinary direct follow-up.

The useful research question is now whether the failure is caused by scheduled
re-entry, event-envelope complexity, or the more general mismatch between
visible answer generation and durable self-state update.

## Verification

Commands run:

```bash
uv run python -m py_compile src/hamutay/taste_open.py src/hamutay/tools/schemas.py tests/unit/test_events.py experiments/event_loop/live_scheduler_walk_context_gate_20260605/run_live_scheduler_walk_context_gate.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 150s env MODEL_FILTER='moonshotai/kimi-k2.6' REPLICATE_FILTER=1 uv run python experiments/event_loop/live_scheduler_walk_context_gate_20260605/run_live_scheduler_walk_context_gate.py
MODEL_FILTER='deepseek/deepseek-v4-pro' uv run python experiments/event_loop/live_scheduler_walk_context_gate_20260605/run_live_scheduler_walk_context_gate.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- focused tests: 73 passed.
- KIMI post-fix run exited with timeout code 124.
- DeepSeek corrected run completed two replicates.
- One DeepSeek replicate completed a walk-context scheduled wake with zero
  context errors.
- full regression suite: 278 passed.
