# Scheduled Walk Validation Repair Pre-Registration

Date: 2026-06-05

## Research Question

Does the validation/repair scaffold let us return to scheduled graph-walk wakes
without prose/object mismatch dominating the result?

Earlier live scheduled-walk work showed that the scheduler and graph substrate
could deliver adjacent walk context, but DeepSeek often described the evidence
in visible prose while failing to persist it into durable state. The new
validation/repair scaffold can classify and repair that failure inside
`OpenTasteSession`.

This experiment applies the scaffold to the scheduled wake itself.

## Hypotheses

### H163: Scheduled walk context still resolves under scaffolded wake

For every valid initialized replicate that schedules a walk-context wake and
reaches the wake, the event runner should resolve adjacent walk context with
four path entries and no context errors.

Falsification condition: a completed wake lacks the four-entry walk path or has
context errors.

### H164: Scaffolded wake records durable graph evidence

For every completed scaffolded wake, the final durable state should contain:

- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
  `composes_with`;
- an appended observation about scheduled adjacent walk context.

Falsification condition: any completed wake lacks the durable graph-evidence
fields after validation/repair.

### H165: Scaffold distinguishes first-pass success from repaired success

Completed wakes should preserve whether graph evidence was recorded on the
first pass or only after repair.

Falsification condition: repaired wakes lack `state_validation.first_pass` or
first-pass successes lack `state_validation.status == "valid"`.

### H166: Scaffold repair is bounded during scheduled wakes

The scaffold should make at most one repair call per wake.

Falsification condition: any wake uses more than one repair call or otherwise
recursively repairs.

### H167: Unrepaired scheduled wake failures are not silently accepted

If a scheduled wake fails first-pass validation and repair also fails, the log
must mark it as `unrepaired` or `repair_failed`, not as clean success.

Falsification condition: a failed wake is logged as valid/repaired.

## Experimental Design

Run `deepseek/deepseek-v4-pro`, four replicates.

For each replicate:

1. Build the same in-memory fork-run graph used by the prior walk gates.
2. Run a behavior-seeded initialization cycle:
   - `probe_id`;
   - `walk_gate_status == "initialized"`;
   - baseline `observations`.
3. Run a scheduling cycle that calls `schedule_event` exactly once with
   `requested_context`:
   - `tool == "walk"`;
   - `from_record_id == fork_run_record_id`;
   - `direction == "forward"`;
   - `depth == 1`;
   - `mode == "adjacent"`.
4. Attach the graph-walk validator and full-target repair builder before
   running the pending event.
5. Run the scheduled wake through `run_next_event`.
6. Score the completed wake using final durable state, event context, and
   `state_validation` metadata.

The validator is active only for the wake cycle, so initialization and
scheduling are not repaired as graph-evidence cycles.

Conditions:

- OpenRouter OpenAI-compatible endpoint;
- no KIMI arm in this gate, because prior KIMI scheduled runs were censored by
  provider/harness stalls;
- in-memory Apacheta bridge;
- max tokens bounded at 2048;
- one repair attempt maximum per wake.

## Expected Result

Expected before running:

- Some replicates may still be censored by initialization or scheduling
  failures.
- For completed wakes, the event context should resolve cleanly.
- At least one completed wake may need scaffold repair.
- If scaffold repair works in the scheduled setting, completed wakes should end
  with durable graph-evidence state while preserving first-pass failure
  metadata when applicable.

## Evaluation Artifacts

- `run_scheduled_walk_validation_repair.py`
- per-replicate session JSONL logs
- event sidecar logs
- `results.json`
- `analysis.md`
