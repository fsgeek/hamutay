"""Phase 2A larger multi-entity sustained loop probe."""

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

EXPERIMENT_ID = "phase_2a_larger_multi_entity_loop_20260618"
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
ROUNDS = [1, 2]
ENTITIES = [
    {"entity_id": "entity_red", "workstream_id": "red_stream"},
    {"entity_id": "entity_blue", "workstream_id": "blue_stream"},
    {"entity_id": "entity_green", "workstream_id": "green_stream"},
]
ENTITY_IDS = {entity["entity_id"] for entity in ENTITIES}
ENTITY_ID_TO_WORKSTREAM = {
    entity["entity_id"]: entity["workstream_id"] for entity in ENTITIES
}
GLOBAL_STATE_FIELDS = {"probe_status"}
SCHEDULER_OWNED_FIELDS = {
    "event_id",
    "record_id",
    "run_id",
    "scheduled_by_record_id",
    "scheduled_by_cycle",
    "created_by_record_epoch",
    "scheduled_by_record_epoch",
    "record_uniquifier",
}


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_sustained_probe_for_phase_2a_larger_multi_entity",
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


def entity_inbound_surface(
    *,
    entity_id: str,
    workstream_id: str,
    tool_choice: str,
) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="handle_phase_2a_entity_inbound",
        description="Handle one entity-scoped inbound event.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["entity work accepted"]},
            "entity_id": {"type": "string", "enum": [entity_id]},
            "workstream_id": {"type": "string", "enum": [workstream_id]},
            "round_index": {"type": "integer"},
            "inbound_status": {"type": "string"},
            "open_items": PROBE.open_items_schema(),
            "continuation_request": PROBE.continuation_request_schema(),
        },
        required=[
            "response",
            "entity_id",
            "workstream_id",
            "round_index",
            "inbound_status",
            "open_items",
            "continuation_request",
        ],
        copy_fields=[
            "entity_id",
            "workstream_id",
            "round_index",
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
        tool_name="complete_phase_2a_entity_continuation",
        description="Complete one entity-scoped continuation.",
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["entity continuation complete"],
            },
            "entity_id": {"type": "string", "enum": [entity_id]},
            "workstream_id": {"type": "string", "enum": [workstream_id]},
            "round_index": {"type": "integer"},
            "continuation_status": {"type": "string"},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "entity_id",
            "workstream_id",
            "round_index",
            "continuation_status",
            "open_items",
        ],
        copy_fields=[
            "entity_id",
            "workstream_id",
            "round_index",
            "continuation_status",
            "open_items",
        ],
    )


def housekeeping_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="complete_phase_2a_housekeeping",
        description="Audit the larger multi-entity loop after an interleaved phase.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["scale housekeeping clean"]},
            "entity_ids": {"type": "array", "items": {"type": "string"}},
            "workstream_ids": {"type": "array", "items": {"type": "string"}},
            "completed_entity_events": {"type": "integer"},
            "cross_contamination_detected": {"type": "boolean"},
            "attribution_errors": {"type": "array", "items": {"type": "string"}},
            "housekeeping_summary": {"type": "string"},
        },
        required=[
            "response",
            "entity_ids",
            "workstream_ids",
            "completed_entity_events",
            "cross_contamination_detected",
            "attribution_errors",
            "housekeeping_summary",
        ],
        copy_fields=[
            "entity_ids",
            "workstream_ids",
            "completed_entity_events",
            "cross_contamination_detected",
            "attribution_errors",
            "housekeeping_summary",
        ],
    )


def final_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_phase_2a_scale_artifact",
        description="Write the final larger multi-entity sustained-loop artifact.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["scale artifact complete"]},
            "artifact_title": {"type": "string"},
            "entity_count": {"type": "integer"},
            "entity_ids": {"type": "array", "items": {"type": "string"}},
            "workstream_ids": {"type": "array", "items": {"type": "string"}},
            "round_count": {"type": "integer"},
            "completed_entity_events": {"type": "integer"},
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
            "round_count",
            "completed_entity_events",
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
            "round_count",
            "completed_entity_events",
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
    for round_index in ROUNDS:
        for entity in ENTITIES:
            entity_id = entity["entity_id"]
            workstream_id = entity["workstream_id"]
            outputs.append(
                {
                    "response": "entity work accepted",
                    "entity_id": entity_id,
                    "workstream_id": workstream_id,
                    "round_index": round_index,
                    "inbound_status": f"{entity_id} round {round_index} accepted",
                    "open_items": [
                        {
                            "kind": "entity_task",
                            "text": f"finish {entity_id} round {round_index}",
                        }
                    ],
                    "continuation_request": {
                        "requested": True,
                        "kind": "entity_bound_continuation",
                        "purpose": f"Finish {entity_id} round {round_index}.",
                        "symbolic_context": [
                            {"source": "completed_wake_state", "field": "entity_id"},
                            {"source": "completed_wake_state", "field": "workstream_id"},
                            {"source": "completed_wake_state", "field": "round_index"},
                        ],
                        "label": f"finish-{entity_id}-round-{round_index}",
                    },
                }
            )
        for entity in ENTITIES:
            entity_id = entity["entity_id"]
            workstream_id = entity["workstream_id"]
            outputs.append(
                {
                    "response": "entity continuation complete",
                    "entity_id": entity_id,
                    "workstream_id": workstream_id,
                    "round_index": round_index,
                    "continuation_status": f"{entity_id} round {round_index} complete",
                    "open_items": [],
                }
            )
        outputs.append(
            {
                "response": "scale housekeeping clean",
                "entity_ids": sorted(ENTITY_IDS),
                "workstream_ids": sorted(ENTITY_ID_TO_WORKSTREAM.values()),
                "completed_entity_events": round_index * len(ENTITIES) * 2,
                "cross_contamination_detected": False,
                "attribution_errors": [],
                "housekeeping_summary": f"round {round_index} interleaving clean",
            }
        )
    outputs.append(
        {
            "response": "scale artifact complete",
            "artifact_title": "Phase 2A Larger Multi-Entity Sustained Loop",
            "entity_count": len(ENTITIES),
            "entity_ids": sorted(ENTITY_IDS),
            "workstream_ids": sorted(ENTITY_ID_TO_WORKSTREAM.values()),
            "round_count": len(ROUNDS),
            "completed_entity_events": len(ROUNDS) * len(ENTITIES) * 2,
            "cross_contamination_detected": False,
            "attribution_errors": [],
            "conclusion": "All interleaved entity work completed cleanly.",
            "declared_losses": [],
        }
    )
    return outputs


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    expected_sequence: list[str] = []
    for _round_index in ROUNDS:
        expected_sequence.extend(["entity_inbound"] * len(ENTITIES))
        expected_sequence.extend(["entity_continuation"] * len(ENTITIES))
        expected_sequence.append("scale_housekeeping")
    expected_sequence.append("scale_final_artifact")
    artifacts = {
        "matrix.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "entities": ENTITIES,
            "rounds": ROUNDS,
            "expected_completed_event_count": len(expected_sequence),
            "expected_event_type_sequence": expected_sequence,
            "memory_substrate": "local_artifacts_only",
            "yanantin_enabled": False,
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 1 + len(expected_sequence) if live_model_calls else 0,
            "max_estimated_cost_usd": 6.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_2a_larger_multi_entity_taxonomy.v1",
            "layers": [
                "state_isolation",
                "identity",
                "interleaving",
                "housekeeping",
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
            "yanantin_enabled": False,
        },
        sandbox={"network": "enabled" if live_model_calls else "disabled"},
    )
    return store, memory, ledger, frontier


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
) -> None:
    entity_id = entity["entity_id"]
    set_session_state(session, entity_states.get(entity_id, clean_seed_state(seed_state)))


def set_global_wake_state(
    session: Any,
    *,
    seed_state: JsonDict,
    entity_record_ids: dict[str, str],
    completed_entity_events: int,
) -> None:
    state = clean_seed_state(seed_state)
    state["entity_record_ids"] = dict(sorted(entity_record_ids.items()))
    state["completed_entity_events"] = completed_entity_events
    state["entity_ids"] = sorted(ENTITY_IDS)
    state["workstream_ids"] = sorted(ENTITY_ID_TO_WORKSTREAM.values())
    set_session_state(session, state)


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


def append_entity_inbound(
    store: Any,
    session: Any,
    entity: JsonDict,
    round_index: int,
    terminal_tool_choice: str,
    *,
    context_record_id: str,
) -> JsonDict:
    entity_id = entity["entity_id"]
    workstream_id = entity["workstream_id"]
    return PROBE.append_probe_event(
        store,
        event_type="entity_inbound",
        label=f"inbound-{entity_id}-round-{round_index}",
        purpose=(
            f"Handle round {round_index} work for {entity_id} in "
            f"{workstream_id}. Return response exactly: entity work accepted. "
            "Preserve entity_id, workstream_id, and round_index exactly; leave "
            "one open item; request a framework-bound continuation."
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
    round_index: int,
    inbound_record_id: str,
    terminal_tool_choice: str,
) -> JsonDict:
    entity_id = entity["entity_id"]
    workstream_id = entity["workstream_id"]
    return PROBE.append_probe_event(
        store,
        event_type="entity_continuation",
        label=f"continuation-{entity_id}-round-{round_index}",
        purpose=(
            f"Complete round {round_index} work for {entity_id} in "
            f"{workstream_id}. Return response exactly: entity continuation "
            "complete. Preserve entity_id, workstream_id, and round_index "
            "exactly; close open items."
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


def append_housekeeping(
    store: Any,
    session: Any,
    round_index: int,
    record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="scale_housekeeping",
        label=f"housekeeping-round-{round_index}",
        purpose=(
            f"Audit interleaved larger multi-entity loop after round {round_index}. "
            "Return response exactly: scale housekeeping clean. Report all "
            "entities and no contamination or attribution errors."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=housekeeping_surface(tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": record_id} for record_id in record_ids],
    )


def append_final(
    store: Any,
    session: Any,
    record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="scale_final_artifact",
        label="phase-2a-scale-final",
        purpose=(
            "Write final artifact for the larger multi-entity sustained loop. "
            "Return response exactly: scale artifact complete. Report three "
            "entities, two rounds, twelve completed entity events, no "
            "cross-contamination, and no attribution errors."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=final_surface(tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": record_id} for record_id in record_ids],
    )


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


def completed_states(records: list[JsonDict], paths: Any) -> list[JsonDict]:
    states = session_state_by_record_id(paths.session_log)
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    return [states.get(str(record.get("result_record_id")), {}) for record in completed]


def entity_prior_state_isolation(path: Path) -> JsonDict:
    observations: list[JsonDict] = []
    leaks: list[JsonDict] = []
    for record in read_jsonl(path):
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict):
            continue
        entity_id = raw_output.get("entity_id")
        if entity_id not in ENTITY_IDS:
            continue
        prior_state = record.get("prior_state") or {}
        text = json.dumps(prior_state, sort_keys=True, default=str)
        foreign = sorted(other for other in ENTITY_IDS - {str(entity_id)} if other in text)
        observation = {
            "cycle": record.get("cycle"),
            "entity_id": entity_id,
            "workstream_id": raw_output.get("workstream_id"),
            "round_index": raw_output.get("round_index"),
            "prior_state_keys": sorted(prior_state) if isinstance(prior_state, dict) else [],
            "foreign_entity_mentions": foreign,
        }
        observations.append(observation)
        if foreign:
            leaks.append(observation)
    return {
        "entity_prior_state_isolated": leaks == [] and len(observations) == 12,
        "entity_prior_state_observations": observations,
        "entity_prior_state_leaks": leaks,
    }


def scheduler_owned_field_violations(path: Path) -> list[JsonDict]:
    violations: list[JsonDict] = []
    for record in read_jsonl(path):
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict):
            continue
        authored = sorted(SCHEDULER_OWNED_FIELDS & set(raw_output))
        if authored:
            violations.append(
                {
                    "cycle": record.get("cycle"),
                    "record_id": record.get("record_id"),
                    "authored_scheduler_fields": authored,
                }
            )
    return violations


def expected_event_type_sequence() -> list[str]:
    sequence: list[str] = []
    for _round_index in ROUNDS:
        sequence.extend(["entity_inbound"] * len(ENTITIES))
        sequence.extend(["entity_continuation"] * len(ENTITIES))
        sequence.append("scale_housekeeping")
    sequence.append("scale_final_artifact")
    return sequence


def expected_identity_sequence() -> list[list[Any]]:
    sequence: list[list[Any]] = []
    for round_index in ROUNDS:
        for entity in ENTITIES:
            sequence.append([entity["entity_id"], entity["workstream_id"], round_index])
        for entity in ENTITIES:
            sequence.append([entity["entity_id"], entity["workstream_id"], round_index])
    return sequence


def required_success(summary: JsonDict, records: list[JsonDict], *, paths: Any) -> JsonDict:
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    states = completed_states(records, paths)
    entity_states = [
        state for state in states
        if state.get("entity_id") in ENTITY_IDS
    ]
    observed_identity_sequence = [
        [state.get("entity_id"), state.get("workstream_id"), state.get("round_index")]
        for state in entity_states
    ]
    housekeeping_states = [state for state in states if "housekeeping_summary" in state]
    final_state = states[-1] if states else {}
    prior_isolation = entity_prior_state_isolation(paths.session_log)
    scheduler_violations = scheduler_owned_field_violations(paths.session_log)
    frontier_line_count = (
        len([line for line in paths.frontier_log.read_text().splitlines() if line.strip()])
        if paths.frontier_log.exists()
        else 0
    )
    checks = {
        "completed_expected_events": completed_types == expected_event_type_sequence(),
        "interleaved_identity_sequence": observed_identity_sequence == expected_identity_sequence(),
        "entity_prior_state_isolated": prior_isolation["entity_prior_state_isolated"],
        "housekeeping_count": len(housekeeping_states) == len(ROUNDS),
        "housekeeping_clean": all(
            state.get("cross_contamination_detected") is False
            and state.get("attribution_errors") == []
            for state in housekeeping_states
        ),
        "final_entity_count": final_state.get("entity_count") == len(ENTITIES),
        "final_round_count": final_state.get("round_count") == len(ROUNDS),
        "final_completed_entity_events": final_state.get("completed_entity_events")
        == len(ROUNDS) * len(ENTITIES) * 2,
        "final_entities": final_state.get("entity_ids") == sorted(ENTITY_IDS),
        "final_workstreams": final_state.get("workstream_ids")
        == sorted(ENTITY_ID_TO_WORKSTREAM.values()),
        "final_clean": final_state.get("cross_contamination_detected") is False
        and final_state.get("attribution_errors") == [],
        "scheduler_owned_fields_not_model_authored": scheduler_violations == [],
        "local_artifacts_only": True,
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
        "multiple_frontier_updates": frontier_line_count >= 1 + len(expected_event_type_sequence()),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "observed_identity_sequence": observed_identity_sequence,
        "entity_prior_state_observations": prior_isolation["entity_prior_state_observations"],
        "entity_prior_state_leaks": prior_isolation["entity_prior_state_leaks"],
        "scheduler_owned_field_violations": scheduler_violations,
        "housekeeping_states": housekeeping_states,
        "final_state": final_state,
        "frontier_line_count": frontier_line_count,
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
    failures = PROBE.collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.phase_2a_larger_multi_entity_loop.v1",
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
    terminal_tool_choice = terminal_tool_choice or PROBE.default_terminal_tool_choice(endpoint)
    if backend is None:
        if live_model_calls:
            backend = PROBE.make_live_backend(endpoint=endpoint, api_key=api_key or "", max_tokens=max_tokens)
        else:
            backend = PROBE.ScriptedTerminalBackend(scripted_outputs())

    store, memory, ledger, frontier = initialize_run(paths, run_id, live_model_calls, endpoint, model, terminal_tool_choice)
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    try:
        session.exchange(
            json.dumps(
                {
                    "event": "initialize_phase_2a_larger_multi_entity_loop",
                    "instruction": "Initialize durable state for a larger multi-entity event-loop probe.",
                    "required_output": {
                        "response": "<brief initialization note>",
                        "probe_status": "ready",
                        "open_items": [],
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            terminal_surface=PROBE.seed_terminal_surface(tool_choice=terminal_tool_choice),
            force_memory=None,
        )
    except Exception as exc:
        PROBE.record_failure(paths, PROBE.classify_exception(exc, stage="seed_exchange"))
        return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": "seed_exchange"})
    seed_state = clone_json(session._state or {})
    seed_record_id = str(session._prior_states[-1][1])
    entity_states: dict[str, JsonDict] = {}
    entity_record_ids: dict[str, str] = {}
    all_entity_record_ids: list[str] = []
    all_shared_record_ids: list[str] = []
    commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after seed"})

    for round_index in ROUNDS:
        inbound_results: dict[str, JsonDict] = {}
        for entity in ENTITIES:
            context_record_id = entity_record_ids.get(entity["entity_id"], seed_record_id)
            set_entity_wake_state(session, entity=entity, entity_states=entity_states, seed_state=seed_state)
            append_entity_inbound(
                store,
                session,
                entity,
                round_index,
                terminal_tool_choice,
                context_record_id=context_record_id,
            )
            inbound = run_one_event(
                session=session,
                store=store,
                paths=paths,
                terminal_tool_choice=terminal_tool_choice,
            )
            if inbound.get("status") != "completed":
                return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"inbound_{entity['entity_id']}_round_{round_index}"})
            raw = inbound.get("raw_output")
            if not isinstance(raw, dict) or not isinstance(raw.get("continuation_request"), dict):
                PROBE.record_failure(paths, PROBE.model_output_failure(code="missing_entity_continuation_request", stage="entity_inbound", message="entity inbound did not include continuation_request"), result=inbound)
                return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"continuation_request_{entity['entity_id']}_round_{round_index}"})
            remember_entity_state(session, entity=entity, entity_states=entity_states, entity_record_ids=entity_record_ids)
            inbound_results[entity["entity_id"]] = inbound
            all_entity_record_ids.append(str(inbound["result_record_id"]))
            commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after inbound {entity['entity_id']} round {round_index}"})

        for entity in ENTITIES:
            set_entity_wake_state(session, entity=entity, entity_states=entity_states, seed_state=seed_state)
            append_entity_continuation(
                store,
                session,
                entity,
                round_index,
                str(inbound_results[entity["entity_id"]]["result_record_id"]),
                terminal_tool_choice,
            )
            continuation = run_one_event(
                session=session,
                store=store,
                paths=paths,
                terminal_tool_choice=terminal_tool_choice,
            )
            if continuation.get("status") != "completed":
                return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"continuation_{entity['entity_id']}_round_{round_index}"})
            remember_entity_state(session, entity=entity, entity_states=entity_states, entity_record_ids=entity_record_ids)
            all_entity_record_ids.append(str(continuation["result_record_id"]))
            commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after continuation {entity['entity_id']} round {round_index}"})

        set_global_wake_state(
            session,
            seed_state=seed_state,
            entity_record_ids=entity_record_ids,
            completed_entity_events=len(all_entity_record_ids),
        )
        append_housekeeping(
            store,
            session,
            round_index,
            list(entity_record_ids.values()),
            terminal_tool_choice,
        )
        housekeeping = run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if housekeeping.get("status") != "completed":
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"housekeeping_round_{round_index}"})
        all_shared_record_ids.append(str(housekeeping["result_record_id"]))
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after housekeeping round {round_index}"})

    set_global_wake_state(
        session,
        seed_state=seed_state,
        entity_record_ids=entity_record_ids,
        completed_entity_events=len(all_entity_record_ids),
    )
    append_final(
        store,
        session,
        [*all_entity_record_ids, *all_shared_record_ids],
        terminal_tool_choice,
    )
    final = run_one_event(
        session=session,
        store=store,
        paths=paths,
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
    print(json.dumps({"classification": result["classification"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
