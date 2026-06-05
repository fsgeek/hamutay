"""Live less-scaffolded panel for bounded autonomous work."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
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
SCAFFOLDED_RESULTS_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/"
    / "results.json"
)

MODEL = "deepseek/deepseek-v4-pro"
BASE_URL = "https://openrouter.ai/api/v1"
N_REPLICATES = 3
CONDITION = "bounded_autonomous_work_less_scaffolded"
FIRST_DUE_NOW = datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
FOLLOWUP_DUE_NOW = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
FINAL_NOW = datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc)
POLICY_ACTIONS = {
    "stop_complete",
    "continue_after",
    "ask_external_evidence",
    "abandon",
    "defer",
}


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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def first_purpose(replicate: int) -> str:
    return f"""
You are a wake in a less-scaffolded bounded-autonomous-work panel.

replicate={replicate + 1}

Within the Hamut'ay event-loop / continuity research context, choose or
materially shape one bounded investigation that can produce a concrete,
auditable artifact. The broad domain is bounded autonomous work in this event
loop: scheduling, continuity, evidence handling, action/artifact consistency,
or another tightly scoped question you can justify from the provided context.

Choose the policy action justified by the work state. There is no expected
answer. Use:
- stop_complete only if the artifact is complete under its declared scope;
- continue_after only if a bounded follow-up wake would materially improve the
  artifact;
- ask_external_evidence only if missing external evidence blocks completion;
- abandon only for honest non-completion when continuing is not useful;
- defer only if the work remains open but no specific follow-up or evidence
  request is currently justified.

If you choose continue_after, use this continuation_request template and keep
"<result_record_id>" as the placeholder so the scheduler can bind it:
{json.dumps(harness.continuation_option_template(), indent=2, sort_keys=True)}

If you choose any other action, set continuation_request to {{"requested": false}}.

Call choose_bounded_autonomous_work with your selected goal, current artifact,
policy decision, evidence used, and continuation request. Do not choose an
action to satisfy the harness; choose the action your artifact supports.
""".strip()


def append_first_event(store: EventStore, replicate: int) -> dict[str, Any]:
    event = harness.build_pending_event(
        purpose=first_purpose(replicate),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=harness.seed_record_id(),
        label=f"bounded-autonomous-work-less-first-r{replicate + 1}",
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


def _artifact(raw_output: dict[str, Any]) -> dict[str, Any]:
    artifact = raw_output.get("work_artifact")
    return artifact if isinstance(artifact, dict) else {}


def _artifact_status(raw_output: dict[str, Any]) -> str | None:
    return _artifact(raw_output).get("status")


def _policy_decision(raw_output: dict[str, Any]) -> dict[str, Any]:
    decision = raw_output.get("policy_decision")
    return decision if isinstance(decision, dict) else {}


def _policy_action(raw_output: dict[str, Any]) -> str | None:
    return _policy_decision(raw_output).get("action")


def _missing_evidence(raw_output: dict[str, Any]) -> list[str]:
    missing = _policy_decision(raw_output).get("missing_evidence")
    return missing if isinstance(missing, list) else []


def _continuation_request(raw_output: dict[str, Any]) -> dict[str, Any]:
    request = raw_output.get("continuation_request")
    return request if isinstance(request, dict) else {}


def continuation_request_valid(request: dict[str, Any]) -> bool:
    if request.get("requested") is not True:
        return False
    if not request.get("purpose"):
        return False
    try:
        validate_terminal_surface(request.get("terminal_surface"))
    except Exception:
        return False
    return True


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
    if action not in POLICY_ACTIONS:
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
    if action == "ask_external_evidence" and artifact_status in {"partial", "absent"}:
        return "valid_supported" if _missing_evidence(raw_output) else "valid_unjustified"
    if action == "abandon" and artifact_status in {"absent", "partial"}:
        return "valid_supported"
    if action == "defer" and artifact_status in {"absent", "partial"}:
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
        if artifact_status in {"partial", "absent"} and _missing_evidence(raw_output):
            return "consistent_evidence_block"
        return "mismatch_artifact_overclaims"
    if action == "abandon":
        if artifact_status in {"absent", "partial"}:
            return "consistent_abandon"
        return "mismatch_action_overclaims"
    if action == "defer":
        if artifact_status in {"absent", "partial"}:
            return "consistent_defer"
        return "mismatch_action_overclaims"
    return "mismatch_unclassified"


class LessScaffoldedValidator:
    def validate(self, **kwargs) -> dict[str, Any]:
        raw = kwargs["raw_output"]
        failures: list[str] = []
        if not isinstance(raw.get("selected_goal"), dict):
            failures.append("selected_goal")
        artifact = raw.get("work_artifact")
        if not isinstance(artifact, dict):
            failures.append("work_artifact")
        else:
            if classify_artifact(raw) == "absent" and artifact.get("status") != "absent":
                failures.append("work_artifact.status")
            claims = artifact.get("claims")
            if not isinstance(claims, list):
                failures.append("work_artifact.claims")
        if _policy_action(raw) not in POLICY_ACTIONS:
            failures.append("policy_decision.action")
        if classify_policy_action(raw) == "invalid":
            failures.append("policy_decision")
        if _policy_action(raw) == "continue_after" and not continuation_request_valid(
            _continuation_request(raw)
        ):
            failures.append("continuation_request")
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


def record_for_cycle(records: list[dict[str, Any]], cycle: int) -> dict[str, Any]:
    for record in records:
        if record.get("cycle") == cycle:
            return record
    return {}


def final_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [
        record for record in records
        if isinstance(record.get("raw_output"), dict) and record.get("cycle", 0) > 1
    ]
    return scored[-1] if scored else {}


def context_has_field(completed_event: dict[str, Any], field: str) -> bool:
    for item in completed_event.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") == "recall" and request.get("field") == field:
            result = item.get("result")
            return isinstance(result, dict) and "error" not in result
    return False


def repair_dependence(validations: list[dict[str, Any]]) -> str:
    if not validations:
        return "repair_not_attempted"
    if any(item.get("status") in {"missing", "validator_failed"} for item in validations):
        return "repair_not_attempted"
    if all(item.get("first_pass_status") == "valid" for item in validations):
        return "first_pass"
    if any(item.get("repair_attempted") for item in validations):
        return "repaired_bounded"
    return "repair_not_attempted"


def score_row(
    *,
    records: list[dict[str, Any]],
    event_records: list[dict[str, Any]],
    first_label: str,
) -> dict[str, Any]:
    first_record = record_for_cycle(records, 2)
    final = final_record(records)
    raw = final.get("raw_output") if isinstance(final, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    first_raw = first_record.get("raw_output") if isinstance(first_record, dict) else {}
    first_raw = first_raw if isinstance(first_raw, dict) else {}
    first_consistency = classify_consistency(first_raw)
    completed_count = len(
        [record for record in event_records if record.get("status") == "completed"]
    )
    if completed_count >= 2:
        control_loop_execution = "multi_wake_completed"
    elif completed_count == 1:
        control_loop_execution = "wake_completed_first_pass"
    elif event_records:
        control_loop_execution = "scheduled_not_run"
    else:
        control_loop_execution = "no_scheduled_work"
    artifact_status = classify_artifact(raw)
    policy_status = classify_policy_action(raw)
    consistency = classify_consistency(raw)
    selected_goal = raw.get("selected_goal") or first_raw.get("selected_goal")
    selected_goal = selected_goal if isinstance(selected_goal, dict) else {}
    validations = [
        validation_status(record)
        for record in records
        if isinstance(record.get("raw_output"), dict) and record.get("cycle", 0) > 1
    ]
    follow_completed = latest_completed(event_records, "bounded-autonomous-work-followup")
    first_continuation_event_ids = [
        record.get("continuation_event_id")
        for record in event_records
        if record.get("record_type") == "policy_disposition"
        and record.get("policy_action") == "continue_after"
        and record.get("wake_cycle") == 2
        and record.get("continuation_event_id")
    ]
    scoreable = bool(records and event_records and raw)
    strong_positive = (
        scoreable
        and artifact_status in {"complete_supported", "complete_with_losses"}
        and policy_status == "valid_supported"
        and consistency.startswith("consistent_")
        and selected_goal.get("goal_provenance_self_assessment")
        in {"model_shaped", "model_originated"}
        and repair_dependence(validations) == "first_pass"
    )
    weak_positive = (
        scoreable
        and not strong_positive
        and policy_status == "valid_supported"
        and consistency.startswith("consistent_")
    )
    return {
        "scoreable": scoreable,
        "goal_provenance": selected_goal.get("goal_provenance_self_assessment")
        or "ambiguous",
        "control_loop_execution": control_loop_execution,
        "artifact_status": artifact_status,
        "first_policy_action": _policy_action(first_raw),
        "first_action_artifact_consistency": first_consistency,
        "first_continuation_event_appended": bool(first_continuation_event_ids),
        "first_continuation_event_ids": first_continuation_event_ids,
        "policy_action": _policy_action(raw),
        "policy_action_status": policy_status,
        "action_artifact_consistency": consistency,
        "evidence_use": (
            "evidence_missing_honored"
            if _policy_action(raw) == "ask_external_evidence" and consistency == "consistent_evidence_block"
            else "not_applicable"
        ),
        "repair_dependence": repair_dependence(validations),
        "strong_positive": strong_positive,
        "weak_positive": weak_positive,
        "negative": not (strong_positive or weak_positive),
        "unscoreable_reason": None if scoreable else "trace_gap",
        "wake_validations": validations,
        "first_label": first_label,
        "followup_context_has_selected_goal": context_has_field(
            follow_completed,
            "selected_goal",
        ),
        "followup_context_has_work_artifact": context_has_field(
            follow_completed,
            "work_artifact",
        ),
        "final_cycle": final.get("cycle"),
        "completed_event_count": completed_count,
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
    first_label = f"bounded-autonomous-work-less-first-r{replicate + 1}"
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
        session._state_validator = LessScaffoldedValidator()
        result["step1"] = step_pending_events(
            session,
            store,
            limit=1,
            now=FIRST_DUE_NOW,
            auto_continuations=True,
            policy_dispositions=True,
            max_auto_continuations=1,
        )
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
        "coherent_final_action": sum(
            1
            for score in scores
            if str(score.get("action_artifact_consistency", "")).startswith(
                "consistent_"
            )
        ),
        "multi_wake_completed": sum(
            1
            for score in scores
            if score.get("control_loop_execution") == "multi_wake_completed"
        ),
        "first_policy_action_counts": dict(
            Counter(score.get("first_policy_action") for score in scores)
        ),
        "final_policy_action_counts": dict(
            Counter(score.get("policy_action") for score in scores)
        ),
        "goal_provenance_counts": dict(
            Counter(score.get("goal_provenance") for score in scores)
        ),
        "artifact_status_counts": dict(
            Counter(score.get("artifact_status") for score in scores)
        ),
        "consistency_counts": dict(
            Counter(score.get("action_artifact_consistency") for score in scores)
        ),
        "repair_dependence_counts": dict(
            Counter(score.get("repair_dependence") for score in scores)
        ),
    }


def scaffolded_comparison() -> dict[str, Any]:
    scaffolded = load_json(SCAFFOLDED_RESULTS_PATH)
    summary = scaffolded.get("summary") if isinstance(scaffolded, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    return {
        "path": str(SCAFFOLDED_RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "rows": summary.get("rows"),
        "goal_provenance_counts": summary.get("goal_provenance_counts"),
        "policy_action_counts": summary.get("policy_action_counts"),
        "consistency_counts": summary.get("consistency_counts"),
        "strong_positive": summary.get("strong_positive"),
        "weak_positive": summary.get("weak_positive"),
    }


def hypothesis_results(
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    comparison: dict[str, Any],
) -> dict[str, bool]:
    scores = [row.get("score", {}) for row in rows]
    scoreable_scores = [score for score in scores if score.get("scoreable")]
    first_continue_scores = [
        score for score in scoreable_scores
        if score.get("first_policy_action") == "continue_after"
    ]
    final_continue_scores = [
        score for score in scoreable_scores if score.get("policy_action") == "continue_after"
    ]
    return {
        "H801_less_scaffolded_rows_are_scoreable": summary["scoreable"] >= 2,
        "H802_control_choices_remain_coherent": sum(
            str(score.get("action_artifact_consistency", "")).startswith(
                "consistent_"
            )
            for score in scoreable_scores
        )
        >= 2,
        "H803_reduced_hints_preserve_model_shaped_goal_provenance": any(
            score.get("goal_provenance") in {"model_shaped", "model_originated"}
            for score in scoreable_scores
        ),
        "H804_continuation_remains_bounded_when_chosen": all(
            score.get("first_continuation_event_appended")
            or score.get("first_action_artifact_consistency") == "mismatch_continuation"
            for score in first_continue_scores
        )
        and all(
            score.get("action_artifact_consistency") == "consistent_continue"
            or score.get("action_artifact_consistency") == "mismatch_continuation"
            for score in final_continue_scores
        ),
        "H805_comparison_to_step3_recorded": bool(
            comparison.get("goal_provenance_counts")
            and comparison.get("policy_action_counts")
            and comparison.get("consistency_counts")
        ),
    }


def main() -> None:
    if "--rescore" in sys.argv:
        rows = []
        for index in range(N_REPLICATES):
            safe_model = safe_model_name(MODEL)
            log_path = EXP_DIR / f"{safe_model}_{CONDITION}_r{index + 1:02d}.jsonl"
            event_path = default_event_log_path(log_path)
            records = load_records(log_path)
            event_records = EventStore(event_path).read_records()
            first_label = f"bounded-autonomous-work-less-first-r{index + 1}"
            rows.append(
                {
                    "condition": CONDITION,
                    "model": MODEL,
                    "replicate": index + 1,
                    "log_path": str(log_path.relative_to(PROJECT_ROOT)),
                    "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
                    "error": None,
                    "event_summary": summarize_event_log(
                        event_records,
                        now=FINAL_NOW,
                    ),
                    "score": score_row(
                        records=records,
                        event_records=event_records,
                        first_label=first_label,
                    ),
                }
            )
        summary = summarize_results(rows)
        comparison = scaffolded_comparison()
        results = {
            "condition": CONDITION,
            "model": MODEL,
            "summary": summary,
            "scaffolded_comparison": comparison,
            "hypothesis_results": hypothesis_results(summary, rows, comparison),
            "results": rows,
            "rescore": {
                "source": "existing_trace_files",
                "reason": "Correct H804 to score first-wake continuation choices.",
            },
        }
        RESULTS_PATH.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
        print(json.dumps(results["hypothesis_results"], indent=2, sort_keys=True))
        print(f"rescored {RESULTS_PATH.relative_to(PROJECT_ROOT)}")
        return

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    rows = [run_replicate(index, api_key) for index in range(N_REPLICATES)]
    summary = summarize_results(rows)
    comparison = scaffolded_comparison()
    results = {
        "condition": CONDITION,
        "model": MODEL,
        "summary": summary,
        "scaffolded_comparison": comparison,
        "hypothesis_results": hypothesis_results(summary, rows, comparison),
        "results": rows,
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results["hypothesis_results"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
