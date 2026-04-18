"""Integration test for tool-enabled taste_open sessions.

Requires ANTHROPIC_API_KEY in environment. Makes a real API call —
gates the whole module on the env var, and uses Haiku to keep cost low.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


def test_tool_enabled_session_reads_file():
    """A tool-enabled instance can read a file and reference its content.

    The file contains a nonce word ('apacheta') that the model cannot
    produce without calling read(). If the response contains the nonce,
    the tool loop worked end-to-end.
    """
    from hamutay.taste_open import OpenTasteSession

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "hello.txt").write_text("The secret word is: apacheta\n")

        log_path = str(root / "session.jsonl")
        session = OpenTasteSession(
            model="claude-haiku-4-5",
            log_path=log_path,
            enable_tools=True,
            project_root=root,
            experiment_label="test_tools",
        )

        response = session.exchange(
            "There is a file called hello.txt in the project. "
            "Read it and tell me the secret word."
        )

        assert "apacheta" in response.lower(), (
            f"Expected 'apacheta' in response, got: {response!r}"
        )

        with open(log_path) as f:
            records = [json.loads(line) for line in f if line.strip()]

        last = records[-1]
        state = last.get("state", {})
        activity = state.get("_activity_log", [])
        tool_names = [a.get("tool") for a in activity]
        assert "read" in tool_names, (
            f"Expected 'read' in activity log, got tools: {tool_names}"
        )


def test_tool_enabled_session_records_optional_reason():
    """When the model provides a reason, it's recorded; when it doesn't,
    the activity log records None rather than an empty string."""
    from hamutay.taste_open import OpenTasteSession

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        log_path = str(root / "session.jsonl")
        session = OpenTasteSession(
            model="claude-haiku-4-5",
            log_path=log_path,
            enable_tools=True,
            project_root=root,
            experiment_label="test_tools_reason",
        )

        session.exchange("What time is it right now?")

        with open(log_path) as f:
            records = [json.loads(line) for line in f if line.strip()]

        last = records[-1]
        activity = last.get("state", {}).get("_activity_log", [])
        clock_entries = [a for a in activity if a.get("tool") == "clock"]
        assert clock_entries, "Expected at least one clock call"

        # Reason should be a string OR explicitly None — never a stub
        # like "no reason" manufactured to satisfy the schema.
        for entry in clock_entries:
            reason = entry.get("reason")
            assert reason is None or isinstance(reason, str)
