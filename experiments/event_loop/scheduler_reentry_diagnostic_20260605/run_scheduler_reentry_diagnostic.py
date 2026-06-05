"""Run the preregistered scheduler re-entry diagnostic."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hamutay.continuity_curator import ClaimTableContinuityCurator
from hamutay.events import (
    EventStore,
    default_event_log_path,
    run_next_event,
    summarize_event_log,
)
from hamutay.protocol_recovery import DeterministicProtocolRecoveryBuilder
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODEL = "moonshotai/kimi-k2.6"
N_REPLICATES = 3
MAX_TOKENS = 4096
SEED_MARKERS = ["alpha", "beta", "gamma"]

BASELINE_FINDINGS: list[dict[str, Any]] = [
    {
        "entry": 1,
        "kind": "baseline",
        "content": "No scheduled re-entry has run yet in this replicate.",
    }
]


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str, *, label: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": f"hamutay/{label}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


def make_session(log_path: Path, api_key: str, label: str) -> OpenTasteSession:
    main_backend = make_backend(api_key, label=label)
    curator_backend = make_backend(api_key, label=f"{label}-curator")
    continuity_curator = ClaimTableContinuityCurator(
        backend=curator_backend,
        model=MODEL,
        experiment_label=f"{label}_claim_table_curator",
        max_summary_chars=900,
        renderer="guardrail_delta",
        delta_max_rows=6,
        guardrail_stable_invalidated_cap=2,
        recover_response_claims=True,
    )
    return OpenTasteSession(
        model=MODEL,
        backend=main_backend,
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
        continuity_curator=continuity_curator,
        protocol_recovery_builder=DeterministicProtocolRecoveryBuilder(),
    )


def init_prompt(replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    probe_id = f"scheduler-reentry-{replicate + 1}-{marker}"
    return f"""
Registered scheduler re-entry diagnostic.
model={MODEL}
replicate={replicate + 1}
marker={marker}

Initialize a compact durable research state using top-level fields only:
- probe_id
- current_task
- assumptions
- constraints
- diagnostic_findings
- reentry_status

Use probe_id: {probe_id}
Set current_task to: "Diagnose whether scheduled re-entry can continue without
user rebriefing when continuity curation and protocol recovery are enabled."
Set assumptions to a list containing:
1. "Scheduled wake context plus scaffold continuity should be enough to continue."
2. "A wake failure is still useful if the sidecar and session log preserve diagnostics."
Set constraints to a list containing:
1. "Do not recursively schedule events in this diagnostic."
Set diagnostic_findings to:
{json.dumps(BASELINE_FINDINGS, indent=2)}
Set reentry_status to "initialized".

Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def update_prompt(replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"""
Registered scheduler re-entry diagnostic task update.
model={MODEL}
replicate={replicate + 1}
marker={marker}

Update durable state with these new facts:

New evidence:
- Prior scheduler work showed operational wake mechanics, but also showed that
  model/protocol failures can make apparent continuity hard to interpret.
- The current diagnostic should treat a failed wake as useful only if the event
  sidecar and session JSONL make the failure class observable.

Required durable updates:
- Append a diagnostic_findings entry recording that operational observability is
  now the primary target.
- Add or update an assumption/constraint noting that successful prose is not
  enough; durable state and sidecar evidence must agree.
- Set reentry_status to "ready_to_schedule".

Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def schedule_prompt(replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    label = f"scheduler-reentry-diagnostic-r{replicate + 1}-{marker}"
    requested_context = [
        {"tool": "recall", "cycle": 1},
        {"tool": "recall", "cycle": 2},
    ]
    purpose = """
You are the scheduled re-entry wake for the Hamut'ay scheduler re-entry
diagnostic. Use the event envelope context and scaffold continuity, without a
new user rebrief, to diagnose whether the scheduled wake can continue.

Required durable wake updates:
- Set top-level reentry_status to "completed".
- Append at least one top-level diagnostic_findings entry whose kind is
  "scheduled_wake" and whose content explains what evidence the wake used.
- Preserve probe_id and current_task.
- Do not recursively schedule any event.

If you cannot determine enough from the provided context, set reentry_status to
"blocked" and append a diagnostic_findings entry explaining the missing
context. Do not schedule another event.
""".strip()
    return f"""
Registered scheduler re-entry diagnostic schedule step.
model={MODEL}
replicate={replicate + 1}
marker={marker}

Call schedule_event exactly once and wait for its result. Use exactly this
requested_context:
{json.dumps(requested_context, indent=2)}

Use label: {label}

Event purpose:
{purpose}

After the schedule_event result returns, set reentry_status to "scheduled" and
end with think_and_respond. Do not claim scheduling succeeded unless the tool
result contains an event_id. Do not call read, search_project, bash, or clock.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def init_failure_reasons(state: dict, replicate: int) -> list[str]:
    marker = SEED_MARKERS[replicate]
    expected_probe_id = f"scheduler-reentry-{replicate + 1}-{marker}"
    reasons: list[str] = []
    if state.get("probe_id") != expected_probe_id:
        reasons.append("probe_id_missing_or_changed")
    if state.get("reentry_status") != "initialized":
        reasons.append("reentry_status_not_initialized")
    if not isinstance(state.get("assumptions"), list):
        reasons.append("assumptions_not_list")
    if not isinstance(state.get("constraints"), list):
        reasons.append("constraints_not_list")
    if not isinstance(state.get("diagnostic_findings"), list):
        reasons.append("diagnostic_findings_not_list")
    if isinstance(state.get("state"), dict):
        reasons.append("nested_state_present")
    return reasons


def task_update_failure_reasons(state: dict) -> list[str]:
    reasons: list[str] = []
    if state.get("reentry_status") != "ready_to_schedule":
        reasons.append("reentry_status_not_ready_to_schedule")
    findings = state.get("diagnostic_findings")
    if not isinstance(findings, list):
        reasons.append("diagnostic_findings_not_list")
    elif len(findings) <= len(BASELINE_FINDINGS):
        reasons.append("diagnostic_findings_not_appended")
    text = json.dumps(state, default=str).lower()
    if "sidecar" not in text or "session" not in text:
        reasons.append("observability_update_missing")
    return reasons


def scheduled_events_in(records: list[dict]) -> list[dict]:
    return [
        event
        for record in records
        for event in (record.get("scheduled_events") or [])
    ]


def event_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def latest_event_statuses(records: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for record in records:
        event_id = record.get("event_id")
        if event_id:
            latest[str(event_id)] = record
    return latest


def count_context_errors(records: list[dict]) -> int:
    count = 0
    for record in records:
        if record.get("status") != "completed":
            continue
        for item in record.get("context_results") or []:
            result = item.get("result")
            if isinstance(result, dict) and result.get("error"):
                count += 1
    return count


def wake_records(records: list[dict], event_id: str | None) -> list[dict]:
    if not event_id:
        return []
    return [
        record
        for record in records
        if event_id in str(record.get("user_message", ""))
    ]


def diagnostic_findings_updated(state: dict) -> bool:
    findings = state.get("diagnostic_findings")
    if not isinstance(findings, list) or len(findings) <= len(BASELINE_FINDINGS):
        return False
    return "wake" in json.dumps(findings, default=str).lower()


def strict_merge_failures(records: list[dict]) -> list[dict]:
    failures = []
    for record in records:
        classification = record.get("failure_classification")
        if (
            record.get("status") == "failed"
            and isinstance(classification, dict)
            and classification.get("failure_stage") == "state_merge"
        ):
            failures.append(record)
    return failures


def score_replicate(log_path: Path, event_path: Path, replicate: int) -> dict:
    records = load_records(log_path)
    event_log = event_records(event_path)
    events = scheduled_events_in(records)
    event_id = events[0].get("event_id") if events else None
    latest_statuses = latest_event_statuses(event_log)
    final_event = latest_statuses.get(str(event_id)) if event_id else None
    final_event_status = final_event.get("status") if final_event else None
    wakes = wake_records(records, str(event_id) if event_id else None)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state")
    final_state = final_state if isinstance(final_state, dict) else {}
    init_state = records[0].get("state") if records else {}
    init_state = init_state if isinstance(init_state, dict) else {}
    update_state = records[1].get("state") if len(records) > 1 else {}
    update_state = update_state if isinstance(update_state, dict) else {}
    merge_failures = strict_merge_failures(records)
    protocol_diagnosed = all(
        isinstance(record.get("protocol_recovery"), dict)
        and record["protocol_recovery"].get("status") == "success"
        for record in merge_failures
    )
    sidecar_failed = final_event_status == "failed"
    return {
        "cycle_count": len(records),
        "init_failure_reasons": init_failure_reasons(init_state, replicate),
        "task_update_failure_reasons": task_update_failure_reasons(update_state),
        "schedule_tool_recorded": len(events) == 1,
        "scheduled_event_count": len(events),
        "event_id": event_id,
        "event_persisted": bool(event_id and any(r.get("event_id") == event_id for r in event_log)),
        "event_completed": final_event_status == "completed",
        "event_failed": sidecar_failed,
        "event_final_status": final_event_status,
        "event_final_status_observed": final_event_status in {"completed", "failed", "expired"},
        "context_error_count": count_context_errors(event_log),
        "wake_record_observed": bool(wakes),
        "wake_continuity_context_observed": any(
            bool(record.get("curator_context_injection")) for record in wakes
        ),
        "reentry_completed": final_state.get("reentry_status") == "completed",
        "reentry_status": final_state.get("reentry_status"),
        "diagnostic_findings_updated": diagnostic_findings_updated(final_state),
        "recursive_scheduling_count": max(0, len(events) - 1),
        "strict_merge_failure_observed": bool(merge_failures),
        "strict_merge_failure_count": len(merge_failures),
        "strict_merge_failure_diagnosed": protocol_diagnosed if merge_failures else None,
        "sidecar_failed_on_merge_failure": sidecar_failed if merge_failures else None,
        "final_top_level_keys": sorted(final_state.keys()),
    }


def run_replicate(replicate: int, api_key: str) -> dict:
    log_path = EXP_DIR / f"{safe_model_name(MODEL)}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    label = f"scheduler_reentry_diagnostic_{safe_model_name(MODEL)}_r{replicate + 1:02d}"
    result: dict[str, Any] = {
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "error": None,
        "event_result_status": None,
    }
    session = make_session(log_path, api_key, label)
    try:
        session.exchange(init_prompt(replicate), force_memory=None)
        session.exchange(update_prompt(replicate), force_memory=None)
        session.exchange(schedule_prompt(replicate), force_memory=None)
        if scheduled_events_in(load_records(log_path)):
            store = EventStore(event_path)
            event_result = run_next_event(session, store)
            result["event_result_status"] = event_result.get("status")
    except Exception as e:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(e)
    result.update(score_replicate(log_path, event_path, replicate))
    return result


def summarize_group(results: list[dict]) -> dict:
    valid = [
        r
        for r in results
        if not r.get("init_failure_reasons") and not r.get("task_update_failure_reasons")
    ]
    merge_failures = [r for r in results if r.get("strict_merge_failure_observed")]
    return {
        "n": len(results),
        "valid_replicates": len(valid),
        "errors": sum(bool(r.get("error")) for r in results),
        "event_persisted": sum(bool(r.get("event_persisted")) for r in valid),
        "event_completed": sum(bool(r.get("event_completed")) for r in valid),
        "event_failed": sum(bool(r.get("event_failed")) for r in valid),
        "event_final_status_observed": sum(
            bool(r.get("event_final_status_observed")) for r in valid
        ),
        "context_error_count": sum(int(r.get("context_error_count") or 0) for r in valid),
        "wake_records": sum(bool(r.get("wake_record_observed")) for r in valid),
        "wake_continuity_context": sum(
            bool(r.get("wake_continuity_context_observed")) for r in valid
        ),
        "reentry_completed": sum(bool(r.get("reentry_completed")) for r in valid),
        "diagnostic_findings_updated": sum(
            bool(r.get("diagnostic_findings_updated")) for r in valid
        ),
        "recursive_scheduling_count": sum(
            int(r.get("recursive_scheduling_count") or 0) for r in results
        ),
        "strict_merge_failures": len(merge_failures),
        "strict_merge_failures_diagnosed": sum(
            bool(r.get("strict_merge_failure_diagnosed")) for r in merge_failures
        ),
        "sidecar_failures_on_merge_failure": sum(
            bool(r.get("sidecar_failed_on_merge_failure")) for r in merge_failures
        ),
    }


def aggregate(results: list[dict]) -> dict:
    summary = summarize_group(results)
    valid_n = summary["valid_replicates"]
    h69 = valid_n > 0 and summary["event_persisted"] == valid_n and (
        summary["event_completed"] + summary["event_failed"] == valid_n
    )
    h70 = summary["reentry_completed"] >= 2 and summary["diagnostic_findings_updated"] >= 2
    merge_failures = summary["strict_merge_failures"]
    h71 = (
        merge_failures == 0
        or (
            summary["strict_merge_failures_diagnosed"] == merge_failures
            and summary["sidecar_failures_on_merge_failure"] == merge_failures
        )
    )
    h72 = valid_n > 0 and summary["wake_continuity_context"] == summary["wake_records"]
    return {
        "summary": summary,
        "hypothesis_results": {
            "H69_scheduled_reentry_observable": h69,
            "H70_successful_reentry_without_rebriefing": h70,
            "H71_failed_reentry_diagnostically_useful": h71,
            "H72_continuity_visible_at_wake_boundary": h72,
        },
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "condition": {
            "continuity_curator": "ClaimTableContinuityCurator",
            "renderer": "guardrail_delta",
            "max_summary_chars": 900,
            "delta_max_rows": 6,
            "protocol_recovery": "DeterministicProtocolRecoveryBuilder",
        },
        "results": results,
        **aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results: list[dict] = []
    for replicate in range(N_REPLICATES):
        print(f"{MODEL} r{replicate + 1}", flush=True)
        result = run_replicate(replicate, api_key)
        results.append(result)
        write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
