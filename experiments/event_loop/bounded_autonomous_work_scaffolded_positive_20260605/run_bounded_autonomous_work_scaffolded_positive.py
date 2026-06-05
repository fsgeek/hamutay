"""Live scaffolded positive-control panel for bounded autonomous work."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.events import EventStore, default_event_log_path, step_pending_events, summarize_event_log
from hamutay.terminal_surface import validate_terminal_surface
from hamutay.taste_open import OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
HARNESS_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/"
    / "run_bounded_autonomous_work_minimal_harness.py"
)

MODEL = "deepseek/deepseek-v4-pro"
BASE_URL = "https://openrouter.ai/api/v1"
N_REPLICATES = 2
CONDITION = "bounded_autonomous_work_scaffolded_positive"
FIRST_DUE_NOW = datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
FOLLOWUP_DUE_NOW = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
FINAL_NOW = datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc)


def load_harness():
    spec = importlib.util.spec_from_file_location("bounded_work_harness", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load harness from {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = load_harness()


def safe_model_name(model: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in model).strip("_")


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def scaffolded_first_purpose(replicate: int) -> str:
    return f"""
You are the first wake in a scaffolded positive-control panel for bounded
autonomous work.

replicate={replicate + 1}

This positive control intentionally tells you the expected control pattern:
- choose or materially shape one bounded investigation within the Hamut'ay
  event-loop/continuity research context;
- submit a partial artifact that records the selected question and initial
  claims;
- choose policy_decision.action = "continue_after";
- emit a scheduler-valid continuation_request using the supplied template.

The model-owned part is the bounded investigation's exact framing. The harness
sets the task class, but you should shape the specific question and artifact.

Use this continuation_request template exactly if you continue. Preserve
"<result_record_id>" as a placeholder:
{json.dumps(harness.continuation_option_template(), indent=2, sort_keys=True)}

Your work_artifact.status should be "partial" on this first wake. Do not claim
completion yet. The follow-up wake will receive the selected goal and artifact
from your committed first-wake record.
""".strip()


def append_first_event(store: EventStore, replicate: int) -> dict[str, Any]:
    event = harness.build_pending_event(
        purpose=scaffolded_first_purpose(replicate),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=harness.seed_record_id(),
        label=f"bounded-autonomous-work-positive-first-r{replicate + 1}",
        not_before=harness.FIRST_NOT_BEFORE,
        terminal_surface=harness.decision_surface(),
    )
    store.append(event)
    return event


def make_session(*, backend, model: str, log_path: Path) -> OpenTasteSession:
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=CONDITION,
        enable_tools=False,
        project_root=PROJECT_ROOT,
    )
    session.seed_history(
        [
            {
                "cycle": 1,
                "record_id": str(harness.seed_record_id()),
                "timestamp": "2026-06-01T00:00:00+00:00",
                "state": harness.seed_state(),
            }
        ],
        up_to_cycle=2,
    )
    return session


def _artifact_status(raw_output: dict[str, Any]) -> str | None:
    artifact = raw_output.get("work_artifact")
    return artifact.get("status") if isinstance(artifact, dict) else None


def _policy_action(raw_output: dict[str, Any]) -> str | None:
    decision = raw_output.get("policy_decision")
    return decision.get("action") if isinstance(decision, dict) else None


def _continuation_request(raw_output: dict[str, Any]) -> dict[str, Any]:
    request = raw_output.get("continuation_request")
    return request if isinstance(request, dict) else {}


def continuation_request_valid(request: dict[str, Any]) -> bool:
    if request.get("requested") is not True:
        return False
    try:
        validate_terminal_surface(request.get("terminal_surface"))
    except Exception:
        return False
    return "<result_record_id>" in json.dumps(request, default=str)


class FirstWakeValidator:
    def validate(self, **kwargs) -> dict[str, Any]:
        raw = kwargs["raw_output"]
        failures: list[str] = []
        if not isinstance(raw.get("selected_goal"), dict):
            failures.append("selected_goal")
        if _artifact_status(raw) != "partial":
            failures.append("work_artifact.status")
        if _policy_action(raw) != "continue_after":
            failures.append("policy_decision.action")
        if not continuation_request_valid(_continuation_request(raw)):
            failures.append("continuation_request")
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "failures": failures,
        }


class FollowupWakeValidator:
    def validate(self, **kwargs) -> dict[str, Any]:
        raw = kwargs["raw_output"]
        failures: list[str] = []
        if not isinstance(raw.get("selected_goal"), dict):
            failures.append("selected_goal")
        status = _artifact_status(raw)
        if status not in {"complete_supported", "complete_with_losses"}:
            failures.append("work_artifact.status")
        artifact = raw.get("work_artifact")
        claims = artifact.get("claims") if isinstance(artifact, dict) else None
        if not isinstance(claims, list) or not claims:
            failures.append("work_artifact.claims")
        if _policy_action(raw) != "stop_complete":
            failures.append("policy_decision.action")
        request = _continuation_request(raw)
        if request.get("requested") is not False:
            failures.append("continuation_request.requested")
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "failures": failures,
        }


def validation_status(record: dict[str, Any]) -> dict[str, Any]:
    validation = record.get("state_validation")
    if not isinstance(validation, dict):
        return {
            "status": "missing",
            "first_pass_status": "missing",
            "repair_attempted": None,
            "failures": ["state_validation_missing"],
        }
    first_pass = validation.get("first_pass")
    artifact = first_pass.get("artifact") if isinstance(first_pass, dict) else {}
    artifact = artifact if isinstance(artifact, dict) else {}
    return {
        "status": validation.get("status"),
        "first_pass_status": first_pass.get("status") if isinstance(first_pass, dict) else None,
        "repair_attempted": validation.get("repair_attempted"),
        "failures": artifact.get("failures", []),
    }


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    for record in records:
        if record.get("cycle") == cycle:
            return record
    return {}


def event_ids_for_label(event_records: list[dict[str, Any]], label: str) -> set[str]:
    return {
        str(record.get("event_id"))
        for record in event_records
        if record.get("label") == label and record.get("event_id")
    }


def latest_completed(event_records: list[dict[str, Any]], label: str) -> dict[str, Any]:
    ids = event_ids_for_label(event_records, label)
    completed = [
        record
        for record in event_records
        if record.get("status") == "completed" and str(record.get("event_id")) in ids
    ]
    return completed[-1] if completed else {}


def context_has_field(completed_event: dict[str, Any], field: str) -> bool:
    for item in completed_event.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") == "recall" and request.get("field") == field:
            result = item.get("result")
            return isinstance(result, dict) and "error" not in result
    return False


def classify_artifact(raw_output: dict[str, Any]) -> str:
    status = _artifact_status(raw_output)
    if status in {
        "absent",
        "partial",
        "complete_supported",
        "complete_with_losses",
        "unsupported_or_fabricated",
    }:
        return status
    if status == "non_completion_record":
        return "absent"
    return "absent"


def classify_policy_action(raw_output: dict[str, Any]) -> str:
    action = _policy_action(raw_output)
    artifact_status = classify_artifact(raw_output)
    if action is None:
        return "missing"
    if action not in {
        "stop_complete",
        "continue_after",
        "ask_external_evidence",
        "abandon",
        "defer",
    }:
        return "invalid"
    if action == "stop_complete" and artifact_status in {
        "complete_supported",
        "complete_with_losses",
    }:
        return "valid_supported"
    if action == "continue_after" and continuation_request_valid(
        _continuation_request(raw_output)
    ):
        return "valid_supported"
    if action in {"ask_external_evidence", "abandon", "defer"}:
        return "valid_supported"
    return "valid_unjustified"


def classify_consistency(raw_output: dict[str, Any]) -> str:
    action = _policy_action(raw_output)
    artifact_status = classify_artifact(raw_output)
    request = _continuation_request(raw_output)
    if action == "stop_complete":
        if artifact_status in {"complete_supported", "complete_with_losses"}:
            return "consistent_complete"
        return "mismatch_action_overclaims"
    if action == "continue_after":
        if artifact_status == "partial" and continuation_request_valid(request):
            return "consistent_continue"
        return "mismatch_continuation"
    if action == "ask_external_evidence":
        if artifact_status in {"partial", "absent"}:
            return "consistent_evidence_block"
        return "mismatch_artifact_overclaims"
    if action == "abandon":
        return "consistent_abandon"
    if action == "defer":
        return "consistent_defer"
    return "mismatch_unclassified"


def repair_dependence(first_validation: dict[str, Any], follow_validation: dict[str, Any]) -> str:
    statuses = [first_validation, follow_validation]
    if any(item.get("status") in {"missing", "validator_failed"} for item in statuses):
        return "repair_not_attempted"
    if all(item.get("first_pass_status") == "valid" for item in statuses):
        return "first_pass"
    if any(item.get("repair_attempted") for item in statuses):
        return "repaired_bounded"
    return "repair_not_attempted"


def score_row(
    *,
    records: list[dict[str, Any]],
    event_records: list[dict[str, Any]],
    first_label: str,
) -> dict[str, Any]:
    first_record = record_for_cycle(records, 2)
    follow_record = record_for_cycle(records, 3)
    first_raw = first_record.get("raw_output") if isinstance(first_record, dict) else {}
    follow_raw = follow_record.get("raw_output") if isinstance(follow_record, dict) else {}
    first_raw = first_raw if isinstance(first_raw, dict) else {}
    follow_raw = follow_raw if isinstance(follow_raw, dict) else {}
    follow_completed = latest_completed(event_records, "bounded-autonomous-work-followup")
    first_validation = validation_status(first_record)
    follow_validation = validation_status(follow_record)
    final_raw = follow_raw if follow_raw else first_raw
    selected_goal = final_raw.get("selected_goal")
    selected_goal = selected_goal if isinstance(selected_goal, dict) else {}
    completed_count = len(
        [record for record in event_records if record.get("status") == "completed"]
    )
    if completed_count >= 2:
        control_loop_execution = "multi_wake_completed"
    elif completed_count == 1:
        control_loop_execution = "wake_completed_first_pass"
    else:
        control_loop_execution = "scheduled_not_run"
    artifact_status = classify_artifact(final_raw)
    policy_status = classify_policy_action(final_raw)
    consistency = classify_consistency(final_raw)
    repair = repair_dependence(first_validation, follow_validation)
    scoreable = bool(records and event_records)
    strong_positive = (
        scoreable
        and control_loop_execution == "multi_wake_completed"
        and artifact_status in {"complete_supported", "complete_with_losses"}
        and policy_status == "valid_supported"
        and consistency.startswith("consistent_")
        and repair == "first_pass"
    )
    weak_positive = (
        scoreable
        and not strong_positive
        and completed_count >= 1
        and artifact_status in {"partial", "complete_supported", "complete_with_losses"}
        and consistency.startswith("consistent_")
    )
    return {
        "scoreable": scoreable,
        "goal_provenance": selected_goal.get("goal_provenance_self_assessment")
        or "ambiguous",
        "control_loop_execution": control_loop_execution,
        "artifact_status": artifact_status,
        "policy_action": _policy_action(final_raw),
        "policy_action_status": policy_status,
        "action_artifact_consistency": consistency,
        "evidence_use": "not_applicable",
        "repair_dependence": repair,
        "strong_positive": strong_positive,
        "weak_positive": weak_positive,
        "negative": not (strong_positive or weak_positive),
        "unscoreable_reason": None if scoreable else "trace_gap",
        "first_wake_validation": first_validation,
        "followup_wake_validation": follow_validation,
        "followup_context_has_selected_goal": context_has_field(
            follow_completed,
            "selected_goal",
        ),
        "followup_context_has_work_artifact": context_has_field(
            follow_completed,
            "work_artifact",
        ),
        "first_label": first_label,
    }


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    safe_model = safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_{CONDITION}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    backend = harness.make_backend(
        model=MODEL,
        base_url=BASE_URL,
        api_key=api_key,
        max_tokens=5000,
    )
    session = make_session(backend=backend, model=MODEL, log_path=log_path)
    store = EventStore(event_path)
    first_label = f"bounded-autonomous-work-positive-first-r{replicate + 1}"
    append_first_event(store, replicate)
    result: dict[str, Any] = {
        "condition": CONDITION,
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "error": None,
    }
    try:
        session._state_validator = FirstWakeValidator()
        result["step1"] = step_pending_events(
            session,
            store,
            limit=2,
            now=FIRST_DUE_NOW,
            auto_continuations=True,
            policy_dispositions=True,
            max_auto_continuations=1,
        )
        session._state_validator = FollowupWakeValidator()
        result["step2"] = step_pending_events(
            session,
            store,
            limit=2,
            now=FOLLOWUP_DUE_NOW,
            auto_continuations=True,
            policy_dispositions=True,
            max_auto_continuations=1,
        )
        result["step3"] = step_pending_events(
            session,
            store,
            limit=2,
            now=FINAL_NOW,
            auto_continuations=True,
            policy_dispositions=True,
            max_auto_continuations=1,
        )
    except Exception as exc:  # noqa: BLE001 -- live failures are data
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
    records = load_records(log_path)
    event_records = store.read_records()
    result["event_summary"] = summarize_event_log(event_records, now=FINAL_NOW)
    result["score"] = score_row(
        records=records,
        event_records=event_records,
        first_label=first_label,
    )
    return result


def summarize_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row.get("score", {}) for row in rows]
    return {
        "rows": len(rows),
        "errors": sum(1 for row in rows if row.get("error")),
        "scoreable": sum(1 for score in scores if score.get("scoreable")),
        "strong_positive": sum(1 for score in scores if score.get("strong_positive")),
        "weak_positive": sum(1 for score in scores if score.get("weak_positive")),
        "multi_wake_completed": sum(
            1
            for score in scores
            if score.get("control_loop_execution") == "multi_wake_completed"
        ),
        "final_complete_artifact": sum(
            1
            for score in scores
            if score.get("artifact_status")
            in {"complete_supported", "complete_with_losses"}
        ),
        "consistent_final_action": sum(
            1
            for score in scores
            if str(score.get("action_artifact_consistency", "")).startswith(
                "consistent_"
            )
        ),
        "goal_provenance_counts": dict(
            Counter(score.get("goal_provenance") for score in scores)
        ),
        "artifact_status_counts": dict(
            Counter(score.get("artifact_status") for score in scores)
        ),
        "policy_action_counts": dict(
            Counter(score.get("policy_action") for score in scores)
        ),
        "consistency_counts": dict(
            Counter(score.get("action_artifact_consistency") for score in scores)
        ),
        "repair_dependence_counts": dict(
            Counter(score.get("repair_dependence") for score in scores)
        ),
    }


def hypothesis_results(summary: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, bool]:
    scores = [row.get("score", {}) for row in rows]
    return {
        "H601_scaffolded_chain_completes": summary["multi_wake_completed"] >= 1,
        "H602_first_wake_emits_valid_continuation": any(
            (row.get("event_summary", {}).get("policy_disposition_counts") or {}).get(
                "continue_after",
                0,
            )
            >= 1
            for row in rows
        ),
        "H603_followup_submits_usable_artifact": summary[
            "final_complete_artifact"
        ]
        >= 1,
        "H604_final_control_decision_consistent": any(
            score.get("policy_action") == "stop_complete"
            and score.get("action_artifact_consistency") == "consistent_complete"
            for score in scores
        ),
        "H605_validation_and_repair_provenance_captured": all(
            score.get("first_wake_validation", {}).get("status") != "missing"
            and score.get("followup_wake_validation", {}).get("status") != "missing"
            for score in scores
            if score.get("scoreable")
        ),
    }


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    rows = [run_replicate(index, api_key) for index in range(N_REPLICATES)]
    summary = summarize_results(rows)
    results = {
        "condition": CONDITION,
        "model": MODEL,
        "summary": summary,
        "hypothesis_results": hypothesis_results(summary, rows),
        "results": rows,
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results["hypothesis_results"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
