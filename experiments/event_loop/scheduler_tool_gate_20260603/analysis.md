# Minimal Scheduler Tool Gate Analysis

Analyzed: 2026-06-03 after the registered run completed.

## Provenance

- Pre-registration commit: `def9297` (`a68d67f` OTS stamp)
- Runner commit: `c339248` (`e81e15f` OTS stamp)
- Results file: `results.json`
- Runner: `run_scheduler_tool_gate.py`

This analysis follows the registered scoring rules in `PRE_REGISTRATION.md`.

## Executive Result

This run did not answer the intended Qwen question because Qwen Plus thinking
was upstream rate-limited in both replicates. It should not be used as evidence
that Qwen can or cannot pass the minimal scheduler tool path.

The run still produced useful scheduler-boundary data:

- KIMI K2.6 passed one of two replicates. The failed replicate repeatedly
  emitted malformed `schedule_event` context (`{"tool": "recall"}` with the
  required `cycle: 1` omitted), then terminated without an event.
- DeepSeek V4 Pro passed event scheduling and event completion in both
  replicates, but both wakes failed to update durable top-level wake state even
  while the visible response claimed the update had been made.
- Qwen Plus thinking was rate-limited by the upstream provider, once after a
  valid initialization and once before any cycle record was written.

The cleanest conclusion is that the scheduler gate has at least three separable
failure surfaces: malformed scheduling arguments, provider availability, and
wake-time prose/object mismatch.

## Aggregate Results

| Model | N | Init valid | Errors | Schedule tool recorded | Event completed | Wake status woke | Observation update | Response/state mismatches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| KIMI K2.6 | 2 | 2 | 0 | 1 | 1 | 1 | 1 | 0 |
| Qwen Plus thinking | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| DeepSeek V4 Pro | 2 | 2 | 0 | 2 | 2 | 0 | 0 | 2 |

Per replicate:

| Model | Replicate | Init valid | Error | Schedule recorded | Event completed | Woke state | Observation update | Mismatch |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| KIMI K2.6 | 1 | true | none | false | false | false | false | false |
| KIMI K2.6 | 2 | true | none | true | true | true | true | false |
| Qwen Plus thinking | 1 | true | upstream 429 after init | false | false | false | false | false |
| Qwen Plus thinking | 2 | false | upstream 429 before record | false | false | false | false | false |
| DeepSeek V4 Pro | 1 | true | none | true | true | false | false | true |
| DeepSeek V4 Pro | 2 | true | none | true | true | false | false | true |

## Falsification Checks

Registered condition: Qwen Plus thinking fails both valid scheduled replicates
before event persistence.

Observed: not interpretable. Qwen did not produce two valid scheduled
replicates. Both failures were provider 429s from the upstream Alibaba route.

Registered condition: Qwen Plus thinking emits prose saying scheduling happened
while no `schedule_event` result is persisted.

Observed: not evaluated. Qwen did not reach a scheduling response.

Registered condition: KIMI fails either replicate, suggesting the minimal prompt
or runner is flawed rather than Qwen-specific.

Observed: triggered. KIMI replicate 1 initialized valid state but failed to
persist an event after repeated malformed `schedule_event` calls. KIMI
replicate 2 passed fully, so the runner is not wholly broken, but the minimal
prompt is less robust than expected.

Registered strengthening condition: Qwen completes at least one scheduled wake
with event persistence, event completion, and durable wake status update.

Observed: not met due upstream rate limits.

## Failure Modes

### KIMI malformed requested_context before recovery

KIMI replicate 1 made seven `schedule_event` attempts. Each attempt omitted the
required locator from the requested context and passed:

`{"tool": "recall"}`

The scheduler correctly rejected each attempt with:

`recall context requires exactly one of cycle or record_id`

The visible response accurately reported that no event id was returned. This was
not a prose/object mismatch. It was a scheduling-argument formation failure.

KIMI replicate 2 emitted the correct shape, persisted an event, completed the
wake, set `scheduler_gate_status` to `"woke"`, and appended a wake observation.

This matters because earlier scheduler-revision runs also show KIMI sometimes
making malformed `requested_context` attempts before eventually correcting
itself. The minimal gate used `max_tokens = 2048`; the prior revision panel used
`max_tokens = 4096`. The failed replicate may have run out of effective repair
budget before discovering the valid shape.

### Qwen upstream rate limit

Qwen replicate 1 initialized valid state, then failed before a scheduling cycle
was recorded with an upstream 429:

`qwen/qwen-plus-2025-07-28:thinking is temporarily rate-limited upstream`

Qwen replicate 2 failed before any cycle record was written with the same 429.

This invalidates the run for the intended Qwen scheduler-tool question. The
result should be treated as missing data, not model behavior.

### DeepSeek event completion without durable wake update

DeepSeek initialized valid state in both replicates, persisted one event per
replicate, and completed both wakes. The event sidecars include successful
pending, running, and completed records with context resolved.

However, the wake cycles did not set durable top-level
`scheduler_gate_status == "woke"` and did not append the requested wake
observation. In both replicates, the visible response claimed the update had
been made while the persisted state did not contain it.

This is a clean prose/object mismatch at wake time. It differs from the earlier
DeepSeek failure where requested fields were placed in visible response text
during initialization. Here the model can use the scheduler path but still fails
the load-bearing identity-object update at the wake.

## Interpretation

The intended binary question was:

- If Qwen passes the minimal gate, the prior failure was probably prompt
  complexity.
- If Qwen fails the minimal gate, Qwen is probably scheduler-ineligible for now.

The observed run cannot answer that because Qwen was rate-limited.

The unplanned but useful result is a sharper decomposition of scheduler
competence:

1. Can the model initialize durable top-level state?
2. Can the model form valid `schedule_event` arguments?
3. Can the model persist an event and receive a wake?
4. Can the wake update durable top-level state rather than only describing the
   update?

KIMI mostly satisfies all four, but argument formation is not deterministic
under the minimal prompt. DeepSeek satisfies 1 through 3 in this gate, but fails
4. Qwen remains unknown for 2 through 4 in this run.

## Limitations

- Qwen data is censored by provider rate limits.
- The KIMI failure means this prompt is not a clean positive-control gate.
- `max_tokens = 2048` may be too low for models that require several malformed
  tool attempts before repair.
- The prompt used a single requested context entry. Prior successful scheduler
  prompts used richer context and a longer purpose; the minimal prompt may have
  unintentionally reduced tool-argument anchoring.

## Next Registered Direction

The next run should be a repaired scheduler tool gate:

1. Use `max_tokens = 4096`.
2. Include three requested context entries, matching the successful scheduler
   revision prompt shape:
   - `{"tool": "recall", "cycle": 1}`
   - `{"tool": "recall", "cycle": 1, "field": "probe_id"}`
   - `{"tool": "recall", "cycle": 1, "field": "observations"}`
3. Keep the wake task simple.
4. Treat provider 429s as censored/missing and either retry within a registered
   retry rule or defer Qwen until the upstream route is available.
5. Score malformed intermediate schedule attempts separately from final event
   persistence.

This repaired gate would test whether context richness and repair budget are
the actual determinants of scheduler-tool success.
