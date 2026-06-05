"""Run the simulated-time scheduler re-entry diagnostic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
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

SIM_BEFORE = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
SIM_DUE = datetime(2026, 6, 5, 12, 5, tzinfo=timezone.utc)
SIM_AFTER = datetime(2026, 6, 5, 12, 6, tzinfo=timezone.utc)

BASE_STATE = {
    "response": "Seed state established.",
    "probe_id": "des-reentry",
    "current_task": "Diagnose simulated-time scheduler re-entry.",
    "diagnostic_findings": [
        {
            "entry": 1,
            "kind": "baseline",
            "content": "No simulated wake has run yet.",
        }
    ],
    "reentry_status": "initialized",
}

SUCCESS_WAKE = {
    "response": "Scheduled wake completed using recalled seed context.",
    "reentry_status": "completed",
    "diagnostic_findings": [
        {
            "entry": 1,
            "kind": "baseline",
            "content": "No simulated wake has run yet.",
        },
        {
            "entry": 2,
            "kind": "scheduled_wake",
            "content": "Wake used event envelope context and continuity curation.",
        },
    ],
}

FAILURE_WAKE = {
    "response": (
        "### Invalidated Assumptions\n"
        "1. Simulated strict failures might be silent.\n"
        "- Evidence: this wake intentionally overlaps delete/update keys.\n\n"
        "### New Constraints\n"
        "- Strict merge failures must preserve diagnostics without accepting state.\n\n"
        "### Next Actions\n"
        "1. Inspect protocol_recovery candidate rows after failure."
    ),
    "diagnostic_findings": [
        {
            "entry": 2,
            "kind": "scheduled_wake",
            "content": "This update must be rejected due to overlap.",
        }
    ],
    "deleted_regions": ["diagnostic_findings"],
}


@dataclass
class FakeBackend:
    outputs: list[dict]

    def __post_init__(self) -> None:
        self.calls: list[dict] = []

    def call(
        self,
        model,
        system,
        messages,
        experiment_label,
        extra_tools=None,
        tool_executor=None,
    ) -> ExchangeResult:
        del extra_tools, tool_executor
        self.calls.append(
            {
                "model": model,
                "system": system,
                "messages": messages,
                "experiment_label": experiment_label,
            }
        )
        if not self.outputs:
            raise RuntimeError("fake backend exhausted")
        return ExchangeResult(
            raw_output=self.outputs.pop(0),
            stop_reason="end_turn",
            input_tokens=10,
            output_tokens=5,
        )


class FakeCurator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def curate(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {
            "curator_type": "fake",
            "summary": (
                f"Carry probe_id and reentry task from cycle {kwargs['cycle']}."
            ),
            "supported_facts": [
                "probe_id is des-reentry",
                "scheduler wake is under simulated time",
            ],
        }


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def status_sequence(records: list[dict]) -> list[str]:
    return [str(record.get("status")) for record in records if record.get("status")]


def make_session(log_path: Path, wake_output: dict) -> OpenTasteSession:
    return OpenTasteSession(
        model="fake-des-model",
        backend=FakeBackend([BASE_STATE, wake_output]),
        log_path=str(log_path),
        event_log_path=str(default_event_log_path(log_path)),
        experiment_label=f"des_reentry_{log_path.stem}",
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
        continuity_curator=FakeCurator(),
        protocol_recovery_builder=DeterministicProtocolRecoveryBuilder(),
    )


def append_scheduled_event(session: OpenTasteSession, event_path: Path) -> dict:
    event = build_pending_event(
        purpose=(
            "Simulated scheduled re-entry. Use recalled cycle 1 context and "
            "continuity curation to update reentry_status and diagnostics."
        ),
        requested_context=[{"tool": "recall", "cycle": 1}],
        scheduled_by_cycle=1,
        scheduled_by_record_id=session._prior_states[-1][1],
        label="des-reentry-diagnostic",
        not_before=SIM_DUE.isoformat(),
    )
    store = EventStore(event_path)
    store.append(event)
    return event


def score_scenario(
    *,
    scenario: str,
    log_path: Path,
    event_path: Path,
    event: dict,
    pre_due: dict,
    run_error: str | None,
) -> dict:
    session_records = load_jsonl(log_path)
    event_records = load_jsonl(event_path)
    wake_records = [
        record
        for record in session_records
        if event["event_id"] in str(record.get("user_message", ""))
    ]
    wake_record = wake_records[-1] if wake_records else {}
    final_state = session_records[-1].get("state") if session_records else {}
    final_state = final_state if isinstance(final_state, dict) else {}
    seed_state = session_records[0].get("state") if session_records else {}
    seed_state = seed_state if isinstance(seed_state, dict) else {}
    failure_classification = wake_record.get("failure_classification")
    protocol_recovery = wake_record.get("protocol_recovery")
    latest_event_record = event_records[-1] if event_records else {}
    outcome = latest_event_record.get("outcome_observation") or {}
    context_results = latest_event_record.get("context_results") or []
    return {
        "scenario": scenario,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "event_id": event["event_id"],
        "run_error": run_error,
        "pre_due_claim_none": pre_due.get("status") == "none",
        "post_due_claimed": any(record.get("status") == "running" for record in event_records),
        "sidecar_status_sequence": status_sequence(event_records),
        "wake_record_observed": bool(wake_records),
        "wake_continuity_context_observed": bool(
            wake_record.get("curator_context_injection")
        ),
        "context_resolved": bool(
            context_results
            and not any(
                isinstance(item.get("result"), dict) and item["result"].get("error")
                for item in context_results
            )
        ),
        "state_changed": bool(outcome.get("state_changed")),
        "event_completed": latest_event_record.get("status") == "completed",
        "event_failed": latest_event_record.get("status") == "failed",
        "accepted_state_unchanged_on_failure": (
            final_state == seed_state if scenario == "strict_merge_failure" else None
        ),
        "failure_classification_logged": isinstance(failure_classification, dict),
        "protocol_recovery_logged": (
            isinstance(protocol_recovery, dict)
            and protocol_recovery.get("status") == "success"
        ),
        "protocol_recovery_candidate_rows": (
            len(
                protocol_recovery.get("artifact", {})
                .get("candidate_rows", [])
            )
            if isinstance(protocol_recovery, dict)
            else 0
        ),
        "final_reentry_status": final_state.get("reentry_status"),
    }


def run_scenario(scenario: str, wake_output: dict) -> dict:
    log_path = EXP_DIR / f"{scenario}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    session = make_session(log_path, wake_output)
    session.exchange("seed simulated scheduler state")
    event = append_scheduled_event(session, event_path)
    store = EventStore(event_path)
    pre_due = run_next_event(session, store, now=SIM_BEFORE)
    run_error = None
    try:
        run_next_event(session, store, now=SIM_AFTER)
    except Exception as e:  # noqa: BLE001 -- strict failure is expected data
        run_error = f"{type(e).__name__}: {e}"
    return score_scenario(
        scenario=scenario,
        log_path=log_path,
        event_path=event_path,
        event=event,
        pre_due=pre_due,
        run_error=run_error,
    )


def aggregate(results: list[dict]) -> dict:
    by_scenario = {result["scenario"]: result for result in results}
    success = by_scenario.get("success", {})
    failure = by_scenario.get("strict_merge_failure", {})
    h73 = all(result.get("pre_due_claim_none") and result.get("post_due_claimed") for result in results)
    h74 = all(
        bool(success.get(key))
        for key in (
            "event_completed",
            "wake_record_observed",
            "wake_continuity_context_observed",
            "context_resolved",
            "state_changed",
        )
    )
    h75 = all(
        bool(failure.get(key))
        for key in (
            "event_failed",
            "accepted_state_unchanged_on_failure",
            "failure_classification_logged",
            "protocol_recovery_logged",
        )
    )
    h76 = all(result.get("wake_continuity_context_observed") for result in results)
    return {
        "hypothesis_results": {
            "H73_simulated_due_time_claiming": h73,
            "H74_successful_reentry_records_completion": h74,
            "H75_strict_merge_failure_records_diagnostics": h75,
            "H76_wake_boundary_receives_continuity_context": h76,
        },
        "summary": {
            "scenarios": len(results),
            "completed": sum(bool(r.get("event_completed")) for r in results),
            "failed": sum(bool(r.get("event_failed")) for r in results),
            "protocol_recovery_logged": sum(
                bool(r.get("protocol_recovery_logged")) for r in results
            ),
        },
    }


def main() -> None:
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results = [
        run_scenario("success", SUCCESS_WAKE),
        run_scenario("strict_merge_failure", FAILURE_WAKE),
    ]
    payload = {
        "simulated_time": {
            "before": SIM_BEFORE.isoformat(),
            "due": SIM_DUE.isoformat(),
            "after": SIM_AFTER.isoformat(),
        },
        "results": results,
        **aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["hypothesis_results"], indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
