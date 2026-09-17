from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from hamutay.assembly.close import GRACE, try_close
from hamutay.assembly.position import record_position
from hamutay.assembly.records import reduce
from hamutay.context_policy import ContextPolicy
from hamutay.events import EventStore, WakeContext, run_next_event
from hamutay.heartbeat import recover_orphaned_running
from hamutay.window import ExhaustedBeforeRequest, TruncatedReply, WakeAccount

from .conftest import (
    CLOSE,
    T0,
    aware_policy,
    inbound_event,
    records,
    scripted_backend,
    seeded_session,
)


def _window_exhaustion():
    return ExhaustedBeforeRequest(
        prompt_tokens=65_000,
        limit=65_536,
        room=535,
        max_tokens=535,
    )


def test_failed_with_retry_appends_two_rows_once_then_only_the_second_failed_row(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    original = inbound_event(event_id="retry-once")
    store.append(original)
    event, first_running = store.claim_next_pending(now=T0)
    before_first = len(store.read_records())

    first_failed, retry = store.append_failed_with_retry(
        event=event,
        run_id=first_running["run_id"],
        exc=_window_exhaustion(),
        reason="exhausted_before_request",
    )

    first_delta = store.read_records()[before_first:]
    assert first_delta == [first_failed, retry]
    assert [row["status"] for row in first_delta] == ["failed", "pending"]
    assert retry["detail"] == {
        "compact_context": True,
        "retry_of_run": first_running["run_id"],
        "reason": "exhausted_before_request",
    }

    compact_event, second_running = store.claim_next_pending(now=T0 + timedelta(seconds=1))
    before_second = len(store.read_records())
    second_failed, no_retry = store.append_failed_with_retry(
        event=compact_event,
        run_id=second_running["run_id"],
        exc=_window_exhaustion(),
        reason="exhausted_before_request",
    )

    assert no_retry is None
    assert store.read_records()[before_second:] == [second_failed]
    assert second_failed["status"] == "failed"


class _FailingSession:
    _prior_states = []
    _bridge = None
    _state = {}
    cycle = 1
    _last_admission = None

    def __init__(self, policy, error):
        self.context_policy = policy
        self.error = error
        self.compact_flags: list[bool] = []

    def exchange(self, message, **kwargs):
        self.compact_flags.append(kwargs["compact"])
        raise self.error


def test_run_next_event_retries_a_window_failure_once_only_on_a_window_aware_door(tmp_path):
    aware_store = EventStore(tmp_path / "aware.jsonl")
    aware_store.append(inbound_event(event_id="aware-event"))
    aware = _FailingSession(aware_policy(), _window_exhaustion())

    with pytest.raises(ExhaustedBeforeRequest):
        run_next_event(aware, aware_store, now=T0)
    assert [row["status"] for row in aware_store.read_records()] == [
        "pending",
        "running",
        "failed",
        "pending",
    ]

    with pytest.raises(ExhaustedBeforeRequest):
        run_next_event(aware, aware_store, now=T0 + timedelta(seconds=1))
    assert aware.compact_flags == [False, True]
    assert aware_store.read_records()[-1]["status"] == "failed"
    assert aware_store.next_pending(now=T0 + timedelta(seconds=2)) is None

    plain_store = EventStore(tmp_path / "plain.jsonl")
    plain_store.append(inbound_event(event_id="plain-event"))
    plain_error = TruncatedReply(
        text="cut",
        message={"content": "cut"},
        turn_index=0,
        prompt_tokens=10,
        completion_tokens=5,
        account=WakeAccount(input_tokens=10, output_tokens=5),
    )
    plain = _FailingSession(ContextPolicy.none(), plain_error)
    with pytest.raises(TruncatedReply):
        run_next_event(plain, plain_store, now=T0)
    assert [row["status"] for row in plain_store.read_records()] == [
        "pending",
        "running",
        "failed",
    ]


def test_boot_recovery_of_a_crashed_compact_run_remains_compact(tmp_path):
    store = EventStore(tmp_path / "recover.jsonl")
    store.append(inbound_event(event_id="recover-compact"))
    event, first_running = store.claim_next_pending(now=T0)
    _, retry = store.append_failed_with_retry(
        event=event,
        run_id=first_running["run_id"],
        exc=_window_exhaustion(),
        reason="exhausted_before_request",
    )
    compact_event, compact_running = store.claim_next_pending(now=T0 + timedelta(seconds=1))
    assert compact_event == retry

    recovered = recover_orphaned_running(store)

    assert len(recovered) == 1
    assert recovered[0]["detail"]["compact_context"] is True
    assert recovered[0]["detail"]["retry_of_run"] == first_running["run_id"]
    assert recovered[0]["recovered_from_run_id"] == compact_running["run_id"]


def _position_attempt(house, door, stance, *, at, complete=True):
    store = EventStore(house.config.members[door].events)
    event, running = store.claim_next_pending(now=at)
    wake = WakeContext(
        event_id=event["event_id"],
        run_id=running["run_id"],
        started_at=running["started_at"],
        event=event,
    )
    record_id = uuid4()
    position = record_position(
        house.ledger,
        binding=house.bindings[door],
        wake=wake,
        cycle=1,
        record_id=record_id,
        question_id=house.question["question_id"],
        stance=stance,
        reasons=None,
        now=at,
    )
    if complete:
        store.append_completed(
            event=event,
            run_id=running["run_id"],
            wake_cycle=1,
            result_record_id=record_id,
            response_text="position recorded",
        )
    return position, wake, store


def _fill_other_members(house):
    _position_attempt(house, "b", "assent", at=T0 + timedelta(days=1), complete=True)
    _position_attempt(house, "c", "assent", at=T0 + timedelta(days=1, minutes=1), complete=True)
    _position_attempt(house, "d", "abstain", at=T0 + timedelta(days=1, minutes=2), complete=True)


def _close(house):
    with house.ledger.locked():
        view = reduce(house.ledger.read_unlocked())
        return try_close(
            house.ledger,
            view,
            view.questions[house.question["question_id"]],
            now=CLOSE + GRACE + timedelta(seconds=1),
            actor="window-validation",
        )


@pytest.mark.parametrize("compact_status", ["pending", "running", "completed"])
def test_failed_run_position_caps_after_a_compact_row_without_a_replacement(
    house_factory, compact_status
):
    house = house_factory()
    _, first_wake, store = _position_attempt(
        house,
        "a",
        "assent",
        at=T0 + timedelta(hours=1),
        complete=False,
    )
    _, retry = store.append_failed_with_retry(
        event=first_wake.event,
        run_id=first_wake.run_id,
        exc=_window_exhaustion(),
        reason="exhausted_before_request",
    )
    if compact_status in {"running", "completed"}:
        compact_event, compact_running = store.claim_next_pending(now=T0 + timedelta(hours=2))
        assert compact_event == retry
        if compact_status == "completed":
            store.append_completed(
                event=compact_event,
                run_id=compact_running["run_id"],
                wake_cycle=2,
                result_record_id=uuid4(),
                response_text="completed without a position",
            )
    _fill_other_members(house)

    closing = _close(house)

    assert closing is not None
    assert "a" in closing["tally"]["position_from_failed_wake"]
    assert closing["tally"]["cap"] is not None


def test_later_eligible_position_from_the_same_member_lifts_the_failed_run_cap(house_factory):
    house = house_factory()
    _, first_wake, store = _position_attempt(
        house,
        "a",
        "assent",
        at=T0 + timedelta(hours=1),
        complete=False,
    )
    _, retry = store.append_failed_with_retry(
        event=first_wake.event,
        run_id=first_wake.run_id,
        exc=_window_exhaustion(),
        reason="exhausted_before_request",
    )
    compact_event, compact_running = store.claim_next_pending(now=T0 + timedelta(hours=2))
    compact_wake = WakeContext(
        event_id=compact_event["event_id"],
        run_id=compact_running["run_id"],
        started_at=compact_running["started_at"],
        event=compact_event,
    )
    replacement_record = uuid4()
    record_position(
        house.ledger,
        binding=house.bindings["a"],
        wake=compact_wake,
        cycle=2,
        record_id=replacement_record,
        question_id=house.question["question_id"],
        stance="abstain",
        reasons=["the compact wake reached a later view"],
        now=T0 + timedelta(hours=2),
    )
    store.append_completed(
        event=retry,
        run_id=compact_running["run_id"],
        wake_cycle=2,
        result_record_id=replacement_record,
        response_text="replacement recorded",
    )
    _fill_other_members(house)

    closing = _close(house)

    assert closing is not None
    assert "a" not in closing["tally"]["position_from_failed_wake"]
    assert "a" in closing["tally"]["abstentions"]
    assert not closing["tally"]["cap"]
    active_position = next(
        position
        for position in closing["positions"]
        if position["eligible"] is True and position["record"]["member"] == "door:a"
    )
    assert active_position["record"]["run_id"] == compact_running["run_id"]
    assert closing["tally"]["active"]["a"] == active_position["record"]["position_id"]


def test_recovered_orphan_run_is_not_running_at_cutoff(house_factory):
    house = house_factory()
    store = EventStore(house.config.members["a"].events)
    _, abandoned = store.claim_next_pending(now=T0 + timedelta(hours=1))
    recovered = recover_orphaned_running(store)
    successor, running = store.claim_next_pending(now=T0 + timedelta(hours=2))
    assert successor == recovered[0]
    store.append_completed(
        event=successor,
        run_id=running["run_id"],
        wake_cycle=2,
        result_record_id=uuid4(),
        response_text="recovered",
    )
    _fill_other_members(house)

    closing = _close(house)

    assert closing is not None
    assert abandoned["run_id"] == recovered[0]["recovered_from_run_id"]
    assert "a" not in closing["tally"]["running_at_cutoff"]


def test_apply_context_limit_keeps_tokenizer_policy_on_loss_then_replaces_with_window_aware(
    tmp_path, monkeypatch
):
    old = aware_policy(limit=65_536, invocation_id="old-invocation")
    backend = scripted_backend([], policy=old)
    session, log_path = seeded_session(tmp_path, backend, name="policy-publication")

    def loses_tokenizer(cls, limit, source, base_url, **kwargs):
        return ContextPolicy.for_limit(limit, source)

    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(loses_tokenizer))
    session.apply_context_limit(32_768, "discovered", "lost-tokenizer")

    assert session.context_policy is old
    kept = records(log_path)[-1]
    assert kept["record_type"] == "substrate_observation"
    assert kept["context_policy_kept"] is True

    replacement = aware_policy(limit=32_768, invocation_id="replacement")

    def remains_window_aware(cls, limit, source, base_url, **kwargs):
        return replacement

    monkeypatch.setattr(ContextPolicy, "for_launch", classmethod(remains_window_aware))
    session.apply_context_limit(32_768, "discovered", "replacement")

    assert session.context_policy is replacement
    assert backend.policy is replacement
    published = records(log_path)[-1]
    assert published["record_type"] == "substrate_observation"
    assert published.get("context_policy_kept") is not True
