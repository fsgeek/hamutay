import inspect
import json

from conftest import append_jsonl


def _status(event_id, status, at):
    return {
        "record_type": "event_status", "event_id": event_id, "status": status,
        "created_at": at.isoformat(), "event": {"type": "validation", "content": "wake"},
    }


def _loan(status, reason, at, episode="lease-episode"):
    return {
        "record_type": "heartbeat_status", "status": status, "reason": reason,
        "created_at": at.isoformat(),
        "detail": {"episode_id": episode, "holder": "yupi", "purpose": "training"},
    }


def _render_notes(records, event):
    from hamutay.events import operational_notes_for_event

    values = {
        "records": records,
        "all_records": records,
        "event": event,
        "event_id": event["event_id"],
        "created_at": event["created_at"],
    }
    args = []
    kwargs = {}
    for parameter in inspect.signature(operational_notes_for_event).parameters.values():
        value = values[parameter.name]
        if parameter.kind in {parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD}:
            args.append(value)
        else:
            kwargs[parameter.name] = value
    return json.dumps(operational_notes_for_event(*args, **kwargs), sort_keys=True)


def test_event_that_waited_through_loan_is_told_holder_and_purpose(clock):
    event = _status("waiting", "pending", clock())
    clock.advance(minutes=1)
    rest = _loan("resting", "substrate_lent", clock())
    clock.advance(minutes=2)
    wake = _loan("waking", "substrate_returning", clock())
    clock.advance(minutes=1)
    records = [event, rest, wake]

    note = _render_notes(records, event)

    assert "yupi" in note
    assert "training" in note
    assert note.count("yupi") == 1


def test_first_post_loan_note_survives_failure_and_is_consumed_once_on_completion(clock):
    rest = _loan("resting", "substrate_lent", clock())
    clock.advance(minutes=1)
    wake = _loan("waking", "substrate_returning", clock())
    clock.advance(minutes=1)
    first = _status("first", "pending", clock())
    records = [rest, wake, first]

    first_attempt = _render_notes(records, first)
    records += [_status("first", "running", clock()), _status("first", "failed", clock()),
                _status("first", "pending", clock())]
    retry = _render_notes(records, first)
    records += [_status("first", "running", clock()), _status("first", "completed", clock())]
    second = _status("second", "pending", clock())
    after_completion = _render_notes(records + [second], second)

    assert first_attempt.count("yupi") == 1
    assert retry.count("yupi") == 1
    assert "yupi" not in after_completion

