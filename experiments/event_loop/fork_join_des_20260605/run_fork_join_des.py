"""Run the fork/join simulated-time scheduler experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import (
    EventStore,
    build_pending_event,
    default_event_log_path,
    run_next_event,
    summarize_event_log,
)
from hamutay.protocol_recovery import DeterministicProtocolRecoveryBuilder
from hamutay.taste_open import ExchangeResult, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
SIM_NOW = datetime(2026, 6, 5, 16, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ContinuationRequest:
    label: str
    purpose: str
    requested_context: list[dict[str, Any]] = field(
        default_factory=lambda: [{"tool": "recall", "cycle": 2}]
    )


@dataclass(frozen=True)
class StepOutput:
    raw_output: dict[str, Any]
    continuations: tuple[ContinuationRequest, ...] = ()


def finding(entry: int, kind: str, content: str) -> dict[str, Any]:
    return {"entry": entry, "kind": kind, "content": content}


BASE_STATE = {
    "response": "Fork/join seed established.",
    "probe_id": "fork-join-des",
    "loop_status": "initialized",
    "research_findings": [
        finding(1, "baseline", "No fork branches have run yet.")
    ],
    "joined_findings": [],
}

FORK_STEP = StepOutput(
    raw_output={
        "response": "Fork point reached; scheduling branch A and branch B.",
        "loop_status": "forked",
        "research_findings": [
            BASE_STATE["research_findings"][0],
            finding(2, "fork", "Two isolated branch continuations requested."),
        ],
        "fork_policy": {
            "mode": "explicit_fork",
            "branch_budget": 2,
            "join_required": True,
        },
    },
    continuations=(
        ContinuationRequest(
            label="branch-a",
            purpose=(
                "Branch A: inspect progress semantics. Do not schedule further "
                "events. Preserve branch_id."
            ),
        ),
        ContinuationRequest(
            label="branch-b",
            purpose=(
                "Branch B: inspect failure/disposition semantics. Do not "
                "schedule further events. Preserve branch_id."
            ),
        ),
    ),
)

BRANCH_A_SUCCESS = StepOutput(
    raw_output={
        "response": "Branch A completed in isolation.",
        "branch_id": "branch-a",
        "branch_findings": [
            finding(
                1,
                "branch_a",
                "Progress semantics should count durable field deltas.",
            )
        ],
    }
)

BRANCH_B_SUCCESS = StepOutput(
    raw_output={
        "response": "Branch B completed in isolation.",
        "branch_id": "branch-b",
        "branch_findings": [
            finding(
                1,
                "branch_b",
                "Disposition semantics should preserve suppressed branch reasons.",
            )
        ],
    }
)

BRANCH_A_FAILURE = StepOutput(
    raw_output={
        "response": (
            "### Invalidated Assumptions\n"
            "1. Fork branches might fail silently.\n"
            "- Evidence: branch A intentionally overlaps delete/update keys.\n\n"
            "### New Constraints\n"
            "- Failed branches must not advance accepted branch state.\n\n"
            "### Next Actions\n"
            "1. Suppress sibling branch B with source-linked policy evidence."
        ),
        "branch_findings": [
            finding(1, "invalid", "This branch update should be rejected.")
        ],
        "deleted_regions": ["branch_findings"],
    }
)


class FakeCurator:
    def curate(self, **kwargs) -> dict:
        return {
            "curator_type": "fake",
            "summary": (
                f"Fork/join continuity from cycle {kwargs['cycle']}: "
                "preserve fork policy, branch outputs, and join status."
            ),
        }


@dataclass
class ScriptedBackend:
    outputs: list[StepOutput]

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ) -> ExchangeResult:
        del model, system, messages, experiment_label, extra_tools
        if not self.outputs:
            raise RuntimeError("scripted backend exhausted")
        step = self.outputs.pop(0)
        tool_activity = []
        if tool_executor is not None:
            for request in step.continuations:
                tool_executor.execute(
                    "schedule_event",
                    {
                        "purpose": request.purpose,
                        "requested_context": request.requested_context,
                        "label": request.label,
                    },
                )
                tool_activity.append(tool_executor.activity_log[-1])
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


def make_session(
    *,
    log_path: Path,
    event_path: Path,
    label: str,
    outputs: list[StepOutput],
) -> OpenTasteSession:
    return OpenTasteSession(
        model="fake-fork-join",
        backend=ScriptedBackend(outputs),
        log_path=str(log_path),
        event_log_path=str(event_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
        continuity_curator=FakeCurator(),
        protocol_recovery_builder=DeterministicProtocolRecoveryBuilder(),
    )


def seed_isolated_session(
    session: OpenTasteSession,
    coordinator_records: list[dict[str, Any]],
) -> None:
    session.seed_history(coordinator_records, up_to_cycle=3)


def coordinator_for(scenario: str) -> tuple[OpenTasteSession, Path, Path]:
    log_path = EXP_DIR / f"{scenario}_coordinator.jsonl"
    event_path = default_event_log_path(log_path)
    session = make_session(
        log_path=log_path,
        event_path=event_path,
        label=f"fork_join_{scenario}_coordinator",
        outputs=[StepOutput(BASE_STATE), FORK_STEP],
    )
    session.exchange("seed fork join state", force_memory=None)
    session.exchange("schedule explicit fork branches", force_memory=None)
    return session, log_path, event_path


def branch_session(
    *,
    scenario: str,
    branch: str,
    event_path: Path,
    coordinator_records: list[dict[str, Any]],
    output: StepOutput,
) -> tuple[OpenTasteSession, Path, str | None]:
    log_path = EXP_DIR / f"{scenario}_{branch}.jsonl"
    session = make_session(
        log_path=log_path,
        event_path=event_path,
        label=f"fork_join_{scenario}_{branch}",
        outputs=[output],
    )
    seed_isolated_session(session, coordinator_records)
    run_error = None
    try:
        run_next_event(session, EventStore(event_path), now=SIM_NOW)
    except Exception as e:  # noqa: BLE001 -- branch failure scenario data
        run_error = f"{type(e).__name__}: {e}"
    return session, log_path, run_error


def append_join_event(
    *,
    event_path: Path,
    fork_record: dict[str, Any],
    branch_outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    purpose = (
        "Join completed fork branches. Branch outputs are explicit policy "
        "context, not recalled memory:\n"
        + json.dumps(branch_outputs, indent=2, default=str)
    )
    event = build_pending_event(
        purpose=purpose,
        requested_context=[{"tool": "recall", "cycle": 2}],
        scheduled_by_cycle=int(fork_record["cycle"]),
        scheduled_by_record_id=UUID(str(fork_record["record_id"])),
        label="fork-join",
    )
    EventStore(event_path).append(event)
    return event


def join_session(
    *,
    scenario: str,
    event_path: Path,
    coordinator_records: list[dict[str, Any]],
    branch_outputs: list[dict[str, Any]],
) -> tuple[OpenTasteSession, Path]:
    joined_findings = [
        {
            "branch_id": output["branch_id"],
            "findings": output.get("branch_findings", []),
        }
        for output in branch_outputs
    ]
    log_path = EXP_DIR / f"{scenario}_join.jsonl"
    session = make_session(
        log_path=log_path,
        event_path=event_path,
        label=f"fork_join_{scenario}_join",
        outputs=[
            StepOutput(
                raw_output={
                    "response": "Join completed from explicit branch outputs.",
                    "loop_status": "joined",
                    "joined_findings": joined_findings,
                }
            )
        ],
    )
    seed_isolated_session(session, coordinator_records)
    run_next_event(session, EventStore(event_path), now=SIM_NOW)
    return session, log_path


def latest_event_by_label(event_records: list[dict[str, Any]]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    first_label_by_id = {
        record["event_id"]: record.get("label")
        for record in event_records
        if record.get("status") == "pending"
    }
    for record in event_records:
        event_id = record.get("event_id")
        label = first_label_by_id.get(event_id)
        if label:
            latest[str(label)] = record
    return latest


def isolation_violations(branch_logs: list[Path]) -> list[dict[str, Any]]:
    violations = []

    def strip_framework_activity(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip_framework_activity(item)
                for key, item in value.items()
                if key != "_activity_log"
            }
        if isinstance(value, list):
            return [strip_framework_activity(item) for item in value]
        return value

    for path in branch_logs:
        records = load_jsonl(path)
        wake = records[-1] if records else {}
        user_message = json.loads(wake.get("user_message", "{}"))
        context_content = [
            item.get("result", {}).get("content")
            for item in user_message.get("context_results", [])
            if isinstance(item, dict)
        ]
        text = json.dumps({
            "prior_state": strip_framework_activity(wake.get("prior_state")),
            "context_content": strip_framework_activity(context_content),
        }, default=str)
        branch_name = path.stem.rsplit("_", 1)[-1]
        sibling_terms = (
            ["\"kind\": \"branch_b\"", "\"branch_id\": \"branch-b\""]
            if branch_name == "branch-a"
            else ["\"kind\": \"branch_a\"", "\"branch_id\": \"branch-a\""]
        )
        if any(term in text for term in sibling_terms):
            violations.append({
                "branch_log": str(path.relative_to(PROJECT_ROOT)),
                "sibling_terms": sibling_terms,
            })
    return violations


def run_success() -> dict[str, Any]:
    _coordinator, coord_path, event_path = coordinator_for("fork_join_success")
    coordinator_records = load_jsonl(coord_path)
    branch_a, branch_a_path, err_a = branch_session(
        scenario="fork_join_success",
        branch="branch-a",
        event_path=event_path,
        coordinator_records=coordinator_records,
        output=BRANCH_A_SUCCESS,
    )
    branch_b, branch_b_path, err_b = branch_session(
        scenario="fork_join_success",
        branch="branch-b",
        event_path=event_path,
        coordinator_records=coordinator_records,
        output=BRANCH_B_SUCCESS,
    )
    branch_outputs = [
        branch_a.state or {},
        branch_b.state or {},
    ]
    append_join_event(
        event_path=event_path,
        fork_record=coordinator_records[-1],
        branch_outputs=branch_outputs,
    )
    join, join_path = join_session(
        scenario="fork_join_success",
        event_path=event_path,
        coordinator_records=coordinator_records,
        branch_outputs=branch_outputs,
    )
    event_summary = summarize_event_log(EventStore(event_path).read_records())
    labels = latest_event_by_label(EventStore(event_path).read_records())
    joined = join.state or {}
    violations = isolation_violations([branch_a_path, branch_b_path])
    return {
        "scenario": "fork_join_success",
        "classification": "joined",
        "coordinator_log_path": str(coord_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "branch_log_paths": [
            str(branch_a_path.relative_to(PROJECT_ROOT)),
            str(branch_b_path.relative_to(PROJECT_ROOT)),
        ],
        "join_log_path": str(join_path.relative_to(PROJECT_ROOT)),
        "branch_errors": [err for err in (err_a, err_b) if err],
        "fork_event_count": len(
            [label for label in labels if str(label).startswith("branch-")]
        ),
        "branch_completed_count": sum(
            labels.get(label, {}).get("status") == "completed"
            for label in ("branch-a", "branch-b")
        ),
        "branch_failed_count": sum(
            labels.get(label, {}).get("status") == "failed"
            for label in ("branch-a", "branch-b")
        ),
        "branch_suppressed_count": sum(
            labels.get(label, {}).get("status") == "suppressed"
            for label in ("branch-a", "branch-b")
        ),
        "join_completed": labels.get("fork-join", {}).get("status") == "completed",
        "joined_findings_count": len(joined.get("joined_findings", [])),
        "branch_isolation_violations": violations,
        "pending_after_policy": int(
            event_summary.get("pending_runnable_count", 0)
            + event_summary.get("pending_waiting_count", 0)
            + event_summary.get("pending_expired_count", 0)
        ),
        "status_counts": event_summary.get("status_counts", {}),
    }


def run_branch_failure() -> dict[str, Any]:
    _coordinator, coord_path, event_path = coordinator_for("fork_branch_failure")
    coordinator_records = load_jsonl(coord_path)
    branch_a, branch_a_path, err_a = branch_session(
        scenario="fork_branch_failure",
        branch="branch-a",
        event_path=event_path,
        coordinator_records=coordinator_records,
        output=BRANCH_A_FAILURE,
    )
    branch_records = load_jsonl(branch_a_path)
    failed_wake = branch_records[-1]
    EventStore(event_path).suppress_pending(
        policy="fork_join",
        reason="branch failure",
        suppressed_by_record_id=failed_wake["record_id"],
        suppressed_by_cycle=int(failed_wake["cycle"]),
        suppressed_by_classification="branch_failed",
    )
    event_records = EventStore(event_path).read_records()
    event_summary = summarize_event_log(event_records)
    labels = latest_event_by_label(event_records)
    failure_classification = failed_wake.get("failure_classification")
    protocol_recovery = failed_wake.get("protocol_recovery")
    return {
        "scenario": "fork_branch_failure",
        "classification": "branch_failed",
        "coordinator_log_path": str(coord_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "branch_log_paths": [str(branch_a_path.relative_to(PROJECT_ROOT))],
        "branch_errors": [err_a] if err_a else [],
        "fork_event_count": len(
            [label for label in labels if str(label).startswith("branch-")]
        ),
        "branch_completed_count": sum(
            labels.get(label, {}).get("status") == "completed"
            for label in ("branch-a", "branch-b")
        ),
        "branch_failed_count": sum(
            labels.get(label, {}).get("status") == "failed"
            for label in ("branch-a", "branch-b")
        ),
        "branch_suppressed_count": sum(
            labels.get(label, {}).get("status") == "suppressed"
            for label in ("branch-a", "branch-b")
        ),
        "join_completed": False,
        "joined_findings_count": 0,
        "branch_isolation_violations": [],
        "failure_classification_logged": isinstance(failure_classification, dict),
        "protocol_recovery_logged": (
            isinstance(protocol_recovery, dict)
            and protocol_recovery.get("status") == "success"
        ),
        "suppression_source_resolved": (
            labels.get("branch-b", {}).get("suppressed_by_record_id")
            == failed_wake["record_id"]
        ),
        "accepted_state_advanced_after_failure": (branch_a.state != failed_wake.get("prior_state")),
        "pending_after_policy": int(
            event_summary.get("pending_runnable_count", 0)
            + event_summary.get("pending_waiting_count", 0)
            + event_summary.get("pending_expired_count", 0)
        ),
        "status_counts": event_summary.get("status_counts", {}),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario = {result["scenario"]: result for result in results}
    success = by_scenario["fork_join_success"]
    failure = by_scenario["fork_branch_failure"]
    return {
        "hypothesis_results": {
            "H88_explicit_fork_not_drift": (
                success["classification"] == "joined"
                and success["fork_event_count"] == 2
                and success["pending_after_policy"] == 0
            ),
            "H89_branch_execution_isolated": (
                not success["branch_isolation_violations"]
            ),
            "H90_join_receives_all_successful_branch_outputs": (
                success["join_completed"]
                and success["joined_findings_count"] == 2
            ),
            "H91_branch_failure_bounded_and_suppresses_sibling": (
                failure["classification"] == "branch_failed"
                and failure["branch_failed_count"] == 1
                and failure["branch_suppressed_count"] == 1
                and failure["accepted_state_advanced_after_failure"] is False
                and failure["failure_classification_logged"]
                and failure["protocol_recovery_logged"]
                and failure["suppression_source_resolved"]
                and failure["pending_after_policy"] == 0
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
    results = [run_success(), run_branch_failure()]
    payload = {"results": results, **aggregate(results)}
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
