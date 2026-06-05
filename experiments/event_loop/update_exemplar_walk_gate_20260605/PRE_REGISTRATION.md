# Update Exemplar Walk Gate Pre-Registration

Date: 2026-06-05

## Research Question

Can an explicit update-time target object make DeepSeek persist graph-walk
evidence into durable state after a valid seeded initialization?

The behavior-seeded walk gate showed that a first-cycle behavior seed can get
DeepSeek past initialization in at least one replicate. But the valid replicate
still failed the graph-evidence update: it accurately described the four
adjacent walk endpoints in visible prose while leaving durable state unchanged.

This experiment tests whether the missing ingredient is an exemplar at the
update moment itself.

## Hypotheses

### H136: Update-time exemplar preserves seeded initialization benefit

If the setup remains comparable, at least one DeepSeek replicate should pass
the seeded initialization gate.

Falsification condition: zero replicates persist `probe_id`,
`walk_gate_status == "initialized"`, and `observations` at top level.

### H137: Update-time exemplar follow-up receives equivalent graph evidence

If the update-time exemplar arm is interpretable, every valid initialized
replicate should receive equivalent adjacent walk evidence: four path entries
with edge types `depends_on`, `branches_from`, and `composes_with`.

Falsification condition: any valid initialized replicate lacks equivalent walk
evidence.

### H138: Update-time exemplar durably records graph evidence

If DeepSeek's failure is caused mainly by missing update-shape instruction, then
at least one valid replicate should persist:

- `walk_gate_status == "woke"`
- `observed_walk_endpoint_count == 4`
- `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
  `composes_with`
- an appended observation about using direct adjacent walk context.

Falsification condition: no valid initialized replicate persists those fields.

### H139: Update-time exemplar prose/object mismatch remains observable

If a replicate describes graph evidence in visible prose but fails H138, the
scorer should mark `response_state_mismatch`.

Falsification condition: such a mismatch appears in logs but is not scored.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, two replicates.

For each replicate:

1. Create an in-memory Apacheta bridge.
2. Project a fixed successful fork-run graph hub into that bridge.
3. Resolve `walk(mode="adjacent", depth=1)` from the fork-run graph record.
4. Run the same behavior-seeded initialization used in the prior gate.
5. If initialization is valid, run a direct follow-up containing the resolved
   walk evidence plus an explicit target object shape:

```json
{
  "response": "Walk evidence recorded.",
  "walk_gate_status": "woke",
  "observed_walk_endpoint_count": 4,
  "observed_walk_edge_types": ["depends_on", "branches_from", "composes_with"],
  "observations": [
    {"entry": 1, "kind": "baseline", "content": "..."},
    {"entry": 2, "kind": "direct_walk", "content": "..."}
  ]
}
```

The target object should include the exact replicate `probe_id` as well.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event;
- in-memory bridge only;
- max tokens bounded at 2048;
- same graph evidence shape as the seeded and scheduled gates.

## Expected Result

Expected before running:

- At least one replicate should initialize validly, as in the behavior-seeded
  gate.
- The update-time exemplar may improve durable graph-evidence persistence. If
  it does, this points to an update-shape literacy problem. If it does not, the
  failure is stronger: the model can copy initialization examples but still
  treats evidence-response generation as sufficient completion.

## Evaluation Artifacts

- `run_update_exemplar_walk_gate.py`
- per-replicate session JSONL logs
- `results.json`
- `analysis.md`
