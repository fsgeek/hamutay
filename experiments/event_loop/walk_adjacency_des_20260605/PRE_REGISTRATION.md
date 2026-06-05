# Walk Adjacency DES Pre-Registration

Date: 2026-06-05

## Research Question

Should `walk(from_record_id)` support bounded adjacency/BFS semantics so
fork-run graph records can be represented as natural hub-and-spoke objects
instead of deterministic spines?

The prior graph projection DES showed that fork-run graph records are
addressable, but current walk semantics follow a single path. A star projection
from the fork-run node only reaches one endpoint. This experiment tests an
explicit traversal mode that preserves existing path behavior while adding
adjacency traversal for graph-shaped run objects.

## Hypotheses

### H112: Adjacent walk recovers all first-hop fork-run endpoints

If `walk(mode="adjacent")` supports adjacency traversal, then walking forward
from a fork-run graph record with hub-and-spoke edges should return every
first-hop endpoint: coordinator root, branch results, join result, and
suppression record when present.

Falsification condition: any directly adjacent projected endpoint is missing.

### H113: Default path walk remains backward compatible

If adjacency is an added mode rather than a semantic replacement, then the
existing default `walk(from_record_id)` behavior should still return a
single-path result for the same star graph.

Falsification condition: default path walk returns all adjacent endpoints or
changes its result shape.

### H114: Adjacent walk is bounded and cycle-safe

If adjacency traversal is safe for graph use, then a graph with cycles should
not repeat already visited records and should respect the requested depth.

Falsification condition: repeated record IDs appear in the path, traversal loops,
or depth is ignored.

### H115: Hub-and-spoke fork-run projection can replace spine projection

If adjacency walk works, then a fork-run graph projection can use direct edges
from the fork-run record to every endpoint and still recover the same endpoint
set as the prior spine projection.

Falsification condition: hub-and-spoke projection cannot recover success and
failure endpoint sets with adjacency walk.

## Experimental Design

Add an optional `mode` parameter to `walk`:

- default/path mode preserves current single-path semantics;
- `mode="adjacent"` performs bounded BFS-style traversal over all matching
  adjacent edges up to `depth`;
- each returned step includes `record_id`, `edge_type`, `edge_source`, `depth`,
  field names, and summary.

Then run a deterministic in-memory graph experiment:

- seed fork-run success and failure endpoint records;
- build direct hub-and-spoke edges from fork-run record to endpoints;
- compare default path walk against adjacent walk;
- include a cyclic graph case to verify visited-set and depth behavior.

Conditions:

- in-memory Apacheta bridge only;
- no live provider calls;
- no Arango requirement;
- preserve existing path behavior unless `mode="adjacent"` is requested.

## Expected Result

Expected before running: H112-H115 pass. If this fails, fork-run graph
projection should continue using a spine or the graph tool surface needs a
different traversal primitive.

## Evaluation Artifacts

- `walk` implementation and schema/test updates;
- `run_walk_adjacency_des.py`;
- `results.json`;
- `analysis.md`.
