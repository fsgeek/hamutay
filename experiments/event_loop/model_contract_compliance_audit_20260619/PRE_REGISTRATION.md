# Model Contract Compliance Audit Preregistration

Date: 2026-06-19

## Question

Were the Phase 3F reduced-scaffolding failures caused by basic model-contract
compliance failures, or did the model satisfy isolated contracts and fail only
under larger context/load pressure?

## Hypothesis

If the event-loop contract is viable but Phase 3F overloaded or under-specified
the model, isolated probes should pass. If one or more isolated probes fail,
the affected contract boundary needs stronger rails, clearer naming, or a
different representation before larger substrate-pressure tests can be
interpreted cleanly.

## Method

Run four isolated probes against the same event-loop machinery and terminal
surface style used by Phase 3F. The schemas require field names but do not
enumerate the target values. Exactness is scored after the run.

The probes are:

1. Vocabulary compliance.
2. Provenance label compliance.
3. Kind/source label compliance.
4. Count semantics compliance.

## Predictions

The most likely basic failures are action-label synonym drift, provenance
record-id substitution for labels, kind/source synonym drift, or class-count
versus record-count collapse. Passing all isolated probes would shift suspicion
toward context size, state accumulation, or multi-step workload pressure.

## Pass Criteria

Pass if all checks in `CONTRACT.md` are true.

## Failure Criteria

Fail if any check is false. Attribute failures to vocabulary compliance,
provenance label compliance, kind/source compliance, count semantics
compliance, model output, provider, artifact behavior, or inconclusive causes.

## Budget

Live direct-DeepSeek run budget: at most 5 model calls and at most 3 USD
estimated cost. Dry scripted runs make no model calls.
