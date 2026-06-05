"""Tests for identity-object graft probe aggregation."""

from hamutay.eval.state_graft_probe import GraftProbeResult, summarize_results


def test_summarize_results_counts_source_and_graft_survival():
    results = [
        GraftProbeResult(
            model="model-a",
            replicate=1,
            source_log_path="source-a.jsonl",
            graft_log_path="graft-a.jsonl",
            source_observed_cycles=4,
            source_activated=True,
            source_survived_cycles=2,
            source_completed_cycles=2,
            source_survived_wake=True,
            graft_attempted=True,
            graft_observed_cycles=3,
            graft_survived_cycles=2,
            graft_completed_cycles=2,
            graft_persistent=True,
            source_scores=[],
            graft_scores=[],
            error=None,
        ),
        GraftProbeResult(
            model="model-a",
            replicate=2,
            source_log_path="source-b.jsonl",
            graft_log_path=None,
            source_observed_cycles=2,
            source_activated=False,
            source_survived_cycles=0,
            source_completed_cycles=0,
            source_survived_wake=False,
            graft_attempted=False,
            graft_observed_cycles=0,
            graft_survived_cycles=0,
            graft_completed_cycles=0,
            graft_persistent=False,
            source_scores=[],
            graft_scores=[],
            error="RuntimeError: provider failed",
        ),
    ]

    assert summarize_results(results) == {
        "seedlings": 2,
        "source_activated": 1,
        "source_survived_wake": 1,
        "graft_attempted": 1,
        "graft_persistent": 1,
        "source_required_events": 2,
        "source_survived_events": 2,
        "graft_required_events": 2,
        "graft_survived_events": 2,
        "errors": ["RuntimeError: provider failed"],
    }
