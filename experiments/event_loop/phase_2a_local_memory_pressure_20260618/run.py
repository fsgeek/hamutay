"""Phase 2A local memory pressure probe."""

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

EXPERIMENT_ID = "phase_2a_local_memory_pressure_20260618"
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
    {
        "entity_id": "entity_red",
        "workstream_id": "red_stream",
        "commitment_code": "red-commitment-alpha",
    },
    {
        "entity_id": "entity_blue",
        "workstream_id": "blue_stream",
        "commitment_code": "blue-commitment-beta",
    },
    {
        "entity_id": "entity_green",
        "workstream_id": "green_stream",
        "commitment_code": "green-commitment-gamma",
    },
]
ENTITY_IDS = {entity["entity_id"] for entity in ENTITIES}
EXPECTED_CODES = sorted(entity["commitment_code"] for entity in ENTITIES)


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_sustained_probe_for_local_memory_pressure",
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


def commitment_surface(*, entity: JsonDict, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="record_local_commitment",
        description="Record one entity commitment for later local recall.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["entity commitment recorded"]},
            "entity_id": {"type": "string", "enum": [entity["entity_id"]]},
            "workstream_id": {"type": "string", "enum": [entity["workstream_id"]]},
            "commitment_code": {"type": "string", "enum": [entity["commitment_code"]]},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "entity_id",
            "workstream_id",
            "commitment_code",
            "open_items",
        ],
        copy_fields=[
            "entity_id",
            "workstream_id",
            "commitment_code",
            "open_items",
        ],
    )


def recall_surface(
    *,
    entity: JsonDict,
    source_record_id: str,
    tool_choice: str,
) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="recall_local_commitment",
        description="Recall one commitment from explicit local requested context.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["entity memory recalled"]},
            "entity_id": {"type": "string", "enum": [entity["entity_id"]]},
            "workstream_id": {"type": "string", "enum": [entity["workstream_id"]]},
            "recalled_commitment_code": {
                "type": "string",
                "enum": [entity["commitment_code"]],
            },
            "source_record_id": {"type": "string", "enum": [source_record_id]},
            "recall_summary": {"type": "string"},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "entity_id",
            "workstream_id",
            "recalled_commitment_code",
            "source_record_id",
            "recall_summary",
            "open_items",
        ],
        copy_fields=[
            "entity_id",
            "workstream_id",
            "recalled_commitment_code",
            "source_record_id",
            "recall_summary",
            "open_items",
        ],
    )


def housekeeping_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="audit_local_memory_pressure",
        description="Audit local recall records for provenance and unresolved items.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["local memory audit clean"]},
            "entity_ids": {"type": "array", "items": {"type": "string"}},
            "recalled_commitment_codes": {"type": "array", "items": {"type": "string"}},
            "recall_records_checked": {"type": "integer"},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "attribution_errors": {"type": "array", "items": {"type": "string"}},
            "audit_summary": {"type": "string"},
        },
        required=[
            "response",
            "entity_ids",
            "recalled_commitment_codes",
            "recall_records_checked",
            "unsupported_claims",
            "attribution_errors",
            "audit_summary",
        ],
        copy_fields=[
            "entity_ids",
            "recalled_commitment_codes",
            "recall_records_checked",
            "unsupported_claims",
            "attribution_errors",
            "audit_summary",
        ],
    )


def final_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_local_memory_pressure_artifact",
        description="Write the final local memory pressure artifact.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["local memory artifact complete"]},
            "artifact_title": {"type": "string"},
            "entity_count": {"type": "integer"},
            "recalled_commitment_codes": {"type": "array", "items": {"type": "string"}},
            "provenance_record_ids": {"type": "array", "items": {"type": "string"}},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "attribution_errors": {"type": "array", "items": {"type": "string"}},
            "conclusion": {"type": "string"},
            "declared_losses": {"type": "array", "items": {"type": "string"}},
        },
        required=[
            "response",
            "artifact_title",
            "entity_count",
            "recalled_commitment_codes",
            "provenance_record_ids",
            "unsupported_claims",
            "attribution_errors",
            "conclusion",
            "declared_losses",
        ],
        copy_fields=[
            "artifact_title",
            "entity_count",
            "recalled_commitment_codes",
            "provenance_record_ids",
            "unsupported_claims",
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
        outputs.append(
            {
                "response": "entity commitment recorded",
                "entity_id": entity["entity_id"],
                "workstream_id": entity["workstream_id"],
                "commitment_code": entity["commitment_code"],
                "open_items": [{"kind": "commitment", "text": entity["commitment_code"]}],
            }
        )
    for entity in ENTITIES:
        outputs.append(
            {
                "response": "entity memory recalled",
                "entity_id": entity["entity_id"],
                "workstream_id": entity["workstream_id"],
                "recalled_commitment_code": entity["commitment_code"],
                "source_record_id": "<patched-by-backend-contract>",
                "recall_summary": f"recalled {entity['commitment_code']}",
                "open_items": [],
            }
        )
    outputs.extend(
        [
            {
                "response": "local memory audit clean",
                "entity_ids": sorted(ENTITY_IDS),
                "recalled_commitment_codes": EXPECTED_CODES,
                "recall_records_checked": len(ENTITIES),
                "unsupported_claims": [],
                "attribution_errors": [],
                "audit_summary": "local recall records are complete and attributed",
            },
            {
                "response": "local memory artifact complete",
                "artifact_title": "Phase 2A Local Memory Pressure Result",
                "entity_count": len(ENTITIES),
                "recalled_commitment_codes": EXPECTED_CODES,
                "provenance_record_ids": [],
                "unsupported_claims": [],
                "attribution_errors": [],
                "conclusion": "Local requested-context recall recovered all commitments.",
                "declared_losses": [],
            },
        ]
    )
    return outputs


class PatchedScriptedBackend(PROBE.ScriptedTerminalBackend):
    def __init__(self, outputs: list[JsonDict | Exception]):
        super().__init__(outputs)
        self.source_record_ids: list[str] = []

    def call_terminal_surface(self, *args: Any, **kwargs: Any) -> Any:
        result = super().call_terminal_surface(*args, **kwargs)
        raw_output = result.raw_output
        surface = kwargs.get("terminal_surface")
        if isinstance(surface, dict) and surface.get("tool_name") == "recall_local_commitment":
            enum = (
                surface.get("input_schema", {})
                .get("properties", {})
                .get("source_record_id", {})
                .get("enum", [])
            )
            if enum:
                raw_output["source_record_id"] = enum[0]
                self.source_record_ids.append(str(enum[0]))
        if isinstance(surface, dict) and surface.get("tool_name") == "write_local_memory_pressure_artifact":
            raw_output["provenance_record_ids"] = sorted(self.source_record_ids)
        return result


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
            "memory_substrate": "local_requested_context_only",
            "yanantin_enabled": False,
            "expected_event_type_sequence": [
                "local_commitment",
                "local_commitment",
                "local_commitment",
                "local_recall",
                "local_recall",
                "local_recall",
                "local_memory_housekeeping",
                "local_memory_final",
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 9 if live_model_calls else 0,
            "max_estimated_cost_usd": 4.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_2a_local_memory_pressure_taxonomy.v1",
            "layers": [
                "local_recall",
                "provenance",
                "state_isolation",
                "housekeeping",
                "scheduler",
                "model_output",
                "provider",
                "artifact",
                "yanantin_gate",
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


def set_clean_entity_state(session: Any, seed_state: JsonDict, entity: JsonDict) -> None:
    session._state = {
        "probe_status": seed_state.get("probe_status", "ready"),
        "entity_id": entity["entity_id"],
        "workstream_id": entity["workstream_id"],
        "open_items": [],
    }


def append_commitment(
    store: Any,
    session: Any,
    entity: JsonDict,
    terminal_tool_choice: str,
    context_record_id: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="local_commitment",
        label=f"commitment-{entity['entity_id']}",
        purpose=(
            f"Record commitment {entity['commitment_code']} for {entity['entity_id']}. "
            "Return response exactly: entity commitment recorded."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=commitment_surface(entity=entity, tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": context_record_id}],
    )


def append_recall(
    store: Any,
    session: Any,
    entity: JsonDict,
    commitment_record_id: str,
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="local_recall",
        label=f"recall-{entity['entity_id']}",
        purpose=(
            f"Recall {entity['entity_id']}'s commitment from explicit local "
            "requested context. The commitment is intentionally absent from the "
            "current wake state. Return response exactly: entity memory recalled."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=recall_surface(
            entity=entity,
            source_record_id=commitment_record_id,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": commitment_record_id}],
    )


def append_housekeeping(
    store: Any,
    session: Any,
    recall_record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="local_memory_housekeeping",
        label="local-memory-housekeeping",
        purpose=(
            "Audit recalled local commitment records for provenance. Return "
            "response exactly: local memory audit clean."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=housekeeping_surface(tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": record_id} for record_id in recall_record_ids],
    )


def append_final(
    store: Any,
    session: Any,
    record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="local_memory_final",
        label="local-memory-final",
        purpose=(
            "Write final local memory pressure artifact. Return response exactly: "
            "local memory artifact complete. Cite all source_record_id values "
            "from recalled commitments in provenance_record_ids."
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


def completed_states(records: list[JsonDict], paths: Any) -> list[JsonDict]:
    states = session_state_by_record_id(paths.session_log)
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    return [states.get(str(record.get("result_record_id")), {}) for record in completed]


def recall_prior_observations(path: Path) -> JsonDict:
    observations: list[JsonDict] = []
    leaks: list[JsonDict] = []
    for record in read_jsonl(path):
        raw_output = record.get("raw_output")
        if not isinstance(raw_output, dict) or "recalled_commitment_code" not in raw_output:
            continue
        prior_state = record.get("prior_state") or {}
        code = raw_output.get("recalled_commitment_code")
        leaked = code in json.dumps(prior_state, sort_keys=True, default=str)
        observation = {
            "cycle": record.get("cycle"),
            "entity_id": raw_output.get("entity_id"),
            "source_record_id": raw_output.get("source_record_id"),
            "recalled_commitment_code": code,
            "commitment_absent_from_prior_state": not leaked,
        }
        observations.append(observation)
        if leaked:
            leaks.append(observation)
    return {
        "recall_prior_observations": observations,
        "recall_prior_leaks": leaks,
        "recall_required_local_context": leaks == [] and len(observations) == len(ENTITIES),
    }


def required_success(summary: JsonDict, records: list[JsonDict], *, paths: Any) -> JsonDict:
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    states = completed_states(records, paths)
    recall_states = [state for state in states if "recalled_commitment_code" in state]
    housekeeping_state = next((state for state in states if "audit_summary" in state), {})
    final_state = states[-1] if states else {}
    expected_source_ids = sorted(state.get("source_record_id") for state in recall_states)
    prior_recall = recall_prior_observations(paths.session_log)
    checks = {
        "completed_expected_events": completed_types == [
            "local_commitment",
            "local_commitment",
            "local_commitment",
            "local_recall",
            "local_recall",
            "local_recall",
            "local_memory_housekeeping",
            "local_memory_final",
        ],
        "recall_required_local_context": prior_recall["recall_required_local_context"],
        "recall_codes_correct": sorted(
            state.get("recalled_commitment_code") for state in recall_states
        ) == EXPECTED_CODES,
        "recall_source_records_present": len(expected_source_ids) == len(ENTITIES)
        and all(expected_source_ids),
        "housekeeping_checked_recall_records": housekeeping_state.get(
            "recall_records_checked"
        ) == len(ENTITIES),
        "housekeeping_clean": housekeeping_state.get("unsupported_claims") == []
        and housekeeping_state.get("attribution_errors") == [],
        "final_entity_count": final_state.get("entity_count") == len(ENTITIES),
        "final_codes": sorted(final_state.get("recalled_commitment_codes") or [])
        == EXPECTED_CODES,
        "final_provenance_records": sorted(final_state.get("provenance_record_ids") or [])
        == expected_source_ids,
        "final_clean": final_state.get("unsupported_claims") == []
        and final_state.get("attribution_errors") == [],
        "yanantin_gate_remains_closed": True,
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "recall_states": recall_states,
        "housekeeping_state": housekeeping_state,
        "final_state": final_state,
        "expected_source_record_ids": expected_source_ids,
        **prior_recall,
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
        "schema_version": "hamutay.phase_2a_local_memory_pressure.v1",
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
            backend = PatchedScriptedBackend(scripted_outputs())

    store, memory, ledger, frontier = initialize_run(paths, run_id, live_model_calls, endpoint, model, terminal_tool_choice)
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    try:
        session.exchange(
            json.dumps(
                {
                    "event": "initialize_local_memory_pressure_probe",
                    "instruction": "Initialize durable state for a local memory pressure probe.",
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
    commitment_record_ids: dict[str, str] = {}
    recall_record_ids: list[str] = []
    commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after seed"})

    for entity in ENTITIES:
        set_clean_entity_state(session, seed_state, entity)
        append_commitment(store, session, entity, terminal_tool_choice, seed_record_id)
        result = run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if result.get("status") != "completed":
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"commitment_{entity['entity_id']}"})
        commitment_record_ids[entity["entity_id"]] = str(result["result_record_id"])
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after commitment {entity['entity_id']}"})

    for entity in ENTITIES:
        set_clean_entity_state(session, seed_state, entity)
        append_recall(
            store,
            session,
            entity,
            commitment_record_ids[entity["entity_id"]],
            terminal_tool_choice,
        )
        result = run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if result.get("status") != "completed":
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"recall_{entity['entity_id']}"})
        recall_record_ids.append(str(result["result_record_id"]))
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after recall {entity['entity_id']}"})

    session._state = {
        "probe_status": seed_state.get("probe_status", "ready"),
        "entity_ids": sorted(ENTITY_IDS),
        "open_items": [],
    }
    append_housekeeping(store, session, recall_record_ids, terminal_tool_choice)
    housekeeping = run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if housekeeping.get("status") != "completed":
        return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": "housekeeping"})
    commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after housekeeping"})

    session._state = {
        "probe_status": seed_state.get("probe_status", "ready"),
        "entity_ids": sorted(ENTITY_IDS),
        "open_items": [],
    }
    append_final(
        store,
        session,
        [*commitment_record_ids.values(), *recall_record_ids, str(housekeeping["result_record_id"])],
        terminal_tool_choice,
    )
    final = run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final.get("status") == "completed":
        commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after final"})
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
