"""Projection engine — transforms temporal message streams into cache-optimized layouts.

The projector replaces _preprocess() in the gateway. Instead of preserving
temporal message ordering (which mutates the KV cache prefix every turn),
it reorders content by stability:

  Region 0: Tools (session lifetime, implicit cache level)
  Region 1: System prompt (session lifetime)
  Region 2: Durable tensors + page table (append-only growth)
  Region 3: Ephemeral conversation turns (rewritten each turn)
  Region 4: Current turn + dynamic anchor (never cached)

Cache breakpoints sit at region boundaries. Stable content at the front,
volatile at the back.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from typing import Any

from hamutay.projection.regions import (
    RegionState,
)
from hamutay.projection.packing import pack_regions
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

_DIM = "\033[2m"
_RESET = "\033[0m"


def _fingerprint(msg: dict) -> str:
    """Stable fingerprint for a message (ported from MessageStore)."""
    role = msg.get("role", "")
    tool_use_id = msg.get("tool_use_id", "")
    if tool_use_id:
        return f"{role}:{tool_use_id}"
    content = msg.get("content", "")
    if isinstance(content, list):
        raw = json.dumps(content, sort_keys=True, default=str)[:512]
    else:
        raw = str(content)[:512]
    h = hashlib.sha256(f"{role}:{raw}".encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"{role}:{h}"


class ProjectionEngine:
    """Transforms a temporal message stream into a cache-optimized projection.

    Owns Region 2 (durable tensor store) state. Regions 0, 1, 3, 4 are
    derived from the incoming payload each turn.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.region_state = RegionState()
        self.cache_state = CacheState()
        self.idle_state = IdleState()
        self._turn = 0

        # Fingerprint tracking for mutation/deletion detection
        self._known_fps: list[str] = []
        self._ingest_stats: dict[str, int] = {}

    def ingest(self, incoming_messages: list[dict]) -> dict[str, int]:
        """Track temporal history, detect new/mutated/deleted messages.

        This is the fingerprinting port from MessageStore. It detects
        what the client changed since last turn so we can build the
        ephemeral region correctly.

        Returns stats dict with keys: new_count, mutations, deletions.
        """
        self._turn += 1
        stats = {"new_count": 0, "mutations": 0, "deletions": 0}

        known_count = len(self._known_fps)
        check_limit = min(known_count, len(incoming_messages))

        # Detect mutations in known messages
        for i in range(check_limit):
            fp = _fingerprint(incoming_messages[i])
            if fp != self._known_fps[i]:
                stats["mutations"] += 1
                self._known_fps[i] = fp

        # Detect client deletions
        if len(incoming_messages) < known_count:
            stats["deletions"] = known_count - len(incoming_messages)
            self._known_fps = self._known_fps[:len(incoming_messages)]

        # Track new messages
        new_start = min(known_count, len(incoming_messages))
        new_messages = incoming_messages[new_start:]
        stats["new_count"] = len(new_messages)

        for msg in new_messages:
            self._known_fps.append(_fingerprint(msg))

        self._ingest_stats = stats
        return stats

    def project(
        self,
        payload: dict,
        *,
        token_state: dict,
        page_store: Any = None,
        block_store: Any = None,
        policy: Any = None,
        last_cleanup_stats: str | None = None,
        token_cap: int = 0,
    ) -> dict:
        """Build the four-region projection from the incoming payload.

        Mutates payload in place (the ephemeral copy — never the physical store).
        Returns the modified payload dict.
        """
        # Check for idle return — free restructure window
        idle_return = self.idle_state.is_idle_return()
        if idle_return:
            print(
                f"  {_DIM}[{self.session_id}] idle return — restructure window{_RESET}",
                file=sys.stderr,
            )

        # Extract the pieces
        incoming_system = payload.get("system", "")
        incoming_messages = payload.get("messages", [])
        # tools pass through unchanged (Region 0) — no extraction needed

        # Normalize system to block list
        system_blocks = self._normalize_system(incoming_system)

        # Inject Pichay system prompt into system blocks (Region 1)
        system_blocks = self._inject_pichay_system(system_blocks)

        # Estimate region sizes for budget calculation
        system_tokens = estimate_tokens(system_blocks)
        tools_tokens = estimate_tokens(payload.get("tools") or [])
        durable_tokens = self._estimate_durable_tokens()

        # Get window size from policy
        window_size = 200_000  # default
        if policy is not None:
            window_size = getattr(policy, "window_size", window_size)
        else:
            from hamutay.config import get_policy
            window_size = get_policy().window_size

        # Compute ephemeral budget and trim if needed
        ephemeral_budget = compute_ephemeral_budget(
            window_size=window_size,
            system_tokens=system_tokens,
            tools_tokens=tools_tokens,
            durable_tokens=durable_tokens,
        )
        ephemeral_messages = trim_ephemeral_to_budget(
            copy.deepcopy(incoming_messages),
            ephemeral_budget,
        )

        # Build page table (Region 2 mutable)
        self._update_page_table(page_store)

        # Build dynamic anchor (Region 4)
        anchor_text = self._build_anchor(
            token_state=token_state,
            page_store=page_store,
            block_store=block_store,
            policy=policy,
            last_cleanup_stats=last_cleanup_stats,
            token_cap=token_cap,
        )

        # Pack all regions into (system, messages)
        system_out, messages_out = pack_regions(
            system_blocks=system_blocks,
            durable_state=self.region_state,
            ephemeral_messages=ephemeral_messages,
            anchor_text=anchor_text,
        )

        # Assemble the payload
        payload["system"] = system_out
        payload["messages"] = messages_out
        # tools pass through unchanged (Region 0)

        # Strip all existing cache controls, then place ours
        strip_all_cache_controls(payload)
        bp_count = place_breakpoints(
            payload,
            frozen_tensor_count=len([
                t for t in self.region_state.tensors.values() if t.frozen
            ]),
            has_page_table=bool(
                self.region_state.page_table or self.region_state.tensors
            ),
        )

        self.cache_state.last_breakpoint_count = bp_count

        # Log projection stats
        self._log_projection(system_out, messages_out, bp_count)

        return payload

    def update_cache_state(self, usage: dict[str, Any]) -> None:
        """Feed API response usage data back to track cache performance."""
        self.cache_state.update_from_usage(usage)

    # ── Internal helpers ──────────────────────────────────────────────

    def _estimate_durable_tokens(self) -> int:
        """Estimate tokens consumed by Region 2 (frozen tensors + page table)."""
        total = 0
        for tensor in self.region_state.tensors.values():
            # Each tensor becomes a user/assistant pair
            total += estimate_tokens(tensor.tensor_text) + 20  # overhead for pair structure
        if self.region_state.page_table or self.region_state.tensors:
            total += estimate_tokens(self.region_state.page_table) + 20  # page table pair
        return total

    def _update_page_table(self, page_store: Any) -> None:
        """Rebuild the page table from durable tensors and page_store state."""
        from hamutay.projection.regions import PageTableEntry

        entries: list[PageTableEntry] = []

        # Add entries for frozen tensors in Region 2
        for handle, tensor in self.region_state.tensors.items():
            entries.append(PageTableEntry(
                handle=handle,
                kind="tensor",
                label=tensor.source_label[:40],
                status="available",
                region=2,
                size_tokens=len(tensor.tensor_text) // 4,  # rough estimate
            ))

        # Add entries from page_store for evicted content (not yet tensored)
        if page_store is not None:
            released_handles = getattr(page_store, "_released_handles", set())
            for ps_handle, entry in page_store._tensor_index.items():
                # Skip if already in our tensor store
                if ps_handle in self.region_state.tensors:
                    continue
                # Skip released entries
                if ps_handle in released_handles:
                    continue
                fault_count = sum(
                    1 for f in page_store.faults
                    if f.original_eviction.tool_use_id == entry.tool_use_id
                )
                entries.append(PageTableEntry(
                    handle=ps_handle,
                    kind="file" if entry.tool_name == "Read" else "tool_result",
                    label=getattr(entry, "label", entry.tool_name)[:40],
                    status="available",
                    region=3,
                    size_tokens=entry.original_size // 4,
                    fault_count=fault_count,
                ))

        self.region_state.page_table = entries

    def _normalize_system(self, system: Any) -> list[dict[str, Any]]:
        """Normalize system prompt to a list of content blocks."""
        if isinstance(system, str):
            if system.strip():
                return [{"type": "text", "text": system}]
            return []
        if isinstance(system, list):
            return list(system)
        return []

    def _inject_pichay_system(
        self, system_blocks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Inject the static Pichay system prompt into system blocks.

        Replaces existing pichay block if present, otherwise appends.
        """
        from hamutay.message_ops import get_system_prompt, PICHAY_STATUS_MARKER

        pichay_text = get_system_prompt()

        # Check if already present
        for i, block in enumerate(system_blocks):
            if (
                isinstance(block, dict)
                and isinstance(block.get("text"), str)
                and PICHAY_STATUS_MARKER in block["text"]
            ):
                system_blocks[i] = {"type": "text", "text": pichay_text}
                return system_blocks

        # Not present — append
        system_blocks.append({"type": "text", "text": pichay_text})
        return system_blocks

    def _build_anchor(
        self,
        *,
        token_state: dict,
        page_store: Any = None,
        block_store: Any = None,
        policy: Any = None,
        last_cleanup_stats: str | None = None,
        token_cap: int = 0,
    ) -> str | None:
        """Build the dynamic anchor text for Region 4.

        Contains live status, tensor manifest, and pressure guidance.
        Ported from inject_system_status() in message_ops.py.
        """
        from hamutay.message_ops import _compute_pressure, _escape_xml_attr, _label_for_entry, _eviction_key_for_entry, MANIFEST_PRUNE_MINUTES

        effective, context_limit, hard_cap, pct, pressure = _compute_pressure(
            token_state, token_cap, policy
        )

        if effective <= 0:
            return None

        anchor_parts = [
            f"\n[pichay-live-status] "
            f"Context: {effective:,}/{context_limit:,} tok ({pct:.0f}%) | "
            f"Pressure: {pressure} | "
            f"Hard cap: {hard_cap:,} tok"
        ]

        # Tensor manifest (yuyay protocol)
        if page_store is not None and page_store._tensor_index:
            now = time.monotonic()
            tensor_lines = []
            released_handles = getattr(page_store, "_released_handles", set())
            released_count = 0
            pruned_count = 0
            for handle, entry in page_store._tensor_index.items():
                is_released = (
                    handle in released_handles
                    or _eviction_key_for_entry(entry) in page_store._released
                )
                if is_released:
                    released_count += 1
                    continue
                age_min = (now - entry.evicted_at) / 60
                fault_count = sum(
                    1 for f in page_store.faults
                    if f.original_eviction.tool_use_id == entry.tool_use_id
                )
                if age_min > MANIFEST_PRUNE_MINUTES and fault_count == 0:
                    pruned_count += 1
                    continue
                tensor_lines.append(
                    f'    <tensor handle="{handle}" tool="{entry.tool_name}" '
                    f'size="{entry.original_size}" age_minutes="{age_min:.0f}" '
                    f'faults="{fault_count}" '
                    f'label="{_escape_xml_attr(_label_for_entry(entry))}"/>'
                )
            if tensor_lines or pruned_count > 0:
                manifest_parts = ["\n<yuyay-manifest>\n"]
                if last_cleanup_stats:
                    manifest_parts.append(
                        f"  <last-turn-ops>{_escape_xml_attr(last_cleanup_stats)}"
                        f"</last-turn-ops>\n"
                    )
                if pruned_count > 0:
                    manifest_parts.append(
                        f'  <pruned count="{pruned_count}" '
                        f'reason="age&gt;{MANIFEST_PRUNE_MINUTES}m,faults=0"/>\n'
                    )
                if tensor_lines:
                    manifest_parts.append(
                        f'  <holdings count="{len(tensor_lines)}" '
                        f'eviction_bytes="{page_store.eviction_bytes_saved}" '
                        f'gc_bytes="{page_store.gc_bytes_saved}">\n'
                        + "\n".join(tensor_lines[:15])
                        + "\n  </holdings>\n"
                    )
                manifest_parts.append("</yuyay-manifest>")
                anchor_parts.append("".join(manifest_parts))

        if pressure in ("moderate", "high") and block_store is not None:
            large = block_store.large_blocks(min_size=2000)
            if large:
                block_lines = [
                    f"  - [block:{b.block_id}] {b.role} turn {b.turn} "
                    f"({b.size / 1024:.1f}KB): {b.preview}"
                    for b in large[:5]
                ]
                anchor_parts.append(
                    f"\nLargest blocks ({block_store.block_count} tracked):\n"
                    + "\n".join(block_lines)
                )
            anchor_parts.append(
                "\nCooperative memory: include <memory_cleanup> tags to manage. "
                "Ops: drop: block:XXXX, summarize: block:XXXX \"text\", "
                "anchor: block:XXXX, release: path1,path2, "
                "collapse: turns N-M \"summary\""
            )

            if pressure == "high" and page_store is not None and page_store._tensor_index:
                anchor_parts.append(
                    "\n<yuyay-query>Context pressure is high. "
                    "Review the manifest above. Which tensors can be "
                    "released? Respond in a <yuyay-response> block with "
                    "release decisions before your normal response."
                    "</yuyay-query>"
                )

        return "".join(anchor_parts)

    def _log_projection(
        self,
        system: list[dict],
        messages: list[dict],
        bp_count: int,
    ) -> None:
        """Log projection stats to stderr."""
        frozen_count = len([
            t for t in self.region_state.tensors.values() if t.frozen
        ])
        ephemeral_count = len(messages) - (frozen_count * 2) - (
            2 if (self.region_state.page_table or self.region_state.tensors) else 0
        )
        if ephemeral_count < 0:
            ephemeral_count = len(messages)

        system_bytes = sum(
            len(json.dumps(b, default=str)) for b in system
        )

        print(
            f"  {_DIM}[{self.session_id}] projection: "
            f"R1={system_bytes // 1024}KB "
            f"R2={frozen_count} tensors "
            f"R3={ephemeral_count} msgs "
            f"total={len(messages)} msgs "
            f"BPs={bp_count}{_RESET}",
            file=sys.stderr,
        )
