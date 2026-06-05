"""Tests for cross-model graft probe aggregation."""

from hamutay.eval.state_cross_model_graft_probe import (
    CrossModelGraftResult,
    _records_deleted_fields,
    summarize_results,
)


def test_records_deleted_fields_detects_deleted_regions():
    assert _records_deleted_fields([
        {"raw_output": {"response": "ok"}},
        {"raw_output": {"deleted_regions": ["current_claim"]}},
    ])


def test_summarize_results_groups_by_source_graft_and_variant():
    results = [
        CrossModelGraftResult(
            source_model="kimi",
            graft_model="deepseek",
            variant="standard",
            replicate=1,
            source_log_path="source.jsonl",
            graft_log_path="graft.jsonl",
            source_activated=True,
            source_survived_cycles=2,
            source_completed_cycles=2,
            source_survived_wake=True,
            graft_attempted=True,
            graft_observed_cycles=3,
            graft_survived_cycles=1,
            graft_completed_cycles=2,
            graft_persistent=False,
            graft_deleted_fields=True,
            final_claim="claim",
            final_decision="revise",
            graft_scores=[],
            error=None,
        ),
        CrossModelGraftResult(
            source_model="kimi",
            graft_model="deepseek",
            variant="standard",
            replicate=2,
            source_log_path="source2.jsonl",
            graft_log_path=None,
            source_activated=True,
            source_survived_cycles=0,
            source_completed_cycles=0,
            source_survived_wake=False,
            graft_attempted=False,
            graft_observed_cycles=0,
            graft_survived_cycles=0,
            graft_completed_cycles=0,
            graft_persistent=False,
            graft_deleted_fields=False,
            final_claim=None,
            final_decision=None,
            graft_scores=[],
            error="RuntimeError: failed",
        ),
    ]

    assert summarize_results(results) == [
        {
            "source_model": "kimi",
            "graft_model": "deepseek",
            "variant": "standard",
            "replicates": 2,
            "source_survived_wake": 1,
            "graft_attempted": 1,
            "graft_persistent": 0,
            "graft_deleted_fields": 1,
            "graft_required_events": 2,
            "graft_survived_events": 1,
            "errors": ["RuntimeError: failed"],
        }
    ]
