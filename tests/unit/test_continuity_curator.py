from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from hamutay.continuity_curator import (
    ClaimTableContinuityCurator,
    ModelContinuityCurator,
)
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


def test_claim_table_curator_renders_accepted_rows_deterministically():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": "claim rows produced",
                "claims": [
                    {
                        "claim": "West Shelter replaced East Clinic.",
                        "status": "supported",
                        "source_cycle": "3",
                        "support": "cycle 3 contradictory update",
                    },
                    {
                        "claim": "Local document storage is prohibited.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "privacy officer ruling",
                    },
                    {
                        "claim": "Use rugged tablets.",
                        "status": "asserted",
                        "source_cycle": 4,
                        "support": "not supported",
                    },
                ],
            },
            input_tokens=13,
            output_tokens=8,
        )
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        max_summary_chars=1200,
    )

    artifact = curator.curate(
        cycle=3,
        record_id=UUID("00000000-0000-0000-0000-000000000003"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state={"site": "East Clinic"},
        raw_output={"response": "main"},
        response_text="main",
        state={"site": "West Shelter"},
    )

    assert artifact["curator_type"] == "claim_table_model"
    assert artifact["summary_source"] == "deterministic_claim_table_full"
    assert artifact["renderer"] == "full"
    assert artifact["accepted_claim_rows"] == 2
    assert artifact["rejected_claim_rows"] == 1
    assert "[supported c3] West Shelter replaced East Clinic." in artifact["summary"]
    assert "[invalidated c3] Local document storage is prohibited." in (
        artifact["summary"]
    )
    assert "rugged tablets" not in artifact["summary"].lower()
    assert artifact["usage"]["output_tokens"] == 8
    assert "bounded claim" in backend.calls[0]["messages"][0]["content"]


def test_claim_table_delta_renderer_selects_new_and_priority_rows():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": "cycle 1",
                "claims": [
                    {
                        "claim": "North Library remains active.",
                        "status": "supported",
                        "source_cycle": 2,
                        "support": "task",
                    },
                    {
                        "claim": "East Clinic is replaced by West Shelter.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "site update",
                    },
                ],
            }
        ),
        ExchangeResult(
            raw_output={
                "response": "cycle 2",
                "claims": [
                    {
                        "claim": "North Library remains active.",
                        "status": "supported",
                        "source_cycle": 2,
                        "support": "task",
                    },
                    {
                        "claim": "East Clinic is replaced by West Shelter.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "site update",
                    },
                    {
                        "claim": "Local document storage is prohibited.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "privacy update",
                    },
                    {
                        "claim": "Vendor availability remains open.",
                        "status": "open",
                        "source_cycle": 4,
                        "support": "open question",
                    },
                ],
            }
        ),
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        renderer="delta",
        delta_max_rows=3,
        max_summary_chars=800,
    )
    common = {
        "record_id": UUID("00000000-0000-0000-0000-000000000003"),
        "timestamp": datetime(2026, 6, 5, tzinfo=timezone.utc),
        "prior_state": None,
        "raw_output": {"response": "main"},
        "response_text": "main",
        "state": {"cycle": 1},
    }

    first = curator.curate(cycle=3, **common)
    second = curator.curate(cycle=4, **common)

    assert first["summary_source"] == "deterministic_claim_table_delta"
    assert first["selected_delta_row_count"] == 2
    assert "new_or_changed" in first["summary"]
    assert second["selected_delta_row_count"] == 3
    assert second["omitted_delta_row_count"] >= 1
    assert "Local document storage is prohibited." in second["summary"]
    assert "East Clinic is replaced by West Shelter." in second["summary"]
    assert "North Library remains active." in second["summary"]


def test_claim_table_guardrail_delta_reserves_epistemic_guardrails():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": "cycle 1",
                "claims": [
                    {
                        "claim": "Local document storage is prohibited.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "privacy officer ruling",
                    },
                    {
                        "claim": "East Clinic is replaced by West Shelter.",
                        "status": "supported",
                        "source_cycle": 3,
                        "support": "site substitution update",
                    },
                    {
                        "claim": "Budget remains at or below $18,000.",
                        "status": "supported",
                        "source_cycle": 2,
                        "support": "task constraint",
                    },
                ],
            }
        ),
        ExchangeResult(
            raw_output={
                "response": "cycle 2",
                "claims": [
                    {
                        "claim": "Local document storage is prohibited.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "privacy officer ruling",
                    },
                    {
                        "claim": "East Clinic is replaced by West Shelter.",
                        "status": "supported",
                        "source_cycle": 3,
                        "support": "site substitution update",
                    },
                    {
                        "claim": "Budget remains at or below $18,000.",
                        "status": "supported",
                        "source_cycle": 2,
                        "support": "task constraint",
                    },
                    {
                        "claim": "Use a vendor-hosted upload session.",
                        "status": "supported",
                        "source_cycle": 4,
                        "support": "current plan",
                    },
                    {
                        "claim": "Vendor capacity remains uncertain.",
                        "status": "uncertain",
                        "source_cycle": 4,
                        "support": "not yet confirmed",
                    },
                ],
            }
        ),
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        renderer="guardrail_delta",
        delta_max_rows=4,
        guardrail_stable_invalidated_cap=1,
        max_summary_chars=900,
    )
    common = {
        "record_id": UUID("00000000-0000-0000-0000-000000000004"),
        "timestamp": datetime(2026, 6, 5, tzinfo=timezone.utc),
        "prior_state": None,
        "raw_output": {"response": "main"},
        "response_text": "main",
        "state": {"cycle": 4},
    }

    first = curator.curate(cycle=3, **common)
    second = curator.curate(cycle=4, **common)

    assert first["summary_source"] == "deterministic_claim_table_guardrail_delta"
    assert "hard_constraint_no_local_document_storage" in second["summary"]
    assert "hard_constraint_west_shelter_replaces_east_clinic" in second["summary"]
    assert "hard_constraint_budget_18000" in second["summary"]
    assert "Use a vendor-hosted upload session." in second["summary"]
    assert "Vendor capacity remains uncertain." not in second["summary"]
    assert second["selected_delta_row_count"] == 4
    assert second["omitted_delta_row_count"] >= 1
    reasons = {
        row["render_reason"] for row in second["selected_delta_rows"]
    }
    assert "hard_constraint_no_local_document_storage" in reasons
    assert "new_or_changed_supported" in reasons


def test_claim_table_typed_guardrail_delta_logs_compact_tokens():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": "cycle 1",
                "claims": [
                    {
                        "claim": "Local document storage is prohibited.",
                        "status": "invalidated",
                        "source_cycle": 3,
                        "support": "privacy officer ruling",
                    },
                    {
                        "claim": "East Clinic is replaced by West Shelter.",
                        "status": "supported",
                        "source_cycle": 3,
                        "support": "site substitution update",
                    },
                    {
                        "claim": "Budget remains at or below $18,000.",
                        "status": "supported",
                        "source_cycle": 2,
                        "support": "task constraint",
                    },
                    {
                        "claim": "Use a vendor-hosted upload session.",
                        "status": "supported",
                        "source_cycle": 4,
                        "support": "current plan",
                    },
                ],
            }
        )
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        renderer="typed_guardrail_delta",
        delta_max_rows=4,
        max_summary_chars=800,
    )

    artifact = curator.curate(
        cycle=4,
        record_id=UUID("00000000-0000-0000-0000-000000000004"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state=None,
        raw_output={"response": "main"},
        response_text="main",
        state={"cycle": 4},
    )

    assert artifact["summary_source"] == (
        "deterministic_claim_table_typed_guardrail_delta"
    )
    assert "blocked:local_document_storage" in artifact["summary"]
    assert "site_replaced:east_clinic->west_shelter" in artifact["summary"]
    assert "constraint:budget<=18000" in artifact["summary"]
    assert "Local document storage is prohibited." not in artifact["summary"]
    tokens = {
        row.get("typed_token")
        for row in artifact["selected_delta_rows"]
        if row.get("typed_token")
    }
    assert tokens == {
        "blocked:local_document_storage",
        "site_replaced:east_clinic->west_shelter",
        "constraint:budget<=18000",
    }


def test_claim_table_curator_rejects_missing_claims_without_prose_fallback():
    backend = _FakeBackend([
        ExchangeResult(raw_output={"response": "free prose instead"})
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        max_summary_chars=1200,
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

    assert artifact["summary"] == "(no valid curator claim rows)"
    assert artifact["accepted_claim_rows"] == 0
    assert artifact["rejected_claim_rows"] == 1
    assert artifact["summary_truncated"] is False
    assert artifact["protocol_recovery_used"] is False


def test_claim_table_curator_can_log_response_object_recovery():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": {
                    "claims": [
                        {
                            "claim": "Offline document storage is prohibited.",
                            "status": "supported",
                            "source_cycle": 3,
                            "support": "privacy officer ruling",
                        }
                    ]
                }
            }
        )
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        recover_response_claims=True,
    )

    artifact = curator.curate(
        cycle=3,
        record_id=UUID("00000000-0000-0000-0000-000000000003"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state=None,
        raw_output={"response": "main"},
        response_text="main",
        state={"cycle": 3},
    )

    assert artifact["accepted_claim_rows"] == 1
    assert artifact["protocol_recovery_used"] is True
    assert artifact["protocol_recovery_source"] == "response_object_claims"
    assert artifact["recovered_claim_rows"] == 1
    assert "Offline document storage is prohibited." in artifact["summary"]


def test_claim_table_curator_can_log_response_string_recovery():
    backend = _FakeBackend([
        ExchangeResult(
            raw_output={
                "response": json.dumps(
                    {
                        "claims": [
                            {
                                "claim": "West Shelter replaced East Clinic.",
                                "status": "supported",
                                "source_cycle": 3,
                                "support": "site update",
                            }
                        ]
                    }
                )
            }
        )
    ])
    curator = ClaimTableContinuityCurator(
        backend=backend,
        model="curator-model",
        recover_response_claims=True,
    )

    artifact = curator.curate(
        cycle=3,
        record_id=UUID("00000000-0000-0000-0000-000000000003"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state=None,
        raw_output={"response": "main"},
        response_text="main",
        state={"cycle": 3},
    )

    assert artifact["accepted_claim_rows"] == 1
    assert artifact["protocol_recovery_used"] is True
    assert artifact["protocol_recovery_source"] == "response_stringified_json_claims"
    assert artifact["recovered_claim_rows"] == 1
