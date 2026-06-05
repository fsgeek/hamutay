# Live Validation Repair Scaffold Pre-Registration

Date: 2026-06-05

## Research Question

Does the newly implemented `OpenTasteSession` validation/repair scaffold
reproduce the external-runner repair finding under live model calls?

The conditioned repair variants showed that DeepSeek repaired a known
prose/object mismatch only when given a complete target durable object. The
validation repair scaffold now makes that policy available inside the session:
validate first-pass state, optionally ask for one repair, validate again, and
log the outcome.

This experiment tests the scaffold itself against the known mismatch state.

## Source Mismatch

Use cycle 2 from:

`experiments/event_loop/strict_repair_walk_gate_20260605/deepseek__deepseek-v4-pro_strict_repair_r04.jsonl`

That state has:

- `walk_gate_status == "initialized"`;
- one baseline observation;
- no `observed_walk_endpoint_count`;
- no `observed_walk_edge_types`;
- no appended `direct_walk` observation.

## Hypotheses

### H158: Built-in validator detects the known mismatch

When the seeded mismatch state is followed by a light repair prompt that does
not provide a full target object, the scaffold validator should detect missing
durable graph-evidence fields whenever the model fails to author them.

Falsification condition: a prose-only first pass lacks required durable fields
but is logged as valid.

### H159: Built-in full-target repair recovers at least one live mismatch

If the scaffold correctly reproduces the external-runner repair boundary, at
least one first-pass mismatch should be repaired by the scaffold's full-target
repair prompt.

Falsification condition: one or more first-pass mismatches occur, but zero are
repaired.

### H160: Repaired scaffold cycles remain auditable

Every repaired cycle should log:

- first-pass validation failure;
- repair raw output;
- repair validation result;
- final `state_validation.status == "repaired"`;
- final durable state containing the required graph-evidence fields.

Falsification condition: a repaired state lacks any of those artifacts.

### H161: Unrepaired scaffold cycles are not silently accepted

If a repair fails, the cycle should be logged as `unrepaired` or
`repair_failed`, not as clean success.

Falsification condition: a failed repair is logged as valid/repaired.

### H162: Repair remains bounded

The scaffold should make at most two backend calls per replicate: one first
pass and one repair.

Falsification condition: any replicate makes more than two backend calls.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, four replicates.

For each replicate:

1. Load the known mismatch state.
2. Seed a new `OpenTasteSession` at cycle 2.
3. Attach a graph-walk state validator.
4. Attach a full-target repair builder.
5. Send a light field-values repair prompt that does not include the complete
   target object.
6. Let the scaffold validate, optionally repair, validate again, and log the
   outcome.

The validator accepts only states with:

- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
  `composes_with`;
- an appended `direct_walk` observation.

The repair builder supplies a complete target object. The harness still does
not mutate state itself; success requires the model to author the fields.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no scheduled event;
- no graph bridge required;
- no memory injection;
- max tokens bounded at 2048;
- one scaffold repair attempt maximum per replicate.

## Expected Result

Expected before running:

- Some first-pass calls should fail in the same prose-only way seen in the
  field-values variant.
- The scaffold should repair at least one such failure with the full-target
  prompt.
- If all first-pass calls succeed, the scaffold repair path will be censored
  rather than falsified.

## Evaluation Artifacts

- `run_live_validation_repair_scaffold.py`
- per-replicate session JSONL logs
- `results.json`
- `analysis.md`
