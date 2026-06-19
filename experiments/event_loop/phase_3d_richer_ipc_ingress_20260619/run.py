"""Phase 3D richer IPC ingress probe."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import importlib.util
import json
import os
import sys
import typing as typing_module
from pathlib import Path
from typing import Any
from uuid import uuid4


JsonDict = dict[str, Any]

EXPERIMENT_ID = "phase_3d_richer_ipc_ingress_20260619"
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

MESSAGE_PLAN = [
    {"event_type": "ipc_task", "label": "task-alpha", "workstream_id": "research"},
    {"event_type": "ipc_task", "label": "task-beta", "workstream_id": "operations"},
    {
        "event_type": "ipc_correction",
        "label": "correction-alpha",
        "workstream_id": "research",
    },
    {
        "event_type": "ipc_cancellation",
        "label": "cancel-beta",
        "workstream_id": "operations",
    },
    {
        "event_type": "ipc_cancellation",
        "label": "cancel-ghost",
        "workstream_id": "unknown",
    },
    {
        "event_type": "self_scheduled_reflection",
        "label": "continue-alpha-corrected",
        "workstream_id": "research",
    },
    {"event_type": "ipc_status_query", "label": "status-all", "workstream_id": "all"},
    {
        "event_type": "ipc_external_evidence",
        "label": "evidence-alpha",
        "workstream_id": "research",
    },
    {"event_type": "final_artifact_synthesis", "label": "final-ipc-synthesis"},
]
EXPECTED_EVENT_TYPES = [item["event_type"] for item in MESSAGE_PLAN]
EXPECTED_TERMINAL_TOOLS = [
    "handle_ipc_task",
    "handle_ipc_task",
    "handle_ipc_correction",
    "handle_ipc_cancellation",
    "handle_ipc_cancellation",
    "complete_corrected_ipc_continuation",
    "answer_ipc_status_query",
    "record_external_evidence",
    "write_ipc_ingress_artifact",
]


def load_longer_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "longer_horizon_for_phase_3d_ipc",
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
            "message_plan": MESSAGE_PLAN,
            "expected_completed_event_count": len(EXPECTED_EVENT_TYPES),
            "expected_event_type_sequence": EXPECTED_EVENT_TYPES,
            "expected_terminal_tools": EXPECTED_TERMINAL_TOOLS,
            "message_classes": [
                "task",
                "correction",
                "cancellation",
                "status_query",
                "external_evidence",
            ],
            "expected_categories": {
                "accepted": ["task-alpha", "task-beta"],
                "corrected": ["task-alpha"],
                "canceled": ["task-beta"],
                "rejected": ["cancel-ghost"],
                "completed": ["task-alpha"],
            },
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 10 if live_model_calls else 0,
            "max_estimated_cost_usd": 5.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_3d_richer_ipc_ingress_taxonomy.v1",
            "layers": [
                "ipc_ingress",
                "message_routing",
                "workstream_isolation",
                "continuation_binding",
                "scheduler_identity",
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


def task_terminal_surface(*, label: str, workstream_id: str, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="handle_ipc_task",
        description="Accept an IPC task message for exactly one workstream.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["ipc task accepted"]},
            "message_label": {"type": "string", "enum": [label]},
            "workstream_id": {"type": "string", "enum": [workstream_id]},
            "message_status": {"type": "string", "enum": ["accepted"]},
            "open_items": PROBE.open_items_schema(),
            "continuation_needed": {"type": "boolean"},
        },
        required=[
            "response",
            "message_label",
            "workstream_id",
            "message_status",
            "open_items",
            "continuation_needed",
        ],
        copy_fields=[
            "message_label",
            "workstream_id",
            "message_status",
            "open_items",
            "continuation_needed",
        ],
    )


def correction_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="handle_ipc_correction",
        description="Apply a correction to the research task without touching operations.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["ipc correction applied"]},
            "message_label": {"type": "string", "enum": ["correction-alpha"]},
            "target_message_label": {"type": "string", "enum": ["task-alpha"]},
            "workstream_id": {"type": "string", "enum": ["research"]},
            "correction_status": {"type": "string", "enum": ["applied"]},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "message_label",
            "target_message_label",
            "workstream_id",
            "correction_status",
            "open_items",
        ],
        copy_fields=[
            "message_label",
            "target_message_label",
            "workstream_id",
            "correction_status",
            "open_items",
        ],
    )


def cancellation_terminal_surface(
    *,
    label: str,
    target_label: str,
    workstream_id: str,
    status: str,
    tool_choice: str,
) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="handle_ipc_cancellation",
        description="Handle an IPC cancellation message.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": [f"ipc cancellation {status}"]},
            "message_label": {"type": "string", "enum": [label]},
            "target_message_label": {"type": "string", "enum": [target_label]},
            "workstream_id": {"type": "string", "enum": [workstream_id]},
            "cancellation_status": {"type": "string", "enum": [status]},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "message_label",
            "target_message_label",
            "workstream_id",
            "cancellation_status",
            "open_items",
        ],
        copy_fields=[
            "message_label",
            "target_message_label",
            "workstream_id",
            "cancellation_status",
            "open_items",
        ],
    )


def continuation_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="complete_corrected_ipc_continuation",
        description="Complete the corrected research task only.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["corrected ipc continuation complete"]},
            "completed_message_label": {"type": "string", "enum": ["task-alpha"]},
            "workstream_id": {"type": "string", "enum": ["research"]},
            "corrected_scope_applied": {"type": "boolean", "enum": [True]},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "completed_message_label",
            "workstream_id",
            "corrected_scope_applied",
            "open_items",
        ],
        copy_fields=[
            "completed_message_label",
            "workstream_id",
            "corrected_scope_applied",
            "open_items",
        ],
    )


def status_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="answer_ipc_status_query",
        description="Report current status for research and operations workstreams.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["ipc status query answered"]},
            "message_label": {"type": "string", "enum": ["status-all"]},
            "research_status": {"type": "string", "enum": ["completed"]},
            "operations_status": {"type": "string", "enum": ["canceled"]},
            "rejected_message_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "message_label",
            "research_status",
            "operations_status",
            "rejected_message_labels",
            "open_items",
        ],
        copy_fields=[
            "message_label",
            "research_status",
            "operations_status",
            "rejected_message_labels",
            "open_items",
        ],
    )


def evidence_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="record_external_evidence",
        description="Attach an external evidence notification to the research workstream.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["external evidence recorded"]},
            "message_label": {"type": "string", "enum": ["evidence-alpha"]},
            "workstream_id": {"type": "string", "enum": ["research"]},
            "evidence_status": {"type": "string", "enum": ["recorded"]},
            "cited_message_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "message_label",
            "workstream_id",
            "evidence_status",
            "cited_message_labels",
            "open_items",
        ],
        copy_fields=[
            "message_label",
            "workstream_id",
            "evidence_status",
            "cited_message_labels",
            "open_items",
        ],
    )


def final_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_ipc_ingress_artifact",
        description="Write the final richer-IPC ingress synthesis.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["ipc ingress artifact complete"]},
            "accepted_task_message_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "accepted_non_task_message_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "corrected_message_labels": {"type": "array", "items": {"type": "string"}},
            "canceled_message_labels": {"type": "array", "items": {"type": "string"}},
            "rejected_message_labels": {"type": "array", "items": {"type": "string"}},
            "completed_message_labels": {"type": "array", "items": {"type": "string"}},
            "research_status": {"type": "string", "enum": ["completed"]},
            "operations_status": {"type": "string", "enum": ["canceled"]},
            "audit_notes": {"type": "array", "items": {"type": "string"}},
            "unsupported_claim_candidates": {
                "type": "array",
                "items": {"type": "string"},
            },
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "unresolved_open_items": PROBE.open_items_schema(),
            "conclusion": {"type": "string"},
        },
        required=[
            "response",
            "accepted_task_message_labels",
            "accepted_non_task_message_labels",
            "corrected_message_labels",
            "canceled_message_labels",
            "rejected_message_labels",
            "completed_message_labels",
            "research_status",
            "operations_status",
            "audit_notes",
            "unsupported_claim_candidates",
            "unsupported_claims",
            "unresolved_open_items",
            "conclusion",
        ],
        copy_fields=[
            "accepted_task_message_labels",
            "accepted_non_task_message_labels",
            "corrected_message_labels",
            "canceled_message_labels",
            "rejected_message_labels",
            "completed_message_labels",
            "research_status",
            "operations_status",
            "audit_notes",
            "unsupported_claim_candidates",
            "unsupported_claims",
            "unresolved_open_items",
            "conclusion",
        ],
    )


def scripted_outputs() -> list[JsonDict]:
    return [
        {"response": "live loop probe initialized", "probe_status": "ready", "open_items": []},
        {
            "response": "ipc task accepted",
            "message_label": "task-alpha",
            "workstream_id": "research",
            "message_status": "accepted",
            "open_items": [{"kind": "task", "text": "complete corrected alpha"}],
            "continuation_needed": True,
        },
        {
            "response": "ipc task accepted",
            "message_label": "task-beta",
            "workstream_id": "operations",
            "message_status": "accepted",
            "open_items": [{"kind": "task", "text": "pending beta until cancellation"}],
            "continuation_needed": False,
        },
        {
            "response": "ipc correction applied",
            "message_label": "correction-alpha",
            "target_message_label": "task-alpha",
            "workstream_id": "research",
            "correction_status": "applied",
            "open_items": [{"kind": "task", "text": "complete corrected alpha"}],
        },
        {
            "response": "ipc cancellation accepted",
            "message_label": "cancel-beta",
            "target_message_label": "task-beta",
            "workstream_id": "operations",
            "cancellation_status": "accepted",
            "open_items": [],
        },
        {
            "response": "ipc cancellation rejected",
            "message_label": "cancel-ghost",
            "target_message_label": "task-ghost",
            "workstream_id": "unknown",
            "cancellation_status": "rejected",
            "open_items": [],
        },
        {
            "response": "corrected ipc continuation complete",
            "completed_message_label": "task-alpha",
            "workstream_id": "research",
            "corrected_scope_applied": True,
            "open_items": [],
        },
        {
            "response": "ipc status query answered",
            "message_label": "status-all",
            "research_status": "completed",
            "operations_status": "canceled",
            "rejected_message_labels": ["cancel-ghost"],
            "open_items": [],
        },
        {
            "response": "external evidence recorded",
            "message_label": "evidence-alpha",
            "workstream_id": "research",
            "evidence_status": "recorded",
            "cited_message_labels": ["task-alpha", "correction-alpha"],
            "open_items": [],
        },
        {
            "response": "ipc ingress artifact complete",
            "accepted_task_message_labels": ["task-alpha", "task-beta"],
            "accepted_non_task_message_labels": [
                "correction-alpha",
                "cancel-beta",
                "status-all",
                "evidence-alpha",
            ],
            "corrected_message_labels": ["task-alpha"],
            "canceled_message_labels": ["task-beta"],
            "rejected_message_labels": ["cancel-ghost"],
            "completed_message_labels": ["task-alpha"],
            "research_status": "completed",
            "operations_status": "canceled",
            "audit_notes": [
                "cancel-beta applied to task-beta",
                "cancel-ghost rejected because task-ghost was unknown",
            ],
            "unsupported_claim_candidates": ["task-ghost was cancelable"],
            "unsupported_claims": [],
            "unresolved_open_items": [],
            "conclusion": "IPC ingress preserved routing and category separation.",
        },
    ]


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
            "message_plan": MESSAGE_PLAN,
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


def terminal_surface_for(item: JsonDict, tool_choice: str) -> JsonDict:
    label = str(item["label"])
    event_type = str(item["event_type"])
    workstream_id = str(item.get("workstream_id", ""))
    if event_type == "ipc_task":
        return task_terminal_surface(
            label=label,
            workstream_id=workstream_id,
            tool_choice=tool_choice,
        )
    if event_type == "ipc_correction":
        return correction_terminal_surface(tool_choice=tool_choice)
    if label == "cancel-beta":
        return cancellation_terminal_surface(
            label=label,
            target_label="task-beta",
            workstream_id="operations",
            status="accepted",
            tool_choice=tool_choice,
        )
    if label == "cancel-ghost":
        return cancellation_terminal_surface(
            label=label,
            target_label="task-ghost",
            workstream_id="unknown",
            status="rejected",
            tool_choice=tool_choice,
        )
    if event_type == "self_scheduled_reflection":
        return continuation_terminal_surface(tool_choice=tool_choice)
    if event_type == "ipc_status_query":
        return status_terminal_surface(tool_choice=tool_choice)
    if event_type == "ipc_external_evidence":
        return evidence_terminal_surface(tool_choice=tool_choice)
    return final_terminal_surface(tool_choice=tool_choice)


def append_ipc_event(
    *,
    store: Any,
    session: Any,
    item: JsonDict,
    terminal_tool_choice: str,
    context_record_ids: list[str],
) -> JsonDict:
    label = str(item["label"])
    event_type = str(item["event_type"])
    context = (
        [{"tool": "recall", "record_id": record_id} for record_id in context_record_ids]
        or [{"tool": "recall", "cycle": session.cycle}]
    )
    return PROBE.append_probe_event(
        store,
        event_type=event_type,
        label=label,
        purpose=(
            f"Handle richer IPC event {label} of type {event_type}. Preserve "
            "workstream routing, scheduler-owned event identity, and category "
            "separation exactly as requested by the terminal surface."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=terminal_surface_for(item, terminal_tool_choice),
        requested_context=context,
    )


def read_jsonl(path: Path) -> list[JsonDict]:
    return LONGER.read_jsonl(path)


def session_state_by_record_id(path: Path) -> dict[str, JsonDict]:
    return LONGER.session_state_by_record_id(path)


def attempted_terminal_tools(path: Path) -> list[str]:
    return LONGER.attempted_terminal_tools(path)


def material_outcome_warnings(summary: JsonDict) -> list[JsonDict]:
    return LONGER.material_outcome_warnings(summary)


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures = PROBE.collect_failures(paths, records, success)
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        layer = "artifact"
        if "routing" in check_name:
            layer = "message_routing"
        elif "isolation" in check_name or "category" in check_name:
            layer = "workstream_isolation"
        elif "continuation" in check_name:
            layer = "continuation_binding"
        elif "identity" in check_name or "sequence" in check_name:
            layer = "scheduler_identity"
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


def state_for_label(
    completed: list[JsonDict],
    states_by_record_id: dict[str, JsonDict],
    labels_by_event_id: dict[str, str],
    label: str,
) -> JsonDict:
    for record in completed:
        event_id = str(record.get("event_id"))
        if labels_by_event_id.get(event_id) == label:
            return states_by_record_id.get(str(record.get("result_record_id")), {})
    return {}


def required_success(summary: JsonDict, records: list[JsonDict], *, paths: Any) -> JsonDict:
    completed = [
        record
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    completed_tools = attempted_terminal_tools(paths.attempts_log)
    states_by_record_id = session_state_by_record_id(paths.session_log)
    labels_by_event_id = {
        str(record.get("event_id")): str(record.get("label"))
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "pending"
        and record.get("event_id")
        and record.get("label")
    }
    states_by_label = {
        str(item["label"]): state_for_label(
            completed,
            states_by_record_id,
            labels_by_event_id,
            str(item["label"]),
        )
        for item in MESSAGE_PLAN
    }
    final_state = states_by_label["final-ipc-synthesis"]
    checks = {
        "completed_expected_events": len(completed) == len(EXPECTED_EVENT_TYPES),
        "event_type_sequence": completed_types == EXPECTED_EVENT_TYPES,
        "terminal_surface_sequence": completed_tools == EXPECTED_TERMINAL_TOOLS,
        "task_routing": states_by_label["task-alpha"].get("workstream_id") == "research"
        and states_by_label["task-beta"].get("workstream_id") == "operations",
        "correction_applied_to_alpha": states_by_label["correction-alpha"].get(
            "target_message_label"
        )
        == "task-alpha"
        and states_by_label["correction-alpha"].get("workstream_id") == "research",
        "cancellation_isolated_to_beta": states_by_label["cancel-beta"].get(
            "target_message_label"
        )
        == "task-beta"
        and states_by_label["cancel-beta"].get("cancellation_status") == "accepted",
        "unknown_cancellation_rejected": states_by_label["cancel-ghost"].get(
            "cancellation_status"
        )
        == "rejected",
        "corrected_continuation_completed": states_by_label[
            "continue-alpha-corrected"
        ].get("completed_message_label")
        == "task-alpha"
        and states_by_label["continue-alpha-corrected"].get("corrected_scope_applied")
        is True,
        "status_query_consistent": states_by_label["status-all"].get("research_status")
        == "completed"
        and states_by_label["status-all"].get("operations_status") == "canceled"
        and states_by_label["status-all"].get("rejected_message_labels")
        == ["cancel-ghost"],
        "external_evidence_routed": states_by_label["evidence-alpha"].get(
            "workstream_id"
        )
        == "research"
        and sorted(states_by_label["evidence-alpha"].get("cited_message_labels") or [])
        == ["correction-alpha", "task-alpha"],
        "final_categories": sorted(final_state.get("accepted_task_message_labels") or [])
        == ["task-alpha", "task-beta"]
        and sorted(final_state.get("accepted_non_task_message_labels") or [])
        == ["cancel-beta", "correction-alpha", "evidence-alpha", "status-all"]
        and final_state.get("corrected_message_labels") == ["task-alpha"]
        and final_state.get("canceled_message_labels") == ["task-beta"]
        and final_state.get("rejected_message_labels") == ["cancel-ghost"]
        and final_state.get("completed_message_labels") == ["task-alpha"],
        "final_workstream_isolation": final_state.get("research_status")
        == "completed"
        and final_state.get("operations_status") == "canceled",
        "final_clean": final_state.get("unsupported_claims") == []
        and final_state.get("unresolved_open_items") == [],
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
        "states_by_label": states_by_label,
        "final_state": final_state,
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
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    success = required_success(summary, records, paths=paths)
    failures = collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.phase_3d_richer_ipc_ingress.v1",
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
        "event": "initialize_phase_3d_richer_ipc_ingress",
        "instruction": "Initialize durable state for a richer IPC ingress probe.",
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

    result_record_ids: dict[str, str] = {}
    for item in MESSAGE_PLAN:
        label = str(item["label"])
        context_record_ids = list(result_record_ids.values())
        append_ipc_event(
            store=store,
            session=session,
            item=item,
            terminal_tool_choice=terminal_tool_choice,
            context_record_ids=context_record_ids,
        )
        result = run_pending_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                extra={"stopped_after": label},
            )
        result_record_ids[label] = str(result["result_record_id"])
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after {label}"},
        )
    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
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
    )
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
