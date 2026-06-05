from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import pytest

from hamutay.protocol_recovery import DeterministicProtocolRecoveryBuilder
from hamutay.taste_open import ExchangeResult, OpenTasteSession


FAILED_RESPONSE = """\
I have updated the plan.

### Invalidated Assumptions
1. **Offline storage allowed (encrypted)**: Assumed encrypted local storage was permissible for offline operation. Now invalidated.
   - *Evidence*: Privacy officer's ruling prohibits local storage entirely.

2. **East Clinic participation**: Assumed East Clinic would host a kiosk.
   - *Evidence*: East Clinic withdrew from the pilot.

### New Constraints
- **No local storage**: Documents cannot be stored locally (even encrypted).
- **Replacement site**: East Clinic replaced by West Shelter.
- All other constraints remain (budget <=$18k, no weekend staffing, 4-hour offline operation, no SSN collection).

### Updated Goals
- Preserve resident privacy (updated to enforce **no local storage**).
- Cover **three pilot sites**: North Library, West Shelter, and South Center.

### Next Actions
1. **Confirm West Shelter suitability**:
   - Validate ADA compliance, power access, and cellular signal strength at West Shelter.
2. **Budget update**:
   - Reserve $1,900 for hardware (vs. $2,850 previously), leaving ~$16.1k contingency.

New expected cost: (3 sites - 1 = 2 sites) x $950/site = $1,900 for hardware.
"""


class _SequenceBackend:
    def __init__(self, results: list[ExchangeResult]):
        self._results = list(results)

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor=None,
    ) -> ExchangeResult:
        del model, system, messages, experiment_label, extra_tools, tool_executor
        if not self._results:
            raise AssertionError("sequence backend exhausted")
        return self._results.pop(0)


def _failure_classification() -> dict:
    return {
        "record_type": "protocol_failure",
        "failure_stage": "state_merge",
        "error_type": "ValueError",
        "error": "deleted_regions overlaps updates",
        "deleted_regions": ["assumptions"],
        "updated_regions": ["assumptions"],
        "overlap_keys": ["assumptions"],
    }


def test_deterministic_builder_extracts_candidates_and_warnings():
    builder = DeterministicProtocolRecoveryBuilder()

    artifact = builder.recover(
        cycle=3,
        record_id=UUID("00000000-0000-0000-0000-000000000003"),
        timestamp=datetime(2026, 6, 5, tzinfo=timezone.utc),
        prior_state={"cycle": 2, "assumptions": ["old"]},
        raw_output={
            "response": FAILED_RESPONSE,
            "assumptions": [],
            "deleted_regions": ["assumptions"],
        },
        response_text=FAILED_RESPONSE,
        failure_classification=_failure_classification(),
    )

    rows = artifact["candidate_rows"]
    warnings = artifact["contamination_warnings"]
    by_type = {}
    for row in rows:
        by_type[row["row_type"]] = by_type.get(row["row_type"], 0) + 1

    assert artifact["accepted_state"] is None
    assert artifact["live_policy"] == "strict_reject"
    assert artifact["overlap_keys"] == ["assumptions"]
    assert by_type["invalidated_assumption"] == 2
    assert by_type["constraint"] == 3
    assert by_type["goal"] == 2
    assert by_type["next_action"] == 2
    assert len(warnings) >= 1
    assert all(row["status"] == "candidate" for row in rows + warnings)
    assert all(row["accepted"] is False for row in rows + warnings)
    assert artifact["raw_update_excerpt"]["overlap_values"] == {"assumptions": []}


def test_deterministic_builder_integrates_with_open_taste_session(tmp_path):
    backend = _SequenceBackend([
        ExchangeResult(
            raw_output={
                "response": FAILED_RESPONSE,
                "assumptions": [],
                "deleted_regions": ["assumptions"],
            },
            stop_reason="tool_use",
            input_tokens=11,
            output_tokens=22,
        ),
        ExchangeResult(
            raw_output={"response": "ok", "status_note": "steady"},
            stop_reason="tool_use",
            input_tokens=33,
            output_tokens=44,
        ),
    ])
    log_path = tmp_path / "session.jsonl"
    session = OpenTasteSession(
        backend=backend,
        experiment_label="deterministic_protocol_recovery_builder_test",
        log_path=str(log_path),
        protocol_recovery_builder=DeterministicProtocolRecoveryBuilder(),
    )

    with pytest.raises(ValueError, match="deleted_regions overlaps updates"):
        session.exchange("fail")

    assert session.cycle == 0
    assert session.state is None
    records = [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip()
    ]
    failed = records[0]
    recovery = failed["protocol_recovery"]
    assert recovery["status"] == "success"
    artifact = recovery["artifact"]
    assert artifact["accepted_state"] is None
    assert len(artifact["candidate_rows"]) >= 4
    assert len(artifact["contamination_warnings"]) >= 1
    assert "continuity_curation" not in failed

    assert session.exchange("succeed") == "ok"
    assert session.cycle == 1
    assert session.state == {"cycle": 1, "status_note": "steady"}
