# Pre-Registration: Prospective Envelope Adoption Gate

Date: 2026-06-05

## Research Question

Can a future scheduler experiment emit the normalized scheduler result envelope
at row-write time without changing the underlying scheduler scoring semantics?

The retrospective scheduler result envelope normalized existing artifacts, but
that does not prove the envelope is suitable as a prospective write-time
contract. This gate tests adoption on representative row shapes before applying
it to live model runs.

## Hypotheses

- H251: The envelope helper can be applied prospectively to representative
  scheduler rows without requiring experiment-name-specific logic.
- H252: Envelope emission preserves existing raw result fields and therefore
  does not change existing scoring semantics.
- H253: The envelope distinguishes at least these three adoption fixtures:
  first-pass valid initialization, repaired-valid initialization, and
  failed/culled initialization.
- H254: Scheduler-score eligibility is invariant under prospective wrapping:
  first-pass valid and repaired-valid rows are eligible; failed/culled rows are
  not.
- H255: The adoption gate can identify minimum field gaps before any live
  scheduler rerun is attempted.

## Method

Build a deterministic local adoption runner using representative existing rows:

1. `init_repair_scheduler_gate_20260605`: first-pass valid initialization.
2. `repaired_init_scheduler_integration_20260605`: repaired-valid
   initialization.
3. `live_event_wake_validation_scoring_20260605` or another strict scheduler
   panel row with failed initialization.

For each fixture:

- load the existing raw row;
- wrap it with the scheduler result envelope helper as a future runner would;
- write both `raw_result` and `result_envelope` in a prospective-style row;
- verify the raw row is unchanged by wrapping;
- verify the envelope class and eligibility match the expected fixture class.

No model calls are permitted. No source result files are modified.

## Predictions

The envelope should adopt cleanly for all three fixture classes because the
retrospective helper already normalized those row shapes. The main expected
gap is not syntax. The expected gap is that legacy rows lack first-pass
initialization details, so the first-pass fixture should be drawn from
`init_repair_scheduler_gate_20260605`, not from older `init_valid == true`
rows.

## Falsification Criteria

- H251 is falsified if fixture wrapping requires special-case code by
  experiment name.
- H252 is falsified if raw fixture rows mutate during envelope generation.
- H253 is falsified if fewer than three expected fixture classes are produced.
- H254 is falsified if eligibility differs from the preregistered class policy.
- H255 is falsified if the gate cannot report field gaps in structured form.

## Analysis Plan

Report:

- fixture classes produced;
- eligibility by fixture;
- raw-row mutation check;
- required-field presence check;
- structured field gaps;
- recommendation on whether to add envelope writing to the next live scheduler
  runner.

Interpret success as permission to use the envelope in the next prospective
live scheduler panel, not as proof that all historical rows are adequate.
