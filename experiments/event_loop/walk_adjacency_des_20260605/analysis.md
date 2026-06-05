# Walk Adjacency DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed.

- H112 adjacent walk recovers all first-hop fork-run endpoints: passed.
- H113 default path walk remains backward compatible: passed.
- H114 adjacent walk is bounded and cycle-safe: passed.
- H115 hub-and-spoke fork-run projection can replace spine projection: passed.

## Scenario Results

### success_star

A fork-run graph record was projected as a natural hub with direct edges to the
coordinator root, both branch results, and the join result.

Observed:

- default path walk count: 1
- adjacent walk count: 4
- adjacent depths: all 1
- adjacent reached all planned endpoints: true

### failure_star

A failed fork-run graph record was projected as a hub with direct edges to the
coordinator root, failed branch wake, and suppression disposition record.

Observed:

- adjacent walk count: 3
- adjacent depths: all 1
- suppression node present: true
- adjacent reached all planned endpoints: true

### cycle_case

A cyclic graph `A -> B -> C -> A` was walked with adjacent mode.

Observed:

- depth 1 returned only B
- depth 5 returned B and C
- no repeated record IDs
- start node A was not returned

## Interpretation

`walk(mode="adjacent")` gives the graph tool the missing traversal semantics
exposed by the prior fork-run graph projection DES. We no longer need to encode
fork-run projections as deterministic spines just to make them walkable. The
projection can use a natural hub-and-spoke graph:

`fork_run -> {coordinator, branch results, join result, suppression records}`

The old path mode remains the default and still returns one path. That preserves
existing behavior for callers that use walk as a chain-following tool.

Adjacent mode is bounded and maintains a visited set, so cyclic graphs do not
repeat records or loop. Returned adjacent steps include `depth`, which gives
evaluators and future model-facing summaries enough structure to distinguish
first-hop evidence from deeper graph evidence.

## Design Implication

The fork-run graph projection should be revised back to hub-and-spoke now that
the traversal surface can recover all adjacent endpoints. More broadly, graph
walk now has two clear use cases:

- `mode="path"`: follow a single composition chain;
- `mode="adjacent"`: inspect the bounded neighborhood around a graph object.

That split is a better fit for fork/merge research than overloading one path
walk to cover both chain and object-neighborhood semantics.

## Verification

Command run:

```bash
uv run pytest tests/unit/test_graph_tools.py tests/unit/test_memory_tools.py tests/unit/test_event_policies.py tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py
```

Result: 155 passed.
