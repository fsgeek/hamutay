# Scheduler Walk Context DES Pre-Registration

Date: 2026-06-05

## Research Question

Can the scheduler requested-context mechanism expose graph-neighborhood evidence
through `walk`, so a scheduled wake can inspect a fork-run graph hub without
hidden or ad hoc context injection?

The prior DES sequence established:

- fork-run final records can be projected into memory as graph-addressable
  records;
- `walk(mode="adjacent")` can recover hub-and-spoke neighborhoods;
- the production fork-run projection helper now writes natural hub edges.

However, scheduled events currently validate only `recall` and `compare` in
`requested_context`. That leaves a gap between graph-addressable continuity
evidence and the scheduler wake surface.

## Hypotheses

### H120: Scheduler requested_context accepts walk

If graph continuity is scheduler-addressable, then
`validate_requested_context()` should accept a `walk` request with a
`from_record_id`, `direction`, `depth`, and optional `mode`.

Falsification condition: a well-formed walk request is rejected.

### H121: Scheduler walk context resolves through memory tools

If the event runner can supply graph evidence to a wake, then
`resolve_requested_context()` should dispatch validated walk requests to
`tool_walk()` and return the normal walk result shape.

Falsification condition: a valid walk request returns an error, uses the wrong
tool surface, or drops the path result.

### H122: Event envelopes preserve walk request and result evidence

If walk context is model-facing rather than hidden, then
`build_event_envelope()` output should include both the original walk request
and the resolved walk result with adjacent fork-run endpoints.

Falsification condition: the rendered envelope omits the walk request, omits the
walk result, or cannot be parsed as JSON.

### H123: Invalid walk context is rejected before event persistence

If scheduler context validation remains protocol-strict, malformed walk requests
should fail validation before a pending event can be built.

Falsification condition: a walk request without `from_record_id`, with invalid
`direction`, invalid `mode`, unsupported extra keys, or invalid `depth` is
accepted.

## Experimental Design

Add `walk` as a first-class scheduler context tool with a deliberately narrow
parameter surface:

- required: `from_record_id`
- optional: `direction` (`forward`, `backward`, `both`; default delegated to
  `tool_walk`)
- optional: `depth`
- optional: `mode` (`path`, `adjacent`; default delegated to `tool_walk`)

Run a deterministic in-memory DES:

1. Build a successful fork-run final record with fixed endpoint record IDs.
2. Apply the production hub projection helper to an in-memory Apacheta bridge.
3. Build a pending event whose requested context is
   `walk(mode="adjacent", depth=1)` from the fork-run graph record.
4. Resolve requested context through `resolve_requested_context()`.
5. Render an event envelope through `build_event_envelope()`.
6. Validate that all planned hub endpoints are visible in the resolved context
   and rendered envelope.
7. Exercise malformed walk requests and confirm validation rejects them.

Conditions:

- in-memory Apacheta bridge only;
- no live provider calls;
- no Arango requirement;
- no model invocation;
- preserve existing `recall` and `compare` validation behavior.

## Expected Result

Expected before running: H120-H123 pass. If any fail, graph continuity remains
only partially integrated: the memory graph may be correct, but scheduled wakes
cannot request its evidence through the normal event substrate.

## Evaluation Artifacts

- event context validation/resolution updates;
- unit tests for scheduler walk context;
- `run_scheduler_walk_context_des.py`;
- `results.json`;
- `analysis.md`.
