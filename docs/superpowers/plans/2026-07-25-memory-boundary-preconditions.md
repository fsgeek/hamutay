# Memory Boundary Preconditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Hamut'ay capable of representing honest unverified authorship and mechanically reject the three forbidden receipt shapes before any cross-project retrieval proof is connected.

**Architecture:** Upgrade Hamut'ay to the released Yanantin/Tiksi provenance model, then keep graph-write policy and receipt-shape policy in two small Hamut'ay modules. `ApachetaBridge` remains the graph sink but supplies explicit unverified provenance and validates endpoints; a new immutable receipt model defines the later `MemoryPort` payload without yet integrating qhaway or llm-memory. A dedicated GitHub Actions job runs the boundary guards remotely and must become a required check before the proof is implemented.

**Tech Stack:** Python 3.14, Pydantic 2, Yanantin 0.1.2+, Tiksi 0.1.1+, pytest, uv, GitHub Actions

## Global Constraints

- Authorship is self-asserted in the present substrate; every new edge and receipt sets `authorship_verified` to `false`.
- Episode bodies, search snippets, raw prompt context, credentials, and private diagnostic payloads never enter a retrieval receipt. `purpose` and `query` are allowed bounded inputs, but their producers must not use them to copy any of that forbidden content.
- An llm-memory `episode://` reference remains an opaque string and is never coerced into a graph UUID. Validate its exact scheme, nonempty authority/corpus, exactly two nonempty path segments, and absence of whitespace, userinfo, port, query, or fragment without decoding it.
- A receipt with outcome `used` requires an authoritative open with standing `available`.
- Receipt integers are strict: bool, float, and string coercions are rejected, including during replacement copies. Retrieval timestamps are timezone-aware.
- Zero-result and pre-selection failure receipts carry no episode reference or selected rank. Those fields occur together only after selection; exact totals are at least the returned count, returned count does not exceed the limit, and every indexed or selected corpus is requested.
- Repeated non-self annotations are distinct append-only assertions and remain permitted; self-loop annotations are rejected.
- Endpoint existence is checked before a composition edge is stored.
- Instance edge endpoints are generic/open records addressed through backend `get_record`; they are not required to be prescribed `TensorRecord` entries.
- Tests exercise in-memory storage only; this precondition package performs no live ArangoDB writes.
- Use `uv run`; do not invoke a system Python.
- Every commit uses the exact Hamut'ay signed identity command shown in its task.

## File map

- Modify `pyproject.toml` and `uv.lock`: require the released provenance model that contains `authorship_verified`.
- Modify `src/hamutay/apacheta_bridge.py`: add honest provenance to instance-authored edges and validate their endpoints.
- Modify `tests/unit/test_apacheta_bridge.py`: lock dependency and bridge-level provenance behavior.
- Modify `tests/unit/test_graph_tools.py`: lock tool-visible missing-endpoint and self-loop behavior.
- Create `src/hamutay/memory/receipts.py`: immutable, strict receipt value objects only; no service or storage code.
- Create `tests/unit/test_memory_boundary_invariants.py`: executable guards for non-duplication, native identities, authoritative open, and explicit cardinality standing.
- Create `.github/workflows/memory-boundary-invariants.yml`: remote, database-free invariant gate.

---

### Task 1: Align Hamut'ay with honest provenance

**Files:**
- Modify: `pyproject.toml:16-34`
- Modify: `uv.lock`
- Modify: `tests/unit/test_apacheta_bridge.py`

**Interfaces:**
- Consumes: PyPI `yanantin>=0.1.2`, whose dependency resolves Tiksi `>=0.1.1`.
- Produces: `ProvenanceEnvelope.authorship_verified: bool`, immutable and defaulting to `False`, for Tasks 2 and 3.

- [ ] **Step 1: Add the failing runtime compatibility test**

Append to `tests/unit/test_apacheta_bridge.py`:

```python
def test_runtime_provenance_exposes_honest_authorship_status():
    from pydantic import ValidationError
    from yanantin.apacheta.models.provenance import ProvenanceEnvelope

    assert "authorship_verified" in ProvenanceEnvelope.model_fields
    provenance = ProvenanceEnvelope(
        author_model_family="haiku",
        author_instance_id="asserted-session",
    )
    assert provenance.authorship_verified is False
    with pytest.raises(ValidationError):
        provenance.authorship_verified = True
```

Add `import pytest` with the existing imports in that file.

- [ ] **Step 2: Demonstrate that Hamut'ay's locked environment is stale**

Run:

```bash
uv run pytest tests/unit/test_apacheta_bridge.py::test_runtime_provenance_exposes_honest_authorship_status -v
```

Expected: FAIL because the locked Yanantin 0.1.0 provenance model has no `authorship_verified` field.

- [ ] **Step 3: Raise the dependency floor and update only the lock resolution**

Change the dependency entry in `pyproject.toml`:

```toml
    "yanantin>=0.1.2",
```

Then run:

```bash
uv lock --upgrade-package yanantin --upgrade-package tiksi
```

Inspect the resolved packages:

```bash
uv run python - <<'PY'
from importlib.metadata import version
from yanantin.apacheta.models.provenance import ProvenanceEnvelope

print("yanantin", version("yanantin"))
print("tiksi", version("tiksi"))
print("authorship_verified", ProvenanceEnvelope().authorship_verified)
PY
```

Expected: Yanantin is at least 0.1.2, Tiksi is at least 0.1.1, and `authorship_verified False` is printed.

- [ ] **Step 4: Run the focused and bridge suites**

Run:

```bash
uv run pytest tests/unit/test_apacheta_bridge.py -v
```

Expected: PASS, including the new compatibility guard.

- [ ] **Step 5: Commit the dependency contract**

```bash
git add pyproject.toml uv.lock tests/unit/test_apacheta_bridge.py
git -c user.email=hamutay@wamason.com \
    -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "Require honest authorship provenance"
```

Expected: the post-commit hook creates a separate signed OTS stamp commit.

---

### Task 2: Make instance-authored edges honest and structurally valid

**Files:**
- Modify: `src/hamutay/apacheta_bridge.py:286-309`
- Modify: `tests/unit/test_apacheta_bridge.py`
- Modify: `tests/unit/test_graph_tools.py`

**Interfaces:**
- Consumes: `ProvenanceEnvelope(..., authorship_verified=False)` from Task 1; backend `get_record(UUID)` and `store_composition_edge(CompositionEdge)`.
- Produces: `ApachetaBridge.store_edge(from_record: UUID, to_record: UUID, relation_type: str, ordering: int = 0) -> UUID`, with `authored_mapping="hamutay.instance_tool.v1"` and asserted session/model provenance.

- [ ] **Step 1: Add failing bridge tests for provenance and endpoint policy**

Append to `tests/unit/test_apacheta_bridge.py`:

```python
def test_instance_edge_carries_asserted_unverified_provenance():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    left = uuid4()
    right = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, left, _now())
    bridge._prior_id = None
    bridge.store_open_state({"cycle": 1}, 1, right, _now())

    edge_id = bridge.store_edge(left, right, "CONFIRMS", ordering=2)
    edge = next(edge for edge in bridge._backend.query_composition_graph() if edge.id == edge_id)

    assert edge.authored_mapping == "hamutay.instance_tool.v1"
    assert edge.provenance.author_instance_id == "session-a"
    assert edge.provenance.author_model_family == "haiku"
    assert edge.provenance.authorship_verified is False


def test_instance_edge_rejects_missing_endpoint_without_storing():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    existing = uuid4()
    missing = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, existing, _now())
    before = tuple(bridge._backend.query_composition_graph())

    with pytest.raises(ValueError, match="edge endpoint does not exist"):
        bridge.store_edge(existing, missing, "CONFIRMS", ordering=2)

    assert tuple(bridge._backend.query_composition_graph()) == before


def test_instance_edge_rejects_self_loop():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    record_id = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, record_id, _now())

    with pytest.raises(ValueError, match="self-loop"):
        bridge.store_edge(record_id, record_id, "CONFIRMS", ordering=2)


def test_repeated_annotation_is_distinct_append_only_assertion():
    bridge = ApachetaBridge.from_memory(session_id="session-a", model="haiku")
    left = uuid4()
    right = uuid4()
    bridge.store_open_state({"cycle": 1}, 1, left, _now())
    bridge._prior_id = None
    bridge.store_open_state({"cycle": 1}, 1, right, _now())

    first = bridge.store_edge(left, right, "CONFIRMS", ordering=2)
    second = bridge.store_edge(left, right, "CONFIRMS", ordering=3)

    assert first != second
```

- [ ] **Step 2: Run the four tests and verify the present defects**

Run:

```bash
uv run pytest \
  tests/unit/test_apacheta_bridge.py::test_instance_edge_carries_asserted_unverified_provenance \
  tests/unit/test_apacheta_bridge.py::test_instance_edge_rejects_missing_endpoint_without_storing \
  tests/unit/test_apacheta_bridge.py::test_instance_edge_rejects_self_loop \
  tests/unit/test_apacheta_bridge.py::test_repeated_annotation_is_distinct_append_only_assertion \
  -v
```

Expected: the first three tests FAIL; the append-only duplicate-semantics test PASSes.

- [ ] **Step 3: Implement the minimal bridge policy**

Replace `ApachetaBridge.store_edge` with:

```python
    def store_edge(
        self,
        from_record: UUID,
        to_record: UUID,
        relation_type: str,
        ordering: int = 0,
    ) -> UUID:
        """Store one asserted instance annotation between existing records.

        Self-loops are rejected. Repeated non-self annotations remain distinct
        append-only assertions with independently minted edge identities.
        """
        from yanantin.apacheta.models.composition import CompositionEdge, RelationType
        from yanantin.apacheta.interface import NotFoundError
        from yanantin.apacheta.models.provenance import ProvenanceEnvelope

        if from_record == to_record:
            raise ValueError("instance-authored edge cannot be a self-loop")
        for endpoint in (from_record, to_record):
            try:
                self._backend.get_record(endpoint)
            except NotFoundError as exc:
                raise ValueError(f"edge endpoint does not exist: {endpoint}") from exc

        edge = CompositionEdge(
            from_tensor=from_record,
            to_tensor=to_record,
            relation_type=RelationType[relation_type],
            ordering=ordering,
            authored_mapping="hamutay.instance_tool.v1",
            provenance=ProvenanceEnvelope(
                author_model_family=self._model,
                author_instance_id=self._session_id,
                authorship_verified=False,
            ),
        )
        self._backend.store_composition_edge(edge)
        return edge.id
```

Do not catch `ValueError` in the bridge. `tool_annotate_edge` already maps bridge exceptions to its identifier-only error result.

- [ ] **Step 4: Add tool-boundary assertions**

Append to `tests/unit/test_graph_tools.py`:

```python
def test_annotate_edge_reports_missing_endpoint_without_edge():
    bridge = ApachetaBridge.from_memory(session_id="s", model="haiku")
    existing = uuid4()
    missing = uuid4()
    bridge.store_open_state(
        {"cycle": 1}, cycle=1, record_id=existing, timestamp=_now()
    )

    result = tool_annotate_edge(
        {
            "from_record_id": str(existing),
            "to_record_id": str(missing),
            "relation": "CONFIRMS",
        },
        cycle=2,
        bridge=bridge,
    )

    assert result == {
        "error": f"Edge creation failed: edge endpoint does not exist: {missing}"
    }


def test_annotate_edge_reports_self_loop():
    bridge = ApachetaBridge.from_memory(session_id="s", model="haiku")
    record_id = uuid4()
    bridge.store_open_state(
        {"cycle": 1}, cycle=1, record_id=record_id, timestamp=_now()
    )

    result = tool_annotate_edge(
        {
            "from_record_id": str(record_id),
            "to_record_id": str(record_id),
            "relation": "CONFIRMS",
        },
        cycle=2,
        bridge=bridge,
    )

    assert result == {
        "error": "Edge creation failed: instance-authored edge cannot be a self-loop"
    }
```

- [ ] **Step 5: Run bridge and graph suites**

Run:

```bash
uv run pytest tests/unit/test_apacheta_bridge.py tests/unit/test_graph_tools.py -v
```

Expected: PASS. No ArangoDB connection is attempted.

- [ ] **Step 6: Commit the graph boundary**

```bash
git add src/hamutay/apacheta_bridge.py tests/unit/test_apacheta_bridge.py tests/unit/test_graph_tools.py
git -c user.email=hamutay@wamason.com \
    -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "Preserve provenance on instance graph edges"
```

Expected: the post-commit hook creates a separate signed OTS stamp commit.

---

### Task 3: Turn boundary invariants into executable receipt guards

**Files:**
- Create: `src/hamutay/memory/receipts.py`
- Create: `tests/unit/test_memory_boundary_invariants.py`

**Interfaces:**
- Consumes: Pydantic 2; llm-memory's public `episode://` references and search metadata as plain values.
- Produces: immutable `EpisodicRetrievalReceipt` and nested `IndexedMemberBoundary` value objects for the later production receipt port. Both validate every `model_copy(update=...)` replacement instead of accepting Pydantic's unvalidated update path.

**Approved final-review amendment (2026-07-26):** The adversarial suite must cover strict numeric input, validated replacement copies (including forged authorship and loss of authoritative-open standing), zero-result and pre-selection failure shapes, selection pairing, impossible cardinality, indexed and selected corpus mismatch, malformed opaque URIs, and naive timestamps. The implementation skeleton below is illustrative; these amended requirements and the committed executable tests are authoritative wherever the original skeleton was incomplete.

- [ ] **Step 1: Write the adversarial tests first**

Create `tests/unit/test_memory_boundary_invariants.py`:

```python
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from hamutay.memory.receipts import (
    EpisodicRetrievalReceipt,
    IndexedMemberBoundary,
)


def valid_receipt(**changes):
    values = {
        "cycle_id": uuid4(),
        "session_id": "session-a",
        "author_model_family": "codex",
        "author_instance_id": "session-a",
        "authorship_verified": False,
        "purpose": "check a prior design decision",
        "query": "memory boundary",
        "corpus_ids": ("codex-history",),
        "limit": 10,
        "strategy": "lexical_bm25_text_en_v1",
        "match_semantics": "analyzed_any_token",
        "indexed_members": (
            IndexedMemberBoundary(
                corpus_id="codex-history",
                source_id="source-a",
                member_id="member-a",
                indexed_through_kind="byte_offset",
                indexed_through_value=123,
            ),
        ),
        "episode_ref": "episode://codex-history/session/episode",
        "returned_episode_count": 5,
        "selected_episode_rank": 1,
        "total_matches": 12,
        "total_standing": "exact",
        "search_index_standing": "available",
        "open_standing": "available",
        "retrieved_at": datetime.now(timezone.utc),
        "outcome": "used",
    }
    values.update(changes)
    return EpisodicRetrievalReceipt(**values)


def test_valid_receipt_is_immutable_and_unverified():
    receipt = valid_receipt()
    assert receipt.authorship_verified is False
    with pytest.raises(ValidationError):
        receipt.authorship_verified = True


def test_invariant_1_rejects_copied_episode_body_and_snippet():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        valid_receipt(episode_body={"response": "copied"})
    with pytest.raises(ValidationError, match="extra_forbidden"):
        valid_receipt(snippet="copied search text")


def test_invariant_2_rejects_uuid_in_place_of_episode_reference():
    with pytest.raises(ValidationError, match="episode_ref"):
        valid_receipt(episode_ref=str(uuid4()))


def test_invariant_5_requires_authoritative_open_before_use():
    with pytest.raises(ValidationError, match="authoritative open"):
        valid_receipt(open_standing="unavailable", outcome="used")


def test_total_unknown_is_explicit_null_not_zero_or_omission():
    receipt = valid_receipt(total_standing="unknown", total_matches=None)
    assert "total_matches" in receipt.model_dump()
    assert receipt.total_matches is None
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_standing="unknown", total_matches=0)


def test_exact_total_requires_nonnegative_integer():
    with pytest.raises(ValidationError, match="total_matches"):
        valid_receipt(total_standing="exact", total_matches=None)


def test_selected_rank_cannot_exceed_returned_episode_count():
    with pytest.raises(ValidationError, match="selected_episode_rank"):
        valid_receipt(returned_episode_count=2, selected_episode_rank=3)
```

- [ ] **Step 2: Verify the tests fail because the contract module does not exist**

Run:

```bash
uv run pytest tests/unit/test_memory_boundary_invariants.py -v
```

Expected: collection ERROR with `ModuleNotFoundError: No module named 'hamutay.memory.receipts'`.

- [ ] **Step 3: Implement the strict value objects**

Create `src/hamutay/memory/receipts.py`:

```python
"""Strict, content-minimized receipts for cross-project episodic retrieval."""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, model_validator


class IndexedMemberBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    corpus_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    indexed_through_kind: str = Field(min_length=1)
    indexed_through_value: StrictInt = Field(ge=0)


class EpisodicRetrievalReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: UUID = Field(default_factory=uuid4)
    cycle_id: UUID
    session_id: str = Field(min_length=1)
    author_model_family: str = Field(min_length=1)
    author_instance_id: str = Field(min_length=1)
    authorship_verified: Literal[False] = False
    purpose: str = Field(min_length=1)
    query: str = Field(min_length=1)
    corpus_ids: tuple[str, ...] = Field(min_length=1)
    limit: StrictInt = Field(ge=1, le=100)
    strategy: str = Field(min_length=1)
    match_semantics: str = Field(min_length=1)
    indexed_members: tuple[IndexedMemberBoundary, ...] = Field(min_length=1)
    episode_ref: str | None = None
    returned_episode_count: StrictInt = Field(ge=0)
    selected_episode_rank: StrictInt | None = Field(default=None, ge=1)
    total_matches: StrictInt | None = Field(ge=0)
    total_standing: Literal["exact", "unknown"]
    search_index_standing: str = Field(min_length=1)
    open_standing: str = Field(min_length=1)
    retrieved_at: AwareDatetime
    outcome: Literal[
        "used",
        "not-used",
        "unavailable",
        "withdrawn",
        "malformed",
        "unauthorized",
        "error",
    ]
    resulting_action_id: UUID | None = None
    interface_version: Literal["v1"] = "v1"
    schema_version: StrictInt = Field(default=1, ge=1, le=1)

    @model_validator(mode="after")
    def validate_cross_field_standing(self) -> Self:
        # The final implementation also validates replacement copies and the
        # amended URI, selection, cardinality, corpus, and timestamp rules.
        if (
            self.selected_episode_rank is not None
            and self.selected_episode_rank > self.returned_episode_count
        ):
            raise ValueError(
                "selected_episode_rank exceeds returned_episode_count"
            )
        if self.total_standing == "exact" and self.total_matches is None:
            raise ValueError("exact total_standing requires total_matches")
        if self.total_standing == "unknown" and self.total_matches is not None:
            raise ValueError("unknown total_standing requires total_matches=null")
        if self.outcome == "used" and self.open_standing != "available":
            raise ValueError("used evidence requires authoritative open standing available")
        return self
```

- [ ] **Step 4: Run the invariant tests**

Run:

```bash
uv run pytest tests/unit/test_memory_boundary_invariants.py -v
```

Expected: all adversarial receipt cases PASS.

- [ ] **Step 5: Run the entire database-free unit suite**

Run:

```bash
uv run pytest tests/unit -v
```

Expected: PASS. Any pre-existing skip remains visible and must be enumerated before committing; no new skip or xfail is allowed.

- [ ] **Step 6: Commit the executable boundary contract**

```bash
git add src/hamutay/memory/receipts.py tests/unit/test_memory_boundary_invariants.py
git -c user.email=hamutay@wamason.com \
    -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "Guard cross-project memory receipts"
```

Expected: the post-commit hook creates a separate signed OTS stamp commit.

---

### Task 4: Move the invariant checks outside the local writer

**Files:**
- Create: `.github/workflows/memory-boundary-invariants.yml`

**Interfaces:**
- Consumes: Tasks 1-3 and Hamut'ay's committed `uv.lock`.
- Produces: GitHub Actions job context `boundary-invariants` from integration ID `15368` (displayed as `Memory boundary invariants / boundary-invariants`); it is useful only after repository rules require it.

- [ ] **Step 1: Create the remote workflow**

Create `.github/workflows/memory-boundary-invariants.yml`:

```yaml
name: Memory boundary invariants

on:
  push:
    branches: [main]
    paths:
      - "src/hamutay/apacheta_bridge.py"
      - "src/hamutay/memory/receipts.py"
      - "tests/unit/test_apacheta_bridge.py"
      - "tests/unit/test_graph_tools.py"
      - "tests/unit/test_memory_boundary_invariants.py"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/memory-boundary-invariants.yml"
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: memory-boundary-${{ github.ref }}
  cancel-in-progress: true

jobs:
  boundary-invariants:
    name: boundary-invariants
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5

      - name: Install uv
        uses: astral-sh/setup-uv@37802adc94f370d6bfd71619e3f0bf239e1f3b78 # v7
        with:
          enable-cache: true

      - name: Install locked dependencies
        run: uv sync --locked --extra dev

      - name: Verify boundary invariants
        run: >-
          uv run --no-sync pytest
          tests/unit/test_memory_boundary_invariants.py
          tests/unit/test_apacheta_bridge.py
          tests/unit/test_graph_tools.py
          -v
```

- [ ] **Step 2: Validate the workflow's commands locally**

Run:

```bash
uv sync --locked --extra dev
uv run --no-sync pytest \
  tests/unit/test_memory_boundary_invariants.py \
  tests/unit/test_apacheta_bridge.py \
  tests/unit/test_graph_tools.py \
  -v
```

Expected: PASS with no ArangoDB service and no credentials.

- [ ] **Step 3: Commit, push the feature branch, and open a pull request**

```bash
git add .github/workflows/memory-boundary-invariants.yml
git -c user.email=hamutay@wamason.com \
    -c user.name="Tony Mason" \
    -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 \
    commit -S -m "Run memory invariants in remote CI"
git push -u origin memory-boundary-preconditions
gh pr create \
  --base main \
  --head memory-boundary-preconditions \
  --title "Enforce memory boundary preconditions" \
  --body "Implements the reviewed memory-boundary preconditions with local and remote invariant evidence."
```

Expected: the code commit and its OTS stamp commit push on the feature branch, a pull request targets `main`, and GitHub Actions reports the job context `boundary-invariants` from GitHub Actions integration ID `15368` (the UI may display `Memory boundary invariants / boundary-invariants`). Never push this feature work directly to `main`.

- [ ] **Step 4: Inspect, then require the remote status check**

First inspect repository rulesets without changing repository settings; legacy branch-protection endpoints are not authoritative for this repository:

```bash
gh api repos/fsgeek/hamutay/rulesets
gh api repos/fsgeek/hamutay/rulesets/19747404
gh api repos/fsgeek/hamutay/rulesets/13896889
```

Ruleset `19747404` owns the required status check. If that rule is absent, inactive, or mismatched, stop and obtain explicit authorization before changing GitHub repository rules. Only ruleset `19747404` may be updated, and only narrowly enough to require context `boundary-invariants` with integration ID `15368` before integration to `main`; preserve every unrelated rule in it. Ruleset `13896889` separately owns the signature and non-fast-forward protections. It must remain active and unchanged.

Re-read the result:

```bash
gh api repos/fsgeek/hamutay/rulesets/19747404 \
  --jq '{enforcement, rules}'
gh api repos/fsgeek/hamutay/rulesets/13896889 \
  --jq '{enforcement, rules}'
```

Expected: ruleset `19747404` is active and its required-status-check rule includes `{"context":"boundary-invariants","integration_id":15368}`. Separately, ruleset `13896889` is active and unchanged, with its required-signatures and non-fast-forward rules intact. Merely committing the workflow is not completion; if the remote check can be omitted without blocking integration, or the separate signature/non-fast-forward ruleset has changed, this task remains incomplete.

---

## Completion gate and next design question

This plan is complete only when:

1. Hamut'ay's locked environment exposes immutable `authorship_verified=False` by default.
2. Instance-authored edges preserve asserted/unverified provenance, reject missing endpoints and self-loops, and explicitly permit repeated append-only assertions.
3. The receipt model mechanically rejects copied bodies/snippets, malformed or UUID-substituted episode references, coercible numeric values, unvalidated replacement copies, impossible cardinality/corpus combinations, naive timestamps, and `used` outcomes without authoritative open and selection.
4. Zero-result and pre-selection failure receipts carry no invented selection data; unknown `total_matches` is explicit `null`, never omission or zero.
5. The remote GitHub job context `boundary-invariants` from integration ID `15368` passes and is required by active ruleset `19747404`; separate ruleset `13896889` remains active and unchanged with its required-signatures and non-fast-forward rules intact.

Completion does **not** authorize the retrieval proof. Before planning that package, decide which production component implements Hamut'ay's `MemoryPort`: a Yanantin-backed adapter, an extension of `ApachetaBridge` behind the port, or another independently reviewed implementation. The local contract-test substrate cannot satisfy the proof.
