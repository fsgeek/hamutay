# Identity Claim-Table Curator Analysis

Filed: 2026-06-05 after the registered panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_claim_table_curator.py`
- raw logs: `mistralai__mistral-small-2603_*.jsonl`
- scored results: `results.json`

## Validation

- `uv run pytest tests/unit/test_continuity_curator.py`: pass
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py tests/unit/test_exchange_tools.py`: pass
- `uv run python -m py_compile src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py`: pass
- `uv run python -m py_compile experiments/identity_claim_table_curator_20260605/run_claim_table_curator.py`: pass
- `uv run python experiments/identity_claim_table_curator_20260605/run_claim_table_curator.py --rescore`: pass, 8 logs rescored
- `jq empty experiments/identity_claim_table_curator_20260605/results.json`: pass
- `git diff --check -- src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py experiments/identity_claim_table_curator_20260605`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Conditions:

- `free_summary_curator`: 4 replicates
- `claim_table_curator`: 4 replicates

One claim-table replicate failed at cycle 3 with the strict state protocol
guard: the model both deleted and updated the same keys in a single cycle.
This was preserved as data.

## Summary Results

All-run aggregate:

| condition | n | errors | avg recovery | avg repaired false assumptions | avg injected chars | accepted claim rows | rejected claim rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| free_summary_curator | 4 | 0 | 30.0 | 5.0 | 5193.0 | 0 | 0 |
| claim_table_curator | 4 | 1 | 11.0 | 2.75 | 116.0 | 0 | 20 |

Successful-run aggregate:

| condition | n | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| free_summary_curator | 4 | 30.0 | 5.0 | 5193.0 | 7617.25 |
| claim_table_curator | 3 | 14.67 | 3.67 | 145.0 | 5526.0 |

Attribution diagnostic counts:

| condition | curator artifact | main raw output | unattributed |
| --- | ---: | ---: | ---: |
| free_summary_curator | 11 | 3 | 6 |
| claim_table_curator | 7 | 3 | 1 |

## Protocol Finding

The claim-table curator accepted zero rows.

All 20 rejected claim-table curation records were rejected for the same reason:
`claims_not_list`. Inspection shows the model often produced a plausible
claim table, but placed it inside the required `response` field rather than as
a top-level `claims` property. Examples include both object-valued
`response: {"claims": [...]}` and stringified JSON in `response`.

The adapter deliberately did not unwrap this after the run. The preregistered
boundary required deterministic rendering from validated rows. Accepting
claims hidden inside `response` would have been a post-hoc protocol repair and
would change the treatment.

## Hypothesis Assessment

### H29: Claim-Table Curator Is Less Contaminating Than Free Summary

Superficially supported, mechanistically not supported.

Claim-table runs had lower repaired false assumptions:

- all-run average: 2.75 vs 5.0
- successful-run average: 3.67 vs 5.0

But this reduction came from starving the continuity channel, not from a
working claim-table memory. Since zero rows were accepted, the condition did
not test an effective claim-table curator. It tested strict rejection of
misplaced claim-table output.

### H30: Claim-Table Curator Preserves Most Recovery

Falsified.

The claim-table condition preserved only 48.9% of free-summary recovery on all
runs and 48.9% on successful runs:

- all-run recovery: 11.0 / 30.0
- successful-run recovery: 14.67 / 30.0

This is far below the registered 90% threshold.

### H31: Claim-Table Curator Reduces Context Pressure

Supported, but for the wrong reason.

Claim-table injection was much smaller:

- all-run injected chars: 116.0 vs 5193.0
- successful-run injected chars: 145.0 vs 5193.0
- successful-run main input tokens: 5526.0 vs 7617.25

However, this was achieved because the injected artifact was usually only
`(no valid curator claim rows)`, not because the claim-table representation
compressed useful continuity.

### H32: Contamination Attribution Becomes More Observable

Partially supported.

The runner produced first-appearance attribution diagnostics for active
contamination patterns. This is useful, but the interpretation is subtle:
`curator_artifact` includes raw curator output, not only injected summary text.
For claim-table runs, several contamination terms first appeared in raw curator
artifacts even though those rows were rejected and not injected. This means the
durable observability layer captured contamination risk that the active context
path did not necessarily transmit.

## Interpretation

This was a productive failure.

The free-summary condition at a 1200-character cap performed much better than
the earlier 2400-character free-summary panel on contamination while retaining
high recovery. It still injected thousands of characters across a run and
still attributed many active contamination patterns to curator artifacts, but
the simple budget reduction appears materially useful.

The claim-table condition failed at the protocol boundary. The model often
understood the requested object semantically, but put it in the wrong place.
This matches a pattern already seen elsewhere in Hamut'ay: models can be close
to the target behavior while still violating the exact structured-output
contract.

The strict adapter did the right thing for this experiment. It prevented
misplaced prose or nested JSON from silently becoming active continuity
context. That gave a clean negative result: a top-level claim-table protocol is
not reliable with this model under the current generic `think_and_respond`
schema.

## Design Implications

1. The next claim-table test should not rely on `additionalProperties` alone.
   It needs a terminal tool schema that explicitly defines top-level `claims`.

2. If the framework wants to be generous in what it accepts, that generosity
   should be preregistered and instrumented. A safe parser could unwrap
   `response.claims` and stringified `response` JSON, but it must log the
   repair as a protocol recovery event.

3. Smaller free-summary budgets deserve a direct follow-up. The 1200-character
   free-summary condition had high recovery and lower contamination than the
   previous larger free-summary run, though cross-panel comparison remains
   weak.

4. Attribution diagnostics should remain. They distinguished raw curator
   contamination from injected-context contamination, which is exactly the kind
   of observability this project needs.

## Limitations

- Small panel: 4 replicates per condition.
- One claim-table run failed early.
- Claim-table rows were never accepted, so the intended representation was not
  actually exercised.
- Same model served as main instance and curator.
- Deterministic attribution is pattern-based and cannot prove causal influence
  from curator artifact to late visible response.

## Next Research Move

The next preregistered question should be:

Can an explicit claim-table terminal schema, with logged protocol-recovery
parsing as a separate condition or diagnostic, make the bounded claim-table
curator actually usable?

Recommended conditions:

- `free_summary_1200`
- `claim_table_strict_schema_1200`
- optionally `claim_table_repair_parser_1200` if preregistered as a distinct
  generous-parser treatment

The primary success criterion should require nonzero accepted claim rows before
interpreting recovery or contamination as a claim-table result.
