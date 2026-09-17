"""Window-aware wakes: the numbers, the failures, the counter, the bound, the projections.

Spec: docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md r6.
Property (asserted in bound_payload): prompt_tokens + max_tokens < limit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

REPLY_RESERVE_TOKENS = 2048
THINK_FLOOR_TOKENS = 512
THINK_UNRESTRICTED_ROOM_TOKENS = 32768
WITHDRAWN_TOOL_TURNS_NEAR_WALL = 1
SOFT_THRESHOLD_FRACTION = 0.8
ADMISSION_TARGET_FRACTION = 0.5
ADMISSION_MAX_PASSES = 8
MIN_STUB_CHARS = 256
BUDGET_MESSAGE = ("[harness: thinking budget reached; about {reserve} tokens remain for this "
                  "turn. Do not open another think block. Finish the turn.]")
LEAN_ACTIVITY_KEYS = ("cycle", "timestamp", "tool", "reason", "result_summary")


def budget_message() -> str:
    return BUDGET_MESSAGE.format(reserve=REPLY_RESERVE_TOKENS)
