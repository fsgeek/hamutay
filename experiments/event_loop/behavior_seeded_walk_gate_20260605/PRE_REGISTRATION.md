# Behavior Seeded Walk Gate Pre-Registration

Date: 2026-06-05

## Research Question

Can an explicit behavior seed get DeepSeek past the initialization prose/object
mismatch so the direct walk-evidence comparison becomes interpretable?

The direct walk evidence gate failed before its intended follow-up: both
DeepSeek replicates described the requested initialization fields in visible
prose, but durable state contained only framework keys. That means the current
blocker is not graph evidence, direct context, or scheduler machinery. It is
the model's failure to author the top-level identity-object fields at cycle 1.

## Hypotheses

### H132: Behavior seed improves durable initialization

If the failure is partly an object-literacy problem, then a prompt containing an
explicit example of the required output object should produce valid durable
initialization in at least one of two DeepSeek replicates.

Falsification condition: zero seeded replicates persist `probe_id`,
`walk_gate_status == "initialized"`, and `observations` at top level.

### H133: Seeded direct follow-up receives equivalent graph evidence

If initialization succeeds, the direct follow-up should receive the same
adjacent walk evidence shape used in the prior direct gate: four path entries
with edge types `depends_on`, `branches_from`, and `composes_with`.

Falsification condition: any valid initialized replicate lacks equivalent walk
evidence in the direct follow-up prompt.

### H134: Seeded direct follow-up durably records graph evidence

If behavior seeding is enough to make the direct comparison interpretable, at
least one valid seeded replicate should persist:

- `walk_gate_status == "woke"`
- `observed_walk_endpoint_count == 4`
- `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
  `composes_with`
- an appended observation about direct adjacent walk context.

Falsification condition: no valid seeded replicate persists those fields.

### H135: Seeded prose/object mismatch remains observable

If a seeded replicate describes the graph evidence in visible prose but fails
H134, the scorer should mark `response_state_mismatch`.

Falsification condition: such a mismatch appears in logs but is not scored.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, two replicates.

For each replicate:

1. Create an in-memory Apacheta bridge.
2. Project a fixed successful fork-run graph hub into that bridge.
3. Resolve `walk(mode="adjacent", depth=1)` from the fork-run graph record.
4. Run a live initialization cycle with the same required fields as the direct
   gate, but include a behavior seed:

```json
{
  "response": "Initialized.",
  "probe_id": "<exact probe id>",
  "walk_gate_status": "initialized",
  "observations": [{"entry": 1, "kind": "baseline", "content": "..."}]
}
```

5. If initialization is valid, run the same direct walk evidence follow-up used
   by the direct gate.
6. Score durable state, visible response, and graph-evidence equivalence.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event;
- in-memory bridge only;
- max tokens bounded at 2048;
- no KIMI run because KIMI was provider-censored in the scheduler walk gate.

## Expected Result

Expected before running:

- Behavior seeding should improve initialization relative to the unseeded
  direct gate, possibly enough for at least one valid follow-up.
- If the seeded follow-up still fails to persist graph evidence after valid
  initialization, that points to a durable-update failure beyond initial
  object-literacy.

## Evaluation Artifacts

- `run_behavior_seeded_walk_gate.py`
- per-replicate session JSONL logs
- `results.json`
- `analysis.md`
