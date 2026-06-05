# Pre-Registration: Scheduler Result Envelope

Date: 2026-06-05

## Research Question

Can event-loop scheduler experiment rows be normalized into a common result
envelope that preserves initialization provenance, wake validation provenance,
and denominator eligibility without hiding older schema debt?

The initialization taxonomy audit showed that scheduler panels are not
directly comparable unless initialization provenance is made explicit. This
experiment tests whether a reusable envelope can be built over existing rows
before modifying live runners.

## Hypotheses

- H246: A deterministic envelope can normalize existing scheduler-relevant rows
  into a stable schema without model calls.
- H247: The envelope can represent first-pass-valid, legacy-valid,
  repaired-valid, failed/culled, and unclassifiable initialization classes
  without collapsing them.
- H248: The envelope can compute denominator eligibility for scheduler-success
  scoring from initialization provenance alone.
- H249: The envelope can preserve wake validation provenance when present and
  mark it missing when absent.
- H250: Retrospective validation will expose specific runner families that
  should be updated before additional live scheduler panels are pooled.

## Method

Build a local helper module:

`experiments/event_loop/scheduler_result_envelope_20260605/scheduler_result_envelope.py`

The helper will:

- accept an experiment name, row index, and raw result row;
- emit a normalized envelope with sections for identity, initialization,
  scheduler, wake, logs, errors, and raw evidence keys;
- classify initialization using only structured fields;
- classify scheduler-score eligibility from initialization provenance;
- preserve explicit missingness rather than inferring from prose.

Then run a deterministic retrospective validator over
`experiments/event_loop/*/results.json` and write:

- `envelopes.json`;
- `analysis.md`.

No model calls are permitted. No existing result files are modified.

## Envelope Requirements

Every normalized row must contain:

- `schema_version`;
- `source.experiment`;
- `source.result_index`;
- `identity.model`;
- `identity.replicate`;
- `initialization.class`;
- `initialization.scheduler_score_eligible`;
- `scheduler.relevant`;
- `scheduler.event_completed`;
- `wake.validation_status`;
- `wake.first_pass_status`;
- `wake.repair_status`;
- `logs.log_path`;
- `logs.event_log_path`;
- `errors.error`;
- `evidence.used`;
- `evidence.missing`.

## Predictions

The helper should normalize most scheduler-relevant rows, but it should expose
three hard edges:

- legacy rows that preserve `init_valid` but not first-pass/repair provenance;
- scheduler rows that have event surfaces but no initialization evidence;
- deterministic or aggregate result files that cannot be treated as live
  scheduler rows.

## Falsification Criteria

- H246 is falsified if the helper cannot generate a syntactically stable
  envelope for every row-like result.
- H247 is falsified if any observed initialization class must be merged into
  another class to fit the envelope.
- H248 is falsified if scheduler eligibility depends on wake outcome,
  experiment name, or manual interpretation instead of initialization
  provenance.
- H249 is falsified if wake validation provenance cannot be represented as
  present, absent, or not applicable.
- H250 is falsified if the validator cannot identify concrete runner families
  needing schema updates.

## Analysis Plan

Report:

- total envelopes generated;
- scheduler-relevant envelopes generated;
- counts by initialization class;
- counts by scheduler eligibility;
- wake validation provenance coverage;
- files or runner families requiring schema updates;
- recommended minimum envelope fields for future live scheduler runners.

Interpretation will distinguish compatibility from adequacy. A row can be
normalized while still carrying weak or missing evidence.
