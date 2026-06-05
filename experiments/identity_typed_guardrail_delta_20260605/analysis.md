# Identity Typed Guardrail Delta Analysis

Filed: 2026-06-05 after the registered panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_typed_guardrail_delta.py`
- raw logs: `mistralai__mistral-small-2603_*.jsonl`
- scored results: `results.json`

## Validation

- `uv run pytest tests/unit/test_continuity_curator.py`: pass
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py tests/unit/test_exchange_tools.py`: pass
- `uv run python -m py_compile src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py experiments/identity_typed_guardrail_delta_20260605/run_typed_guardrail_delta.py`: pass
- `uv run python experiments/identity_typed_guardrail_delta_20260605/run_typed_guardrail_delta.py --help`: pass
- `uv run python experiments/identity_typed_guardrail_delta_20260605/run_typed_guardrail_delta.py --rescore`: pass, 12 logs rescored
- `jq empty experiments/identity_typed_guardrail_delta_20260605/results.json`: pass
- `git diff --check`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Conditions:

- `claim_table_delta_800`: 4 replicates
- `claim_table_guardrail_delta_900`: 4 replicates
- `claim_table_typed_guardrail_delta_800`: 4 replicates

Five runs failed early with the strict state protocol guard:

- `claim_table_delta_800` replicate 1 failed at cycle 3.
- `claim_table_guardrail_delta_900` replicate 1 failed at cycle 3.
- `claim_table_guardrail_delta_900` replicate 3 failed at cycle 3.
- `claim_table_guardrail_delta_900` replicate 4 failed at cycle 3.
- `claim_table_typed_guardrail_delta_800` replicate 1 failed at cycle 3.

All failures were `deleted_regions` plus update overlap failures and were
preserved as data. No run was censored for rate limit or length.

## Summary Results

All-run aggregate:

| condition | n | errors | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| claim_table_delta_800 | 4 | 1 | 20.25 | 6.0 | 2342.25 | 5581.25 |
| claim_table_guardrail_delta_900 | 4 | 3 | 6.5 | 1.0 | 1398.75 | 2802.75 |
| claim_table_typed_guardrail_delta_800 | 4 | 1 | 15.5 | 3.5 | 2478.75 | 5338.25 |

Successful-run aggregate:

| condition | n | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| claim_table_delta_800 | 3 | 27.0 | 8.0 | 3109.0 | 6997.67 |
| claim_table_guardrail_delta_900 | 1 | 26.0 | 4.0 | 4024.0 | 6843.0 |
| claim_table_typed_guardrail_delta_800 | 3 | 20.67 | 4.67 | 3143.0 | 6636.0 |

Claim-row mechanics:

| condition | accepted rows | accepted cycles | selected rows | omitted rows | truncations |
| --- | ---: | ---: | ---: | ---: | ---: |
| claim_table_delta_800 | 131 | 19 | 85 | 126 | 5 |
| claim_table_guardrail_delta_900 | 81 | 12 | 62 | 35 | 4 |
| claim_table_typed_guardrail_delta_800 | 133 | 19 | 106 | 49 | 3 |

Typed guardrail selected these all-run compact tokens:

| token | count |
| --- | ---: |
| blocked:local_document_storage | 13 |
| site_replaced:east_clinic->west_shelter | 11 |
| constraint:no_ssn | 9 |
| constraint:budget<=18000 | 9 |

## Hypothesis Assessment

### H45: Typed Guardrails Restore Compression

Supported on successful-run injected characters, with caveat.

Successful-run injected characters:

- simple delta: 3109.0;
- typed guardrail delta: 3143.0;
- English guardrail delta: 4024.0.

Typed guardrail delta was 1.1% larger than simple delta, within the registered
10% allowance, and 22.0% smaller than English guardrail delta. The caveat is
that English guardrail has only one successful run in this panel.

### H46: Typed Guardrails Preserve Contamination Benefit

Partially supported, not a clean win.

Successful-run repaired false assumptions:

- simple delta: 8.0;
- English guardrail delta: 4.0;
- typed guardrail delta: 4.67.

Typed guardrails improved over simple delta but did not match the English
guardrail control. Because the English control had only one successful run,
this should be treated as weak evidence rather than a stable ranking.

### H47: Typed Guardrails Preserve Recovery

Weakened.

Successful-run recovery:

- simple delta: 27.0;
- English guardrail delta: 26.0;
- typed guardrail delta: 20.67.

Typed guardrail delta fell below English guardrail delta and below the prior
full-table 90% recovery comparator from `identity_guardrail_delta_20260605`
(26.78). The compact token form appears to save context but may not carry
enough task-progress signal for recovery.

### H48: Typed Guardrails Keep Claim-Row Yield

Supported.

Typed guardrail delta accepted rows in 19 of 20 completed curation cycles
all-run and 17 of 18 successful-run curation cycles, above the registered 75%
threshold.

## Interpretation

Typed guardrails tested the intended mechanism and produced a useful negative
result.

The renderer executed correctly: all four registered compact tokens appeared
in selected rows. It also achieved the compression target against simple delta
on successful runs and improved contamination relative to simple delta.

But it did not preserve recovery. The result suggests that hard-constraint
tokens alone are too sparse: they protect against some stale false assumptions
but do not carry enough ordinary task continuity. The English guardrail rows
may be doing double duty by preserving both the guardrail and the surrounding
claim semantics.

The larger issue is protocol instability. Five of twelve runs failed under the
strict delete-plus-update guard, and three of those failures occurred in the
English guardrail control. That makes this panel weaker than the previous
guardrail panel and turns merge protocol behavior into an active confound.

## Limitations

- Small panel: 4 replicates per condition.
- Five strict merge failures reduce interpretability.
- English guardrail had only one successful run.
- Same model served as main instance and curator.
- Typed tokens were hand-registered for this task.
- Deterministic scorer remains pattern-based.

## Design Implications

1. Typed guardrails are viable for compression but insufficient as the only
   guardrail representation.

2. The substrate likely needs a two-channel rendered context:
   compact typed guardrails plus a small number of English task-progress rows.

3. The delete-plus-update merge rule is now a research confound. Treating it
   only as a failure guard may discard useful runs, but silently normalizing it
   would change identity-state semantics. That needs its own preregistered
   protocol experiment.

4. The next scheduler substrate slice should not proceed until merge protocol
   behavior is isolated or explicitly modeled, because scheduled re-entry
   results would otherwise mix scheduler behavior with state-merge fragility.

## Next Research Move

The next falsification question should isolate the delete-plus-update protocol:

> Does a preregistered delete-plus-update normalizer preserve behavioral
> continuity data without introducing state corruption?

Candidate conditions:

- `strict_reject`
- `delete_then_update_normalizer`
- `update_wins_normalizer`

The test should use the same city benefits task and score:

- protocol completion;
- recovery;
- repaired false assumptions;
- whether the normalized state contradicts visible response claims;
- whether any deleted key remains absent when the same cycle also provided an
  updated value.

If normalization preserves state/response consistency while reducing failure
rate, it should become part of the substrate. If it increases contradiction or
contamination, strict rejection remains the right guard despite the lost runs.
