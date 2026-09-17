from __future__ import annotations

import copy
import json
from uuid import uuid4

import pytest

from hamutay.events import EventStore, build_event_envelope
from hamutay.window import TruncatedReply

from .conftest import (
    aware_policy,
    inbound_event,
    records,
    scripted_backend,
    seeded_session,
    tool_call,
    turn,
)


@pytest.mark.parametrize(
    ("wake_mode", "session_wake_mode"),
    [("natural", "natural"), ("terminal", "terminal")],
    ids=["natural-path", "multi-turn-path"],
)
def test_length_finish_records_the_truncated_turn_after_accounting_but_not_as_interim_text(
    tmp_path, wake_mode, session_wake_mode
):
    backend = scripted_backend(
        [
            turn(
                "earlier-text",
                tool_calls=[tool_call("clock", {})],
                prompt_tokens=101,
                completion_tokens=11,
            ),
            turn(
                "cut-content",
                finish="length",
                prompt_tokens=202,
                completion_tokens=22,
                reasoning_content="cut-reasoning",
            ),
        ],
        counts=[101, 202],
        policy=aware_policy(),
        wake_mode=wake_mode,
    )
    session, log_path = seeded_session(
        tmp_path,
        backend,
        name=f"truncated-{wake_mode}",
        wake_mode=session_wake_mode,
    )

    with pytest.raises(TruncatedReply) as raised:
        session.exchange("perform a two-turn wake")

    error = raised.value
    assert error.account.input_tokens == 303
    assert error.account.output_tokens == 33
    assert error.account.interim_text == ["earlier-text"]
    assert error.text.startswith("cut-content")
    assert error.text.endswith("cut-reasoning")

    failed = records(log_path)[-1]
    classification = failed["failure_classification"]
    truncated = classification["truncated_reply"]
    assert classification["error_type"] == "TruncatedReply"
    assert truncated["text"] == error.text
    assert truncated["message"]["content"] == "cut-content"
    assert truncated["message"]["reasoning_content"] == "cut-reasoning"
    assert truncated["prompt_tokens"] == 202
    assert truncated["completion_tokens"] == 22
    assert truncated["trusted"] is False
    assert failed["interim_text"] == ["earlier-text"]
    assert "cut-content" not in json.dumps(failed["interim_text"])
    assert failed["usage"]["input_tokens"] == 303
    assert failed["usage"]["output_tokens"] == 33
    assert failed["usage"]["stop_reason"] == "max_tokens"


def test_window_envelope_is_a_non_mutating_typed_projection_but_store_keeps_full_results(tmp_path):
    event = inbound_event(event_id="envelope-event")
    context_results = [
        {
            "request": {"tool": "recall", "cycle": 11},
            "result": {
                "cycle": 11,
                "content": {
                    "large": "x" * 5_000,
                    "_activity_log": [
                        {
                            "cycle": 11,
                            "timestamp": "2026-09-17T00:00:00+00:00",
                            "tool": "read",
                            "reason": "validation",
                            "result_summary": "large result",
                            "parameters": {"path": "secretly-large"},
                        }
                    ],
                },
            },
        }
    ]
    original_event = copy.deepcopy(event)
    original_results = copy.deepcopy(context_results)
    original_result_identity = id(context_results[0]["result"])

    envelope = build_event_envelope(
        event,
        context_results,
        "run-envelope",
        policy=aware_policy(),
        cap_chars=512,
    )

    projected = json.loads(envelope)["context_results"][0]["result"]
    assert projected["truncated"] is True
    assert projected["why"] == "context result cap"
    assert projected["chars"] > projected["chars_kept"] == 512
    assert len(projected["head"]) == 512
    assert event == original_event
    assert context_results == original_results
    assert id(context_results[0]["result"]) == original_result_identity

    store = EventStore(tmp_path / "events.jsonl")
    completed = store.append_completed(
        event=event,
        run_id="run-envelope",
        wake_cycle=2,
        result_record_id=uuid4(),
        response_text="done",
        context_results=context_results,
    )
    saved = completed["context_results"][0]["result"]
    assert saved["content"]["large"] == "x" * 5_000
    assert saved["content"]["_activity_log"][0]["parameters"] == {
        "path": "secretly-large"
    }


def test_render_envelope_halves_the_cap_until_the_scripted_count_is_at_most_half_the_limit(
    tmp_path,
):
    backend = scripted_backend(
        [turn("admitted", prompt_tokens=30_000)],
        counts=[40_000, 30_000],
        policy=aware_policy(),
    )
    session, log_path = seeded_session(tmp_path, backend, name="admission")
    caps: list[int | None] = []

    def render_envelope(cap):
        caps.append(cap)
        return json.dumps({"cap": cap, "context_results": [{"result": "x" * max(cap or 0, 1)}]})

    assert session.exchange("unused", render_envelope=render_envelope) == "admitted"

    assert caps[:2] == [32_768, 16_384]
    admission = records(log_path)[-1]["admission"]
    assert admission == {
        "passes": 2,
        "final_cap": 16_384,
        "prompt_tokens": 30_000,
        "over_target": False,
        "envelope_exhausted": False,
    }
    assert backend.payloads[0]["messages"][-1]["content"] == render_envelope(16_384)


def test_compact_exchange_starts_admission_at_metadata_only_cap_zero(tmp_path):
    backend = scripted_backend(
        [turn("compact", prompt_tokens=100)],
        counts=[100],
        policy=aware_policy(),
    )
    session, log_path = seeded_session(tmp_path, backend, name="compact")
    caps: list[int | None] = []

    def render_envelope(cap):
        caps.append(cap)
        return json.dumps({"cap": cap})

    assert session.exchange("unused", render_envelope=render_envelope, compact=True) == "compact"

    assert caps[0] == 0
    admission = records(log_path)[-1]["admission"]
    assert admission["passes"] == 1
    assert admission["final_cap"] == 0
    assert admission["envelope_exhausted"] is True
