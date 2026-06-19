# Phase 3D Durable Category-Ledger Preregistration

Date: 2026-06-19

## Question

Does a durable event-loop-owned category ledger repair the Phase 3D richer IPC
final-category failure?

## Hypothesis

If the prior Phase 3D failure was caused by final reconstruction load rather
than a deeper inability to read explicit state, then final synthesis should
preserve accepted, rejected, canceled, completed, evidence, and unsupported
claim categories when a correct durable ledger is supplied.

## Prediction

The durable ledger should repair the final category flattening. If final
synthesis still places rejected messages in accepted categories, promotes
unsupported candidates into unsupported claims, or drops summary provenance,
the weak axis is model/surface discipline rather than substrate fact loss.

## Method

Run the same eleven-event IPC ingress matrix as the split-final Phase 3D
baseline. After every completed event, the harness updates
`category_ledger.jsonl` deterministically. Category summary, claim audit, and
final synthesis are instructed to treat the durable ledger as authoritative
substrate-owned state.

The final artifact must carry forward ledger fields for accepted task
messages, accepted non-task messages, corrected messages, canceled messages,
rejected messages, completed messages, evidence citations, unsupported claim
candidates, unsupported claims, unresolved open items, and workstream status.

Clarification after the initial live run: final `summary_source_labels` is
constrained to the two split-summary labels, `category-summary` and
`claim-audit`, because the initial surface did not enumerate the permitted
provenance labels.

## Pass Criteria

Pass if all contract checks in `CONTRACT.md` are true.

## Failure Criteria

Fail if any pass criterion is false. Attribute failures to category ledger,
IPC ingress, message routing, workstream isolation, continuation binding,
scheduler identity, model output, provider transport, or artifact/scorer
behavior.

## Budget

Live direct-DeepSeek run budget: at most 12 model calls and at most 5 USD
estimated cost. Dry scripted runs make no model calls.
