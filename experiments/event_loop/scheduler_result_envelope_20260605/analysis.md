# Analysis: Scheduler Result Envelope

Date: 2026-06-05

## Result

The normalization slice succeeded technically and produced a sharper research
constraint: future scheduler panels need a common result envelope before they
should be pooled.

- H246 deterministic envelope generation: supported.
- H247 initialization classes remain distinct: supported.
- H248 denominator eligibility from initialization provenance: supported.
- H249 wake validation provenance represented as present/absent/not
  applicable: supported.
- H250 runner families needing schema updates identified: supported.

## Summary

The runner generated 140 envelopes from row-like event-loop result records.

Scheduler-relevant rows:

- total: 89;
- scheduler-score eligible by initialization provenance: 60;
- ineligible or unclassifiable: 29.

Initialization classes across all envelopes:

- `valid_legacy`: 54;
- `not_scheduler_scored`: 51;
- `failed_or_culled`: 21;
- `unclassifiable`: 8;
- `first_pass_valid`: 4;
- `repaired_valid`: 2.

Wake validation provenance among scheduler-relevant rows:

- absent: 54;
- session state validation: 27;
- event log scoring: 8.

Three result files remain aggregate or malformed for row-level envelope
purposes:

- `framework_field_reservation_20260605/results.json`;
- `protected_merge_observability_20260605/results.json`;
- `simulated_time_scheduler_20260605/results.json`.

## Interpretation

The envelope can represent the current corpus without collapsing evidence, but
the corpus is not yet adequate for broad pooled claims. The main issue is not
that rows cannot be normalized. The main issue is that normalization makes the
missing evidence visible.

Only two live scheduler rows currently have the cleanest repaired-initialization
provenance class:

- `repaired_init_scheduler_integration_20260605`: 2/2 rows.

Only four scheduler rows currently have explicit first-pass initialization
provenance:

- `init_repair_scheduler_gate_20260605`: 4/4 rows.

Most historical eligible rows are `valid_legacy`, meaning they preserve
`init_valid == true` but not whether initialization was first-pass valid,
repaired, or accepted by an older ad hoc gate. Those rows remain valuable, but
they should not be silently treated as equivalent to first-pass or repaired
initialization evidence.

## Schema Update Targets

Twenty-one scheduler-relevant experiment families need schema updates before
future comparable reruns:

- `behavior_seeded_walk_gate_20260605`;
- `delayed_thinking_contract_variant_20260605`;
- `delayed_thinking_controlled_seed_20260605`;
- `delayed_thinking_envelope_variant_20260605`;
- `delayed_thinking_example_variant_20260605`;
- `delayed_thinking_simtime_20260605`;
- `direct_walk_evidence_gate_20260605`;
- `init_repair_scheduler_gate_20260605`;
- `live_event_wake_validation_scoring_20260605`;
- `live_scheduler_walk_context_gate_20260605`;
- `missing_field_repair_walk_gate_20260605`;
- `protocol_gate_scout_20260603`;
- `scheduled_walk_protected_merge_20260605`;
- `scheduled_walk_strict_continuity_20260605`;
- `scheduled_walk_validation_repair_20260605`;
- `scheduler_des_reentry_diagnostic_20260605`;
- `scheduler_revision_model_panel_20260603`;
- `scheduler_revision_preregistered_20260603`;
- `scheduler_tool_gate_20260603`;
- `strict_repair_walk_gate_20260605`;
- `update_exemplar_walk_gate_20260605`.

The common update reasons are:

- legacy initialization evidence;
- missing wake validation provenance;
- unclassifiable initialization in two older scheduler/reentry panels.

## Minimum Future Envelope

Future live scheduler runners should write a normalized envelope, or enough
raw fields to derive one, at result-write time. Minimum fields:

- `schema_version`;
- `source.experiment`;
- `identity.model`;
- `identity.replicate`;
- `initialization.class`;
- `initialization.first_pass_status`;
- `initialization.repair_attempted`;
- `initialization.repair_status`;
- `initialization.scheduler_score_eligible`;
- `scheduler.relevant`;
- `scheduler.schedule_valid`;
- `scheduler.event_completed`;
- `wake.validation_status`;
- `wake.first_pass_status`;
- `wake.repair_attempted`;
- `wake.repair_status`;
- `wake.source`;
- `logs.log_path`;
- `logs.event_log_path`;
- `errors.error`;
- `evidence.used`;
- `evidence.missing`.

The key policy is that scheduler-score eligibility must be decided before wake
outcome. Wake completion can measure scheduler behavior only after the row has
entered the qualified initialization population.

## Next Research Move

The next productive experiment is not a broad model sweep. It is a normalized
rerun of a small scheduler panel using the envelope at write time.

Recommended panel:

1. one first-pass-valid path;
2. one repaired-initialization path;
3. one intentionally failed initialization path.

That panel would test whether the envelope works prospectively and whether
repaired initialization behaves equivalently to first-pass initialization
downstream.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/scheduler_result_envelope_20260605/scheduler_result_envelope.py experiments/event_loop/scheduler_result_envelope_20260605/run_scheduler_result_envelope.py
uv run python experiments/event_loop/scheduler_result_envelope_20260605/run_scheduler_result_envelope.py
```

Additional key-presence validation checked all 140 generated envelopes for the
required schema sections and fields. The run wrote:

`experiments/event_loop/scheduler_result_envelope_20260605/envelopes.json`
