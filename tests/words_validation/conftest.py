"""Fixtures authored from the recall-words plan, independent of implementation."""

import json
import socket

import pytest


CLAIM_NOTICE = (
    "This is what was said at this cycle, as recorded in your log. It is "
    "a claim made then, not verified truth: check it against other records "
    "before relying on it."
)


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("Independent words validation must not use the network")

    monkeypatch.setattr(socket.socket, "connect", refused)
    monkeypatch.setattr(socket.socket, "connect_ex", refused)
    monkeypatch.setattr(socket, "create_connection", refused)


@pytest.fixture
def claim_notice():
    return CLAIM_NOTICE


@pytest.fixture
def record():
    def make(cycle=17, **changes):
        value = {
            "cycle": cycle,
            "record_id": f"synthetic-record-{cycle}",
            "timestamp": f"2026-10-05T12:00:{cycle % 60:02d}+00:00",
            "model": "synthetic-validator-model",
            "user_message": f"Incoming words for cycle {cycle}.",
            "response_text": f"Reply words for cycle {cycle}.",
            "interim_text": None,
            "tool_activity_full": [],
        }
        value.update(changes)
        return value

    return make


@pytest.fixture
def write_log(tmp_path):
    """Bytes are written unchanged; dicts become synthetic UTF-8 JSONL records."""
    count = 0

    def write(*lines):
        nonlocal count
        count += 1
        path = tmp_path / f"synthetic-{count}.jsonl"
        raw_lines = [
            line
            if isinstance(line, bytes)
            else (json.dumps(line, ensure_ascii=False) + "\n").encode("utf-8")
            for line in lines
        ]
        path.write_bytes(b"".join(raw_lines))
        return path, raw_lines

    return write


@pytest.fixture
def words_tools():
    # Import only when the custodian runs the frozen suite.
    from hamutay.tools.words import tool_recall_words, tool_search_words

    return tool_recall_words, tool_search_words


@pytest.fixture
def labeled_values():
    """Walk labeled metadata without imposing an unspecified container layout."""
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                yield str(key).lower(), item
                yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)

    return walk
