"""Run the bounded autonomy simulated-time scheduler experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    run_next_event,
)
from hamutay.protocol_recovery import DeterministicProtocolRecoveryBuilder
from hamutay.taste_open import ExchangeResult, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MAX_WAKE_DEPTH = 4
NO_PROGRESS_LIMIT = 2
PROGRESS_FIELDS = {
    "research_findings",
    "open_questions",
    "declared_losses",
    "loop_status",
}
SIM_START = datetime(2026, 6, 5, 14, 0, tzinfo=timezone.utc)


BASE_STATE = {
    "response": "Bounded autonomy seed established.",
    "probe_id": "bounded-autonomy-des",
    "loop_status": "initialized",
    "research_findings": [
        {
            "entry": 1,
            "kind": "baseline",
            "content": "No continuation wake has run yet.",
        }
    ],
    "open_questions": [
        "Can bounded continuation distinguish progress from stasis?"
    ],
    "declared_losses": [],
}


@dataclass(frozen=True)
class ContinuationRequest:
    label: str
    purpose: str = (
        "Continue the bounded autonomy diagnostic. Use recalled state to decide "
        "whether to make progress, complete, declare loss, or stop."
    )
    requested_context: list[dict[str, Any]] = field(
        default_factory=lambda: [{"tool": "recall", "cycle": 1}]
    )


@dataclass(frozen=True)
class StepOutput:
    raw_output: dict[str, Any]
    continuations: tuple[ContinuationRequest, ...] = ()


def finding(entry: int, kind: str, content: str) -> dict[str, Any]:
    return {"entry": entry, "kind": kind, "content": content}


SCENARIOS: dict[str, list[StepOutput]] = {
    "progress_complete": [
        StepOutput(
            raw_output={
                "response": "Progress made; scheduling one continuation.",
                "loop_status": "in_progress",
                "research_findings": [
                    BASE_STATE["research_findings"][0],
                    finding(
                        2,
                        "progress",
                        "First wake narrowed the autonomy question to loop policy.",
                    ),
                ],
                "open_questions": [
                    "Can the second wake terminate cleanly after progress?"
                ],
            },
            continuations=(
                ContinuationRequest(label="progress-complete-followup"),
            ),
        ),
        StepOutput(
            raw_output={
                "response": "Continuation completed with a terminal finding.",
                "loop_status": "complete",
                "research_findings": [
                    BASE_STATE["research_findings"][0],
                    finding(
                        2,
                        "progress",
                        "First wake narrowed the autonomy question to loop policy.",
                    ),
                    finding(
                        3,
                        "completion",
                        "Second wake reached terminal state without rescheduling.",
                    ),
                ],
                "open_questions": [],
            },
        ),
    ],
    "stasis_cutoff": [
        StepOutput(
            raw_output={
                "response": "No new durable progress; scheduling another look.",
            },
            continuations=(ContinuationRequest(label="stasis-repeat-1"),),
        ),
        StepOutput(
            raw_output={
                "response": "Still no new durable progress; scheduling another look.",
            },
            continuations=(ContinuationRequest(label="stasis-repeat-2"),),
        ),
        StepOutput(
            raw_output={
                "response": "This wake should not run if stasis cutoff works.",
                "loop_status": "unexpected_third_stasis_wake",
            },
        ),
    ],
    "recursive_drift": [
        StepOutput(
            raw_output={
                "response": "Progress is uncertain; scheduling two branches.",
                "loop_status": "in_progress",
                "research_findings": [
                    BASE_STATE["research_findings"][0],
                    finding(
                        2,
                        "drift",
                        "Wake attempted multiple continuations in one cycle.",
                    ),
                ],
            },
            continuations=(
                ContinuationRequest(label="recursive-drift-a"),
                ContinuationRequest(label="recursive-drift-b"),
            ),
        ),
    ],
    "strict_merge_failure": [
        StepOutput(
            raw_output={
                "response": (
                    "### Invalidated Assumptions\n"
                    "1. Bounded loop failures might be silent.\n"
                    "- Evidence: this wake intentionally overlaps delete/update keys.\n\n"
                    "### New Constraints\n"
                    "- Failed continuation must not advance accepted state.\n\n"
                    "### Next Actions\n"
                    "1. Inspect sidecar failure context and protocol recovery."
                ),
                "research_findings": [
                    finding(
                        2,
                        "invalid",
                        "This should be rejected by strict merge.",
                    )
                ],
                "deleted_regions": ["research_findings"],
            },
        ),
    ],
}


class FakeCurator:
    def curate(self, **kwargs) -> dict:
        return {
            "curator_type": "fake",
            "summary": (
                f"Bounded autonomy continuity from cycle {kwargs['cycle']}: "
                "preserve probe_id, loop_status, and research trail."
            ),
            "supported_facts": [
                "bounded autonomy diagnostic is running under simulated time"
            ],
        }


@dataclass
class ScriptedBackend:
    outputs: list[StepOutput]

    def __post_init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ) -> ExchangeResult:
        del extra_tools
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "experiment_label": experiment_label,
            }
        )
        if not self.outputs:
            raise RuntimeError("scripted backend exhausted")
        step = self.outputs.pop(0)
        tool_activity = []
        if tool_executor is not None:
            for request in step.continuations:
                result = tool_executor.execute(
                    "schedule_event",
                    {
                        "purpose": request.purpose,
                        "requested_context": request.requested_context,
                        "label": request.label,
                    },
                )
                tool_activity.append(tool_executor.activity_log[-1])
                if "error" in result:
                    raise RuntimeError(f"schedule_event failed: {result['error']}")
        return ExchangeResult(
            raw_output=step.raw_output,
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=5,
            tool_activity=tool_activity,
        )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def make_session(scenario: str) -> OpenTasteSession:
    log_path = EXP_DIR / f"{scenario}.jsonl"
    return OpenTasteSession(
        model="fake-bounded-autonomy",
        backend=ScriptedBackend(
            [StepOutput(BASE_STATE), *SCENARIOS[scenario]]
        ),
        log_path=str(log_path),
        event_log_path=str(default_event_log_path(log_path)),
        experiment_label=f"bounded_autonomy_des_{scenario}",
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
        continuity_curator=FakeCurator(),
        protocol_recovery_builder=DeterministicProtocolRecoveryBuilder(),
    )


def append_initial_event(session: OpenTasteSession, event_path: Path) -> dict[str, Any]:
    event = build_pending_event(
        purpose=(
            "Initial bounded-autonomy continuation. Use recalled seed state to "
            "make progress, complete, declare loss, or schedule one continuation."
        ),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
        label="bounded-autonomy-initial",
        not_before=SIM_START.isoformat(),
    )
    EventStore(event_path).append(event)
    return event


def latest_statuses(event_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in event_records:
        event_id = record.get("event_id")
        if event_id:
            latest[str(event_id)] = record
    return latest


def scheduled_count_for_record(record: dict[str, Any]) -> int:
    events = record.get("scheduled_events")
    return len(events) if isinstance(events, list) else 0


def progress_changed(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return any(before.get(field) != after.get(field) for field in PROGRESS_FIELDS)


def wake_records(session_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in session_records
        if "self_scheduled_reflection" in str(record.get("user_message", ""))
    ]


def classify_and_score(
    scenario: str,
    *,
    run_error: str | None,
    stop_reason: str | None,
    progress_wake_count: int,
    no_progress_streak: int,
) -> dict[str, Any]:
    log_path = EXP_DIR / f"{scenario}.jsonl"
    event_path = default_event_log_path(log_path)
    session_records = load_jsonl(log_path)
    event_records = load_jsonl(event_path)
    wakes = wake_records(session_records)
    latest = latest_statuses(event_records)
    pending = [
        record for record in latest.values() if record.get("status") == "pending"
    ]
    completed = [
        record for record in latest.values() if record.get("status") == "completed"
    ]
    failed = [
        record for record in latest.values() if record.get("status") == "failed"
    ]
    final_state = session_records[-1].get("state") if session_records else {}
    final_state = final_state if isinstance(final_state, dict) else {}
    seed_state = session_records[0].get("state") if session_records else {}
    seed_state = seed_state if isinstance(seed_state, dict) else {}
    failed_wake = next(
        (
            record for record in reversed(wakes)
            if record.get("status") == "failed"
        ),
        {},
    )
    failure_classification = failed_wake.get("failure_classification")
    protocol_recovery = failed_wake.get("protocol_recovery")
    max_scheduled = max(
        [scheduled_count_for_record(record) for record in wakes] or [0]
    )
    if failed:
        classification = "failed"
    elif max_scheduled > 1:
        classification = "drift"
    elif final_state.get("loop_status") == "complete":
        classification = "complete"
    elif no_progress_streak >= NO_PROGRESS_LIMIT:
        classification = "stasis"
    elif len(wakes) >= MAX_WAKE_DEPTH:
        classification = "depth_limit"
    else:
        classification = stop_reason or "incomplete"
    return {
        "scenario": scenario,
        "classification": classification,
        "run_error": run_error,
        "stop_reason": stop_reason,
        "wake_count": len(wakes),
        "completed_event_count": len(completed),
        "failed_event_count": len(failed),
        "pending_event_count": len(pending),
        "progress_wake_count": progress_wake_count,
        "no_progress_streak": no_progress_streak,
        "max_continuations_scheduled_in_one_wake": max_scheduled,
        "accepted_state_advanced_after_failure": (
            final_state != seed_state if failed else None
        ),
        "failure_classification_logged": isinstance(failure_classification, dict),
        "protocol_recovery_logged": (
            isinstance(protocol_recovery, dict)
            and protocol_recovery.get("status") == "success"
        ),
        "protocol_recovery_candidate_rows": (
            len(protocol_recovery.get("artifact", {}).get("candidate_rows", []))
            if isinstance(protocol_recovery, dict)
            else 0
        ),
        "event_status_sequences": [
            {
                "event_id": event_id,
                "status": record.get("status"),
            }
            for event_id, record in latest.items()
        ],
        "final_loop_status": final_state.get("loop_status"),
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
    }


def run_scenario(scenario: str) -> dict[str, Any]:
    log_path = EXP_DIR / f"{scenario}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    session = make_session(scenario)
    session.exchange("seed bounded autonomy state", force_memory=None)
    append_initial_event(session, event_path)
    store = EventStore(event_path)

    progress_wake_count = 0
    no_progress_streak = 0
    stop_reason: str | None = None
    run_error: str | None = None
    now = SIM_START
    for _ in range(MAX_WAKE_DEPTH):
        before = json.loads(json.dumps(session.state or {}, default=str))
        try:
            result = run_next_event(session, store, now=now)
        except Exception as e:  # noqa: BLE001 -- expected for failure scenario
            run_error = f"{type(e).__name__}: {e}"
            stop_reason = "event_failed"
            break
        if result.get("status") == "none":
            stop_reason = "no_pending_event"
            break
        if result.get("status") == "expired":
            stop_reason = "event_expired"
            break

        after = json.loads(json.dumps(session.state or {}, default=str))
        if progress_changed(before, after):
            progress_wake_count += 1
            no_progress_streak = 0
        else:
            no_progress_streak += 1

        records = load_jsonl(log_path)
        last_wake = wake_records(records)[-1]
        if scheduled_count_for_record(last_wake) > 1:
            stop_reason = "recursive_drift"
            break
        if after.get("loop_status") == "complete":
            stop_reason = "complete"
            break
        if no_progress_streak >= NO_PROGRESS_LIMIT:
            stop_reason = "stasis"
            break
        now += timedelta(minutes=1)
    else:
        stop_reason = "depth_limit"

    return classify_and_score(
        scenario,
        run_error=run_error,
        stop_reason=stop_reason,
        progress_wake_count=progress_wake_count,
        no_progress_streak=no_progress_streak,
    )


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario = {result["scenario"]: result for result in results}
    return {
        "hypothesis_results": {
            "H77_bounded_continuation_completes": (
                by_scenario["progress_complete"]["classification"] == "complete"
                and by_scenario["progress_complete"]["progress_wake_count"] >= 2
                and by_scenario["progress_complete"]["pending_event_count"] == 0
            ),
            "H78_stasis_detected": (
                by_scenario["stasis_cutoff"]["classification"] == "stasis"
                and by_scenario["stasis_cutoff"]["no_progress_streak"]
                >= NO_PROGRESS_LIMIT
            ),
            "H79_recursive_scheduling_drift_observable": (
                by_scenario["recursive_drift"]["classification"] == "drift"
                and by_scenario["recursive_drift"][
                    "max_continuations_scheduled_in_one_wake"
                ]
                > 1
            ),
            "H80_strict_failure_bounded_and_diagnostic": (
                by_scenario["strict_merge_failure"]["classification"] == "failed"
                and by_scenario["strict_merge_failure"][
                    "accepted_state_advanced_after_failure"
                ]
                is False
                and by_scenario["strict_merge_failure"][
                    "failure_classification_logged"
                ]
                and by_scenario["strict_merge_failure"][
                    "protocol_recovery_logged"
                ]
            ),
        },
        "summary": {
            "scenario_count": len(results),
            "classifications": {
                result["scenario"]: result["classification"]
                for result in results
            },
        },
    }


def main() -> None:
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")
    results = [run_scenario(scenario) for scenario in SCENARIOS]
    payload = {
        "policy": {
            "max_wake_depth": MAX_WAKE_DEPTH,
            "no_progress_limit": NO_PROGRESS_LIMIT,
            "progress_fields": sorted(PROGRESS_FIELDS),
        },
        "results": results,
        **aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
