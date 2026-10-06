"""Independent r3 validation; each numbered docstring maps to a Testing item.

All histories are constructed locally. The public operational-notes function
is the sole production entry point exercised here.
"""

from datetime import datetime, timedelta, timezone

import pytest

from hamutay import events


T0 = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
NOW = T0 + timedelta(hours=6)
UNCERTAIN_STATE = (
    "This record does not say whether that wake's state update was kept; "
    "some failures happen before the state is saved and some after."
)
COMPLETED_STATE = "completed and its state was kept"
RERUN = "this event is the same one, run again"


def event_status(status, event_id="current-event", run_id=None, at=T0, **fields):
    row = {
        "record_type": "event_status",
        "event_id": event_id,
        "event_type": "inbound_message",
        "status": status,
        "created_at": at.isoformat(),
    }
    if run_id is not None:
        row["run_id"] = run_id
    if status == "completed":
        row["completed_at"] = at.isoformat()
    if status == "running":
        row["started_at"] = at.isoformat()
    row.update(fields)
    return row


def failed(event_id="failed-event", run_id="failed-run", at=T0, **fields):
    return event_status(
        "failed", event_id, run_id, at,
        failed_at=at.isoformat(),
        error_type="RuntimeError",
        error="wake failure sentinel",
        **fields,
    )


def heartbeat(status, reason, at, episode_id):
    return {
        "record_type": "heartbeat_status",
        "status": status,
        "reason": reason,
        "created_at": at.isoformat(),
        "detail": {
            "episode_id": episode_id,
            "holder": "validation-holder",
            "purpose": "validation workload",
        },
    }


def rest_history():
    # The first loan predates the current event (b); the second overlaps (a).
    current = event_status("pending", at=T0 + timedelta(hours=2))
    records = [
        heartbeat("resting", "substrate_lent", T0, "earlier-loan"),
        heartbeat("waking", "substrate_returning", T0 + timedelta(hours=1), "earlier-loan"),
        current,
        heartbeat("resting", "substrate_lent", T0 + timedelta(hours=3), "overlap-loan"),
        heartbeat("waking", "substrate_returning", T0 + timedelta(hours=4), "overlap-loan"),
    ]
    return records, current


@pytest.mark.parametrize("other_status", ["pending", "running", "expired"])
def test_01_no_failed_outcome_gives_no_failure_note(other_status):
    """1: Unrelated statuses, even with error fields, do not count."""
    current = event_status("pending")
    records = [
        event_status("completed", "previous", "completed-run"),
        event_status(other_status, "other", error="not a failed outcome"),
        {"record_type": "protocol_failure", "status": "failed", "error": "not an event"},
        current,
    ]
    assert events.operational_notes_for_event(records, current, now=NOW) == []


def test_02_single_failure_reports_all_recorded_fields():
    """2: The resident can identify the event, attempt, time and exception."""
    current = event_status("pending")
    failure = failed(
        "reflection-event-sentinel", "attempt-sentinel",
        at=T0 + timedelta(minutes=5),
        event_type="self_scheduled_reflection",
    )
    records = [
        event_status("completed", "previous", "completed-run"),
        failure,
        current,
    ]
    notes = events.operational_notes_for_event(records, current, now=NOW)
    assert len(notes) == 1
    for field in ("event_type", "event_id", "run_id", "failed_at", "error_type", "error"):
        assert failure[field] in notes[0]


def test_03_completion_boundary_uses_append_order_not_timestamps():
    """3: The last appended completion clears even a later-dated failure."""
    current = event_status("pending")
    records = [
        event_status("completed", "first-completion", "run-first", at=NOW),
        failed("cleared-failure", at=NOW + timedelta(days=1)),
        event_status("completed", "last-completion", "run-last", at=T0),
        current,
    ]
    assert events.operational_notes_for_event(records, current, now=NOW) == []
    later = failed("after-boundary", "later-run", at=T0 - timedelta(days=1))
    notes = events.operational_notes_for_event(records + [later], current, now=NOW)
    assert len(notes) == 1
    assert "after-boundary" in notes[0]
    assert "cleared-failure" not in notes[0]


def test_04_no_completed_wake_counts_every_failure_in_append_order():
    """4: With no completion, pending/running rows do not reset selection."""
    current = event_status("pending")
    records = [
        failed("first-failure", "first-run", at=NOW),
        event_status("running", "intermediate", "intermediate-run"),
        failed("second-failure", "second-run", at=T0),
        current,
    ]
    notes = events.operational_notes_for_event(records, current, now=NOW)
    assert len(notes) == 2
    assert "first-failure" in notes[0]
    assert "second-failure" in notes[1]


@pytest.mark.parametrize("failure_count", [5, 6, 8])
def test_05_only_five_most_recent_failures_with_summary_first(failure_count):
    """5: The cap, order and omission count are independent of timestamps."""
    current = event_status("pending")
    failures = [
        failed(
            f"failure-{i}-sentinel", f"run-{i}-sentinel",
            at=NOW - timedelta(minutes=i),
        )
        for i in range(failure_count)
    ]
    records = [
        failed("obsolete-failure", "obsolete-run"),
        event_status("completed", "boundary", "boundary-run"),
        *failures,
        current,
    ]
    notes = events.operational_notes_for_event(records, current, now=NOW)
    omitted = failure_count - 5
    assert len(notes) == 5 + bool(omitted)
    detail_notes = notes
    if omitted:
        assert notes[0].startswith(f"{omitted} earlier failed wake")
        assert "since your last completed wake are not listed; the event log holds them." in notes[0]
        detail_notes = notes[1:]
    for note, failure in zip(detail_notes, failures[-5:], strict=True):
        assert failure["event_id"] in note
        assert failure["run_id"] in note
    all_text = "\n".join(notes)
    assert "obsolete-failure" not in all_text
    for failure in failures[:omitted]:
        assert failure["event_id"] not in all_text


@pytest.mark.parametrize("current_id", ["failed-event", "different-event"])
def test_06_rerun_clause_requires_same_event_id(current_id):
    """6: Matching the event, rather than the run, signals a rerun."""
    current = event_status("pending", current_id, "new-run")
    notes = events.operational_notes_for_event([failed(), current], current, now=NOW)
    assert len(notes) == 1
    assert (RERUN in notes[0].lower()) == (current_id == "failed-event")


@pytest.mark.parametrize("error_length", [299, 300, 301, 450])
def test_07_error_has_300_character_boundary_and_visible_truncation(error_length):
    """7: Preserve the recorded prefix and visibly mark any omitted tail."""
    current = event_status("pending")
    error = "x" * min(error_length, 300) + "z" * max(error_length - 300, 0)
    failure = failed()
    failure["error"] = error
    notes = events.operational_notes_for_event([failure, current], current, now=NOW)
    assert len(notes) == 1
    assert error[:300] in notes[0]
    if error_length > 300:
        assert error not in notes[0]
        assert "z" not in notes[0]
        assert "truncated" in notes[0].lower()
    else:
        assert error in notes[0]
        assert "truncated" not in notes[0].lower()


@pytest.mark.parametrize(
    "missing",
    [
        ("failed_at",),
        ("error",),
        ("failed_at", "error"),
        ("failed_at", "error", "error_type", "event_type", "event_id", "run_id"),
    ],
)
def test_08_missing_optional_fields_still_produce_an_honest_note(missing):
    """8: Incomplete historical rows are still reportable without guessing."""
    current = event_status("pending")
    failure = failed()
    for field in missing:
        del failure[field]
    notes = events.operational_notes_for_event([failure, current], current, now=NOW)
    assert len(notes) == 1
    assert notes[0].startswith("A wake of yours failed:")
    assert UNCERTAIN_STATE in notes[0]
    assert RERUN not in notes[0].lower()
    assert COMPLETED_STATE not in notes[0]


def test_09_existing_rest_notes_are_unchanged_and_precede_failure_notes():
    """9: An overlapping loan (a) and an earlier loan (b) precede (c)."""
    records, current = rest_history()
    baseline = events.operational_notes_for_event(records, current, now=NOW)
    assert len(baseline) == 2
    assert baseline[0].startswith("heartbeat rested from")
    assert "this event waited 1h 0m of it." in baseline[0]
    assert baseline[1].startswith("Before this event existed")
    assert all('holder "validation-holder"' in note for note in baseline)
    notes = events.operational_notes_for_event(
        records + [failed()], current, now=NOW,
    )
    assert len(notes) == 3
    assert notes[:2] == baseline
    assert notes[2].startswith("A wake of yours failed:")


def test_10_failed_with_compact_retry_is_told_to_the_retry():
    """10: Construct the failed/pending pair written by append_failed_with_retry."""
    original = event_status("pending", "compact-event", at=T0)
    failure = {
        "record_type": "event_status",
        "event_id": original["event_id"],
        "event_type": original["event_type"],
        "status": "failed",
        "run_id": "window-failed-run",
        "failed_at": (T0 + timedelta(minutes=1)).isoformat(),
        "error_type": "TruncatedReply",
        "error": "finish_reason=length",
        "context_results": [],
        "admission": {"over_target": True},
    }
    retry = {
        **original,
        "created_at": (T0 + timedelta(minutes=2)).isoformat(),
        "detail": {
            "compact_context": True,
            "retry_of_run": "window-failed-run",
            "reason": "truncated_reply",
        },
    }
    records = [
        original,
        event_status("running", "compact-event", "window-failed-run"),
        failure,
        retry,
    ]
    notes = events.operational_notes_for_event(records, retry, now=NOW)
    assert len(notes) == 1
    assert "window-failed-run" in notes[0]
    assert "TruncatedReply: finish_reason=length" in notes[0]
    assert UNCERTAIN_STATE in notes[0]
    assert RERUN in notes[0].lower()


@pytest.mark.parametrize("same_run", [True, False])
def test_11_post_completion_wording_joins_on_run_id(same_run):
    """11: A completed event alone cannot establish that another run saved state."""
    current = event_status("pending")
    completion = event_status("completed", "shared-event", "saved-run")
    failure = failed("shared-event", "saved-run" if same_run else "other-run")
    notes = events.operational_notes_for_event(
        [completion, failure, current], current, now=NOW,
    )
    assert len(notes) == 1
    for field in ("event_type", "event_id", "run_id", "failed_at", "error_type", "error"):
        assert failure[field] in notes[0]
    if same_run:
        assert COMPLETED_STATE in notes[0]
        assert "a step after completion failed" in notes[0]
        assert UNCERTAIN_STATE not in notes[0]
    else:
        assert COMPLETED_STATE not in notes[0]
        assert UNCERTAIN_STATE in notes[0]


@pytest.mark.parametrize("created_at", [None, "not-an-ISO-date", ""])
def test_12_undated_event_receives_failures_without_rest_notes(created_at):
    """12: The age guard still applies to (a)/(b), while (c) remains available."""
    records, current = rest_history()
    assert len(events.operational_notes_for_event(records, current, now=NOW)) == 2
    if created_at is None:
        del current["created_at"]
    else:
        current["created_at"] = created_at
    assert events.operational_notes_for_event(records, current, now=NOW) == []
    notes = events.operational_notes_for_event(
        records + [failed()], current, now=NOW,
    )
    assert len(notes) == 1
    assert notes[0].startswith("A wake of yours failed:")
    assert UNCERTAIN_STATE in notes[0]


@pytest.mark.parametrize("post_completion", [False, True])
def test_13_failure_notes_never_claim_state_was_lost(post_completion):
    """13: Both note forms avoid the rejected r1/r2 state-loss assertions."""
    current = event_status("pending")
    failure = failed()
    records = []
    if post_completion:
        records.append(event_status("completed", failure["event_id"], failure["run_id"]))
    records.extend([failure, current])
    notes = events.operational_notes_for_event(records, current, now=NOW)
    assert len(notes) == 1
    text = notes[0].lower()
    for rejected in (
        "was not kept", "nothing reached your state", "nothing reached the state",
        "state was lost", "state update was lost",
    ):
        assert rejected not in text
    if post_completion:
        assert COMPLETED_STATE in notes[0]
    else:
        assert UNCERTAIN_STATE in notes[0]
        assert COMPLETED_STATE not in notes[0]


def test_notes_repeat_after_another_failure_and_clear_on_completion():
    """At-least-once delivery requires a completion, not a note read or a claim."""
    current = event_status("pending")
    records = [failed(), current]
    first = events.operational_notes_for_event(records, current, now=NOW)
    assert events.operational_notes_for_event(records, current, now=NOW) == first
    records.extend([
        event_status("running", current["event_id"], "next-run"),
        failed(current["event_id"], "next-run"),
    ])
    retry = event_status("pending", "later-event")
    repeated = events.operational_notes_for_event(records + [retry], retry, now=NOW)
    assert len(repeated) == 2
    assert repeated[0] == first[0]
    assert "next-run" in repeated[1]
    records.extend([
        event_status("completed", retry["event_id"], "successful-run"),
        retry,
    ])
    assert events.operational_notes_for_event(records, retry, now=NOW) == []
