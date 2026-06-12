import json
import re
from uuid import UUID

from hamutay.memory.live_pilot import (
    REQUIRED_FAILURE_LAYERS,
    ProviderActionResponse,
    _action_object_system_prompt,
    _has_running_to_pending_recovery,
    classify_report_failures,
    evaluate_pilot_report,
    execute_live_pilot,
    failure_taxonomy,
    run_no_token_dry_run_gate,
    sandbox_manifest,
    token_cycle_budget,
)


class ScriptedPilotClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate_action(self, *, messages: list[dict], max_output_tokens: int):
        self.calls += 1
        assert max_output_tokens == token_cycle_budget()["max_output_tokens_per_cycle"]
        if self.calls == 1:
            action = {
                "response": "I opened one bounded pilot item and scheduled the wake.",
                "open_items": [
                    {
                        "kind": "todo",
                        "text": "resolve the first tiny live autonomy pilot",
                    }
                ],
                "schedule_requests": [
                    {
                        "purpose": "resume and close the tiny live pilot item",
                        "requested_context": [
                            {
                                "tool": "recall",
                                "record_id": "70000000-0000-0000-0000-000000000001",
                            }
                        ],
                    }
                ],
            }
        else:
            open_item = _extract_open_item(messages[-1]["content"])
            action = {
                "response": "I closed the bounded pilot item and can stop.",
                "closures": [
                    {
                        "target_handle": open_item["handle"],
                        "status": "resolved",
                        "basis": "the tiny live pilot wake was resolved",
                    }
                ],
                "policy_action": "stop_complete",
            }
        return ProviderActionResponse(
            action_object=action,
            raw_content=json.dumps(action),
            request_payload={"messages": messages},
            response_payload={
                "choices": [{"message": {"content": json.dumps(action)}}],
                "usage": {"total_tokens": 123},
            },
            elapsed_seconds=0.01,
            usage={"total_tokens": 123},
        )


def _extract_open_item(content: str) -> dict:
    match = re.search(r"Open item:\n(.*?)\nReturn one JSON object", content, re.S)
    assert match is not None
    return json.loads(match.group(1))


def test_no_token_dry_run_gate_writes_artifacts_and_passes(tmp_path):
    report = run_no_token_dry_run_gate(tmp_path)

    assert report["live_model_calls"] is False
    assert report["passed"] is True
    assert {case["case_id"] for case in report["cases"]} == {
        "clean_reconstruction",
        "resume_after_event_claim",
    }
    assert all(case["passed"] for case in report["cases"])
    assert all(case["failures"] == [] for case in report["cases"])

    for filename in (
        "sandbox_manifest.json",
        "token_cycle_budget.json",
        "failure_taxonomy.json",
        "dry_run_gate_report.json",
    ):
        assert (tmp_path / filename).exists()

    manifest = json.loads((tmp_path / "sandbox_manifest.json").read_text())
    budget = json.loads((tmp_path / "token_cycle_budget.json").read_text())
    taxonomy = json.loads((tmp_path / "failure_taxonomy.json").read_text())

    assert manifest == sandbox_manifest()
    assert budget == token_cycle_budget()
    assert taxonomy == failure_taxonomy()
    assert manifest["live_model_calls"] is False
    assert manifest["enforcement_level"] == "in_process_detective"
    assert "not OS-level containment" in manifest["enforcement_note"]
    assert manifest["tools"]["shell"] == "disabled"
    assert budget["max_cycles"] == 2

    resume_case = next(
        case for case in report["cases"]
        if case["case_id"] == "resume_after_event_claim"
    )
    statuses = [
        item["status"] for item in resume_case["report"]["event_statuses"]
        if item["record_type"] == "event_status"
    ]
    assert statuses == ["pending", "running", "pending", "running", "completed"]


def test_execute_live_pilot_with_scripted_client_preserves_artifacts(tmp_path):
    run_id = UUID("70000000-0000-0000-0000-000000000099")
    client = ScriptedPilotClient()

    result = execute_live_pilot(
        runs_root=tmp_path,
        run_id=run_id,
        action_client=client,
    )
    run_root = tmp_path / str(run_id)
    report = json.loads((run_root / "reconstructed_report.json").read_text())
    evaluation = json.loads((run_root / "evaluation.json").read_text())

    assert result["passed"] is True
    assert result["outcome_layer"] == "passed"
    assert client.calls == 2
    assert evaluation["passed"] is True
    assert report["invariant_failures"] == []
    assert all(report["invariants"].values())
    assert (run_root / "cycle_01_provider_request.json").exists()
    assert (run_root / "cycle_01_provider_response.json").exists()
    assert (run_root / "cycle_02_provider_request.json").exists()
    assert (run_root / "cycle_02_provider_response.json").exists()
    assert "live_model_call" in {
        item["operation_type"] for item in report["operation_statuses"]
    }


def test_execute_live_pilot_without_api_key_writes_provider_failure(tmp_path):
    run_id = UUID("70000000-0000-0000-0000-000000000100")

    result = execute_live_pilot(
        runs_root=tmp_path,
        run_id=run_id,
        api_key="",
    )
    run_root = tmp_path / str(run_id)
    evaluation = json.loads((run_root / "evaluation.json").read_text())

    assert result["passed"] is False
    assert result["outcome_layer"] == "provider"
    assert evaluation["failures"][0]["layer"] == "provider"
    assert evaluation["failures"][0]["code"] == "provider_api_error"


def test_failure_taxonomy_covers_required_layers():
    layers = {entry["layer"] for entry in failure_taxonomy()["entries"]}

    assert REQUIRED_FAILURE_LAYERS <= layers


def test_evaluator_classifies_report_failures_by_layer():
    report = {
        "ledger_verification": {"ok": False, "errors": [{"code": "tamper"}]},
        "ignored_ledger_count": 2,
        "invariant_failures": ["stop_policy_consistent_with_idle"],
        "action_trace_count": 1,
        "stopped_because": "wording should not drive classification",
        "invariants": {
            "ledger_verified": False,
            "restart_frontier_clean": False,
            "closed_handle_had_prior_open_item": True,
            "stop_policy_consistent_with_idle": False,
            "event_reached_completed": True,
            "no_pending_or_running_events": True,
        },
    }

    failures = classify_report_failures(report)
    evaluation = evaluate_pilot_report(report, case_id="synthetic_failure")
    layers = {failure["layer"] for failure in failures}
    codes = {failure["code"] for failure in failures}

    assert evaluation["passed"] is False
    assert {"substrate", "restart_boundary", "harness", "model"} <= layers
    assert {
        "action_ledger_verification_failed",
        "restart_frontier_unclean",
        "invariant_failure",
        "model_action_missing",
        "model_policy_incoherent",
    } <= codes
    assert evaluation["required_layers_available"] is True


def test_stop_message_wording_does_not_create_model_failure():
    report = {
        "ledger_verification": {"ok": True, "errors": []},
        "ignored_ledger_count": 0,
        "invariant_failures": [],
        "action_trace_count": 2,
        "stopped_because": "idle with alternate human-readable phrasing",
        "invariants": {
            "ledger_verified": True,
            "restart_frontier_clean": True,
            "closed_handle_had_prior_open_item": True,
            "stop_policy_consistent_with_idle": True,
            "event_reached_completed": True,
            "no_pending_or_running_events": True,
        },
    }

    assert classify_report_failures(report) == []
    assert evaluate_pilot_report(report, case_id="alternate_stop")[
        "passed"
    ] is True


def test_evaluator_marks_missing_invariants_unscoreable():
    report = {
        "ledger_verification": {"ok": True, "errors": []},
        "ignored_ledger_count": 0,
        "invariant_failures": [],
        "action_trace_count": 2,
        "stopped_because": "idle: no open work remained",
        "invariants": {"ledger_verified": True},
    }

    evaluation = evaluate_pilot_report(report, case_id="missing_invariants")

    assert evaluation["passed"] is False
    assert evaluation["failures"] == [
        {
            "layer": "scorer",
            "code": "report_unscoreable",
            "evidence": {
                "missing_invariants": [
                    "closed_handle_had_prior_open_item",
                    "event_reached_completed",
                    "no_pending_or_running_events",
                    "restart_frontier_clean",
                    "stop_policy_consistent_with_idle",
                ]
            },
        }
    ]


def test_recovery_detection_is_event_id_aware():
    assert _has_running_to_pending_recovery(
        {
            "event_statuses": [
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "running",
                },
                {
                    "record_type": "event_status",
                    "event_id": "b",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "completed",
                },
            ]
        }
    ) is False
    assert _has_running_to_pending_recovery(
        {
            "event_statuses": [
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "running",
                },
                {
                    "record_type": "event_status",
                    "event_id": "b",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "pending",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "running",
                },
                {
                    "record_type": "event_status",
                    "event_id": "a",
                    "status": "completed",
                },
            ]
        }
    ) is True


def test_action_object_prompt_names_transport_and_nested_schema_contract():
    prompt = _action_object_system_prompt()

    assert "first visible character must be {" in prompt
    assert "last visible character must be }" in prompt
    assert "Do not wrap the object in markdown fences" in prompt
    assert "Do not duplicate the object" in prompt
    assert "Do not put the answer only in reasoning content" in prompt
    assert "{\"kind\":\"todo\",\"text\":\"inspect the fulfilled evidence\"}" in prompt
    assert "requested_context must be a non-empty array, not a single object" in prompt
    assert (
        "{\"purpose\":\"resume after evidence arrives\",\"requested_context\":"
        "[{\"tool\":\"recall\",\"record_id\":\"00000000-0000-0000-0000-"
        "000000000000\"}]}"
        in prompt
    )
    assert "\"policy_action\":\"ask_external_evidence\"" in prompt
    assert "\"policy_action\":\"defer\"" in prompt
    assert "\"policy_action\":\"abandon\"" in prompt
