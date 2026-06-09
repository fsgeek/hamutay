"""Cognition adapters for autonomous memory-driven runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


JsonDict = dict[str, Any]


class ExchangeSession(Protocol):
    """Session surface required by the live autonomous cognition adapter."""

    def exchange(self, user_message: str, **kwargs: Any) -> str:
        ...


class _NoArgument:
    pass


NO_ARGUMENT = _NoArgument()
TerminalSurfaceProvider = JsonDict | Callable[[str], JsonDict | None] | None


@dataclass
class SessionExchangeCognition:
    """Adapt a live session's ``exchange`` method to ``AutonomousDriver``.

    ``OpenTasteSession.exchange`` already has the right core shape for the
    driver: one stimulus in, one visible response out. This adapter makes that
    contract explicit and keeps optional taste-open controls out of the driver.
    ``force_memory`` is omitted unless explicitly supplied, so simpler sessions
    such as ``ChatSession`` can still be wrapped without receiving unsupported
    keyword arguments.
    """

    session: ExchangeSession
    force_memory: Any = NO_ARGUMENT
    terminal_surface: TerminalSurfaceProvider = None

    def __call__(self, stimulus: str) -> str:
        kwargs: JsonDict = {}
        if self.force_memory is not NO_ARGUMENT:
            kwargs["force_memory"] = self.force_memory
        terminal_surface = self._terminal_surface(stimulus)
        if terminal_surface is not None:
            kwargs["terminal_surface"] = terminal_surface
        return str(self.session.exchange(stimulus, **kwargs))

    def _terminal_surface(self, stimulus: str) -> JsonDict | None:
        if callable(self.terminal_surface):
            return self.terminal_surface(stimulus)
        return self.terminal_surface
