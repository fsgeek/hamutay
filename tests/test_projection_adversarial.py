"""Adversarial contract tests for the projection engine."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from hamutay.config import PagingPolicy
from hamutay.message_ops import PICHAY_STATUS_MARKER, get_system_prompt
from hamutay.phantom import PhantomCall, _handle_phantom_call
from hamutay.projection import ProjectionEngine
from hamutay.projection.cache import place_breakpoints
from hamutay.projection.idle import IdleState
from hamutay.projection.layout import trim_ephemeral_to_budget
from hamutay.projection.packing import _build_page_table_xml, pack_regions
from hamutay.projection.regions import PageTableEntry, RegionState, TensorEntry


def _msg_text(msg: dict) -> str:
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict)
        )
    return str(content)


def _assert_adjacent_roles_alternate(messages: list[dict]) -> None:
    assert messages
    for i in range(1, len(messages)):
        assert messages[i]["role"] != messages[i - 1]["role"]


class _FakePageStoreForProjection:
    def __init__(self):
        self._tensor_index = {
            "h_read": SimpleNamespace(
                tool_use_id="tu-read",
                tool_name="Read",
                label="src/app.py",
                original_size=4000,
            ),
            "h_released": SimpleNamespace(
                tool_use_id="tu-rel",
                tool_name="Read",
                label="old.py",
                original_size=2000,
            ),
            "h_tool": SimpleNamespace(
                tool_use_id="tu-tool",
                tool_name="Grep",
                label="grep output",
                original_size=1000,
            ),
        }
        self._released_handles = {"h_released"}
        self.faults = [
            SimpleNamespace(original_eviction=SimpleNamespace(tool_use_id="tu-read")),
            SimpleNamespace(original_eviction=SimpleNamespace(tool_use_id="tu-read")),
            SimpleNamespace(original_eviction=SimpleNamespace(tool_use_id="irrelevant")),
        ]
        self._released = set()
        self._eviction_index = {}


class _FakePageStoreForAnchor:
    def __init__(self):
        self._tensor_index = {
            "t1": SimpleNamespace(
                tool_name="Read",
                tool_input={"file_path": "docs/spec.md"},
                tool_use_id="tu1",
                summary="[tensor:t1 — docs/spec.md (1024 bytes)]",
                original_size=1024,
                evicted_at=0.0,
            )
        }
        self.faults = []
        self._released = set()
        self._released_handles = set()
        self._eviction_index = {}
        self.eviction_bytes_saved = 100
        self.gc_bytes_saved = 10


class _FakeBlockStore:
    def __init__(self, blocks):
        self._blocks = blocks
        self.block_count = 3

    def large_blocks(self, min_size: int):
        return self._blocks


class _FakePageStoreForQunqay:
    def __init__(self):
        self._found = {"found-handle"}
        self._released = []
        self._eviction_index = {}

    def mark_released(self, identifier: str) -> bool:
        if identifier in self._found:
            self._released.append(identifier)
            return True
        return False

    def resolve_tensor(self, handle: str):
        if handle == "found-handle":
            return SimpleNamespace(
                tool_use_id="tu-found",
                tool_name="Read",
                label="src/found.py",
            )
        return None


def test_project_budget_trims_oldest_and_keeps_latest_user_turn():
    engine = ProjectionEngine("adv-budget")
    policy = PagingPolicy(window_size=1000)

    messages = []
    for i in range(21):
        role = "user" if i % 2 == 0 else "assistant"
        text = f"m{i}-" + ("x" * 2500)
        if i == 20:
            text = "LAST-USER-SENTINEL"
        messages.append({"role": role, "content": text})

    payload = {"system": "sys", "messages": messages}
    out = engine.project(payload, token_state={"last_effective": 0}, policy=policy)

    assert len(out["messages"]) < len(messages)
    assert out["messages"][-1]["role"] == "user"
    assert "LAST-USER-SENTINEL" in _msg_text(out["messages"][-1])
    _assert_adjacent_roles_alternate(out["messages"])


def test_project_system_marker_block_is_replaced_not_duplicated():
    engine = ProjectionEngine("adv-system-replace")
    payload = {
        "system": [
            {"type": "text", "text": "keep this"},
            {"type": "text", "text": f"stale {PICHAY_STATUS_MARKER} old"},
        ],
        "messages": [{"role": "user", "content": "hi"}],
    }

    out = engine.project(payload, token_state={"last_effective": 0})
    system_texts = [b.get("text", "") for b in out["system"] if isinstance(b, dict)]

    assert system_texts.count(get_system_prompt()) == 1
    assert sum(PICHAY_STATUS_MARKER in t for t in system_texts) == 1


def test_project_system_marker_block_is_appended_when_absent():
    engine = ProjectionEngine("adv-system-append")
    payload = {
        "system": [{"type": "text", "text": "custom rules"}],
        "messages": [{"role": "user", "content": "hi"}],
    }

    out = engine.project(payload, token_state={"last_effective": 0})
    system_texts = [b.get("text", "") for b in out["system"] if isinstance(b, dict)]

    assert "custom rules" in system_texts
    assert system_texts.count(get_system_prompt()) == 1
    assert sum(PICHAY_STATUS_MARKER in t for t in system_texts) == 1


def test_project_page_table_integrates_page_store_and_filters_released_handles():
    engine = ProjectionEngine("adv-page-table")
    engine.region_state.tensors["durable-1"] = TensorEntry(
        handle="durable-1",
        tensor_text="durable tensor content",
        source_tool_use_id="tu-durable",
        source_tool_name="Read",
        source_label="durable.py",
    )

    page_store = _FakePageStoreForProjection()
    payload = {"system": "sys", "messages": [{"role": "user", "content": "hi"}]}
    engine.project(payload, token_state={"last_effective": 0}, page_store=page_store)

    by_handle = {e.handle: e for e in engine.region_state.page_table}

    assert "durable-1" in by_handle
    assert by_handle["durable-1"].kind == "tensor"
    assert by_handle["durable-1"].region == 2

    assert "h_read" in by_handle
    assert by_handle["h_read"].kind == "file"
    assert by_handle["h_read"].fault_count == 2

    assert "h_tool" in by_handle
    assert by_handle["h_tool"].kind == "tool_result"

    assert "h_released" not in by_handle


def test_project_anchor_not_injected_when_effective_tokens_non_positive():
    engine = ProjectionEngine("adv-anchor-none")
    payload = {"system": "sys", "messages": [{"role": "user", "content": "hi"}]}

    out = engine.project(payload, token_state={"last_effective": 0})

    assert "[pichay-live-status]" not in json.dumps(out["messages"])


def test_project_anchor_high_pressure_includes_yuyay_query_with_tensors():
    engine = ProjectionEngine("adv-anchor-high")
    page_store = _FakePageStoreForAnchor()
    block_store = _FakeBlockStore([])
    policy = PagingPolicy(
        window_size=1000,
        floor_tokens=0,
        advisory_tokens=100,
        involuntary_tokens=200,
        hard_cap_tokens=900,
    )
    payload = {"system": "sys", "messages": [{"role": "user", "content": "hi"}]}

    out = engine.project(
        payload,
        token_state={"last_effective": 250},
        page_store=page_store,
        block_store=block_store,
        policy=policy,
    )

    assert "<yuyay-query>" in _msg_text(out["messages"][-1])


def test_project_anchor_moderate_pressure_includes_block_inventory():
    engine = ProjectionEngine("adv-anchor-moderate")
    block = SimpleNamespace(
        block_id="block-42",
        role="assistant",
        turn=7,
        size=4096,
        preview="Preview text",
    )
    block_store = _FakeBlockStore([block])
    policy = PagingPolicy(
        window_size=1000,
        floor_tokens=0,
        advisory_tokens=100,
        involuntary_tokens=300,
        hard_cap_tokens=900,
    )
    payload = {"system": "sys", "messages": [{"role": "user", "content": "hi"}]}

    out = engine.project(
        payload,
        token_state={"last_effective": 150},
        block_store=block_store,
        policy=policy,
    )

    anchor_text = _msg_text(out["messages"][-1])
    assert "Largest blocks" in anchor_text
    assert "[block:block-42]" in anchor_text


def test_page_table_xml_escapes_label_attributes():
    entries = [
        PageTableEntry(
            handle="h1",
            kind="file",
            label='a&b<c>"d',
            status="available",
            region=3,
            size_tokens=10,
        )
    ]
    xml = _build_page_table_xml(entries)

    assert "a&amp;b&lt;c&gt;&quot;d" in xml


def test_breakpoints_tolerate_inconsistent_frozen_tensor_count_without_crash():
    payload = {
        "system": [{"type": "text", "text": "system"}],
        "messages": [
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": "a"},
        ],
    }

    count = place_breakpoints(payload, frozen_tensor_count=99, has_page_table=True)

    assert count == 1
    assert "cache_control" in payload["system"][-1]


def test_breakpoints_with_empty_messages_place_only_system_marker():
    payload = {
        "system": [{"type": "text", "text": "system"}],
        "messages": [],
    }
    count = place_breakpoints(payload)

    assert count == 1
    assert "cache_control" in payload["system"][-1]


def test_breakpoints_skip_bp4_when_it_would_collide_with_durable_boundaries():
    payload = {
        "system": [{"type": "text", "text": "system"}],
        "messages": [
            {"role": "user", "content": "t1"},
            {"role": "assistant", "content": "t1 ack"},
            {"role": "user", "content": "pt"},
            {"role": "assistant", "content": "pt ack"},
        ],
    }

    count = place_breakpoints(payload, frozen_tensor_count=1, has_page_table=True)

    assert count == 3
    assert "cache_control" in payload["messages"][1]["content"][0]
    assert "cache_control" in payload["messages"][3]["content"][0]
    assert "cache_control" not in payload["messages"][2].get("content", [{}])[0]


def test_trim_ephemeral_to_budget_does_not_mutate_input_messages_or_list():
    original = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
        {"role": "user", "content": "z"},
    ]
    snapshot = copy.deepcopy(original)

    trimmed = trim_ephemeral_to_budget(original, budget_tokens=1)

    assert original == snapshot
    assert trimmed is not original
    assert trimmed[-1]["content"] == "z"


def test_idle_state_idle_return_with_monkeypatched_monotonic(monkeypatch):
    import hamutay.projection.idle as idle_module

    now = {"t": 100.0}

    def fake_monotonic() -> float:
        return now["t"]

    monkeypatch.setattr(idle_module.time, "monotonic", fake_monotonic)

    idle = IdleState(cache_ttl=10.0)
    assert not idle.cache_expired

    now["t"] = 111.0
    assert idle.cache_expired
    assert idle.is_idle_return()

    now["t"] = 112.0
    assert not idle.is_idle_return()


def test_qunqay_handle_phantom_call_stores_tensor_only_for_found_handles():
    engine = ProjectionEngine("adv-qunqay")
    page_store = _FakePageStoreForQunqay()
    call = PhantomCall(
        name="qunqay",
        tool_use_id="toolu-1",
        input={
            "handles": ["found-handle", "missing-handle"],
            "reason": "free space",
            "tensor": {
                "content": "compressed meaning",
                "declared_losses": "line-level detail",
            },
        },
    )

    result_text = _handle_phantom_call(call, page_store=page_store, projector=engine)

    assert "found-handle" in engine.region_state.tensors
    assert "missing-handle" not in engine.region_state.tensors
    assert "Released 1 tensor(s): found-handle" in result_text
    assert "Not found: missing-handle" in result_text
    assert "Tensor stored in durable region" in result_text


def test_pack_regions_preserves_non_alternating_ephemeral_sequence_as_is():
    state = RegionState()
    ephemeral = [
        {"role": "assistant", "content": "assistant starts"},
        {"role": "user", "content": "user reply"},
        {"role": "assistant", "content": "assistant again"},
    ]

    _, msgs = pack_regions(
        system_blocks=[],
        durable_state=state,
        ephemeral_messages=ephemeral,
    )

    assert [m["role"] for m in msgs] == ["assistant", "user", "assistant"]


@pytest.mark.parametrize("system_input", ["", None, []])
def test_project_injects_pichay_for_empty_or_edge_system_inputs(system_input):
    engine = ProjectionEngine("adv-system-edge")
    payload = {
        "system": system_input,
        "messages": [{"role": "user", "content": "hello"}],
    }

    out = engine.project(payload, token_state={"last_effective": 0})
    system_texts = [b.get("text", "") for b in out["system"] if isinstance(b, dict)]

    assert system_texts.count(get_system_prompt()) == 1
    assert sum(PICHAY_STATUS_MARKER in t for t in system_texts) == 1
