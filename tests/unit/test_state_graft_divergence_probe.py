"""Tests for paired graft divergence aggregation."""

from hamutay.eval.state_graft_divergence_probe import (
    GraftBranchResult,
    PairedDivergenceResult,
    _field_divergence,
    summarize_results,
)


def test_field_divergence_ignores_cycle_and_counts_shared_differences():
    left = {
        "cycle": 2,
        "current_claim": "supportive",
        "revision_decision": "revise",
        "evidence_register": [{"a": 1}],
    }
    right = {
        "cycle": 3,
        "current_claim": "disconfirming",
        "revision_decision": "revise",
        "evidence_register": [{"b": 2}],
    }

    shared, divergent = _field_divergence(left, right)

    assert shared == 3
    assert divergent == 2


def test_summarize_results_counts_coherent_divergence():
    branch = GraftBranchResult(
        branch="a",
        log_path="a.jsonl",
        observed_cycles=3,
        survived_cycles=2,
        completed_cycles=2,
        persistent=True,
        final_claim="claim",
        final_decision="revise",
        final_evidence_count=3,
        scores=[],
        error=None,
    )
    result = PairedDivergenceResult(
        model="model-a",
        replicate=1,
        source_log_path="source.jsonl",
        source_activated=True,
        source_survived_cycles=2,
        source_completed_cycles=2,
        source_survived_wake=True,
        branch_a=branch,
        branch_b=branch,
        final_claims_differ=True,
        shared_field_count=4,
        divergent_field_count=2,
        coherent_divergence=True,
        error=None,
    )

    assert summarize_results([result]) == {
        "pairs": 1,
        "source_activated": 1,
        "source_survived_wake": 1,
        "branch_a_persistent": 1,
        "branch_b_persistent": 1,
        "final_claims_differ": 1,
        "coherent_divergence": 1,
        "errors": [],
    }
