"""Tests for identity-object persistence probe scoring."""

from hamutay.eval.state_persistence_probe import (
    CyclePersistenceScore,
    SeedlingPersistenceResult,
    _activation_from_record,
    _score_continuation_cycle,
    summarize_results,
)


def test_score_continuation_cycle_detects_durable_state_use():
    previous_state = {
        "revision_decision": "revise",
        "current_claim": "Prior claim.",
        "evidence_register": [{"kind": "baseline"}],
    }
    record = {
        "cycle": 3,
        "response_text": "I revise the claim.",
        "state": {
            "revision_decision": "revise",
            "current_claim": "Narrower continuation claim.",
            "evidence_register": [
                {"kind": "baseline"},
                {"kind": "topic_shift"},
            ],
        },
    }

    score = _score_continuation_cycle(
        stage="topic_shift",
        required_update=True,
        record=record,
        previous_state=previous_state,
    )

    assert score.durable_state_use is True
    assert score.passed is True
    assert score.evidence_changed is True
    assert score.state_changed is True
    assert score.response_claimed_revision is True


def test_activation_accepts_open_revision_label():
    record = {
        "response_text": "Revised.",
        "state": {
            "revision_decision": "revised",
            "current_claim": "Narrower claim.",
            "evidence_register": [
                {"kind": "baseline"},
                {"kind": "counterevidence"},
            ],
        },
    }

    activated, response_claimed = _activation_from_record(record)

    assert activated is True
    assert response_claimed is True


def test_score_continuation_cycle_rejects_response_only_revision():
    previous_state = {
        "revision_decision": "revise",
        "current_claim": "Prior claim.",
        "evidence_register": [{"kind": "baseline"}],
    }
    record = {
        "cycle": 3,
        "response_text": "I revise the claim.",
        "state": dict(previous_state),
    }

    score = _score_continuation_cycle(
        stage="topic_shift",
        required_update=True,
        record=record,
        previous_state=previous_state,
    )

    assert score.durable_state_use is False
    assert score.passed is False
    assert score.evidence_changed is False
    assert score.state_changed is False
    assert score.response_claimed_revision is True


def test_score_continuation_cycle_accepts_open_decision_label():
    previous_state = {
        "revision_decision": "revise",
        "current_claim": "Prior claim.",
        "evidence_register": [{"kind": "baseline"}],
    }
    record = {
        "cycle": 4,
        "response_text": "Adopted a narrower claim.",
        "state": {
            "revision_decision": "adopted",
            "current_claim": "Narrower claim.",
            "evidence_register": [{"kind": "baseline"}],
        },
    }

    score = _score_continuation_cycle(
        stage="wake_delay",
        required_update=True,
        record=record,
        previous_state=previous_state,
    )

    assert score.state_changed is True
    assert score.durable_state_use is True
    assert score.passed is True


def test_idle_continuation_cycle_allows_no_state_change():
    previous_state = {
        "revision_decision": "revise",
        "current_claim": "Prior claim.",
        "evidence_register": [{"kind": "baseline"}],
    }
    record = {
        "cycle": 3,
        "response_text": "No new evidence arrived.",
        "state": dict(previous_state),
    }

    score = _score_continuation_cycle(
        stage="idle",
        required_update=False,
        record=record,
        previous_state=previous_state,
    )

    assert score.durable_state_use is False
    assert score.passed is True


def test_summarize_results_counts_culled_and_persistent_seedlings():
    cycle_score = CyclePersistenceScore(
        stage="topic_shift",
        cycle=3,
        required_update=True,
        revision_decision="revise",
        current_claim="Narrower claim.",
        evidence_count=2,
        previous_evidence_count=1,
        evidence_changed=True,
        state_changed=True,
        durable_state_use=True,
        passed=True,
        response_claimed_revision=True,
        response_snippet="",
    )
    results = [
        SeedlingPersistenceResult(
            model="model-a",
            condition="content_plus_behavior_seed",
            replicate=1,
            log_path="a.jsonl",
            observed_cycles=3,
            activated=True,
            activation_response_claimed_revision=True,
            survived_cycles=1,
            completed_cycles=1,
            persistent=True,
            cycle_scores=[cycle_score],
            error=None,
        ),
        SeedlingPersistenceResult(
            model="model-a",
            condition="content_plus_behavior_seed",
            replicate=2,
            log_path="b.jsonl",
            observed_cycles=2,
            activated=False,
            activation_response_claimed_revision=True,
            survived_cycles=0,
            completed_cycles=0,
            persistent=False,
            cycle_scores=[],
            error=None,
        ),
    ]

    summary = summarize_results(results)

    assert summary == [
        {
            "model": "model-a",
            "condition": "content_plus_behavior_seed",
            "seedlings": 2,
            "activated_seedlings": 1,
            "persistent_seedlings": 1,
            "continuation_cycles": 1,
            "survived_continuation_cycles": 1,
        }
    ]
