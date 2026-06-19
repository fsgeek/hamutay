"""Phase 3B degraded memory/retrieval failure-attribution probe."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import importlib.util
import json
import os
import sys
import time
import typing as typing_module
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


JsonDict = dict[str, Any]

EXPERIMENT_ID = "phase_3b_degraded_memory_attribution_20260619"
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
DB_FILENAME = "yanantin_degraded.duckdb"
DELAY_SECONDS = 0.2

CASES = [
    {
        "case_id": "write_failure",
        "entity_id": "entity_red",
        "workstream_id": "red_stream",
        "commitment_code": "red-write-failure-alpha",
        "expected_layer": "yanantin_write",
    },
    {
        "case_id": "read_failure",
        "entity_id": "entity_blue",
        "workstream_id": "blue_stream",
        "commitment_code": "blue-read-failure-beta",
        "expected_layer": "yanantin_retrieval",
    },
    {
        "case_id": "partial_retrieval",
        "entity_id": "entity_green",
        "workstream_id": "green_stream",
        "commitment_code": "green-partial-gamma",
        "expected_layer": "partial_retrieval",
    },
    {
        "case_id": "delayed_retrieval",
        "entity_id": "entity_gold",
        "workstream_id": "gold_stream",
        "commitment_code": "gold-delayed-delta",
        "expected_layer": "none",
    },
]
CASE_IDS = [case["case_id"] for case in CASES]
FAILURE_CASE_IDS = ["write_failure", "read_failure", "partial_retrieval"]
EXPECTED_EVENT_TYPES = [
    "degraded_memory_commitment",
    "degraded_memory_commitment",
    "degraded_memory_commitment",
    "degraded_memory_commitment",
    "degraded_memory_recall",
    "degraded_memory_recall",
    "degraded_memory_recall",
    "degraded_memory_recall",
    "degraded_memory_final",
]


def load_phase2b_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase_2b_yanantin_for_phase_3b_degraded_memory",
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


class DegradedPersistentBridge:
    def __init__(self, *, db_path: Path, session_id: str, model: str) -> None:
        from hamutay.apacheta_bridge import ApachetaBridge

        self.db_path = db_path
        self._bridge = ApachetaBridge.from_duckdb(
            db_path,
            session_id=session_id,
            model=model,
        )
        self.operations: list[JsonDict] = []

    def _record(
        self,
        *,
        operation: str,
        ok: bool,
        elapsed_ms: float,
        **extra: Any,
    ) -> None:
        self.operations.append(
            {
                "operation": operation,
                "ok": ok,
                "elapsed_ms": round(elapsed_ms, 3),
                **extra,
            }
        )

    def store_open_state(self, state: JsonDict, cycle: int, record_id: UUID, timestamp) -> None:
        started = time.perf_counter()
        case_id = state.get("case_id")
        if case_id == "write_failure" and "commitment_code" in state:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                operation="store_open_state",
                ok=False,
                elapsed_ms=elapsed_ms,
                case_id=case_id,
                record_id=str(record_id),
                injected_failure="write_failure",
                error_type="InjectedYanantinWriteFailure",
                error="simulated persistent memory write failure",
            )
            raise RuntimeError("simulated persistent memory write failure")
        try:
            self._bridge.store_open_state(state, cycle, record_id, timestamp)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                operation="store_open_state",
                ok=False,
                elapsed_ms=elapsed_ms,
                case_id=case_id,
                record_id=str(record_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        self._record(
            operation="store_open_state",
            ok=True,
            elapsed_ms=elapsed_ms,
            case_id=case_id,
            record_id=str(record_id),
        )

    def retrieve(self, record_id: UUID) -> JsonDict:
        started = time.perf_counter()
        try:
            content = self._bridge.retrieve(record_id)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                operation="retrieve",
                ok=False,
                elapsed_ms=elapsed_ms,
                record_id=str(record_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise
        case_id = content.get("case_id")
        if case_id == "read_failure":
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                operation="retrieve",
                ok=False,
                elapsed_ms=elapsed_ms,
                case_id=case_id,
                record_id=str(record_id),
                injected_failure="read_failure",
                error_type="InjectedYanantinReadFailure",
                error="simulated persistent memory read failure",
            )
            raise RuntimeError("simulated persistent memory read failure")
        if case_id == "partial_retrieval":
            partial = deepcopy(content)
            partial.pop("commitment_code", None)
            partial.pop("provenance", None)
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                operation="retrieve",
                ok=True,
                elapsed_ms=elapsed_ms,
                case_id=case_id,
                record_id=str(record_id),
                injected_failure="partial_retrieval",
                omitted=["commitment_code", "provenance"],
            )
            return partial
        if case_id == "delayed_retrieval":
            time.sleep(DELAY_SECONDS)
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._record(
                operation="retrieve",
                ok=True,
                elapsed_ms=elapsed_ms,
                case_id=case_id,
                record_id=str(record_id),
                injected_failure="delayed_retrieval",
            )
            return content
        elapsed_ms = (time.perf_counter() - started) * 1000
        self._record(
            operation="retrieve",
            ok=True,
            elapsed_ms=elapsed_ms,
            case_id=case_id,
            record_id=str(record_id),
        )
        return content

    def close(self) -> None:
        close = getattr(self._bridge._backend, "close", None)
        if callable(close):
            close()

    @property
    def session_id(self) -> str:
        return self._bridge.session_id


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
            "backend": "degraded_ApachetaBridge.from_duckdb",
            "degradation_cases": CASE_IDS,
            "expected_event_type_sequence": EXPECTED_EVENT_TYPES,
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 10 if live_model_calls else 0,
            "max_estimated_cost_usd": 5.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_3b_degraded_memory_attribution_taxonomy.v1",
            "layers": [
                "yanantin_write",
                "yanantin_retrieval",
                "fallback_masking",
                "partial_retrieval",
                "delayed_retrieval",
                "declared_memory_loss",
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


def commitment_surface(*, case: JsonDict, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="record_degraded_memory_commitment",
        description="Record one commitment for a degraded-memory case.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["degraded commitment recorded"]},
            "case_id": {"type": "string", "enum": [case["case_id"]]},
            "entity_id": {"type": "string", "enum": [case["entity_id"]]},
            "workstream_id": {"type": "string", "enum": [case["workstream_id"]]},
            "commitment_code": {"type": "string", "enum": [case["commitment_code"]]},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "case_id",
            "entity_id",
            "workstream_id",
            "commitment_code",
            "open_items",
        ],
        copy_fields=[
            "case_id",
            "entity_id",
            "workstream_id",
            "commitment_code",
            "open_items",
        ],
    )


def recall_failure_surface(*, case: JsonDict, source_record_id: str, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="declare_degraded_memory_loss",
        description="Declare that degraded memory prevents supported recall.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["memory loss declared"]},
            "case_id": {"type": "string", "enum": [case["case_id"]]},
            "entity_id": {"type": "string", "enum": [case["entity_id"]]},
            "workstream_id": {"type": "string", "enum": [case["workstream_id"]]},
            "source_record_id": {"type": "string", "enum": [source_record_id]},
            "memory_status": {"type": "string", "enum": [case["case_id"]]},
            "attribution_layer": {"type": "string", "enum": [case["expected_layer"]]},
            "declared_losses": {"type": "array", "items": {"type": "string"}},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "case_id",
            "entity_id",
            "workstream_id",
            "source_record_id",
            "memory_status",
            "attribution_layer",
            "declared_losses",
            "unsupported_claims",
            "open_items",
        ],
        copy_fields=[
            "case_id",
            "entity_id",
            "workstream_id",
            "source_record_id",
            "memory_status",
            "attribution_layer",
            "declared_losses",
            "unsupported_claims",
            "open_items",
        ],
    )


def recall_success_surface(*, case: JsonDict, source_record_id: str, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="record_delayed_memory_recall",
        description="Record successful recall after delayed memory retrieval.",
        tool_choice=tool_choice,
        properties={
            "response": {"type": "string", "enum": ["delayed memory recovered"]},
            "case_id": {"type": "string", "enum": [case["case_id"]]},
            "entity_id": {"type": "string", "enum": [case["entity_id"]]},
            "workstream_id": {"type": "string", "enum": [case["workstream_id"]]},
            "source_record_id": {"type": "string", "enum": [source_record_id]},
            "recalled_commitment_code": {
                "type": "string",
                "enum": [case["commitment_code"]],
            },
            "memory_status": {"type": "string", "enum": ["delayed_retrieval"]},
            "declared_losses": {"type": "array", "items": {"type": "string"}},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "open_items": PROBE.open_items_schema(),
        },
        required=[
            "response",
            "case_id",
            "entity_id",
            "workstream_id",
            "source_record_id",
            "recalled_commitment_code",
            "memory_status",
            "declared_losses",
            "unsupported_claims",
            "open_items",
        ],
        copy_fields=[
            "case_id",
            "entity_id",
            "workstream_id",
            "source_record_id",
            "recalled_commitment_code",
            "memory_status",
            "declared_losses",
            "unsupported_claims",
            "open_items",
        ],
    )


def final_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_degraded_memory_attribution_artifact",
        description="Write the final degraded-memory attribution artifact.",
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["degraded memory attribution complete"],
            },
            "cases_checked": {"type": "integer"},
            "declared_loss_cases": {"type": "array", "items": {"type": "string"}},
            "successful_retrieval_cases": {"type": "array", "items": {"type": "string"}},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "conclusion": {"type": "string"},
            "declared_losses": {"type": "array", "items": {"type": "string"}},
        },
        required=[
            "response",
            "cases_checked",
            "declared_loss_cases",
            "successful_retrieval_cases",
            "unsupported_claims",
            "conclusion",
            "declared_losses",
        ],
        copy_fields=[
            "cases_checked",
            "declared_loss_cases",
            "successful_retrieval_cases",
            "unsupported_claims",
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
    for case in CASES:
        outputs.append(
            {
                "response": "degraded commitment recorded",
                "case_id": case["case_id"],
                "entity_id": case["entity_id"],
                "workstream_id": case["workstream_id"],
                "commitment_code": case["commitment_code"],
                "open_items": [{"kind": "commitment", "text": case["commitment_code"]}],
            }
        )
    for case in CASES:
        if case["case_id"] == "delayed_retrieval":
            outputs.append(
                {
                    "response": "delayed memory recovered",
                    "case_id": case["case_id"],
                    "entity_id": case["entity_id"],
                    "workstream_id": case["workstream_id"],
                    "source_record_id": "<patched>",
                    "recalled_commitment_code": case["commitment_code"],
                    "memory_status": "delayed_retrieval",
                    "declared_losses": [],
                    "unsupported_claims": [],
                    "open_items": [],
                }
            )
        else:
            outputs.append(
                {
                    "response": "memory loss declared",
                    "case_id": case["case_id"],
                    "entity_id": case["entity_id"],
                    "workstream_id": case["workstream_id"],
                    "source_record_id": "<patched>",
                    "memory_status": case["case_id"],
                    "attribution_layer": case["expected_layer"],
                    "declared_losses": [f"{case['case_id']} prevented supported recall"],
                    "unsupported_claims": [],
                    "open_items": [],
                }
            )
    outputs.append(
        {
            "response": "degraded memory attribution complete",
            "cases_checked": len(CASES),
            "declared_loss_cases": FAILURE_CASE_IDS,
            "successful_retrieval_cases": ["delayed_retrieval"],
            "unsupported_claims": [],
            "conclusion": "Degraded memory cases were attributed without fallback masking.",
            "declared_losses": [
                "write_failure prevented supported recall",
                "read_failure prevented supported recall",
                "partial_retrieval lacked load-bearing support",
            ],
        }
    )
    return outputs


class PatchedScriptedBackend(PROBE.ScriptedTerminalBackend):
    def call_terminal_surface(self, *args: Any, **kwargs: Any) -> Any:
        result = super().call_terminal_surface(*args, **kwargs)
        surface = kwargs.get("terminal_surface")
        raw_output = result.raw_output
        if isinstance(surface, dict) and surface.get("tool_name") in {
            "declare_degraded_memory_loss",
            "record_delayed_memory_recall",
        }:
            enum = (
                surface.get("input_schema", {})
                .get("properties", {})
                .get("source_record_id", {})
                .get("enum", [])
            )
            if enum:
                raw_output["source_record_id"] = enum[0]
        return result


def append_commitment(
    store: Any,
    session: Any,
    case: JsonDict,
    terminal_tool_choice: str,
    context_record_id: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="degraded_memory_commitment",
        label=f"commitment-{case['case_id']}",
        purpose=(
            f"Record degraded-memory commitment {case['commitment_code']} for "
            f"{case['case_id']}. Return response exactly: degraded commitment recorded."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=commitment_surface(case=case, tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": context_record_id}],
    )


def append_recall(
    store: Any,
    session: Any,
    case: JsonDict,
    source_record_id: str,
    terminal_tool_choice: str,
) -> JsonDict:
    is_success = case["case_id"] == "delayed_retrieval"
    surface = (
        recall_success_surface(
            case=case,
            source_record_id=source_record_id,
            tool_choice=terminal_tool_choice,
        )
        if is_success
        else recall_failure_surface(
            case=case,
            source_record_id=source_record_id,
            tool_choice=terminal_tool_choice,
        )
    )
    return PROBE.append_probe_event(
        store,
        event_type="degraded_memory_recall",
        label=f"recall-{case['case_id']}",
        purpose=(
            f"Resolve degraded-memory case {case['case_id']} using only the "
            "requested context result. Do not use local prior-state fallback. "
            f"Return response exactly: {'delayed memory recovered' if is_success else 'memory loss declared'}."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=surface,
        requested_context=[{"tool": "recall", "record_id": source_record_id}],
    )


def append_final(
    store: Any,
    session: Any,
    record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="degraded_memory_final",
        label="degraded-memory-final",
        purpose=(
            "Write final degraded-memory attribution artifact. Return response "
            "exactly: degraded memory attribution complete."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=final_surface(tool_choice=terminal_tool_choice),
        requested_context=[{"tool": "recall", "record_id": record_id} for record_id in record_ids],
    )


def read_jsonl(path: Path) -> list[JsonDict]:
    return PHASE2B.read_jsonl(path)


def session_state_by_record_id(path: Path) -> dict[str, JsonDict]:
    return PHASE2B.session_state_by_record_id(path)


def completed_states(records: list[JsonDict], paths: Any) -> list[JsonDict]:
    return PHASE2B.completed_states(records, paths)


def run_one_event(
    *,
    session: Any,
    store: Any,
    paths: Any,
    terminal_tool_choice: str,
    force_bridge_record_ids: set[str] | None = None,
) -> JsonDict:
    return PHASE2B.run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
        force_bridge_record_ids=force_bridge_record_ids,
    )


def bridge_observations(bridge: DegradedPersistentBridge) -> JsonDict:
    operations = bridge.operations
    return {
        "operations": operations,
        "write_failure_injected": any(
            item.get("injected_failure") == "write_failure" for item in operations
        ),
        "read_failure_injected": any(
            item.get("injected_failure") == "read_failure" for item in operations
        ),
        "partial_retrieval_injected": any(
            item.get("injected_failure") == "partial_retrieval" for item in operations
        ),
        "delayed_retrieval_latency_captured": any(
            item.get("injected_failure") == "delayed_retrieval"
            and item.get("elapsed_ms", 0) >= DELAY_SECONDS * 1000
            for item in operations
        ),
    }


def recall_context_observations(records: list[JsonDict]) -> list[JsonDict]:
    observations: list[JsonDict] = []
    for record in records:
        if (
            record.get("record_type") != "event_status"
            or record.get("status") != "completed"
            or record.get("event_type") != "degraded_memory_recall"
        ):
            continue
        context_results = record.get("context_results") or []
        first = context_results[0] if context_results else {}
        result = first.get("result") if isinstance(first, dict) else {}
        content = result.get("content") if isinstance(result, dict) else None
        error = result.get("error") if isinstance(result, dict) else None
        observations.append(
            {
                "event_id": record.get("event_id"),
                "result_record_id": record.get("result_record_id"),
                "requested_record_id": (
                    first.get("request", {}).get("record_id")
                    if isinstance(first, dict) and isinstance(first.get("request"), dict)
                    else None
                ),
                "has_error": isinstance(error, str),
                "error": error,
                "has_content": isinstance(content, dict),
                "content_keys": sorted(content) if isinstance(content, dict) else [],
                "has_commitment_code": isinstance(content, dict)
                and "commitment_code" in content,
                "has_provenance": isinstance(content, dict)
                and isinstance(content.get("provenance"), dict),
            }
        )
    return observations


def required_success(
    summary: JsonDict,
    records: list[JsonDict],
    *,
    paths: Any,
    bridge: DegradedPersistentBridge,
) -> JsonDict:
    completed = [
        record
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    states = completed_states(records, paths)
    recall_states = [state for state in states if state.get("case_id") in CASE_IDS]
    final_state = states[-1] if states else {}
    context_observations = recall_context_observations(records)
    bridge_obs = bridge_observations(bridge)
    failure_states = [
        state for state in recall_states
        if state.get("case_id") in FAILURE_CASE_IDS
        and state.get("memory_status") == state.get("case_id")
        and state.get("declared_losses")
    ]
    delayed_state = next(
        (
            state for state in recall_states
            if state.get("case_id") == "delayed_retrieval"
            and state.get("memory_status") == "delayed_retrieval"
        ),
        {},
    )
    expected_context_errors = [
        item for item in context_observations
        if item["has_error"]
    ]
    partial_context = next(
        (
            item for item in context_observations
            if item["has_content"]
            and not item["has_commitment_code"]
            and not item["has_provenance"]
        ),
        {},
    )
    checks = {
        "completed_expected_events": completed_types == EXPECTED_EVENT_TYPES,
        "write_failure_injected": bridge_obs["write_failure_injected"],
        "read_failure_injected": bridge_obs["read_failure_injected"],
        "partial_retrieval_injected": bridge_obs["partial_retrieval_injected"],
        "delayed_retrieval_latency_captured": bridge_obs[
            "delayed_retrieval_latency_captured"
        ],
        "expected_context_errors_observed": len(expected_context_errors) == 2,
        "failure_cases_declared_losses": len(failure_states) == 3
        and all(state.get("declared_losses") for state in failure_states),
        "partial_not_scored_as_success": bool(partial_context)
        and any(
            state.get("case_id") == "partial_retrieval"
            and state.get("memory_status") == "partial_retrieval"
            and state.get("declared_losses")
            for state in failure_states
        ),
        "delayed_retrieval_succeeded": delayed_state.get(
            "recalled_commitment_code"
        ) == "gold-delayed-delta"
        and delayed_state.get("declared_losses") == []
        and delayed_state.get("unsupported_claims") == [],
        "final_declared_loss_cases": sorted(
            final_state.get("declared_loss_cases") or []
        ) == sorted(FAILURE_CASE_IDS),
        "final_successful_retrieval_cases": final_state.get(
            "successful_retrieval_cases"
        ) == ["delayed_retrieval"],
        "final_clean": final_state.get("cases_checked") == len(CASES)
        and sorted(final_state.get("declared_loss_cases") or [])
        == sorted(FAILURE_CASE_IDS)
        and final_state.get("successful_retrieval_cases") == ["delayed_retrieval"]
        and bool(final_state.get("declared_losses")),
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
        "no_unexpected_context_errors": len(summary.get("context_errors") or []) == 2,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "recall_states": recall_states,
        "final_state": final_state,
        "context_observations": context_observations,
        "expected_context_errors": expected_context_errors,
        "bridge_observations": bridge_obs,
    }


def postcondition_failures(success: JsonDict) -> list[JsonDict]:
    failures = []
    for check_name, passed in success.get("checks", {}).items():
        if passed:
            continue
        layer = "artifact"
        if "write_failure" in check_name:
            layer = "yanantin_write"
        elif "read_failure" in check_name:
            layer = "yanantin_retrieval"
        elif "partial" in check_name:
            layer = "partial_retrieval"
        elif "delayed" in check_name:
            layer = "delayed_retrieval"
        elif "declared_loss" in check_name:
            layer = "declared_memory_loss"
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


def collect_failures(paths: Any, records: list[JsonDict], success: JsonDict) -> list[JsonDict]:
    failures: list[JsonDict] = []
    if paths.failures_log.exists():
        failures.extend(
            json.loads(line)
            for line in paths.failures_log.read_text().splitlines()
            if line.strip()
        )
    failures.extend(
        record for record in records
        if record.get("record_type") == "failure_attribution"
    )
    failures.extend(postcondition_failures(success))
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
    bridge: DegradedPersistentBridge,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    success = required_success(summary, records, paths=paths, bridge=bridge)
    failures = collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    bridge.close()
    results = {
        "schema_version": "hamutay.phase_3b_degraded_memory_attribution.v1",
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
            backend = PatchedScriptedBackend(scripted_outputs())

    bridge = DegradedPersistentBridge(
        db_path=paths.output_root / DB_FILENAME,
        session_id=run_id,
        model=model,
    )
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
                    "event": "initialize_degraded_memory_attribution_probe",
                    "instruction": "Initialize durable state for a degraded-memory attribution probe.",
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
    source_record_ids: dict[str, str] = {}
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

    for case in CASES:
        LOCAL.set_clean_entity_state(session, seed_state, case)
        append_commitment(store, session, case, terminal_tool_choice, seed_record_id)
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
                extra={"stopped_after": f"commitment_{case['case_id']}"},
            )
        source_record_ids[case["case_id"]] = str(result["result_record_id"])
        LOCAL.commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after commitment {case['case_id']}"},
        )

    for case in CASES:
        LOCAL.set_clean_entity_state(session, seed_state, case)
        source_record_id = source_record_ids[case["case_id"]]
        append_recall(store, session, case, source_record_id, terminal_tool_choice)
        result = run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
            force_bridge_record_ids={source_record_id},
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
                extra={"stopped_after": f"recall_{case['case_id']}"},
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
            {"boundary": f"after recall {case['case_id']}"},
        )

    session._state = {
        "probe_status": seed_state.get("probe_status", "ready"),
        "case_ids": CASE_IDS,
        "open_items": [],
    }
    append_final(store, session, recall_record_ids, terminal_tool_choice)
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
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0 if result["classification"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
