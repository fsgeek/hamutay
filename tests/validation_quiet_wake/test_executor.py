"""Independent validation from 2026-10-25-quiet-wake-option-design.md.

Expectations come from the spec and the existing public tool contract, without
reading the wake_at_until implementation. No model or event builder is mocked.
"""

from copy import deepcopy
from uuid import UUID

import pytest

from hamutay.tools import ToolExecutor


RECORD_ID = UUID("00000000-0000-0000-0000-000000000027")
UNTIL = "2026-10-31T20:00:00Z"
LATER = "2026-11-01T20:00:00Z"
REASON = 'Waiting for Sut’i: "bring the question back".\nThen I will listen.'


@pytest.fixture
def executor(tmp_path):
    return ToolExecutor(
        project_root=tmp_path, cycle=27, scheduled_by_record_id=RECORD_ID,
    )


@pytest.mark.parametrize(
    "options",
    [{}, {"until": UNTIL}],
    ids=["untimed", "timed"],
)
def test_default_declaration_schedules_nothing_and_keeps_result_shape(executor, options):
    result = executor.execute("declare_quiet", {"reason": REASON, **options})

    expected = {"recorded": True, "reason": REASON}
    if "until" in options:
        expected["until"] = UNTIL
    assert result == expected
    declaration = executor.pending_quiet_declaration
    assert declaration["record_type"] == "quiet_declaration"
    assert declaration["reason"] == REASON
    assert declaration["declared_by_cycle"] == 27
    assert declaration["declared_by_record_id"] == str(RECORD_ID)
    if "until" in options:
        assert declaration["until"] == UNTIL
    else:
        assert "until" not in declaration
    assert executor.pending_events == []


@pytest.mark.parametrize("options", [{}, {"until": UNTIL}], ids=["untimed", "timed"])
def test_explicit_false_records_quiet_without_scheduling(executor, options):
    result = executor.execute("declare_quiet", {
        "reason": REASON, "wake_at_until": False, **options,
    })

    assert "error" not in result
    assert result["recorded"] is True
    assert result["reason"] == REASON
    assert executor.pending_quiet_declaration["reason"] == REASON
    if "until" in options:
        assert result["until"] == UNTIL
        assert executor.pending_quiet_declaration["until"] == UNTIL
    assert executor.pending_events == []


@pytest.mark.parametrize(
    "until", [UNTIL, "2026-10-31T13:00:00-07:00"], ids=["utc", "offset"],
)
def test_wake_buffers_one_self_event_and_reports_its_identity(executor, until):
    result = executor.execute(
        "declare_quiet", {"reason": REASON, "until": until, "wake_at_until": True},
    )

    assert "error" not in result
    assert result["recorded"] is True
    assert result["reason"] == REASON
    assert result["until"] == until
    declaration = executor.pending_quiet_declaration
    assert declaration["reason"] == REASON
    assert declaration["until"] == until
    assert len(executor.pending_events) == 1
    event, = executor.pending_events
    assert event["record_type"] == "event_status"
    assert event["event_type"] == "self_scheduled_reflection"
    assert event["status"] == "pending"
    assert event["event_id"]
    assert event["not_before"] == until
    assert event["label"] == "quiet_end"
    assert event["requested_context"] == [{"tool": "recall", "record_id": str(RECORD_ID)}]
    assert event["purpose"] == (
        "Your declared quiet has ended; you asked to be woken now. "
        "Your reason when you went quiet: " + REASON
    )
    assert event["scheduled_by_cycle"] == 27
    assert event["scheduled_by_record_id"] == str(RECORD_ID)
    assert result["wake_scheduled"] is True
    assert result["wake_event_id"] == event["event_id"]
    assert result["wake_at"] == until


def test_missing_until_refuses_only_the_wake_and_preserves_words(executor):
    result = executor.execute(
        "declare_quiet", {"reason": REASON, "wake_at_until": True},
    )

    assert "error" not in result
    assert result["recorded"] is True
    assert result["reason"] == REASON
    assert executor.pending_quiet_declaration["reason"] == REASON
    assert "until" not in executor.pending_quiet_declaration
    assert executor.pending_events == []
    assert result["wake_scheduled"] is False
    assert isinstance(result["wake_refused"], str) and result["wake_refused"].strip()
    assert "until" in result["wake_refused"]
    assert "wake_event_id" not in result


@pytest.mark.parametrize(
    "option", ["yes", 1, 0, None, [], {}],
    ids=["string", "one", "zero", "null", "list", "object"],
)
@pytest.mark.parametrize("options", [{}, {"until": UNTIL}], ids=["untimed", "timed"])
def test_non_boolean_option_refuses_only_the_wake(executor, option, options):
    result = executor.execute(
        "declare_quiet", {"reason": REASON, "wake_at_until": option, **options},
    )

    assert "error" not in result
    assert result["recorded"] is True
    assert result["reason"] == REASON
    assert executor.pending_quiet_declaration["reason"] == REASON
    if "until" in options:
        assert result["until"] == UNTIL
        assert executor.pending_quiet_declaration["until"] == UNTIL
    else:
        assert "until" not in executor.pending_quiet_declaration
    assert executor.pending_events == []
    assert result["wake_scheduled"] is False
    assert isinstance(result["wake_refused"], str) and result["wake_refused"].strip()
    assert "wake_event_id" not in result


@pytest.mark.parametrize(
    "until", ["soon-ish", "", "2026-10-31T20:00:00"],
    ids=["unparseable", "empty", "naive"],
)
def test_malformed_until_records_neither_declaration_nor_wake(executor, until):
    result = executor.execute(
        "declare_quiet", {"reason": REASON, "until": until, "wake_at_until": True},
    )

    assert result.get("error")
    assert executor.pending_quiet_declaration is None
    assert executor.pending_events == []


@pytest.mark.parametrize(
    "replacement, wants_wake",
    [({"until": LATER, "wake_at_until": True}, True),
     ({"until": LATER}, False),
     ({"until": LATER, "wake_at_until": False}, False),
     ({"wake_at_until": True}, False),
     ({"until": LATER, "wake_at_until": "yes"}, False)],
    ids=["new-wake", "omitted", "false", "missing-until", "non-boolean"],
)
def test_replacement_retires_only_its_own_wake(executor, replacement, wants_wake):
    # Even a manually scheduled event with the same label must survive.
    scheduled = executor.execute("schedule_event", {
        "purpose": "Revisit evidence with context.", "label": "quiet_end",
        "requested_context": [{"tool": "recall", "cycle": 2}],
        "not_before": UNTIL,
    })
    assert "error" not in scheduled
    manual_before = deepcopy(executor.pending_events[0])
    first = executor.execute("declare_quiet", {
        "reason": "first quiet", "until": UNTIL, "wake_at_until": True,
    })
    assert len(executor.pending_events) == 2
    first_wake_id = first["wake_event_id"]
    first_declaration_id = executor.pending_quiet_declaration["declaration_id"]

    # Events scheduled after the declaration must also remain untouched.
    scheduled_after = executor.execute("schedule_event", {
        "purpose": "An independent later task.",
        "requested_context": [{"tool": "recall", "cycle": 3}],
        "not_before": LATER,
    })
    assert "error" not in scheduled_after
    manual_after = deepcopy(executor.pending_events[-1])
    result = executor.execute("declare_quiet", {"reason": REASON, **replacement})

    assert "error" not in result
    assert result["recorded"] is True
    assert result["reason"] == REASON
    declaration = executor.pending_quiet_declaration
    assert declaration["reason"] == REASON
    assert declaration["declaration_id"] != first_declaration_id
    pending = executor.pending_events
    assert len(pending) == 2 + wants_wake
    assert manual_before in pending
    assert manual_after in pending
    assert first_wake_id not in {event["event_id"] for event in pending}
    quiet_events = [event for event in pending if event["event_id"] not in {
        manual_before["event_id"], manual_after["event_id"],
    }]
    if wants_wake:
        event, = quiet_events
        assert event["event_id"] == result["wake_event_id"]
        assert event["not_before"] == LATER
        assert event["label"] == "quiet_end"
        assert event["requested_context"] == [{"tool": "recall", "record_id": str(RECORD_ID)}]
        assert event["purpose"].endswith(REASON)
        assert result["wake_scheduled"] is True
    else:
        assert quiet_events == []
        if replacement.get("wake_at_until") is not False and "wake_at_until" in replacement:
            assert result["wake_scheduled"] is False
            assert isinstance(result["wake_refused"], str) and result["wake_refused"].strip()


def test_malformed_replacement_preserves_previous_declaration_and_wake(executor):
    executor.execute("declare_quiet", {
        "reason": REASON, "until": UNTIL, "wake_at_until": True,
    })
    assert len(executor.pending_events) == 1
    declaration = deepcopy(executor.pending_quiet_declaration)
    pending = deepcopy(executor.pending_events)

    result = executor.execute("declare_quiet", {
        "reason": "must not replace", "until": "soon-ish", "wake_at_until": True,
    })

    assert result.get("error")
    assert executor.pending_quiet_declaration == declaration
    assert executor.pending_events == pending
