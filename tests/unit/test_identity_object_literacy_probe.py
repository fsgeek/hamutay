"""Tests for identity-object operational literacy scoring."""

from hamutay.eval.identity_object_literacy_probe import (
    LiteracyResult,
    SEED_STATE,
    _cycle_check,
    summarize_results,
)


def test_activate_detects_response_state_mismatch():
    record = {
        "response_text": "Revised in prose only.",
        "raw_output": {"response": "Revised in prose only."},
        "state": dict(SEED_STATE, cycle=1),
    }

    check = _cycle_check("activate", record, dict(SEED_STATE))

    assert check.passed is False
    assert "response_state_mismatch" in check.reasons
    assert "claim_not_changed" in check.reasons


def test_replace_detects_delete_plus_update():
    record = {
        "response_text": "Replaced.",
        "raw_output": {
            "response": "Replaced.",
            "continuity_contract": {
                "replace_me": "new",
                "preserve_me": "stable",
                "version": 1,
            },
            "deleted_regions": ["continuity_contract"],
        },
        "state": dict(
            SEED_STATE,
            continuity_contract={
                "replace_me": "new",
                "preserve_me": "stable",
                "version": 1,
            },
            cycle=2,
        ),
    }

    check = _cycle_check("replace", record, dict(SEED_STATE))

    assert check.passed is False
    assert "delete_update_overlap" in check.reasons
    assert "deleted_load_bearing" in check.reasons
    assert "replace_used_delete" in check.reasons


def test_idle_detects_unnecessary_mutation():
    previous = dict(SEED_STATE, cycle=2)
    record = {
        "response_text": "No change.",
        "raw_output": {"response": "No change.", "revision_decision": "affirm"},
        "state": dict(previous, revision_decision="affirm", cycle=3),
    }

    check = _cycle_check("idle", record, previous)

    assert check.passed is False
    assert "idle_changed_revision_decision" in check.reasons


def test_summarize_results_aggregates_by_model_and_condition():
    results = [
        LiteracyResult(
            model="deepseek",
            condition="thin",
            replicate=1,
            log_path="a.jsonl",
            cycles_observed=2,
            passed_checks=1,
            total_checks=5,
            literacy_score=0.2,
            delete_update_overlap=True,
            deleted_load_bearing_fields=True,
            response_state_mismatch=True,
            checks=[],
            error=None,
        ),
        LiteracyResult(
            model="deepseek",
            condition="thin",
            replicate=2,
            log_path="b.jsonl",
            cycles_observed=5,
            passed_checks=5,
            total_checks=5,
            literacy_score=1.0,
            delete_update_overlap=False,
            deleted_load_bearing_fields=False,
            response_state_mismatch=False,
            checks=[],
            error=None,
        ),
    ]

    assert summarize_results(results) == [
        {
            "model": "deepseek",
            "condition": "thin",
            "replicates": 2,
            "mean_literacy_score": 0.6,
            "passed_runs": 1,
            "delete_update_overlap": 1,
            "deleted_load_bearing_fields": 1,
            "response_state_mismatch": 1,
            "errors": [],
        }
    ]
