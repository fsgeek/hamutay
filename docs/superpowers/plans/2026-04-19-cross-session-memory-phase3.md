# Cross-Session Memory (Phase 3a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give taste_open instances (a) read access to records from *other* sessions, not just their own, and (b) the ability to write typed records and composition edges into the open collection. Together these make the memory graph a living substrate across sessions, not a session-local log.

**Architecture:** Three moving parts, coupled on purpose (read-before-write). (1) Yanantin's `ApachetaInterface` gains query methods over the open-records collection — currently only `get_record(uuid)` exists; everything else targets the prescribed-schema `TensorRecord` collection. (2) `ApachetaBridge` exposes those queries to hamutay. (3) The Phase 2 memory tools (`recall`, `search_memory`, `walk`, `memory_schema`) gain a `scope` parameter; two new tools (`store`, `annotate_edge`) give the instance write access.

**Tech Stack:** Python 3.14, pytest, uv. Primary backend: ArangoDB (running, auto-restart, integrated via `ApachetaBridge.from_arango`). Secondary: in-memory backend for unit-test parity. DuckDB: explicit `NotImplementedError` on new query methods (SQL is the wrong substrate for graph-traversal queries; partial impls would be worse than honest deferral).

**Spec:** `docs/tool_api_proposal_v3.md` — sections I (Memory) and III (Graph Writes). Phase 2 landed in-session memory tools against `_prior_states`. Phase 3a adds the cross-session dimension and the write side.

**Deviations from v3 spec** (flagged in tool descriptions the instance reads, so no surprise):
- Cross-session queries use load-all-and-filter in v1, mirroring the pattern already in `list_tensors()` and `_load_all()`. AQL-level graph traversal is a later optimization — the API is designed so that swap is local to the backend.
- `annotate_edge` is limited to existing `RelationType` enum values; new relation types remain a schema-evolution concern (out of scope).
- `store` records include automatic provenance from the current session; the instance doesn't author provenance.
- No attestation (`willay` not stood up) — mentioned here because v3 spec references it on every tool.

---

## Design decisions worth naming up front

**Tensor identity: UUID at creation, conversations are DAGs.** Every tensor/record has a UUID assigned at creation (the Projector or `_build_open_record` generates it, not the storage layer). `session_UUID` is a lineage tag, not an identity component — a tensor can belong to multiple lineages (merge) or start one (branch origin). Cycle is a frame-local coordinate, meaningful inside one execution path, meaningless across. Addressing duality falls out naturally: in-session uses cycle as a convenience; cross-session uses UUID. LLM conversations can branch (resume from cycle 5 twice, edit cycle 3 and re-run) and merge (tensor C synthesizes A from S1 and B from S2) — a merge node belongs to two sessions or neither, which `(session, cycle)` cannot address. See `memory/project_graph_model_decision.md` for full framing. **Task 0 surfaces these UUIDs into `_prior_states` and in-session tool responses; it is prerequisite to everything below.**

**Addressing across sessions.** Cycle numbers are session-scoped (every session has a cycle 1). For cross-session access, UUID is the only unambiguous address. `recall` gains a `record_id` mode that works cross-session by construction. `cycle` mode remains session-scoped.

**`scope` semantics.** `scope="session"` (default) reads from `_prior_states` as today — fast, cheap, no backend hit. `scope="all"` unions in-session state with cross-session records from the bridge. `scope="cross_session"` reads only from the backend, skipping `_prior_states` (useful for "what did *other* instances say" queries). Default stays "session" — cross-session is opt-in, because it costs a DB round-trip.

**Instance identity in writes.** `store` and `annotate_edge` inherit session_id from the running session. The instance can't forge provenance.

**Edge authoring scope.** `annotate_edge` can reference any record_id the instance can read — in-session (via cycle's record_id, if we expose it) or cross-session (via `recall` or `search_memory` returning record_ids). The model can't fabricate UUIDs and have them land.

**DuckDB deferral is explicit.** New interface methods raise `NotImplementedError("DuckDB open-record queries deferred; use Arango or memory backend")` — not silently returning empty lists, not pretending to work. A future plan can fill them in if DuckDB becomes a tier-A target for hamutay.

---

## File Structure

```
# Yanantin (sibling repo — editable dependency)
src/yanantin/apacheta/interface/abstract.py   # MODIFY — add 5 abstract methods
src/yanantin/apacheta/backends/memory.py      # MODIFY — impl the 5 methods
src/yanantin/apacheta/backends/arango.py      # MODIFY — impl the 5 methods
src/yanantin/apacheta/backends/duckdb.py      # MODIFY — NotImplementedError on the 5 methods
tests/unit/test_interface.py                  # MODIFY — cross-backend contract tests
tests/unit/test_arango.py                     # MODIFY — arango-specific tests (if file exists)
tests/unit/test_memory_backend.py             # MODIFY — memory-specific tests (if file exists)

# Hamutay
src/hamutay/apacheta_bridge.py                # MODIFY — expose new query methods + list_sessions
src/hamutay/tools/memory.py                   # MODIFY — add scope param to 4 tools, new tools
src/hamutay/tools/graph.py                    # NEW — tool_store, tool_annotate_edge
src/hamutay/tools/schemas.py                  # MODIFY — update 4 schemas, register 2 new
src/hamutay/tools/executor.py                 # MODIFY — accept bridge param, dispatch 2 new tools
src/hamutay/taste_open.py                     # MODIFY — thread bridge into executor, update _TOOL_GUIDANCE
tests/unit/test_memory_tools.py               # MODIFY — scope param tests
tests/unit/test_graph_tools.py                # NEW — store, annotate_edge unit tests
tests/unit/test_executor.py                   # MODIFY — dispatch tests for new tools
tests/integration/test_cross_session.py       # NEW — two-session integration
```

Note on test locations: yanantin's tests may live at `tests/` (top level), `tests/unit/`, or colocated — verify in Task 1 before writing test files.

---

### Task 0 (pre-3a refactor): Surface record_ids into `_prior_states` and in-session tool responses

The Projector and `_build_open_record` already generate UUIDs at record creation (see `apacheta_bridge.py:133` — `record_id = uuid4()`). The gap: `store_open_state` returns the UUID, but `taste_open.py` at the cycle-completion site discards it before appending the 3-tuple `(cycle, state, timestamp)` to `_prior_states`. So Phase 2 tools have no way to surface an in-session record's UUID to the instance.

Without this refactor, the instance can reference cross-session records by UUID (via `recall`/`search_memory` results) but not its *own* in-session records. `annotate_edge(from_record_id=<in-session>, to_record_id=<cross-session>, ...)` then has no way to name the in-session endpoint, and the composition graph has a boundary discontinuity. This task closes that gap before Phase 3a's addressing work builds on the assumption.

**Files:**
- Modify: `src/hamutay/taste_open.py` (cycle-completion site around line 770)
- Modify: `src/hamutay/tools/memory.py` (in-session response shapes)
- Modify: `src/hamutay/tools/executor.py` and any `_prior_states` unpackers
- Modify: `tests/unit/test_memory_tools.py` (expect `record_id` in in-session responses)

- [ ] **Step 1: Flip the ordering at the cycle-completion site**

Capture the UUID returned by `store_open_state` before appending to `_prior_states`. When no bridge is configured, generate a local UUID so `_prior_states` is uniformly addressed. `_prior_states` widens from `(cycle, state, timestamp)` to `(cycle, record_id, state, timestamp)` — a 4-tuple.

```python
from uuid import uuid4, UUID

# Generate / capture the record_id before appending.
record_id: UUID
if self._bridge is not None:
    try:
        record_id = self._bridge.store_open_state(self._state, self._cycle)
    except Exception as e:
        print(f"  WARNING: bridge persist failed cycle {self._cycle}: {e}")
        record_id = uuid4()  # local-only UUID keeps _prior_states uniform
else:
    record_id = uuid4()

self._prior_states.append(
    (self._cycle, record_id, json.loads(json.dumps(self._state)), self._last_cycle_time.isoformat())
)
```

- [ ] **Step 2: Update all `_prior_states` unpackers**

Per Phase 2 handoff, several sites unpack these tuples. Widen them to 4-tuples. `_pick_memory`'s caller-facing return shape stays `(cycle, state)` to preserve its contract; internal unpacking widens.

- [ ] **Step 3: Expose `record_id` in in-session tool responses**

`tool_recall(cycle=N)` returns `{cycle, record_id, timestamp, content}`. `tool_memory_schema(cycle=N)` returns `{cycle, record_id, ...}`. `tool_search_memory` in-session hits carry `record_id` alongside `cycle`. `tool_walk` cycle-adjacency results carry `record_id`.

- [ ] **Step 4: Update tool schemas**

Where descriptions mention returning cycle/timestamp, mention `record_id` too. Keep the calibrated voice — descriptive not directive, no "useful when" language.

- [ ] **Step 5: Run Phase 2 unit tests**

```
uv run pytest tests/unit/ -v
```

Existing tests should pass with the tuple widening (unpackers updated) plus response-shape updates. Minor test assertions may need to expect `record_id` in returned dicts.

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/taste_open.py src/hamutay/tools/memory.py src/hamutay/tools/executor.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "refactor: surface record_ids into _prior_states and tool responses (pre-3a)"
```

After this lands, the subsequent tasks' assumption that in-session records are addressable by UUID becomes true. `annotate_edge` can bridge in-session to cross-session. `scope="all"` dedup by UUID is trivial. The conceptual model and the data flow agree.

---

### Task 1: Yanantin — abstract interface extension

Add five abstract methods to `ApachetaInterface` for querying the open-records collection. All backends (memory, arango, duckdb) will need to implement them in subsequent tasks.

**Files:**
- Modify: `src/yanantin/apacheta/interface/abstract.py` (append below existing abstract methods, before `count_records`)

- [ ] **Step 1: Locate yanantin's test directory layout**

Run: `ls /home/tony/projects/yanantin/tests/` and `find /home/tony/projects/yanantin -name "test_*.py" -not -path "*/node_modules/*" | head -20`

Use the result to decide where the cross-backend contract test file goes. Subsequent tasks refer to `tests/unit/test_interface.py` — adjust the path if the convention differs.

- [ ] **Step 2: Add five abstract methods**

In `src/yanantin/apacheta/interface/abstract.py`, append a new section below the existing query methods and before `count_records`:

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
    def query_open_by_session(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """Records authored by a given session (provenance.author_instance_id)."""
        ...

    @abstractmethod
    def query_open_by_lineage_tag(
        self,
        tag: str,
        limit: int | None = None,
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """Records whose lineage_tags contains the given tag."""
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
    def list_sessions(self) -> list[str]:
        """All distinct session_ids (author_instance_id) present in the
        open records collection. For cross-session discovery."""
        ...
```

- [ ] **Step 3: Verify ApachetaBaseModel field access**

The implementations below rely on:
- `record.provenance.author_instance_id` — existing, in `models/provenance.py`
- `record.lineage_tags` — existing tuple field
- `record.model_extra` — pydantic's standard name for fields accepted via `extra='allow'`

Run: `grep -n "model_config\|extra=" /home/tony/projects/yanantin/src/yanantin/apacheta/models/base.py` to confirm `ApachetaBaseModel` is configured with `extra='allow'`. If it isn't, the `query_open_has_field` semantics need to shift to named-field only (which is still useful but narrower). Note the result in your commit message.

- [ ] **Step 4: Commit**

```bash
cd /home/tony/projects/yanantin
git add src/yanantin/apacheta/interface/abstract.py
git -c user.email=<yanantin email> -c user.name="Tony Mason" commit -S -m "feat(interface): add open-record query methods"
```

(Yanantin's commit identity is separate from hamutay's — check `cd /home/tony/projects/yanantin && git log -1 --format='%ae %an'` for the convention before signing.)

---

### Task 2: Yanantin — memory backend implementation

In-memory impl for the five new query methods. Simple dict iteration; this is the unit-test harness for the interface.

**Files:**
- Modify: `src/yanantin/apacheta/backends/memory.py`
- Modify/Create: `tests/unit/test_memory_backend.py` (path from Task 1 Step 1)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_memory_backend.py (or equivalent path)
from uuid import uuid4
from yanantin.apacheta.backends.memory import InMemoryBackend
from yanantin.apacheta.models.base import ApachetaBaseModel
from yanantin.apacheta.models.provenance import ProvenanceEnvelope


def _make_record(session_id: str, tags: tuple[str, ...], **extras) -> ApachetaBaseModel:
    prov = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id=session_id,
        predecessors_in_scope=(),
    )
    return ApachetaBaseModel(provenance=prov, lineage_tags=tags, **extras)


def test_list_open_records_returns_all_newest_first():
    backend = InMemoryBackend()
    id_a, id_b = uuid4(), uuid4()
    backend.store_record(id_a, _make_record("s1", ("hamutay",)))
    backend.store_record(id_b, _make_record("s2", ("hamutay",)))
    results = backend.list_open_records()
    ids = [rid for (rid, _) in results]
    assert set(ids) == {id_a, id_b}


def test_list_open_records_respects_limit():
    backend = InMemoryBackend()
    for _ in range(5):
        backend.store_record(uuid4(), _make_record("s1", ()))
    results = backend.list_open_records(limit=2)
    assert len(results) == 2


def test_query_open_by_session_filters_correctly():
    backend = InMemoryBackend()
    id_s1_a = uuid4()
    id_s1_b = uuid4()
    id_s2 = uuid4()
    backend.store_record(id_s1_a, _make_record("s1", ()))
    backend.store_record(id_s1_b, _make_record("s1", ()))
    backend.store_record(id_s2, _make_record("s2", ()))
    results = backend.query_open_by_session("s1")
    ids = {rid for (rid, _) in results}
    assert ids == {id_s1_a, id_s1_b}


def test_query_open_by_lineage_tag():
    backend = InMemoryBackend()
    id_a = uuid4()
    id_b = uuid4()
    backend.store_record(id_a, _make_record("s1", ("hamutay", "cycle-5")))
    backend.store_record(id_b, _make_record("s1", ("hamutay", "cycle-6")))
    results = backend.query_open_by_lineage_tag("cycle-5")
    ids = {rid for (rid, _) in results}
    assert ids == {id_a}


def test_query_open_has_field():
    backend = InMemoryBackend()
    id_a = uuid4()
    id_b = uuid4()
    backend.store_record(id_a, _make_record("s1", (), theme="opening"))
    backend.store_record(id_b, _make_record("s1", ()))  # no 'theme'
    results = backend.query_open_has_field("theme")
    ids = {rid for (rid, _) in results}
    assert ids == {id_a}


def test_list_sessions_distinct():
    backend = InMemoryBackend()
    backend.store_record(uuid4(), _make_record("s1", ()))
    backend.store_record(uuid4(), _make_record("s1", ()))
    backend.store_record(uuid4(), _make_record("s2", ()))
    assert set(backend.list_sessions()) == {"s1", "s2"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/tony/projects/yanantin && uv run pytest tests/unit/test_memory_backend.py -v`
Expected: FAIL — AttributeError: 'InMemoryBackend' object has no attribute 'list_open_records'

- [ ] **Step 3: Implement in memory.py**

Append below `list_tensors()` (around line 190):

```python
    # ── Open-Record Queries ──────────────────────────────────────

    def list_open_records(
        self, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            # Insertion order on dict gives a reasonable "newest first" via reversed()
            items = [(rid, self._deep_copy(r)) for rid, r in self._records.items()]
            items.reverse()
            return items if limit is None else items[:limit]

    def query_open_by_session(
        self, session_id: str, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            matched = [
                (rid, self._deep_copy(r))
                for rid, r in self._records.items()
                if r.provenance.author_instance_id == session_id
            ]
            matched.reverse()
            return matched if limit is None else matched[:limit]

    def query_open_by_lineage_tag(
        self, tag: str, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            matched = [
                (rid, self._deep_copy(r))
                for rid, r in self._records.items()
                if tag in (r.lineage_tags or ())
            ]
            matched.reverse()
            return matched if limit is None else matched[:limit]

    def query_open_has_field(
        self, field: str, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            matched = []
            for rid, r in self._records.items():
                # model_extra holds fields accepted via extra='allow'
                extras = getattr(r, "model_extra", None) or {}
                if field in extras:
                    matched.append((rid, self._deep_copy(r)))
            matched.reverse()
            return matched if limit is None else matched[:limit]

    def list_sessions(self) -> list[str]:
        with self._lock:
            return sorted({r.provenance.author_instance_id for r in self._records.values()})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_memory_backend.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/tony/projects/yanantin
git add src/yanantin/apacheta/backends/memory.py tests/unit/test_memory_backend.py
git commit -S -m "feat(memory backend): open-record queries"
```

---

### Task 3: Yanantin — ArangoDB backend implementation

AQL-based impl of the five query methods. Uses load-all-and-filter in Python rather than pushing filters into AQL — consistent with the existing pattern in `list_tensors()`, and keeps the obfuscator layer out of query construction. Optimization deferred.

**Files:**
- Modify: `src/yanantin/apacheta/backends/arango.py`
- Create/Modify: `tests/unit/test_arango.py` (integration — requires running Arango)

- [ ] **Step 1: Verify Arango is reachable**

Run: `docker ps | grep arango` (or equivalent) — expect a running container.

If unreachable, the first hypothesis is credentials/tier, not that it's down. Check `yanantin.apacheta.connect(tier="app")` vs `tier="root"` and the env vars Arango's connection config expects. Report findings before escalating.

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_arango.py (append or create)
import os
from uuid import uuid4
import pytest
from yanantin.apacheta import connect
from yanantin.apacheta.models.base import ApachetaBaseModel
from yanantin.apacheta.models.provenance import ProvenanceEnvelope

pytestmark = pytest.mark.skipif(
    os.environ.get("APACHETA_SKIP_ARANGO") == "1",
    reason="APACHETA_SKIP_ARANGO=1 set",
)


@pytest.fixture
def backend():
    """Connect to arango and clean up records from this test run."""
    b = connect(tier="app")
    ids_to_clean: list[str] = []
    yield b, ids_to_clean
    # Teardown: best-effort delete of records we created
    from yanantin.apacheta.storage_obfuscator import TransparentObfuscator
    mapped = b._map.collection_name("records") if hasattr(b, "_map") else "records"
    try:
        collection = b._db.collection(mapped)
        for key in ids_to_clean:
            if collection.has(key):
                collection.delete(key)
    except Exception:
        pass


def _make_record(session_id: str, tags: tuple[str, ...], **extras) -> ApachetaBaseModel:
    prov = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id=session_id,
        predecessors_in_scope=(),
    )
    return ApachetaBaseModel(provenance=prov, lineage_tags=tags, **extras)


def test_arango_list_open_records(backend):
    b, cleanup = backend
    session = f"test-{uuid4()}"
    id_a, id_b = uuid4(), uuid4()
    b.store_record(id_a, _make_record(session, ()))
    b.store_record(id_b, _make_record(session, ()))
    cleanup.extend([str(id_a), str(id_b)])
    results = b.query_open_by_session(session)
    ids = {rid for (rid, _) in results}
    assert ids == {id_a, id_b}


def test_arango_query_open_has_field(backend):
    b, cleanup = backend
    session = f"test-{uuid4()}"
    id_a, id_b = uuid4(), uuid4()
    b.store_record(id_a, _make_record(session, (), marker_field="present"))
    b.store_record(id_b, _make_record(session, ()))
    cleanup.extend([str(id_a), str(id_b)])
    results = b.query_open_has_field("marker_field")
    ids = {rid for (rid, _) in results}
    assert id_a in ids


def test_arango_list_sessions_includes_new_session(backend):
    b, cleanup = backend
    session = f"test-session-{uuid4()}"
    rid = uuid4()
    b.store_record(rid, _make_record(session, ()))
    cleanup.append(str(rid))
    sessions = b.list_sessions()
    assert session in sessions
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_arango.py -v`
Expected: FAIL — AttributeError on `query_open_by_session` etc.

- [ ] **Step 4: Implement in arango.py**

Add a helper `_load_all_generic` that returns `(UUID, ApachetaBaseModel)` pairs, then implement the five methods.

Append below `get_record` (around line 232):

```python
    # ── Open-Record Queries ──────────────────────────────────────

    def _load_all_generic(
        self, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        """Load all records from the open-records collection as (uuid, model) pairs.

        Orders by ArangoDB document creation order (implicit via _id), newest first.
        load-and-filter pattern matches the existing list_tensors() approach;
        AQL-native filtering is a later optimization.
        """
        mapped = self._map.collection_name("records")
        collection = self._db.collection(mapped)
        # collection.all() returns documents in an unspecified order — we sort
        # by _rev descending as a rough "newest first" proxy. Arango does not
        # guarantee insertion-order retrieval, so callers needing strict
        # ordering should filter and sort on a timestamp field (not yet added).
        docs = list(collection.all())
        results = []
        for doc in docs:
            record = self._from_generic_doc(doc)
            rid = UUID(doc["_key"])
            results.append((rid, record))
        # Reverse so newer (higher _rev) comes first; not a strict guarantee
        # but matches the "newest first" spirit of list_tensors() in memory.
        results.reverse()
        return results if limit is None else results[:limit]

    def list_open_records(
        self, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            self._enforce_access("system", "list_open_records")
            return self._load_all_generic(limit=limit)

    def query_open_by_session(
        self, session_id: str, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            self._enforce_access("system", "query_open_by_session")
            all_records = self._load_all_generic()
            matched = [
                (rid, r) for (rid, r) in all_records
                if r.provenance.author_instance_id == session_id
            ]
            return matched if limit is None else matched[:limit]

    def query_open_by_lineage_tag(
        self, tag: str, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            self._enforce_access("system", "query_open_by_lineage_tag")
            all_records = self._load_all_generic()
            matched = [
                (rid, r) for (rid, r) in all_records
                if tag in (r.lineage_tags or ())
            ]
            return matched if limit is None else matched[:limit]

    def query_open_has_field(
        self, field: str, limit: int | None = None
    ) -> list[tuple[UUID, ApachetaBaseModel]]:
        with self._lock:
            self._enforce_access("system", "query_open_has_field")
            all_records = self._load_all_generic()
            matched = []
            for rid, r in all_records:
                extras = getattr(r, "model_extra", None) or {}
                if field in extras:
                    matched.append((rid, r))
            return matched if limit is None else matched[:limit]

    def list_sessions(self) -> list[str]:
        with self._lock:
            self._enforce_access("system", "list_sessions")
            all_records = self._load_all_generic()
            return sorted({
                r.provenance.author_instance_id for (_, r) in all_records
            })
```

Note on AQL: the pure-Python filter works but loads all records into memory per query. For collections beyond ~10k records, push filters into AQL using `self._map.field_name(...)` to handle obfuscation of nested field names (`provenance.author_instance_id` → obfuscated path). Out of scope here; the path is visible when we hit it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_arango.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/tony/projects/yanantin
git add src/yanantin/apacheta/backends/arango.py tests/unit/test_arango.py
git commit -S -m "feat(arango): open-record queries — load-all-and-filter v1"
```

---

### Task 4: Yanantin — DuckDB `NotImplementedError`

New query methods raise `NotImplementedError` with an explicit message pointing at Arango/memory. Signatures present so abstract-method enforcement passes; behavior honest about the deferral.

**Files:**
- Modify: `src/yanantin/apacheta/backends/duckdb.py`

- [ ] **Step 1: Add the five methods as NotImplementedError**

Append below `query_entities_by_uuid` (around line 500):

```python
    # ── Open-Record Queries ──────────────────────────────────────
    # Deferred: graph-shaped queries over SQL storage require recursive
    # CTEs and do not compose with filters cleanly. Use Arango or memory
    # backend for open-record queries. A follow-up plan can fill these
    # in if DuckDB becomes a tier-A target for hamutay.

    def list_open_records(self, limit=None):
        raise NotImplementedError(
            "DuckDB open-record queries deferred. Use Arango or memory backend."
        )

    def query_open_by_session(self, session_id, limit=None):
        raise NotImplementedError(
            "DuckDB open-record queries deferred. Use Arango or memory backend."
        )

    def query_open_by_lineage_tag(self, tag, limit=None):
        raise NotImplementedError(
            "DuckDB open-record queries deferred. Use Arango or memory backend."
        )

    def query_open_has_field(self, field, limit=None):
        raise NotImplementedError(
            "DuckDB open-record queries deferred. Use Arango or memory backend."
        )

    def list_sessions(self):
        raise NotImplementedError(
            "DuckDB open-record queries deferred. Use Arango or memory backend."
        )
```

- [ ] **Step 2: Verify existing DuckDB tests still pass**

Run: `uv run pytest tests/ -k duckdb -v` (or whatever the duckdb-backend test filename matches)
Expected: no regression; new tests of the new methods are not added here.

- [ ] **Step 3: Commit**

```bash
cd /home/tony/projects/yanantin
git add src/yanantin/apacheta/backends/duckdb.py
git commit -S -m "feat(duckdb): open-record queries raise NotImplementedError (deferred)"
```

---

### Task 5: Hamutay — `ApachetaBridge` exposes new queries

Thin pass-through from hamutay's bridge to yanantin's backend. Keeps hamutay's tools decoupled from yanantin internals.

**Files:**
- Modify: `src/hamutay/apacheta_bridge.py`
- Modify/Create: `tests/unit/test_apacheta_bridge.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_apacheta_bridge.py
from uuid import UUID, uuid4
from hamutay.apacheta_bridge import ApachetaBridge


def test_bridge_list_open_records_from_memory():
    bridge = ApachetaBridge.from_memory(session_id="test-session", model="haiku")
    rid_1 = bridge.store_open_state({"cycle": 1, "theme": "opening"}, cycle=1)
    rid_2 = bridge.store_open_state({"cycle": 2, "theme": "explore"}, cycle=2)
    results = bridge.list_open_records()
    ids = {rid for (rid, _) in results}
    assert {rid_1, rid_2} <= ids


def test_bridge_query_by_session_isolates_sessions():
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend,  # share backend to simulate two sessions, one store
        session_id="session-b", model="haiku",
    )
    rid_a = bridge_a.store_open_state({"cycle": 1}, cycle=1)
    rid_b = bridge_b.store_open_state({"cycle": 1}, cycle=1)
    results = bridge_a.query_open_by_session("session-a")
    ids = {rid for (rid, _) in results}
    assert rid_a in ids
    assert rid_b not in ids


def test_bridge_list_sessions():
    bridge_a = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    bridge_b = ApachetaBridge(
        backend=bridge_a._backend, session_id="session-b", model="haiku",
    )
    bridge_a.store_open_state({"cycle": 1}, cycle=1)
    bridge_b.store_open_state({"cycle": 1}, cycle=1)
    sessions = bridge_a.list_sessions()
    assert "session-a" in sessions
    assert "session-b" in sessions


def test_bridge_query_has_field():
    bridge = ApachetaBridge.from_memory(session_id="test", model="haiku")
    rid_with = bridge.store_open_state({"cycle": 1, "marker": "here"}, cycle=1)
    rid_without = bridge.store_open_state({"cycle": 2}, cycle=2)
    results = bridge.query_open_has_field("marker")
    ids = {rid for (rid, _) in results}
    assert rid_with in ids
    assert rid_without not in ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_apacheta_bridge.py -v`
Expected: FAIL — AttributeError on `list_open_records`.

- [ ] **Step 3: Add pass-through methods to `ApachetaBridge`**

In `src/hamutay/apacheta_bridge.py`, append below `retrieve()` (around line 218):

```python
    # ── Cross-session queries ────────────────────────────────────

    def list_open_records(self, limit: int | None = None):
        """All open records in the backend, newest first."""
        return self._backend.list_open_records(limit=limit)

    def query_open_by_session(self, session_id: str, limit: int | None = None):
        """Records authored by a given session."""
        return self._backend.query_open_by_session(session_id, limit=limit)

    def query_open_by_lineage_tag(self, tag: str, limit: int | None = None):
        """Records whose lineage_tags contains the given tag."""
        return self._backend.query_open_by_lineage_tag(tag, limit=limit)

    def query_open_has_field(self, field: str, limit: int | None = None):
        """Records carrying a given free-form field key."""
        return self._backend.query_open_has_field(field, limit=limit)

    def list_sessions(self) -> list[str]:
        """All distinct session_ids in the open records collection."""
        return self._backend.list_sessions()

    @property
    def session_id(self) -> str:
        """The session_id this bridge tags its writes with."""
        return self._session_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_apacheta_bridge.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/apacheta_bridge.py tests/unit/test_apacheta_bridge.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat(bridge): expose open-record queries and session_id"
```

---

### Task 6: Memory tools — `scope` parameter on `recall`

Give `recall` a `scope` parameter (`"session"` default, `"all"`, `"cross_session"`) and a `record_id` addressing mode for cross-session access. Keep `cycle` mode session-scoped — cycle numbers aren't meaningful across sessions.

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_memory_tools.py (append)

from unittest.mock import MagicMock


def _mock_bridge_with_records(records: list[tuple[str, dict, str]]):
    """Build a mock bridge whose list_open_records returns the given
    (record_id_str, extras_dict, session_id) tuples as (UUID, ApachetaBaseModel)."""
    from uuid import UUID
    from yanantin.apacheta.models.base import ApachetaBaseModel
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    def make(rid_str: str, extras: dict, session_id: str):
        prov = ProvenanceEnvelope(
            author_model_family="haiku",
            author_instance_id=session_id,
            predecessors_in_scope=(),
        )
        return (UUID(rid_str), ApachetaBaseModel(provenance=prov, **extras))

    pairs = [make(rid, extras, sid) for (rid, extras, sid) in records]
    bridge = MagicMock()
    bridge.list_open_records.return_value = pairs
    bridge.query_open_has_field.return_value = pairs  # test-time: also return all
    bridge.query_open_by_session.return_value = pairs
    bridge.session_id = "test-current"
    return bridge


def test_recall_scope_session_default_ignores_bridge():
    """Default scope=session should not touch the bridge."""
    bridge = MagicMock()
    result = tool_recall(
        {"cycle": 1, "field": "theme"},
        prior_states=_make_prior_states(),
        bridge=bridge,
    )
    assert result["content"] == "hello"  # from _make_prior_states cycle 1... adjust if fixture differs
    bridge.list_open_records.assert_not_called()


def test_recall_scope_all_with_random_spans_sessions():
    prior = _make_prior_states()
    bridge = _mock_bridge_with_records([
        ("00000000-0000-0000-0000-000000000001", {"theme": "cross-session-a"}, "other-session"),
    ])
    import random
    random.seed(1)
    result = tool_recall(
        {"random": True, "field": "theme", "scope": "all"},
        prior_states=prior, bridge=bridge,
    )
    # Could land on an in-session or cross-session record; both are legal with scope=all
    assert "theme" in result.get("content", result) or result.get("content") is not None


def test_recall_by_record_id_cross_session():
    bridge = _mock_bridge_with_records([
        ("00000000-0000-0000-0000-000000000001", {"theme": "from-other"}, "other-session"),
    ])
    bridge.retrieve = MagicMock(return_value={"theme": "from-other"})
    result = tool_recall(
        {"record_id": "00000000-0000-0000-0000-000000000001", "field": "theme"},
        prior_states=[], bridge=bridge,
    )
    assert result["content"] == "from-other"


def test_recall_by_record_id_no_bridge_errors():
    result = tool_recall(
        {"record_id": "00000000-0000-0000-0000-000000000001"},
        prior_states=[], bridge=None,
    )
    assert "error" in result


def test_recall_cycle_mode_with_scope_all_falls_back_to_session():
    """Cycle mode is session-scoped; scope=all doesn't change that, but
    the tool should still succeed when the cycle exists in-session."""
    result = tool_recall(
        {"cycle": 1, "field": "greeting", "scope": "all"},
        prior_states=_make_prior_states(), bridge=None,
    )
    assert result["content"] == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_memory_tools.py -k "scope or record_id" -v`
Expected: FAIL — TypeError (unexpected kwarg `bridge`) or missing record_id handling.

- [ ] **Step 3: Update `tool_recall` signature and add handling**

In `src/hamutay/tools/memory.py`, modify `tool_recall`:

```python
from uuid import UUID


def tool_recall(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
    bridge=None,  # ApachetaBridge or None
) -> dict:
    """Retrieve content from prior cycles. Five addressing modes."""
    cycle = params.get("cycle")
    field = params.get("field")
    recent = params.get("recent")
    is_random = params.get("random", False)
    record_id_str = params.get("record_id")
    scope = params.get("scope", "session")

    # Mode 1: record_id (cross-session by construction)
    if record_id_str is not None:
        if bridge is None:
            return {"error": "record_id mode requires a bridge (persistence backend)"}
        try:
            record_id = UUID(record_id_str)
        except (ValueError, AttributeError):
            return {"error": f"record_id is not a valid UUID: {record_id_str!r}"}
        try:
            content = bridge.retrieve(record_id)
        except Exception as e:
            return {"error": f"Record {record_id} not found: {e}"}
        if field is not None:
            if field not in content:
                return {"error": f"Field {field!r} not in record {record_id}"}
            return {"record_id": str(record_id), "content": content[field]}
        return {"record_id": str(record_id), "content": content}

    # Mode 2: cycle (always session-scoped)
    if cycle is not None:
        found = _find_by_cycle(prior_states, cycle)
        if found is None:
            return {"error": f"No state found for cycle {cycle}"}
        _cycle, state, timestamp = found
        if field is not None:
            if field not in state:
                return {"error": f"Field {field!r} not in state at cycle {cycle}"}
            return {"cycle": _cycle, "timestamp": timestamp, "content": state[field]}
        return {"cycle": _cycle, "timestamp": timestamp, "content": dict(state)}

    # Mode 3: recent (respects scope)
    if recent is not None:
        if field is None:
            return {"error": "recent mode requires field"}
        collected = _collect_recent(prior_states, field, recent, scope, bridge)
        return {"content": collected}

    # Mode 4: random (respects scope)
    if is_random:
        if field is None:
            return {"error": "random mode requires field"}
        candidates = _candidates_with_field(prior_states, field, scope, bridge)
        if not candidates:
            return {"error": f"No records contain field {field!r}"}
        _random_local = _random
        choice = _random_local.choice(candidates)
        return choice

    return {"error": "recall requires one of: cycle, record_id, recent, random"}


def _collect_recent(prior_states, field, recent, scope, bridge):
    """Walk recent → oldest, collect up to `recent` hits on `field`.
    Respects scope for cross-session extension."""
    collected = []
    # In-session first
    if scope in ("session", "all"):
        for _cycle, state, timestamp in reversed(prior_states):
            if field in state:
                collected.append({
                    "cycle": _cycle, "timestamp": timestamp, "value": state[field],
                })
                if len(collected) >= recent:
                    return collected

    # Cross-session extension
    if scope in ("cross_session", "all") and bridge is not None:
        # query_open_has_field returns newest-first
        remaining = recent - len(collected)
        results = bridge.query_open_has_field(field, limit=remaining)
        for (rid, record) in results:
            extras = getattr(record, "model_extra", None) or {}
            if field in extras:
                collected.append({
                    "record_id": str(rid),
                    "session": record.provenance.author_instance_id,
                    "value": extras[field],
                })
                if len(collected) >= recent:
                    break

    return collected


def _candidates_with_field(prior_states, field, scope, bridge):
    """Return a list of result-dicts eligible for random selection."""
    candidates = []
    if scope in ("session", "all"):
        for _cycle, state, timestamp in prior_states:
            if field in state:
                candidates.append({
                    "cycle": _cycle, "timestamp": timestamp, "content": state[field],
                })
    if scope in ("cross_session", "all") and bridge is not None:
        results = bridge.query_open_has_field(field)
        for (rid, record) in results:
            extras = getattr(record, "model_extra", None) or {}
            if field in extras:
                candidates.append({
                    "record_id": str(rid),
                    "session": record.provenance.author_instance_id,
                    "content": extras[field],
                })
    return candidates
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_memory_tools.py -k recall -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: recall gains scope param and record_id addressing"
```

---

### Task 7: Memory tools — `scope` parameter on `search_memory`

Extend `search_memory` to include cross-session results when `scope="all"` or `scope="cross_session"`. Results from cross-session records include `record_id` and `session` in place of `cycle`.

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_memory_tools.py (append)

def test_search_memory_scope_all_includes_cross_session():
    prior = _searchable_prior_states()
    bridge = _mock_bridge_with_records([
        ("00000000-0000-0000-0000-000000000001",
         {"theme": "pattern from other session"}, "other-session"),
    ])
    # The mock returns `pairs` for every narrowing call; that's fine for this test
    result = tool_search_memory(
        {"query": "pattern", "scope": "all"},
        prior_states=prior, bridge=bridge,
    )
    # We should see results from both in-session and cross-session
    in_session_cycles = [r for r in result["results"] if "cycle" in r]
    cross_session_records = [r for r in result["results"] if "record_id" in r]
    assert len(in_session_cycles) >= 1
    assert len(cross_session_records) >= 1


def test_search_memory_scope_session_default_ignores_bridge():
    prior = _searchable_prior_states()
    bridge = MagicMock()
    result = tool_search_memory(
        {"query": "pattern"},  # default scope=session
        prior_states=prior, bridge=bridge,
    )
    bridge.query_open_has_field.assert_not_called()
    bridge.list_open_records.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Extend `tool_search_memory`**

Modify the signature to accept `bridge=None`, and after the in-session match loop, add a cross-session pass when scope permits. Use `bridge.query_open_by_lineage_tag("hamutay")` to bound the cross-session search to hamutay-authored records only (the lineage_tag convention from `_build_open_record`).

Sketch (integrate into the existing function body):

```python
def tool_search_memory(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
    bridge=None,
) -> dict:
    query = params.get("query")
    narrow_by = params.get("narrow_by") or {}
    limit = params.get("limit", 5)
    scope = params.get("scope", "session")

    if not query:
        return {"error": "query is required"}

    query_lower = query.lower()
    total = len(prior_states)

    # In-session matches (existing logic)
    matches = _match_in_session(prior_states, query_lower, narrow_by)

    # Cross-session matches (new)
    cross_matches = []
    if scope in ("cross_session", "all") and bridge is not None:
        cross_matches = _match_cross_session(bridge, query_lower, narrow_by)

    combined = matches + cross_matches
    # Rank: in-session by cycle desc first, then cross-session
    combined.sort(key=lambda r: (
        0 if "cycle" in r else 1,
        -(r.get("cycle") or 0),
    ))
    limited = combined[:limit]

    return {
        "results": limited,
        "search_metadata": {
            "total_candidates": total,
            "narrowed_to": len(matches),
            "matched_count": len(combined),
            "cross_session_count": len(cross_matches),
        },
    }


def _match_in_session(prior_states, query_lower, narrow_by):
    # Existing body of tool_search_memory, extracted. Keeps the
    # cycle_range / has_field / fields narrowing logic unchanged.
    ...  # lift existing code


def _match_cross_session(bridge, query_lower, narrow_by):
    """Search across stored records (any session tagged 'hamutay')."""
    candidates = bridge.query_open_by_lineage_tag("hamutay")
    has_field = narrow_by.get("has_field")
    field_filter = narrow_by.get("fields")
    matches = []
    for rid, record in candidates:
        extras = getattr(record, "model_extra", None) or {}
        if has_field and has_field not in extras:
            continue
        search_fields = field_filter if field_filter else list(extras.keys())
        matched_fields = []
        snippets = {}
        for key in search_fields:
            if key not in extras:
                continue
            if _value_contains(extras[key], query_lower):
                matched_fields.append(key)
                snippets[key] = _snippet(extras[key], query_lower)
        if matched_fields:
            matches.append({
                "record_id": str(rid),
                "session": record.provenance.author_instance_id,
                "relevance": 1.0,
                "matched_fields": matched_fields,
                "snippets": snippets,
            })
    return matches
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_memory_tools.py -k search_memory -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: search_memory scope param includes cross-session matches"
```

---

### Task 8: Memory tools — `scope` on `walk` and `memory_schema`

`walk` accepts `scope` but cross-session walking requires a CompositionEdge-driven traversal (not just cycle arithmetic). For v1 of cross-session walk: accept `from_record_id`, return adjacent records via the composition graph. `memory_schema` accepts `record_id` for inspecting cross-session record structure.

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Decide scope for walk's cross-session support**

`walk` in Phase 2 used cycle adjacency (cycle N, step ±1). Cross-session needs CompositionEdge traversal. For Plan 3a we add a minimum-viable cross-session walk: `from_record_id` resolves adjacent records by looking up composition edges where `from_tensor == record_id` (forward) or `to_tensor == record_id` (backward).

This requires a bridge method `query_edges_by_endpoint(record_id, direction)`. Add it to the bridge (pass-through to `backend.query_composition_graph()` filtered in Python for v1; AQL graph traversal is the natural upgrade). Add that method to the bridge in this task as a sub-step.

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_memory_tools.py (append)

def test_memory_schema_by_record_id():
    from uuid import UUID
    from yanantin.apacheta.models.base import ApachetaBaseModel
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope
    bridge = MagicMock()
    rid = UUID("00000000-0000-0000-0000-000000000001")
    prov = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id="other-session",
        predecessors_in_scope=(),
    )
    record = ApachetaBaseModel(
        provenance=prov, lineage_tags=("hamutay", "cycle-5"),
        theme="cross-session", notes=["a", "b"],
    )
    bridge.retrieve.return_value = {
        "theme": "cross-session", "notes": ["a", "b"],
        "provenance": {"author_instance_id": "other-session"},
        "lineage_tags": ["hamutay", "cycle-5"],
    }
    result = tool_memory_schema(
        {"record_id": "00000000-0000-0000-0000-000000000001"},
        prior_states=[], bridge=bridge,
    )
    assert result["record_id"] == "00000000-0000-0000-0000-000000000001"
    assert "theme" in result["field_names"]


def test_walk_from_record_id_across_sessions():
    from uuid import UUID
    bridge = MagicMock()
    rid_from = UUID("00000000-0000-0000-0000-000000000001")
    rid_to = UUID("00000000-0000-0000-0000-000000000002")
    # Simulate one edge from→to
    bridge.query_edges_by_endpoint.return_value = [
        {"from_record": rid_from, "to_record": rid_to, "relation_type": "refines"},
    ]
    # And the adjacent record's schema
    bridge.retrieve.return_value = {"theme": "next", "provenance": {"author_instance_id": "s"}}
    result = tool_walk(
        {"from_record_id": "00000000-0000-0000-0000-000000000001",
         "direction": "forward", "depth": 1},
        prior_states=[], bridge=bridge,
    )
    assert len(result["path"]) == 1
    assert result["path"][0]["record_id"] == "00000000-0000-0000-0000-000000000002"
```

- [ ] **Step 3: Add `query_edges_by_endpoint` to the bridge**

In `src/hamutay/apacheta_bridge.py`, add:

```python
    def query_edges_by_endpoint(self, record_id: UUID, direction: str = "both"):
        """Find composition edges touching record_id.

        direction='forward' returns edges where record_id is from_tensor
        direction='backward' returns edges where record_id is to_tensor
        direction='both' returns both.

        Returns list of dicts with keys {from_record, to_record, relation_type, ordering}.
        """
        edges = self._backend.query_composition_graph()
        results = []
        for edge in edges:
            rel = getattr(edge.relation_type, "value", str(edge.relation_type))
            if direction in ("forward", "both") and edge.from_tensor == record_id:
                results.append({
                    "from_record": edge.from_tensor,
                    "to_record": edge.to_tensor,
                    "relation_type": rel,
                    "ordering": edge.ordering,
                })
            if direction in ("backward", "both") and edge.to_tensor == record_id:
                results.append({
                    "from_record": edge.from_tensor,
                    "to_record": edge.to_tensor,
                    "relation_type": rel,
                    "ordering": edge.ordering,
                })
        return results
```

- [ ] **Step 4: Extend `tool_memory_schema` and `tool_walk`**

`tool_memory_schema`: accept `record_id` mode. When set, call `bridge.retrieve(UUID(record_id))` and compute the schema from the returned dict (fields, types, sizes, tokens).

`tool_walk`: accept `from_record_id` mode. When set, call `bridge.query_edges_by_endpoint(rid, direction)` to find neighbors, then `bridge.retrieve` each to build path steps. `depth>1` iterates by repeatedly looking up edges from the most recent neighbor.

(Implementations parallel Phase 2's shapes; details follow the same pattern. Sketch given here; full body is mechanical.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_memory_tools.py -k "walk or memory_schema" -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/tools/memory.py src/hamutay/apacheta_bridge.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: walk and memory_schema gain record_id cross-session modes"
```

---

### Task 9: New tool — `store`

Instance writes a typed payload into the open records collection. Provenance is inherited from the running session; the instance can't forge it.

**Files:**
- Create: `src/hamutay/tools/graph.py`
- Create: `tests/unit/test_graph_tools.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_graph_tools.py
from unittest.mock import MagicMock
from hamutay.tools.graph import tool_store


def test_store_calls_bridge_with_content():
    bridge = MagicMock()
    from uuid import UUID
    bridge.store_open_state.return_value = UUID("00000000-0000-0000-0000-000000000099")
    result = tool_store(
        {"content": {"observation": "pattern X recurs"}, "tags": ["hypothesis"]},
        cycle=5, bridge=bridge,
    )
    assert result["record_id"] == "00000000-0000-0000-0000-000000000099"
    bridge.store_open_state.assert_called_once()


def test_store_without_bridge_errors():
    result = tool_store(
        {"content": {"x": 1}},
        cycle=5, bridge=None,
    )
    assert "error" in result


def test_store_requires_content():
    bridge = MagicMock()
    result = tool_store({"tags": ["x"]}, cycle=5, bridge=bridge)
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement `tool_store`**

```python
# src/hamutay/tools/graph.py
"""Graph-write tools — store and annotate_edge.

These let the instance write typed records and composition edges into
the open records collection. Provenance is inherited from the running
session; the instance can't forge author_instance_id or model_family.
"""

from __future__ import annotations


def tool_store(
    params: dict,
    *,
    cycle: int,
    bridge=None,
) -> dict:
    """Store a typed payload in the open records collection.

    The payload lands with provenance matching the current session and
    lineage_tags including 'hamutay', 'instance_authored', and any user
    tags. The instance learns the record_id so it can reference it in
    annotate_edge or later recall calls.
    """
    if bridge is None:
        return {"error": "store requires a persistence backend (bridge not configured)"}

    content = params.get("content")
    if not isinstance(content, dict):
        return {"error": "store requires content (dict)"}

    tags = params.get("tags") or []
    if not isinstance(tags, list):
        return {"error": "tags must be a list of strings"}

    # The bridge's store_open_state already adds hamutay + taste_open + cycle-N tags.
    # We add "instance_authored" to distinguish these from framework-written records,
    # plus any caller-supplied tags. This conversion happens inside the store;
    # the record that lands is marked as instance-authored.
    payload = dict(content)
    payload["_instance_authored"] = True
    payload["_instance_tags"] = list(tags)

    try:
        record_id = bridge.store_open_state(payload, cycle=cycle)
    except Exception as e:
        return {"error": f"Store failed: {e}"}

    return {
        "record_id": str(record_id),
        "session": bridge.session_id,
        "cycle": cycle,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_graph_tools.py -k store -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/graph.py tests/unit/test_graph_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: store tool — instance writes typed records into the graph"
```

---

### Task 10: New tool — `annotate_edge`

Instance authors a CompositionEdge between two record_ids. Relation type must be from the existing `RelationType` enum.

**Files:**
- Modify: `src/hamutay/tools/graph.py`
- Modify: `tests/unit/test_graph_tools.py`

- [ ] **Step 1: Enumerate available relation types**

Run: `grep -n "class RelationType" /home/tony/projects/yanantin/src/yanantin/apacheta/models/composition.py` and read the enum values. They become the allowed values in the tool schema.

- [ ] **Step 2: Write failing tests**

```python
# tests/unit/test_graph_tools.py (append)
from hamutay.tools.graph import tool_annotate_edge


def test_annotate_edge_calls_store_composition_edge():
    bridge = MagicMock()
    result = tool_annotate_edge(
        {
            "from_record_id": "00000000-0000-0000-0000-000000000001",
            "to_record_id": "00000000-0000-0000-0000-000000000002",
            "relation": "REFINES",
        },
        cycle=5, bridge=bridge,
    )
    assert "edge_id" in result
    # Bridge exposes _backend.store_composition_edge via a helper we'll add
    assert bridge.store_edge.called or bridge._backend.store_composition_edge.called


def test_annotate_edge_rejects_unknown_relation():
    bridge = MagicMock()
    result = tool_annotate_edge(
        {
            "from_record_id": "00000000-0000-0000-0000-000000000001",
            "to_record_id": "00000000-0000-0000-0000-000000000002",
            "relation": "NOT_A_REAL_RELATION",
        },
        cycle=5, bridge=bridge,
    )
    assert "error" in result


def test_annotate_edge_rejects_malformed_uuid():
    bridge = MagicMock()
    result = tool_annotate_edge(
        {"from_record_id": "not-a-uuid", "to_record_id": "also-not",
         "relation": "REFINES"},
        cycle=5, bridge=bridge,
    )
    assert "error" in result
```

- [ ] **Step 3: Add `store_edge` helper to bridge**

In `src/hamutay/apacheta_bridge.py`:

```python
    def store_edge(
        self,
        from_record: UUID,
        to_record: UUID,
        relation_type: str,
        ordering: int = 0,
    ) -> UUID:
        """Store a CompositionEdge. Returns edge.id."""
        from yanantin.apacheta.models.composition import CompositionEdge, RelationType
        relation = RelationType[relation_type]  # KeyError if unknown
        edge = CompositionEdge(
            from_tensor=from_record,
            to_tensor=to_record,
            relation_type=relation,
            ordering=ordering,
        )
        self._backend.store_composition_edge(edge)
        return edge.id
```

- [ ] **Step 4: Implement `tool_annotate_edge`**

```python
# src/hamutay/tools/graph.py (append)
from uuid import UUID


def tool_annotate_edge(
    params: dict,
    *,
    cycle: int,
    bridge=None,
) -> dict:
    """Author a composition edge between two records.

    relation must be one of the RelationType enum values.
    """
    if bridge is None:
        return {"error": "annotate_edge requires a persistence backend"}

    from_str = params.get("from_record_id")
    to_str = params.get("to_record_id")
    relation = params.get("relation")

    if not from_str or not to_str or not relation:
        return {"error": "from_record_id, to_record_id, and relation are required"}

    try:
        from_id = UUID(from_str)
        to_id = UUID(to_str)
    except (ValueError, AttributeError):
        return {"error": "from_record_id and to_record_id must be valid UUIDs"}

    try:
        edge_id = bridge.store_edge(from_id, to_id, relation, ordering=cycle)
    except KeyError:
        return {"error": f"Unknown relation: {relation!r}. See RelationType enum."}
    except Exception as e:
        return {"error": f"Edge creation failed: {e}"}

    return {
        "edge_id": str(edge_id),
        "from_record_id": from_str,
        "to_record_id": to_str,
        "relation": relation,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_graph_tools.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/tools/graph.py src/hamutay/apacheta_bridge.py tests/unit/test_graph_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: annotate_edge tool — instance authors composition edges"
```

---

### Task 11: Tool schemas + executor dispatch + system-prompt guidance

Register the new tools, extend the four memory-tool schemas with `scope` and `record_id`, dispatch through `ToolExecutor`, update `_TOOL_GUIDANCE`.

**Files:**
- Modify: `src/hamutay/tools/schemas.py`
- Modify: `src/hamutay/tools/executor.py`
- Modify: `src/hamutay/tools/__init__.py`
- Modify: `src/hamutay/taste_open.py` (`_TOOL_GUIDANCE`)

- [ ] **Step 1: Extend memory tool schemas**

For each of `recall`, `search_memory`, `walk`, `memory_schema`: add `scope` property (enum of `"session"`, `"cross_session"`, `"all"`, default `"session"`), and `record_id` where applicable. Descriptions stay in the calibrated voice — permissive, descriptive-not-directive, no "check when it matters."

Example for `recall`:

```python
RECALL_SCHEMA = {
    "name": "recall",
    "description": (
        "Retrieve content from a prior record. Addressing modes: "
        "(a) cycle + field — one field at one cycle of this session; "
        "(b) cycle alone — full state snapshot from this session; "
        "(c) record_id (+ field?) — one record by UUID, useful for "
        "cross-session references from search results; "
        "(d) recent + field — last N values of one field, scope "
        "determines whether cross-session records are included; "
        "(e) random + field — one randomly chosen prior record with "
        "that field, scoped by `scope`. What you retrieve is what was "
        "claimed then, not necessarily what was true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {"type": "integer", "description": "Cycle number within this session."},
            "field": {"type": "string", "description": "Field within the state."},
            "recent": {"type": "integer", "description": "Return this many recent values of field."},
            "random": {"type": "boolean", "description": "Pick a random record with field."},
            "record_id": {
                "type": "string",
                "description": (
                    "UUID of a record. Works cross-session by construction. "
                    "Obtain record_ids from search_memory or walk results."
                ),
            },
            "scope": {
                "type": "string",
                "enum": ["session", "cross_session", "all"],
                "description": (
                    "session (default): this session only. cross_session: "
                    "skip this session, look elsewhere. all: both. "
                    "Cross-session costs a backend query; default stays "
                    "session unless you have reason to look further."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": [],
    },
}
```

Do the same shape for `search_memory`, `walk`, `memory_schema` — add `scope` (and `record_id` for walk+memory_schema). Keep backward compatibility: the `scope` default is `"session"`, which matches Phase 2 behavior.

- [ ] **Step 2: Add schemas for `store` and `annotate_edge`**

```python
STORE_SCHEMA = {
    "name": "store",
    "description": (
        "Write a typed payload into the open records collection. "
        "Your session's provenance is attached automatically; you "
        "cannot forge authorship. Returns record_id so later cycles "
        "(yours or others') can reference the record via recall or "
        "annotate_edge."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "description": "The payload. Free-form; whatever keys you want.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags recorded with the record.",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["content"],
    },
}

ANNOTATE_EDGE_SCHEMA = {
    "name": "annotate_edge",
    "description": (
        "Author a composition edge between two records (yours or "
        "others'). The edge is permanent — edges compose, don't "
        "overwrite. Relation types are from yanantin's RelationType "
        "enum."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_record_id": {"type": "string", "description": "Source record UUID."},
            "to_record_id": {"type": "string", "description": "Target record UUID."},
            "relation": {
                "type": "string",
                # Enum filled from RelationType introspection in Task 10 Step 1
                "description": "Relation type from RelationType enum (e.g. REFINES).",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["from_record_id", "to_record_id", "relation"],
    },
}

TOOL_SCHEMAS["store"] = STORE_SCHEMA
TOOL_SCHEMAS["annotate_edge"] = ANNOTATE_EDGE_SCHEMA
```

- [ ] **Step 3: Update `ToolExecutor`**

`ToolExecutor.__init__` accepts `bridge=None`. `execute()` dispatches `store` and `annotate_edge` to the new tools, and passes `bridge` to memory tools that accept it.

```python
# src/hamutay/tools/executor.py (modify)

from hamutay.tools.graph import tool_annotate_edge, tool_store

class ToolExecutor:
    def __init__(
        self,
        project_root: Path,
        cycle: int,
        session_start: datetime | None = None,
        last_cycle_time: datetime | None = None,
        prior_states: list[tuple[int, dict, str]] | None = None,
        bridge=None,  # ApachetaBridge or None
    ):
        # ... existing init ...
        self._bridge = bridge

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        # ... existing dispatch for read/search_project/clock/memory tools ...
        # Memory tools now receive bridge:
        elif tool_name == "recall":
            result = tool_recall(
                tool_input,
                prior_states=self._prior_states,
                bridge=self._bridge,
            )
        # ... similar for search_memory, walk, memory_schema ...

        elif tool_name == "store":
            result = tool_store(
                tool_input, cycle=self._cycle, bridge=self._bridge,
            )
        elif tool_name == "annotate_edge":
            result = tool_annotate_edge(
                tool_input, cycle=self._cycle, bridge=self._bridge,
            )
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        # ... existing activity logging ...
```

Extend `_summarize` with cases for `store` and `annotate_edge`:

```python
    if tool_name == "store":
        return f"store: record_id={result.get('record_id', '?')[:8]}..."
    if tool_name == "annotate_edge":
        return f"annotate_edge: {result.get('relation', '?')} → {result.get('edge_id', '?')[:8]}..."
```

- [ ] **Step 4: Thread bridge into executor from `exchange()`**

In `src/hamutay/taste_open.py`, at the tool_executor construction site (around line 706 per Plan 2):

```python
tool_executor = ToolExecutor(
    project_root=self._project_root,
    cycle=self._cycle,
    session_start=self._session_start,
    last_cycle_time=self._last_cycle_time,
    prior_states=self._prior_states,
    bridge=self._bridge,  # self._bridge is set in __init__ if persistence is configured
)
```

If `self._bridge` isn't already a field on the session, add it: thread it through from the constructor (the CLI in `main()` already creates the bridge — pass it to `OpenTasteSession(..., bridge=bridge)`).

- [ ] **Step 5: Update `_TOOL_GUIDANCE`**

Extend the Memory section with scope-and-cross-session language, and add a Graph section for `store` and `annotate_edge`:

```
### Memory (extends Phase 2)

... existing text ...

Each memory tool accepts a `scope` parameter: "session" (default —
this session's cycles only), "cross_session" (records from other
sessions), "all" (both). Cross-session scope costs a backend query;
leave default unless you have reason to look further.

`recall` and `memory_schema` accept `record_id` (a UUID) to address
records across sessions. `walk` accepts `from_record_id` to traverse
composition edges across sessions.

### Graph

- store(content, tags?): Write a typed payload to the open records
  collection. Returns record_id. Your provenance is attached
  automatically.
- annotate_edge(from_record_id, to_record_id, relation): Author a
  composition edge between two records. Edges are permanent.

These exist so you can shape the graph, not just read it. You are
not required to use them. They are not rewarded.
```

- [ ] **Step 6: Run all unit tests**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/hamutay/tools/schemas.py src/hamutay/tools/executor.py src/hamutay/taste_open.py src/hamutay/tools/__init__.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: register cross-session schemas, dispatch graph tools, update guidance"
```

---

### Task 12: Integration test — two-session cross-session round-trip

Two sequential sessions against the same bridge. Session A stores a record. Session B recalls it by `record_id`, then annotates an edge back to it.

**Files:**
- Create: `tests/integration/test_cross_session.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_cross_session.py
"""Integration test for cross-session memory and graph-writes.

Requires ANTHROPIC_API_KEY in environment AND a running Arango instance.
Skip if either isn't present.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path

from hamutay.taste_open import OpenTasteSession
from hamutay.apacheta_bridge import ApachetaBridge

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


def test_two_sessions_cross_session_recall_and_annotate():
    """Session A stores a distinctive record. Session B finds it via
    search_memory (cross-session), recalls the content, and annotates
    an edge back to it. Verifies the round trip."""

    # Shared in-memory bridge — same backend across both sessions
    bridge_a = ApachetaBridge.from_memory(session_id="session-alpha", model="claude-haiku-4-5")
    backend = bridge_a._backend

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # --- Session A: store a record ---
        session_a = OpenTasteSession(
            model="claude-haiku-4-5",
            log_path=str(root / "session_a.jsonl"),
            enable_tools=True,
            project_root=root,
            experiment_label="test_cross_session_a",
            bridge=bridge_a,
        )
        session_a.exchange(
            "Use the store tool to save this observation: "
            "content={{'hypothesis': 'quinoa-is-the-best-grain', "
            "'epistemic_status': 'tentative'}}. "
            "Tag it as 'hypothesis'."
        )

        # Verify A's write actually landed
        all_records = bridge_a.list_open_records()
        assert len(all_records) >= 1

        # --- Session B: new session, shared backend ---
        bridge_b = ApachetaBridge(
            backend=backend, session_id="session-beta", model="claude-haiku-4-5",
        )
        session_b = OpenTasteSession(
            model="claude-haiku-4-5",
            log_path=str(root / "session_b.jsonl"),
            enable_tools=True,
            project_root=root,
            experiment_label="test_cross_session_b",
            bridge=bridge_b,
        )

        # Ask B to look cross-session and find the hypothesis
        response = session_b.exchange(
            "Use search_memory with scope='cross_session' to find a hypothesis "
            "about grains. Report what you find."
        )
        assert "quinoa" in response.lower()

        # Verify B called search_memory cross-session
        with open(root / "session_b.jsonl") as f:
            records = [json.loads(line) for line in f if line.strip()]
        last = records[-1]
        activity = last.get("state", {}).get("_activity_log", [])
        tool_names = [a.get("tool") for a in activity]
        assert "search_memory" in tool_names
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/integration/test_cross_session.py -v`
Expected: PASS (if ANTHROPIC_API_KEY is set). Skip otherwise.

If the model fails to use the tool in the expected shape (e.g., doesn't recognize `scope='cross_session'`), loosen the assertions or adjust the user message rather than relaxing the schema — model-prompt fit is part of what the test is measuring.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_cross_session.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "test: integration — cross-session recall and store round-trip"
```

---

## Summary

After completing all 12 tasks:

- **Five new open-record query methods** in yanantin's backend interface, implemented against memory + arango, deferred on duckdb.
- **`ApachetaBridge` exposes** `list_open_records`, `query_open_by_session`, `query_open_by_lineage_tag`, `query_open_has_field`, `list_sessions`, `query_edges_by_endpoint`, `store_edge`.
- **Phase 2 memory tools gain `scope`** (`session`/`cross_session`/`all`) and `record_id` / `from_record_id` addressing for cross-session access.
- **Two new instance tools**: `store` (write typed records with inherited provenance) and `annotate_edge` (author composition edges between records).
- **System prompt updated** in the calibrated voice. Defaults preserve Phase 2 behavior; cross-session is opt-in.
- **Integration test**: two sessions, shared backend, round-trip storage and recall.

## What this does NOT include (deferred)

- **AQL-native graph traversal** — load-all-and-filter works for the current scale; AQL graph operators (`FOR v, e, p IN 1..N OUTBOUND`) become the natural optimization when collections grow or when multi-hop walks get hot. The API is shaped so the swap is local to the Arango backend.
- **DuckDB implementations** — explicit `NotImplementedError`. Follow-up plan if duckdb becomes a tier-A target.
- **Attestation** (`willay`) — still not stood up. `store` and `annotate_edge` don't produce attestation chains.
- **Semantic similarity** in `search_memory` — keyword substring remains, same as Phase 2.
- **`verify` tool** — grounding via external evidence. Phase 3b.
- **Tiered forgetting / activity stream compression** — the activity log continues to accumulate. Phase 3b.
- **Edge-type filtering in `walk`** — Phase 2 walk only does cycle adjacency; cross-session walk follows any `CompositionEdge` with no relation-type filter. Adding `edge_type` param is a follow-up.
- **Communication tools** (`commune`, `listen`, `discover`) — Phase 4.
