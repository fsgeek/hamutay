# Identity Claim-Table Schema Analysis

Filed: 2026-06-05 after the registered panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_claim_table_schema.py`
- raw logs: `mistralai__mistral-small-2603_*.jsonl`
- scored results: `results.json`

## Validation

- `uv run pytest tests/unit/test_continuity_curator.py`: pass
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py tests/unit/test_exchange_tools.py`: pass
- `uv run python -m py_compile src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py`: pass
- `uv run python -m py_compile experiments/identity_claim_table_schema_20260605/run_claim_table_schema.py`: pass
- `uv run python experiments/identity_claim_table_schema_20260605/run_claim_table_schema.py --rescore`: pass, 12 logs rescored
- `jq empty experiments/identity_claim_table_schema_20260605/results.json`: pass
- `git diff --check -- src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py experiments/identity_claim_table_schema_20260605`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Conditions:

- `free_summary_1200`: 4 replicates
- `claim_table_strict_schema_1200`: 4 replicates
- `claim_table_repair_parser_1200`: 4 replicates

Two runs failed early with the strict state protocol guard:

- `free_summary_1200` replicate 2 failed at cycle 3.
- `claim_table_strict_schema_1200` replicate 1 failed at cycle 3.

Both failures were preserved as data.

## Summary Results

All-run aggregate:

| condition | n | errors | avg recovery | avg repaired false assumptions | accepted rows | accepted cycles | rejected rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| free_summary_1200 | 4 | 1 | 23.0 | 3.0 | 0 | 0 | 0 |
| claim_table_strict_schema_1200 | 4 | 1 | 22.25 | 1.5 | 127 | 20 | 83 |
| claim_table_repair_parser_1200 | 4 | 0 | 29.0 | 4.75 | 163 | 23 | 92 |

Successful-run aggregate:

| condition | n | avg recovery | avg repaired false assumptions | accepted rows | accepted cycles | avg injected chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| free_summary_1200 | 3 | 30.67 | 4.0 | 0 | 0 | 5247.67 |
| claim_table_strict_schema_1200 | 3 | 29.67 | 2.0 | 117 | 18 | 5365.33 |
| claim_table_repair_parser_1200 | 4 | 29.0 | 4.75 | 163 | 23 | 5199.0 |

Protocol recovery:

- strict schema recovery events: 0
- repair-parser recovery events: 0
- recovered rows: 0

All rejected claim rows in schema claim-table conditions were rejected because
of the row cap, not malformed shape or invalid status:

- `row_cap_exceeded`: 150

## Hypothesis Assessment

### H33: Explicit Schema Produces Accepted Claim Rows

Supported.

The explicit schema fixed the protocol-slot failure from the prior panel.
Strict schema accepted rows in 20 of 20 completed curation cycles. Successful
strict-schema runs accepted 117 rows across 18 completed curation cycles.

The previous zero-row result was therefore not evidence that Mistral could not
produce claim-table rows. It was evidence that the generic open schema was too
weak to make the model put rows in the correct location.

### H34: Repair Parser Improves Protocol Yield

Falsified.

Repair parsing did not fire at all:

- protocol recovery events: 0
- recovered claim rows: 0

With the explicit schema, the model produced top-level `claims`; there were no
near-miss `response.claims` objects for the repair parser to recover. The
repair-parser condition accepted more rows only because it completed all four
runs and had one more completed curation cycle than strict schema, not because
repair parsing helped.

### H35: Accepted Claim Tables Recover More Than Starved Claim Tables

Supported.

The previous zero-row claim-table panel had successful-run average recovery of
14.67. Both explicit-schema claim-table conditions exceeded that:

- strict schema successful-run recovery: 29.67
- repair-parser successful-run recovery: 29.0

Accepted claim tables restored almost all of the free-summary recovery:

- free-summary successful-run recovery: 30.67
- strict-schema successful-run recovery: 96.7% of free summary
- repair-parser successful-run recovery: 94.6% of free summary

### H36: Claim Tables Stay Less Contaminating Than Free Summary

Partly supported.

Strict schema was clearly cleaner:

- successful-run repaired false assumptions: 2.0 vs free-summary 4.0
- all-run repaired false assumptions: 1.5 vs free-summary 3.0

Repair-parser condition stayed below the registered prior free-summary
threshold of 5.0, but it was worse than the same-panel free-summary comparator:

- repair-parser repaired false assumptions: 4.75
- same-panel free-summary repaired false assumptions: 4.0 successful-run, 3.0 all-run

Because repair parsing never fired, this difference is probably stochastic or
condition-prompt sensitivity, not evidence that repair parsing caused
contamination.

## Interpretation

This is the first clean positive result for bounded claim-table continuity.

The prior claim-table failure was a protocol-design failure. Once the curator
backend used an explicit terminal schema requiring top-level `claims`, the
model produced usable rows reliably. Strict schema also reduced repaired false
assumptions while preserving nearly all of free-summary recovery.

The claim-table representation did not reduce injected characters in this
implementation. Most summaries hit the 1200-character cap, and row-cap
overflow was common. That means the current deterministic renderer is still too
verbose or the row cap/support fields are too large. However, the important
failure changed: we no longer have a starved continuity channel. We now have a
working bounded channel that needs compression.

The repair parser is not needed when the schema is explicit, at least for this
model and task. It remains useful as a separately instrumented robustness
option, but it did not contribute in this panel.

## Design Implications

1. Claim-table curation should use an explicit terminal schema. Relying on
   `additionalProperties` is not sufficient for this role.

2. Strict parsing is viable. It accepted rows in every completed strict-schema
   curation cycle and all rejections were row-cap overflow.

3. The next compression target should be renderer design, not protocol repair:
   reduce support verbosity, cap rows by status priority, or render deltas
   rather than full tables each cycle.

4. Attribution diagnostics should remain. Even with strict schema,
   contamination sometimes first appeared in curator artifacts, so the curator
   remains an epistemic risk surface.

## Limitations

- Small panel: 4 replicates per condition.
- Two early strict-protocol run failures complicate all-run averages.
- Same model served as main instance and curator.
- Explicit schema used an experiment-local backend subclass, not a generalized
  production schema-selection mechanism.
- Claim-table summaries still hit the character cap often, so efficiency
  claims are limited.

## Next Research Move

The next preregistered question should be about claim-table compression:

Can a prioritized delta claim-table renderer reduce injected context while
preserving the strict-schema recovery and contamination advantages?

Recommended conditions:

- `free_summary_1200`
- `claim_table_full_1200`
- `claim_table_delta_800`

The delta renderer should preserve only new or changed rows, plus a small
stable set of active constraints and invalidated assumptions. The primary
success criterion should require recovery within 90% of full claim-table while
reducing injected characters and main input tokens.
