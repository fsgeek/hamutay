"""Live controls for bounded autonomous work Step 5."""

from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

from hamutay.events import EventStore, default_event_log_path, step_pending_events, summarize_event_log
from hamutay.taste_open import OpenTasteSession


EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
RESULTS_PATH = EXP_DIR / "results.json"
HARNESS_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/"
    / "run_bounded_autonomous_work_minimal_harness.py"
)
LESS_RUNNER_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/"
    / "run_bounded_autonomous_work_less_scaffolded.py"
)
TREATMENT_RESULTS_PATH = (
    PROJECT_ROOT
    / "experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/"
    / "results.json"
)

MODEL = "deepseek/deepseek-v4-pro"
BASE_URL = "https://openrouter.ai/api/v1"
CONDITION = "bounded_autonomous_work_controls"
FIRST_DUE_NOW = datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
FOLLOWUP_DUE_NOW = datetime(2026, 6, 1, 2, 0, tzinfo=timezone.utc)
FINAL_NOW = datetime(2026, 6, 1, 3, 0, tzinfo=timezone.utc)
CONTROLS = [
    "direct_one_shot",
    "scheduler_harness_selected_continuation",
    "identity_only_carry_forward",
    "event_loop_without_model_owned_continuation_policy",
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = load_module("bounded_work_harness", HARNESS_PATH)
less = load_module("bounded_work_less_scaffolded", LESS_RUNNER_PATH)


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


def make_backend(api_key: str):
    return harness.make_backend(
        model=MODEL,
        base_url=BASE_URL,
        api_key=api_key,
        max_tokens=5000,
    )


def control_prompt(control: str) -> str:
    base = """
You are in a Step 5 control condition for bounded autonomous work.

Within the Hamut'ay event-loop / continuity research context, choose or shape
one bounded investigation that can produce a concrete, auditable artifact. Use
the terminal surface to submit selected_goal, work_artifact, policy_decision,
evidence_used, and continuation_request.

Choose the policy action your artifact supports. Do not invent evidence. If
the work is complete under its declared scope, use stop_complete. If external
evidence is missing, use ask_external_evidence. If work remains open but no
specific continuation is justified, use defer. If the work should not continue,
use abandon.
""".strip()
    if control == "direct_one_shot":
        return base + """

This is the direct one-shot control. There is no scheduler and no event-loop
requested-context recall. Complete what can be completed in this one call. Set
continuation_request to {"requested": false}; no scheduler will consume it.
""".rstrip()
    if control == "identity_only_carry_forward_first":
        return base + """

This is the first call of the identity-only carry-forward control. A second
ordinary conversational call may occur, but there will be no scheduler event
and no event-loop requested-context recall. If a second call would improve the
artifact, you may choose continue_after, but set continuation_request to
{"requested": false} because no scheduler will consume it.
""".rstrip()
    if control == "identity_only_carry_forward_second":
        return """
Continue the prior bounded investigation using only the durable state and
ordinary conversation history available to you. You are not receiving an
event-loop requested-context recall envelope. Submit the best current artifact
and policy decision through submit_autonomous_work_artifact. Set
continuation_request to {"requested": false}.
""".strip()
    if control == "harness_selected_first":
        return base + """

This is the first wake of a scheduler control where the harness, not you, will
select exactly one follow-up wake after this wake completes. Do not schedule a
continuation yourself. Set continuation_request to {"requested": false}. Your
policy_decision may still honestly describe whether the current artifact is
complete, partial, blocked, deferred, or abandoned.
""".rstrip()
    if control == "harness_selected_followup":
        return """
This follow-up wake was selected by the harness, not by a model-owned
continuation policy. Use the recalled selected_goal and work_artifact from the
first wake to refine or complete the work. Submit the best current artifact and
policy decision through submit_autonomous_work_artifact. Set
continuation_request to {"requested": false}.
""".strip()
    raise ValueError(f"unknown control prompt: {control}")


def append_first_event(
    store: EventStore,
    *,
    control: str,
    label: str,
) -> dict[str, Any]:
    event = harness.build_pending_event(
        purpose=control_prompt(control),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=harness.seed_record_id(),
        label=label,
        not_before=harness.FIRST_NOT_BEFORE,
        terminal_surface=harness.decision_surface(),
    )
    store.append(event)
    return event


def latest_completed_for_label(
    event_records: list[dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    ids = {
        str(record.get("event_id"))
        for record in event_records
        if record.get("label") == label and record.get("event_id")
    }
    completed = [
        record
        for record in event_records
        if record.get("status") == "completed" and str(record.get("event_id")) in ids
    ]
    return completed[-1] if completed else {}


def append_harness_followup(
    store: EventStore,
    *,
    first_completed: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    result_record_id = first_completed.get("result_record_id")
    wake_cycle = first_completed.get("wake_cycle")
    if not result_record_id or not isinstance(wake_cycle, int):
        raise RuntimeError("completed first wake lacks result_record_id/wake_cycle")
    event = harness.build_pending_event(
        purpose=control_prompt("harness_selected_followup"),
        requested_context=[
            {"tool": "recall", "cycle": 1},
            {
                "tool": "recall",
                "record_id": result_record_id,
                "field": "selected_goal",
            },
            {
                "tool": "recall",
                "record_id": result_record_id,
                "field": "work_artifact",
            },
        ],
        scheduled_by_cycle=wake_cycle,
        scheduled_by_record_id=result_record_id,
        label=label,
        not_before="2026-06-01T02:00:00+00:00",
        terminal_surface=harness.followup_surface(str(result_record_id)),
    )
    event["continuation_ownership"] = "harness_owned"
    event["control_condition"] = label
    store.append(event)
    return event


def records_score(records: list[dict[str, Any]]) -> dict[str, Any]:
    final = less.final_record(records)
    raw = final.get("raw_output") if isinstance(final, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    validations = [
        less.validation_status(record)
        for record in records
        if isinstance(record.get("raw_output"), dict) and record.get("cycle", 0) > 1
    ]
    selected_goal = raw.get("selected_goal")
    selected_goal = selected_goal if isinstance(selected_goal, dict) else {}
    return {
        "scoreable": bool(records and raw),
        "goal_provenance": selected_goal.get("goal_provenance_self_assessment")
        or "ambiguous",
        "artifact_status": less.classify_artifact(raw),
        "policy_action": less._policy_action(raw),
        "policy_action_status": less.classify_policy_action(raw),
        "action_artifact_consistency": less.classify_consistency(raw),
        "repair_dependence": less.repair_dependence(validations),
        "wake_validations": validations,
        "final_cycle": final.get("cycle"),
        "raw_output_present": bool(raw),
    }


def event_loop_recall_present(event_records: list[dict[str, Any]]) -> bool:
    for record in event_records:
        for item in record.get("context_results") or []:
            request = item.get("request") or {}
            if request.get("tool") == "recall" and request.get("field") in {
                "selected_goal",
                "work_artifact",
            }:
                result = item.get("result")
                if isinstance(result, dict) and "error" not in result:
                    return True
    return False


def scheduler_trace_present(event_records: list[dict[str, Any]]) -> bool:
    return any(record.get("record_type") == "event_status" for record in event_records)


def completed_event_count(event_records: list[dict[str, Any]]) -> int:
    return len([record for record in event_records if record.get("status") == "completed"])


def continuation_ownership(event_records: list[dict[str, Any]]) -> str:
    model_owned = any(
        record.get("record_type") == "policy_disposition"
        and record.get("policy_action") == "continue_after"
        and record.get("continuation_event_id")
        for record in event_records
    )
    harness_owned = any(record.get("continuation_ownership") == "harness_owned" for record in event_records)
    if model_owned:
        return "model_owned"
    if harness_owned:
        return "harness_owned"
    return "none"


def unsupported_or_contaminated(score: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    final = less.final_record(records)
    raw = final.get("raw_output") if isinstance(final, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    evidence_used = raw.get("evidence_used")
    evidence_used = evidence_used if isinstance(evidence_used, list) else []
    text = json.dumps(raw, sort_keys=True, default=str).lower()
    unsupported = (
        score.get("artifact_status") in {"complete_supported", "complete_with_losses"}
        and not evidence_used
    )
    mentions_requested_context = (
        "event-loop requested-context" in text
        or "event-loop requested context" in text
    )
    negates_requested_context = (
        "no event-loop requested-context" in text
        or "no event-loop requested context" in text
        or "without event-loop requested-context" in text
        or "without event-loop requested context" in text
    )
    contaminated = mentions_requested_context and not negates_requested_context
    return {
        "unsupported_claim_flag": unsupported,
        "contamination_flag": contaminated,
    }


def finalize_row(
    *,
    condition: str,
    log_path: Path,
    event_path: Path | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = load_records(log_path)
    event_records = EventStore(event_path).read_records() if event_path else []
    score = records_score(records)
    score.update(unsupported_or_contaminated(score, records))
    score.update(
        {
            "scheduler_trace_present": scheduler_trace_present(event_records),
            "event_loop_recall_present": event_loop_recall_present(event_records),
            "completed_event_count": completed_event_count(event_records),
            "continuation_ownership": continuation_ownership(event_records),
        }
    )
    return {
        "condition": condition,
        "model": MODEL,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": (
            str(event_path.relative_to(PROJECT_ROOT)) if event_path else None
        ),
        "error": error,
        "event_summary": (
            summarize_event_log(event_records, now=FINAL_NOW) if event_records else {}
        ),
        "score": score,
    }


def run_direct_one_shot(api_key: str) -> dict[str, Any]:
    log_path = EXP_DIR / f"{safe_model_name(MODEL)}_direct_one_shot.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")
    session = make_session(backend=make_backend(api_key), model=MODEL, log_path=log_path)
    session._state_validator = less.LessScaffoldedValidator()
    error = None
    try:
        session.exchange(
            control_prompt("direct_one_shot"),
            terminal_surface=harness.decision_surface(),
        )
    except Exception as exc:  # noqa: BLE001
        error = {"type": type(exc).__name__, "message": str(exc)}
    return finalize_row(condition="direct_one_shot", log_path=log_path, error=error)


def run_identity_only(api_key: str) -> dict[str, Any]:
    log_path = EXP_DIR / f"{safe_model_name(MODEL)}_identity_only_carry_forward.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")
    session = make_session(backend=make_backend(api_key), model=MODEL, log_path=log_path)
    session._state_validator = less.LessScaffoldedValidator()
    error = None
    try:
        session.exchange(
            control_prompt("identity_only_carry_forward_first"),
            terminal_surface=harness.decision_surface(),
        )
        session.exchange(
            control_prompt("identity_only_carry_forward_second"),
            terminal_surface=harness.followup_surface("identity-only-prior-state"),
        )
    except Exception as exc:  # noqa: BLE001
        error = {"type": type(exc).__name__, "message": str(exc)}
    return finalize_row(
        condition="identity_only_carry_forward",
        log_path=log_path,
        error=error,
    )


def run_harness_scheduler_control(api_key: str, condition: str) -> dict[str, Any]:
    safe = safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe}_{condition}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session = make_session(backend=make_backend(api_key), model=MODEL, log_path=log_path)
    session._state_validator = less.LessScaffoldedValidator()
    store = EventStore(event_path)
    first_label = f"{condition}-first"
    append_first_event(
        store,
        control="harness_selected_first",
        label=first_label,
    )
    error = None
    try:
        step_pending_events(
            session,
            store,
            limit=1,
            now=FIRST_DUE_NOW,
            auto_continuations=False,
            policy_dispositions=True,
        )
        first_completed = latest_completed_for_label(store.read_records(), first_label)
        append_harness_followup(
            store,
            first_completed=first_completed,
            label=f"{condition}-followup",
        )
        step_pending_events(
            session,
            store,
            limit=1,
            now=FOLLOWUP_DUE_NOW,
            auto_continuations=False,
            policy_dispositions=True,
        )
    except Exception as exc:  # noqa: BLE001
        error = {"type": type(exc).__name__, "message": str(exc)}
    return finalize_row(
        condition=condition,
        log_path=log_path,
        event_path=event_path,
        error=error,
    )


def summarize_controls(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [row.get("score", {}) for row in rows]
    return {
        "rows": len(rows),
        "errors": sum(1 for row in rows if row.get("error")),
        "scoreable": sum(1 for score in scores if score.get("scoreable")),
        "scheduler_trace_present": sum(1 for score in scores if score.get("scheduler_trace_present")),
        "event_loop_recall_present": sum(1 for score in scores if score.get("event_loop_recall_present")),
        "unsupported_claim_flags": sum(1 for score in scores if score.get("unsupported_claim_flag")),
        "contamination_flags": sum(1 for score in scores if score.get("contamination_flag")),
        "artifact_status_counts": dict(Counter(score.get("artifact_status") for score in scores)),
        "policy_action_counts": dict(Counter(score.get("policy_action") for score in scores)),
        "consistency_counts": dict(Counter(score.get("action_artifact_consistency") for score in scores)),
        "goal_provenance_counts": dict(Counter(score.get("goal_provenance") for score in scores)),
        "continuation_ownership_counts": dict(Counter(score.get("continuation_ownership") for score in scores)),
    }


def treatment_comparison() -> dict[str, Any]:
    treatment = load_json(TREATMENT_RESULTS_PATH)
    summary = treatment.get("summary") if isinstance(treatment, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    return {
        "path": str(TREATMENT_RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "rows": summary.get("rows"),
        "artifact_status_counts": summary.get("artifact_status_counts"),
        "control_loop_trace": {
            "multi_wake_completed": summary.get("multi_wake_completed"),
            "first_policy_action_counts": summary.get("first_policy_action_counts"),
            "final_policy_action_counts": summary.get("final_policy_action_counts"),
        },
        "consistency_counts": summary.get("consistency_counts"),
        "goal_provenance_counts": summary.get("goal_provenance_counts"),
    }


def hypothesis_results(rows: list[dict[str, Any]], comparison: dict[str, Any]) -> dict[str, bool]:
    by_condition = {row["condition"]: row.get("score", {}) for row in rows}
    return {
        "H901_controls_are_scoreable": sum(
            1 for score in by_condition.values() if score.get("scoreable")
        )
        >= 3,
        "H902_direct_one_shot_lacks_control_loop_trace": not by_condition.get(
            "direct_one_shot",
            {},
        ).get("scheduler_trace_present"),
        "H903_harness_selected_continuation_separates_scheduler_from_policy_ownership": (
            by_condition.get("scheduler_harness_selected_continuation", {}).get(
                "completed_event_count"
            )
            == 2
            and by_condition.get("scheduler_harness_selected_continuation", {}).get(
                "continuation_ownership"
            )
            == "harness_owned"
        ),
        "H904_identity_only_lacks_event_loop_recall_trace": not by_condition.get(
            "identity_only_carry_forward",
            {},
        ).get("event_loop_recall_present"),
        "H905_event_loop_without_model_owned_policy_distinguishable": (
            by_condition.get(
                "event_loop_without_model_owned_continuation_policy",
                {},
            ).get("event_loop_recall_present")
            and by_condition.get(
                "event_loop_without_model_owned_continuation_policy",
                {},
            ).get("continuation_ownership")
            == "harness_owned"
        ),
        "H906_treatment_comparison_recorded": bool(
            comparison.get("artifact_status_counts")
            and comparison.get("control_loop_trace")
            and comparison.get("consistency_counts")
            and comparison.get("goal_provenance_counts")
        ),
    }


def main() -> None:
    if "--rescore" in sys.argv:
        rows = [
            finalize_row(
                condition="direct_one_shot",
                log_path=EXP_DIR / f"{safe_model_name(MODEL)}_direct_one_shot.jsonl",
            ),
            finalize_row(
                condition="scheduler_harness_selected_continuation",
                log_path=EXP_DIR
                / f"{safe_model_name(MODEL)}_scheduler_harness_selected_continuation.jsonl",
                event_path=default_event_log_path(
                    EXP_DIR
                    / f"{safe_model_name(MODEL)}_scheduler_harness_selected_continuation.jsonl"
                ),
            ),
            finalize_row(
                condition="identity_only_carry_forward",
                log_path=EXP_DIR
                / f"{safe_model_name(MODEL)}_identity_only_carry_forward.jsonl",
            ),
            finalize_row(
                condition="event_loop_without_model_owned_continuation_policy",
                log_path=EXP_DIR
                / f"{safe_model_name(MODEL)}_event_loop_without_model_owned_continuation_policy.jsonl",
                event_path=default_event_log_path(
                    EXP_DIR
                    / f"{safe_model_name(MODEL)}_event_loop_without_model_owned_continuation_policy.jsonl"
                ),
            ),
        ]
        summary = summarize_controls(rows)
        comparison = treatment_comparison()
        payload = {
            "condition": CONDITION,
            "model": MODEL,
            "controls": CONTROLS,
            "summary": summary,
            "treatment_comparison": comparison,
            "hypothesis_results": hypothesis_results(rows, comparison),
            "results": rows,
            "rescore": {
                "source": "existing_trace_files",
                "reason": "Correct contamination heuristic to distinguish negated requested-context claims.",
            },
        }
        RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(json.dumps(payload["hypothesis_results"], indent=2, sort_keys=True))
        print(f"rescored {RESULTS_PATH.relative_to(PROJECT_ROOT)}")
        return

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    rows = [
        run_direct_one_shot(api_key),
        run_harness_scheduler_control(
            api_key,
            "scheduler_harness_selected_continuation",
        ),
        run_identity_only(api_key),
        run_harness_scheduler_control(
            api_key,
            "event_loop_without_model_owned_continuation_policy",
        ),
    ]
    summary = summarize_controls(rows)
    comparison = treatment_comparison()
    payload = {
        "condition": CONDITION,
        "model": MODEL,
        "controls": CONTROLS,
        "summary": summary,
        "treatment_comparison": comparison,
        "hypothesis_results": hypothesis_results(rows, comparison),
        "results": rows,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2, sort_keys=True))
    print(f"wrote {RESULTS_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
