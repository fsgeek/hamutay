# Fork Run Graph Projection DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed after two preserved harness/scorer
corrections.

- H108 fork-run records can be stored as graph-addressable records: passed.
- H109 successful fork-run graph projection is walkable: passed.
- H110 failed fork-run graph projection preserves failure disposition: passed.
- H111 projection is backend-optional and deterministic: passed.

## Preserved Corrections

Two initial runs are preserved:

- `initial_json_serialization_*`: graph projection succeeded far enough to build
  payloads, but `results.json` serialization failed because retrieved Apacheta
  provenance contained UUID objects. The runner now serializes with
  `default=str`.
- `initial_truthy_scorer_*`: the corrected serialization run produced truthy
  UUID/list values for H108-H110 rather than strict booleans. The scorer now
  wraps those fields with `bool(...)`.

The unit test phase also exposed a more substantive graph-shape issue. A star
projection from the fork-run node only reached the first endpoint because
`tool_walk(from_record_id)` follows a single path, not all adjacent edges. The
projection was changed to write a deterministic spine:

`fork_run -> coordinator/root -> branch... -> join/suppression`

That makes every projected endpoint reachable through the current walk
semantics. A future graph walker with adjacency or BFS semantics could support a
more natural star projection.

## Scenario Results

### graph_projection_success

Classification: `joined`

The final fork-run record was stored through an in-memory `ApachetaBridge` as an
instance-authored graph record. The projection then authored edges through the
coordinator root, both branch result records, and the join result record.

Observed:

- graph fork-run record: present and retrievable
- planned endpoint count: 4
- reached endpoint count: 4
- reached all planned endpoints: true
- plan deterministic: true

### graph_projection_failure

Classification: `branch_failed`

The failed fork-run record was stored as a graph record, then linked through the
coordinator root, failed branch wake record, and a compact suppression record.
The suppression record names the suppressed sibling event and suppression
source.

Observed:

- graph fork-run record: present and retrievable
- planned endpoint count: 3
- reached endpoint count: 3
- suppression graph node: present
- reached all planned endpoints: true
- plan deterministic: true

## Interpretation

Fork-run identity is now compatible with the memory graph substrate in the
deterministic in-memory case. A later process can address the run by graph
record UUID, retrieve the fork-run object, and walk to the coordinator, branch,
join, or suppression evidence.

This does not require Arango or a live Apacheta service. The projection produces
a deterministic operation plan first, then applies it to any bridge that
supports `store_instance_record`, `store_edge`, `retrieve`, and
`query_edges_by_endpoint`.

The main design caveat is graph shape. Current `tool_walk` is path-oriented, so
the projection writes a path/spine. If we want fork runs to be represented as
natural hub-and-spoke objects, the walker needs adjacency-list or bounded BFS
semantics.

## Design Implication

The event-loop substrate now has a chain from DES scheduling through graph
addressability:

1. simulated-time event execution;
2. bounded autonomy and terminal disposition;
3. branch-private fork/join policy;
4. durable fork-run identity;
5. graph-addressable fork-run projection.

The next research question is probably not another local DES capability. The
remaining boundary is whether graph traversal semantics should change from
single-path walk to adjacency/BFS before live-provider or long-horizon fork
experiments depend on the graph representation.

## Verification

Command run:

```bash
uv run pytest tests/unit/test_event_policies.py tests/unit/test_graph_tools.py tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py
```

Result: 96 passed.
