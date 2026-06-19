"""Model-contract compliance audit for reduced scaffolding failures."""

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

EXPERIMENT_ID = "model_contract_compliance_audit_20260619"
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

EXPECTED_EVENT_TYPES = [
    "contract_vocabulary_probe",
    "contract_provenance_probe",
    "contract_kind_source_probe",
    "contract_count_semantics_probe",
]
EXPECTED_TERMINAL_TOOLS = [
    "audit_vocabulary_contract",
    "audit_provenance_label_contract",
    "audit_kind_source_contract",
    "audit_count_semantics_contract",
]
EXPECTED_ACTION_LABELS = [
    "retire_stale",
    "retire_obsolete_report",
    "mark_contested",
]
EXPECTED_PROVENANCE_LINK = {
    "duplicate_record_label": "beta-duplicate-b",
    "canonical_record_label": "beta-duplicate-a",
    "provenance_record_labels": ["beta-duplicate-a", "beta-duplicate-b"],
}
EXPECTED_KIND_SOURCE = {
    "unresolved_kind": "contested_memory",
    "maintenance_summary_source_label": "housekeeping-maintenance",
}
EXPECTED_COUNTS = {
    "disorder_class_count_before": 4,
    "disorder_class_count_after": 1,
    "disorder_record_count_before": 5,
    "disorder_record_count_after": 2,
    "maintenance_reduction_class_count": 3,
}

CONTRACT_TEXT = """# Model Contract Compliance Audit Contract

Date: 2026-06-19

The audit isolates four contract obligations that failed or became ambiguous
in Phase 3F reduced scaffolding. Each obligation is tested in a separate
single-event probe with loose terminal value schemas and exact post-run
scoring.

## Required Behavior

1. The vocabulary probe must return exactly these action labels, in order:
   `retire_stale`, `retire_obsolete_report`, `mark_contested`.
2. The provenance probe must return visible record labels, not record ids:
   duplicate `beta-duplicate-b`, canonical `beta-duplicate-a`, provenance
   labels `beta-duplicate-a` and `beta-duplicate-b`, and
   `used_record_ids_as_provenance` false.
3. The kind/source probe must return `contested_memory` and
   `housekeeping-maintenance` without synonym drift.
4. The count-semantics probe must distinguish disorder classes from
   disordered records: class counts 4 to 1, record counts 5 to 2, class
   reduction 3.

## Pass Rule

The run passes only if all four probes complete in order, use the expected
terminal tools, return no unsupported claims, leave no runnable events, and
meet every exact postcondition.

## Interpretation

An isolated failure supports a model-contract or framework-contract weakness
for that obligation. Isolated success paired with Phase 3F failure supports a
context/load interaction rather than a basic inability to copy the contract.
"""

PREREGISTRATION_TEXT = """# Model Contract Compliance Audit Preregistration

Date: 2026-06-19

## Question

Were the Phase 3F reduced-scaffolding failures caused by basic model-contract
compliance failures, or did the model satisfy isolated contracts and fail only
under larger context/load pressure?

## Hypothesis

If the event-loop contract is viable but Phase 3F overloaded or under-specified
the model, isolated probes should pass. If one or more isolated probes fail,
the affected contract boundary needs stronger rails, clearer naming, or a
different representation before larger substrate-pressure tests can be
interpreted cleanly.

## Method

Run four isolated probes against the same event-loop machinery and terminal
surface style used by Phase 3F. The schemas require field names but do not
enumerate the target values. Exactness is scored after the run.

The probes are:

1. Vocabulary compliance.
2. Provenance label compliance.
3. Kind/source label compliance.
4. Count semantics compliance.

## Predictions

The most likely basic failures are action-label synonym drift, provenance
record-id substitution for labels, kind/source synonym drift, or class-count
versus record-count collapse. Passing all isolated probes would shift suspicion
toward context size, state accumulation, or multi-step workload pressure.

## Pass Criteria

Pass if all checks in `CONTRACT.md` are true.

## Failure Criteria

Fail if any check is false. Attribute failures to vocabulary compliance,
provenance label compliance, kind/source compliance, count semantics
compliance, model output, provider, artifact behavior, or inconclusive causes.

## Budget

Live direct-DeepSeek run budget: at most 5 model calls and at most 3 USD
estimated cost. Dry scripted runs make no model calls.
"""


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_probe_for_model_contract_compliance",
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


def list_schema() -> JsonDict:
    return {"type": "array", "items": {"type": "string"}}


def vocabulary_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="audit_vocabulary_contract",
        description="Return exact action labels from plain-text instructions.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string"},
            "probe_name": {"type": "string"},
            "action_labels": list_schema(),
            "unsupported_claims": list_schema(),
        },
        required=["response", "probe_name", "action_labels", "unsupported_claims"],
        copy_fields=["probe_name", "action_labels", "unsupported_claims"],
    )


def provenance_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="audit_provenance_label_contract",
        description="Return record labels as provenance, not record ids.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string"},
            "probe_name": {"type": "string"},
            "duplicate_record_label": {"type": "string"},
            "canonical_record_label": {"type": "string"},
            "provenance_record_labels": list_schema(),
            "used_record_ids_as_provenance": {"type": "boolean"},
            "unsupported_claims": list_schema(),
        },
        required=[
            "response",
            "probe_name",
            "duplicate_record_label",
            "canonical_record_label",
            "provenance_record_labels",
            "used_record_ids_as_provenance",
            "unsupported_claims",
        ],
        copy_fields=[
            "probe_name",
            "duplicate_record_label",
            "canonical_record_label",
            "provenance_record_labels",
            "used_record_ids_as_provenance",
            "unsupported_claims",
        ],
    )


def kind_source_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="audit_kind_source_contract",
        description="Return exact kind and source-label strings from plain text.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string"},
            "probe_name": {"type": "string"},
            "unresolved_kind": {"type": "string"},
            "maintenance_summary_source_label": {"type": "string"},
            "unsupported_claims": list_schema(),
        },
        required=[
            "response",
            "probe_name",
            "unresolved_kind",
            "maintenance_summary_source_label",
            "unsupported_claims",
        ],
        copy_fields=[
            "probe_name",
            "unresolved_kind",
            "maintenance_summary_source_label",
            "unsupported_claims",
        ],
    )


def count_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="audit_count_semantics_contract",
        description="Return exact disorder class and record count semantics.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string"},
            "probe_name": {"type": "string"},
            "disorder_class_count_before": {"type": "integer"},
            "disorder_class_count_after": {"type": "integer"},
            "disorder_record_count_before": {"type": "integer"},
            "disorder_record_count_after": {"type": "integer"},
            "maintenance_reduction_class_count": {"type": "integer"},
            "unsupported_claims": list_schema(),
        },
        required=[
            "response",
            "probe_name",
            "disorder_class_count_before",
            "disorder_class_count_after",
            "disorder_record_count_before",
            "disorder_record_count_after",
            "maintenance_reduction_class_count",
            "unsupported_claims",
        ],
        copy_fields=[
            "probe_name",
            "disorder_class_count_before",
            "disorder_class_count_after",
            "disorder_record_count_before",
            "disorder_record_count_after",
            "maintenance_reduction_class_count",
            "unsupported_claims",
        ],
    )


PROBES = [
    {
        "label": "vocabulary-compliance",
        "event_type": "contract_vocabulary_probe",
        "surface": vocabulary_surface,
        "purpose": (
            "Vocabulary compliance probe. The schema does not enum values. "
            "Return action_labels exactly as these three strings, preserving "
            "spelling and order: retire_stale, retire_obsolete_report, "
            "mark_contested. Do not shorten, synonymize, or paraphrase them."
        ),
    },
    {
        "label": "provenance-label-compliance",
        "event_type": "contract_provenance_probe",
        "surface": provenance_surface,
        "purpose": (
            "Provenance label compliance probe. The visible records have "
            "labels beta-duplicate-a and beta-duplicate-b. Their record ids "
            "are intentionally irrelevant. Return duplicate_record_label "
            "beta-duplicate-b, canonical_record_label beta-duplicate-a, and "
            "provenance_record_labels exactly [beta-duplicate-a, "
            "beta-duplicate-b]. Set used_record_ids_as_provenance false."
        ),
    },
    {
        "label": "kind-source-compliance",
        "event_type": "contract_kind_source_probe",
        "surface": kind_source_surface,
        "purpose": (
            "Kind/source label compliance probe. The schema does not enum "
            "values. Return unresolved_kind exactly contested_memory and "
            "maintenance_summary_source_label exactly housekeeping-maintenance."
        ),
    },
    {
        "label": "count-semantics-compliance",
        "event_type": "contract_count_semantics_probe",
        "surface": count_surface,
        "purpose": (
            "Count semantics compliance probe. Disorder class counts and "
            "record counts are different. There are four disorder classes "
            "before maintenance and one after maintenance. There are five "
            "disordered records before maintenance and two after maintenance. "
            "Return disorder_class_count_before 4, disorder_class_count_after "
            "1, disorder_record_count_before 5, disorder_record_count_after 2, "
            "and maintenance_reduction_class_count 3."
        ),
    },
]


def scripted_outputs() -> list[JsonDict]:
    return [
        {
            "response": "live loop probe initialized",
            "probe_status": "ready",
            "open_items": [],
        },
        {
            "response": "vocabulary compliance complete",
            "probe_name": "vocabulary-compliance",
            "action_labels": EXPECTED_ACTION_LABELS,
            "unsupported_claims": [],
        },
        {
            "response": "provenance label compliance complete",
            "probe_name": "provenance-label-compliance",
            **EXPECTED_PROVENANCE_LINK,
            "used_record_ids_as_provenance": False,
            "unsupported_claims": [],
        },
        {
            "response": "kind source compliance complete",
            "probe_name": "kind-source-compliance",
            **EXPECTED_KIND_SOURCE,
            "unsupported_claims": [],
        },
        {
            "response": "count semantics compliance complete",
            "probe_name": "count-semantics-compliance",
            **EXPECTED_COUNTS,
            "unsupported_claims": [],
        },
    ]


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "CONTRACT.md": CONTRACT_TEXT,
        "PRE_REGISTRATION.md": PREREGISTRATION_TEXT,
        "matrix.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "expected_event_type_sequence": EXPECTED_EVENT_TYPES,
            "expected_terminal_tools": EXPECTED_TERMINAL_TOOLS,
            "probes": [
                {
                    "label": probe["label"],
                    "event_type": probe["event_type"],
                    "purpose": probe["purpose"],
                }
                for probe in PROBES
            ],
            "expected_action_labels": EXPECTED_ACTION_LABELS,
            "expected_provenance_link": EXPECTED_PROVENANCE_LINK,
            "expected_kind_source": EXPECTED_KIND_SOURCE,
            "expected_counts": EXPECTED_COUNTS,
            "schema_profile": {
                "field_names_required": True,
                "exact_value_enums_removed": True,
                "scoring_exact": True,
                "probes_are_isolated": True,
            },
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 5 if live_model_calls else 0,
            "max_estimated_cost_usd": 3.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.model_contract_compliance_audit_taxonomy.v1",
            "layers": [
                "vocabulary_compliance",
                "provenance_label_compliance",
                "kind_source_compliance",
                "count_semantics_compliance",
                "model_output",
                "provider",
                "artifact",
                "inconclusive",
            ],
        },
    }
    for name, payload in artifacts.items():
        path = output_root / name
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            PROBE.write_json(path, payload)
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


def append_compliance_probe(
    *,
    store: Any,
    session: Any,
    probe: JsonDict,
    terminal_tool_choice: str,
) -> JsonDict:
    surface_factory = probe["surface"]
    return PROBE.append_probe_event(
        store,
        event_type=str(probe["event_type"]),
        label=str(probe["label"]),
        purpose=str(probe["purpose"]),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=surface_factory(tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": session._prior_states[-1][1]}],
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


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures = PROBE.collect_failures(paths, records, success)
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        layer = "artifact"
        if "vocabulary" in check_name:
            layer = "vocabulary_compliance"
        elif "provenance" in check_name:
            layer = "provenance_label_compliance"
        elif "kind" in check_name or "source" in check_name:
            layer = "kind_source_compliance"
        elif "count" in check_name:
            layer = "count_semantics_compliance"
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
    vocabulary_state = by_label.get("vocabulary-compliance", {})
    provenance_state = by_label.get("provenance-label-compliance", {})
    kind_source_state = by_label.get("kind-source-compliance", {})
    count_state = by_label.get("count-semantics-compliance", {})
    checks = {
        "completed_expected_events": completed_types == EXPECTED_EVENT_TYPES,
        "terminal_surface_sequence": completed_tools == EXPECTED_TERMINAL_TOOLS,
        "vocabulary_exact": vocabulary_state.get("action_labels")
        == EXPECTED_ACTION_LABELS,
        "vocabulary_clean": vocabulary_state.get("unsupported_claims") == [],
        "provenance_uses_record_labels": {
            "duplicate_record_label": provenance_state.get("duplicate_record_label"),
            "canonical_record_label": provenance_state.get("canonical_record_label"),
            "provenance_record_labels": normalize_list(
                provenance_state.get("provenance_record_labels")
            ),
        }
        == EXPECTED_PROVENANCE_LINK,
        "provenance_avoids_record_ids": provenance_state.get(
            "used_record_ids_as_provenance"
        )
        is False,
        "provenance_clean": provenance_state.get("unsupported_claims") == [],
        "kind_source_exact": {
            "unresolved_kind": kind_source_state.get("unresolved_kind"),
            "maintenance_summary_source_label": kind_source_state.get(
                "maintenance_summary_source_label"
            ),
        }
        == EXPECTED_KIND_SOURCE,
        "kind_source_clean": kind_source_state.get("unsupported_claims") == [],
        "count_semantics_exact": {
            "disorder_class_count_before": count_state.get(
                "disorder_class_count_before"
            ),
            "disorder_class_count_after": count_state.get(
                "disorder_class_count_after"
            ),
            "disorder_record_count_before": count_state.get(
                "disorder_record_count_before"
            ),
            "disorder_record_count_after": count_state.get(
                "disorder_record_count_after"
            ),
            "maintenance_reduction_class_count": count_state.get(
                "maintenance_reduction_class_count"
            ),
        }
        == EXPECTED_COUNTS,
        "count_semantics_clean": count_state.get("unsupported_claims") == [],
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
        "vocabulary_state": vocabulary_state,
        "provenance_state": provenance_state,
        "kind_source_state": kind_source_state,
        "count_state": count_state,
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
        "schema_version": "hamutay.model_contract_compliance_audit.v1",
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
        "event": "initialize_model_contract_compliance_audit",
        "instruction": "Initialize durable state for a model-contract compliance audit.",
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
    for probe in PROBES:
        session._state = {
            "probe_status": "ready",
            "open_items": [],
        }
        append_compliance_probe(
            store=store,
            session=session,
            probe=probe,
            terminal_tool_choice=terminal_tool_choice,
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
                extra={"stopped_after": probe["label"]},
            )
        commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after {probe['label']}"},
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
