import json
import os
import threading
import time
from datetime import datetime, timezone

import pytest

from hamutay.assembly.ledger import (
    Ledger, LedgerMalformed, LedgerUnavailable, iso, parse_instant,
)


def test_parse_instant_requires_offset():
    assert parse_instant("2026-09-16T10:00:00Z").tzinfo is not None
    assert parse_instant("2026-09-16T10:00:00+00:00").hour == 10
    with pytest.raises(ValueError):
        parse_instant("2026-09-16T10:00:00")


def test_append_assigns_seq_and_created_at_and_is_one_line(ledger_path):
    led = Ledger(ledger_path)
    a = led.append({"record_type": "testimony", "text": "x"})
    b = led.append({"record_type": "testimony", "text": "y"})
    assert (a["seq"], b["seq"]) == (1, 2)
    parse_instant(a["created_at"])
    lines = ledger_path.read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["seq"] == 2
    assert not lines[1].endswith("\r")


def test_read_tolerates_exactly_one_torn_final_line(ledger_path):
    led = Ledger(ledger_path)
    led.append({"record_type": "testimony", "text": "x"})
    with ledger_path.open("a") as f:
        f.write('{"record_type": "test')          # torn, no newline
    records = led.read()
    assert [r["seq"] for r in records] == [1]
    assert led.torn_tail.startswith('{"record_type"')
    # the next append recovers: it overwrites from the end of the last complete line
    led.append({"record_type": "testimony", "text": "z"})
    records = led.read()
    assert [r["seq"] for r in records] == [1, 2] and led.torn_tail is None


def test_read_raises_on_a_malformed_middle_line(ledger_path):
    led = Ledger(ledger_path)
    led.append({"record_type": "testimony", "text": "x"})
    with ledger_path.open("a") as f:
        f.write("not json\n")
    # append() should fail when there's a malformed middle line (fail-closed)
    with pytest.raises(LedgerMalformed):
        led.append({"record_type": "testimony", "text": "y"})
    # file should still contain exactly the good line and the garbage line, no write
    lines = ledger_path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["seq"] == 1
    assert lines[1] == "not json"
    # read() should also raise
    with pytest.raises(LedgerMalformed):
        led.read()


def test_try_locked_times_out_while_another_holder_has_the_lock(ledger_path):
    led = Ledger(ledger_path)
    held = threading.Event()
    release = threading.Event()

    def holder():
        with Ledger(ledger_path).locked():
            held.set()
            release.wait(5)

    t = threading.Thread(target=holder)
    t.start()
    held.wait(5)
    t0 = time.monotonic()
    with pytest.raises(LedgerUnavailable):
        with led.try_locked(0.3):
            pass
    assert 0.25 <= time.monotonic() - t0 < 2.0
    release.set()
    t.join()


def test_signature_changes_on_append(ledger_path):
    led = Ledger(ledger_path)
    assert led.signature() == (0, 0.0)
    led.append({"record_type": "testimony", "text": "x"})
    size, mtime = led.signature()
    assert size > 0 and mtime > 0


def test_fsync_is_called_on_append(ledger_path, monkeypatch):
    calls = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(fd), real(fd)))
    Ledger(ledger_path).append({"record_type": "testimony", "text": "x"})
    assert calls
