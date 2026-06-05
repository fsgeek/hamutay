# Analysis: Initialization Taxonomy Audit

Date: 2026-06-05

## Result

The event-loop research arm has not run out of useful questions. The next
question is now comparability: many prior scheduler panels are shaped by
initialization provenance and censoring.

All preregistered hypotheses are supported under the conservative taxonomy.

- H241 initialization evidence classifies most scheduler rows: supported.
- H242 at least three initialization classes are present: supported.
- H243 scheduler panels are materially censored by initialization failure:
  supported.
- H244 some artifacts remain unclassifiable or aggregate-only: supported.
- H245 reusable machine-readable manifest can be generated locally: supported.

## Counts

The audit scanned 41 `results.json` files and 140 row-like records.

Overall row classes:

- `valid_legacy`: 54;
- `failed_or_culled`: 21;
- `not_scheduler_scored`: 51;
- `unclassifiable`: 8;
- `first_pass_valid`: 4;
- `repaired_valid`: 2.

Scheduler-relevant row classes:

- `valid_legacy`: 54;
- `failed_or_culled`: 21;
- `unclassifiable`: 8;
- `first_pass_valid`: 4;
- `repaired_valid`: 2.

The scheduler-relevant classified denominator is 81/89 rows. The remaining
8/89 scheduler-relevant rows have scheduler/event surfaces but no structured
initialization evidence.

## Censoring

Thirteen panels have a changed denominator when initialization-qualified rows
are separated from all attempted rows:

- `behavior_seeded_walk_gate_20260605`;
- `delayed_thinking_simtime_20260605`;
- `direct_walk_evidence_gate_20260605`;
- `live_event_wake_validation_scoring_20260605`;
- `live_scheduler_walk_context_gate_20260605`;
- `missing_field_repair_walk_gate_20260605`;
- `protocol_gate_scout_20260603`;
- `scheduled_walk_protected_merge_20260605`;
- `scheduler_des_reentry_diagnostic_20260605`;
- `scheduler_revision_model_panel_20260603`;
- `scheduler_revision_preregistered_20260603`;
- `scheduler_tool_gate_20260603`;
- `strict_repair_walk_gate_20260605`.

This is not a small bookkeeping issue. Example completion rates change when
failed or unclassifiable initialization rows are excluded:

- `live_event_wake_validation_scoring_20260605`: all attempts 3/4,
  initialization-qualified 3/3;
- `live_scheduler_walk_context_gate_20260605`: all attempts 1/2,
  initialization-qualified 1/1;
- `protocol_gate_scout_20260603`: all attempts 2/5,
  initialization-qualified 2/3;
- `scheduler_tool_gate_20260603`: all attempts 3/6,
  initialization-qualified 3/5;
- `scheduler_revision_model_panel_20260603`: all attempts 3/12,
  initialization-qualified 3/9.

For panels where the initialization-qualified denominator is zero, completion
rates are not interpretable as scheduler success rates.

## Evidence Classes

The repaired-initialization class is currently small but important:

- `repaired_init_scheduler_integration_20260605`: 2/2 rows are
  `repaired_valid`.

That class is distinct from `valid_legacy`. It should remain distinct because
it carries provenance about a prior failed initialization that was repaired
before scheduler scoring.

The `first_pass_valid` class is also small:

- `init_repair_scheduler_gate_20260605`: 4/4 rows are `first_pass_valid`.

Most successful historical scheduler rows are `valid_legacy`, not
`first_pass_valid`. That means they are usable, but their evidence is weaker:
the row says initialization passed, not whether it passed a first-pass
validator, a repair validator, or an older ad hoc gate.

## Data Debt

Three result files are aggregate or missing row-level `results` lists:

- `framework_field_reservation_20260605/results.json`;
- `protected_merge_observability_20260605/results.json`;
- `simulated_time_scheduler_20260605/results.json`.

Eight scheduler-relevant rows are unclassifiable because they expose scheduler
or event surfaces without initialization evidence:

- `scheduler_des_reentry_diagnostic_20260605`: 2 rows;
- `scheduler_revision_preregistered_20260603`: 6 rows.

The audit deliberately did not reinterpret prose logs to fill this gap.
Missing structured evidence is data debt.

## Interpretation

The event-loop arm should continue, but the next move should be data
normalization before new model novelty. The scheduler substrate is now
interesting enough that sloppy denominators would produce misleading findings.

Future scheduler analyses should use three explicit initialization populations:

1. first-pass valid;
2. repaired-valid with provenance label;
3. failed/culled or unclassifiable, excluded from scheduler-success scoring
   but retained as initialization-behavior data.

Legacy `init_valid == true` rows can be used for retrospective comparison, but
they should be labeled `valid_legacy` and not merged with first-pass validated
or repaired-valid rows without caveat.

## Answer To The Research Triage

There is more to do. We have not exhausted the research arm. The evidence now
points to a sharper set of next questions:

- Can future scheduler experiments emit a common initialization provenance
  envelope on every row?
- Do first-pass-valid, valid-legacy, and repaired-valid initialization
  populations behave equivalently downstream?
- Does repaired initialization merely rescue the denominator, or does it change
  later wake behavior?
- Can deterministic DES scaffold artifacts share enough schema with live runs
  to support comparison without contaminating model-behavior claims?

The immediate next practical step is to define and enforce a normalized
experiment result envelope for event-loop scheduler panels.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/initialization_taxonomy_audit_20260605/run_initialization_taxonomy_audit.py
uv run python experiments/event_loop/initialization_taxonomy_audit_20260605/run_initialization_taxonomy_audit.py
```

Both commands exited successfully. The run wrote:

`experiments/event_loop/initialization_taxonomy_audit_20260605/taxonomy.json`
