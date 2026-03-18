"""Idle detection and restructure triggering.

The Anthropic KV cache expires after ~5 minutes of inactivity. When the
cache expires, restructuring is free — the write cost is the same whether
we send the old layout or a clean one.

This module detects idle gaps and provides restructure triggers based on
both idle expiry and cumulative waste.
"""

from __future__ import annotations

import time


# Anthropic KV cache TTL — inferred from API behavior
_CACHE_TTL_SECONDS = 300.0  # 5 minutes

# Default waste threshold for active-session restructure (tokens)
_DEFAULT_WASTE_THRESHOLD = 50_000


class IdleState:
    """Tracks idle periods and restructure eligibility."""

    def __init__(
        self,
        cache_ttl: float = _CACHE_TTL_SECONDS,
        waste_threshold: int = _DEFAULT_WASTE_THRESHOLD,
    ):
        self._cache_ttl = cache_ttl
        self._waste_threshold = waste_threshold
        self._last_activity: float = time.monotonic()
        self._restructure_pending: bool = False

    def touch(self) -> None:
        """Record activity (called on each API request)."""
        self._last_activity = time.monotonic()

    @property
    def idle_seconds(self) -> float:
        """Seconds since last activity."""
        return time.monotonic() - self._last_activity

    @property
    def cache_expired(self) -> bool:
        """True if the KV cache has likely expired."""
        return self.idle_seconds > self._cache_ttl

    def is_idle_return(self) -> bool:
        """True if this is a return from an idle period.

        Should be called at the start of request processing. Returns True
        once per idle gap (resets after the first call).
        """
        if self.cache_expired:
            self.touch()  # reset for the new active period
            return True
        self.touch()
        return False

    def should_restructure(self, waste_tokens: int) -> bool:
        """True if a restructure is warranted based on waste accumulation.

        Called during active sessions (not idle). Returns True when
        cumulative waste exceeds the threshold.
        """
        return waste_tokens > self._waste_threshold
