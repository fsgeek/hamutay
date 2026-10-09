"""Independent r5 validation; numbered docstrings map to spec Tests 1–10."""

from datetime import timedelta
import json
import pytest

from hamutay import events
from hamutay.taste_open import ExchangeResult, OpenTasteSession

from .helpers import (
    CLEAN, LEAK, NOW, SENTINEL, T0, UNKNOWN, WITHDRAWN,
    completed_kwargs, detect, expected_note, leaked, notes, pending,
    persisted_completion, session_and_store, status, turn, xml,
)


@pytest.mark.parametrize("text", [xml(), LEAK, "Prose before the call.\n" + xml()])
def test_01_qwen_complete_block_is_detected(text):
    """1: Standalone, empty think block, and prose-prefixed Qwen XML."""
    assert detect(text) == [{"function": "send_message"}]


@pytest.mark.parametrize("text", [
    None, "", "ordinary prose", "<tool_call></tool_call>",
    "<tool_call><function=>body</function></tool_call>",
    "<tool_call><function=send_message>body</function>",
    "<tool_call><function=send_message>body</tool_call>",
    "<function=send_message>body</function></tool_call>",
])
def test_01_malformed_or_empty_text_is_not_detected(text):
    """1: Incomplete delimiters or a missing function name give []."""
    assert detect(text) == []


def test_01_fenced_example_is_detected_with_honest_wording():
    """1: A quotation still is a call written as text; no intent is inferred."""
    text = "Here is an example:\n```xml\n" + xml() + "\n```"
    row = status("completed", response_text=text, unexecuted_tool_calls=detect(text))
    assert row["unexecuted_tool_calls"] == [{"function": "send_message"}]
    assert events.unexecuted_call_notes([row], status("pending")) == [expected_note(row)]


@pytest.mark.parametrize("optional", [{}, {"final_turn": None, "unexecuted_tool_calls": None},
                                       {"final_turn": {}, "unexecuted_tool_calls": []}])
def test_02_store_omits_absent_or_empty_optional_fields(tmp_path, optional):
    """2/Interface: Both completion builders accept optional keywords and omit empties."""
    store = events.EventStore(tmp_path / "events.jsonl")
    kwargs = completed_kwargs(**optional)
    built = store._build_completed(**kwargs)
    saved = store.append_completed_atomic(**kwargs)
    for row in (built, saved, store.read_records()[0]):
        assert "final_turn" not in row
        assert "unexecuted_tool_calls" not in row


@pytest.mark.parametrize("evidence", [
    {"tools_offered": True, "all_tools_withdrawn": False},
    {"tools_offered": False, "all_tools_withdrawn": True},
    {"tools_offered": False, "all_tools_withdrawn": False},
])
def test_02_store_preserves_populated_parameter_free_fields(tmp_path, evidence):
    """2/Interface: A dict with false booleans is populated, not absent."""
    store = events.EventStore(tmp_path / "events.jsonl")
    fields = {"final_turn": evidence, "unexecuted_tool_calls": [{"function": "send_message"}]}
    built = store._build_completed(**completed_kwargs(**fields))
    saved = store.append_completed_atomic(**completed_kwargs(**fields))
    for row in (built, saved, store.read_records()[0]):
        for key, value in fields.items():
            assert row[key] == value
        assert SENTINEL not in json.dumps({key: row[key] for key in fields})
        assert row["response_text"] == LEAK


@pytest.mark.parametrize("text,detected", [(LEAK, True), (CLEAN, False), ("<tool_call>", False)])
def test_02_runner_records_only_detected_calls(tmp_path, monkeypatch, text, detected):
    """2: The runner copies booleans, detects text, and persists only names."""
    session, store, transport, _, _ = session_and_store(tmp_path, monkeypatch, [turn(text)])
    pending(store)
    result = events.run_next_event(session, store, now=NOW)
    row, _ = persisted_completion(store, result["run_id"])
    assert not transport.script
    assert row["final_turn"] == {"tools_offered": True, "all_tools_withdrawn": False}
    if detected:
        assert row["unexecuted_tool_calls"] == [{"function": "send_message"}]
    else:
        assert "unexecuted_tool_calls" not in row
    assert SENTINEL not in json.dumps({k: row[k] for k in ("final_turn", "unexecuted_tool_calls") if k in row})
    assert row["response_text"] == text


class TerminalBackend:
    """A non-natural exchange can contain XML without creating natural evidence."""

    def call(self, **kwargs):
        return ExchangeResult(raw_output={"response": LEAK}, stop_reason="tool_use",
                              input_tokens=10, output_tokens=10)


def test_02_non_natural_completion_writes_neither_field(tmp_path):
    """2/Interface: None evidence on a terminal path suppresses both new fields."""
    store = events.EventStore(tmp_path / "events.jsonl")
    session = OpenTasteSession(backend=TerminalBackend(), log_path=str(tmp_path / "session.jsonl"))
    pending(store)
    result = events.run_next_event(session, store, now=NOW)
    assert session._last_natural_final_turn is None
    row, rows = persisted_completion(store, result["run_id"])
    assert "final_turn" not in row and "unexecuted_tool_calls" not in row
    assert events.unexecuted_call_notes(rows, status("pending")) == []


def test_03_notes_repeat_until_clean_completion():
    """3: Reading notes, running, and failing do not acknowledge a leak."""
    row = leaked()
    current = status("pending", "receiving-event", "receiving-run")
    history = [row, current]
    first = notes(history, current)
    assert first == [expected_note(row)]
    assert notes(history, current) == first
    history.extend([status("running", "receiving-event", "receiving-run"),
                    status("failed", "receiving-event", "receiving-run")])
    assert events.unexecuted_call_notes(history, current) == first
    second = leaked("second-leak", "second-run")
    history.append(second)
    assert notes(history, current) == [expected_note(row), expected_note(second)]
    history.append(status("completed", "clean-event", "clean-run", response_text=CLEAN,
                          unexecuted_tool_calls=[]))
    assert notes(history, current) == []


def rest_history():
    current = status("pending", "receiving-event", at=T0 + timedelta(hours=2))
    def hb(kind, hour, episode):
        return {"record_type": "heartbeat_status", "status": kind,
                "reason": "substrate_lent" if kind == "resting" else "substrate_returning",
                "created_at": (T0 + timedelta(hours=hour)).isoformat(),
                "detail": {"episode_id": episode, "holder": "validation-holder", "purpose": "validation"}}
    return [hb("resting", 0, "earlier"), hb("waking", 1, "earlier"), current,
            hb("resting", 3, "overlap"), hb("waking", 4, "overlap")], current


def test_03_rule_d_follows_unchanged_rules_a_b_c():
    """3: Exact existing rest/failure notes precede the new leak note."""
    records, current = rest_history()
    row = leaked()
    failure = status("failed", "failure-event", "failure-run")
    baseline = notes([*records, failure], current)
    assert len(baseline) == 3
    assert baseline[0].startswith("heartbeat rested from")
    assert baseline[1].startswith("Before this event existed")
    assert baseline[2].startswith("A wake of yours failed:")
    # Insert the completion BEFORE the failure so rule (c) has the same selection.
    actual = notes([row, *records, failure], current)
    assert actual == [*baseline, expected_note(row)]
    assert events.failed_wake_notes([row, *records, failure], current) == baseline[2:]


@pytest.mark.parametrize("evidence", [
    None, {}, {"tools_offered": True, "all_tools_withdrawn": False},
    {"tools_offered": False, "all_tools_withdrawn": False},
    {"tools_offered": False, "all_tools_withdrawn": True},
])
@pytest.mark.parametrize("misleading_activity", [False, True])
def test_05_cause_reads_only_completed_row_final_turn(evidence, misleading_activity):
    """5: Earlier withdrawal, repair withdrawal and mismatch cannot supply a cause."""
    row = leaked()
    if evidence is None:
        del row["final_turn"]
    else:
        row["final_turn"] = evidence
    row["response_state_mismatch"] = True
    if misleading_activity:
        row["tool_activity_full"] = [{"tool": "_framework", "action": "all_tools_withdrawn"}]
        row["wake_validation"] = {"repair": {"final_turn": {"all_tools_withdrawn": True}}}
    result = events.unexecuted_call_notes([row], status("pending"))
    assert result == [expected_note(row)]
    withdrawn = bool(evidence and evidence.get("all_tools_withdrawn"))
    assert (WITHDRAWN in result[0]) is withdrawn
    assert (UNKNOWN in result[0]) is not withdrawn


@pytest.mark.parametrize("mismatch", [False, True])
def test_06_old_xml_completion_is_never_backfilled(mismatch):
    """6: Neither response text nor mismatch retroactively establishes a leak."""
    old = status("completed", response_text=LEAK, response_state_mismatch=mismatch)
    assert events.unexecuted_call_notes([old], status("pending")) == []
    assert notes([old]) == []
    new = leaked("new-event", "new-run")
    assert notes([old, new]) == [expected_note(new)]
    assert notes([new, old]) == []  # a field-less completion is a clean boundary


def test_08_repeated_function_names_keep_block_order():
    """8/1: Complete blocks are not collapsed by function name."""
    text = xml("send_message") + "\n" + xml("update_state") + "\n" + xml("send_message")
    names = ["send_message", "update_state", "send_message"]
    assert detect(text) == [{"function": name} for name in names]
    row = leaked(names=names)
    result = events.unexecuted_call_notes([row], status("pending"))
    assert len(result) == 1
    assert "ended with calls to `send_message`, `update_state`, `send_message` written as text." in result[0]
    assert result[0].endswith(UNKNOWN)
    assert SENTINEL not in result[0]


def test_09_leak_failures_leak_clean_has_separate_cutoffs():
    """9/3: Leak completions clear (c); only a clean completion clears (d)."""
    a, b = leaked("leak-a", "run-a"), leaked("leak-b", "run-b")
    failures = [status("failed", "retry-event", f"failed-{i}") for i in range(2)]
    history = [a, *failures]
    failure_notes = events.failed_wake_notes(history, status("pending"))
    assert len(failure_notes) == 2
    assert notes(history) == [*failure_notes, expected_note(a)]
    history.append(b)
    assert events.failed_wake_notes(history, status("pending")) == []
    assert notes(history) == [expected_note(a), expected_note(b)]
    history.append(status("completed", "clean", "clean-run"))
    assert notes(history) == []


@pytest.mark.parametrize("same_event", [False, True])
def test_09_completed_then_failed_in_same_run_keeps_both_honest_notes(same_event):
    """9: Failure after completion does not erase the recorded unexecuted call."""
    row = leaked()
    history = [row, status("failed", row["event_id"], row["run_id"])]
    current = status("pending", row["event_id"] if same_event else "receiving-event",
                     "receiving-run")
    failure_notes = events.failed_wake_notes(history, current)
    assert len(failure_notes) == 1
    assert "completed and its state was kept" in failure_notes[0]
    assert "a step after completion failed" in failure_notes[0]
    assert (" This event is the same one, run again." in failure_notes[0]) is same_event
    assert notes(history, current) == [*failure_notes, expected_note(row)]


@pytest.mark.parametrize("created_at", [None, "", "not-an-ISO-date"])
def test_09_undated_receiving_event_still_gets_rules_c_then_d(created_at):
    """9: The early return suppresses rest notes but preserves (c) and (d)."""
    records, current = rest_history()
    if created_at is None:
        del current["created_at"]
    else:
        current["created_at"] = created_at
    row = leaked()
    failure = status("failed", "failure-event", "failure-run")
    history = [row, *records, failure]
    failure_notes = events.failed_wake_notes(history, current)
    assert len(failure_notes) == 1
    assert notes(history, current) == [*failure_notes, expected_note(row)]


@pytest.mark.parametrize("count", [5, 6, 8])
def test_09_newest_five_runs_in_append_order_with_overflow_first(count):
    """9: Same event IDs and reversed dates cannot collapse or reorder runs."""
    assert events.UNEXECUTED_CALL_NOTE_LIMIT == 5
    rows = [leaked("shared-retry-event", f"run-{i}-sentinel", at=NOW - timedelta(minutes=i))
            for i in range(count)]
    history = [leaked("obsolete-event", "obsolete-run"),
               status("completed", "clean-boundary", at=T0), *rows]
    omitted = count - 5
    expected = [expected_note(row) for row in rows[-5:]]
    if omitted:
        noun, verb = ("wake", "is") if omitted == 1 else ("wakes", "are")
        expected.insert(0, f"{omitted} earlier {noun} that ended with an unexecuted call "
                        f"since your last clean wake {verb} not listed; the event log holds them.")
    assert events.unexecuted_call_notes(history, status("pending")) == expected
    assert notes(history) == expected


@pytest.mark.parametrize("kind", ["pending", "running", "failed", "expired"])
def test_09_only_completed_event_status_rows_produce_leak_notes(kind):
    """9/6: Stray new fields on non-completions are not completed-wake evidence."""
    row = leaked()
    row["status"] = kind
    unrelated = {**leaked("unrelated", "unrelated-run"), "record_type": "protocol_failure"}
    assert events.unexecuted_call_notes([row, unrelated], status("pending")) == []
