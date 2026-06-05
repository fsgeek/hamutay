from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from hamutay.continuity_curator import ModelContinuityCurator
from hamutay.taste_open import ExchangeResult, OpenTasteSession


class _FakeBackend:
    def __init__(self, results: list[ExchangeResult]):
        self._results = list(results)
        self.calls: list[dict] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ):
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "experiment_label": experiment_label,
                "extra_tools": extra_tools,
                "tool_executor": tool_executor,
            }
        )
        if not self._results:
            raise AssertionError("fake backend exhausted")
        return self._results.pop(0)


def test_model_curator_extracts_summary_and_usage():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": "internal response",
                "summary": "Keep the West Shelter substitution.",
                "supported_facts": ["West Shelter replaced East Clinic."],
                "uncertain_claims": ["vendor capacity is unresolved"],
                "invalidated_assumptions": ["local document storage"],
                "curator_notes": ["compact"],
            },
            input_tokens=11,
            output_tokens=7,
        )
    ])
    curator = ModelContinuityCurator(
        backend=backend,
        model="curator-model",
        experiment_label="curator-test",
    )

    artifact = curator.curate(
        cycle=2,
        record_id=UUID("00000000-0000-0000-0000-000000000002"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state={"task": "old"},
        raw_output={"response": "main", "task": "new"},
        response_text="main",
        state={"task": "new"},
    )

    assert artifact["curator_type"] == "model"
    assert artifact["model"] == "curator-model"
    assert artifact["summary"] == "Keep the West Shelter substitution."
    assert artifact["summary_source"] == "summary"
    assert artifact["summary_truncated"] is False
    assert artifact["supported_facts"] == ["West Shelter replaced East Clinic."]
    assert artifact["usage"]["input_tokens"] == 11
    assert backend.calls[0]["experiment_label"] == "curator-test"
    assert "You are a continuity curator" in backend.calls[0]["system"]
    assert "merged_state" in backend.calls[0]["messages"][0]["content"]


def test_model_curator_uses_response_fallback_and_marks_truncation():
    backend = _FakeBackend([
        ExchangeResult(raw_output={"response": "abcdefghi"})
    ])
    curator = ModelContinuityCurator(
        backend=backend,
        model="curator-model",
        max_summary_chars=5,
    )

    artifact = curator.curate(
        cycle=1,
        record_id=UUID("00000000-0000-0000-0000-000000000001"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state=None,
        raw_output={"response": "main"},
        response_text="main",
        state={"cycle": 1},
    )

    assert artifact["summary"] == "abcde"
    assert artifact["summary_source"] == "response"
    assert artifact["summary_chars"] == 5
    assert artifact["summary_truncated"] is True


def test_model_curator_integrates_with_open_taste_session(tmp_path):
    backend = _FakeBackend([
        ExchangeResult(raw_output={"response": "first", "status": "ready"}),
        ExchangeResult(
            raw_output={
                "response": "curator internal",
                "summary": "Carry status=ready.",
            }
        ),
        ExchangeResult(raw_output={"response": "second"}),
        ExchangeResult(
            raw_output={
                "response": "curator internal",
                "summary": "Carry status=ready and cycle 2.",
            }
        ),
    ])
    curator = ModelContinuityCurator(backend=backend, model="curator-model")
    log_path = tmp_path / "session.jsonl"
    session = OpenTasteSession(
        model="main-model",
        backend=backend,
        log_path=str(log_path),
        project_root=tmp_path,
        continuity_curator=curator,
    )

    assert session.exchange("seed") == "first"
    assert session.exchange("resume") == "second"

    records = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    assert records[0]["state"]["status"] == "ready"
    assert records[0]["continuity_curation"]["status"] == "success"
    assert records[0]["continuity_curation"]["summary"] == "Carry status=ready."
    assert records[1]["curator_context_injection"]["summary"] == (
        "Carry status=ready."
    )
    assert "Continuity curator summary" in backend.calls[2]["system"]
    assert "Carry status=ready." in backend.calls[2]["system"]
    assert backend.calls[0]["model"] == "main-model"
    assert backend.calls[1]["model"] == "curator-model"
    assert backend.calls[2]["model"] == "main-model"
    assert "continuity_curation" not in records[0]["state"]
