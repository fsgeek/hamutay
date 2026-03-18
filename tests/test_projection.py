"""Tests for the projection engine (Phase 1-2)."""

from __future__ import annotations

import copy
import json
import pytest

from hamutay.projection import ProjectionEngine
from hamutay.projection.regions import (
    RegionID,
    RegionState,
    TensorEntry,
    PageTableEntry,
)
from hamutay.projection.packing import (
    pack_regions,
    _build_tensor_pair,
    _build_page_table_xml,
)
from hamutay.projection.cache import (
    CacheState,
    strip_all_cache_controls,
    place_breakpoints,
)
from hamutay.projection.layout import (
    estimate_tokens,
    compute_ephemeral_budget,
    trim_ephemeral_to_budget,
)
from hamutay.projection.idle import IdleState


# ── Region data model ─────────────────────────────────────────────────

class TestRegionID:
    def test_ordering(self):
        assert RegionID.TOOLS < RegionID.SYSTEM < RegionID.DURABLE < RegionID.EPHEMERAL < RegionID.ANCHOR

    def test_values(self):
        assert RegionID.TOOLS == 0
        assert RegionID.ANCHOR == 4


class TestTensorEntry:
    def test_creation(self):
        t = TensorEntry(
            handle="abc12345",
            tensor_text="Summary of content",
            source_tool_use_id="tu_123",
            source_tool_name="Read",
            source_label="test.py",
        )
        assert t.frozen is True
        assert t.handle == "abc12345"


class TestPageTableEntry:
    def test_defaults(self):
        e = PageTableEntry(
            handle="abc12345",
            kind="file",
            label="test.py",
            status="present",
            region=3,
            size_tokens=100,
        )
        assert e.fault_count == 0
        assert e.age_turns == 0


# ── Packing ───────────────────────────────────────────────────────────

class TestPacking:
    def test_tensor_pair_structure(self):
        t = TensorEntry(
            handle="abc12345",
            tensor_text="Summary here",
            source_tool_use_id="tu_1",
            source_tool_name="Read",
            source_label="f.py",
        )
        user, asst = _build_tensor_pair(t)
        assert user["role"] == "user"
        assert asst["role"] == "assistant"
        assert "abc12345" in user["content"][0]["text"]
        assert "abc12345" in asst["content"][0]["text"]

    def test_page_table_xml_empty(self):
        xml = _build_page_table_xml([])
        assert 'count="0"' in xml

    def test_page_table_xml_entries(self):
        entries = [
            PageTableEntry("aaa", "file", "test.py", "present", 3, 100),
            PageTableEntry("bbb", "tensor", "summary", "available", 2, 50),
        ]
        xml = _build_page_table_xml(entries)
        assert 'count="2"' in xml
        assert 'handle="aaa"' in xml
        assert 'handle="bbb"' in xml

    def test_pack_empty_durable(self):
        """With no tensors, only ephemeral messages appear."""
        state = RegionState()
        system_blocks = [{"type": "text", "text": "system prompt"}]
        ephemeral = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

        sys_out, msgs_out = pack_regions(
            system_blocks=system_blocks,
            durable_state=state,
            ephemeral_messages=ephemeral,
        )

        assert sys_out == system_blocks
        assert len(msgs_out) == 2
        assert msgs_out[0]["role"] == "user"
        assert msgs_out[1]["role"] == "assistant"

    def test_pack_with_tensors(self):
        """Tensors produce pairs before ephemeral messages."""
        state = RegionState()
        state.tensors["abc"] = TensorEntry(
            "abc", "tensor content", "tu_1", "Read", "f.py"
        )
        ephemeral = [
            {"role": "user", "content": "hello"},
        ]

        _, msgs = pack_regions(
            system_blocks=[],
            durable_state=state,
            ephemeral_messages=ephemeral,
        )

        # 2 (tensor pair) + 2 (page table pair) + 1 (ephemeral) = 5
        assert len(msgs) == 5
        assert msgs[0]["role"] == "user"  # tensor user
        assert msgs[1]["role"] == "assistant"  # tensor asst
        assert msgs[2]["role"] == "user"  # page table user
        assert msgs[3]["role"] == "assistant"  # page table asst
        assert msgs[4]["role"] == "user"  # ephemeral

    def test_pack_alternation(self):
        """All packed messages must alternate user/assistant."""
        state = RegionState()
        state.tensors["a"] = TensorEntry("a", "t1", "tu_1", "Read", "a.py")
        state.tensors["b"] = TensorEntry("b", "t2", "tu_2", "Read", "b.py")
        ephemeral = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
        ]

        _, msgs = pack_regions(
            system_blocks=[],
            durable_state=state,
            ephemeral_messages=ephemeral,
        )

        for i in range(len(msgs)):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert msgs[i]["role"] == expected_role, (
                f"Message {i} has role {msgs[i]['role']}, expected {expected_role}"
            )

    def test_anchor_appended_to_last_user(self):
        """Anchor text should be appended to the last user message."""
        state = RegionState()
        ephemeral = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "question"},
        ]

        _, msgs = pack_regions(
            system_blocks=[],
            durable_state=state,
            ephemeral_messages=ephemeral,
            anchor_text="\n[test-anchor]",
        )

        last_user = msgs[-1]
        assert last_user["role"] == "user"
        assert "question" in last_user["content"]
        assert "[test-anchor]" in last_user["content"]


# ── Cache breakpoints ─────────────────────────────────────────────────

class TestCacheBreakpoints:
    def test_strip_all(self):
        payload = {
            "system": [
                {"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}},
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}},
                    ],
                },
            ],
        }
        strip_all_cache_controls(payload)
        assert "cache_control" not in payload["system"][0]
        assert "cache_control" not in payload["messages"][0]["content"][0]

    def test_bp_system_only(self):
        """Single message — only system BP."""
        payload = {
            "system": [{"type": "text", "text": "system"}],
            "messages": [{"role": "user", "content": "hi"}],
        }
        count = place_breakpoints(payload)
        assert count == 1
        assert "cache_control" in payload["system"][0]

    def test_bp_system_and_second_to_last(self):
        """Multiple messages — system BP + second-to-last."""
        payload = {
            "system": [{"type": "text", "text": "system"}],
            "messages": [
                {"role": "user", "content": "q1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "q2"},
            ],
        }
        count = place_breakpoints(payload)
        assert count == 2

    def test_bp_with_tensors(self):
        """With frozen tensors — system + frozen boundary + second-to-last."""
        payload = {
            "system": [{"type": "text", "text": "system"}],
            "messages": [
                # 2 tensor pairs (4 messages)
                {"role": "user", "content": "tensor 1"},
                {"role": "assistant", "content": "loaded 1"},
                {"role": "user", "content": "tensor 2"},
                {"role": "assistant", "content": "loaded 2"},
                # page table pair
                {"role": "user", "content": "page table"},
                {"role": "assistant", "content": "ack"},
                # ephemeral
                {"role": "user", "content": "q1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "q2"},
            ],
        }
        count = place_breakpoints(
            payload, frozen_tensor_count=2, has_page_table=True
        )
        # BP1 (system) + BP2 (end of frozen) + BP3 (end of page table) + BP4 (second-to-last)
        assert count == 4
        # Verify positions
        assert "cache_control" in payload["system"][0]
        # BP2: message[3] (last frozen assistant)
        assert "cache_control" in payload["messages"][3]["content"][0]
        # BP3: message[5] (page table ack)
        assert "cache_control" in payload["messages"][5]["content"][0]
        # BP4: message[7] (second-to-last)
        assert "cache_control" in payload["messages"][7]["content"][0]

    def test_max_4_breakpoints(self):
        """Never exceed 4 cache_control markers total."""
        payload = {
            "system": [{"type": "text", "text": "system"}],
            "messages": [
                {"role": "user", "content": "t1"},
                {"role": "assistant", "content": "l1"},
                {"role": "user", "content": "pt"},
                {"role": "assistant", "content": "ack"},
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "a"},
                {"role": "user", "content": "q2"},
            ],
        }
        count = place_breakpoints(
            payload, frozen_tensor_count=1, has_page_table=True
        )
        assert count <= 4


class TestCacheState:
    def test_hit_rate(self):
        cs = CacheState()
        cs.cache_read_tokens = 80
        cs.cache_creation_tokens = 20
        assert cs.hit_rate == 0.8

    def test_hit_rate_zero(self):
        cs = CacheState()
        assert cs.hit_rate == 0.0

    def test_update_from_usage(self):
        cs = CacheState()
        cs.update_from_usage({
            "cache_read_input_tokens": 5000,
            "cache_creation_input_tokens": 1000,
        })
        assert cs.cache_read_tokens == 5000
        assert cs.cache_creation_tokens == 1000


# ── Layout / budget ───────────────────────────────────────────────────

class TestLayout:
    def test_estimate_tokens(self):
        # Should produce a reasonable estimate
        text = "hello world" * 100
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # tokens < bytes

    def test_budget_calculation(self):
        budget = compute_ephemeral_budget(
            window_size=200_000,
            system_tokens=10_000,
            tools_tokens=5_000,
            durable_tokens=20_000,
        )
        # 200K - 10K - 5K - 20K - 2K (anchor) - 8K (output) = 155K
        assert budget == 155_000

    def test_budget_floor(self):
        budget = compute_ephemeral_budget(
            window_size=10_000,
            system_tokens=5_000,
            tools_tokens=5_000,
            durable_tokens=5_000,
        )
        assert budget == 0  # can't go negative

    def test_trim_no_change(self):
        msgs = [{"role": "user", "content": "hi"}]
        result = trim_ephemeral_to_budget(msgs, 100_000)
        assert len(result) == 1

    def test_trim_drops_oldest(self):
        msgs = [
            {"role": "user", "content": "x" * 10000},
            {"role": "assistant", "content": "y" * 10000},
            {"role": "user", "content": "z"},
        ]
        result = trim_ephemeral_to_budget(msgs, 100)
        # Should keep at least the last message
        assert len(result) >= 1
        assert result[-1]["content"] == "z"

    def test_trim_preserves_last(self):
        msgs = [{"role": "user", "content": "x" * 100000}]
        result = trim_ephemeral_to_budget(msgs, 1)
        assert len(result) == 1  # never drops last


# ── ProjectionEngine ──────────────────────────────────────────────────

class TestProjectionEngine:
    def _make_payload(self, msg_count=3):
        messages = []
        for i in range(msg_count):
            if i % 2 == 0:
                messages.append({"role": "user", "content": f"question {i}"})
            else:
                messages.append({"role": "assistant", "content": f"answer {i}"})
        return {
            "system": "You are helpful.",
            "messages": messages,
        }

    def test_ingest_tracking(self):
        engine = ProjectionEngine("test")
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        stats = engine.ingest(msgs)
        assert stats["new_count"] == 2
        assert stats["mutations"] == 0
        assert stats["deletions"] == 0

    def test_ingest_detects_new(self):
        engine = ProjectionEngine("test")
        engine.ingest([{"role": "user", "content": "hello"}])
        stats = engine.ingest([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "followup"},
        ])
        assert stats["new_count"] == 2

    def test_ingest_detects_deletion(self):
        engine = ProjectionEngine("test")
        engine.ingest([
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
        ])
        stats = engine.ingest([
            {"role": "user", "content": "a"},
        ])
        assert stats["deletions"] == 2

    def test_project_basic(self):
        engine = ProjectionEngine("test")
        payload = self._make_payload()
        token_state = {"last_effective": 5000}

        result = engine.project(
            payload,
            token_state=token_state,
            token_cap=0,
        )

        # Should have system as list
        assert isinstance(result["system"], list)
        # Should have messages
        assert len(result["messages"]) > 0
        # System should contain pichay marker
        sys_text = json.dumps(result["system"])
        assert "pichay" in sys_text.lower()

    def test_project_cache_breakpoints(self):
        engine = ProjectionEngine("test")
        payload = self._make_payload(msg_count=5)
        token_state = {"last_effective": 10000}

        result = engine.project(
            payload,
            token_state=token_state,
        )

        # Should have at least 1 breakpoint (system)
        system_bps = sum(
            1 for b in result["system"]
            if isinstance(b, dict) and "cache_control" in b
        )
        assert system_bps >= 1

    def test_project_preserves_tools(self):
        engine = ProjectionEngine("test")
        tools = [{"name": "test_tool", "description": "test"}]
        payload = {
            "system": "test",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": tools,
        }
        token_state = {"last_effective": 1000}

        result = engine.project(payload, token_state=token_state)
        assert result["tools"] == tools

    def test_project_alternation_valid(self):
        """Projected messages must alternate user/assistant."""
        engine = ProjectionEngine("test")
        payload = self._make_payload(msg_count=7)
        token_state = {"last_effective": 10000}

        result = engine.project(payload, token_state=token_state)

        messages = result["messages"]
        for i in range(len(messages)):
            expected = "user" if i % 2 == 0 else "assistant"
            assert messages[i]["role"] == expected, (
                f"Message {i}: expected {expected}, got {messages[i]['role']}"
            )

    def test_cache_state_tracking(self):
        engine = ProjectionEngine("test")
        engine.update_cache_state({
            "cache_read_input_tokens": 8000,
            "cache_creation_input_tokens": 2000,
        })
        assert engine.cache_state.hit_rate == 0.8

    def test_project_with_tensors(self):
        """When tensors exist, they appear as frozen pairs before ephemeral."""
        engine = ProjectionEngine("test")
        # Manually add a tensor
        engine.region_state.tensors["abc12345"] = TensorEntry(
            handle="abc12345",
            tensor_text="Summary of important file",
            source_tool_use_id="tu_1",
            source_tool_name="Read",
            source_label="important.py",
        )

        payload = self._make_payload(msg_count=3)
        token_state = {"last_effective": 10000}
        result = engine.project(payload, token_state=token_state)

        messages = result["messages"]
        # Should have: 2 (tensor pair) + 2 (page table) + 3 (ephemeral) = 7
        assert len(messages) == 7
        # First pair should be the tensor
        assert "abc12345" in json.dumps(messages[0])
        # Page table pair
        assert "page-table" in json.dumps(messages[2]).lower() or "Page table" in json.dumps(messages[3])
        # Alternation still valid
        for i in range(len(messages)):
            expected = "user" if i % 2 == 0 else "assistant"
            assert messages[i]["role"] == expected

    def test_page_table_populated_from_tensors(self):
        """Page table should include entries for durable tensors."""
        engine = ProjectionEngine("test")
        engine.region_state.tensors["aaa"] = TensorEntry(
            "aaa", "content A", "tu_1", "Read", "a.py"
        )
        engine.region_state.tensors["bbb"] = TensorEntry(
            "bbb", "content B", "tu_2", "Grep", "grep results"
        )

        payload = self._make_payload()
        engine.project(payload, token_state={"last_effective": 5000})

        # Page table should have entries for both tensors
        assert len(engine.region_state.page_table) >= 2
        handles = {e.handle for e in engine.region_state.page_table}
        assert "aaa" in handles
        assert "bbb" in handles

    def test_idle_state_integration(self):
        """Engine should have idle state tracking."""
        engine = ProjectionEngine("test")
        assert hasattr(engine, "idle_state")
        assert isinstance(engine.idle_state, IdleState)


# ── Idle detection ────────────────────────────────────────────────────

class TestIdleState:
    def test_initial_state(self):
        idle = IdleState()
        assert idle.idle_seconds < 1.0  # just created
        assert not idle.cache_expired

    def test_not_idle_return_on_active(self):
        idle = IdleState()
        assert not idle.is_idle_return()

    def test_idle_return_after_ttl(self):
        idle = IdleState(cache_ttl=0.01)  # 10ms TTL for testing
        import time
        time.sleep(0.02)
        assert idle.is_idle_return()
        # Second call should NOT be idle (reset after first)
        assert not idle.is_idle_return()

    def test_waste_threshold(self):
        idle = IdleState(waste_threshold=10_000)
        assert not idle.should_restructure(5_000)
        assert idle.should_restructure(15_000)

    def test_touch_resets(self):
        idle = IdleState(cache_ttl=0.01)
        import time
        time.sleep(0.02)
        idle.touch()
        assert not idle.cache_expired


# ── Phantom tensor storage ────────────────────────────────────────────

class TestPhantomTensorStorage:
    def test_store_tensor_in_projector(self):
        from hamutay.phantom import _store_tensor_in_projector

        engine = ProjectionEngine("test")
        _store_tensor_in_projector(
            engine,
            "abc12345",
            {"content": "Summary of file", "declared_losses": "Line numbers lost"},
        )

        assert "abc12345" in engine.region_state.tensors
        tensor = engine.region_state.tensors["abc12345"]
        assert "Summary of file" in tensor.tensor_text
        assert "declared_losses" in tensor.tensor_text
        assert tensor.frozen is True

    def test_store_tensor_without_losses(self):
        from hamutay.phantom import _store_tensor_in_projector

        engine = ProjectionEngine("test")
        _store_tensor_in_projector(
            engine,
            "def67890",
            {"content": "Just a summary"},
        )

        tensor = engine.region_state.tensors["def67890"]
        assert tensor.tensor_text == "Just a summary"

    def test_qunqay_schema_has_tensor(self):
        from hamutay.phantom import PHANTOM_TOOL_DEFINITIONS

        qunqay = next(t for t in PHANTOM_TOOL_DEFINITIONS if t["name"] == "qunqay")
        props = qunqay["input_schema"]["properties"]
        assert "tensor" in props
        assert "content" in props["tensor"]["properties"]
        assert "declared_losses" in props["tensor"]["properties"]
