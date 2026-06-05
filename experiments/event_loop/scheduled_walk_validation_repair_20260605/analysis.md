# Scheduled Walk Validation Repair Analysis

Date: 2026-06-05

## Result

The scheduled graph-walk wake gate succeeded under the validation/repair
scaffold, but exposed a narrower validator-contract problem.

- H163 scheduled walk context still resolves under scaffolded wake: passed.
- H164 scaffolded wake records durable graph evidence: passed.
- H165 scaffold distinguishes first-pass success from repaired success: passed.
- H166 scaffold repair is bounded during scheduled wakes: passed.
- H167 unrepaired scheduled wake failures are not silently accepted: passed.

All four replicates initialized, scheduled a walk-context wake, completed the
wake, received four-entry adjacent walk context, failed first-pass wake
validation, and were repaired by the scaffold.

## Scenario Results

### Shared Substrate Result

Each replicate produced exactly one scheduled event with requested context:

- `tool == "walk"`;
- `direction == "forward"`;
- `depth == 1`;
- `mode == "adjacent"`.

Each event sidecar contains:

- `pending`;
- `running`;
- `completed`;
- `context_results` with four walk path entries;
- edge types `depends_on`, `branches_from`, and `composes_with`;
- zero context errors.

### Wake Result

Every completed wake had:

- `state_validation.first_pass.status == "invalid"`;
- `state_validation.status == "repaired"`;
- `state_validation.repair.status == "valid"`;
- final durable graph-evidence fields:
  - `walk_gate_status == "woke"`;
  - `observed_walk_endpoint_count == 4`;
  - `observed_walk_edge_types` containing `depends_on`, `branches_from`, and
    `composes_with`;
  - a `scheduled_walk` observation.

Each wake used two backend calls: first pass plus one scaffold repair. No wake
used more than one repair call.

## Important Caveat

The graph-evidence validator accepted some repairs that were not continuity
clean:

- Replicate 1 lost the baseline observation during scheduling and the repair
  preserved only the scheduled-walk observation.
- Replicate 1's repair output included `cycle: 4`, so the durable state cycle
  diverged from the log record's wake cycle 3.
- Replicate 4 changed `probe_id` from
  `scheduled-scaffold-walk-deepseek__deepseek-v4-pro-r4-delta` to
  `scheduled-scaffold-walk-deepseek__deepseek-v4-pro-r4`.
- Replicate 4's repair output deleted `cycle`, leaving final durable state
  without a `cycle` field.

These do not falsify H163-H167 as preregistered, because those hypotheses
focused on graph-walk evidence and bounded scaffold repair. They do show that
the validator contract was too narrow for identity continuity. The scaffold
did exactly what it was asked to do; it did not ask enough.

## Interpretation

The original scheduled-wake confound is no longer dominant. The scheduler,
graph context resolution, event runner, validator, and full-target repair
scaffold now work together:

- walk evidence is delivered;
- first-pass failure is preserved;
- repair is bounded;
- final graph-evidence state is durable.

The next boundary is contract completeness. A validator that checks only the
new evidence fields can permit collateral damage to identity fields. This is
the same lesson as the earlier repair experiments, but one layer deeper:
output-shape scaffolds can recover target fields while still allowing adjacent
state drift unless the contract names the invariants.

## Design Implication

The next scaffold iteration should validate both:

- task-specific evidence fields; and
- continuity invariants.

For this gate, continuity invariants should include at least:

- `probe_id` unchanged from prior state;
- `cycle` present and equal to the wake cycle;
- baseline observation preserved;
- no deletion of framework continuity fields unless explicitly allowed.

The validator should report these separately from evidence-field failures so
analysis can distinguish:

- evidence repair success with continuity drift;
- evidence repair success with continuity preservation;
- unrepaired evidence failure.

That is now a more useful research question than testing whether scheduled
walk evidence can be repaired at all.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/scheduled_walk_validation_repair_20260605/run_scheduled_walk_validation_repair.py
timeout 1200s uv run python experiments/event_loop/scheduled_walk_validation_repair_20260605/run_scheduled_walk_validation_repair.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- four of four replicates initialized validly.
- four of four scheduled events completed.
- four of four completed events had four-entry adjacent walk context.
- four of four wakes failed first-pass validation.
- four of four wakes were repaired by the scaffold.
- zero bounded-wake-call violations occurred.
- full regression suite: 283 passed.
