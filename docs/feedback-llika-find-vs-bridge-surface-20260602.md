# Feedback: Llika `find` vs. the actual Hamut'ay bridge surface

**Date:** 2026-06-02
**Re:** `yanantin/docs/superpowers/specs/2026-06-02-llika-find-goal-focused-recall-design.md`
**From:** Hamut'ay side, grounded in a call-site census of `src/hamutay/apacheta_bridge.py`
and `src/hamutay/tools/memory.py` (not the spec's account of them — verify against code).

## TL;DR

The `find` spec is sound and worth building. The decomposition (verb on Llika, not a
catalog method on Apacheta), the axes, `find`-as-data-not-callable, the recall boundary,
`total_matched`, and the Indaleko observability obligation are all right.

**But the stated goal — "remove Hamut'ay's custom DB integration layer" — is over-claimed
by one step.** `find` replaces the *retrieval* half of the bridge. The *write* half stays
(correctly, per the spec's own scoping). And one load-bearing method — single-record
hydration by id — is **named in the spec but its post-migration owner is unspecified.**
Migration scope is therefore: search/traversal → Llika; write → Hamut'ay; hydrate-by-id →
decide. Not "delete the layer."

## The census (verifiable)

Bridge methods Hamut'ay actually invokes (from `grep` over `src/hamutay/`), by job:

| Method | Invocations | Job | Covered by `find`? |
|---|---|---|---|
| `retrieve(record_id)` | 6 | hydrate one full record by id | **No — see gap below** |
| `store_open_state` | 3 | write record **+ author REFINES edge** | No — out of scope (correct) |
| `query_open_has_field` | 3 | cross-session field-presence search | Yes → `filter {op: not_empty}` |
| `store_record` | 2 | generic write | No — write path |
| `query_open_by_lineage_tag` | 2 | tag-scoped search | Yes → `filter` axis |
| `store_edge` | 1 | author composition edge | No — write path |
| `query_open_by_author_instance` | 1 | session-scoped search | Yes → `filter` axis |
| `query_edges_by_endpoint` | 1 | traversal hop | Yes → `structure` axis / `walk` |
| `query_composition_graph` | 1 | full-graph read | Yes → `structure`/`walk` |

Instance-facing memory tools (`tools/memory.py`) that ride on these: `search_memory`
(→ content+filter axes), cross-session `recall` modes (→ `retrieve`), `walk`
(→ structure axis / `query_edges_by_endpoint`).

## Three buckets

**1. Retrieval — `find` covers it, and improves on it.** Today `search_memory` is a
Python substring scan over loaded records (the 3-min-scan pattern); the cross-session
query methods are ad-hoc. `find` is index-backed and collapses all of them into one verb.
This is a genuine upgrade, not parity. The instance-facing tools shrink to a single
`find` call. ✅

**2. Write path — stays in Hamut'ay, by the spec's own scoping (lines 386–401).**
`store_open_state` is not just a write: it authors the REFINES edge to the prior record
and carries the cross-cycle bookkeeping (`self._prior_id`, `ordering=cycle`,
`apacheta_bridge.py:195–310`). `find` reads, never writes. The new `store_turn`-like
wrapper is also Hamut'ay-side. So the bridge's write half survives the migration. This is
correct layering — flagging it only because "remove the layer" implies otherwise. ⚠️

**3. Single-record hydration by id — THE GAP.** `find` returns addresses + snippets,
**never full content** — the recall-boundary discipline, and it is correct. But after
search moves to `find`, Hamut'ay still needs to hydrate one record by id: today
`recall(record_id=…)` and the walk's node-read both call `bridge.retrieve(record_id)` →
`backend.get_record` (6 call sites — the single most-used bridge method). The spec names
this as "a separate deliberate `recall(record_id)`" (lines 180, 220, 402) and calls it
"the hand-off's existing principle, independent of this design" — but **it does not place
`recall`/`get` on Llika, and does not say whose method it is post-migration.** This is
the same shape as a husk: a capability named in prose with its owner unspecified.

## The one ask

Pin down the hydrate-by-id boundary. Two honest options:

- **(a)** Llika grows a `get(record_id) -> serializable record` verb (companion to `find`,
  the deliberate-hydration counterpart to find's address-only return). Then the bridge can
  go to ~zero on the read side, and the migration story is clean: search→`find`,
  hydrate→`get`, write→Hamut'ay.
- **(b)** Llika owns only `find`; Hamut'ay keeps a thin bridge for `retrieve` (and the
  write path). Smaller-than-today bridge, not deleted.

Either is fine. What is not fine is leaving it implicit — it is the difference between
"delete the bridge" and "shrink the bridge to store + get," and the success criterion of
the migration depends on which is true.

## Note

`find` is the right design and the retrieval upgrade is real. This note narrows the *claim*
about what gets removed; it does not argue against building `find`. Build it.
