import json

from hamutay.memory.contract_literacy import (
    CONDITION_IDS,
    budget_manifest,
    condition_matrix,
    evaluate_cycle1_action_object,
    evaluate_failed_run_fixture,
    failure_taxonomy,
    load_failed_cycle1_action_object,
    prompt_variants,
    write_no_live_artifacts,
)


def test_condition_matrix_is_fixed_and_no_live():
    matrix = condition_matrix()
    budget = budget_manifest()
    prompts = prompt_variants()
    taxonomy = failure_taxonomy()

    assert [condition["condition_id"] for condition in matrix["conditions"]] == list(
        CONDITION_IDS
    )
    assert "Example valid open item shape" in prompts["variants"][
        "original_plus_one_valid_open_item_example"
    ]["addendum"]
    assert "open_items[0].kind" in prompts["variants"][
        "original_plus_schema_and_checklist"
    ]["addendum"]
    assert "The live harness must not silently repair" in prompts["variants"][
        "relaxed_open_item_contract_counterfactual"
    ]["addendum"]
    assert all("prompt_addendum" in condition for condition in matrix["conditions"])
    assert budget["live_execution_status"] == "not_authorized_by_this_artifact"
    assert budget["max_live_calls_if_later_authorized"] == 12
    assert {entry["layer"] for entry in taxonomy["entries"]} == {
        "model",
        "prompt_schema",
        "contract",
        "protocol",
        "provider",
        "scorer",
    }


def test_failed_live_run_is_strict_failure_but_relaxed_contract_candidate():
    fixture = evaluate_failed_run_fixture()
    strict = fixture["strict_evaluation"]
    relaxed = fixture["relaxed_counterfactual"]

    assert fixture["primary_interpretation"] == (
        "contract_underspecification_candidate"
    )
    assert strict["strict_required_actions_valid"] is False
    assert strict["strict_open_item_valid"] is False
    assert strict["schedule_request_valid"] is True
    assert "$.open_items[0].kind" in strict["rejection_paths"]
    assert strict["normalization_applied"] is False

    assert relaxed["relaxed_required_actions_valid"] is True
    assert relaxed["relaxed_open_item"]["would_accept"] is True
    item = relaxed["relaxed_open_item"]["items"][0]
    assert item["normalization_required"] is True
    assert item["missing_fields"] == ["kind", "text"]
    assert item["normalized_candidate"]["kind"] == "todo"
    assert item["normalized_candidate"]["text"].startswith("Verify the integrity")
    assert relaxed["normalization_applied"] is False
    assert "contract_underspecification_candidate" in relaxed[
        "explanation_candidates"
    ]


def test_strict_valid_action_satisfies_contract_without_normalization():
    raw = {
        "response": "I opened one item and scheduled one wake.",
        "open_items": [
            {
                "kind": "todo",
                "text": "resolve the bounded contract literacy item",
            }
        ],
        "schedule_requests": [
            {
                "purpose": "resolve the item",
                "requested_context": [
                    {
                        "tool": "recall",
                        "record_id": "70000000-0000-0000-0000-000000000001",
                    }
                ],
            }
        ],
    }

    evaluation = evaluate_cycle1_action_object(
        raw,
        condition_id="A_original_prompt_strict_contract",
        relaxed_open_item_contract=True,
    )

    assert evaluation["strict_required_actions_valid"] is True
    assert evaluation["relaxed_required_actions_valid"] is True
    assert evaluation["relaxed_open_item"]["items"][0]["normalization_required"] is False
    assert evaluation["explanation_candidates"] == ["strict_contract_satisfied"]


def test_malformed_open_item_is_not_relaxed_acceptable():
    raw = {
        "response": "I attempted the action.",
        "open_items": [{"handle": "oi-001", "status": "open"}],
        "schedule_requests": [
            {
                "purpose": "resolve the item",
                "requested_context": [
                    {
                        "tool": "recall",
                        "record_id": "70000000-0000-0000-0000-000000000001",
                    }
                ],
            }
        ],
    }

    evaluation = evaluate_cycle1_action_object(
        raw,
        condition_id="D_relaxed_open_item_contract",
        relaxed_open_item_contract=True,
    )

    assert evaluation["strict_required_actions_valid"] is False
    assert evaluation["relaxed_required_actions_valid"] is False
    assert evaluation["relaxed_open_item"]["would_accept"] is False
    assert evaluation["relaxed_open_item"]["items"][0]["reason"] == (
        "missing_text_and_description"
    )


def test_no_live_artifact_writer_preserves_failed_fixture(tmp_path):
    result = write_no_live_artifacts(tmp_path)

    assert result["live_model_calls"] is False
    assert set(result["artifacts"]) == {
        "budget.json",
        "failure_taxonomy.json",
        "fixture_failed_live_run_cycle1_evaluation.json",
        "matrix.json",
        "prompt_variants.json",
    }

    fixture = json.loads(
        (tmp_path / "fixture_failed_live_run_cycle1_evaluation.json").read_text()
    )
    assert fixture["source_run_id"] == "c39ba9a3-9dda-48f2-82f6-cb90f8229bae"
    assert fixture["primary_interpretation"] == (
        "contract_underspecification_candidate"
    )


def test_failed_fixture_loader_reads_provider_content_object():
    action = load_failed_cycle1_action_object()

    assert action["open_items"][0]["description"].startswith("Verify the integrity")
    assert "kind" not in action["open_items"][0]
