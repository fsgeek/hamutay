"""Phase 3C longer wall-clock sustained-operation probe."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import importlib.util
import json
import os
import sys
import time
import typing as typing_module
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


JsonDict = dict[str, Any]

EXPERIMENT_ID = "phase_3c_longer_wall_clock_sustained_operation_20260619"
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
YANANTIN_SRC_ROOT = PROJECT_ROOT.parent / "yanantin" / "src"
TIKSI_SRC_ROOT = PROJECT_ROOT.parent / "tiksi" / "src"
for path in (PROJECT_ROOT, SRC_ROOT, YANANTIN_SRC_ROOT, TIKSI_SRC_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
if not hasattr(datetime_module, "UTC"):
    datetime_module.UTC = datetime_module.timezone.utc
if not hasattr(typing_module, "Self"):
    from typing_extensions import Self

    typing_module.Self = Self

LONGER_RUN_PATH = ROOT_DIR.parent / "longer_horizon_sustained_loop_20260618" / "run.py"
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
WORKSTREAMS = [
    {"task_label": "alpha", "workstream_id": "research"},
    {"task_label": "beta", "workstream_id": "operations"},
]
TASK_LABELS = [item["task_label"] for item in WORKSTREAMS]
WORKSTREAM_IDS = [item["workstream_id"] for item in WORKSTREAMS]
INTERRUPTED_TASK_LABEL = "beta"
EXPECTED_EVENT_TYPES = [
    "inbound_message",
    "self_scheduled_reflection",
    "housekeeping",
    "periodic_report",
    "inbound_message",
    "self_scheduled_reflection",
    "housekeeping",
    "periodic_report",
    "final_artifact_synthesis",
]
EXPECTED_TERMINAL_TOOLS = [
    "handle_workstream_ipc",
    "complete_bound_continuation",
    "complete_housekeeping_audit",
    "write_periodic_report",
    "handle_workstream_ipc",
    "complete_bound_continuation",
    "complete_housekeeping_audit",
    "write_periodic_report",
    "write_autonomous_loop_artifact",
]
DEFAULT_DELAY_SECONDS = 2.0
MIN_OBSERVED_DELAY_SECONDS = 1.0
DELAY_WINDOWS = [
    {
        "label": "alpha-report-delay",
        "event_type": "periodic_report",
        "task_label": "alpha",
    },
    {
        "label": "beta-restart-delay",
        "event_type": "self_scheduled_reflection",
        "task_label": "beta",
    },
]


def load_longer_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "longer_horizon_for_phase_2c_autonomous",
        LONGER_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {LONGER_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    module.PROBE.EXPERIMENT_ID = EXPERIMENT_ID
    module.PROBE.ROOT_DIR = ROOT_DIR
    return module


LONGER = load_longer_module()
PROBE = LONGER.PROBE


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "workstreams": WORKSTREAMS,
            "delay_windows": DELAY_WINDOWS,
            "minimum_observed_delay_seconds": MIN_OBSERVED_DELAY_SECONDS,
            "expected_completed_event_count": len(EXPECTED_EVENT_TYPES),
            "expected_event_type_sequence": EXPECTED_EVENT_TYPES,
            "interruption": {
                "event_type": "self_scheduled_reflection",
                "task_label": INTERRUPTED_TASK_LABEL,
                "point": "after claim as running before exchange",
                "expected_history": [
                    "pending",
                    "running",
                    "pending",
                    "running",
                    "completed",
                ],
            },
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 10 if live_model_calls else 0,
            "max_estimated_cost_usd": 5.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_3c_wall_clock_sustained_operation_taxonomy.v1",
            "layers": [
                "scheduler",
                "elapsed_time_scheduler",
                "restart_frontier",
                "state_reconstruction",
                "housekeeping",
                "periodic_reporting",
                "model_output",
                "provider",
                "artifact",
                "inconclusive",
            ],
        },
    }
    for name, payload in artifacts.items():
        PROBE.write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


def workstream_inbound_terminal_surface(*, workstream: JsonDict, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="handle_workstream_ipc",
        description="Handle an inbound workstream IPC message.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["workstream IPC accepted"]},
            "task_label": {"type": "string", "enum": [workstream["task_label"]]},
            "workstream_id": {"type": "string", "enum": [workstream["workstream_id"]]},
            "inbound_status": {"type": "string"},
            "open_items": PROBE.open_items_schema(),
            "continuation_request": PROBE.continuation_request_schema(),
        },
        required=[
            "response",
            "task_label",
            "workstream_id",
            "inbound_status",
            "open_items",
            "continuation_request",
        ],
        copy_fields=[
            "task_label",
            "workstream_id",
            "inbound_status",
            "open_items",
            "continuation_request",
        ],
    )


def periodic_report_terminal_surface(*, workstream: JsonDict, tool_choice: str) -> JsonDict:
    report_index = WORKSTREAMS.index(workstream) + 1
    return PROBE.terminal_surface(
        tool_name="write_periodic_report",
        description="Write a bounded periodic workstream report.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["periodic report complete"]},
            "task_label": {"type": "string", "enum": [workstream["task_label"]]},
            "workstream_id": {"type": "string", "enum": [workstream["workstream_id"]]},
            "report_index": {"type": "integer", "enum": [report_index]},
            "report_status": {"type": "string", "enum": ["clean"]},
            "open_item_count": {"type": "integer"},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        },
        required=[
            "response",
            "task_label",
            "workstream_id",
            "report_index",
            "report_status",
            "open_item_count",
            "unsupported_claims",
        ],
        copy_fields=[
            "task_label",
            "workstream_id",
            "report_index",
            "report_status",
            "open_item_count",
            "unsupported_claims",
        ],
    )


def final_artifact_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_autonomous_loop_artifact",
        description="Write the final autonomous-loop synthesis.",
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["autonomous loop artifact complete"],
            },
            "artifact_title": {"type": "string"},
            "workstream_count": {"type": "integer"},
            "completed_task_labels": {"type": "array", "items": {"type": "string"}},
            "completed_workstream_ids": {"type": "array", "items": {"type": "string"}},
            "periodic_report_count": {"type": "integer"},
            "elapsed_delay_window_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "currently_pending_event_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "preserved_state_labels": {"type": "array", "items": {"type": "string"}},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "open_items": PROBE.open_items_schema(),
            "conclusion": {"type": "string"},
            "declared_losses": {"type": "array", "items": {"type": "string"}},
        },
        required=[
            "response",
            "artifact_title",
            "workstream_count",
            "completed_task_labels",
            "completed_workstream_ids",
            "periodic_report_count",
            "elapsed_delay_window_labels",
            "currently_pending_event_labels",
            "preserved_state_labels",
            "unsupported_claims",
            "open_items",
            "conclusion",
            "declared_losses",
        ],
        copy_fields=[
            "artifact_title",
            "workstream_count",
            "completed_task_labels",
            "completed_workstream_ids",
            "periodic_report_count",
            "elapsed_delay_window_labels",
            "currently_pending_event_labels",
            "preserved_state_labels",
            "unsupported_claims",
            "open_items",
            "conclusion",
            "declared_losses",
        ],
    )


def scripted_outputs() -> list[JsonDict]:
    outputs: list[JsonDict] = [
        {
            "response": "live loop probe initialized",
            "probe_status": "ready",
            "open_items": [],
        }
    ]
    for report_index, workstream in enumerate(WORKSTREAMS, start=1):
        label = workstream["task_label"]
        outputs.extend(
            [
                {
                    "response": "workstream IPC accepted",
                    "task_label": label,
                    "workstream_id": workstream["workstream_id"],
                    "inbound_status": f"{label}-accepted",
                    "open_items": [{"kind": "task", "text": f"finish {label}"}],
                    "continuation_request": {
                        "requested": True,
                        "kind": "session_bound_continuation",
                        "purpose": f"Finish task {label} from <result_record_id>.",
                        "symbolic_context": [
                            {"source": "completed_wake_state", "field": "inbound_status"}
                        ],
                        "label": f"finish-{label}",
                    },
                },
                {
                    "response": "bound continuation complete",
                    "continuation_status": "completed",
                    "open_items": [],
                },
                {
                    "response": "housekeeping audit clean",
                    "open_items": [],
                    "housekeeping_audit": {
                        "audit_index": 1,
                        "open_item_count": 0,
                        "status": "clean",
                    },
                },
                {
                    "response": "periodic report complete",
                    "task_label": label,
                    "workstream_id": workstream["workstream_id"],
                    "report_index": report_index,
                    "report_status": "clean",
                    "open_item_count": 0,
                    "unsupported_claims": [],
                },
            ]
        )
    outputs.append(
        {
            "response": "autonomous loop artifact complete",
            "artifact_title": "Phase 3C Wall-Clock Sustained Operation Probe",
            "workstream_count": len(WORKSTREAMS),
            "completed_task_labels": TASK_LABELS,
            "completed_workstream_ids": WORKSTREAM_IDS,
            "periodic_report_count": len(WORKSTREAMS),
            "elapsed_delay_window_labels": [
                "alpha-report-delay",
                "beta-restart-delay",
            ],
            "currently_pending_event_labels": [],
            "preserved_state_labels": [
                "restart-frontier",
                "open-item-empty-state",
                "periodic-report-history",
            ],
            "unsupported_claims": [],
            "open_items": [],
            "conclusion": "Both bounded workstreams completed after observed elapsed delays.",
            "declared_losses": [],
        }
    )
    return outputs


def initialize_run(
    *,
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
):
    store, memory, ledger, frontier = LONGER.initialize_run(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
    )
    frontier.ensure_run_manifest(
        ledger=ledger,
        run_id=run_id,
        manifest={
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "endpoint": endpoint if live_model_calls else None,
            "model": model,
            "terminal_tool_choice": terminal_tool_choice,
            "interruption": "beta continuation after running claim",
            "delay_windows": DELAY_WINDOWS,
        },
        sandbox={"network": "enabled" if live_model_calls else "disabled"},
    )
    return store, memory, ledger, frontier


def commit_or_stop(
    *,
    paths: Any,
    frontier: Any,
    memory: Any,
    ledger: Any,
    store: Any,
    session: Any,
    run_id: str,
    notes: JsonDict,
) -> JsonDict | None:
    return LONGER.commit_or_stop(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes=notes,
    )


def append_inbound_event(
    *,
    store: Any,
    session: Any,
    workstream: JsonDict,
    terminal_tool_choice: str,
) -> JsonDict:
    label = workstream["task_label"]
    return PROBE.append_probe_event(
        store,
        event_type="inbound_message",
        label=f"inbound-{label}",
        purpose=(
            f"Handle inbound IPC task {label} for workstream "
            f"{workstream['workstream_id']}: record acceptance, leave one "
            "open item, and request a framework-bound continuation using "
            "symbolic_context with source completed_wake_state. Return response "
            "exactly: workstream IPC accepted."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=workstream_inbound_terminal_surface(
            workstream=workstream,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": str(session._prior_states[-1][1])}],
    )


def append_housekeeping_event(
    *,
    store: Any,
    session: Any,
    terminal_tool_choice: str,
) -> JsonDict:
    return LONGER.append_housekeeping_event(
        store=store,
        session=session,
        terminal_tool_choice=terminal_tool_choice,
    )


def append_periodic_report_event(
    *,
    store: Any,
    session: Any,
    workstream: JsonDict,
    context_record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    label = workstream["task_label"]
    return PROBE.append_probe_event(
        store,
        event_type="periodic_report",
        label=f"periodic-report-{label}",
        purpose=(
            f"Write a bounded periodic report for workstream "
            f"{workstream['workstream_id']} and task {label}. Return response "
            "exactly: periodic report complete."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=periodic_report_terminal_surface(
            workstream=workstream,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in context_record_ids
        ],
    )


def append_final_event(
    *,
    store: Any,
    session: Any,
    result_record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="final_artifact_synthesis",
        label="final-autonomous-loop-synthesis",
        purpose=(
            "Write the final artifact synthesizing completed tasks alpha and "
            "beta. Set workstream_count to 2, periodic_report_count to 2, "
            "completed_task_labels to ['alpha', 'beta'], "
            "completed_workstream_ids to ['research', 'operations'], "
            "elapsed_delay_window_labels to ['alpha-report-delay', "
            "'beta-restart-delay'] for the historical delay windows observed "
            "during this run, currently_pending_event_labels to [], "
            "unsupported_claims to [], open_items to [], and response exactly: "
            "autonomous loop artifact complete."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=final_artifact_terminal_surface(
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in result_record_ids
        ],
    )


def read_jsonl(path: Path) -> list[JsonDict]:
    return LONGER.read_jsonl(path)


def session_state_by_record_id(path: Path) -> dict[str, JsonDict]:
    return LONGER.session_state_by_record_id(path)


def attempted_terminal_tools(path: Path) -> list[str]:
    return LONGER.attempted_terminal_tools(path)


def material_outcome_warnings(summary: JsonDict) -> list[JsonDict]:
    return LONGER.material_outcome_warnings(summary)


def event_histories(records: list[JsonDict]) -> dict[str, list[str]]:
    histories: dict[str, list[str]] = {}
    for record in records:
        event_id = record.get("event_id")
        status = record.get("status")
        if event_id and status:
            histories.setdefault(str(event_id), []).append(str(status))
    return histories


def utc_now_iso() -> str:
    return (
        datetime_module.datetime.now(datetime_module.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_utc(value: str | None) -> datetime_module.datetime | None:
    if not value:
        return None
    return datetime_module.datetime.fromisoformat(value.replace("Z", "+00:00"))


def observe_delay(
    *,
    label: str,
    seconds: float,
    event: JsonDict | None = None,
) -> JsonDict:
    started_at = utc_now_iso()
    monotonic_start = time.monotonic()
    time.sleep(max(0.0, seconds))
    elapsed_seconds = time.monotonic() - monotonic_start
    completed_at = utc_now_iso()
    observation: JsonDict = {
        "label": label,
        "requested_seconds": seconds,
        "observed_seconds": round(elapsed_seconds, 3),
        "started_at": started_at,
        "completed_at": completed_at,
    }
    if event is not None:
        observation.update(
            {
                "event_id": str(event.get("event_id")),
                "event_type": event.get("event_type"),
                "event_label": event.get("label"),
                "event_created_at": event.get("created_at"),
            }
        )
    return observation


def observed_pending_elapsed(delay_observations: list[JsonDict]) -> list[float]:
    elapsed: list[float] = []
    for observation in delay_observations:
        created_at = parse_utc(str(observation.get("event_created_at") or ""))
        delay_completed_at = parse_utc(str(observation.get("completed_at") or ""))
        if created_at is None or delay_completed_at is None:
            continue
        elapsed.append(max(0.0, (delay_completed_at - created_at).total_seconds()))
    return elapsed


def preserved_state_labels_sufficient(labels: Any) -> bool:
    if not isinstance(labels, list):
        return False
    normalized = {str(label) for label in labels}
    has_open_state = bool({"open_items", "open-item-empty-state"} & normalized)
    has_continuation_or_restart_state = bool(
        {
            "continuation_request",
            "continuation_status",
            "restart-frontier",
        }
        & normalized
    )
    has_report_or_housekeeping_state = bool(
        {
            "report_status",
            "periodic-report-history",
            "housekeeping_audit",
        }
        & normalized
    )
    return (
        has_open_state
        and has_continuation_or_restart_state
        and has_report_or_housekeeping_state
    )


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures = PROBE.collect_failures(paths, records, success)
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        layer = "artifact"
        if "interrupted" in check_name or "frontier" in check_name:
            layer = "restart_frontier"
        elif "delay" in check_name or "wall_clock" in check_name:
            layer = "elapsed_time_scheduler"
        elif "housekeeping" in check_name:
            layer = "housekeeping"
        elif "periodic" in check_name:
            layer = "periodic_reporting"
        elif "sequence" in check_name or "idle" in check_name:
            layer = "scheduler"
        failures.append(
            {
                "record_type": "probe_postcondition_failure",
                "failure_attribution": {
                    "surface": "present",
                    "layer": layer,
                    "code": check_name,
                    "stage": "postcondition",
                    "error_type": "ProbePostconditionFailure",
                    "error": f"{check_name} failed",
                },
            }
        )
    return failures


def required_success(
    summary: JsonDict,
    records: list[JsonDict],
    *,
    paths: Any,
    interrupted_event_id: str,
    recovered_records: list[JsonDict],
    delay_observations: list[JsonDict],
) -> JsonDict:
    completed = [
        record
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    completed_tools = attempted_terminal_tools(paths.attempts_log)
    states_by_record_id = session_state_by_record_id(paths.session_log)
    final_records = [
        record for record in completed
        if record.get("event_type") == "final_artifact_synthesis"
    ]
    final_after = {}
    if final_records:
        final_after = states_by_record_id.get(
            str(final_records[-1].get("result_record_id")),
            {},
        )
    report_states = [
        states_by_record_id.get(str(record.get("result_record_id")), {})
        for record in completed
        if record.get("event_type") == "periodic_report"
    ]
    histories = event_histories(records)
    interrupted_history = histories.get(interrupted_event_id, [])
    delayed_pending_elapsed = observed_pending_elapsed(delay_observations)
    frontier_line_count = 0
    if paths.frontier_log.exists():
        frontier_line_count = len(
            [
                line
                for line in paths.frontier_log.read_text().splitlines()
                if line.strip()
            ]
        )
    checks = {
        "completed_nine_events": len(completed) == len(EXPECTED_EVENT_TYPES),
        "event_type_sequence": completed_types == EXPECTED_EVENT_TYPES,
        "terminal_surface_sequence": completed_tools == EXPECTED_TERMINAL_TOOLS,
        "two_workstreams": sorted(final_after.get("completed_workstream_ids") or [])
        == sorted(WORKSTREAM_IDS),
        "two_periodic_reports": len(report_states) == 2
        and all(state.get("report_status") == "clean" for state in report_states),
        "report_consistency": sorted(
            state.get("task_label") for state in report_states
        )
        == sorted(TASK_LABELS)
        and all(state.get("open_item_count") == 0 for state in report_states),
        "observed_delay_windows": len(delay_observations) == len(DELAY_WINDOWS)
        and all(
            observation.get("observed_seconds", 0.0) >= MIN_OBSERVED_DELAY_SECONDS
            for observation in delay_observations
        ),
        "delayed_events_waited_before_start": len(delayed_pending_elapsed)
        == len(DELAY_WINDOWS)
        and all(elapsed >= MIN_OBSERVED_DELAY_SECONDS for elapsed in delayed_pending_elapsed),
        "interrupted_event_recovered_and_completed": interrupted_history
        == ["pending", "running", "pending", "running", "completed"],
        "recovered_one_interrupted_event": len(recovered_records) == 1,
        "final_workstream_count": final_after.get("workstream_count") == 2,
        "final_labels": sorted(final_after.get("completed_task_labels") or [])
        == sorted(TASK_LABELS),
        "final_clean": final_after.get("unsupported_claims") == []
        and final_after.get("open_items") == [],
        "final_distinguishes_operation_state": sorted(
            final_after.get("elapsed_delay_window_labels") or []
        )
        == sorted(["alpha-report-delay", "beta-restart-delay"])
        and final_after.get("currently_pending_event_labels") == []
        and preserved_state_labels_sufficient(final_after.get("preserved_state_labels")),
        "multiple_frontier_updates": frontier_line_count >= 10,
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
        "no_material_outcome_warnings": material_outcome_warnings(summary) == [],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "completed_terminal_surface_tools": completed_tools,
        "final_after_state": final_after,
        "periodic_report_states": report_states,
        "delay_observations": delay_observations,
        "delayed_pending_elapsed_seconds": delayed_pending_elapsed,
        "frontier_line_count": frontier_line_count,
        "interrupted_event_id": interrupted_event_id,
        "interrupted_event_history": interrupted_history,
        "recovered_event_records": recovered_records,
    }


def finalize_results(
    *,
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
    store: Any,
    interrupted_event_id: str = "",
    recovered_records: list[JsonDict] | None = None,
    delay_observations: list[JsonDict] | None = None,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    success = required_success(
        summary,
        records,
        paths=paths,
        interrupted_event_id=interrupted_event_id,
        recovered_records=recovered_records or [],
        delay_observations=delay_observations or [],
    )
    failures = collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.phase_3c_wall_clock_sustained_operation.v1",
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model,
        "terminal_tool_choice": terminal_tool_choice,
        "classification": classification,
        "success": success,
        "event_summary": summary,
        "failure_attribution": failures,
        "evidence": {
            "session_log": paths.session_log.name,
            "event_log": paths.event_log.name,
            "attempts_log": paths.attempts_log.name,
            "restart_frontier": paths.frontier_log.name,
            "memory_snapshot": paths.memory_snapshot.name,
            "action_log": paths.action_log.name,
        },
    }
    if extra:
        results.update(extra)
    PROBE.write_json(paths.output_root / "results.json", results)
    return results


def run_pending_event(
    *,
    session: Any,
    store: Any,
    paths: Any,
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )


def run_probe(
    *,
    output_root: Path = ROOT_DIR,
    overwrite: bool = False,
    live_model_calls: bool = False,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    terminal_tool_choice: str | None = None,
    backend: Any | None = None,
    run_id: str | None = None,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> JsonDict:
    if live_model_calls and not api_key and backend is None:
        raise ValueError("api_key is required for live model calls")
    paths = PROBE.prepare_output_root(output_root, overwrite=overwrite)
    write_preregistration_artifacts(output_root, live_model_calls=live_model_calls)
    run_id = run_id or str(uuid4())
    terminal_tool_choice = terminal_tool_choice or PROBE.default_terminal_tool_choice(
        endpoint
    )
    if backend is None:
        if live_model_calls:
            backend = PROBE.make_live_backend(
                endpoint=endpoint,
                api_key=api_key or "",
                max_tokens=max_tokens,
            )
        else:
            backend = PROBE.ScriptedTerminalBackend(scripted_outputs())

    store, memory, ledger, frontier = initialize_run(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
    )
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    seed_request = {
        "event": "initialize_phase_3c_wall_clock_sustained_operation",
        "instruction": "Initialize durable state for a wall-clock sustained-operation probe.",
        "required_output": {
            "response": "<brief initialization note>",
            "probe_status": "ready",
            "open_items": [],
        },
    }
    try:
        session.exchange(
            json.dumps(seed_request, indent=2, sort_keys=True),
            terminal_surface=PROBE.seed_terminal_surface(tool_choice=terminal_tool_choice),
            force_memory=None,
        )
    except Exception as exc:
        PROBE.record_failure(
            paths,
            PROBE.classify_exception(exc, stage="seed_exchange"),
            request=seed_request,
        )
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "seed_exchange"},
        )
    commit_or_stop(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes={"boundary": "after seed"},
    )

    synthesis_record_ids: list[str] = []
    interrupted_event_id = ""
    recovered_records: list[JsonDict] = []
    delay_observations: list[JsonDict] = []

    for workstream in WORKSTREAMS:
        label = workstream["task_label"]
        append_inbound_event(
            store=store,
            session=session,
            workstream=workstream,
            terminal_tool_choice=terminal_tool_choice,
        )
        inbound_result = PROBE.run_attributed_event(
            session=session,
            store=store,
            paths=paths,
            auto_continuations=True,
            terminal_tool_choice=terminal_tool_choice,
        )
        if inbound_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                interrupted_event_id=interrupted_event_id,
                recovered_records=recovered_records,
                delay_observations=delay_observations,
                extra={"stopped_after": f"inbound_{label}"},
            )
        if isinstance(inbound_result.get("continuation_binding_failure"), dict):
            PROBE.record_failure(
                paths,
                inbound_result["continuation_binding_failure"],
                result=inbound_result,
            )
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                interrupted_event_id=interrupted_event_id,
                recovered_records=recovered_records,
                delay_observations=delay_observations,
                extra={"stopped_after": f"continuation_binding_{label}"},
            )
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after inbound {label}"},
        )

        if label == INTERRUPTED_TASK_LABEL:
            commit_or_stop(
                paths=paths,
                frontier=frontier,
                memory=memory,
                ledger=ledger,
                store=store,
                session=session,
                run_id=run_id,
                notes={"boundary": "before interrupted beta continuation claim"},
            )
            claimed = store.claim_next_pending(run_id=UUID(run_id))
            if claimed is None:
                PROBE.record_failure(
                    paths,
                    PROBE.model_output_failure(
                        code="missing_interrupted_claim",
                        stage="interruption",
                        message="beta continuation was not claimable",
                    ),
                )
                return finalize_results(
                    paths=paths,
                    run_id=run_id,
                    live_model_calls=live_model_calls,
                    endpoint=endpoint,
                    model=model,
                    terminal_tool_choice=terminal_tool_choice,
                store=store,
                interrupted_event_id=interrupted_event_id,
                recovered_records=recovered_records,
                delay_observations=delay_observations,
                extra={"stopped_after": "interrupted_claim"},
            )
            interrupted_event_id = str(claimed[0]["event_id"])
            delay_observations.append(
                observe_delay(
                    label="beta-restart-delay",
                    seconds=delay_seconds,
                    event=claimed[0],
                )
            )
            resumed_memory = PROBE.LocalMemorySubstrate()
            resumed_ledger = PROBE.ActionLedger(paths.action_log)
            resumed_frontier = PROBE.RestartFrontierStore(
                frontier_path=paths.frontier_log,
                memory_snapshot_path=paths.memory_snapshot,
            )
            load = resumed_frontier.load_latest(
                run_id=run_id,
                memory=resumed_memory,
                ledger=resumed_ledger,
                event_store=store,
            )
            recovered_records = load.recovered_event_records
            resumed_session = PROBE.make_session(
                paths=paths,
                backend=backend,
                model=model,
                resume=True,
            )
            continuation_result = run_pending_event(
                session=resumed_session,
                store=store,
                paths=paths,
                terminal_tool_choice=terminal_tool_choice,
            )
            session = resumed_session
            memory = resumed_memory
            ledger = resumed_ledger
            frontier = resumed_frontier
        else:
            continuation_result = run_pending_event(
                session=session,
                store=store,
                paths=paths,
                terminal_tool_choice=terminal_tool_choice,
            )
        if continuation_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                interrupted_event_id=interrupted_event_id,
                recovered_records=recovered_records,
                delay_observations=delay_observations,
                extra={"stopped_after": f"continuation_{label}"},
            )
        synthesis_record_ids.append(str(continuation_result["result_record_id"]))
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after continuation {label}"},
        )

        append_housekeeping_event(
            store=store,
            session=session,
            terminal_tool_choice=terminal_tool_choice,
        )
        housekeeping_result = run_pending_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if housekeeping_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                interrupted_event_id=interrupted_event_id,
                recovered_records=recovered_records,
                delay_observations=delay_observations,
                extra={"stopped_after": f"housekeeping_{label}"},
            )
        synthesis_record_ids.append(str(housekeeping_result["result_record_id"]))
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after housekeeping {label}"},
        )

        report_event = append_periodic_report_event(
            store=store,
            session=session,
            workstream=workstream,
            context_record_ids=[str(continuation_result["result_record_id"]), str(housekeeping_result["result_record_id"])],
            terminal_tool_choice=terminal_tool_choice,
        )
        if label == "alpha":
            delay_observations.append(
                observe_delay(
                    label="alpha-report-delay",
                    seconds=delay_seconds,
                    event=report_event,
                )
            )
        report_result = run_pending_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if report_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                interrupted_event_id=interrupted_event_id,
                recovered_records=recovered_records,
                delay_observations=delay_observations,
                extra={"stopped_after": f"periodic_report_{label}"},
            )
        synthesis_record_ids.append(str(report_result["result_record_id"]))
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after periodic report {label}"},
        )

    append_final_event(
        store=store,
        session=session,
        result_record_ids=synthesis_record_ids,
        terminal_tool_choice=terminal_tool_choice,
    )
    final_result = run_pending_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final_result.get("status") == "completed":
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": "after final synthesis"},
        )
    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
        interrupted_event_id=interrupted_event_id,
        recovered_records=recovered_records,
        delay_observations=delay_observations,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--terminal-tool-choice", default=None)
    parser.add_argument("--delay-seconds", type=float, default=DEFAULT_DELAY_SECONDS)
    args = parser.parse_args(argv)
    if args.write_prereg:
        write_preregistration_artifacts(args.output_root, live_model_calls=args.live)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}))
        return 0
    if not args.live and not args.dry_run:
        parser.error("choose --dry-run or --live")
    result = run_probe(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=os.environ.get(args.api_key_env, "") if args.live else None,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        terminal_tool_choice=args.terminal_tool_choice,
        delay_seconds=args.delay_seconds,
    )
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
