"""Tests for the identity-object activation probe scorer."""

import json

from hamutay.eval.state_activation_probe import BASE_CLAIM, _score


def _write_log(path, final_raw, final_state):
    records = [
        {
            "cycle": 1,
            "raw_output": {"response": "seed"},
            "response_text": "seed",
            "state": {"current_claim": BASE_CLAIM},
        },
        {
            "cycle": 2,
            "raw_output": final_raw,
            "response_text": final_raw.get("response", ""),
            "state": final_state,
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n")


def test_score_detects_durable_revision(tmp_path):
    path = tmp_path / "run.jsonl"
    _write_log(
        path,
        {
            "response": "I revise the claim.",
            "revision_decision": "revise",
            "current_claim": "Narrower claim.",
            "evidence_register": [{"a": 1}, {"b": 2}],
        },
        {
            "revision_decision": "revise",
            "current_claim": "Narrower claim.",
            "evidence_register": [{"a": 1}, {"b": 2}],
        },
    )

    result = _score("test", path)

    assert result.durable_revision is True
    assert result.response_claimed_revision is True


def test_score_rejects_response_only_revision(tmp_path):
    path = tmp_path / "run.jsonl"
    _write_log(
        path,
        {"response": "I revise the claim."},
        {
            "revision_decision": "initialize",
            "current_claim": BASE_CLAIM,
            "evidence_register": [{"a": 1}],
        },
    )

    result = _score("test", path)

    assert result.durable_revision is False
    assert result.response_claimed_revision is True


def test_score_accepts_mapping_evidence_register(tmp_path):
    path = tmp_path / "run.jsonl"
    _write_log(
        path,
        {
            "response": "I revise the claim.",
            "revision_decision": "revise",
            "current_claim": "Narrower claim.",
            "evidence_register": {
                "baseline": "initial",
                "counterevidence": "new",
            },
        },
        {
            "revision_decision": "revise",
            "current_claim": "Narrower claim.",
            "evidence_register": {
                "baseline": "initial",
                "counterevidence": "new",
            },
        },
    )

    result = _score("test", path)

    assert result.evidence_count == 2
    assert result.durable_revision is True
