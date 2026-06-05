# Conditioned Repair Variants Pre-Registration

Date: 2026-06-05

## Research Question

When the initialization and mismatch-generation confounds are removed, which
repair prompt shapes can make DeepSeek author the missing graph-evidence update
into durable state?

The strict-repair gate showed one successful repair after a complete target
object was supplied. The missing-field repair gate was censored because no
replicate reached the repair condition. This experiment conditions directly on
a known mismatch state and compares repair prompt variants.

## Source Mismatch

Use the preserved mismatch state from:

`experiments/event_loop/strict_repair_walk_gate_20260605/deepseek__deepseek-v4-pro_strict_repair_r04.jsonl`

Specifically, cycle 2:

- visible response says graph-walk evidence was recorded;
- durable state still has `walk_gate_status == "initialized"`;
- `observed_walk_endpoint_count` is absent;
- `observed_walk_edge_types` is absent;
- no `direct_walk` observation has been appended.

Each repair run seeds this state with `OpenTasteSession.seed_state(state,
cycle=2)`, then runs exactly one repair cycle.

## Variants

Run `deepseek/deepseek-v4-pro`, two replicates per variant.

### Variant A: Full Target Object

The repair prompt includes the current state, missing fields, evidence summary,
and a complete target durable object.

### Variant B: Field Values

The repair prompt includes the current state, missing fields, evidence summary,
and expected field-level values, but not a complete target object.

### Variant C: Field Names Only

The repair prompt includes the current state, missing field names, and evidence
summary, but not a complete target object and not a JSON object containing the
expected values.

## Hypotheses

### H148: Conditioned full-target repair recovers reliably

If the strict-repair success was not a fluke, both full-target replicates should
persist the required durable graph-evidence update.

Falsification condition: any full-target replicate fails to persist the update.

### H149: Conditioned field-values repair can recover

If repair does not require a complete target object, at least one field-values
replicate should persist the required durable graph-evidence update.

Falsification condition: zero field-values replicates persist the update.

### H150: Conditioned field-names-only repair can recover

If evidence summary plus missing field names is enough, at least one
field-names-only replicate should persist the required durable graph-evidence
update.

Falsification condition: zero field-names-only replicates persist the update.

### H151: Repair success preserves prior identity fields

Every successful repair, regardless of variant, must preserve `probe_id` and
the baseline observation.

Falsification condition: any successful repair loses `probe_id` or the baseline
observation.

### H152: Variant outcomes are auditable

The result artifact must record, per replicate:

- variant;
- seeded source state;
- missing fields;
- repair prompt class;
- durable repair success;
- visible repair prose without durable success.

Falsification condition: a replicate reaches one of those states but the result
artifact does not record it.

## Experimental Design

For each variant and replicate:

1. Load the known mismatch source log.
2. Extract cycle 2 durable state.
3. Seed a new `OpenTasteSession` at cycle 2 with that state.
4. Run one repair prompt for the selected variant.
5. Score success only if the final durable state contains:
   - `walk_gate_status == "woke"`;
   - `observed_walk_endpoint_count == 4`;
   - `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
     `composes_with`;
   - an appended `direct_walk` observation.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event;
- no graph bridge required in the repair session;
- no memory injection;
- max tokens bounded at 2048;
- one repair cycle per replicate.

## Expected Result

Expected before running:

- Full-target repair should recover at least one replicate and may recover
  both.
- Field-values repair may recover if explicit field-level instruction is
  enough.
- Field-names-only repair is expected to be weaker; success would be evidence
  that the model can reconstruct the required object from mismatch awareness
  and evidence summary alone.

## Evaluation Artifacts

- `run_conditioned_repair_variants.py`
- per-variant session JSONL logs
- `results.json`
- `analysis.md`
