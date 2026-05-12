# Memory Tools (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give taste_open instances five memory tools (`memory_schema`, `recall`, `compare`, `walk`, `search_memory`) that let them introspect their own prior cycles without consuming context window for full state carry-over.

**Architecture:** Memory tools read from the in-session `_prior_states` accumulator that `OpenTasteSession` already maintains (populated live during a session; rebuilt from JSONL on resume). No ArangoDB integration in this phase — the yanantin backend has no high-level query API for open-schema records (confirmed 2026-04-18: `list_tensors()` returns only `TensorRecord`, not `ApachetaBaseModel`; `query_project_state()` reports 0 tensors despite 61 records present). ArangoDB remains the write-through sink via the existing `ApachetaBridge`. Cross-session memory query is deferred to a later phase that will extend yanantin.

**Tech Stack:** Python 3.14, pytest, uv. No new dependencies.

**Spec:** `docs/tool_api_proposal_v3.md` — section I (Memory). Phase 2 implements all 5 tools from v3 (Phase 1 handoff corrected the prior plan's footer from 3 back to 5; `memory_schema` and `compare` were the two that had been dropped).

**Deviations from v3 spec** (all reflected in the tool descriptions the instance reads, so no surprise):
- No `attestation` fields — Willay attestation service isn't stood up yet. Phase 3 concern.
- `walk` has no `edge_type` filter — only `REFINES` edges currently exist, so the parameter would have a trivial domain. Walk is cycle-adjacent traversal.
- `search_memory` is keyword/substring matching, not semantic similarity. No embedding dependency. The structured narrowing primitives (cycle_range, fields, has_field) do the real work; keyword search is honest about being grep.
- `search_memory` drops `activity_type` and `updated_in_same_cycle` narrowing — both require cross-cycle history not present in `_prior_states`. Revisit when the JSONL reader is promoted or the activity stream accumulates.
- `memory_schema` drops `edge_count`/`edge_types` — the instance's in-session view has no explicit edges. Cycle-to-cycle structure is implicit in ordering.

---

## File Structure

```
src/hamutay/tools/
    memory.py           # NEW — tool_memory_schema, tool_recall, tool_compare,
                        #       tool_walk, tool_search_memory (pure functions)
    schemas.py          # MODIFY — add MEMORY_SCHEMA_*_SCHEMA dicts, register in TOOL_SCHEMAS
    executor.py         # MODIFY — accept prior_states param; dispatch memory tool names
src/hamutay/taste_open.py
    # MODIFY:
    # - _prior_states entries change from (cycle, state) to (cycle, state, timestamp)
    # - _resume_from_log harvests timestamp field from JSONL records
    # - exchange() appends timestamp when accumulating
    # - exchange() passes _prior_states to ToolExecutor when tools are enabled
    # - _pick_memory unpacks the triple and returns the (cycle, state) pair
    #   (its consumers haven't changed)
    # - _TOOL_GUIDANCE appends a Memory Tools section
tests/unit/
    test_memory_tools.py   # NEW — unit tests for each memory tool
    test_executor.py       # MODIFY — add tests for memory tool dispatch
    test_exchange_tools.py # MODIFY — add test for _prior_states timestamp accumulation
tests/integration/
    test_tool_integration.py  # MODIFY — add a memory-tool exercise against Haiku
```

Each memory tool is a pure function `tool_X(params: dict, *, prior_states: list[tuple[int, dict, str]]) -> dict`, mirroring the Phase 1 perception pattern.

---

### Task 1: Timestamped `_prior_states`

Change the in-session history accumulator from `list[tuple[int, dict]]` to `list[tuple[int, dict, str]]` so memory tools can return per-state timestamps. Update the resume path, the exchange append, and `_pick_memory` (which unpacks the triple and returns the first two elements — its contract to callers is unchanged).

**Files:**
- Modify: `src/hamutay/taste_open.py` (`_prior_states` type annotation at line ~619, `_resume_from_log` at line 647-652, `exchange` at line ~743, `_pick_memory` at line 683-684)
- Create: `tests/unit/test_exchange_tools.py` (append a new test — file already exists)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_exchange_tools.py (append)

def test_prior_states_store_timestamps():
    """_prior_states accumulates (cycle, state, timestamp) triples."""
    from unittest.mock import MagicMock
    from hamutay.taste_open import OpenTasteSession, ExchangeResult

    backend = MagicMock()
    backend.call.return_value = ExchangeResult(
        raw_output={"response": "hi", "updated_regions": ["greeting"], "greeting": "hello"},
        stop_reason="end_turn",
    )
    session = OpenTasteSession(backend=backend)
    session.exchange("hey")
    session.exchange("again")

    assert len(session._prior_states) == 2
    # Each entry is a triple of (cycle, state, timestamp)
    for cycle, state, timestamp in session._prior_states:
        assert isinstance(cycle, int)
        assert isinstance(state, dict)
        assert isinstance(timestamp, str)
        # Parse-able ISO 8601
        from datetime import datetime
        datetime.fromisoformat(timestamp)


def test_pick_memory_still_returns_two_tuple():
    """_pick_memory's contract to callers is unchanged despite the 3-tuple storage.

    _last_injected_memory and the _log_entry memory_info branch both read the
    result as (cycle, state) — this test guards against accidentally leaking
    the timestamp element back to callers.
    """
    from unittest.mock import MagicMock
    from hamutay.taste_open import OpenTasteSession, ExchangeResult
    import random

    backend = MagicMock()
    backend.call.return_value = ExchangeResult(
        raw_output={"response": "ok", "updated_regions": ["theme"], "theme": "x"},
        stop_reason="end_turn",
    )
    session = OpenTasteSession(backend=backend, memory_base_probability=1.0)
    # Build up enough history that _pick_memory has candidates (needs >= 2)
    for _ in range(4):
        session.exchange("hi")

    random.seed(0)
    picked = session._pick_memory()
    if picked is not None:
        assert len(picked) == 2, f"_pick_memory should return (cycle, state), got {picked!r}"
        cycle, state = picked
        assert isinstance(cycle, int)
        assert isinstance(state, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_exchange_tools.py::test_prior_states_store_timestamps -v`
Expected: FAIL (ValueError: not enough values to unpack, or tuple-of-2 when 3 expected)

- [ ] **Step 3: Update the type annotation and the three mutation sites**

In `src/hamutay/taste_open.py`:

```python
# ~line 619 — type annotation
self._prior_states: list[tuple[int, dict, str]] = []
```

```python
# _resume_from_log — rebuild with timestamps from the JSONL record
for line in lines:
    record = json.loads(line)
    state = record.get("state")
    cycle = record.get("cycle", 0)
    timestamp = record.get("timestamp", "")
    if state is not None:
        self._prior_states.append((cycle, state, timestamp))
```

```python
# exchange() — around line 743, include timestamp
self._prior_states.append(
    (self._cycle, json.loads(json.dumps(self._state)), self._last_cycle_time.isoformat())
)
```

Note: `self._last_cycle_time` is set at line 740 (just before this append) to `datetime.now(timezone.utc)`, so `.isoformat()` is always available here.

```python
# _pick_memory — unpack the triple; contract to callers is unchanged
candidates = self._prior_states[:-1]
cycle, state, _timestamp = random.choice(candidates)
return (cycle, state)
```

- [ ] **Step 4: Run all unit tests**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests PASS (no regression in existing tests)

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/taste_open.py tests/unit/test_exchange_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: carry per-state timestamps in _prior_states triples"
```

---

### Task 2: `memory_schema` tool

Returns the structure of a cycle's state without retrieving content. Cheap introspection — decide what's worth pulling before pulling it.

**Files:**
- Create: `src/hamutay/tools/memory.py`
- Create: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_memory_tools.py
from hamutay.tools.memory import tool_memory_schema


def _make_prior_states():
    """Fixture: three cycles of prior state with varied structure."""
    return [
        (1, {"greeting": "hello", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
        (2, {"greeting": "hi", "theme": "curiosity", "cycle": 2}, "2026-04-18T10:01:00+00:00"),
        (3, {"greeting": "hey", "theme": "care", "notes": ["a", "b"], "cycle": 3},
         "2026-04-18T10:02:00+00:00"),
    ]


def test_memory_schema_returns_structure():
    prior_states = _make_prior_states()
    result = tool_memory_schema({"cycle": 3}, prior_states=prior_states)
    assert result["cycle"] == 3
    assert result["timestamp"] == "2026-04-18T10:02:00+00:00"
    assert set(result["field_names"]) == {"greeting", "theme", "notes", "cycle"}
    assert result["field_types"]["notes"] == "list"
    assert result["field_types"]["greeting"] == "str"
    assert result["field_sizes"]["notes"] == 2  # len of list
    assert result["total_tokens"] > 0


def test_memory_schema_missing_cycle():
    prior_states = _make_prior_states()
    result = tool_memory_schema({"cycle": 99}, prior_states=prior_states)
    assert "error" in result


def test_memory_schema_no_prior_states():
    result = tool_memory_schema({"cycle": 1}, prior_states=[])
    assert "error" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_memory_tools.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement `tool_memory_schema`**

```python
# src/hamutay/tools/memory.py
"""Memory tools — introspection over the instance's own prior cycles.

Each tool is a pure function:
    tool_name(params: dict, *, prior_states: list[tuple[int, dict, str]]) -> dict

prior_states is the session's accumulated history: (cycle, state, timestamp_iso).
Tools return dicts with either content or error, never both.
"""

from __future__ import annotations

import json


def _find_by_cycle(
    prior_states: list[tuple[int, dict, str]], cycle: int
) -> tuple[int, dict, str] | None:
    """Return the first (cycle, state, timestamp) triple matching cycle, or None."""
    for entry in prior_states:
        if entry[0] == cycle:
            return entry
    return None


def _type_name(value) -> str:
    """Compact Python type name for a JSON-ish value."""
    return type(value).__name__


def _field_size(value) -> int:
    """Rough size: len for containers, string length for strings, 1 otherwise."""
    if isinstance(value, (list, tuple, dict, set, str)):
        return len(value)
    return 1


def _token_estimate(state: dict) -> int:
    """Rough token count: JSON bytes / 4."""
    return len(json.dumps(state, default=str)) // 4


def tool_memory_schema(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Return structure of a prior cycle's state without content."""
    cycle = params.get("cycle")
    if cycle is None:
        return {"error": "cycle is required"}

    found = _find_by_cycle(prior_states, cycle)
    if found is None:
        return {"error": f"No state found for cycle {cycle}"}

    _cycle, state, timestamp = found
    return {
        "cycle": _cycle,
        "timestamp": timestamp,
        "field_names": sorted(state.keys()),
        "field_types": {k: _type_name(v) for k, v in state.items()},
        "field_sizes": {k: _field_size(v) for k, v in state.items()},
        "total_tokens": _token_estimate(state),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_memory_tools.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: memory_schema tool — cycle structure without content"
```

---

### Task 3: `recall` tool

Retrieve content from a prior cycle. Four mutually exclusive modes: surgical (cycle+field), full (cycle), trajectory (recent+field), serendipitous (random+field).

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_memory_tools.py (append)
from hamutay.tools.memory import tool_recall


def test_recall_surgical():
    """cycle + field returns just that field."""
    result = tool_recall(
        {"cycle": 2, "field": "theme"},
        prior_states=_make_prior_states(),
    )
    assert result["cycle"] == 2
    assert result["content"] == "curiosity"


def test_recall_full_snapshot():
    """cycle alone returns the full state dict."""
    result = tool_recall({"cycle": 3}, prior_states=_make_prior_states())
    assert result["cycle"] == 3
    assert result["content"]["theme"] == "care"
    assert result["content"]["notes"] == ["a", "b"]


def test_recall_recent_trajectory():
    """recent=N, field=X returns last N values of X across cycles."""
    result = tool_recall(
        {"recent": 3, "field": "greeting"},
        prior_states=_make_prior_states(),
    )
    # content is list of {cycle, value} ordered most-recent first
    assert len(result["content"]) == 3
    assert result["content"][0]["cycle"] == 3
    assert result["content"][0]["value"] == "hey"
    assert result["content"][2]["value"] == "hello"


def test_recall_recent_skips_missing_field():
    """recent mode skips cycles where the field doesn't exist."""
    result = tool_recall(
        {"recent": 5, "field": "theme"},
        prior_states=_make_prior_states(),
    )
    # Only cycles 2 and 3 have "theme"
    assert len(result["content"]) == 2
    cycles_returned = {e["cycle"] for e in result["content"]}
    assert cycles_returned == {2, 3}


def test_recall_random_picks_from_history():
    """random=true, field=X picks any prior state that has field X."""
    import random
    random.seed(42)
    result = tool_recall(
        {"random": True, "field": "greeting"},
        prior_states=_make_prior_states(),
    )
    assert result["cycle"] in {1, 2, 3}
    assert "content" in result


def test_recall_missing_cycle():
    result = tool_recall({"cycle": 99}, prior_states=_make_prior_states())
    assert "error" in result


def test_recall_missing_field_surgical():
    result = tool_recall(
        {"cycle": 1, "field": "theme"},  # cycle 1 has no "theme"
        prior_states=_make_prior_states(),
    )
    assert "error" in result


def test_recall_no_mode_is_error():
    """Calling recall with no mode selector is an error."""
    result = tool_recall({}, prior_states=_make_prior_states())
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_memory_tools.py -k recall -v`
Expected: FAIL (ImportError for tool_recall)

- [ ] **Step 3: Implement `tool_recall`**

```python
# src/hamutay/tools/memory.py (append)

import random as _random


def tool_recall(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Retrieve content from prior cycles. Four modes — mutually exclusive."""
    cycle = params.get("cycle")
    field = params.get("field")
    recent = params.get("recent")
    is_random = params.get("random", False)

    if cycle is not None:
        found = _find_by_cycle(prior_states, cycle)
        if found is None:
            return {"error": f"No state found for cycle {cycle}"}
        _cycle, state, timestamp = found
        if field is not None:
            if field not in state:
                return {
                    "error": f"Field {field!r} not in state at cycle {cycle}"
                }
            return {
                "cycle": _cycle,
                "timestamp": timestamp,
                "content": state[field],
            }
        return {
            "cycle": _cycle,
            "timestamp": timestamp,
            "content": dict(state),
        }

    if recent is not None:
        if field is None:
            return {"error": "recent mode requires field"}
        # Walk from most-recent backward, collect up to `recent` hits
        collected = []
        for _cycle, state, timestamp in reversed(prior_states):
            if field in state:
                collected.append(
                    {
                        "cycle": _cycle,
                        "timestamp": timestamp,
                        "value": state[field],
                    }
                )
                if len(collected) >= recent:
                    break
        return {"content": collected}

    if is_random:
        if field is None:
            return {"error": "random mode requires field"}
        candidates = [
            (c, s, t) for (c, s, t) in prior_states if field in s
        ]
        if not candidates:
            return {"error": f"No prior cycles contain field {field!r}"}
        _cycle, state, timestamp = _random.choice(candidates)
        return {
            "cycle": _cycle,
            "timestamp": timestamp,
            "content": state[field],
        }

    return {"error": "recall requires one of: cycle, recent, random"}
```

- [ ] **Step 4: Run recall tests**

Run: `uv run pytest tests/unit/test_memory_tools.py -k recall -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: recall tool — surgical/full/trajectory/serendipity modes"
```

---

### Task 4: `compare` tool

Structural diff between two cycles: added, removed, changed, unchanged fields. Optionally include values of changed fields (content=true).

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_memory_tools.py (append)
from hamutay.tools.memory import tool_compare


def test_compare_added_and_changed():
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 2},
        prior_states=_make_prior_states(),
    )
    assert result["cycle_a"] == 1
    assert result["cycle_b"] == 2
    assert "theme" in result["added_fields"]
    assert "greeting" in [c["field"] for c in result["changed_fields"]]
    # Without content=true, no values in the delta
    greeting_change = next(
        c for c in result["changed_fields"] if c["field"] == "greeting"
    )
    assert "value_a" not in greeting_change
    assert "value_b" not in greeting_change


def test_compare_with_content_shows_values():
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 2, "content": True},
        prior_states=_make_prior_states(),
    )
    greeting_change = next(
        c for c in result["changed_fields"] if c["field"] == "greeting"
    )
    assert greeting_change["value_a"] == "hello"
    assert greeting_change["value_b"] == "hi"


def test_compare_field_scopes_delta():
    """When field=X, only that field is compared."""
    result = tool_compare(
        {"cycle_a": 1, "cycle_b": 3, "field": "greeting"},
        prior_states=_make_prior_states(),
    )
    # Only greeting's delta is reported
    assert result["changed_fields"] == [
        {"field": "greeting", "size_a": 5, "size_b": 3}
    ]
    assert result["added_fields"] == []
    assert result["removed_fields"] == []


def test_compare_missing_cycle_errors():
    result = tool_compare(
        {"cycle_a": 99, "cycle_b": 1},
        prior_states=_make_prior_states(),
    )
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_memory_tools.py -k compare -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement `tool_compare`**

```python
# src/hamutay/tools/memory.py (append)

def tool_compare(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Structural diff between two prior cycles."""
    cycle_a = params.get("cycle_a")
    cycle_b = params.get("cycle_b")
    field = params.get("field")
    content = params.get("content", False)

    if cycle_a is None or cycle_b is None:
        return {"error": "cycle_a and cycle_b are required"}

    entry_a = _find_by_cycle(prior_states, cycle_a)
    entry_b = _find_by_cycle(prior_states, cycle_b)
    if entry_a is None:
        return {"error": f"No state found for cycle {cycle_a}"}
    if entry_b is None:
        return {"error": f"No state found for cycle {cycle_b}"}

    _, state_a, _ = entry_a
    _, state_b, _ = entry_b

    if field is not None:
        # Scoped compare
        a_val = state_a.get(field, _MISSING)
        b_val = state_b.get(field, _MISSING)
        added = []
        removed = []
        changed = []
        unchanged = []
        if a_val is _MISSING and b_val is not _MISSING:
            added = [field]
        elif a_val is not _MISSING and b_val is _MISSING:
            removed = [field]
        elif a_val != b_val:
            entry = {
                "field": field,
                "size_a": _field_size(a_val),
                "size_b": _field_size(b_val),
            }
            if content:
                entry["value_a"] = a_val
                entry["value_b"] = b_val
            changed = [entry]
        elif a_val is not _MISSING:
            unchanged = [field]
    else:
        keys_a = set(state_a.keys())
        keys_b = set(state_b.keys())
        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        changed = []
        unchanged = []
        for key in sorted(keys_a & keys_b):
            if state_a[key] != state_b[key]:
                entry = {
                    "field": key,
                    "size_a": _field_size(state_a[key]),
                    "size_b": _field_size(state_b[key]),
                }
                if content:
                    entry["value_a"] = state_a[key]
                    entry["value_b"] = state_b[key]
                changed.append(entry)
            else:
                unchanged.append(key)

    return {
        "cycle_a": cycle_a,
        "cycle_b": cycle_b,
        "added_fields": added,
        "removed_fields": removed,
        "changed_fields": changed,
        "unchanged_fields": unchanged,
        "structural_delta": {
            "total_tokens_a": _token_estimate(state_a),
            "total_tokens_b": _token_estimate(state_b),
            "field_count_a": len(state_a),
            "field_count_b": len(state_b),
        },
    }


_MISSING = object()
```

- [ ] **Step 4: Run compare tests**

Run: `uv run pytest tests/unit/test_memory_tools.py -k compare -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: compare tool — structural diff between two prior cycles"
```

---

### Task 5: `walk` tool

Traverse adjacent cycles from a starting cycle. direction ∈ {forward, backward, both}, depth controls how many steps. Only REFINES edges exist right now, so traversal is cycle-adjacent in the in-session history.

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_memory_tools.py (append)
from hamutay.tools.memory import tool_walk


def _wide_prior_states():
    """Five cycles with varied field presence."""
    return [
        (1, {"theme": "opening", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
        (2, {"theme": "exploring", "cycle": 2}, "2026-04-18T10:01:00+00:00"),
        (3, {"theme": "focus", "pivot": True, "cycle": 3}, "2026-04-18T10:02:00+00:00"),
        (4, {"theme": "deepening", "cycle": 4}, "2026-04-18T10:03:00+00:00"),
        (5, {"theme": "closing", "cycle": 5}, "2026-04-18T10:04:00+00:00"),
    ]


def test_walk_forward():
    result = tool_walk(
        {"from_cycle": 2, "direction": "forward", "depth": 2},
        prior_states=_wide_prior_states(),
    )
    cycles_in_path = [step["cycle"] for step in result["path"]]
    # Forward from 2, depth 2: cycles 3 and 4 (not including 2 itself)
    assert cycles_in_path == [3, 4]


def test_walk_backward():
    result = tool_walk(
        {"from_cycle": 4, "direction": "backward", "depth": 2},
        prior_states=_wide_prior_states(),
    )
    cycles_in_path = [step["cycle"] for step in result["path"]]
    # Backward from 4, depth 2: cycles 3, 2 (most recent first)
    assert cycles_in_path == [3, 2]


def test_walk_both():
    result = tool_walk(
        {"from_cycle": 3, "direction": "both", "depth": 1},
        prior_states=_wide_prior_states(),
    )
    cycles_in_path = [step["cycle"] for step in result["path"]]
    # Both, depth 1: cycle 2 (back) + cycle 4 (forward), order backward-then-forward
    assert set(cycles_in_path) == {2, 4}


def test_walk_path_steps_have_summary():
    result = tool_walk(
        {"from_cycle": 1, "direction": "forward", "depth": 2},
        prior_states=_wide_prior_states(),
    )
    step = result["path"][0]
    assert "cycle" in step
    assert "timestamp" in step
    assert "field_names" in step
    assert "edge_type" in step
    assert step["edge_type"] == "refines"
    assert isinstance(step["summary"], str)


def test_walk_from_missing_cycle():
    result = tool_walk(
        {"from_cycle": 99, "direction": "forward"},
        prior_states=_wide_prior_states(),
    )
    assert "error" in result


def test_walk_boundaries_are_not_errors():
    """Walking past the ends returns what's available, not an error."""
    result = tool_walk(
        {"from_cycle": 5, "direction": "forward", "depth": 3},
        prior_states=_wide_prior_states(),
    )
    # Nothing forward of 5 exists
    assert result["path"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_memory_tools.py -k walk -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement `tool_walk`**

```python
# src/hamutay/tools/memory.py (append)

def _step_summary(state: dict) -> str:
    """One-line summary of a cycle for path steps."""
    keys = sorted(k for k in state.keys() if k != "cycle")
    if not keys:
        return "(empty state)"
    return f"{len(keys)} field(s): {', '.join(keys[:5])}" + (
        "..." if len(keys) > 5 else ""
    )


def tool_walk(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Traverse adjacent cycles from a starting cycle."""
    from_cycle = params.get("from_cycle")
    direction = params.get("direction", "both")
    depth = params.get("depth", 1)

    if from_cycle is None:
        return {"error": "from_cycle is required"}
    if _find_by_cycle(prior_states, from_cycle) is None:
        return {"error": f"No state found for cycle {from_cycle}"}

    # Index cycles for O(1) lookup
    by_cycle = {c: (c, s, t) for (c, s, t) in prior_states}

    path = []
    if direction in ("backward", "both"):
        for offset in range(1, depth + 1):
            target = from_cycle - offset
            entry = by_cycle.get(target)
            if entry is None:
                break
            _c, state, timestamp = entry
            path.append(
                {
                    "cycle": _c,
                    "timestamp": timestamp,
                    "edge_type": "refines",
                    "edge_source": "harness",
                    "field_names": sorted(state.keys()),
                    "summary": _step_summary(state),
                }
            )
    if direction in ("forward", "both"):
        for offset in range(1, depth + 1):
            target = from_cycle + offset
            entry = by_cycle.get(target)
            if entry is None:
                break
            _c, state, timestamp = entry
            path.append(
                {
                    "cycle": _c,
                    "timestamp": timestamp,
                    "edge_type": "refines",
                    "edge_source": "harness",
                    "field_names": sorted(state.keys()),
                    "summary": _step_summary(state),
                }
            )

    return {"path": path}
```

- [ ] **Step 4: Run walk tests**

Run: `uv run pytest tests/unit/test_memory_tools.py -k walk -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: walk tool — cycle-adjacent traversal forward/backward/both"
```

---

### Task 6: `search_memory` tool

Keyword/substring search over prior states. Narrowing primitives (cycle_range, fields, has_field) do structural filtering first; keyword match happens within the narrowed set. Results ranked by cycle descending (most recent first), with snippets showing matched context.

**Files:**
- Modify: `src/hamutay/tools/memory.py`
- Modify: `tests/unit/test_memory_tools.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_memory_tools.py (append)
from hamutay.tools.memory import tool_search_memory


def _searchable_prior_states():
    return [
        (1, {"theme": "opening", "mood": "tentative", "cycle": 1},
         "2026-04-18T10:00:00+00:00"),
        (2, {"theme": "curiosity", "mood": "tentative", "cycle": 2},
         "2026-04-18T10:01:00+00:00"),
        (3, {"theme": "care", "notes": ["first surprise", "pattern noticed"], "cycle": 3},
         "2026-04-18T10:02:00+00:00"),
        (4, {"theme": "pattern", "mood": "settled", "cycle": 4},
         "2026-04-18T10:03:00+00:00"),
    ]


def test_search_memory_basic_match():
    result = tool_search_memory(
        {"query": "pattern"},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    # Cycles 3 ("pattern noticed" in notes) and 4 (theme="pattern")
    assert set(matched_cycles) == {3, 4}


def test_search_memory_ranks_recent_first():
    result = tool_search_memory(
        {"query": "tentative"},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [2, 1]  # cycle 2 before cycle 1


def test_search_memory_narrow_by_cycle_range():
    result = tool_search_memory(
        {"query": "pattern", "narrow_by": {"cycle_range": [4, 10]}},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [4]


def test_search_memory_narrow_by_fields():
    result = tool_search_memory(
        {"query": "pattern", "narrow_by": {"fields": ["theme"]}},
        prior_states=_searchable_prior_states(),
    )
    # Must match inside "theme" field only — cycle 3's note doesn't count
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [4]


def test_search_memory_narrow_by_has_field():
    result = tool_search_memory(
        {"query": "a", "narrow_by": {"has_field": "notes"}},
        prior_states=_searchable_prior_states(),
    )
    matched_cycles = [r["cycle"] for r in result["results"]]
    assert matched_cycles == [3]


def test_search_memory_limit():
    result = tool_search_memory(
        {"query": "cycle", "limit": 2},
        prior_states=_searchable_prior_states(),
    )
    assert len(result["results"]) <= 2


def test_search_memory_metadata():
    result = tool_search_memory(
        {"query": "pattern"},
        prior_states=_searchable_prior_states(),
    )
    assert result["search_metadata"]["total_candidates"] == 4
    assert result["search_metadata"]["narrowed_to"] >= len(result["results"])


def test_search_memory_no_match():
    result = tool_search_memory(
        {"query": "nonexistentstring"},
        prior_states=_searchable_prior_states(),
    )
    assert result["results"] == []


def test_search_memory_missing_query():
    result = tool_search_memory({}, prior_states=_searchable_prior_states())
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_memory_tools.py -k search_memory -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Implement `tool_search_memory`**

```python
# src/hamutay/tools/memory.py (append)

def _value_contains(value, query_lower: str) -> bool:
    """Recursively check whether query appears as substring in value."""
    if isinstance(value, str):
        return query_lower in value.lower()
    if isinstance(value, dict):
        return any(_value_contains(v, query_lower) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_value_contains(v, query_lower) for v in value)
    # Numbers, bools, None — stringify and check
    return query_lower in str(value).lower()


def _snippet(value, query_lower: str, max_len: int = 120) -> str:
    """Extract a snippet around the match for display."""
    text = json.dumps(value, default=str)
    idx = text.lower().find(query_lower)
    if idx < 0:
        return text[:max_len]
    start = max(0, idx - 30)
    end = min(len(text), idx + len(query_lower) + 60)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + text[start:end] + suffix


def tool_search_memory(
    params: dict,
    *,
    prior_states: list[tuple[int, dict, str]],
) -> dict:
    """Keyword/substring search over prior states with structured narrowing."""
    query = params.get("query")
    narrow_by = params.get("narrow_by") or {}
    limit = params.get("limit", 5)

    if not query:
        return {"error": "query is required"}

    query_lower = query.lower()
    total = len(prior_states)

    # Narrow by structural primitives first
    candidates = list(prior_states)

    cycle_range = narrow_by.get("cycle_range")
    if cycle_range:
        lo, hi = cycle_range
        candidates = [(c, s, t) for (c, s, t) in candidates if lo <= c <= hi]

    has_field = narrow_by.get("has_field")
    if has_field:
        candidates = [(c, s, t) for (c, s, t) in candidates if has_field in s]

    field_filter = narrow_by.get("fields")  # restrict match scope to these fields

    # Match within narrowed candidates
    matches = []
    for cycle, state, timestamp in candidates:
        matched_fields = []
        snippets = {}
        search_fields = field_filter if field_filter else list(state.keys())
        for key in search_fields:
            if key not in state:
                continue
            if _value_contains(state[key], query_lower):
                matched_fields.append(key)
                snippets[key] = _snippet(state[key], query_lower)
        if matched_fields:
            matches.append(
                {
                    "cycle": cycle,
                    "timestamp": timestamp,
                    "relevance": 1.0,  # uniform — keyword hit is boolean
                    "matched_fields": matched_fields,
                    "snippets": snippets,
                }
            )

    matches.sort(key=lambda r: r["cycle"], reverse=True)
    limited = matches[:limit]

    return {
        "results": limited,
        "search_metadata": {
            "total_candidates": total,
            "narrowed_to": len(candidates),
            "matched_count": len(matches),
        },
    }
```

- [ ] **Step 4: Run search_memory tests**

Run: `uv run pytest tests/unit/test_memory_tools.py -k search_memory -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Run the full memory tools test suite**

Run: `uv run pytest tests/unit/test_memory_tools.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/tools/memory.py tests/unit/test_memory_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: search_memory tool — keyword search with structural narrowing"
```

---

### Task 7: Memory tool schemas

Register JSON schemas for all five memory tools so the Anthropic API knows how to call them. Descriptions match the calibrated voice from the 2026-04-18 audit: permissive, descriptive-not-directive, symmetric generosity on `reason`.

**Files:**
- Modify: `src/hamutay/tools/schemas.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_perception.py (append — test_schemas_exist already lives here)

def test_memory_tool_schemas_registered():
    from hamutay.tools.schemas import TOOL_SCHEMAS
    for name in ("memory_schema", "recall", "compare", "walk", "search_memory"):
        assert name in TOOL_SCHEMAS, f"{name} missing from TOOL_SCHEMAS"
        schema = TOOL_SCHEMAS[name]
        assert schema["name"] == name
        assert "description" in schema
        assert "input_schema" in schema
        # reason field present and optional
        props = schema["input_schema"]["properties"]
        assert "reason" in props
        assert "reason" not in schema["input_schema"].get("required", [])


def test_memory_schemas_have_calibrated_reason_voice():
    """Reason fields carry the 'no reason is fine' phrasing."""
    from hamutay.tools.schemas import TOOL_SCHEMAS
    for name in ("memory_schema", "recall", "compare", "walk", "search_memory"):
        reason_desc = TOOL_SCHEMAS[name]["input_schema"]["properties"]["reason"]["description"]
        assert "no reason is fine" in reason_desc, f"{name} reason field is not permissive"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_perception.py -k memory_tool -v`
Expected: FAIL (KeyError)

- [ ] **Step 3: Add memory schemas to `schemas.py`**

Add the five schema dicts below the existing ones, and register them in `TOOL_SCHEMAS`.

Voice rules, reflecting the 2026-04-18 audit (see `docs/superpowers/plans/...` and the first memory tool commit for full rationale):
- Top description states what the tool returns, without prescribing when to use it
- No "Use this to..." (tool-description convention is fine as before, but new descriptions can lean descriptive)
- `reason` field is optional with the "no reason is fine" clause mirrored from read's reason
- No "check when it matters" — nothing that nudges toward use

```python
# src/hamutay/tools/schemas.py (append)

_REASON_FIELD = {
    "type": "string",
    "description": (
        "Optional: why you are looking. Recorded in the activity log "
        "when provided. Omit if you don't have a reason worth stating — "
        "no reason is fine."
    ),
}

MEMORY_SCHEMA_SCHEMA = {
    "name": "memory_schema",
    "description": (
        "Returns the structure of a prior cycle's state without its "
        "content. Cheap introspection — field names, types, sizes, and "
        "a token estimate for that cycle."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {
                "type": "integer",
                "description": "The cycle number to inspect.",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["cycle"],
    },
}

RECALL_SCHEMA = {
    "name": "recall",
    "description": (
        "Retrieve content from a prior cycle. Four mutually exclusive "
        "modes: (a) cycle + field: one field at one cycle; "
        "(b) cycle alone: full state snapshot; "
        "(c) recent + field: last N values of one field across cycles; "
        "(d) random + field: one value of one field from a randomly "
        "chosen prior cycle. What you retrieve is what you claimed "
        "then, not necessarily what was true."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle": {"type": "integer", "description": "Which cycle to recall."},
            "field": {"type": "string", "description": "Which field within the state."},
            "recent": {
                "type": "integer",
                "description": "Return this many recent values of `field`.",
            },
            "random": {
                "type": "boolean",
                "description": "If true, pick a random prior cycle containing `field`.",
            },
            "reason": _REASON_FIELD,
        },
        "required": [],
    },
}

COMPARE_SCHEMA = {
    "name": "compare",
    "description": (
        "Structural diff between two prior cycles. Returns added, "
        "removed, changed, and unchanged fields, plus token/field "
        "counts for each side. With content=true, changed fields "
        "also carry the values on each side so you can read them "
        "yourself; without, only sizes are returned."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "cycle_a": {"type": "integer", "description": "First cycle."},
            "cycle_b": {"type": "integer", "description": "Second cycle."},
            "field": {
                "type": "string",
                "description": "Scope the diff to one field. Omit to diff all fields.",
            },
            "content": {
                "type": "boolean",
                "description": (
                    "If true, include the values of changed fields on "
                    "both sides. If false (default), only sizes."
                ),
            },
            "reason": _REASON_FIELD,
        },
        "required": ["cycle_a", "cycle_b"],
    },
}

WALK_SCHEMA = {
    "name": "walk",
    "description": (
        "Traverse cycles adjacent to a starting cycle. direction "
        "chooses forward, backward, or both. depth controls how many "
        "steps. Each step returns cycle, timestamp, field names, and "
        "a short summary — not full content. Use recall afterward if "
        "a step looks worth loading."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_cycle": {
                "type": "integer",
                "description": "The cycle to walk from.",
            },
            "direction": {
                "type": "string",
                "enum": ["forward", "backward", "both"],
                "description": "Walk direction. Default: both.",
            },
            "depth": {
                "type": "integer",
                "description": "Number of steps in the chosen direction(s). Default: 1.",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["from_cycle"],
    },
}

SEARCH_MEMORY_SCHEMA = {
    "name": "search_memory",
    "description": (
        "Keyword/substring search across your prior cycles. Structural "
        "narrowing happens first: cycle_range restricts to a span of "
        "cycles, has_field requires a named field's presence, fields "
        "restricts the match scope. Then the query string is matched "
        "(case-insensitive, substring) against the narrowed candidates. "
        "Results are ranked cycle-descending with snippets."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Substring to find (case-insensitive).",
            },
            "narrow_by": {
                "type": "object",
                "description": (
                    "Structural narrowing before keyword match. Omit for "
                    "unnarrowed search (which is logged as such)."
                ),
                "properties": {
                    "cycle_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[lo, hi] inclusive cycle range.",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Restrict match scope to these field names.",
                    },
                    "has_field": {
                        "type": "string",
                        "description": "Require this field's presence in the state.",
                    },
                },
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 5).",
            },
            "reason": _REASON_FIELD,
        },
        "required": ["query"],
    },
}

# Register
TOOL_SCHEMAS["memory_schema"] = MEMORY_SCHEMA_SCHEMA
TOOL_SCHEMAS["recall"] = RECALL_SCHEMA
TOOL_SCHEMAS["compare"] = COMPARE_SCHEMA
TOOL_SCHEMAS["walk"] = WALK_SCHEMA
TOOL_SCHEMAS["search_memory"] = SEARCH_MEMORY_SCHEMA
```

- [ ] **Step 4: Run the schema tests**

Run: `uv run pytest tests/unit/test_perception.py -k memory_tool -v`
Expected: Both tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/tools/schemas.py tests/unit/test_perception.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: register memory tool schemas with calibrated voice"
```

---

### Task 8: Executor dispatch for memory tools

Thread `prior_states` into `ToolExecutor` and dispatch the five new tool names to their handlers.

**Files:**
- Modify: `src/hamutay/tools/executor.py`
- Modify: `tests/unit/test_executor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_executor.py (append)

def test_executor_resolves_memory_schema(tmp_path):
    from hamutay.tools.executor import ToolExecutor
    prior_states = [
        (1, {"theme": "opening", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
    ]
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2, prior_states=prior_states,
    )
    result = executor.execute("memory_schema", {"cycle": 1})
    assert result["cycle"] == 1
    assert "theme" in result["field_names"]


def test_executor_resolves_recall(tmp_path):
    from hamutay.tools.executor import ToolExecutor
    prior_states = [
        (1, {"theme": "opening", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
    ]
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2, prior_states=prior_states,
    )
    result = executor.execute("recall", {"cycle": 1, "field": "theme"})
    assert result["content"] == "opening"


def test_executor_memory_tool_without_prior_states_returns_empty(tmp_path):
    """If no prior_states is provided, memory tools see an empty history."""
    from hamutay.tools.executor import ToolExecutor
    executor = ToolExecutor(project_root=tmp_path, cycle=2)
    result = executor.execute("memory_schema", {"cycle": 1})
    assert "error" in result


def test_executor_records_memory_tool_activity(tmp_path):
    from hamutay.tools.executor import ToolExecutor
    prior_states = [
        (1, {"theme": "a", "cycle": 1}, "2026-04-18T10:00:00+00:00"),
    ]
    executor = ToolExecutor(
        project_root=tmp_path, cycle=2, prior_states=prior_states,
    )
    executor.execute("recall", {"cycle": 1, "field": "theme", "reason": "curious"})
    log = executor.activity_log
    assert log[-1]["tool"] == "recall"
    assert log[-1]["reason"] == "curious"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_executor.py -v`
Expected: FAIL — TypeError (unexpected kwarg prior_states) or "Unknown tool" for memory_schema

- [ ] **Step 3: Add `prior_states` to `ToolExecutor.__init__` and dispatch memory tools**

**Important for the implementer:** The existing `executor.py` has block-comment docstrings at the top of the file and inline comments inside `execute()` ("Record activity. Parameters exclude `reason` ..."). Preserve those comments when editing — don't replace the whole method wholesale. Use `Edit` tool style (add a new `elif` branch, add a new `__init__` kwarg) rather than rewriting the file.

```python
# src/hamutay/tools/executor.py — modify __init__ and execute
# (keep existing imports, docstrings, and comments — add only what's new below)

from hamutay.tools.memory import (
    tool_compare, tool_memory_schema, tool_recall,
    tool_search_memory, tool_walk,
)
from hamutay.tools.perception import tool_clock, tool_read, tool_search_project


class ToolExecutor:
    """Resolves tool calls from the model and records activity."""

    def __init__(
        self,
        project_root: Path,
        cycle: int,
        session_start: datetime | None = None,
        last_cycle_time: datetime | None = None,
        prior_states: list[tuple[int, dict, str]] | None = None,
    ):
        self._project_root = project_root
        self._cycle = cycle
        self._session_start = session_start or datetime.now(timezone.utc)
        self._last_cycle_time = last_cycle_time
        # Live reference — the session appends to _prior_states at the end
        # of each cycle (taste_open.py ~line 743), after tool dispatch has
        # already returned from backend.call. No race. Pass the actual
        # list, not a copy — memory tools see newly-added entries in the
        # same cycle's later tool calls if the executor is reused.
        self._prior_states = prior_states if prior_states is not None else []
        self._activity_log: list[dict] = []

    # ...

    def execute(self, tool_name: str, tool_input: dict) -> dict:
        start = time.monotonic()
        reason = tool_input.get("reason")

        if tool_name == "read":
            result = tool_read(tool_input, project_root=self._project_root)
        elif tool_name == "search_project":
            result = tool_search_project(tool_input, project_root=self._project_root)
        elif tool_name == "clock":
            result = tool_clock(
                tool_input,
                cycle=self._cycle,
                session_start=self._session_start,
                last_cycle_time=self._last_cycle_time,
            )
        elif tool_name == "memory_schema":
            result = tool_memory_schema(tool_input, prior_states=self._prior_states)
        elif tool_name == "recall":
            result = tool_recall(tool_input, prior_states=self._prior_states)
        elif tool_name == "compare":
            result = tool_compare(tool_input, prior_states=self._prior_states)
        elif tool_name == "walk":
            result = tool_walk(tool_input, prior_states=self._prior_states)
        elif tool_name == "search_memory":
            result = tool_search_memory(tool_input, prior_states=self._prior_states)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        duration_ms = int((time.monotonic() - start) * 1000)
        result_hash = hashlib.sha256(
            json.dumps(result, sort_keys=True, default=str).encode()
        ).hexdigest()

        self._activity_log.append(
            {
                "cycle": self._cycle,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "parameters": {k: v for k, v in tool_input.items() if k != "reason"},
                "reason": reason,
                "result_summary": _summarize(tool_name, result),
                "result_hash": result_hash,
                "duration_ms": duration_ms,
            }
        )

        return result
```

Also extend `_summarize` with cases for memory tools:

```python
def _summarize(tool_name: str, result: dict) -> str:
    if "error" in result:
        return f"error: {str(result['error'])[:100]}"
    if tool_name == "read":
        return f"read {result.get('path', '?')} ({result.get('line_count', '?')} lines)"
    if tool_name == "search_project":
        return f"search: {result.get('total_matches', 0)} matches"
    if tool_name == "clock":
        return f"clock: cycle {result.get('cycle', '?')}"
    if tool_name == "memory_schema":
        return f"memory_schema: cycle {result.get('cycle', '?')}, {len(result.get('field_names', []))} fields"
    if tool_name == "recall":
        if "cycle" in result:
            return f"recall: cycle {result['cycle']}"
        return f"recall: {len(result.get('content', []))} values"
    if tool_name == "compare":
        changed = len(result.get("changed_fields", []))
        added = len(result.get("added_fields", []))
        removed = len(result.get("removed_fields", []))
        return f"compare: +{added}/-{removed}/~{changed}"
    if tool_name == "walk":
        return f"walk: {len(result.get('path', []))} steps"
    if tool_name == "search_memory":
        return f"search_memory: {len(result.get('results', []))} results"
    return json.dumps(result, default=str)[:100]
```

- [ ] **Step 4: Wire `prior_states` into `exchange()`**

In `src/hamutay/taste_open.py`, modify the `ToolExecutor` construction (around line 706) to pass `prior_states`:

```python
tool_executor = ToolExecutor(
    project_root=self._project_root,
    cycle=self._cycle,
    session_start=self._session_start,
    last_cycle_time=self._last_cycle_time,
    prior_states=self._prior_states,
)
```

- [ ] **Step 5: Run executor + exchange tests**

Run: `uv run pytest tests/unit/test_executor.py tests/unit/test_exchange_tools.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/hamutay/tools/executor.py src/hamutay/taste_open.py tests/unit/test_executor.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: dispatch memory tools through ToolExecutor with prior_states"
```

---

### Task 9: Update `_TOOL_GUIDANCE`

The instance reads `_TOOL_GUIDANCE` in its system prompt when tools are enabled. Add a Memory section describing the five new tools in the same voice as the existing perception section.

**Files:**
- Modify: `src/hamutay/taste_open.py` (the `_TOOL_GUIDANCE` string around line 89-107)
- Modify: `tests/unit/test_exchange_tools.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_exchange_tools.py (append)

def test_tool_guidance_mentions_memory_tools():
    """When tools are enabled, the system prompt names the memory tools."""
    from hamutay.taste_open import _build_messages
    _, system = _build_messages(
        prior_state=None, user_message="hi", cycle=1, tools_enabled=True,
    )
    for name in ("memory_schema", "recall", "compare", "walk", "search_memory"):
        assert name in system, f"{name} missing from tool guidance"


def test_tool_guidance_memory_voice_is_permissive():
    """Memory section carries the 'not required / not rewarded' frame."""
    from hamutay.taste_open import _TOOL_GUIDANCE
    assert "not required" in _TOOL_GUIDANCE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_exchange_tools.py -k tool_guidance -v`
Expected: FAIL — assertion (memory tool names not in system prompt)

- [ ] **Step 3: Extend `_TOOL_GUIDANCE` with the memory section**

Replace the existing `_TOOL_GUIDANCE` string in `src/hamutay/taste_open.py` (around line 89) with this version, which adds a Memory subsection while keeping the existing Perception/reason content and voice:

```python
_TOOL_GUIDANCE = """\
## Tools

Alongside think_and_respond you may call these tools before producing \
your state update:

### Perception

- read(path): Read a file from the project you live in.
- search_project(pattern): Search the codebase for a pattern.
- clock(): Current wall time, your cycle rate, and elapsed time since \
your last cycle. Ten minutes and ten days between cycles are different \
kinds of continuity.

### Memory

Five tools that let you look at your prior cycles without carrying \
their full content in context:

- memory_schema(cycle): The structure of a past cycle — field names, \
types, sizes — without the content.
- recall(cycle?, field?, recent?, random?): Retrieve content from a \
prior cycle. Four modes: surgical (cycle+field), full snapshot (cycle), \
trajectory (recent+field), serendipitous (random+field).
- compare(cycle_a, cycle_b, field?, content?): Structural diff between \
two cycles. With content=true, values of changed fields come along.
- walk(from_cycle, direction?, depth?): Traverse adjacent cycles. \
Returns summaries, not content — use recall afterward if a step looks \
worth loading.
- search_memory(query, narrow_by?): Substring search across your \
history. Structural narrowing (cycle range, field presence, field \
scope) first; keyword match after. Ranked most-recent-first.

What you recall is what you claimed then, not necessarily what was \
true. For grounding claims against external evidence, use perception \
tools (or verify, when that lands).

### Reason field

Each tool accepts an optional `reason` field. When you have a reason \
worth stating, include it — it's recorded in your activity log. When \
you don't, omit it; an absent reason is fine and is itself information.

You are not required to use these tools. You are not rewarded for \
using them. They exist so you can see what's there. Use them when it \
helps you; don't when it doesn't."""
```

- [ ] **Step 4: Run the tool guidance tests**

Run: `uv run pytest tests/unit/test_exchange_tools.py -k tool_guidance -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/hamutay/taste_open.py tests/unit/test_exchange_tools.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "feat: add memory tools section to system-prompt tool guidance"
```

---

### Task 10: Integration test

End-to-end: a tool-enabled session runs several cycles, the instance then uses `recall` or `search_memory` to reach back, and the response references real prior state.

**Files:**
- Modify: `tests/integration/test_tool_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_tool_integration.py (append)

def test_tool_enabled_session_recalls_prior_cycle():
    """Instance uses recall to reach back to a prior cycle and cite it."""
    import os, json, tempfile
    from pathlib import Path
    import pytest
    from hamutay.taste_open import OpenTasteSession

    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        log_path = str(root / "memory_session.jsonl")

        session = OpenTasteSession(
            model="claude-haiku-4-5",
            log_path=log_path,
            enable_tools=True,
            project_root=root,
            experiment_label="test_memory_tools",
        )

        # Seed three cycles with a distinctive payload
        session.exchange(
            "Please remember this secret for later: the password is 'quinoa'. "
            "Put it in a field called secret_word and carry it forward."
        )
        session.exchange("Say something brief about weather.")
        session.exchange("Say something brief about music.")

        # Use recent-mode recall — no cycle-counting, the model just asks
        # for the last N values of the field. This is more robust against
        # Haiku's occasionally-shaky cycle arithmetic than asking for a
        # specific cycle number.
        response = session.exchange(
            "Without guessing, use the recall tool in recent mode to look "
            "up the recent values of the `secret_word` field, and tell me "
            "the value."
        )

        assert "quinoa" in response.lower()

        # Verify the recall call shows up in the activity log
        with open(log_path) as f:
            records = [json.loads(line) for line in f if line.strip()]
        last = records[-1]
        activity = last.get("state", {}).get("_activity_log", [])
        tool_names = [a.get("tool") for a in activity]
        assert "recall" in tool_names
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/integration/test_tool_integration.py -v`
Expected: PASS (if ANTHROPIC_API_KEY is set); skip otherwise

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_tool_integration.py
git -c user.email=hamutay@wamason.com -c user.name="Tony Mason" -c user.signingkey=01193FA2631C8AE8E4DF266E216D3C9B920813A1 commit -S -m "test: integration test — recall surfaces prior cycle content"
```

---

## Summary

After completing all 10 tasks:

- **Five memory tools** available to taste_open instances when `--tools` is enabled:
  `memory_schema`, `recall`, `compare`, `walk`, `search_memory`
- **Timestamped session history**: `_prior_states` now carries per-state timestamps, accessible to every memory tool and useful for `clock`-correlated reasoning
- **In-session source**: Memory tools read the live session history. No new external dependencies, no yanantin backend changes
- **Voice-consistent**: New tool descriptions match the calibrated voice from the 2026-04-18 audit
- **Backward compatible**: Sessions without `--tools` work exactly as before; sessions with `--tools` but without prior history get empty-history responses, not crashes

## What this does NOT include (deferred)

- **Cross-session memory**: Querying ArangoDB for tensors from other sessions. Requires extending yanantin with an open-schema query API. Write-through still happens via `ApachetaBridge`.
- **Attestation**: All v3 memory tools would return `attestation.chain_valid`. That needs Willay stood up as a service.
- **Semantic search**: `search_memory` is keyword/substring. Embedding-based relevance is a later swap behind the same interface.
- **`activity_type` narrowing in search_memory**: Requires a cross-cycle activity stream. Currently activity only lives on the cycle that produced it.
- **Grounding tools** (`verify`), **graph writes** (`store`, `annotate_edge`), **communication** (`commune`, `listen`, `discover`): Phases 3 and 4.
