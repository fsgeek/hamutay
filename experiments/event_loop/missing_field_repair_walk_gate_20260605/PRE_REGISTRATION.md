# Missing-Field Repair Walk Gate Pre-Registration

Date: 2026-06-05

## Research Question

Does DeepSeek need a full target durable object to repair a prose/object
mismatch, or can it repair from a lighter adapter prompt that names only the
current state, missing fields, and evidence summary?

The strict-repair walk gate showed that one prose/object mismatch was
recoverable when the repair turn supplied a complete target object. That is a
useful existence proof, but it is not yet a practical adapter result. A full
target object may simply make the task a copy operation.

This experiment tests whether a lighter missing-field repair prompt is enough.

## Hypotheses

### H144: Missing-field repair gate produces at least one initial mismatch

If the setup remains comparable to the strict-repair and update-exemplar gates,
at least one valid initialized replicate should produce a visible
graph-evidence response without the corresponding durable update.

Falsification condition: no valid initialized replicate produces an initial
prose/object mismatch.

### H145: Missing-field repair can recover at least one mismatch

If recovery does not require a full target object, then at least one initially
mismatched replicate should persist the required durable graph-evidence fields
after a repair prompt that does not include the full target object.

Falsification condition: zero initially mismatched replicates persist the
required fields after missing-field repair.

### H146: Missing-field repair preserves prior identity fields

If missing-field repair is usable as a scaffold policy, a successful repair
must preserve `probe_id` and the baseline observation while adding graph
evidence.

Falsification condition: any successful repair loses `probe_id` or the
baseline observation.

### H147: Missing-field repair outcomes distinguish copy-dependence

If the result is to inform adapter design, the artifact must distinguish:

- first-follow-up success;
- first-follow-up mismatch;
- repair attempted;
- repair succeeded;
- repair failed despite visible repair prose.

Falsification condition: a replicate reaches one of those states but the result
artifact does not record it.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, four replicates.

For each replicate:

1. Create an in-memory Apacheta bridge.
2. Project the fixed fork-run graph used by the prior walk gates.
3. Resolve `walk(mode="adjacent", depth=1)` from the fork-run graph record.
4. Run the same seeded initialization used by the strict-repair gate.
5. If initialization is valid, run the same direct follow-up with graph
   evidence and update-time target object.
6. If the follow-up response mentions graph evidence but durable state does not
   record it, run one missing-field repair turn.

The missing-field repair turn will include:

- the current durable state;
- the names of missing or incorrect fields;
- a short evidence summary;
- the expected field-level values.

The missing-field repair turn will not include a complete target object and
will not include the full prior evidence JSON.

No mainline harness behavior changes are made in this experiment.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event;
- in-memory bridge only;
- max tokens bounded at 2048;
- same graph evidence shape as the strict-repair gate;
- one repair attempt maximum per replicate.

## Expected Result

Expected before running:

- At least one replicate may mismatch, based on the prior two gates.
- If repair mainly depends on mismatch awareness plus field-level instruction,
  missing-field repair should recover at least one mismatch.
- If strict repair succeeded mainly because the model copied the full target
  object, missing-field repair should fail or produce another prose/object
  mismatch.

## Evaluation Artifacts

- `run_missing_field_repair_walk_gate.py`
- per-replicate session JSONL logs
- `results.json`
- `analysis.md`
