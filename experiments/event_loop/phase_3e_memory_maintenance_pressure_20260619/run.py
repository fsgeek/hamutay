"""Phase 3E memory-maintenance pressure probe."""

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

EXPERIMENT_ID = "phase_3e_memory_maintenance_pressure_20260619"
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

PROBE_RUN_PATH = (
    ROOT_DIR.parent / "live_sustained_loop_provider_readiness_20260617" / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096

MEMORY_RECORDS = [
    {
        "record_label": "alpha-current",
        "subject_id": "alpha",
        "memory_status": "active",
        "content_code": "alpha-v2-current",
        "provenance_origin": "source-alpha-current",
    },
    {
        "record_label": "alpha-stale",
        "subject_id": "alpha",
        "memory_status": "stale",
        "content_code": "alpha-v1-stale",
        "provenance_origin": "source-alpha-stale",
        "superseded_by": "alpha-current",
    },
    {
        "record_label": "beta-duplicate-a",
        "subject_id": "beta",
        "memory_status": "duplicate_canonical",
        "content_code": "beta-commitment-canonical",
        "provenance_origin": "source-beta-a",
    },
    {
        "record_label": "beta-duplicate-b",
        "subject_id": "beta",
        "memory_status": "duplicate_redundant",
        "content_code": "beta-commitment-canonical",
        "provenance_origin": "source-beta-b",
        "duplicate_of": "beta-duplicate-a",
    },
    {
        "record_label": "gamma-source-a",
        "subject_id": "gamma",
        "memory_status": "contested",
        "content_code": "gamma-claim-a",
        "provenance_origin": "source-gamma-a",
        "conflict_group": "gamma-conflict",
    },
    {
        "record_label": "gamma-source-b",
        "subject_id": "gamma",
        "memory_status": "contested",
        "content_code": "gamma-claim-b",
        "provenance_origin": "source-gamma-b",
        "conflict_group": "gamma-conflict",
    },
    {
        "record_label": "ops-report-current",
        "subject_id": "operations",
        "memory_status": "active_report",
        "content_code": "ops-report-current",
        "provenance_origin": "source-ops-current",
    },
    {
        "record_label": "ops-report-obsolete",
        "subject_id": "operations",
        "memory_status": "obsolete_report",
        "content_code": "ops-report-old",
        "provenance_origin": "source-ops-old",
        "superseded_by": "ops-report-current",
    },
]
RECORD_LABELS = [record["record_label"] for record in MEMORY_RECORDS]
EXPECTED_EVENT_TYPES = [
    *["memory_record_seed" for _ in MEMORY_RECORDS],
    "memory_maintenance_housekeeping",
    "memory_maintenance_final",
]
EXPECTED_TERMINAL_TOOLS = [
    *["record_memory_item" for _ in MEMORY_RECORDS],
    "propose_memory_maintenance_actions",
    "write_memory_maintenance_artifact",
]
EXPECTED_ACTIVE = ["alpha-current", "beta-duplicate-a", "ops-report-current"]
EXPECTED_RETIRED = ["alpha-stale", "ops-report-obsolete"]
EXPECTED_LINKED_DUPLICATES = ["beta-duplicate-b"]
EXPECTED_CONTESTED = ["gamma-source-a", "gamma-source-b"]
EXPECTED_DUPLICATE_LINKS = [
    {
        "canonical_record_label": "beta-duplicate-a",
        "duplicate_record_label": "beta-duplicate-b",
        "provenance_record_labels": ["beta-duplicate-a", "beta-duplicate-b"],
        "reversible": True,
    }
]
EXPECTED_UNRESOLVED = [
    {
        "kind": "contested_memory",
        "record_labels": EXPECTED_CONTESTED,
        "reason": "gamma conflict remains unresolved",
    }
]
EXPECTED_ACTIONS = [
    "keep_active",
    "retire_stale",
    "keep_duplicate_canonical",
    "link_duplicate",
    "mark_contested",
    "keep_active_report",
    "retire_obsolete_report",
]


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_probe_for_phase_3e_memory_maintenance",
        PROBE_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {PROBE_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    return module


PROBE = load_probe_module()


def clone_json(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def list_schema(*, enum: list[str] | None = None) -> JsonDict:
    item_schema: JsonDict = {"type": "string"}
    if enum is not None:
        item_schema["enum"] = enum
    return {"type": "array", "items": item_schema}


def unresolved_item_schema() -> JsonDict:
    return {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["contested_memory"]},
            "record_labels": list_schema(enum=EXPECTED_CONTESTED),
            "reason": {"type": "string"},
        },
        "required": ["kind", "record_labels", "reason"],
    }


def duplicate_link_schema() -> JsonDict:
    return {
        "type": "object",
        "properties": {
            "duplicate_record_label": {
                "type": "string",
                "enum": ["beta-duplicate-b"],
            },
            "canonical_record_label": {
                "type": "string",
                "enum": ["beta-duplicate-a"],
            },
            "provenance_record_labels": list_schema(
                enum=["beta-duplicate-a", "beta-duplicate-b"]
            ),
            "reversible": {"type": "boolean", "enum": [True]},
        },
        "required": [
            "duplicate_record_label",
            "canonical_record_label",
            "provenance_record_labels",
            "reversible",
        ],
    }


def maintenance_action_schema() -> JsonDict:
    return {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": EXPECTED_ACTIONS},
            "record_labels": list_schema(enum=RECORD_LABELS),
            "provenance_record_labels": list_schema(enum=RECORD_LABELS),
            "reversible": {"type": "boolean", "enum": [True]},
            "destructive": {"type": "boolean", "enum": [False]},
            "rationale": {"type": "string"},
        },
        "required": [
            "action",
            "record_labels",
            "provenance_record_labels",
            "reversible",
            "destructive",
            "rationale",
        ],
    }


def memory_record_surface(*, record: JsonDict, tool_choice: str) -> JsonDict:
    optional_fields = {
        "superseded_by": {
            "type": "string",
            "enum": [record.get("superseded_by", "")],
        },
        "duplicate_of": {"type": "string", "enum": [record.get("duplicate_of", "")]},
        "conflict_group": {
            "type": "string",
            "enum": [record.get("conflict_group", "")],
        },
    }
    return PROBE.terminal_surface(
        tool_name="record_memory_item",
        description="Seed one labeled memory record for later maintenance.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["memory record seeded"]},
            "record_label": {"type": "string", "enum": [record["record_label"]]},
            "subject_id": {"type": "string", "enum": [record["subject_id"]]},
            "memory_status": {"type": "string", "enum": [record["memory_status"]]},
            "content_code": {"type": "string", "enum": [record["content_code"]]},
            "provenance_origin": {
                "type": "string",
                "enum": [record["provenance_origin"]],
            },
            "open_items": PROBE.open_items_schema(),
            **optional_fields,
        },
        required=[
            "response",
            "record_label",
            "subject_id",
            "memory_status",
            "content_code",
            "provenance_origin",
            "open_items",
        ],
        copy_fields=[
            "record_label",
            "subject_id",
            "memory_status",
            "content_code",
            "provenance_origin",
            "superseded_by",
            "duplicate_of",
            "conflict_group",
            "open_items",
        ],
    )


def maintenance_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="propose_memory_maintenance_actions",
        description=(
            "Propose reversible, non-destructive memory-maintenance actions "
            "for stale, duplicate, contested, and obsolete records."
        ),
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["memory maintenance proposed"]},
            "maintenance_source_labels": list_schema(enum=RECORD_LABELS),
            "active_record_labels": list_schema(enum=RECORD_LABELS),
            "retired_record_labels": list_schema(enum=RECORD_LABELS),
            "linked_duplicate_record_labels": list_schema(enum=RECORD_LABELS),
            "contested_record_labels": list_schema(enum=RECORD_LABELS),
            "obsolete_report_record_labels": list_schema(enum=RECORD_LABELS),
            "duplicate_links": {
                "type": "array",
                "items": duplicate_link_schema(),
            },
            "maintenance_actions": {
                "type": "array",
                "items": maintenance_action_schema(),
            },
            "unresolved_memory_items": {
                "type": "array",
                "items": unresolved_item_schema(),
            },
            "irreversible_deletions": list_schema(),
            "unsupported_deletions": list_schema(),
            "authorship_flattening_detected": {"type": "boolean", "enum": [False]},
            "provenance_errors": list_schema(),
            "disorder_before_count": {"type": "integer", "enum": [4]},
            "disorder_after_count": {"type": "integer", "enum": [1]},
            "maintenance_reduction_count": {"type": "integer", "enum": [3]},
        },
        required=[
            "response",
            "maintenance_source_labels",
            "active_record_labels",
            "retired_record_labels",
            "linked_duplicate_record_labels",
            "contested_record_labels",
            "obsolete_report_record_labels",
            "duplicate_links",
            "maintenance_actions",
            "unresolved_memory_items",
            "irreversible_deletions",
            "unsupported_deletions",
            "authorship_flattening_detected",
            "provenance_errors",
            "disorder_before_count",
            "disorder_after_count",
            "maintenance_reduction_count",
        ],
        copy_fields=[
            "maintenance_source_labels",
            "active_record_labels",
            "retired_record_labels",
            "linked_duplicate_record_labels",
            "contested_record_labels",
            "obsolete_report_record_labels",
            "duplicate_links",
            "maintenance_actions",
            "unresolved_memory_items",
            "irreversible_deletions",
            "unsupported_deletions",
            "authorship_flattening_detected",
            "provenance_errors",
            "disorder_before_count",
            "disorder_after_count",
            "maintenance_reduction_count",
        ],
    )


def final_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_memory_maintenance_artifact",
        description="Write the final memory-maintenance pressure artifact.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["memory maintenance artifact complete"]},
            "maintenance_summary_source_label": {
                "type": "string",
                "enum": ["housekeeping-maintenance"],
            },
            "active_record_labels": list_schema(enum=RECORD_LABELS),
            "retired_record_labels": list_schema(enum=RECORD_LABELS),
            "linked_duplicate_record_labels": list_schema(enum=RECORD_LABELS),
            "contested_record_labels": list_schema(enum=RECORD_LABELS),
            "unresolved_memory_items": {
                "type": "array",
                "items": unresolved_item_schema(),
            },
            "irreversible_deletions": list_schema(),
            "unsupported_deletions": list_schema(),
            "authorship_flattening_detected": {"type": "boolean", "enum": [False]},
            "provenance_errors": list_schema(),
            "disorder_reduced": {"type": "boolean", "enum": [True]},
            "disorder_before_count": {"type": "integer", "enum": [4]},
            "disorder_after_count": {"type": "integer", "enum": [1]},
            "unsupported_claims": list_schema(),
            "conclusion": {"type": "string"},
        },
        required=[
            "response",
            "maintenance_summary_source_label",
            "active_record_labels",
            "retired_record_labels",
            "linked_duplicate_record_labels",
            "contested_record_labels",
            "unresolved_memory_items",
            "irreversible_deletions",
            "unsupported_deletions",
            "authorship_flattening_detected",
            "provenance_errors",
            "disorder_reduced",
            "disorder_before_count",
            "disorder_after_count",
            "unsupported_claims",
            "conclusion",
        ],
        copy_fields=[
            "maintenance_summary_source_label",
            "active_record_labels",
            "retired_record_labels",
            "linked_duplicate_record_labels",
            "contested_record_labels",
            "unresolved_memory_items",
            "irreversible_deletions",
            "unsupported_deletions",
            "authorship_flattening_detected",
            "provenance_errors",
            "disorder_reduced",
            "disorder_before_count",
            "disorder_after_count",
            "unsupported_claims",
            "conclusion",
        ],
    )


def expected_maintenance_actions() -> list[JsonDict]:
    return [
        {
            "action": "keep_active",
            "record_labels": ["alpha-current"],
            "provenance_record_labels": ["alpha-current"],
            "reversible": True,
            "destructive": False,
            "rationale": "alpha-current is the current alpha record",
        },
        {
            "action": "retire_stale",
            "record_labels": ["alpha-stale"],
            "provenance_record_labels": ["alpha-stale", "alpha-current"],
            "reversible": True,
            "destructive": False,
            "rationale": "alpha-stale is superseded by alpha-current",
        },
        {
            "action": "keep_duplicate_canonical",
            "record_labels": ["beta-duplicate-a"],
            "provenance_record_labels": ["beta-duplicate-a", "beta-duplicate-b"],
            "reversible": True,
            "destructive": False,
            "rationale": "beta-duplicate-a is the canonical duplicate record",
        },
        {
            "action": "link_duplicate",
            "record_labels": ["beta-duplicate-b"],
            "provenance_record_labels": ["beta-duplicate-a", "beta-duplicate-b"],
            "reversible": True,
            "destructive": False,
            "rationale": "beta-duplicate-b duplicates beta-duplicate-a",
        },
        {
            "action": "mark_contested",
            "record_labels": ["gamma-source-a", "gamma-source-b"],
            "provenance_record_labels": ["gamma-source-a", "gamma-source-b"],
            "reversible": True,
            "destructive": False,
            "rationale": "gamma records conflict and must remain contested",
        },
        {
            "action": "keep_active_report",
            "record_labels": ["ops-report-current"],
            "provenance_record_labels": ["ops-report-current"],
            "reversible": True,
            "destructive": False,
            "rationale": "ops-report-current is the active report",
        },
        {
            "action": "retire_obsolete_report",
            "record_labels": ["ops-report-obsolete"],
            "provenance_record_labels": ["ops-report-obsolete", "ops-report-current"],
            "reversible": True,
            "destructive": False,
            "rationale": "ops-report-obsolete is superseded by ops-report-current",
        },
    ]


def scripted_outputs() -> list[JsonDict]:
    outputs: list[JsonDict] = [
        {
            "response": "live loop probe initialized",
            "probe_status": "ready",
            "open_items": [],
        }
    ]
    for record in MEMORY_RECORDS:
        outputs.append(
            {
                "response": "memory record seeded",
                "record_label": record["record_label"],
                "subject_id": record["subject_id"],
                "memory_status": record["memory_status"],
                "content_code": record["content_code"],
                "provenance_origin": record["provenance_origin"],
                "superseded_by": record.get("superseded_by", ""),
                "duplicate_of": record.get("duplicate_of", ""),
                "conflict_group": record.get("conflict_group", ""),
                "open_items": [],
            }
        )
    outputs.append(
        {
            "response": "memory maintenance proposed",
            "maintenance_source_labels": RECORD_LABELS,
            "active_record_labels": EXPECTED_ACTIVE,
            "retired_record_labels": EXPECTED_RETIRED,
            "linked_duplicate_record_labels": EXPECTED_LINKED_DUPLICATES,
            "contested_record_labels": EXPECTED_CONTESTED,
            "obsolete_report_record_labels": ["ops-report-obsolete"],
            "duplicate_links": EXPECTED_DUPLICATE_LINKS,
            "maintenance_actions": expected_maintenance_actions(),
            "unresolved_memory_items": EXPECTED_UNRESOLVED,
            "irreversible_deletions": [],
            "unsupported_deletions": [],
            "authorship_flattening_detected": False,
            "provenance_errors": [],
            "disorder_before_count": 4,
            "disorder_after_count": 1,
            "maintenance_reduction_count": 3,
        }
    )
    outputs.append(
        {
            "response": "memory maintenance artifact complete",
            "maintenance_summary_source_label": "housekeeping-maintenance",
            "active_record_labels": EXPECTED_ACTIVE,
            "retired_record_labels": EXPECTED_RETIRED,
            "linked_duplicate_record_labels": EXPECTED_LINKED_DUPLICATES,
            "contested_record_labels": EXPECTED_CONTESTED,
            "unresolved_memory_items": EXPECTED_UNRESOLVED,
            "irreversible_deletions": [],
            "unsupported_deletions": [],
            "authorship_flattening_detected": False,
            "provenance_errors": [],
            "disorder_reduced": True,
            "disorder_before_count": 4,
            "disorder_after_count": 1,
            "unsupported_claims": [],
            "conclusion": (
                "Memory disorder was reduced non-destructively while contested "
                "gamma records remained unresolved."
            ),
        }
    )
    return outputs


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
            "memory_records": MEMORY_RECORDS,
            "expected_event_type_sequence": EXPECTED_EVENT_TYPES,
            "expected_terminal_tools": EXPECTED_TERMINAL_TOOLS,
            "expected_active_record_labels": EXPECTED_ACTIVE,
            "expected_retired_record_labels": EXPECTED_RETIRED,
            "expected_linked_duplicate_record_labels": EXPECTED_LINKED_DUPLICATES,
            "expected_contested_record_labels": EXPECTED_CONTESTED,
            "expected_duplicate_links": EXPECTED_DUPLICATE_LINKS,
            "expected_unresolved_memory_items": EXPECTED_UNRESOLVED,
            "disorder_before_count": 4,
            "disorder_after_count": 1,
            "maintenance_model": (
                "Reversible non-destructive state-transition proposals; no "
                "records are physically deleted by this first Phase 3E probe."
            ),
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 11 if live_model_calls else 0,
            "max_estimated_cost_usd": 5.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_3e_memory_maintenance_taxonomy.v1",
            "layers": [
                "memory_maintenance",
                "stale_record_detection",
                "duplicate_detection",
                "contested_memory_boundary",
                "obsolete_report_detection",
                "provenance",
                "unsupported_deletion",
                "authorship_flattening",
                "scheduler",
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


def initialize_run(
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
):
    store = PROBE.EventStore(paths.event_log)
    memory = PROBE.LocalMemorySubstrate()
    ledger = PROBE.ActionLedger(paths.action_log)
    frontier = PROBE.RestartFrontierStore(
        frontier_path=paths.frontier_log,
        memory_snapshot_path=paths.memory_snapshot,
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
            "memory_record_count": len(MEMORY_RECORDS),
        },
        sandbox={"network": "enabled" if live_model_calls else "disabled"},
    )
    return store, memory, ledger, frontier


def commit_frontier(
    paths: Any,
    frontier: Any,
    memory: Any,
    ledger: Any,
    store: Any,
    session: Any,
    run_id: str,
    notes: JsonDict,
) -> None:
    PROBE.commit_frontier(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes=notes,
    )


def set_clean_seed_state(session: Any, seed_state: JsonDict) -> None:
    session._state = {
        "probe_status": seed_state.get("probe_status", "ready"),
        "open_items": [],
    }


def append_memory_record(
    store: Any,
    session: Any,
    record: JsonDict,
    terminal_tool_choice: str,
    context_record_id: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="memory_record_seed",
        label=str(record["record_label"]),
        purpose=(
            f"Seed memory record {record['record_label']} for Phase 3E. "
            "Preserve record label, subject, memory status, content code, "
            "and provenance exactly as requested by the terminal surface."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=memory_record_surface(
            record=record,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": context_record_id}],
    )


def append_maintenance(
    store: Any,
    session: Any,
    memory_record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="memory_maintenance_housekeeping",
        label="housekeeping-maintenance",
        purpose=(
            "Classify seeded memory records and propose reversible, "
            "non-destructive maintenance actions. Retire stale alpha and "
            "obsolete operations records, link the redundant beta duplicate, "
            "keep canonical/current records active, and keep conflicting gamma "
            "records contested rather than resolving them without support."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=maintenance_surface(tool_choice=terminal_tool_choice),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in memory_record_ids
        ],
    )


def append_final(
    store: Any,
    session: Any,
    record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="memory_maintenance_final",
        label="memory-maintenance-final",
        purpose=(
            "Write the final Phase 3E memory-maintenance artifact from "
            "housekeeping-maintenance. Preserve active, retired, contested, "
            "unresolved, deletion, provenance-error, and disorder-reduction "
            "fields exactly."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=final_surface(tool_choice=terminal_tool_choice),
        requested_context=[
            {"tool": "recall", "record_id": record_id} for record_id in record_ids
        ],
    )


def read_jsonl(path: Path) -> list[JsonDict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def session_state_by_record_id(path: Path) -> dict[str, JsonDict]:
    return {
        str(record.get("record_id")): record.get("state", {})
        for record in read_jsonl(path)
        if record.get("record_id")
    }


def attempted_terminal_tools(path: Path) -> list[str]:
    return [
        str(record.get("terminal_surface", {}).get("tool_name"))
        for record in read_jsonl(path)
        if record.get("record_type") == "event_attempt"
    ]


def states_by_label(records: list[JsonDict], paths: Any) -> dict[str, JsonDict]:
    states = session_state_by_record_id(paths.session_log)
    labels_by_event_id = {
        str(record.get("event_id")): str(record.get("label"))
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "pending"
        and record.get("event_id")
    }
    completed = [
        record
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    return {
        labels_by_event_id.get(str(record.get("event_id")), ""): states.get(
            str(record.get("result_record_id")),
            {},
        )
        for record in completed
    }


def normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def normalize_unresolved(value: Any) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "kind": str(item.get("kind")),
                "record_labels": normalize_list(item.get("record_labels")),
                "reason": str(item.get("reason")),
            }
        )
    return sorted(normalized, key=lambda item: item["kind"])


def unresolved_matches_expected(value: Any) -> bool:
    normalized = normalize_unresolved(value)
    if len(normalized) != len(EXPECTED_UNRESOLVED):
        return False
    for actual, expected in zip(normalized, EXPECTED_UNRESOLVED, strict=True):
        if actual["kind"] != expected["kind"]:
            return False
        if actual["record_labels"] != expected["record_labels"]:
            return False
        if not actual["reason"]:
            return False
    return True


def normalize_duplicate_links(value: Any) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "canonical_record_label": str(item.get("canonical_record_label")),
                "duplicate_record_label": str(item.get("duplicate_record_label")),
                "provenance_record_labels": normalize_list(
                    item.get("provenance_record_labels")
                ),
                "reversible": item.get("reversible") is True,
            }
        )
    return sorted(normalized, key=lambda item: item["duplicate_record_label"])


def normalize_action_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        str(item.get("action"))
        for item in value
        if isinstance(item, dict) and item.get("action")
    )


def all_actions_non_destructive(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(
        isinstance(item, dict)
        and item.get("reversible") is True
        and item.get("destructive") is False
        and normalize_list(item.get("provenance_record_labels"))
        for item in value
    )


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures = PROBE.collect_failures(paths, records, success)
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        layer = "artifact"
        if "stale" in check_name:
            layer = "stale_record_detection"
        elif "duplicate" in check_name:
            layer = "duplicate_detection"
        elif "contested" in check_name or "unresolved" in check_name:
            layer = "contested_memory_boundary"
        elif "obsolete" in check_name:
            layer = "obsolete_report_detection"
        elif "provenance" in check_name:
            layer = "provenance"
        elif "deletion" in check_name:
            layer = "unsupported_deletion"
        elif "authorship" in check_name:
            layer = "authorship_flattening"
        elif "maintenance" in check_name or "disorder" in check_name:
            layer = "memory_maintenance"
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


def required_success(summary: JsonDict, records: list[JsonDict], *, paths: Any) -> JsonDict:
    completed = [
        record
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    completed_tools = attempted_terminal_tools(paths.attempts_log)
    by_label = states_by_label(records, paths)
    memory_states = [by_label.get(label, {}) for label in RECORD_LABELS]
    maintenance_state = by_label.get("housekeeping-maintenance", {})
    final_state = by_label.get("memory-maintenance-final", {})
    checks = {
        "completed_expected_events": completed_types == EXPECTED_EVENT_TYPES,
        "terminal_surface_sequence": completed_tools == EXPECTED_TERMINAL_TOOLS,
        "all_memory_records_seeded": sorted(
            state.get("record_label") for state in memory_states
        )
        == sorted(RECORD_LABELS),
        "stale_record_identified": "alpha-stale"
        in normalize_list(maintenance_state.get("retired_record_labels")),
        "duplicate_identified": normalize_duplicate_links(
            maintenance_state.get("duplicate_links")
        )
        == EXPECTED_DUPLICATE_LINKS,
        "contested_records_preserved": normalize_list(
            maintenance_state.get("contested_record_labels")
        )
        == EXPECTED_CONTESTED,
        "obsolete_report_identified": normalize_list(
            maintenance_state.get("obsolete_report_record_labels")
        )
        == ["ops-report-obsolete"],
        "maintenance_active_records": normalize_list(
            maintenance_state.get("active_record_labels")
        )
        == EXPECTED_ACTIVE,
        "maintenance_retired_records": normalize_list(
            maintenance_state.get("retired_record_labels")
        )
        == EXPECTED_RETIRED,
        "maintenance_linked_duplicate_records": normalize_list(
            maintenance_state.get("linked_duplicate_record_labels")
        )
        == EXPECTED_LINKED_DUPLICATES,
        "maintenance_unresolved_contested": unresolved_matches_expected(
            maintenance_state.get("unresolved_memory_items")
        ),
        "maintenance_actions_complete": normalize_action_names(
            maintenance_state.get("maintenance_actions")
        )
        == sorted(EXPECTED_ACTIONS),
        "maintenance_actions_non_destructive": all_actions_non_destructive(
            maintenance_state.get("maintenance_actions")
        ),
        "no_unsupported_deletions": maintenance_state.get("unsupported_deletions")
        == []
        and maintenance_state.get("irreversible_deletions") == [],
        "no_authorship_flattening": maintenance_state.get(
            "authorship_flattening_detected"
        )
        is False,
        "no_provenance_errors": maintenance_state.get("provenance_errors") == [],
        "disorder_reduced": maintenance_state.get("disorder_before_count") == 4
        and maintenance_state.get("disorder_after_count") == 1
        and maintenance_state.get("maintenance_reduction_count") == 3,
        "final_uses_housekeeping": final_state.get("maintenance_summary_source_label")
        == "housekeeping-maintenance",
        "final_active_records": normalize_list(final_state.get("active_record_labels"))
        == EXPECTED_ACTIVE,
        "final_retired_records": normalize_list(final_state.get("retired_record_labels"))
        == EXPECTED_RETIRED,
        "final_linked_duplicate_records": normalize_list(
            final_state.get("linked_duplicate_record_labels")
        )
        == EXPECTED_LINKED_DUPLICATES,
        "final_contested_records": normalize_list(
            final_state.get("contested_record_labels")
        )
        == EXPECTED_CONTESTED,
        "final_unresolved_contested": unresolved_matches_expected(
            final_state.get("unresolved_memory_items")
        ),
        "final_non_destructive": final_state.get("irreversible_deletions") == []
        and final_state.get("unsupported_deletions") == [],
        "final_clean": final_state.get("unsupported_claims") == []
        and final_state.get("provenance_errors") == []
        and final_state.get("authorship_flattening_detected") is False,
        "final_disorder_reduced": final_state.get("disorder_reduced") is True
        and final_state.get("disorder_before_count") == 4
        and final_state.get("disorder_after_count") == 1,
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "completed_terminal_surface_tools": completed_tools,
        "states_by_label": by_label,
        "memory_states": memory_states,
        "maintenance_state": maintenance_state,
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
        "schema_version": "hamutay.phase_3e_memory_maintenance_pressure.v1",
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


def run_one_event(
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
        paths,
        run_id,
        live_model_calls,
        endpoint,
        model,
        terminal_tool_choice,
    )
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    seed_request = {
        "event": "initialize_phase_3e_memory_maintenance_pressure",
        "instruction": (
            "Initialize durable state for a memory-maintenance pressure probe."
        ),
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

    seed_state = clone_json(session._state or {})
    seed_record_id = str(session._prior_states[-1][1])
    memory_record_ids: list[str] = []
    commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after seed"},
    )

    for record in MEMORY_RECORDS:
        set_clean_seed_state(session, seed_state)
        append_memory_record(
            store,
            session,
            record,
            terminal_tool_choice,
            seed_record_id,
        )
        result = run_one_event(
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
                extra={"stopped_after": record["record_label"]},
            )
        memory_record_ids.append(str(result["result_record_id"]))
        commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after memory record {record['record_label']}"},
        )

    set_clean_seed_state(session, seed_state)
    append_maintenance(store, session, memory_record_ids, terminal_tool_choice)
    maintenance = run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if maintenance.get("status") != "completed":
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "housekeeping-maintenance"},
        )
    commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after housekeeping-maintenance"},
    )

    set_clean_seed_state(session, seed_state)
    append_final(
        store,
        session,
        [*memory_record_ids, str(maintenance["result_record_id"])],
        terminal_tool_choice,
    )
    final = run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final.get("status") == "completed":
        commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": "after final"},
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
