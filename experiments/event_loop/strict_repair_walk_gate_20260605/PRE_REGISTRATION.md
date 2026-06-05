# Strict Repair Walk Gate Pre-Registration

Date: 2026-06-05

## Research Question

When a model accurately describes graph-walk evidence in visible prose but
fails to persist the corresponding durable identity-object update, is the
failure recoverable by a strict repair turn?

The update-exemplar walk gate showed a split result for
`deepseek/deepseek-v4-pro`: both replicates initialized validly and received
equivalent graph evidence, but only one of two durably recorded that evidence.
The failed replicate emitted the correct visible response while leaving the
state unchanged.

This experiment tests whether that failure is a recoverable protocol error or
a more stable inability to treat the durable object as the completion surface.

## Hypotheses

### H140: Repair gate produces at least one initial prose/object mismatch

If the setup remains comparable to the update-exemplar gate, at least one
replicate should produce a graph-evidence response without the corresponding
durable state update.

Falsification condition: every valid initialized replicate either records the
graph evidence durably on the first follow-up or fails before the mismatch can
be observed.

### H141: Strict repair turn can recover at least one mismatch

If the failure is a recoverable protocol-shape error, then at least one
replicate that initially shows a prose/object mismatch should persist the
required graph-evidence fields after a repair turn that explicitly names the
mismatch and supplies the target durable object.

Falsification condition: zero initially mismatched replicates persist the
required fields after repair.

### H142: Repair does not erase prior durable identity fields

If repair is usable as a scaffold policy, a successful repair must preserve the
existing `probe_id` and prior baseline observation while adding the graph
evidence update.

Falsification condition: any successful repair loses `probe_id` or the
baseline observation.

### H143: Repair outcomes remain auditable

If the adapter concept is useful for research, the runner must preserve whether
each replicate was:

- initialized;
- given equivalent walk evidence;
- initially mismatched;
- repair-attempted;
- repair-succeeded;
- still mismatched after repair.

Falsification condition: a replicate reaches one of those states but the result
artifact does not record it.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, four replicates.

For each replicate:

1. Create an in-memory Apacheta bridge.
2. Project the fixed fork-run graph used by the prior walk gates.
3. Resolve `walk(mode="adjacent", depth=1)` from the fork-run graph record.
4. Run the same seeded initialization used in the update-exemplar gate.
5. If initialization is valid, run the same direct follow-up with graph
   evidence and update-time target object.
6. If the follow-up response mentions the graph evidence but durable state does
   not record it, run one strict repair turn.

The repair turn will:

- name the exact mismatch;
- show the current durable state;
- show the missing required fields;
- show the target durable object;
- instruct the model not to call perception, memory, shell, or scheduler
  tools;
- end with `think_and_respond`.

No mainline harness behavior changes are made in this experiment. The repair
adapter is simulated by the runner so that the experiment can decide whether
implementation is worth doing.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event;
- in-memory bridge only;
- max tokens bounded at 2048;
- same graph evidence shape as the update-exemplar gate;
- one repair attempt maximum per replicate.

## Expected Result

Expected before running:

- Some replicates may succeed on the first update, as in the update-exemplar
  gate.
- At least one replicate may mismatch before repair.
- If the mismatch is mainly an instruction/protocol-shape failure, the repair
  turn should recover at least one mismatch.
- If repair fails consistently, the scaffold should not use a naive repair
  adapter; it should instead move toward stricter schema enforcement or model
  selection/training.

## Evaluation Artifacts

- `run_strict_repair_walk_gate.py`
- per-replicate session JSONL logs
- `results.json`
- `analysis.md`
