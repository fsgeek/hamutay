"""Run the durable fork-run identity simulated-time scheduler experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hamutay.event_policies import (
    BranchContextPolicy,
    ForkRunStore,
    ForkJoinPolicyRunner,
    build_fork_run_started_record,
    default_fork_run_log_path,
    finalize_failed_fork_run,
    finalize_successful_fork_run,
    latest_event_records_by_label,
)
from hamutay.events import (
    EventStore,
    default_event_log_path,
    summarize_event_log,
)
from hamutay.protocol_recovery import DeterministicProtocolRecoveryBuilder
from hamutay.taste_open import ExchangeResult, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]
SIM_NOW = datetime(2026, 6, 5, 16, 0, tzinfo=timezone.utc)
POLICY = BranchContextPolicy()
RUNNER = ForkJoinPolicyRunner(policy=POLICY, now=SIM_NOW)
BRANCH_LABELS = ("branch-a", "branch-b")


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
    "probe_id": "fork-run-identity-des",
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
                f"Fork-run identity continuity from cycle {kwargs['cycle']}: "
                "preserve durable run identity, branches, and disposition."
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
        model="fake-fork-run-identity",
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


def coordinator_for(scenario: str) -> tuple[OpenTasteSession, Path, Path]:
    log_path = EXP_DIR / f"{scenario}_coordinator.jsonl"
    event_path = default_event_log_path(log_path)
    session = make_session(
        log_path=log_path,
        event_path=event_path,
        label=f"fork_run_identity_{scenario}_coordinator",
        outputs=[StepOutput(BASE_STATE), FORK_STEP],
    )
    session.exchange("seed fork join state", force_memory=None)
    session.exchange("schedule explicit fork branches", force_memory=None)
    return session, log_path, event_path


def make_branch_session(
    *,
    scenario: str,
    branch: str,
    event_path: Path,
    output: StepOutput,
) -> tuple[OpenTasteSession, Path]:
    log_path = EXP_DIR / f"{scenario}_{branch}.jsonl"
    session = make_session(
        log_path=log_path,
        event_path=event_path,
        label=f"fork_run_identity_{scenario}_{branch}",
        outputs=[output],
    )
    return session, log_path


def join_session(
    *,
    scenario: str,
    event_path: Path,
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
        label=f"fork_run_identity_{scenario}_join",
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
    return session, log_path


def latest_event_by_label(event_records: list[dict[str, Any]]) -> dict[str, dict]:
    return latest_event_records_by_label(event_records)


def branch_private_violations(branch_logs: list[Path]) -> list[dict[str, Any]]:
    violations = []

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
            "prior_state": wake.get("prior_state"),
            "context_content": context_content,
        }, default=str)
        branch_name = path.stem.rsplit("_", 1)[-1]
        sibling_terms = (
            [
                "_activity_log",
                "branch-b",
                "inspect failure/disposition semantics",
            ]
            if branch_name == "branch-a"
            else [
                "_activity_log",
                "branch-a",
                "inspect progress semantics",
            ]
        )
        matched = [term for term in sibling_terms if term in text]
        if matched:
            violations.append({
                "branch_log": str(path.relative_to(PROJECT_ROOT)),
                "matched_terms": matched,
            })
    return violations


def policy_idempotence_holds(records: list[dict[str, Any]]) -> bool:
    once = POLICY.branch_visible_records(records)
    twice = POLICY.branch_visible_records(once)
    text = json.dumps(once, default=str)
    return once == twice and "_activity_log" not in text


def run_success() -> dict[str, Any]:
    _coordinator, coord_path, event_path = coordinator_for("fork_run_identity_success")
    coordinator_records = load_jsonl(coord_path)
    store = EventStore(event_path)
    run_store = ForkRunStore(default_fork_run_log_path(event_path))
    started_record = build_fork_run_started_record(
        fork_record=coordinator_records[-1],
        branch_labels=BRANCH_LABELS,
        fork_run_id="fork-run-success",
    )
    run_store.append(started_record)
    branch_a, branch_a_path = make_branch_session(
        scenario="fork_run_identity_success",
        branch="branch-a",
        event_path=event_path,
        output=BRANCH_A_SUCCESS,
    )
    branch_a_result = RUNNER.run_branch(
        label="branch-a",
        session=branch_a,
        store=store,
        seed_records=coordinator_records,
    )
    branch_b, branch_b_path = make_branch_session(
        scenario="fork_run_identity_success",
        branch="branch-b",
        event_path=event_path,
        output=BRANCH_B_SUCCESS,
    )
    branch_b_result = RUNNER.run_branch(
        label="branch-b",
        session=branch_b,
        store=store,
        seed_records=coordinator_records,
    )
    branch_outputs = [
        branch_a.state or {},
        branch_b.state or {},
    ]
    join_event = RUNNER.schedule_join(
        store=store,
        fork_record=coordinator_records[-1],
        branch_outputs=branch_outputs,
        requested_context=[{"tool": "recall", "cycle": 2}],
    )
    join, join_path = join_session(
        scenario="fork_run_identity_success",
        event_path=event_path,
        branch_outputs=branch_outputs,
    )
    join_result = RUNNER.run_join(
        session=join,
        store=store,
        seed_records=coordinator_records,
    )
    event_records = EventStore(event_path).read_records()
    event_summary = summarize_event_log(event_records)
    labels = latest_event_by_label(event_records)
    audit_projection = POLICY.sidecar_audit_projection(
        event_records,
        labels=BRANCH_LABELS,
    )
    final_run_record = finalize_successful_fork_run(
        started_record=started_record,
        branch_results=[branch_a_result, branch_b_result],
        join_event=join_event,
        join_result=join_result,
        sidecar_audit_projection=audit_projection,
    )
    run_store.append(final_run_record)
    run_records = run_store.read_records()
    latest_run = run_store.latest_by_run_id()[started_record["fork_run_id"]]
    joined = join.state or {}
    violations = branch_private_violations([branch_a_path, branch_b_path])
    return {
        "scenario": "fork_run_identity_success",
        "classification": "joined",
        "coordinator_log_path": str(coord_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "fork_run_log_path": str(run_store.path.relative_to(PROJECT_ROOT)),
        "branch_log_paths": [
            str(branch_a_path.relative_to(PROJECT_ROOT)),
            str(branch_b_path.relative_to(PROJECT_ROOT)),
        ],
        "join_log_path": str(join_path.relative_to(PROJECT_ROOT)),
        "runner_branch_results": [
            branch_a_result.to_dict(),
            branch_b_result.to_dict(),
        ],
        "runner_join_result": join_result.to_dict(),
        "fork_run_started_record": started_record,
        "fork_run_final_record": final_run_record,
        "fork_run_record_count": len(run_records),
        "latest_fork_run_record": latest_run,
        "branch_errors": [
            result.error
            for result in (branch_a_result, branch_b_result)
            if result.error
        ],
        "fork_event_count": len(
            [label for label in labels if str(label).startswith("branch-")]
        ),
        "branch_completed_count": sum(
            labels.get(label, {}).get("status") == "completed"
            for label in BRANCH_LABELS
        ),
        "branch_failed_count": sum(
            labels.get(label, {}).get("status") == "failed"
            for label in BRANCH_LABELS
        ),
        "branch_suppressed_count": sum(
            labels.get(label, {}).get("status") == "suppressed"
            for label in BRANCH_LABELS
        ),
        "join_completed": labels.get("fork-join", {}).get("status") == "completed",
        "joined_findings_count": len(joined.get("joined_findings", [])),
        "branch_private_violations": violations,
        "policy_idempotence_holds": policy_idempotence_holds(coordinator_records),
        "sidecar_audit_preserved": POLICY.sidecar_audit_complete(
            event_records,
            labels=BRANCH_LABELS,
        ),
        "sidecar_audit_projection": audit_projection,
        "pending_after_policy": int(
            event_summary.get("pending_runnable_count", 0)
            + event_summary.get("pending_waiting_count", 0)
            + event_summary.get("pending_expired_count", 0)
        ),
        "status_counts": event_summary.get("status_counts", {}),
    }


def run_branch_failure() -> dict[str, Any]:
    _coordinator, coord_path, event_path = coordinator_for("fork_run_identity_failure")
    coordinator_records = load_jsonl(coord_path)
    store = EventStore(event_path)
    run_store = ForkRunStore(default_fork_run_log_path(event_path))
    started_record = build_fork_run_started_record(
        fork_record=coordinator_records[-1],
        branch_labels=BRANCH_LABELS,
        fork_run_id="fork-run-failure",
    )
    run_store.append(started_record)
    branch_a, branch_a_path = make_branch_session(
        scenario="fork_run_identity_failure",
        branch="branch-a",
        event_path=event_path,
        output=BRANCH_A_FAILURE,
    )
    branch_a_result = RUNNER.run_branch(
        label="branch-a",
        session=branch_a,
        store=store,
        seed_records=coordinator_records,
    )
    branch_records = load_jsonl(branch_a_path)
    failed_wake = branch_records[-1]
    suppression_records = RUNNER.suppress_pending_after_failure(
        store=store,
        failed_wake_record=failed_wake,
    )
    event_records = EventStore(event_path).read_records()
    event_summary = summarize_event_log(event_records)
    labels = latest_event_by_label(event_records)
    audit_projection = POLICY.sidecar_audit_projection(
        event_records,
        labels=BRANCH_LABELS,
    )
    final_run_record = finalize_failed_fork_run(
        started_record=started_record,
        failed_branch_result=branch_a_result,
        failed_wake_record=failed_wake,
        suppression_records=suppression_records,
        sidecar_audit_projection=audit_projection,
    )
    run_store.append(final_run_record)
    run_records = run_store.read_records()
    latest_run = run_store.latest_by_run_id()[started_record["fork_run_id"]]
    failure_classification = failed_wake.get("failure_classification")
    protocol_recovery = failed_wake.get("protocol_recovery")
    violations = branch_private_violations([branch_a_path])
    return {
        "scenario": "fork_run_identity_failure",
        "classification": "branch_failed",
        "coordinator_log_path": str(coord_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "fork_run_log_path": str(run_store.path.relative_to(PROJECT_ROOT)),
        "branch_log_paths": [str(branch_a_path.relative_to(PROJECT_ROOT))],
        "runner_branch_results": [branch_a_result.to_dict()],
        "runner_suppression_records": suppression_records,
        "fork_run_started_record": started_record,
        "fork_run_final_record": final_run_record,
        "fork_run_record_count": len(run_records),
        "latest_fork_run_record": latest_run,
        "branch_errors": [branch_a_result.error] if branch_a_result.error else [],
        "fork_event_count": len(
            [label for label in labels if str(label).startswith("branch-")]
        ),
        "branch_completed_count": sum(
            labels.get(label, {}).get("status") == "completed"
            for label in BRANCH_LABELS
        ),
        "branch_failed_count": sum(
            labels.get(label, {}).get("status") == "failed"
            for label in BRANCH_LABELS
        ),
        "branch_suppressed_count": sum(
            labels.get(label, {}).get("status") == "suppressed"
            for label in BRANCH_LABELS
        ),
        "join_completed": False,
        "joined_findings_count": 0,
        "branch_private_violations": violations,
        "policy_idempotence_holds": policy_idempotence_holds(coordinator_records),
        "sidecar_audit_preserved": POLICY.sidecar_audit_complete(
            event_records,
            labels=BRANCH_LABELS,
        ),
        "sidecar_audit_projection": audit_projection,
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
    success = by_scenario["fork_run_identity_success"]
    failure = by_scenario["fork_run_identity_failure"]
    success_record = success["fork_run_final_record"]
    failure_record = failure["fork_run_final_record"]
    return {
        "hypothesis_results": {
            "H104_fork_run_records_have_stable_identity_and_root": (
                success["fork_run_started_record"]["fork_run_id"]
                == "fork-run-success"
                and failure["fork_run_started_record"]["fork_run_id"]
                == "fork-run-failure"
                and success["fork_run_started_record"]["scheduled_by_cycle"] == 2
                and failure["fork_run_started_record"]["scheduled_by_cycle"] == 2
                and success["fork_run_started_record"]["branch_labels"]
                == list(BRANCH_LABELS)
                and failure["fork_run_started_record"]["branch_labels"]
                == list(BRANCH_LABELS)
            ),
            "H105_successful_run_records_bind_branches_and_join": (
                success_record["classification"] == "joined"
                and success_record["join_event_id"]
                and success_record["join_result_record_id"]
                and all(
                    success_record["branch_events"][label]["event_id"]
                    and success_record["branch_events"][label]["result_record_id"]
                    and success_record["branch_events"][label]["terminal_status"]
                    == "completed"
                    for label in BRANCH_LABELS
                )
                and success["sidecar_audit_preserved"]
            ),
            "H106_failed_run_records_bind_failure_and_suppression": (
                failure_record["classification"] == "branch_failed"
                and failure_record["failed_branch"] == "branch-a"
                and failure_record["failed_branch_wake_record_id"]
                and failure_record["failed_branch_result"]["status"] == "failed"
                and failure_record["failed_branch_result"]["error"]
                and failure_record["branch_events"]["branch-b"][
                    "terminal_status"
                ]
                == "suppressed"
                and failure_record["suppressed_events"]
                and failure["suppression_source_resolved"]
            ),
            "H107_run_records_sufficient_for_compact_evaluation": (
                all(
                    success_record["branch_events"][label]["terminal_status"]
                    == "completed"
                    for label in BRANCH_LABELS
                )
                and success_record["join_result_record_id"]
                and failure_record["branch_events"]["branch-a"][
                    "terminal_status"
                ]
                == "failed"
                and failure_record["branch_events"]["branch-b"][
                    "terminal_status"
                ]
                == "suppressed"
                and bool(failure_record["suppression_records"])
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
