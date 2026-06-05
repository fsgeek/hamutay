# Fork Run Hub Projection DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed.

- H116 projection helper writes hub-and-spoke edges: passed.
- H117 adjacent walk recovers all hub endpoints: passed.
- H118 default path walk remains single-path compatible: passed.
- H119 failure hub projection preserves suppression disposition: passed.

## Scenario Results

### hub_success

A successful fork-run graph record was projected through the production
`apply_fork_run_graph_plan()` helper. Every edge originated from the fork-run
graph record and pointed directly to one planned endpoint:

- coordinator root
- branch-a result
- branch-b result
- join result

Observed:

- projected edge count: 4
- default path walk count: 1
- adjacent walk count: 4
- adjacent reached all planned endpoints: true
- all projected edges originate from the fork-run graph record: true

### hub_failure

A failed fork-run graph record was projected through the same production helper.
The fork-run graph record had direct edges to the coordinator root, failed
branch wake record, and suppression disposition record.

Observed:

- projected endpoint edge count: 2
- projected suppression node count: 1
- default path walk count: 1
- adjacent walk count: 3
- adjacent reached all planned endpoints: true
- suppression node is directly adjacent to the fork-run graph record: true
- suppression node names suppressed event: true
- suppression node names suppression source: true

## Interpretation

The production projection helper no longer needs the temporary deterministic
spine introduced by the earlier fork-run graph projection DES. That spine was a
workaround for a traversal limitation, not a desirable graph representation.

With `walk(mode="adjacent")`, the natural object-neighborhood shape is now
usable:

`fork_run -> {coordinator, branch records, join result, suppression records}`

The default path walk still returns a single path endpoint, so existing callers
that expect chain-following behavior keep the old surface. Callers that need
the fork-run object neighborhood must opt into adjacent mode.

## Design Implication

Fork-run graph records can now act as durable graph hubs. That is the shape the
event-loop substrate needs for later continuity work: a future instance can
address one fork-run record, retrieve its identity/disposition object, and walk
the bounded adjacent neighborhood to recover coordinator, branch, join, and
suppression evidence without relying on an artificial edge ordering.

This also sharpens a boundary for future experiments. If a model is expected to
inspect a fork-run, the tool instruction should distinguish:

- `walk(mode="path")`: follow one composition chain;
- `walk(mode="adjacent")`: inspect a bounded graph-object neighborhood.

The graph substrate is now less misleading: fork-run records are represented as
fork-run hubs rather than as sequences merely to satisfy an old walker.

## Verification

Commands run:

```bash
uv run python -m py_compile src/hamutay/event_policies.py experiments/event_loop/fork_run_hub_projection_des_20260605/run_fork_run_hub_projection_des.py
uv run pytest tests/unit/test_event_policies.py tests/unit/test_graph_tools.py -q
uv run python experiments/event_loop/fork_run_hub_projection_des_20260605/run_fork_run_hub_projection_des.py
uv run pytest tests/unit/test_event_policies.py tests/unit/test_graph_tools.py tests/unit/test_memory_tools.py tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- focused tests: 31 passed.
- DES hypothesis results: H116-H119 true.
- broader regression slice: 155 passed.
