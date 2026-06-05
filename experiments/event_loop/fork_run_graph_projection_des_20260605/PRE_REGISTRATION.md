# Fork Run Graph Projection DES Pre-Registration

Date: 2026-06-05

## Research Question

Can a durable fork-run identity record be projected into the existing
Apacheta-style memory graph as a walkable object without adding a new backend?

The prior DES created append-only `.fork_runs.jsonl` sidecars. That made
fork/run identity durable locally, but not yet visible to graph tools such as
`recall(record_id)` and `walk(from_record_id)`. This experiment tests the
smallest graph-shaped projection that can reuse existing bridge primitives.

## Hypotheses

### H108: Fork-run records can be stored as graph-addressable records

If fork-run identity can enter the memory graph, then the final fork-run record
should store through `ApachetaBridge.store_instance_record()` and return a UUID
that can be retrieved by `bridge.retrieve(record_id)`.

Falsification condition: the fork-run graph record is not stored, lacks
`fork_run_id`, or cannot be retrieved by UUID.

### H109: Successful fork-run graph projection is walkable

If a successful fork-run graph projection is sufficient, then walking from the
fork-run graph record should reach coordinator root, branch result records, and
join result record using explicit composition edges.

Falsification condition: walk from the fork-run record cannot reach all expected
success endpoints, or endpoint roles are missing from the projected graph
record.

### H110: Failed fork-run graph projection preserves failure disposition

If failure disposition is graph-addressable, then walking from the failed
fork-run graph record should reach the failed branch wake record and a
suppression/disposition record that names the suppressed sibling event.

Falsification condition: failed branch source, suppression disposition, or
suppressed sibling event cannot be recovered from the graph projection.

### H111: Projection is backend-optional and deterministic

If the graph projection is a correct boundary layer, then it should produce a
deterministic operation plan before applying it to a bridge, and applying that
plan to an in-memory bridge should not require Arango/Apacheta services.

Falsification condition: projection requires a live external backend, operation
plan contents vary across repeated construction from the same run record, or
bridge application produces a different endpoint set than the plan.

## Experimental Design

Add graph-projection helpers that:

- build a deterministic operation plan from a final fork-run record;
- store the final fork-run record as an instance-authored graph record;
- optionally store a compact suppression/disposition record;
- author explicit composition edges from the fork-run record to coordinator,
  branch results, join result, failed wake, and suppression record using
  existing relation types;
- verify graph traversal through an in-memory `ApachetaBridge`.

Run deterministic simulated-time success and failure scenarios equivalent to
the fork-run identity DES, then project the final fork-run records into an
in-memory graph seeded with the referenced coordinator/branch/join records.

Conditions:

- deterministic fake backend;
- simulated time;
- in-memory Apacheta bridge only;
- no live provider calls;
- no Arango requirement.

## Expected Result

Expected before running: H108-H111 pass. If this fails, fork-run identity is
durable locally but not yet compatible with the memory graph substrate.

## Evaluation Artifacts

- graph projection implementation and unit tests;
- `run_fork_run_graph_projection_des.py`;
- scenario JSONL logs;
- graph projection results;
- `results.json`;
- `analysis.md`.
