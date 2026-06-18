"""Phase 2B Yanantin-backed multi-entity memory probe."""

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
from uuid import UUID, uuid4


JsonDict = dict[str, Any]

EXPERIMENT_ID = "phase_2b_yanantin_backed_multi_entity_memory_20260618"
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

LOCAL_MEMORY_RUN_PATH = (
    ROOT_DIR.parent / "phase_2a_local_memory_pressure_20260618" / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096


def load_local_memory_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase_2a_local_memory_pressure_for_yanantin_probe",
        LOCAL_MEMORY_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {LOCAL_MEMORY_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LOCAL = load_local_memory_module()
PROBE = LOCAL.PROBE
ENTITIES = LOCAL.ENTITIES
ENTITY_IDS = LOCAL.ENTITY_IDS
EXPECTED_CODES = LOCAL.EXPECTED_CODES


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
            "memory_substrate": "yanantin_apacheta_bridge_in_memory",
            "yanantin_enabled": True,
            "expected_event_type_sequence": [
                "yanantin_commitment",
                "yanantin_commitment",
                "yanantin_commitment",
                "yanantin_recall",
                "yanantin_recall",
                "yanantin_recall",
                "yanantin_memory_housekeeping",
                "yanantin_memory_final",
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 9 if live_model_calls else 0,
            "max_estimated_cost_usd": 4.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_2b_yanantin_backed_memory_taxonomy.v1",
            "layers": [
                "yanantin_write",
                "yanantin_retrieval",
                "state_isolation",
                "authorization",
                "provenance",
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


def scripted_outputs() -> list[JsonDict]:
    outputs = LOCAL.scripted_outputs()
    for output in outputs:
        response = output.get("response")
        if response == "entity commitment recorded":
            output["response"] = "yanantin commitment recorded"
        elif response == "entity memory recalled":
            output["response"] = "yanantin memory recalled"
        elif response == "local memory audit clean":
            output["response"] = "yanantin memory audit clean"
            output["audit_summary"] = "Yanantin recall records are complete and attributed"
        elif response == "local memory artifact complete":
            output["response"] = "yanantin memory artifact complete"
            output["artifact_title"] = "Phase 2B Yanantin Memory Result"
            output["conclusion"] = "Yanantin-backed recall recovered all commitments."
    return outputs


class PatchedYanantinScriptedBackend(PROBE.ScriptedTerminalBackend):
    def __init__(self, outputs: list[JsonDict | Exception]):
        super().__init__(outputs)
        self.source_record_ids: list[str] = []

    def call_terminal_surface(self, *args: Any, **kwargs: Any) -> Any:
        result = super().call_terminal_surface(*args, **kwargs)
        raw_output = result.raw_output
        surface = kwargs.get("terminal_surface")
        if (
            isinstance(surface, dict)
            and surface.get("tool_name") == "recall_yanantin_commitment"
        ):
            enum = (
                surface.get("input_schema", {})
                .get("properties", {})
                .get("source_record_id", {})
                .get("enum", [])
            )
            if enum:
                raw_output["source_record_id"] = enum[0]
                self.source_record_ids.append(str(enum[0]))
        if (
            isinstance(surface, dict)
            and surface.get("tool_name")
            == "write_yanantin_memory_pressure_artifact"
        ):
            raw_output["provenance_record_ids"] = sorted(self.source_record_ids)
        return result


def commitment_surface(*, entity: JsonDict, tool_choice: str) -> JsonDict:
    surface = LOCAL.commitment_surface(entity=entity, tool_choice=tool_choice)
    surface["tool_name"] = "record_yanantin_commitment"
    surface["description"] = "Record one entity commitment for Yanantin-backed recall."
    surface["input_schema"]["properties"]["response"]["enum"] = [
        "yanantin commitment recorded"
    ]
    return surface


def recall_surface(
    *,
    entity: JsonDict,
    source_record_id: str,
    tool_choice: str,
) -> JsonDict:
    surface = LOCAL.recall_surface(
        entity=entity,
        source_record_id=source_record_id,
        tool_choice=tool_choice,
    )
    surface["tool_name"] = "recall_yanantin_commitment"
    surface["description"] = (
        "Recall one commitment from explicit Yanantin-backed retrieved memory."
    )
    surface["input_schema"]["properties"]["response"]["enum"] = [
        "yanantin memory recalled"
    ]
    return surface


def housekeeping_surface(*, tool_choice: str) -> JsonDict:
    surface = LOCAL.housekeeping_surface(tool_choice=tool_choice)
    surface["tool_name"] = "audit_yanantin_memory_pressure"
    surface["description"] = "Audit Yanantin-backed recall records for provenance."
    surface["input_schema"]["properties"]["response"]["enum"] = [
        "yanantin memory audit clean"
    ]
    return surface


def final_surface(*, tool_choice: str) -> JsonDict:
    surface = LOCAL.final_surface(tool_choice=tool_choice)
    surface["tool_name"] = "write_yanantin_memory_pressure_artifact"
    surface["description"] = "Write the final Yanantin memory pressure artifact."
    surface["input_schema"]["properties"]["response"]["enum"] = [
        "yanantin memory artifact complete"
    ]
    return surface


def initialize_run(
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
):
    store, memory, ledger, frontier = LOCAL.initialize_run(
        paths,
        run_id,
        live_model_calls,
        endpoint,
        model,
        terminal_tool_choice,
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
            "yanantin_enabled": True,
            "yanantin_backend": "ApachetaBridge.from_memory",
        },
        sandbox={"network": "enabled" if live_model_calls else "disabled"},
    )
    return store, memory, ledger, frontier


def append_yanantin_event(
    store: Any,
    *,
    event_type: str,
    label: str,
    purpose: str,
    scheduled_by_cycle: int,
    scheduled_by_record_id: str,
    terminal_surface: JsonDict,
    requested_context: list[JsonDict],
    evidence_context: JsonDict | None = None,
) -> JsonDict:
    event = PROBE.build_pending_event(
        purpose=purpose,
        requested_context=requested_context,
        scheduled_by_cycle=scheduled_by_cycle,
        scheduled_by_record_id=scheduled_by_record_id,
        label=label,
        terminal_surface=terminal_surface,
    )
    event["event_type"] = event_type
    if evidence_context is not None:
        event["evidence_context"] = evidence_context
    store.append(event)
    return event


def yanantin_retrieved_memory_item(
    *,
    bridge: Any,
    record_id: str,
    entity: JsonDict,
    retrieval_reason: str,
) -> JsonDict:
    content = bridge.retrieve(UUID(str(record_id)))
    excerpt = {
        key: content.get(key)
        for key in ("entity_id", "workstream_id", "commitment_code", "open_items")
        if key in content
    }
    return {
        "source_record_id": record_id,
        "source_event_id": None,
        "source_run_id": bridge.session_id,
        "entity_id": entity["entity_id"],
        "workstream_id": entity["workstream_id"],
        "memory_scope": "entity_scoped",
        "access_scope": "entity_private",
        "relation_type": "retrieved_for",
        "retrieval_id": str(uuid4()),
        "retrieval_reason": retrieval_reason,
        "content_excerpt": excerpt,
        "omitted": ["provenance"],
        "truncated": False,
    }


def append_commitment(
    store: Any,
    session: Any,
    entity: JsonDict,
    terminal_tool_choice: str,
    context_record_id: str,
) -> JsonDict:
    return append_yanantin_event(
        store,
        event_type="yanantin_commitment",
        label=f"yanantin-commitment-{entity['entity_id']}",
        purpose=(
            f"Record commitment {entity['commitment_code']} for {entity['entity_id']}. "
            "Return response exactly: yanantin commitment recorded."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=str(session._prior_states[-1][1]),
        terminal_surface=commitment_surface(
            entity=entity,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": context_record_id}],
    )


def append_recall(
    store: Any,
    session: Any,
    entity: JsonDict,
    commitment_record_id: str,
    terminal_tool_choice: str,
    bridge: Any,
) -> JsonDict:
    retrieved_memory = yanantin_retrieved_memory_item(
        bridge=bridge,
        record_id=commitment_record_id,
        entity=entity,
        retrieval_reason="entity_commitment_recall",
    )
    return append_yanantin_event(
        store,
        event_type="yanantin_recall",
        label=f"yanantin-recall-{entity['entity_id']}",
        purpose=(
            f"Recall {entity['entity_id']}'s commitment from explicit "
            "Yanantin-backed requested context. The commitment is intentionally "
            "absent from the current wake state. Return response exactly: "
            "yanantin memory recalled."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=str(session._prior_states[-1][1]),
        terminal_surface=recall_surface(
            entity=entity,
            source_record_id=commitment_record_id,
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[{"tool": "recall", "record_id": commitment_record_id}],
        evidence_context={"retrieved_memory": [retrieved_memory]},
    )


def append_housekeeping(
    store: Any,
    session: Any,
    recall_record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return append_yanantin_event(
        store,
        event_type="yanantin_memory_housekeeping",
        label="yanantin-memory-housekeeping",
        purpose=(
            "Audit Yanantin-backed recall records for provenance. Return "
            "response exactly: yanantin memory audit clean."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=str(session._prior_states[-1][1]),
        terminal_surface=housekeeping_surface(tool_choice=terminal_tool_choice),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in recall_record_ids
        ],
    )


def append_final(
    store: Any,
    session: Any,
    record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return append_yanantin_event(
        store,
        event_type="yanantin_memory_final",
        label="yanantin-memory-final",
        purpose=(
            "Write final Yanantin memory pressure artifact. Return response "
            "exactly: yanantin memory artifact complete. Cite all "
            "source_record_id values from recalled commitments in "
            "provenance_record_ids."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=str(session._prior_states[-1][1]),
        terminal_surface=final_surface(tool_choice=terminal_tool_choice),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in record_ids
        ],
    )


def run_one_event(
    *,
    session: Any,
    store: Any,
    paths: Any,
    terminal_tool_choice: str,
    force_bridge_record_ids: set[str] | None = None,
) -> JsonDict:
    if not force_bridge_record_ids:
        return LOCAL.run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
    saved_prior_states = list(session._prior_states)
    filtered_prior_states = [
        entry for entry in saved_prior_states
        if str(entry[1]) not in force_bridge_record_ids
    ]
    session._prior_states = filtered_prior_states
    try:
        result = LOCAL.run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        new_entries = [
            entry for entry in session._prior_states
            if str(entry[1]) not in {str(saved[1]) for saved in saved_prior_states}
        ]
    finally:
        session._prior_states = saved_prior_states
    session._prior_states.extend(new_entries)
    return result


def read_jsonl(path: Path) -> list[JsonDict]:
    return LOCAL.read_jsonl(path)


def session_state_by_record_id(path: Path) -> dict[str, JsonDict]:
    return LOCAL.session_state_by_record_id(path)


def completed_states(records: list[JsonDict], paths: Any) -> list[JsonDict]:
    return LOCAL.completed_states(records, paths)


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
        "recall_required_yanantin_context": (
            leaks == [] and len(observations) == len(ENTITIES)
        ),
    }


def yanantin_context_observations(records: list[JsonDict]) -> JsonDict:
    observations: list[JsonDict] = []
    missing: list[JsonDict] = []
    for record in records:
        if (
            record.get("record_type") != "event_status"
            or record.get("status") != "completed"
            or record.get("event_type") != "yanantin_recall"
        ):
            continue
        context_results = record.get("context_results") or []
        first = context_results[0] if context_results else {}
        result = first.get("result") if isinstance(first, dict) else {}
        content = result.get("content") if isinstance(result, dict) else {}
        has_provenance = isinstance(content, dict) and isinstance(
            content.get("provenance"),
            dict,
        )
        observation = {
            "event_id": record.get("event_id"),
            "result_record_id": record.get("result_record_id"),
            "requested_record_id": (
                first.get("request", {}).get("record_id")
                if isinstance(first, dict) and isinstance(first.get("request"), dict)
                else None
            ),
            "has_yanantin_provenance": has_provenance,
            "content_keys": sorted(content) if isinstance(content, dict) else [],
        }
        observations.append(observation)
        if not has_provenance:
            missing.append(observation)
    return {
        "yanantin_context_observations": observations,
        "yanantin_context_missing_provenance": missing,
        "retrieval_context_has_yanantin_provenance": (
            missing == [] and len(observations) == len(ENTITIES)
        ),
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
    yanantin_context = yanantin_context_observations(records)
    checks = {
        "completed_expected_events": completed_types == [
            "yanantin_commitment",
            "yanantin_commitment",
            "yanantin_commitment",
            "yanantin_recall",
            "yanantin_recall",
            "yanantin_recall",
            "yanantin_memory_housekeeping",
            "yanantin_memory_final",
        ],
        "recall_required_yanantin_context": prior_recall[
            "recall_required_yanantin_context"
        ],
        "recall_codes_correct": sorted(
            state.get("recalled_commitment_code") for state in recall_states
        ) == EXPECTED_CODES,
        "recall_source_records_present": len(expected_source_ids) == len(ENTITIES)
        and all(expected_source_ids),
        "retrieval_context_has_yanantin_provenance": yanantin_context[
            "retrieval_context_has_yanantin_provenance"
        ],
        "housekeeping_checked_recall_records": housekeeping_state.get(
            "recall_records_checked"
        ) == len(ENTITIES),
        "housekeeping_clean": housekeeping_state.get("unsupported_claims") == []
        and housekeeping_state.get("attribution_errors") == [],
        "final_entity_count": final_state.get("entity_count") == len(ENTITIES),
        "final_codes": sorted(final_state.get("recalled_commitment_codes") or [])
        == EXPECTED_CODES,
        "final_provenance_includes_source_records": set(expected_source_ids).issubset(
            set(final_state.get("provenance_record_ids") or [])
        ),
        "final_clean": final_state.get("unsupported_claims") == []
        and final_state.get("attribution_errors") == [],
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
        **yanantin_context,
    }


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures = PROBE.collect_failures(paths, records, success)
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        layer = "artifact"
        if "yanantin" in check_name or "retrieval" in check_name:
            layer = "yanantin_retrieval"
        elif "provenance" in check_name:
            layer = "provenance"
        elif "context" in check_name:
            layer = "yanantin_retrieval"
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


def finalize_results(
    *,
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
    store: Any,
    bridge: Any,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    success = required_success(summary, records, paths=paths)
    failures = collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    open_records = bridge.list_open_records()
    results = {
        "schema_version": "hamutay.phase_2b_yanantin_backed_memory.v1",
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
        "yanantin": {
            "backend": "ApachetaBridge.from_memory",
            "session_id": bridge.session_id,
            "open_record_count": len(open_records),
            "open_record_ids": [str(record_id) for record_id, _record in open_records],
        },
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
    terminal_tool_choice = terminal_tool_choice or PROBE.default_terminal_tool_choice(
        endpoint,
    )
    if backend is None:
        if live_model_calls:
            backend = PROBE.make_live_backend(
                endpoint=endpoint,
                api_key=api_key or "",
                max_tokens=max_tokens,
            )
        else:
            backend = PatchedYanantinScriptedBackend(scripted_outputs())

    from hamutay.apacheta_bridge import ApachetaBridge

    bridge = ApachetaBridge.from_memory(session_id=run_id, model=model)
    store, memory, ledger, frontier = initialize_run(
        paths,
        run_id,
        live_model_calls,
        endpoint,
        model,
        terminal_tool_choice,
    )
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    session._bridge = bridge
    try:
        session.exchange(
            json.dumps(
                {
                    "event": "initialize_yanantin_memory_pressure_probe",
                    "instruction": (
                        "Initialize durable state for a Yanantin-backed "
                        "memory pressure probe."
                    ),
                    "required_output": {
                        "response": "<brief initialization note>",
                        "probe_status": "ready",
                        "open_items": [],
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            terminal_surface=PROBE.seed_terminal_surface(
                tool_choice=terminal_tool_choice,
            ),
            force_memory=None,
        )
    except Exception as exc:
        PROBE.record_failure(paths, PROBE.classify_exception(exc, stage="seed_exchange"))
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            bridge=bridge,
            extra={"stopped_after": "seed_exchange"},
        )

    seed_state = LOCAL.clone_json(session._state or {})
    seed_record_id = str(session._prior_states[-1][1])
    commitment_record_ids: dict[str, str] = {}
    recall_record_ids: list[str] = []
    LOCAL.commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after seed"},
    )

    for entity in ENTITIES:
        LOCAL.set_clean_entity_state(session, seed_state, entity)
        append_commitment(
            store,
            session,
            entity,
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
                bridge=bridge,
                extra={"stopped_after": f"commitment_{entity['entity_id']}"},
            )
        commitment_record_ids[entity["entity_id"]] = str(result["result_record_id"])
        LOCAL.commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after commitment {entity['entity_id']}"},
        )

    for entity in ENTITIES:
        LOCAL.set_clean_entity_state(session, seed_state, entity)
        commitment_record_id = commitment_record_ids[entity["entity_id"]]
        append_recall(
            store,
            session,
            entity,
            commitment_record_id,
            terminal_tool_choice,
            bridge,
        )
        result = run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
            force_bridge_record_ids={commitment_record_id},
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
                bridge=bridge,
                extra={"stopped_after": f"recall_{entity['entity_id']}"},
            )
        recall_record_ids.append(str(result["result_record_id"]))
        LOCAL.commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after recall {entity['entity_id']}"},
        )

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
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            bridge=bridge,
            extra={"stopped_after": "housekeeping"},
        )
    LOCAL.commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after housekeeping"},
    )

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
        LOCAL.commit_frontier(
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
        bridge=bridge,
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
    print(json.dumps({"classification": result["classification"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
