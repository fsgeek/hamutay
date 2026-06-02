"""Tests for prompt-clarification variant probe."""

from hamutay.eval.state_prompt_variant_probe import (
    PRESERVATION_PREFIX,
    PromptVariantResult,
    VARIANT_PREFIXES,
    _deleted_load_bearing_fields,
    summarize_results,
)


def test_deleted_load_bearing_fields_detects_current_claim_deletion():
    records = [
        {"raw_output": {"response": "ok"}},
        {"raw_output": {"deleted_regions": ["current_claim", "scratch"]}},
    ]

    assert _deleted_load_bearing_fields(records) is True


def test_variant_prefixes_include_activation_and_legacy_alias():
    assert VARIANT_PREFIXES["fixed"] == PRESERVATION_PREFIX
    assert VARIANT_PREFIXES["preservation"] == PRESERVATION_PREFIX
    assert "incomplete cycle" in VARIANT_PREFIXES["activation"]
    assert "deleted_regions" in VARIANT_PREFIXES["combined"]
    assert "incomplete cycle" in VARIANT_PREFIXES["combined"]


def test_summarize_results_groups_by_model_and_variant():
    results = [
        PromptVariantResult(
            model="deepseek",
            variant="current",
            replicate=1,
            log_path="a.jsonl",
            activated=True,
            observed_cycles=5,
            survived_cycles=0,
            completed_cycles=2,
            persistent=False,
            deleted_load_bearing_fields=True,
            final_claim=None,
            final_decision=None,
            scores=[],
            error=None,
        ),
        PromptVariantResult(
            model="deepseek",
            variant="fixed",
            replicate=1,
            log_path="b.jsonl",
            activated=True,
            observed_cycles=5,
            survived_cycles=2,
            completed_cycles=2,
            persistent=True,
            deleted_load_bearing_fields=False,
            final_claim="claim",
            final_decision="revise",
            scores=[],
            error=None,
        ),
    ]

    assert summarize_results(results) == [
        {
            "model": "deepseek",
            "variant": "current",
            "replicates": 1,
            "activated": 1,
            "persistent": 0,
            "deleted_load_bearing_fields": 1,
            "required_events": 2,
            "survived_events": 0,
            "errors": [],
        },
        {
            "model": "deepseek",
            "variant": "fixed",
            "replicates": 1,
            "activated": 1,
            "persistent": 1,
            "deleted_load_bearing_fields": 0,
            "required_events": 2,
            "survived_events": 2,
            "errors": [],
        },
    ]
