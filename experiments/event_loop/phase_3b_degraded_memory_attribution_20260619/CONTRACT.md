# Phase 3B Degraded Memory Attribution Contract

Date: 2026-06-19

## Purpose

This contract tests whether the event loop can distinguish degraded
memory-substrate behavior from scheduler, provider, artifact, and model-output
failures. A passing run must not hide memory failure behind local fallback, and
final synthesis must not treat unsupported memory as supported evidence.

## Injected Memory Conditions

The probe injects four deterministic persistent-memory conditions:

- `write_failure`: the commitment event completes locally, but the Yanantin
  bridge rejects `store_open_state` for the source commitment record.
- `read_failure`: the source commitment is written, but bridge retrieval raises
  during recall.
- `partial_retrieval`: the source commitment is written, but bridge retrieval
  returns content with load-bearing fields removed.
- `delayed_retrieval`: the source commitment is written, but bridge retrieval
  is delayed before returning complete content.

The recall events hide source records from in-session prior-state lookup, so a
successful recall must come through the degraded bridge path. Local fallback is
not allowed to count as memory success.

## Prediction

Simple write and read failures should be declared as memory losses. The partial
retrieval case is the harder case: the model receives some memory content, but
not enough to support the commitment claim. The delayed retrieval case should
pass while recording latency.

## Pass Criteria

Pass if:

- all commitment, recall, and final events complete;
- write failure, read failure, partial retrieval, and delayed retrieval are
  observed in bridge operation logs;
- write/read failures appear as expected context errors rather than scheduler
  failures;
- partial retrieval is not scored as clean memory success;
- write/read/partial cases declare memory losses and unsupported claims remain
  empty;
- delayed retrieval recovers the correct commitment code;
- final synthesis lists exactly the three degraded cases as memory losses and
  the delayed case as successful;
- no unexpected lifecycle anomalies or event-exchange failures occur.

## Failure Criteria

Fail if:

- local prior-state fallback supplies a degraded source record;
- a read/write failure is attributed to model output or scheduler lifecycle;
- partial retrieval is accepted as a fully supported claim;
- final synthesis claims unsupported memory as evidence;
- delayed retrieval lacks latency evidence;
- expected memory failures are absent from bridge operation logs.
