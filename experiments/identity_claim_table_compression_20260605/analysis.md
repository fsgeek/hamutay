# Identity Claim-Table Compression Analysis

Filed: 2026-06-05 after the registered panel completed.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- runner: `run_claim_table_compression.py`
- raw logs: `mistralai__mistral-small-2603_*.jsonl`
- scored results: `results.json`

## Validation

- `uv run pytest tests/unit/test_continuity_curator.py`: pass
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py tests/unit/test_exchange_tools.py`: pass
- `uv run python -m py_compile src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py`: pass
- `uv run python -m py_compile experiments/identity_claim_table_compression_20260605/run_claim_table_compression.py`: pass
- `uv run python experiments/identity_claim_table_compression_20260605/run_claim_table_compression.py --rescore`: pass, 12 logs rescored
- `jq empty experiments/identity_claim_table_compression_20260605/results.json`: pass
- `git diff --check -- src/hamutay/continuity_curator.py tests/unit/test_continuity_curator.py experiments/identity_claim_table_compression_20260605`: pass

## Registered Panel

Model:

- `mistralai/mistral-small-2603`

Conditions:

- `free_summary_1200`: 4 replicates
- `claim_table_full_1200`: 4 replicates
- `claim_table_delta_800`: 4 replicates

Three runs failed early with the strict state protocol guard:

- `free_summary_1200` replicate 2 failed at cycle 5.
- `free_summary_1200` replicate 3 failed at cycle 3.
- `claim_table_full_1200` replicate 3 failed at cycle 3.

All failures were preserved as data.

## Summary Results

All-run aggregate:

| condition | n | errors | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| free_summary_1200 | 4 | 2 | 18.75 | 3.0 | 2850.0 | 5283.75 |
| claim_table_full_1200 | 4 | 1 | 18.75 | 1.5 | 4162.25 | 6266.75 |
| claim_table_delta_800 | 4 | 0 | 25.25 | 2.5 | 2922.75 | 6866.5 |

Successful-run aggregate:

| condition | n | avg recovery | avg repaired false assumptions | avg injected chars | avg main input tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| free_summary_1200 | 2 | 31.0 | 5.0 | 4653.0 | 7030.5 |
| claim_table_full_1200 | 3 | 25.0 | 2.0 | 5218.67 | 7793.67 |
| claim_table_delta_800 | 4 | 25.25 | 2.5 | 2922.75 | 6866.5 |

Claim-row mechanics:

| condition | accepted rows | accepted cycles | selected delta rows | omitted delta rows | truncations |
| --- | ---: | ---: | ---: | ---: | ---: |
| claim_table_full_1200 | 130 | 19 | 0 | 0 | 14 |
| claim_table_delta_800 | 164 | 23 | 106 | 179 | 1 |

## Hypothesis Assessment

### H37: Delta Rendering Reduces Injected Context

Supported on injected text and partially supported on main-call tokens.

Successful-run comparison:

- injected characters: 2922.75 vs 5218.67, a 44.0% reduction;
- main input tokens: 6866.5 vs 7793.67, an 11.9% reduction.

Delta rendering almost eliminated summary truncation:

- delta: 1 truncation;
- full: 14 truncations.

The main-token reduction was smaller than the injected-character reduction,
which suggests other prompt/state growth still matters.

### H38: Delta Rendering Preserves Most Recovery

Supported.

Delta recovery matched the full claim-table condition:

- delta successful-run recovery: 25.25;
- full successful-run recovery: 25.0.

This exceeds the registered 90% threshold.

### H39: Delta Rendering Does Not Increase Contamination

Weakened.

Delta repaired false assumptions were slightly higher:

- delta successful-run average: 2.5;
- full successful-run average: 2.0.

The increase is small in absolute terms, and still lower than successful
free-summary contamination at 5.0, but the registered prediction was no
increase relative to full claim-table. That prediction did not hold.

### H40: Delta Rendering Keeps Claim-Row Yield

Supported.

Delta accepted rows in 23 of 24 completed curation cycles, above the 75%
threshold. It accepted 164 claim rows, selected 106 for rendering, and omitted
179. The renderer compressed active context without starving the claim-row
channel.

## Interpretation

This is a stronger result than the previous compression-adjacent panels.

The delta renderer preserved recovery while substantially reducing injected
characters. It also avoided the full-table renderer's chronic truncation. That
means the claim-table continuity channel can be compressed without collapsing
the task-memory benefit.

The result is not a clean domination. Delta did not reduce main input tokens as
much as injected characters, and repaired contamination increased slightly
relative to full claim-table. The plausible mechanism is that omitting rows can
drop some epistemic guardrails even while preserving enough task facts for
recovery.

The full-table condition had one early failure and a weaker successful-run
recovery than the previous schema panel, so cross-panel certainty remains
limited. But within this panel, the delta condition completed all four runs and
met the recovery and row-yield tests.

## Design Implications

1. Delta/prioritized claim-table rendering is viable. It does not starve the
   continuity channel.

2. The next compression target is epistemic guardrail preservation, not raw
   memory recovery. Delta should carry a minimal stable set of invalidated
   assumptions and uncertainty markers even when they are not new.

3. The event-loop scaffold should continue logging selected and omitted rows.
   Omission is now an experimental variable, not invisible loss.

4. Claim-table curation remains a better candidate than free summary for the
   scaffold, but the renderer needs a contamination-aware selection policy.

## Limitations

- Small panel: 4 replicates per condition.
- Comparator failures complicate all-run averages.
- Same model served as main instance and curator.
- Deterministic scorer remains pattern-based.
- Delta renderer was simple and did not explicitly score rows by contamination
  risk or epistemic guardrail value.

## Next Research Move

The next preregistered question should be contamination-aware delta rendering:

Can a guardrail-preserving delta renderer keep the context reduction while
matching or improving full claim-table contamination?

Recommended conditions:

- `claim_table_full_1200`
- `claim_table_delta_800`
- `claim_table_guardrail_delta_900`

The guardrail delta should reserve slots for:

- all current invalidated assumptions up to a small cap;
- no-local-document-storage constraint;
- site substitution status;
- top new/changed supported claims;
- one uncertainty/open-question row if present.

The primary success criterion should require delta-like context reduction,
recovery within 90% of full claim-table, and repaired false assumptions no
higher than full claim-table.
