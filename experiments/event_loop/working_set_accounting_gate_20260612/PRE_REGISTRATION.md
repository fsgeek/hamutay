# Working-Set Accounting Gate Preregistration

Experiment ID: `working_set_accounting_gate_20260612`

Date: 2026-06-13

Plan source: `docs/event-loop-research-program-goals-20260612`, Goal 7.

## Research Question

Can Hamut'ay's event-loop harness report, for a dry-run bounded local memory
substitute, what was in live context, what was carried forward, what was
recalled, what was omitted, what losses were declared, and whether
model-authored evidence requests were answerable by the configured substrate?

## Hypothesis H8-G7

A bounded local memory substitute plus deterministic accounting can provide a
readiness gate for the matched working-set panel by preserving:

- live context injected;
- carried state;
- recalled/evidence context;
- omitted context;
- declared losses;
- approximate token counts;
- recall provenance;
- truncation and omission metadata;
- evidence-request answerability;
- recovery and contamination metrics;
- failure attribution by layer.

## Falsification Conditions

H8-G7 is falsified if the dry-run gate cannot:

- distinguish live prompt context, carried state, recalled context, omitted
  context, declared losses, and unavailable evidence;
- classify evidence requests as answerable, unavailable, structurally
  impossible, or malformed;
- preserve recall provenance and truncation/omission metadata;
- compute recovery and contamination metrics from preserved artifacts;
- state memory-substrate limitations explicitly;
- produce artifacts sufficient for the matched working-set panel readiness
  decision.

## Substrate Decision

Use the existing `LocalMemorySubstrate` as the bounded local substitute for this
gate. Yanantin remains the intended richer substrate, but Goal 7 does not block
on Yanantin delivery. The local substitute is sufficient for the accounting
gate because it supports immutable records, recall, retrieval logs, truncation
metadata, explicit missing-record failures, and snapshots.

## Bounded Inspectable Corpus

The dry-run corpus must include:

- records required for a bounded investigation;
- a record that should be omitted as a distractor;
- a long field that is recalled with truncation;
- enough metadata to classify recall provenance and omissions.

## Evidence Request Categories

`answerable_by_substrate`: request is well-formed, supported by the configured
substrate, and resolves successfully.

`unavailable_but_well_formed`: request is well-formed and substrate-supported,
but the requested record or field is not available.

`structurally_impossible`: request is syntactically meaningful but requires a
capability not provided by the configured substrate or by this gate's bounded
mapping.

`malformed_or_underspecified`: request cannot be validated or lacks required
coordinates.

## Success Criteria

The gate survives if:

- `working_set_accounting.json` contains all required accounting sections;
- every evidence request receives one of the preregistered classifications;
- recall provenance includes retrieval log entries for recalled records;
- at least one omitted context item and one truncation item are recorded;
- recovery and contamination metrics are computed deterministically;
- `analysis.md` states whether the matched working-set panel is ready and
  separates model, substrate, recall-protocol, prompt/schema, scorer, and
  inconclusive layers.

