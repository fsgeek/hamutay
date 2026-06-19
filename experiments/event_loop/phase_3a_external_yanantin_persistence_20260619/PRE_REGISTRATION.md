# Phase 3A External Persistent Yanantin Preregistration

Date: 2026-06-19

## Question

Does the Phase 2B Yanantin-backed multi-entity memory-pressure result survive a
file-backed persistent Yanantin backend boundary?

## Hypothesis

The event-loop memory contract remains viable when `ApachetaBridge.from_memory`
is replaced by `ApachetaBridge.from_duckdb`, provided that the test only
requires direct source-record persistence and explicit provenance rather than
open-record query helpers.

## Prediction

Basic writes and direct reads will pass. The main expected caveat is that
DuckDB open-record query helpers are explicitly deferred in Yanantin, so the
result should record that limitation rather than treating it as invisible.

## Method

Reuse the Phase 2B Yanantin-backed memory-pressure shape:

1. initialize a session with a persistent DuckDB-backed Apacheta bridge;
2. write three entity commitments;
3. reset current wake state before recall;
4. force recall through bridge fallback by hiding source records from
   in-session prior-state resolution;
5. run housekeeping and final synthesis;
6. close and reopen the DuckDB-backed bridge;
7. retrieve each source commitment record from the reopened bridge;
8. record operation latency, record counts, and open-query support status.

## Pass Criteria

Pass if all checks in `matrix.json` are true:

- Phase 2B event-sequence and provenance checks pass;
- persistent DB file exists;
- backend record counts include open records;
- reopened bridge retrieves all source commitment records;
- source commitment codes, entity IDs, and workstream IDs match expectations;
- operation latencies are captured;
- DuckDB open-query limitations are explicitly represented;
- failure attribution is empty.

## Failure Criteria

Fail on missing DB file, unrecoverable source records after reopen, provenance
loss, source identity drift, masked fallback, final citation failure, or
unattributed backend errors.

## Budget

Live direct-DeepSeek run budget: at most 9 model calls and at most 4 USD
estimated cost. Dry scripted runs make no model calls.
