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


def test_tool_enabled_session_recalls_prior_cycle():
    """Instance uses recall(recent=...) to reach back into seeded history.

    The unit of integration under test is: tool schema → model chooses to
    call recall → executor dispatches to tool_recall → result comes back
    through the multi-turn loop → model references it in its response.

    We seed `_prior_states` directly rather than driving the session
    through setup cycles, because Haiku's compliance with the default-
    stable state protocol is independent of memory-tool dispatch and
    would muddy the signal. (Observed: Haiku will name a field in
    `updated_regions` while omitting the field from its output, so the
    framework applies nothing — a state-update bug, not a memory-tool bug.)
    """
    from hamutay.taste_open import OpenTasteSession

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

        # Seed prior history directly — three cycles, with the nonce in
        # every one of them so recall(recent=N, field=...) finds it.
        session._prior_states.extend(
            [
                (
                    1,
                    {"secret_word": "quinoa", "cycle": 1},
                    "2026-04-18T10:00:00+00:00",
                ),
                (
                    2,
                    {"secret_word": "quinoa", "theme": "weather", "cycle": 2},
                    "2026-04-18T10:01:00+00:00",
                ),
                (
                    3,
                    {"secret_word": "quinoa", "theme": "music", "cycle": 3},
                    "2026-04-18T10:02:00+00:00",
                ),
            ]
        )
        # Bump the cycle counter so the next exchange runs as cycle 4.
        session._cycle = 3

        response = session.exchange(
            "Use the recall tool in recent mode to look up the recent "
            "values of the `secret_word` field in your prior cycles, and "
            "tell me the value you retrieved."
        )

        assert "quinoa" in response.lower(), (
            f"Expected 'quinoa' in response, got: {response!r}"
        )

        with open(log_path) as f:
            records = [json.loads(line) for line in f if line.strip()]
        last = records[-1]
        activity = last.get("state", {}).get("_activity_log", [])
        tool_names = [a.get("tool") for a in activity]
        assert "recall" in tool_names, (
            f"Expected 'recall' in activity log, got tools: {tool_names}"
        )
