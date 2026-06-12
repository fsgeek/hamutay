import importlib.util
from pathlib import Path


def _load_runner():
    path = (
        Path(__file__).parents[2]
        / "experiments/event_loop/live_evidence_resume_20260612/run.py"
    )
    spec = importlib.util.spec_from_file_location("live_evidence_resume_runner", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_first_wake_strict_requires_external_evidence_request():
    valid = {
        "response": "I cannot determine this without the external ledger record.",
        "policy_action": "ask_external_evidence",
        "uncertainty": runner.MISSING_EVIDENCE,
    }
    completion = {
        "response": "BRAVO-17 passed under LEDGER-BRAVO-17-PASS.",
        "policy_action": "stop_complete",
    }

    valid_score = runner.evaluate_wake_action(valid, wake_kind="first", relaxed=False)
    completion_score = runner.evaluate_wake_action(
        completion,
        wake_kind="first",
        relaxed=False,
    )

    assert valid_score["strict_required_actions_valid"] is True
    assert completion_score["strict_required_actions_valid"] is False
    assert "policy_action.ask_external_evidence" in completion_score["failures"]
    assert "first_wake_fabricated_fulfilled_evidence" in completion_score["failures"]


def test_resume_scorer_separates_evidence_use_from_policy_action():
    evidence_used_wrong_policy = {
        "response": "The fulfilled ledger says BRAVO-17 passed: LEDGER-BRAVO-17-PASS.",
        "policy_action": "ask_external_evidence",
        "uncertainty": "I still want more evidence.",
    }
    unsupported_completion = {
        "response": "The task is complete.",
        "policy_action": "stop_complete",
    }

    evidence_score = runner.evaluate_wake_action(
        evidence_used_wrong_policy,
        wake_kind="resume",
        relaxed=False,
    )
    unsupported_score = runner.evaluate_wake_action(
        unsupported_completion,
        wake_kind="resume",
        relaxed=False,
    )

    assert evidence_score["evidence_use"] == "evidence_fulfilled_used"
    assert evidence_score["strict_required_actions_valid"] is False
    assert evidence_score["action_artifact_consistency"] == (
        "fossilized_prior_block"
    )
    assert "policy_action.stop_complete" in evidence_score["failures"]

    assert unsupported_score["unsupported_completion"] is True
    assert unsupported_score["evidence_use"] == "evidence_absent"
    assert unsupported_score["action_artifact_consistency"] == (
        "unsupported_completion"
    )


def test_append_only_linkage_audit_distinguishes_harness_failure():
    flow = {
        "policy_disposition": {"disposition_id": "disp-1"},
        "evidence_request": {
            "request_id": "req-1",
            "source_disposition_id": "disp-1",
            "result_record_id": "record-1",
        },
        "evidence_fulfillment": {
            "fulfillment_id": "fulfill-1",
            "request_id": "req-1",
        },
        "resume_event": {
            "resumes_evidence_request_id": "req-1",
            "resumes_evidence_fulfillment_id": "fulfill-1",
            "evidence_context": {"present": True},
        },
    }
    broken = {
        **flow,
        "resume_event": {
            **flow["resume_event"],
            "resumes_evidence_fulfillment_id": "wrong",
        },
    }

    assert runner.audit_evidence_linkage(flow)["ok"] is True
    audit = runner.audit_evidence_linkage(broken)
    assert audit["ok"] is False
    assert audit["checks"]["resume_links_fulfillment"] is False


def test_h1_classification_survives_with_two_positive_rows():
    positive_score = {
        "positive_evidence_resume": True,
        "first_evidence_request_valid": True,
        "append_only_linkage": {"ok": True},
        "resumed_wake_received_evidence": True,
        "evidence_use": "evidence_fulfilled_used",
        "unsupported_completion": False,
        "fossilized_prior_blocked_state": False,
        "artifact_action_consistency": "consistent_supported_completion",
    }
    negative_score = {
        **positive_score,
        "positive_evidence_resume": False,
        "evidence_use": "evidence_absent",
        "artifact_action_consistency": "unsupported_completion",
    }
    rows = [
        {"score": positive_score, "failure_attribution": {"layer": "passed"}},
        {"score": positive_score, "failure_attribution": {"layer": "passed"}},
        {"score": negative_score, "failure_attribution": {"layer": "model"}},
    ]

    assert runner.classify_h1(rows) == "survived"
