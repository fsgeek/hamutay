# Hypothesis Ledger Audit Notes

Date: 2026-06-05

## Validation

Validation status: `passed`.

## Extraction Coverage

- `results.json` files seen: 117
- result JSON shapes: {'list': 17, 'dict': 100}
- result files with hypothesis maps: 31
- result files without hypothesis maps: 69
- non-dict result files: 17
- Markdown sources scanned: 233
- ledger entries emitted: 552
- entries with nearby raw trace links: 233
- status counts: {'boundary': 67, 'contaminated': 4, 'unknown': 281, 'survived': 181, 'falsified': 19}
- entry-type counts: {'confound': 41, 'falsification_criterion': 241, 'hypothesis': 223, 'paper_claim': 14, 'synthesis_reference': 33}

## Schema Gaps

- Many older `results.json` files do not expose `hypothesis_results` or `hypothesis_outcomes` maps.
- Some result files are list-shaped rather than object-shaped.
- Markdown hypotheses often repeat across preregistration, analysis, and synthesis; the extractor merges experiment-local hypothesis IDs when possible.
- `H1`, `H2`, and similar IDs are source-local, not globally unique.
- Some entries are criteria or synthesis references rather than direct hypothesis outcomes; these are typed separately.
- Raw JSONL traces are linked for ambiguous rows when nearby, but the first pass does not re-score every raw trace.

## Sampling Checks

Manual spot checks performed during generation:

- Structured bounded-autonomous-work outcomes matched the known Step 6 and Step 7 results.
- `docs/paper-evidence-ledger.md` table rows were parsed as `paper_claim` entries with conservative status mapping.
- Preregistration-only headings remain `unknown` unless later result or analysis evidence updates them.
- KIMI Step 7 timeout behavior is represented as a provider/protocol boundary in the source analysis, not as a model incapability proof.

First five emitted ledger IDs for repeatability checks:

- `HL-b7fd02b738db`
- `HL-bb5092ec23a3`
- `HL-226c9aaa3c79`
- `HL-96275892721e`
- `HL-40aad895a10d`
