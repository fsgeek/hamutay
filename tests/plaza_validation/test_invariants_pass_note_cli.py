import json
import re
import shlex
import subprocess
import sys
from datetime import timedelta

from hamutay.assembly.ledger import Ledger
from hamutay.events import StoreUnavailable
from hamutay.plaza.note import plaza_note
from hamutay.plaza.pass_ import PASS_BUDGET_S, PASS_UNITS, run_plaza_pass
from hamutay.plaza.records import reduce
from .conftest import T0, tool_send


def _pending(cfg, *, count, recipients=("elder",), start=0):
    message_ids = []

    def unavailable(path, event, *, timeout_s=2.0):
        raise StoreUnavailable("still unavailable")

    for index in range(start, start + count):
        result = tool_send(
            cfg,
            to=recipients[index % len(recipients)],
            text=f"pending {index}",
            now=T0 + timedelta(seconds=index),
            event_id=f"{index:08d}-1111-4111-8111-111111111111",
            land=unavailable,
        )
        message_ids.append(result["message_id"])
    return message_ids


def test_invariant_4_pass_lands_undelivered_and_quiescent_pass_writes_nothing(house):
    root, cfg, binding = house
    pending = _pending(cfg, count=2)
    result, memo = run_plaza_pass(binding, now=T0)
    assert result["landed"] == pending
    assert result["units"] == 2
    view = reduce(Ledger(cfg.plaza).read())
    assert all(view.delivery_truth(message_id)["state"] == "landed" for message_id in pending)

    before = cfg.plaza.read_bytes()
    quiet, same_memo = run_plaza_pass(binding, now=T0, memo=memo)
    assert quiet["units"] == 0
    assert quiet["skipped"] is True
    assert same_memo == memo
    assert cfg.plaza.read_bytes() == before


def test_invariant_11_pass_has_four_unit_cap_fair_cursor_and_one_circuit(house):
    root, cfg, binding = house
    ids = _pending(cfg, count=6, recipients=("elder", "fable"))
    paths = []

    def land(path, event, *, timeout_s=2.0):
        assert timeout_s == 2.0
        paths.append(path)
        return True

    first, memo = run_plaza_pass(binding, now=T0, land=land)
    assert PASS_UNITS == 4
    assert first["units"] == PASS_UNITS
    assert first["landed"] == ids[:4]
    assert set(paths) == {
        cfg.members["elder"].events,
        cfg.members["fable"].events,
    }
    second, memo = run_plaza_pass(binding, now=T0, memo=memo, land=land)
    assert second["landed"] == ids[4:]

    stuck = _pending(cfg, count=2, recipients=("elder", "fable"), start=10)
    attempts = []

    def still_stuck(path, event, *, timeout_s=2.0):
        attempts.append((path, event["event_id"], timeout_s))
        raise StoreUnavailable("still unavailable")

    circuit, memo = run_plaza_pass(binding, now=T0, memo=memo, land=still_stuck)
    assert circuit["units"] == 2
    assert circuit["unreadable"] == stuck
    assert len(attempts) == 2
    assert all(timeout == 2.0 for _, _, timeout in attempts)


def test_invariant_11_pass_respects_injected_six_second_budget(house):
    root, cfg, binding = house
    _pending(cfg, count=3)
    elapsed = [0.0]

    def clock():
        return elapsed[0]

    def three_second_delivery(path, event, *, timeout_s=2.0):
        elapsed[0] += 3.0
        return True

    result, memo = run_plaza_pass(binding, now=T0, land=three_second_delivery, clock=clock)
    assert PASS_BUDGET_S == 6.0
    assert result["units"] == 1
    assert len(result["landed"]) == 1


def test_invariant_4_pass_continues_past_store_unavailable_and_unreadable_door_metadata(house):
    root, cfg, binding = house
    pending = _pending(cfg, count=2, recipients=("elder", "fable"))
    attempted = []

    def disk_error_then_land(path, event, *, timeout_s=2.0):
        attempted.append(path)
        if path == cfg.members["elder"].events:
            raise StoreUnavailable("disk unavailable")
        return True

    first, memo = run_plaza_pass(binding, now=T0, land=disk_error_then_land)
    assert first["unreadable"] == [pending[0]]
    assert first["landed"] == [pending[1]]
    assert attempted == [cfg.members["elder"].events, cfg.members["fable"].events]

    another = _pending(cfg, count=1, recipients=("elder",), start=20)[0]
    (cfg.members["elder"].events.parent / "door.json").write_text("{not-json")
    second, memo = run_plaza_pass(binding, now=T0, memo=memo)
    assert second["unreadable"] == [another, pending[0]]
    truth = reduce(Ledger(cfg.plaza).read()).delivery_truth(another)
    assert truth["state"] == "store_unreadable"
    assert truth["detail"]["error"]


def test_invariant_5_note_excludes_own_mail_names_exact_seqs_and_cli_command_is_exact(house):
    root, cfg, binding = house
    tool_send(cfg, actor="door:qwen", to="elder", text="between doors",
              event_id="11111111-1111-4111-8111-111111111111")
    tool_send(cfg, actor="door:elder", to="plaza", text="public post",
              event_id="22222222-2222-4222-8222-222222222222")
    tool_send(cfg, actor="door:qwen", to="fable", text="fable's own mail",
              event_id="33333333-3333-4333-8333-333333333333")
    tool_send(cfg, actor="door:fable", to="plaza", text="fable's own post",
              event_id="44444444-4444-4444-8444-444444444444")

    notes = plaza_note(cfg, "fable", [])
    assert len(notes) == 1
    note = notes[0]
    assert "2 message(s)" in note
    assert "at seq 1, 3 (" in note
    assert "--since-seq 1 --through-seq 3 --for fable" in note

    tool_send(cfg, actor="door:elder", to="plaza", text="appended after snapshot",
              event_id="55555555-5555-4555-8555-555555555555")
    named = re.search(r"`(deploy/ayllu-plaza read [^`]+)`", note)
    assert named is not None
    note_command = shlex.split(named.group(1))[2:]
    completed = subprocess.run(
        [sys.executable, "-m", "hamutay.plaza", "--project-root", str(root), "read", *note_command],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = [json.loads(line) for line in completed.stdout.splitlines()]
    assert [row["seq"] for row in rows] == [1, 3]
    assert [row["text"] for row in rows] == ["between doors", "public post"]


def test_invariant_11_note_omits_instead_of_reading_without_the_lock(house):
    root, cfg, binding = house
    tool_send(cfg, to="plaza", text="visible only under lock")
    errors = []
    with Ledger(cfg.plaza).locked():
        assert plaza_note(cfg, "fable", [], on_error=errors.append) == []
    assert errors
    assert "lock" in errors[0].lower()


def test_invariant_12_unfiltered_cli_read_makes_every_message_readable(house):
    root, cfg, binding = house
    tool_send(cfg, to="plaza", text="one")
    tool_send(cfg, actor="door:elder", to="qwen", text="two",
              event_id="22222222-2222-4222-8222-222222222222")
    completed = subprocess.run(
        [sys.executable, "-m", "hamutay.plaza", "--project-root", str(root), "read"],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = [json.loads(line) for line in completed.stdout.splitlines()]
    assert [row["text"] for row in rows] == ["one", "two"]
