# Identity Guardrail Delta Analysis

Filed: 2026-06-05 after the registered panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_guardrail_delta.py`
- raw logs: `mistralai__mistral-small-2603_*.jsonl`
- scored results: `results.json`

## Validation

- `uv run pytest tests/unit/test_continuity_curator.py`: pass
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py tests/unit/test_exchange_tools.py`: pass
- `uv run python -m py_compile src/hamutay/continuity_curator.py experiments/identity_guardrail_delta_20260605/run_guardrail_delta.py tests/unit/test_continuity_curator.py`: pass
- `uv run python experiments/identity_guardrail_delta_20260605/run_guardrail_delta.py --help`: pass
- `uv run python experiments/identity_guardrail_delta_20260605/run_guardrail_delta.py --rescore`: pass, 12 logs rescored
- `jq empty experiments/identity_guardrail_delta_20260605/results.json`: pass
- `git diff --check`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Conditions:

- `claim_table_full_1200`: 4 replicates
- `claim_table_delta_800`: 4 replicates
- `claim_table_guardrail_delta_900`: 4 replicates

Two runs failed early with the strict state protocol guard:

- `claim_table_delta_800` replicate 2 failed at cycle 5.
- `claim_table_guardrail_delta_900` replicate 2 failed at cycle 3.

Both failures were preserved as data. No run was censored for rate limit or
length.

## Summary Results

All-run aggregate:

| condition | n | errors | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| claim_table_full_1200 | 4 | 0 | 29.75 | 5.5 | 5472.5 | 7968.75 |
| claim_table_delta_800 | 4 | 1 | 22.0 | 5.0 | 2529.75 | 6613.25 |
| claim_table_guardrail_delta_900 | 4 | 1 | 20.0 | 3.25 | 2758.5 | 5475.0 |

Successful-run aggregate:

| condition | n | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| claim_table_full_1200 | 4 | 29.75 | 5.5 | 5472.5 | 7968.75 |
| claim_table_delta_800 | 3 | 25.0 | 6.33 | 2773.33 | 6884.67 |
| claim_table_guardrail_delta_900 | 3 | 26.67 | 4.33 | 3663.0 | 6851.0 |

Claim-row mechanics:

| condition | accepted rows | accepted cycles | selected rows | omitted rows | truncations |
| --- | ---: | ---: | ---: | ---: | ---: |
| claim_table_full_1200 | 167 | 23 | 0 | 0 | 19 |
| claim_table_delta_800 | 149 | 21 | 95 | 156 | 0 |
| claim_table_guardrail_delta_900 | 118 | 18 | 95 | 38 | 7 |

Guardrail delta selected these all-run row reasons:

| reason | count |
| --- | ---: |
| hard_constraint_west_shelter_replaces_east_clinic | 21 |
| hard_constraint_no_local_document_storage | 18 |
| new_or_changed_invalidated_guardrail | 12 |
| hard_constraint_budget_18000 | 9 |
| hard_constraint_no_social_security_numbers | 4 |
| new_or_changed_supported | 26 |
| new_or_changed_open | 3 |
| new_or_changed_uncertain | 2 |

## Hypothesis Assessment

### H41: Guardrail Delta Preserves Compression

Mixed.

All-run injected characters support the registered prediction:

- guardrail delta: 2758.5;
- simple delta: 2529.75;
- full table: 5472.5.

Guardrail delta was 49.6% smaller than full table and 9.0% larger than simple
delta, within the registered 25% allowance.

Successful-run injected characters are less favorable:

- guardrail delta: 3663.0;
- simple delta: 2773.33;
- full table: 5472.5.

On successful runs, guardrail delta remained 33.1% smaller than full table but
was 32.1% larger than simple delta, exceeding the registered allowance. The
failed guardrail run ended at cycle 3 with only 45 injected characters, so the
all-run compression number is artificially favorable.

### H42: Guardrail Delta Preserves Recovery

Narrowly weakened.

Successful-run recovery:

- full table: 29.75;
- guardrail delta: 26.67.

Guardrail delta reached 89.6% of full-table recovery, just below the registered
90% threshold. The shortfall is small, but the preregistered criterion was not
met.

### H43: Guardrail Delta Reduces Delta Contamination

Supported in this panel.

Successful-run repaired false assumptions:

- simple delta: 6.33;
- full table: 5.5;
- guardrail delta: 4.33.

All-run repaired false assumptions show the same direction:

- simple delta: 5.0;
- full table: 5.5;
- guardrail delta: 3.25.

The guardrail renderer selected hard-constraint and invalidation rows
frequently, and contamination fell relative to both comparators.

### H44: Guardrail Delta Keeps Claim-Row Yield

Supported.

Guardrail delta accepted rows in 18 of 20 completed curation cycles all-run
and 17 of 18 successful-run curation cycles, above the registered 75%
threshold.

## Interpretation

The result supports the mechanism but not a clean domination claim.

Guardrail delta did what it was designed to do: it spent context on
invalidations and hard constraints, and repaired false assumptions fell. That
is useful evidence that the prior simple-delta contamination increase was at
least partly an omission problem.

The cost is also visible. Guardrail delta increased injected characters
relative to simple delta on successful runs and missed the recovery threshold
by a narrow margin. The likely mechanism is budget displacement: guardrail rows
prevent some contamination but leave fewer slots for task-progress claims.

The full-table condition again showed heavy truncation, so it remains a poor
substrate default despite strong recovery in this panel. The simple delta
condition stayed compact but carried the worst successful-run contamination.
Guardrail delta is the better substrate candidate if contamination control is
weighted above marginal recovery, but it needs a tighter representation before
we treat it as settled.

## Limitations

- Small panel: 4 replicates per condition.
- Two protocol-guard failures complicate all-run averages.
- Same model served as main instance and curator.
- Hard-constraint phrase set was hand-registered for this task.
- Deterministic scorer remains pattern-based.
- Guardrail delta had 7 truncations, so the 900-character budget may be too
  small for the current row text format.

## Design Implications

1. Guardrail preservation is a real substrate concern. Omitting rows is not
   neutral; it changes contamination behavior.

2. The continuity substrate should carry invalidated assumptions and hard
   constraints as first-class compact rows, not as ordinary delta rows.

3. Renderer rows should probably be shorter and typed. A compact
   machine-rendered form may preserve the same guardrails with less text than
   current English claim rows.

4. Scheduled re-entry experiments should use a guardrail-aware continuity
   renderer, but the next substrate work should reduce guardrail row verbosity
   before broadening model or scheduler claims.

## Next Research Move

The next falsification question should attack compact guardrail representation:

> Can typed guardrail rows preserve the contamination improvement of guardrail
> delta while returning injected context to simple-delta size?

Candidate conditions:

- `claim_table_delta_800`
- `claim_table_guardrail_delta_900`
- `claim_table_typed_guardrail_delta_800`

The typed guardrail condition should replace repeated English hard-constraint
rows with compact deterministic tokens such as:

- `blocked:local_document_storage`
- `site_replaced:east_clinic->west_shelter`
- `constraint:no_ssn`
- `constraint:budget<=18000`

That would test whether the benefit comes from semantic guardrail preservation
rather than the prose form of the rows.
