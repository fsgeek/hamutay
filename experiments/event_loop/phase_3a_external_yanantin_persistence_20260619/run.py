"""Phase 3A persistent Yanantin backend pressure probe."""

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

EXPERIMENT_ID = "phase_3a_external_yanantin_persistence_20260619"
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

PHASE2B_RUN_PATH = (
    ROOT_DIR.parent
    / "phase_2b_yanantin_backed_multi_entity_memory_20260618"
    / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
DB_FILENAME = "yanantin_persistent.duckdb"


def load_phase2b_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase_2b_yanantin_for_phase_3a_persistence",
        PHASE2B_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {PHASE2B_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    module.PROBE.EXPERIMENT_ID = EXPERIMENT_ID
    module.PROBE.ROOT_DIR = ROOT_DIR
    return module


PHASE2B = load_phase2b_module()
PROBE = PHASE2B.PROBE
LOCAL = PHASE2B.LOCAL
ENTITIES = PHASE2B.ENTITIES
ENTITY_IDS = PHASE2B.ENTITY_IDS
EXPECTED_CODES = PHASE2B.EXPECTED_CODES


class TimedPersistentBridge:
    """Timing wrapper around ApachetaBridge.from_duckdb."""

    def __init__(self, *, db_path: Path, session_id: str, model: str) -> None:
        from hamutay.apacheta_bridge import ApachetaBridge

        self.db_path = db_path
        self._bridge = ApachetaBridge.from_duckdb(
            db_path,
            session_id=session_id,
            model=model,
        )
        self.operations: list[JsonDict] = []

    def _timed(self, operation: str, func, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.operations.append(
                {
                    "operation": operation,
                    "ok": False,
                    "elapsed_ms": round(elapsed_ms, 3),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        self.operations.append(
            {
                "operation": operation,
                "ok": True,
                "elapsed_ms": round(elapsed_ms, 3),
            }
        )
        return result

    def store_open_state(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("store_open_state", self._bridge.store_open_state, *args, **kwargs)

    def retrieve(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("retrieve", self._bridge.retrieve, *args, **kwargs)

    def store_edge(self, *args: Any, **kwargs: Any) -> Any:
        return self._timed("store_edge", self._bridge.store_edge, *args, **kwargs)

    def count_records(self) -> JsonDict:
        return self._timed("count_records", self._bridge._backend.count_records)

    def probe_open_record_query_support(self) -> JsonDict:
        probes = {}
        for name, call in {
            "list_open_records": lambda: self._bridge.list_open_records(limit=1),
            "query_open_by_session": lambda: self._bridge.query_open_by_session(
                self.session_id,
                limit=1,
            ),
            "query_open_by_lineage_tag": lambda: self._bridge.query_open_by_lineage_tag(
                "hamutay",
                limit=1,
            ),
            "query_open_has_field": lambda: self._bridge.query_open_has_field(
                "entity_id",
                limit=1,
            ),
        }.items():
            try:
                result = self._timed(name, call)
            except NotImplementedError as exc:
                probes[name] = {
                    "supported": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            else:
                probes[name] = {
                    "supported": True,
                    "result_count": len(result),
                }
        return probes

    def close(self) -> None:
        backend = getattr(self._bridge, "_backend", None)
        close = getattr(backend, "close", None)
        if callable(close):
            self._timed("close", close)

    @property
    def session_id(self) -> str:
        return self._bridge.session_id

    @property
    def count(self) -> int:
        return self._bridge.count


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
            "base_protocol": "phase_2b_yanantin_backed_multi_entity_memory_20260618",
            "backend": "ApachetaBridge.from_duckdb",
            "persistent_artifact": DB_FILENAME,
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
            "schema_version": "hamutay.phase_3a_external_yanantin_persistence_taxonomy.v1",
            "layers": [
                "yanantin_write",
                "yanantin_retrieval",
                "backend_configuration",
                "backend_persistence",
                "backend_query_limitation",
                "state_isolation",
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


def verify_reopened_source_records(
    *,
    db_path: Path,
    run_id: str,
    model: str,
    source_record_ids: list[str],
) -> JsonDict:
    from hamutay.apacheta_bridge import ApachetaBridge

    reopened = ApachetaBridge.from_duckdb(db_path, session_id=run_id, model=model)
    observations: list[JsonDict] = []
    try:
        counts = reopened._backend.count_records()
        for record_id in source_record_ids:
            try:
                content = reopened.retrieve(UUID(str(record_id)))
            except Exception as exc:
                observations.append(
                    {
                        "record_id": record_id,
                        "retrieved": False,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                continue
            observations.append(
                {
                    "record_id": record_id,
                    "retrieved": True,
                    "entity_id": content.get("entity_id"),
                    "workstream_id": content.get("workstream_id"),
                    "commitment_code": content.get("commitment_code"),
                    "has_provenance": isinstance(content.get("provenance"), dict),
                    "content_keys": sorted(content),
                }
            )
    finally:
        close = getattr(reopened._backend, "close", None)
        if callable(close):
            close()
    expected_by_code = {
        entity["commitment_code"]: entity for entity in ENTITIES
    }
    identity_preserved = True
    for item in observations:
        if not item.get("retrieved"):
            identity_preserved = False
            continue
        expected = expected_by_code.get(str(item.get("commitment_code")))
        if expected is None:
            identity_preserved = False
            continue
        if item.get("entity_id") != expected["entity_id"]:
            identity_preserved = False
        if item.get("workstream_id") != expected["workstream_id"]:
            identity_preserved = False
        if item.get("has_provenance") is not True:
            identity_preserved = False
    return {
        "record_counts_after_reopen": counts,
        "reopened_source_record_observations": observations,
        "reopened_source_records_retrievable": (
            len(observations) == len(source_record_ids)
            and all(item.get("retrieved") is True for item in observations)
        ),
        "reopened_source_identity_preserved": identity_preserved
        and len(observations) == len(source_record_ids),
    }


def add_persistence_checks(
    *,
    success: JsonDict,
    db_path: Path,
    bridge: TimedPersistentBridge,
    run_id: str,
    model: str,
    open_query_support: JsonDict,
) -> JsonDict:
    source_record_ids = success.get("expected_source_record_ids") or []
    counts_before = bridge.count_records()
    bridge.close()
    reopened = verify_reopened_source_records(
        db_path=db_path,
        run_id=run_id,
        model=model,
        source_record_ids=source_record_ids,
    )
    query_limitations = [
        name for name, result in open_query_support.items()
        if result.get("supported") is False
    ]
    checks = dict(success["checks"])
    checks.update(
        {
            "persistent_db_file_exists": db_path.exists() and db_path.stat().st_size > 0,
            "backend_counts_include_records": counts_before.get("records", 0)
            >= len(source_record_ids),
            "reopened_source_records_retrievable": reopened[
                "reopened_source_records_retrievable"
            ],
            "reopened_source_identity_preserved": reopened[
                "reopened_source_identity_preserved"
            ],
            "operation_latencies_captured": any(
                operation.get("operation") == "store_open_state"
                for operation in bridge.operations
            )
            and any(
                operation.get("operation") == "retrieve"
                for operation in bridge.operations
            ),
            "open_record_query_limitations_explicit": (
                len(query_limitations) > 0
                and all(
                    open_query_support[name].get("error_type") == "NotImplementedError"
                    for name in query_limitations
                )
            ),
        }
    )
    return {
        **success,
        "passed": all(checks.values()),
        "checks": checks,
        "persistent_backend": {
            "backend": "ApachetaBridge.from_duckdb",
            "db_path": str(db_path),
            "db_file_exists": db_path.exists(),
            "db_file_size_bytes": db_path.stat().st_size if db_path.exists() else 0,
            "record_counts_before_reopen": counts_before,
            "open_record_query_support": open_query_support,
            "open_record_query_limitations": query_limitations,
            "operations": bridge.operations,
            **reopened,
        },
    }


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures = PHASE2B.collect_failures(paths, records, success)
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        if any(
            marker in check_name
            for marker in ("persistent", "reopened", "backend_counts")
        ):
            layer = "backend_persistence"
        elif "latencies" in check_name:
            layer = "backend_configuration"
        elif "open_record_query" in check_name:
            layer = "backend_query_limitation"
        else:
            continue
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
    bridge: TimedPersistentBridge,
    db_path: Path,
    open_query_support: JsonDict | None = None,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    base_success = PHASE2B.required_success(summary, records, paths=paths)
    success = add_persistence_checks(
        success=base_success,
        db_path=db_path,
        bridge=bridge,
        run_id=run_id,
        model=model,
        open_query_support=open_query_support or {},
    )
    failures = collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.phase_3a_external_yanantin_persistence.v1",
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
            "persistent_db": DB_FILENAME,
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
            backend = PHASE2B.PatchedYanantinScriptedBackend(PHASE2B.scripted_outputs())

    db_path = paths.output_root / DB_FILENAME
    bridge = TimedPersistentBridge(db_path=db_path, session_id=run_id, model=model)
    store, memory, ledger, frontier = PHASE2B.initialize_run(
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
                    "event": "initialize_phase_3a_external_yanantin_persistence",
                    "instruction": (
                        "Initialize durable state for a persistent Yanantin "
                        "backend pressure probe."
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
            db_path=db_path,
            extra={"stopped_after": "seed_exchange"},
        )

    seed_state = PHASE2B.LOCAL.clone_json(session._state or {})
    seed_record_id = str(session._prior_states[-1][1])
    commitment_record_ids: dict[str, str] = {}
    recall_record_ids: list[str] = []
    PHASE2B.LOCAL.commit_frontier(
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
        PHASE2B.LOCAL.set_clean_entity_state(session, seed_state, entity)
        PHASE2B.append_commitment(
            store,
            session,
            entity,
            terminal_tool_choice,
            seed_record_id,
        )
        result = PHASE2B.run_one_event(
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
                db_path=db_path,
                extra={"stopped_after": f"commitment_{entity['entity_id']}"},
            )
        commitment_record_ids[entity["entity_id"]] = str(result["result_record_id"])
        PHASE2B.LOCAL.commit_frontier(
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
        PHASE2B.LOCAL.set_clean_entity_state(session, seed_state, entity)
        commitment_record_id = commitment_record_ids[entity["entity_id"]]
        PHASE2B.append_recall(
            store,
            session,
            entity,
            commitment_record_id,
            terminal_tool_choice,
            bridge,
        )
        result = PHASE2B.run_one_event(
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
                db_path=db_path,
                extra={"stopped_after": f"recall_{entity['entity_id']}"},
            )
        recall_record_ids.append(str(result["result_record_id"]))
        PHASE2B.LOCAL.commit_frontier(
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
    PHASE2B.append_housekeeping(store, session, recall_record_ids, terminal_tool_choice)
    housekeeping = PHASE2B.run_one_event(
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
            db_path=db_path,
            extra={"stopped_after": "housekeeping"},
        )
    PHASE2B.LOCAL.commit_frontier(
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
    PHASE2B.append_final(
        store,
        session,
        [*commitment_record_ids.values(), *recall_record_ids, str(housekeeping["result_record_id"])],
        terminal_tool_choice,
    )
    final = PHASE2B.run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final.get("status") == "completed":
        PHASE2B.LOCAL.commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": "after final"},
        )
    open_query_support = bridge.probe_open_record_query_support()
    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
        bridge=bridge,
        db_path=db_path,
        open_query_support=open_query_support,
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
    return 0 if result["classification"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
