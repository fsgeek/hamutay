"""Tool calls that came back as text: detection by known textual format.

A model can write a well-formed call when the request offered no tools to
parse it against (spec docs/superpowers/specs/2026-10-08-unexecuted-tool-call-note-design.md).
The server then returns it as content, and nothing executes it. This module
finds such blocks so the resident can be told. It returns function names only;
parameter values are the resident's words and are never extracted.

The detector knows only the formats in ``_FORMATS``. An unknown format is
silent, which the spec declares.
"""

from __future__ import annotations

import re

# Qwen's XML tool-call form: <tool_call> <function=NAME> ... </function> </tool_call>
_QWEN_XML = re.compile(
    r"<tool_call>\s*<function=([A-Za-z_][A-Za-z0-9_.-]*)>.*?</function>\s*</tool_call>",
    re.DOTALL,
)

_FORMATS: tuple[re.Pattern[str], ...] = (_QWEN_XML,)


def detect_unexecuted_tool_calls(text: str | None) -> list[dict]:
    """One ``{"function": NAME}`` per complete block, in the order written."""
    if not text:
        return []
    found: list[tuple[int, str]] = []
    for pattern in _FORMATS:
        found.extend((m.start(), m.group(1)) for m in pattern.finditer(text))
    return [{"function": name} for _, name in sorted(found)]
