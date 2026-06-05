# Fork Run Hub Projection DES Pre-Registration

Date: 2026-06-05

## Research Question

Can the fork-run graph projection helper switch from the temporary spine
projection back to natural hub-and-spoke edges now that
`walk(mode="adjacent")` exists?

The previous graph projection DES made fork-run records graph-addressable, but
used a deterministic spine because the old walk tool followed a single path.
The walk adjacency DES added bounded adjacent traversal. This experiment tests
whether the production projection helper can now use direct edges from the
fork-run record to every endpoint.

## Hypotheses

### H116: Projection helper writes hub-and-spoke edges

If the helper has been revised, then every graph edge in
`apply_fork_run_graph_plan()` should originate from the fork-run graph record,
not from the previously linked endpoint.

Falsification condition: any projected edge or suppression edge has
`from_record_id` other than the fork-run graph record ID.

### H117: Adjacent walk recovers all hub endpoints

If hub projection is compatible with the new traversal surface, then
`walk(mode="adjacent", depth=1)` from the fork-run graph record should recover
all planned endpoints in success and failure scenarios.

Falsification condition: any planned endpoint is missing from adjacent walk.

### H118: Default path walk remains single-path compatible

If hub projection relies on explicit adjacent mode, then default path walk from
the fork-run graph record should still return only one path endpoint.

Falsification condition: default walk returns all hub endpoints or changes
shape.

### H119: Failure hub projection preserves suppression disposition

If failure disposition is represented naturally, then the failed fork-run hub
projection should include a directly adjacent suppression node whose content
names the suppressed sibling event and suppression source.

Falsification condition: suppression node is missing, not adjacent to the
fork-run graph record, or lacks suppressed event/source fields.

## Experimental Design

Revise `apply_fork_run_graph_plan()` so all planned endpoint edges and
suppression edges originate from the fork-run graph record. Keep
`build_fork_run_graph_plan()` deterministic and unchanged except where needed
for the new application shape.

Run deterministic in-memory graph scenarios:

- successful fork-run hub projection;
- failed fork-run hub projection with suppression node;
- compare default path walk and adjacent walk from the same fork-run graph
  record.

Conditions:

- in-memory Apacheta bridge only;
- no live provider calls;
- no Arango requirement;
- preserve existing path walk behavior.

## Expected Result

Expected before running: H116-H119 pass. If this fails, the helper should retain
spine projection or the adjacent traversal semantics are insufficient for the
production projection shape.

## Evaluation Artifacts

- projection helper and unit test updates;
- `run_fork_run_hub_projection_des.py`;
- `results.json`;
- `analysis.md`.
