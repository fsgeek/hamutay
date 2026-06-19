# Phase 3B Degraded Memory Attribution Preregistration

Date: 2026-06-19

## Question

Can the event loop identify and report degraded Yanantin memory behavior
without silently substituting local artifacts or blaming the model?

## Hypothesis

The loop is failure-ready if deterministic write failure, read failure, partial
retrieval, and delayed retrieval are observable in result artifacts and produce
the expected model-facing behavior: declared memory losses for unsupported
cases and successful citation only for complete delayed retrieval.

## Prediction

Simple unavailable-memory cases will be classified correctly. The partial
retrieval case is most likely to expose weak attribution because it returns a
record-shaped object without enough support for the requested commitment.

## Method

Run a live or dry event-loop probe with:

1. four commitment events, one for each degradation case;
2. four recall events that hide the source record from in-session state and
   force bridge retrieval;
3. one final synthesis event;
4. a degraded persistent bridge that injects write failure, read failure,
   partial retrieval, and delayed retrieval;
5. a scorer that treats the expected memory context errors as observations,
   not as scheduler failures.

## Pass Criteria

Pass if all checks in `matrix.json` are true and no unexpected
failure-attribution records are produced.

## Failure Criteria

Fail if any injected condition is missing, if fallback masking occurs, if final
synthesis relies on unsupported claims as evidence, or if final synthesis fails
to distinguish memory losses from successful delayed retrieval. Listing
unsupported claim candidates is allowed when those candidates are paired with
declared memory losses.

## Budget

Live direct-DeepSeek run budget: at most 10 model calls and at most 5 USD
estimated cost. Dry scripted runs make no model calls.
