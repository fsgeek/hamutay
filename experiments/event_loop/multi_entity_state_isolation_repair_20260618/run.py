"""Multi-entity state-isolation repair probe."""

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

EXPERIMENT_ID = "multi_entity_state_isolation_repair_20260618"
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
    ROOT_DIR.parent
    / "live_sustained_loop_provider_readiness_20260617"
    / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
ENTITIES = [
    {"entity_id": "entity_red", "workstream_id": "red_stream"},
    {"entity_id": "entity_blue", "workstream_id": "blue_stream"},
]
ENTITY_IDS = {entity["entity_id"] for entity in ENTITIES}
ENTITY_SCOPED_FIELDS = {
    "entity_id",
    "workstream_id",
    "inbound_status",
    "continuation_request",
    "continuation_status",
    "open_items",
}
GLOBAL_STATE_FIELDS = {"probe_status"}


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_sustained_probe_for_multi_entity",
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


def entity_inbound_surface(*, entity_id: str, workstream_id: str, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="handle_entity_inbound",
        description="Handle one entity-scoped inbound event.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["entity work accepted"]},
            "entity_id": {"type": "string", "enum": [entity_id]},
            "workstream_id": {"type": "string", "enum": [workstream_id]},
            "inbound_status": {"type": "string"},
            "open_items": PROBE.open_items_schema(),
            "continuation_request": PROBE.continuation_request_schema(),
        },
        required=[
            "response",
            "entity_id",
            "workstream_id",
            "inbound_status",
            "open_items",
            "continuation_request",
        ],
        copy_fields=[
            "entity_id",
            "workstream_id",
            "inbound_status",
            "open_items",
            "continuation_request",
        ],
    )


def entity_continuation_surface(
    *,
    entity_id: str,
    workstream_id: str,
    tool_choice: str,
) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="complete_entity_continuation",
        description="Complete one entity-scoped continuation.",
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["entity continuation complete"],
            },
            "entity_id": {"type": "string", "enum": [entity_id]},
            "workstream_id": {"type": "string", "enum": [workstream_id]},
            "continuation_status": {"type": "string"},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "entity_id",
            "workstream_id",
            "continuation_status",
            "open_items",
        ],
        copy_fields=[
            "entity_id",
            "workstream_id",
            "continuation_status",
            "open_items",
        ],
    )


def identity_audit_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="complete_identity_isolation_audit",
        description="Audit multi-entity isolation and attribution.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["identity audit complete"]},
            "entity_ids": {"type": "array", "items": {"type": "string"}},
            "workstream_ids": {"type": "array", "items": {"type": "string"}},
            "cross_contamination_detected": {"type": "boolean"},
            "attribution_errors": {"type": "array", "items": {"type": "string"}},
            "audit_summary": {"type": "string"},
        },
        required=[
            "response",
            "entity_ids",
            "workstream_ids",
            "cross_contamination_detected",
            "attribution_errors",
            "audit_summary",
        ],
        copy_fields=[
            "entity_ids",
            "workstream_ids",
            "cross_contamination_detected",
            "attribution_errors",
            "audit_summary",
        ],
    )


def final_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_multi_entity_artifact",
        description="Write the final multi-entity artifact.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["multi entity artifact complete"]},
            "artifact_title": {"type": "string"},
            "entity_count": {"type": "integer"},
            "entity_ids": {"type": "array", "items": {"type": "string"}},
            "workstream_ids": {"type": "array", "items": {"type": "string"}},
            "cross_contamination_detected": {"type": "boolean"},
            "attribution_errors": {"type": "array", "items": {"type": "string"}},
            "conclusion": {"type": "string"},
            "declared_losses": {"type": "array", "items": {"type": "string"}},
        },
        required=[
            "response",
            "artifact_title",
            "entity_count",
            "entity_ids",
            "workstream_ids",
            "cross_contamination_detected",
            "attribution_errors",
            "conclusion",
            "declared_losses",
        ],
        copy_fields=[
            "artifact_title",
            "entity_count",
            "entity_ids",
            "workstream_ids",
            "cross_contamination_detected",
            "attribution_errors",
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
    for entity in ENTITIES:
        entity_id = entity["entity_id"]
        workstream_id = entity["workstream_id"]
        outputs.extend(
            [
                {
                    "response": "entity work accepted",
                    "entity_id": entity_id,
                    "workstream_id": workstream_id,
                    "inbound_status": f"{entity_id} accepted",
                    "open_items": [
                        {"kind": "entity_task", "text": f"finish {entity_id}"}
                    ],
                    "continuation_request": {
                        "requested": True,
                        "kind": "entity_bound_continuation",
                        "purpose": f"Finish {entity_id} from <result_record_id>.",
                        "symbolic_context": [
                            {"source": "completed_wake_state", "field": "entity_id"},
                            {
                                "source": "completed_wake_state",
                                "field": "workstream_id",
                            },
                        ],
                        "label": f"finish-{entity_id}",
                    },
                },
                {
                    "response": "entity continuation complete",
                    "entity_id": entity_id,
                    "workstream_id": workstream_id,
                    "continuation_status": f"{entity_id} complete",
                    "open_items": [],
                },
            ]
        )
    outputs.extend(
        [
            {
                "response": "identity audit complete",
                "entity_ids": ["entity_red", "entity_blue"],
                "workstream_ids": ["red_stream", "blue_stream"],
                "cross_contamination_detected": False,
                "attribution_errors": [],
                "audit_summary": "entity identity and workstream attribution preserved",
            },
            {
                "response": "multi entity artifact complete",
                "artifact_title": "Multi-Entity Event Loop Isolation Result",
                "entity_count": 2,
                "entity_ids": ["entity_red", "entity_blue"],
                "workstream_ids": ["red_stream", "blue_stream"],
                "cross_contamination_detected": False,
                "attribution_errors": [],
                "conclusion": "Both entity-scoped workstreams completed without identity drift.",
                "declared_losses": [],
            },
        ]
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
            "entities": ENTITIES,
            "repair_contract": (
                "entity-scoped wake state is restored before each entity event; "
                "first contact starts from clean seed state rather than the "
                "previous entity's default-stable state"
            ),
            "expected_completed_event_count": 6,
            "expected_event_type_sequence": [
                "entity_inbound",
                "entity_continuation",
                "entity_inbound",
                "entity_continuation",
                "identity_isolation_audit",
                "multi_entity_artifact",
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 7 if live_model_calls else 0,
            "max_estimated_cost_usd": 3.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.multi_entity_state_isolation_repair_taxonomy.v1",
            "layers": [
                "entity_state_isolation",
                "identity_drift",
                "context_contamination",
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


def initialize_run(paths: Any, run_id: str, live_model_calls: bool, endpoint: str, model: str, terminal_tool_choice: str):
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


def clone_json(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def clean_seed_state(seed_state: JsonDict) -> JsonDict:
    state = {
        key: clone_json(value)
        for key, value in seed_state.items()
        if key in GLOBAL_STATE_FIELDS
    }
    state["open_items"] = []
    return state


def set_session_state(session: Any, state: JsonDict) -> None:
    session._state = clone_json(state)


def set_entity_wake_state(
    session: Any,
    *,
    entity: JsonDict,
    entity_states: dict[str, JsonDict],
    seed_state: JsonDict,
) -> JsonDict:
    entity_id = entity["entity_id"]
    state = entity_states.get(entity_id, clean_seed_state(seed_state))
    set_session_state(session, state)
    return clone_json(state)


def set_global_wake_state(
    session: Any,
    *,
    seed_state: JsonDict,
    entity_record_ids: dict[str, str],
) -> JsonDict:
    state = clean_seed_state(seed_state)
    state["entity_record_ids"] = dict(sorted(entity_record_ids.items()))
    set_session_state(session, state)
    return clone_json(state)


def remember_entity_state(
    session: Any,
    *,
    entity: JsonDict,
    entity_states: dict[str, JsonDict],
    entity_record_ids: dict[str, str],
) -> None:
    entity_id = entity["entity_id"]
    entity_states[entity_id] = clone_json(session._state)
    entity_record_ids[entity_id] = str(session._prior_states[-1][1])


def foreign_entity_mentions(state: Any, entity_id: str) -> list[str]:
    text = json.dumps(state, sort_keys=True, default=str)
    return sorted(other for other in ENTITY_IDS - {entity_id} if other in text)


def commit_frontier(paths: Any, frontier: Any, memory: Any, ledger: Any, store: Any, session: Any, run_id: str, notes: JsonDict) -> None:
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


def append_entity_inbound(
    store: Any,
    session: Any,
    entity: JsonDict,
    terminal_tool_choice: str,
    *,
    context_record_id: str,
) -> JsonDict:
    entity_id = entity["entity_id"]
    workstream_id = entity["workstream_id"]
    return PROBE.append_probe_event(
        store,
        event_type="entity_inbound",
        label=f"inbound-{entity_id}",
        purpose=(
            f"Handle work for {entity_id} in {workstream_id}. Return response "
            "exactly: entity work accepted. Preserve entity_id and "
            "workstream_id exactly, leave one open item, and request a "
            "framework-bound continuation using symbolic_context."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=entity_inbound_surface(
            entity_id=entity_id,
            workstream_id=workstream_id,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": context_record_id}],
    )


def append_entity_continuation(
    store: Any,
    session: Any,
    entity: JsonDict,
    inbound_record_id: str,
    terminal_tool_choice: str,
) -> JsonDict:
    entity_id = entity["entity_id"]
    workstream_id = entity["workstream_id"]
    return PROBE.append_probe_event(
        store,
        event_type="entity_continuation",
        label=f"continuation-{entity_id}",
        purpose=(
            f"Complete work for {entity_id} in {workstream_id}. Return response "
            "exactly: entity continuation complete. Preserve entity_id and "
            "workstream_id exactly and close open items."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=entity_continuation_surface(
            entity_id=entity_id,
            workstream_id=workstream_id,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": inbound_record_id}],
    )


def append_audit(store: Any, session: Any, continuation_record_ids: list[str], terminal_tool_choice: str) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="identity_isolation_audit",
        label="identity-audit",
        purpose=(
            "Audit entity_red/red_stream and entity_blue/blue_stream for identity "
            "drift, context contamination, and attribution errors. Return "
            "response exactly: identity audit complete."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=identity_audit_surface(tool_choice=terminal_tool_choice),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in continuation_record_ids
        ],
    )


def append_final(store: Any, session: Any, record_ids: list[str], terminal_tool_choice: str) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="multi_entity_artifact",
        label="multi-entity-final",
        purpose=(
            "Write final multi-entity artifact. Report both entities, both "
            "workstreams, no cross-contamination, and no attribution errors. "
            "Return response exactly: multi entity artifact complete."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=final_surface(tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": record_id} for record_id in record_ids],
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


def entity_prior_state_isolation(path: Path) -> JsonDict:
    leaks: list[JsonDict] = []
    observed: list[JsonDict] = []
    for record in read_jsonl(path):
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict):
            continue
        entity_id = raw_output.get("entity_id")
        workstream_id = raw_output.get("workstream_id")
        if entity_id not in ENTITY_IDS:
            continue
        prior_state = record.get("prior_state") or {}
        prior_keys = sorted(prior_state) if isinstance(prior_state, dict) else []
        foreign_mentions = foreign_entity_mentions(prior_state, str(entity_id))
        observed.append(
            {
                "cycle": record.get("cycle"),
                "entity_id": entity_id,
                "workstream_id": workstream_id,
                "prior_state_keys": prior_keys,
                "foreign_entity_mentions": foreign_mentions,
            }
        )
        if foreign_mentions:
            leaks.append(observed[-1])
    return {
        "entity_prior_state_isolated": leaks == [],
        "entity_prior_state_observations": observed,
        "entity_prior_state_leaks": leaks,
    }


def attempted_terminal_tools(path: Path) -> list[str]:
    tools: list[str] = []
    for record in read_jsonl(path):
        if record.get("record_type") != "event_attempt":
            continue
        surface = record.get("terminal_surface")
        if isinstance(surface, dict):
            tools.append(str(surface.get("tool_name")))
    return tools


def material_outcome_warnings(summary: JsonDict) -> list[JsonDict]:
    return [
        warning for warning in summary.get("outcome_warnings", []) or []
        if warning.get("response_state_mismatch") is True
        or warning.get("deleted_load_bearing_field") is True
    ]


def completed_states(records: list[JsonDict], paths: Any) -> list[JsonDict]:
    states = session_state_by_record_id(paths.session_log)
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    return [states.get(str(record.get("result_record_id")), {}) for record in completed]


def entity_identity_checks(states: list[JsonDict]) -> JsonDict:
    entity_states = [
        state for state in states
        if state.get("entity_id") in {"entity_red", "entity_blue"}
    ]
    pairs = [
        [state.get("entity_id"), state.get("workstream_id")]
        for state in entity_states
    ]
    expected = [
        ["entity_red", "red_stream"],
        ["entity_red", "red_stream"],
        ["entity_blue", "blue_stream"],
        ["entity_blue", "blue_stream"],
    ]
    return {
        "entity_event_identity_preserved": pairs[:4] == expected,
        "observed_pairs": pairs,
    }


def required_success(summary: JsonDict, records: list[JsonDict], *, paths: Any) -> JsonDict:
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    completed_tools = attempted_terminal_tools(paths.attempts_log)
    states = completed_states(records, paths)
    final_state = states[-1] if states else {}
    audit_state = next(
        (state for state in states if "audit_summary" in state),
        {},
    )
    identity = entity_identity_checks(states[:4])
    prior_isolation = entity_prior_state_isolation(paths.session_log)
    checks = {
        "completed_six_events": len(completed) == 6,
        "event_type_sequence": completed_types == [
            "entity_inbound",
            "entity_continuation",
            "entity_inbound",
            "entity_continuation",
            "identity_isolation_audit",
            "multi_entity_artifact",
        ],
        "terminal_surface_sequence": completed_tools == [
            "handle_entity_inbound",
            "complete_entity_continuation",
            "handle_entity_inbound",
            "complete_entity_continuation",
            "complete_identity_isolation_audit",
            "write_multi_entity_artifact",
        ],
        "entity_prior_state_isolated": prior_isolation["entity_prior_state_isolated"],
        "entity_event_identity_preserved": identity["entity_event_identity_preserved"],
        "audit_no_contamination": audit_state.get("cross_contamination_detected") is False,
        "audit_no_attribution_errors": audit_state.get("attribution_errors") == [],
        "final_entity_count": final_state.get("entity_count") == 2,
        "final_entities": final_state.get("entity_ids") == ["entity_red", "entity_blue"],
        "final_workstreams": final_state.get("workstream_ids") == ["red_stream", "blue_stream"],
        "final_no_contamination": final_state.get("cross_contamination_detected") is False,
        "final_no_attribution_errors": final_state.get("attribution_errors") == [],
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
        "observed_entity_pairs": identity["observed_pairs"],
        "entity_prior_state_observations": prior_isolation[
            "entity_prior_state_observations"
        ],
        "entity_prior_state_leaks": prior_isolation["entity_prior_state_leaks"],
        "audit_state": audit_state,
        "final_state": final_state,
        "frontier_line_count": 0,
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
    if paths.frontier_log.exists():
        success["frontier_line_count"] = len(
            [line for line in paths.frontier_log.read_text().splitlines() if line.strip()]
        )
        success["checks"]["multiple_frontier_updates"] = success["frontier_line_count"] >= 7
    else:
        success["checks"]["multiple_frontier_updates"] = False
    failures = PROBE.collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.multi_entity_event_loop.v1",
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
    terminal_tool_choice = terminal_tool_choice or PROBE.default_terminal_tool_choice(endpoint)
    if backend is None:
        if live_model_calls:
            backend = PROBE.make_live_backend(endpoint=endpoint, api_key=api_key or "", max_tokens=max_tokens)
        else:
            backend = PROBE.ScriptedTerminalBackend(scripted_outputs())

    store, memory, ledger, frontier = initialize_run(paths, run_id, live_model_calls, endpoint, model, terminal_tool_choice)
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    seed_request = {
        "event": "initialize_multi_entity_loop",
        "instruction": "Initialize durable state for a multi-entity event-loop probe.",
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
        PROBE.record_failure(paths, PROBE.classify_exception(exc, stage="seed_exchange"), request=seed_request)
        return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": "seed_exchange"})
    seed_state = clone_json(session._state or {})
    seed_record_id = str(session._prior_states[-1][1])
    entity_states: dict[str, JsonDict] = {}
    entity_record_ids: dict[str, str] = {}
    commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after seed"})

    continuation_record_ids: list[str] = []
    for entity in ENTITIES:
        context_record_id = entity_record_ids.get(entity["entity_id"], seed_record_id)
        set_entity_wake_state(
            session,
            entity=entity,
            entity_states=entity_states,
            seed_state=seed_state,
        )
        append_entity_inbound(
            store,
            session,
            entity,
            terminal_tool_choice,
            context_record_id=context_record_id,
        )
        inbound = PROBE.run_attributed_event(
            session=session,
            store=store,
            paths=paths,
            auto_continuations=False,
            terminal_tool_choice=terminal_tool_choice,
        )
        if inbound.get("status") != "completed":
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"inbound_{entity['entity_id']}"})
        raw = inbound.get("raw_output")
        if not isinstance(raw, dict) or not isinstance(raw.get("continuation_request"), dict):
            PROBE.record_failure(paths, PROBE.model_output_failure(code="missing_entity_continuation_request", stage="entity_inbound", message="entity inbound did not include continuation_request"), result=inbound)
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"continuation_request_{entity['entity_id']}"})
        remember_entity_state(
            session,
            entity=entity,
            entity_states=entity_states,
            entity_record_ids=entity_record_ids,
        )
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after inbound {entity['entity_id']}"})

        set_entity_wake_state(
            session,
            entity=entity,
            entity_states=entity_states,
            seed_state=seed_state,
        )
        append_entity_continuation(
            store,
            session,
            entity,
            str(inbound["result_record_id"]),
            terminal_tool_choice,
        )
        continuation = PROBE.run_attributed_event(
            session=session,
            store=store,
            paths=paths,
            auto_continuations=False,
            terminal_tool_choice=terminal_tool_choice,
        )
        if continuation.get("status") != "completed":
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"continuation_{entity['entity_id']}"})
        remember_entity_state(
            session,
            entity=entity,
            entity_states=entity_states,
            entity_record_ids=entity_record_ids,
        )
        continuation_record_ids.append(str(continuation["result_record_id"]))
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after continuation {entity['entity_id']}"})

    set_global_wake_state(
        session,
        seed_state=seed_state,
        entity_record_ids=entity_record_ids,
    )
    append_audit(store, session, continuation_record_ids, terminal_tool_choice)
    audit = PROBE.run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if audit.get("status") != "completed":
        return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": "identity_audit"})
    commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after identity audit"})

    set_global_wake_state(
        session,
        seed_state=seed_state,
        entity_record_ids=entity_record_ids,
    )
    append_final(store, session, [*continuation_record_ids, str(audit["result_record_id"])], terminal_tool_choice)
    final = PROBE.run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final.get("status") == "completed":
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after final artifact"})
    return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store)


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
