"""Drive real natural loops, completion persistence, and rebuilt operational notes."""

from copy import deepcopy
import json

import pytest

from hamutay import events
from hamutay.window import TruncatedReply

from .helpers import (
    CLEAN, LEAK, NOW, REPAIRED, SENTINEL, UNKNOWN, WITHDRAWN,
    call, expected_note, notes, pending, persisted_completion,
    session_and_store, status, turn, wake_script, xml,
)


@pytest.mark.parametrize("withdrawal", ["full", "perception", "stale"])
@pytest.mark.parametrize("repair", ["none", "valid", "invalid", "clean_then_repair", "exception"])
def test_07_real_loop_persists_pre_repair_pair(tmp_path, monkeypatch, withdrawal, repair):
    """7: Capture final text/request together before every state-repair outcome."""
    natural_text = CLEAN if repair == "clean_then_repair" else LEAK
    # Stale evidence is produced by a real previous exchange on the SAME session.
    previous = wake_script(LEAK, "full") if withdrawal == "stale" else []
    script = previous + wake_script(natural_text, "none" if withdrawal == "stale" else withdrawal)
    repair_text = None
    if repair == "valid":
        repair_text = REPAIRED
    elif repair in ("invalid", "clean_then_repair"):
        repair_text = xml("update_state", "repair-only-parameter")
    elif repair == "exception":
        script.append(RuntimeError("repair exception sentinel"))
    if repair_text is not None:
        script.append(turn(repair_text))
    session, store, transport, validator, builder = session_and_store(
        tmp_path, monkeypatch, script,
    )
    if withdrawal == "stale":
        pending(store, "Previous wake")
        previous_result = events.run_next_event(session, store, now=NOW)
        previous_row, _ = persisted_completion(store, previous_result["run_id"])
        assert transport.accepted[-1].get("tools", []) == []
        assert session._last_natural_final_turn == {
            "text": LEAK, "tools_offered": False, "all_tools_withdrawn": True,
        }
        assert previous_row["final_turn"] == {"tools_offered": False, "all_tools_withdrawn": True}
        # Clear the old leak as a selection boundary without overwriting session
        # evidence, so the new row/note must stand on its own.
        store.append(status("completed", "clean-boundary", "boundary-run", response_text=CLEAN))
    if repair != "none":
        session._state_validator = validator
        session._state_repair_builder = builder
    current = pending(store, "Current wake")
    expected_pair = {
        "text": natural_text,
        "tools_offered": withdrawal != "full",
        "all_tools_withdrawn": withdrawal == "full",
    }
    result = events.run_next_event(session, store, now=NOW)
    assert result["status"] == "completed"
    row, rows = persisted_completion(store, result["run_id"])
    assert row["response_text"] == (repair_text if repair_text is not None else natural_text)
    assert row["final_turn"] == {k: v for k, v in expected_pair.items() if k != "text"}
    if natural_text == LEAK:
        assert row["unexecuted_tool_calls"] == [{"function": "send_message"}]
        assert notes(rows) == [expected_note(row)]
        assert (WITHDRAWN in notes(rows)[0]) is (withdrawal == "full")
        assert (UNKNOWN in notes(rows)[0]) is (withdrawal != "full")
    else:
        assert "unexecuted_tool_calls" not in row
        assert notes(rows) == []
    if repair == "exception":
        assert not [r for r in rows if r.get("event_id") == current["event_id"]
                    and r.get("status") == "failed"]
        assert events.failed_wake_notes(rows, current) == []
        session_rows = [json.loads(line) for line in (tmp_path / "session.jsonl").read_text().splitlines()]
        assert session_rows[-1]["state_validation"]["status"] == "repair_failed"
    elif repair != "none":
        assert row["wake_validation"]["status"] == ("repaired" if repair == "valid" else "unrepaired")
    assert session._last_natural_final_turn == expected_pair
    assert not transport.script
    final_natural_request = transport.accepted[-2] if repair_text is not None else transport.accepted[-1]
    assert bool(final_natural_request.get("tools")) == expected_pair["tools_offered"]
    if withdrawal == "full":
        assert final_natural_request["tool_choice"] == "none"
    elif withdrawal == "perception":
        names = {t["function"]["name"] for t in final_natural_request["tools"]}
        assert "update_state" in names and "read" not in names and "bash" not in names
    else:
        assert "read" in {t["function"]["name"] for t in final_natural_request["tools"]}
    if repair != "none":
        assert len(builder.calls) == 1
        assert builder.calls[0]["response_text"] == natural_text
        assert validator.calls[0]["evidence"] == expected_pair  # BEFORE repair is invoked
        assert transport.payloads[-1].get("tools", []) == []


def test_07_evidence_resets_before_a_new_exchange_can_fail(tmp_path, monkeypatch):
    """7/Interface: A failed next exchange cannot leave the previous final pair."""
    script = wake_script(LEAK, "full") + [RuntimeError("next exchange failed")]
    session, store, transport, _, _ = session_and_store(tmp_path, monkeypatch, script)
    pending(store)
    events.run_next_event(session, store, now=NOW)
    assert session._last_natural_final_turn["all_tools_withdrawn"] is True
    seen_at_start = []
    original = transport.__call__
    def observe(payload):
        seen_at_start.append(deepcopy(session._last_natural_final_turn))
        return original(payload)
    monkeypatch.setattr(session._backend, "_post_chat", observe)
    with pytest.raises(RuntimeError, match="next exchange failed"):
        session.exchange("Next wake")
    assert seen_at_start == [None]
    assert session._last_natural_final_turn is None


def test_07_evidence_describes_accepted_request_after_recovery(tmp_path, monkeypatch):
    """7/Interface: A rejected offered-tools request is not the reply-producing request."""
    # Recovery is allowed after an accepted tool turn; it withdraws perception
    # and resends the same turn with only the surviving state tools.
    script = [turn(calls=[call("clock", {})]),
              RuntimeError("request (1200 tokens) exceeds the available context size (1000 tokens)"),
              turn(LEAK)]
    session, store, transport, _, _ = session_and_store(tmp_path, monkeypatch, script)
    pending(store)
    result = events.run_next_event(session, store, now=NOW)
    row, rows = persisted_completion(store, result["run_id"])
    assert len(transport.payloads) == 3 and len(transport.accepted) == 2
    rejected_names = {t["function"]["name"] for t in transport.payloads[1]["tools"]}
    accepted_names = {t["function"]["name"] for t in transport.accepted[-1]["tools"]}
    assert "read" in rejected_names and "read" not in accepted_names
    assert "update_state" in accepted_names
    assert session._last_natural_final_turn == {
        "text": LEAK, "tools_offered": True, "all_tools_withdrawn": False,
    }
    assert row["final_turn"] == {"tools_offered": True, "all_tools_withdrawn": False}
    assert notes(rows) == [expected_note(row)]
    assert notes(rows)[0].endswith(UNKNOWN)


def test_08_interim_xml_beside_structured_call_is_not_detected(tmp_path, monkeypatch):
    """8: Interim text is archived but only the final reply supplies detection."""
    script = [turn(LEAK, calls=[call("update_state", {"updates": {"observed": True}})]), turn(CLEAN)]
    session, store, transport, _, _ = session_and_store(tmp_path, monkeypatch, script)
    pending(store)
    result = events.run_next_event(session, store, now=NOW)
    row, rows = persisted_completion(store, result["run_id"])
    assert row["response_text"] == CLEAN
    assert "unexecuted_tool_calls" not in row
    assert session._last_natural_final_turn["text"] == CLEAN
    assert row["final_turn"] == {"tools_offered": True, "all_tools_withdrawn": False}
    assert notes(rows) == []
    session_rows = [json.loads(line) for line in (tmp_path / "session.jsonl").read_text().splitlines()]
    assert session_rows[-1]["interim_text"] == [LEAK]
    assert session.state["observed"] is True
    assert not transport.script


@pytest.mark.parametrize("truncated_text", [LEAK, LEAK.removesuffix("</tool_call>")])
def test_08_length_is_failure_and_compact_retry_is_a_new_run(tmp_path, monkeypatch, truncated_text):
    """8: Even complete XML under length cannot become completed-call evidence."""
    retry_text = xml("send_message") + "\n" + xml("send_message")
    script = [turn(truncated_text, finish="length"), turn(retry_text)]
    session, store, transport, _, _ = session_and_store(tmp_path, monkeypatch, script, aware=True)
    original = pending(store)
    with pytest.raises(TruncatedReply):
        events.run_next_event(session, store, now=NOW)
    rows = events.EventStore(store.path).read_records()
    failure = next(r for r in rows if r.get("status") == "failed")
    retry = next(r for r in rows if r.get("status") == "pending" and r.get("detail", {}).get("compact_context"))
    assert retry["event_id"] == original["event_id"]
    assert retry["detail"]["retry_of_run"] == failure["run_id"]
    assert "unexecuted_tool_calls" not in failure and "final_turn" not in failure
    assert session._last_natural_final_turn is None
    assert events.unexecuted_call_notes(rows, retry) == []
    first_notes = notes(rows, retry)
    assert len(first_notes) == 1 and "TruncatedReply" in first_notes[0]
    result = events.run_next_event(session, store, now=NOW)
    row, rows = persisted_completion(store, result["run_id"])
    assert row["event_id"] == original["event_id"] and row["run_id"] != failure["run_id"]
    assert row["response_text"] == retry_text
    assert row["unexecuted_tool_calls"] == [{"function": "send_message"}, {"function": "send_message"}]
    assert row["final_turn"] == {"tools_offered": True, "all_tools_withdrawn": False}
    assert events.failed_wake_notes(rows, status("pending")) == []
    rebuilt = notes(rows)
    assert len(rebuilt) == 1 and row["run_id"] in rebuilt[0]
    assert "calls to `send_message`, `send_message` written as text." in rebuilt[0]
    assert failure["run_id"] not in rebuilt[0]
    assert SENTINEL not in rebuilt[0]
    assert not transport.script
