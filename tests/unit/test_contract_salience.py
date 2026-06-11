from hamutay.memory.contract_salience import (
    MODEL_SET,
    PROMPT_CONDITIONS,
    assess_cross_model_salience,
    budget_manifest,
    cross_model_matrix,
    failure_taxonomy,
    render_analysis,
    summarize_results,
    write_preregistration_artifacts,
)


def test_cross_model_matrix_is_fixed_and_budgeted():
    matrix = cross_model_matrix()
    budget = budget_manifest()

    assert len(MODEL_SET) == 4
    assert len(PROMPT_CONDITIONS) == 2
    assert matrix["live_calls_per_condition"] == 3
    assert len(matrix["conditions"]) == 8
    assert budget["max_live_calls"] == 24
    assert budget["max_estimated_cost_usd"] == 2.0
    assert budget["max_output_tokens_per_call"] is None
    assert "No artificial per-call output cap" in budget["output_cap_policy"]
    assert {condition["model_id"] for condition in matrix["conditions"]} == {
        "deepseek/deepseek-v4-pro",
        "moonshotai/kimi-k2.6",
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-5.1",
    }
    assert {condition["prompt_condition"] for condition in matrix["conditions"]} == {
        "original_strict",
        "example_strict",
    }


def test_failure_taxonomy_includes_cross_model_layers():
    taxonomy = failure_taxonomy()
    entries = {(entry["layer"], entry["code"]) for entry in taxonomy["entries"]}

    assert (
        "model_family",
        "model_specific_contract_salience_boundary",
    ) in entries
    assert (
        "prompt_contract",
        "cross_model_contract_salience_boundary",
    ) in entries


def test_preregistration_artifact_writer_is_no_live(tmp_path):
    result = write_preregistration_artifacts(tmp_path)

    assert result["live_model_calls"] is False
    assert set(result["artifacts"]) == {
        "budget.json",
        "failure_taxonomy.json",
        "matrix.json",
        "prompt_variants.json",
    }
    assert (tmp_path / "matrix.json").exists()


def test_assessment_detects_deepseek_specific_boundary():
    by_model = {
        "deepseek_v4_pro": _model_bucket(original=0, example=3, original_relaxed=3),
        "kimi_k2_6": _model_bucket(original=3, example=3),
        "claude_sonnet_4_6": _model_bucket(original=3, example=3),
        "gpt_5_1": _model_bucket(original=3, example=3),
    }

    assessment = assess_cross_model_salience(
        by_model,
        source_deepseek_reference={
            "original_strict_pass_count": 0,
            "example_strict_pass_count": 3,
        },
    )

    assert assessment["primary_pattern"] == (
        "deepseek_specific_contract_salience_boundary"
    )
    assert assessment["deepseek_specific_boundary"] is True
    assert assessment["cross_model_contract_salience"] is False


def test_assessment_detects_cross_model_contract_salience():
    by_model = {
        "deepseek_v4_pro": _model_bucket(original=0, example=3, original_relaxed=3),
        "kimi_k2_6": _model_bucket(original=1, example=3, original_relaxed=2),
        "claude_sonnet_4_6": _model_bucket(original=3, example=3),
        "gpt_5_1": _model_bucket(original=3, example=3),
    }

    assessment = assess_cross_model_salience(
        by_model,
        source_deepseek_reference={
            "original_strict_pass_count": 0,
            "example_strict_pass_count": 3,
        },
    )

    assert assessment["primary_pattern"] == "cross_model_contract_salience_boundary"
    assert assessment["deepseek_specific_boundary"] is False
    assert assessment["cross_model_contract_salience"] is True


def test_assessment_uses_source_deepseek_when_current_deepseek_unscoreable():
    by_model = {
        "deepseek_v4_pro": _model_bucket(
            original=0,
            example=0,
            original_scorable=0,
            example_scorable=0,
        ),
        "gpt_5_1": _model_bucket(original=0, example=3, original_relaxed=3),
    }
    source = {
        "original_strict_pass_count": 0,
        "example_strict_pass_count": 3,
    }

    assessment = assess_cross_model_salience(
        by_model,
        source_deepseek_reference=source,
    )

    assert assessment["source_deepseek_reference_used"] is True
    assert assessment["primary_pattern"] == "cross_model_contract_salience_boundary"
    assert assessment["models_with_example_rescue"] == ["gpt_5_1"]
    assert assessment["source_reference_models_with_example_rescue"] == [
        "deepseek_v4_pro"
    ]
    assert assessment["models_with_unscoreable_original"] == ["deepseek_v4_pro"]


def test_summary_counts_model_prompt_rows_and_renders_analysis(tmp_path):
    rows = [
        _row("deepseek_v4_pro", "deepseek/deepseek-v4-pro", "original_strict", False),
        _row("deepseek_v4_pro", "deepseek/deepseek-v4-pro", "original_strict", False),
        _row("deepseek_v4_pro", "deepseek/deepseek-v4-pro", "original_strict", False),
        _row("deepseek_v4_pro", "deepseek/deepseek-v4-pro", "example_strict", True),
        _row("deepseek_v4_pro", "deepseek/deepseek-v4-pro", "example_strict", True),
        _row("deepseek_v4_pro", "deepseek/deepseek-v4-pro", "example_strict", True),
    ]

    summary = summarize_results(
        row_results=rows,
        started_at="2026-06-11T00:00:00+00:00",
        finished_at="2026-06-11T00:01:00+00:00",
        output_dir=tmp_path,
        endpoint="https://openrouter.ai/api/v1",
    )
    analysis = render_analysis(summary)

    assert summary["by_model"]["deepseek_v4_pro"]["original_strict_pass_count"] == 0
    assert summary["by_model"]["deepseek_v4_pro"]["example_strict_pass_count"] == 3
    assert summary["usage_totals"]["total_tokens"] == 600
    assert "Cross-Model Action-Object Contract Salience Analysis" in analysis


def _model_bucket(
    *,
    original: int,
    example: int,
    original_relaxed: int = 0,
    example_relaxed: int = 0,
    original_scorable: int = 3,
    example_scorable: int = 3,
) -> dict:
    return {
        "original_scorable_count": original_scorable,
        "example_scorable_count": example_scorable,
        "original_strict_pass_count": original,
        "example_strict_pass_count": example,
        "original_strict_fail_relaxed_pass_count": original_relaxed,
        "example_strict_fail_relaxed_pass_count": example_relaxed,
    }


def _row(
    model_key: str,
    model_id: str,
    prompt_condition: str,
    strict: bool,
) -> dict:
    return {
        "row_id": f"{model_key}__{prompt_condition}",
        "condition_id": f"{model_key}__{prompt_condition}",
        "model_key": model_key,
        "model_id": model_id,
        "prompt_condition": prompt_condition,
        "provider_failure": None,
        "usage": {"total_tokens": 100, "cost": 0.001},
        "strict_evaluation": {
            "strict_required_actions_valid": strict,
            "rejection_paths": [] if strict else ["$.open_items[0].kind"],
            "explanation_candidates": ["strict_contract_satisfied"]
            if strict
            else ["contract_underspecification_candidate"],
        },
        "relaxed_evaluation": {
            "relaxed_required_actions_valid": not strict,
        },
    }
