# Direct Walk Evidence Gate Pre-Registration

Date: 2026-06-05

## Research Question

Does DeepSeek persist graph-walk evidence into durable state when the same
evidence is delivered as an ordinary direct follow-up rather than as a
scheduled wake event envelope?

The live scheduler walk context gate produced one clean completed DeepSeek wake:
the event sidecar contained a valid `walk(mode="adjacent")` result with four
path entries and zero context errors. The model accurately described the path
in visible prose, but failed to persist the required durable fields and deleted
`walk_gate_status`.

This experiment attacks the confound: was that failure caused by scheduled
re-entry/event-envelope complexity, or is it a broader durable-state update
failure after seeing graph evidence?

## Comparison Baseline

The scheduled baseline is the corrected DeepSeek replicate 2 from:

`experiments/event_loop/live_scheduler_walk_context_gate_20260605/`

Baseline facts:

- model: `deepseek/deepseek-v4-pro`
- event completed: true
- context error count: 0
- event context walk path count: 4
- event context edge types: `depends_on`, `branches_from`, `composes_with`
- durable graph evidence fields persisted: false
- response/state mismatch: true

This experiment does not rerun the scheduled arm. It runs a direct-follow-up arm
against the same model and same graph evidence shape.

## Hypotheses

### H128: Direct follow-up can initialize durable walk-gate state

If the direct arm is interpretable, at least one replicate should pass the same
initialization gate used by the scheduled live gate.

Falsification condition: no direct replicate initializes durable `probe_id`,
`walk_gate_status == "initialized"`, and `observations`.

### H129: Direct follow-up receives equivalent graph evidence

If the direct arm is a valid comparison, the direct prompt should include the
same evidence type as the scheduled wake: an adjacent walk path with four
entries and edge types `depends_on`, `branches_from`, and `composes_with`.

Falsification condition: scorer cannot verify the direct prompt carried those
four path entries and edge types.

### H130: Direct follow-up durably records graph evidence

If the scheduled failure was mainly caused by event-envelope or re-entry
complexity, then direct follow-up should more often persist:

- `walk_gate_status == "woke"`
- `observed_walk_endpoint_count == 4`
- `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
  `composes_with`
- an appended observation about using adjacent walk context.

Falsification condition: no valid direct replicate persists those durable
fields.

### H131: Direct prose/object mismatch is observable

If the model describes the graph evidence in visible prose but fails H130, the
scorer should mark `response_state_mismatch`.

Falsification condition: such a prose/object mismatch appears in logs but is not
scored.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, two direct replicates.

For each replicate:

1. Create an in-memory Apacheta bridge.
2. Project a fixed successful fork-run graph hub into that bridge.
3. Resolve `walk(mode="adjacent", depth=1)` from the fork-run graph record.
4. Run a live initialization cycle requiring durable top-level fields:
   `probe_id`, `walk_gate_status`, `observations`.
5. If initialization is valid, run a direct follow-up prompt containing the
   resolved walk evidence as plain JSON, not as a scheduled event envelope.
6. Score durable state, visible response, and graph-evidence equivalence.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event in the direct arm;
- in-memory bridge only;
- no Arango requirement;
- max tokens bounded at 2048;
- outer process timeout for provider stalls;
- no KIMI run in this experiment because KIMI was censored by repeated provider
  stalls in the preceding gate.

## Expected Result

Expected before running:

- At least one DeepSeek direct replicate initializes valid durable state.
- Direct follow-up may still fail to persist graph-evidence fields. If so, the
  failure is broader than scheduled re-entry and points back to identity-object
  literacy rather than event-loop mechanics.
- If direct succeeds while the scheduled baseline failed, then event-envelope or
  scheduled re-entry complexity becomes the leading cause.

## Evaluation Artifacts

- `run_direct_walk_evidence_gate.py`
- per-replicate session JSONL logs
- `results.json`
- `analysis.md`
