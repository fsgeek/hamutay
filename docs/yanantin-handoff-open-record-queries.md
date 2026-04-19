# Yanantin Hand-off: Open-Record Query Methods

**Date:** 2026-04-19
**Requesting project:** Hamutay (cross-session memory — Phase 3a)
**Delta:** 5 new abstract methods on `ApachetaInterface`, implementations in memory + arango backends, `NotImplementedError` in duckdb.

---

## Motivation (from yanantin's side)

`ApachetaInterface` currently exposes `store_record(UUID, ApachetaBaseModel)` and `get_record(UUID)` for the open-records collection — generic storage for records that don't fit a prescribed schema. These are the only entry points to that collection. Every other query method on the interface targets typed collections (`TensorRecord`, `CompositionEdge`, `CorrectionRecord`, etc.).

Hamutay stores free-form `taste_open` session state into the open-records collection via `store_record`. For a second instance (new session, new ghola) to read those records, the interface needs query surface over the open collection parallel to what exists for typed collections. Without this, the open collection is write-only from the caller's perspective — you can put records in and get them back by UUID, but you can't discover UUIDs you don't already hold.

This hand-off is the minimum surface to unblock cross-session read access. It does **not** add write methods, edge queries, or AQL optimizations — those are explicitly out of scope.

---

## Scope

Five new abstract methods on `ApachetaInterface`, added in a new section `# ── Open-Record Queries ──`:

| Method | Purpose |
|---|---|
| `list_open_records(limit)` | All records in the open collection, newest first |
| `query_open_by_author_instance(author_instance_id, limit)` | Records whose provenance envelope carries the given author_instance_id |
| `query_open_by_lineage_tag(tag, limit)` | Records whose lineage_tags carries the given tag |
| `query_open_has_field(field, limit)` | Records whose `model_extra` contains the given key |
| `list_author_instances()` | All distinct author_instance_id values present in the open collection |

All query methods return `list[tuple[UUID, ApachetaBaseModel]]` — callers address records by UUID without parsing the model's provenance. `list_author_instances` returns `list[str]`.

`limit: int | None = None` across the board; `None` means no limit. Filter applied after ordering.

**Vocabulary:** method names use yanantin's primitives (`author_instance`, not `session`). Translation to caller vocabulary lives at the boundary — hamutay's bridge will expose `session_id` to its callers and pass it through as `author_instance_id`.

**Conventional, not structural:** provenance envelopes and `lineage_tags` are carried by convention, not enforced by `ApachetaBaseModel`. Implementations probe `model_extra` (or the attribute, where present), skip records that lack the probed field, and do not raise. Docstrings read "records whose envelope carries X" rather than "records authored by X." If hamutay (or any caller) needs structural guarantees about authorship, that's a separate conversation about a typed subclass of `ApachetaBaseModel` — not this hand-off.

---

## Signatures (copy into `src/yanantin/apacheta/interface/abstract.py`)

Append below existing query methods, above `count_records`:

```python
    # ── Open-Record Queries ──────────────────────────────────────
    # Queries over the open-schema records collection — records stored
    # via store_record() that don't fit a prescribed schema. Added
    # for hamutay's taste_open cross-session memory access.

    @abstractmethod
    def list_open_records(
        self,
        limit: int | None = None,
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """All records in the open-records collection, newest first.

        Returns (record_id, record) pairs so callers can address records
        by UUID without parsing the model's provenance. limit is applied
        after ordering — None means no limit.
        """
        ...

    @abstractmethod
    def query_open_by_author_instance(
        self,
        author_instance_id: str,
        limit: int | None = None,
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """Records whose provenance envelope carries the given author_instance_id.

        Provenance is conventional, not structural — records without a
        provenance envelope (or without author_instance_id inside it) are
        skipped, not raised on. Callers needing structural guarantees
        should use a typed subclass of ApachetaBaseModel.
        """
        ...

    @abstractmethod
    def query_open_by_lineage_tag(
        self,
        tag: str,
        limit: int | None = None,
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """Records whose lineage_tags carries the given tag.

        lineage_tags is conventional — records without the field are skipped.
        """
        ...

    @abstractmethod
    def query_open_has_field(
        self,
        field: str,
        limit: int | None = None,
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """Records whose model_extra (free-form fields) contains `field`.

        Open records use ApachetaBaseModel with `extra='allow'`, so free-form
        keys live in `model_extra`. This query returns records that carry
        a given key, regardless of its value.
        """
        ...

    @abstractmethod
    def list_author_instances(self) -> list[str]:
        """All distinct author_instance_id values present in the envelopes
        of the open records collection. Records without provenance are
        skipped. For cross-instance discovery."""
        ...
```

---

## Integration notes (verified against current yanantin)

- `ApachetaBaseModel` is configured with `extra="allow"` (`models/base.py:15-17`). Free-form fields land in pydantic's `model_extra`, which is what `query_open_has_field` inspects.
- `ProvenanceEnvelope.author_instance_id` is a `str` field already in use.
- `lineage_tags` is a tuple field on `ApachetaBaseModel`.
- `store_record` and `get_record` already exist on the interface; no changes to write-side.

---

## Backend obligations

### Memory backend (`backends/memory.py`) — full implementation

Dict iteration over the backend's internal record store. Insertion order gives a reasonable "newest first" via `reversed()`. Uses `self._lock` and the existing `self._deep_copy` helper so returns don't alias stored records.

### Arango backend (`backends/arango.py`) — full implementation

**AQL-native filters with indexes on the filtered fields.** The obfuscator's collection-name translation (`self._map.collection_name(...)`) already has precedent; the same mechanism should extend to field paths (`provenance.author_instance_id` → obfuscated dotted path). If `self._map` doesn't yet expose `field_name(...)` or equivalent, adding that capability is part of this hand-off — it is strictly more valuable than a query implementation we will rewrite.

Create indexes on:
- `provenance.author_instance_id` (for `query_open_by_author_instance` and `list_author_instances`)
- `lineage_tags` (array field; for `query_open_by_lineage_tag`)

`query_open_has_field` queries `model_extra`-level keys, which land as top-level fields on the Arango document due to `extra='allow'`. AQL can filter with `HAS(doc, @field)` (translated through the obfuscator for stored field names). Indexing here is a judgment call — if typical callers probe a small stable set of extra fields, index those; otherwise leave unindexed and accept the collection scan for this one query.

**Why not load-all-and-filter:** proposed and rejected previously. The open collection grows monotonically (immutable, no delete), so every query pulling the whole collection degrades as the system is used. Taste_open instances call these methods during live cycles where latency is experience-facing. Consistency with `list_tensors()` is not a rationale — if anything, `list_tensors()` is a candidate for the same treatment, separately.

Uses `self._map.collection_name("records")` for the obfuscated collection name and `self._from_generic_doc` for hydration. Ordering: sort by insertion-time proxy (document `_rev` or, preferably, a `created_at` field if one can be added to `ApachetaBaseModel` — out of scope here, flag if it blocks).

### DuckDB backend (`backends/duckdb.py`) — explicit `NotImplementedError`

All five methods raise `NotImplementedError("DuckDB open-record queries deferred. Use Arango or memory backend.")`. Rationale: graph-shaped queries over SQL require recursive CTEs that don't compose cleanly with filters. Partial impls would be worse than honest deferral. A follow-up plan can fill these in if DuckDB becomes a tier-A target for hamutay.

---

## Acceptance tests (contract)

These are the assertions any implementation must pass. Memory backend runs them as unit tests; arango runs them as integration tests with a live Arango container.

```python
def _make_record(session_id, tags, **extras):
    prov = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id=session_id,
        predecessors_in_scope=(),
    )
    return ApachetaBaseModel(provenance=prov, lineage_tags=tags, **extras)


def test_list_open_records_returns_all():
    # Two records stored; both returned with their UUIDs
    backend = InMemoryBackend()
    id_a, id_b = uuid4(), uuid4()
    backend.store_record(id_a, _make_record("s1", ("hamutay",)))
    backend.store_record(id_b, _make_record("s2", ("hamutay",)))
    results = backend.list_open_records()
    assert {rid for (rid, _) in results} == {id_a, id_b}


def test_list_open_records_respects_limit():
    backend = InMemoryBackend()
    for _ in range(5):
        backend.store_record(uuid4(), _make_record("s1", ()))
    assert len(backend.list_open_records(limit=2)) == 2


def test_query_open_by_author_instance_filters():
    backend = InMemoryBackend()
    id_s1_a, id_s1_b, id_s2 = uuid4(), uuid4(), uuid4()
    backend.store_record(id_s1_a, _make_record("s1", ()))
    backend.store_record(id_s1_b, _make_record("s1", ()))
    backend.store_record(id_s2, _make_record("s2", ()))
    results = backend.query_open_by_author_instance("s1")
    assert {rid for (rid, _) in results} == {id_s1_a, id_s1_b}


def test_query_open_by_author_instance_skips_records_without_provenance():
    """Provenance is conventional: records without it are skipped, not raised on."""
    backend = InMemoryBackend()
    id_with = uuid4()
    id_without = uuid4()
    backend.store_record(id_with, _make_record("s1", ()))
    # A record stored without provenance should not appear in any author filter
    backend.store_record(id_without, ApachetaBaseModel(lineage_tags=()))
    results = backend.query_open_by_author_instance("s1")
    assert {rid for (rid, _) in results} == {id_with}


def test_query_open_by_lineage_tag():
    backend = InMemoryBackend()
    id_a, id_b = uuid4(), uuid4()
    backend.store_record(id_a, _make_record("s1", ("hamutay", "cycle-5")))
    backend.store_record(id_b, _make_record("s1", ("hamutay", "cycle-6")))
    results = backend.query_open_by_lineage_tag("cycle-5")
    assert {rid for (rid, _) in results} == {id_a}


def test_query_open_has_field():
    backend = InMemoryBackend()
    id_a, id_b = uuid4(), uuid4()
    backend.store_record(id_a, _make_record("s1", (), theme="opening"))
    backend.store_record(id_b, _make_record("s1", ()))  # no 'theme'
    results = backend.query_open_has_field("theme")
    assert {rid for (rid, _) in results} == {id_a}


def test_list_author_instances_distinct():
    backend = InMemoryBackend()
    backend.store_record(uuid4(), _make_record("s1", ()))
    backend.store_record(uuid4(), _make_record("s1", ()))
    backend.store_record(uuid4(), _make_record("s2", ()))
    assert set(backend.list_author_instances()) == {"s1", "s2"}


def test_duckdb_raises_not_implemented():
    backend = DuckDBBackend(db_path=":memory:")
    with pytest.raises(NotImplementedError):
        backend.list_open_records()
```

For arango, wrap each test in a fixture that cleans up records by `_key` after the run. Use a `pytest.mark.skipif(os.environ.get("APACHETA_SKIP_ARANGO") == "1", ...)` guard so CI without a container can skip.

---

## Non-goals (explicit)

- **No DuckDB open-record queries.** Deferred via explicit `NotImplementedError`.
- **No new write methods.** `store_record` is sufficient; `store_composition_edge` already exists.
- **No new edge queries.** Phase 3a's edge-authoring needs can be served by `query_composition_graph` (filtered in the bridge) for v1.
- **No obfuscation-layer changes.** Query methods respect existing obfuscation by going through `self._map.collection_name(...)`.
- **No ordering guarantees beyond "newest first, best-effort."** Strict ordering requires a timestamp field not yet in the model.

---

## Reference: hamutay-side consumer

For context on why these methods matter: hamutay's `apacheta_bridge.py` will wrap these pass-through, and the memory tools (`recall`, `search_memory`, `walk`, `memory_schema`) will gain a `scope` parameter that routes `scope="cross_session"` and `scope="all"` through them. Plan doc: `docs/superpowers/plans/2026-04-19-cross-session-memory-phase3.md` (hamutay). A yanantin maintainer does not need to read it to implement this hand-off.

---

## Commit identity

Yanantin recent commits author as `yanantin@wamason.com`, `Tony Mason`, signed. Match that — do not use hamutay's email (`hamutay@wamason.com`).

```bash
cd /home/tony/projects/yanantin
git -c user.email=yanantin@wamason.com -c user.name="Tony Mason" commit -S -m "..."
```

---

## Suggested commit sequence

1. `feat(interface): add open-record query methods` — abstract methods only
2. `feat(memory backend): open-record queries` — memory impl + tests
3. `feat(arango): open-record queries — load-all-and-filter v1` — arango impl + tests
4. `feat(duckdb): open-record queries raise NotImplementedError (deferred)` — duckdb stubs

Each commit should leave the test suite green.
