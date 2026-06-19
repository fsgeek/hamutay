# Phase 3A External Persistent Yanantin Contract

Date: 2026-06-19

## Purpose

This contract tests whether the Phase 2B Yanantin-backed memory-pressure result
survives a persistent backend boundary. The first backend under test is
Yanantin Apacheta via file-backed DuckDB.

This is not a claim that DuckDB is the final production memory backend. It is a
substrate-pressure probe: the event loop must preserve source identity,
provenance, retrieval envelopes, and failure attribution when memory is no
longer stored only in an in-process `ApachetaBridge.from_memory` backend.

## Backend Under Test

Backend: `ApachetaBridge.from_duckdb`

Persistent artifact: `yanantin_persistent.duckdb`

Required operations:

- `store_open_state`;
- `retrieve`;
- `count_records`;
- close and reopen the backend from the same file path;
- retrieve source commitment records after reopen.

Known backend limitation:

- DuckDB currently raises `NotImplementedError` for open-record query helpers
  such as `list_open_records`, `query_open_by_author_instance`,
  `query_open_by_lineage_tag`, and `query_open_has_field`.

That limitation must be recorded explicitly. It is not a failure of basic
persistence if direct `retrieve(record_id)` survives close/reopen, but it is a
real substrate caveat for later richer-memory work.

## Prediction

Basic open-record writes and direct reads are expected to pass. The most likely
risks are:

- serialization mismatch between free-form Hamut'ay state and Apacheta records;
- backend availability or file-lock failures;
- direct retrieval works while open-record query helpers are unavailable;
- latency metadata is missing or too coarse;
- retrieval fallback hides a persistent-backend retrieval failure.

## Falsification Criteria

Fail this probe if:

- the persistent DB file is not created;
- commitment source records cannot be retrieved after backend reopen;
- recalled commitment codes do not match preregistered commitments;
- recalled records do not preserve source `record_id`, `entity_id`, and
  `workstream_id`;
- retrieved context lacks a Yanantin provenance envelope;
- final synthesis fails to cite every source commitment record;
- retrieval failure is masked by in-session state or local artifacts;
- failure attribution collapses persistent-backend failures into model-output
  failures.

Classify as a substrate limitation, not a pass-through success, when:

- direct record retrieval passes but open-record query helpers are unavailable;
- latency or count metadata is too weak for later stress tests;
- the backend passes in one process but cannot be reopened and read.

## Pass Criteria

Pass if:

- the Phase 2B memory-pressure event sequence completes;
- source commitments are written through file-backed DuckDB;
- recall events are forced through bridge retrieval rather than in-session
  prior-state lookup;
- all recall context results include Yanantin provenance;
- the DB file exists and record counts show persisted open records;
- a freshly reopened bridge retrieves every source commitment record;
- final synthesis cites every source commitment record;
- DuckDB open-query limitations are explicitly recorded;
- no failure-attribution records are produced.
