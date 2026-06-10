"""Gate artifacts and no-token dry run for the first live autonomy pilot."""

from __future__ import annotations

import argparse
import json
import os
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx

from hamutay.events import EventStore
from hamutay.memory.action_application import AutonomousActionApplier
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.bridge import LocalMemorySubstrate
from hamutay.memory.rehearsal import (
    RehearsalInterrupted,
    RehearsalPaths,
    RestartableAutonomyRehearsal,
    reconstruct_rehearsal_report,
    run_fake_autonomy_rehearsal,
)
from hamutay.memory.restart_frontier import RestartFrontierStore


JsonDict = dict[str, Any]

PILOT_ID = "live_autonomy_pilot_20260609"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_PROVIDER = "openrouter"
DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1"
DEFAULT_OUTPUT_DIR = Path("experiments/live_autonomy_pilot_20260609/dry_run")
DEFAULT_RUN_ROOT = Path("experiments/live_autonomy_pilot_20260609/runs")
REQUIRED_FAILURE_LAYERS = {
    "model",
    "protocol",
    "harness",
    "substrate",
    "provider",
    "scorer",
    "restart_boundary",
    "sandbox",
}


@dataclass(frozen=True)
class PilotGateResult:
    """Result of evaluating one no-token pilot gate case."""

    case_id: str
    passed: bool
    report_path: Path
    report: JsonDict
    failures: list[JsonDict]

    def to_dict(self) -> JsonDict:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "report_path": str(self.report_path),
            "failures": deepcopy(self.failures),
            "report": deepcopy(self.report),
        }


@dataclass(frozen=True)
class ProviderActionResponse:
    """One provider response containing a model-authored action object."""

    action_object: JsonDict
    raw_content: str
    request_payload: JsonDict
    response_payload: JsonDict
    elapsed_seconds: float
    usage: JsonDict


class LivePilotFailure(RuntimeError):
    """A classified pilot failure that can be written as an outcome."""

    def __init__(
        self,
        *,
        layer: str,
        code: str,
        message: str,
        evidence: JsonDict | None = None,
    ) -> None:
        super().__init__(message)
        self.layer = layer
        self.code = code
        self.message = message
        self.evidence = deepcopy(evidence or {})

    def to_failure(self) -> JsonDict:
        return {
            "layer": self.layer,
            "code": self.code,
            "message": self.message,
            "evidence": deepcopy(self.evidence),
        }


class OpenRouterActionClient:
    """Minimal OpenAI-compatible client for the preregistered pilot model."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_action(
        self,
        *,
        messages: list[JsonDict],
        max_output_tokens: int,
    ) -> ProviderActionResponse:
        payload: JsonDict = {
            "model": self.model,
            "messages": deepcopy(messages),
            "max_tokens": int(max_output_tokens),
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "provider": {"allow_fallbacks": False},
            "transforms": [],
        }
        started = time.monotonic()
        try:
            response = httpx.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            elapsed = time.monotonic() - started
            response.raise_for_status()
            response_payload = response.json()
        except httpx.TimeoutException as exc:
            raise LivePilotFailure(
                layer="provider",
                code="provider_budget_or_timeout",
                message=str(exc),
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LivePilotFailure(
                layer="provider",
                code="provider_api_error",
                message=str(exc),
                evidence={
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text[:4000],
                },
            ) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LivePilotFailure(
                layer="provider",
                code="provider_api_error",
                message=str(exc),
            ) from exc

        content = _extract_openai_content(response_payload)
        try:
            action_object = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LivePilotFailure(
                layer="protocol",
                code="invalid_action_schema",
                message="provider content was not a JSON object",
                evidence={"raw_content": content[:4000]},
            ) from exc
        if not isinstance(action_object, dict):
            raise LivePilotFailure(
                layer="protocol",
                code="invalid_action_schema",
                message="provider JSON content was not an object",
                evidence={"raw_content": content[:4000]},
            )
        usage = response_payload.get("usage")
        return ProviderActionResponse(
            action_object=action_object,
            raw_content=content,
            request_payload=payload,
            response_payload=response_payload,
            elapsed_seconds=elapsed,
            usage=deepcopy(usage if isinstance(usage, dict) else {}),
        )


def sandbox_manifest(*, live_model_calls: bool = False) -> JsonDict:
    """Return the preregistered first-pilot sandbox posture."""

    return {
        "schema_version": "hamutay.autonomy_pilot_sandbox.v1",
        "pilot_id": PILOT_ID,
        "live_model_calls": live_model_calls,
        "enforcement_level": "in_process_detective",
        "enforcement_note": (
            "Disabled shell/network/filesystem entries mean those surfaces are "
            "not exposed through model-visible harness APIs. This is detective "
            "auditability, not OS-level containment."
        ),
        "filesystem": {
            "repo_access": "read_only_for_model",
            "allowed_write_roots": [
                "experiments/live_autonomy_pilot_20260609/runs/<run_id>",
            ],
            "model_direct_filesystem_access": False,
        },
        "tools": {
            "shell": "disabled",
            "network_tools": "disabled",
            "model_visible_tools": [
                "memory_action_object",
            ],
            "harness_only_tools": [
                "ActionLedger",
                "EventStore",
                "RestartFrontierStore",
                "LocalMemorySubstrate",
            ],
        },
        "secrets": {
            "model_can_read_environment": False,
            "redaction_policy": "default_preserve_non_secret_values",
            "api_key_source": "operator_environment_only",
        },
        "model": {
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
            "endpoint": DEFAULT_ENDPOINT,
            "endpoint_contract": "openai_compatible_chat_completions",
            "allow_fallbacks": False,
        },
        "audit_storage": {
            "action_ledger": "actions.jsonl",
            "event_log": "events.jsonl",
            "restart_frontier": "restart_frontier.jsonl",
            "memory_snapshot": "memory_snapshot.json",
            "tamper_evidence": "hash_chained_action_ledger",
        },
    }


def token_cycle_budget() -> JsonDict:
    """Return the preregistered budget for the first live run."""

    return {
        "schema_version": "hamutay.autonomy_pilot_budget.v1",
        "pilot_id": PILOT_ID,
        "max_cycles": 2,
        "max_scheduled_wakes": 1,
        "max_input_tokens_per_cycle": 8000,
        "max_output_tokens_per_cycle": 2000,
        "max_total_tokens": 20000,
        "max_wall_time_seconds": 600,
        "max_estimated_cost_usd": 1.00,
        "stop_conditions": [
            "policy_action.stop_complete",
            "budget.max_cycles",
            "unclassified_failure",
            "restart_frontier_unclean",
        ],
    }


def failure_taxonomy() -> JsonDict:
    """Return layer-classified failure vocabulary for the pilot gate."""

    entries = [
        (
            "model",
            "model_action_missing",
            "Model output did not contain a scoreable action object.",
        ),
        (
            "model",
            "model_policy_incoherent",
            "Model-authored policy action contradicts the artifact state.",
        ),
        (
            "protocol",
            "invalid_action_schema",
            "Action parsing or validation rejected required model output.",
        ),
        (
            "protocol",
            "tool_protocol_failure",
            "Provider/tool protocol returned malformed or unusable data.",
        ),
        (
            "harness",
            "invariant_failure",
            "Evaluator invariant failed on reconstructed artifacts.",
        ),
        (
            "harness",
            "hidden_inference_refused",
            "Harness refused an operation requiring hidden intent inference.",
        ),
        (
            "substrate",
            "action_ledger_verification_failed",
            "Hash-chain verification failed for the action ledger.",
        ),
        (
            "substrate",
            "memory_or_event_substrate_error",
            "Memory, event, or frontier substrate returned an operation error.",
        ),
        (
            "provider",
            "provider_api_error",
            "Remote model provider returned an API or transport error.",
        ),
        (
            "provider",
            "provider_budget_or_timeout",
            "Provider call exceeded timeout, token, or cost budget.",
        ),
        (
            "scorer",
            "report_unscoreable",
            "Evaluator cannot classify the run from preserved artifacts.",
        ),
        (
            "scorer",
            "scorer_internal_error",
            "Evaluator failed independently of model or substrate behavior.",
        ),
        (
            "restart_boundary",
            "restart_frontier_unclean",
            "Restart frontier contains uncommitted ledger records.",
        ),
        (
            "restart_boundary",
            "resume_recovery_failed",
            "Interrupted run did not recover or suppress events coherently.",
        ),
        (
            "sandbox",
            "sandbox_manifest_violation",
            "Observed run attempted an operation outside the manifest.",
        ),
    ]
    return {
        "schema_version": "hamutay.autonomy_failure_taxonomy.v1",
        "pilot_id": PILOT_ID,
        "required_layers": sorted(REQUIRED_FAILURE_LAYERS),
        "entries": [
            {"layer": layer, "code": code, "description": description}
            for layer, code, description in entries
        ],
    }


def classify_report_failures(report: JsonDict) -> list[JsonDict]:
    """Classify observable report failures by layer."""

    failures: list[JsonDict] = []
    ledger_verification = report.get("ledger_verification", {})
    if ledger_verification.get("ok") is not True:
        failures.append(
            {
                "layer": "substrate",
                "code": "action_ledger_verification_failed",
                "evidence": ledger_verification,
            }
        )
    ignored_count = int(report.get("ignored_ledger_count", 0) or 0)
    if ignored_count:
        failures.append(
            {
                "layer": "restart_boundary",
                "code": "restart_frontier_unclean",
                "evidence": {"ignored_ledger_count": ignored_count},
            }
        )
    for invariant in report.get("invariant_failures", []) or []:
        failures.append(
            {
                "layer": "harness",
                "code": "invariant_failure",
                "evidence": {"invariant": invariant},
            }
        )
    if int(report.get("action_trace_count", 0) or 0) < 2:
        failures.append(
            {
                "layer": "model",
                "code": "model_action_missing",
                "evidence": {
                    "action_trace_count": report.get("action_trace_count"),
                },
            }
        )
    invariants = report.get("invariants")
    if (
        isinstance(invariants, dict)
        and invariants.get("stop_policy_consistent_with_idle") is False
    ):
        failures.append(
            {
                "layer": "model",
                "code": "model_policy_incoherent",
                "evidence": {
                    "invariant": "stop_policy_consistent_with_idle",
                    "value": False,
                },
            }
        )
    return failures


def evaluate_pilot_report(report: JsonDict, *, case_id: str) -> JsonDict:
    """Evaluate one reconstructed pilot report against the dry-run gate."""

    failures = classify_report_failures(report)
    required_invariants = {
        "ledger_verified",
        "restart_frontier_clean",
        "closed_handle_had_prior_open_item",
        "stop_policy_consistent_with_idle",
        "event_reached_completed",
        "no_pending_or_running_events",
    }
    missing_invariants = sorted(
        required_invariants - set((report.get("invariants") or {}).keys())
    )
    if missing_invariants:
        failures.append(
            {
                "layer": "scorer",
                "code": "report_unscoreable",
                "evidence": {"missing_invariants": missing_invariants},
            }
        )
    return {
        "schema_version": "hamutay.autonomy_pilot_evaluation.v1",
        "pilot_id": PILOT_ID,
        "case_id": case_id,
        "passed": not failures,
        "failures": failures,
        "taxonomy_layers_available": sorted(_taxonomy_layers()),
        "required_layers_available": (
            _taxonomy_layers() >= REQUIRED_FAILURE_LAYERS
        ),
    }


def run_no_token_dry_run_gate(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> JsonDict:
    """Run the first-pilot dry gate without model/provider calls."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "sandbox_manifest.json", sandbox_manifest())
    _write_json(output / "token_cycle_budget.json", token_cycle_budget())
    _write_json(output / "failure_taxonomy.json", failure_taxonomy())

    clean = _run_clean_case(output / "clean_reconstruction")
    resumed = _run_resume_case(output / "resume_after_event_claim")
    cases = [clean, resumed]
    gate_report = {
        "schema_version": "hamutay.autonomy_pilot_dry_run_gate.v1",
        "pilot_id": PILOT_ID,
        "live_model_calls": False,
        "sandbox_manifest": str(output / "sandbox_manifest.json"),
        "token_cycle_budget": str(output / "token_cycle_budget.json"),
        "failure_taxonomy": str(output / "failure_taxonomy.json"),
        "case_count": len(cases),
        "cases": [case.to_dict() for case in cases],
        "passed": all(case.passed for case in cases),
    }
    _write_json(output / "dry_run_gate_report.json", gate_report)
    return gate_report


def execute_live_pilot(
    *,
    runs_root: str | Path = DEFAULT_RUN_ROOT,
    run_id: str | UUID | None = None,
    action_client: Any | None = None,
    api_key: str | None = None,
) -> JsonDict:
    """Execute the preregistered live pilot and preserve run artifacts."""

    _assert_dry_run_gate_passed()
    run_uuid = UUID(str(run_id)) if run_id is not None else uuid4()
    run_id_text = str(run_uuid)
    run_root = Path(runs_root) / run_id_text
    paths = RehearsalPaths.from_root(run_root)
    client = action_client or OpenRouterActionClient(
        api_key=api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
    )
    if isinstance(client, OpenRouterActionClient) and not client.api_key:
        result = _classified_failure_result(
            run_root=run_root,
            run_id=run_id_text,
            failure=LivePilotFailure(
                layer="provider",
                code="provider_api_error",
                message="OPENROUTER_API_KEY is required for live pilot execution",
            ),
        )
        return result

    _write_json(run_root / "sandbox_manifest.json", sandbox_manifest(live_model_calls=True))
    _write_json(run_root / "token_cycle_budget.json", token_cycle_budget())
    _write_json(run_root / "failure_taxonomy.json", failure_taxonomy())
    _write_json(
        run_root / "run_manifest.json",
        {
            "schema_version": "hamutay.live_autonomy_pilot_run.v1",
            "pilot_id": PILOT_ID,
            "run_id": run_id_text,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "preregistration": (
                "experiments/live_autonomy_pilot_20260609/PRE_REGISTRATION.md"
            ),
            "model": sandbox_manifest(live_model_calls=True)["model"],
            "budget": token_cycle_budget(),
            "sandbox": sandbox_manifest(live_model_calls=True),
        },
    )
    try:
        runner = LiveAutonomyPilotRunner(
            paths=paths,
            run_id=run_uuid,
            action_client=client,
        )
        report = runner.run()
        evaluation = evaluate_pilot_report(report, case_id="live_pilot")
        result = {
            "schema_version": "hamutay.live_autonomy_pilot_result.v1",
            "pilot_id": PILOT_ID,
            "run_id": run_id_text,
            "passed": bool(evaluation["passed"]),
            "outcome_layer": "passed" if evaluation["passed"] else (
                evaluation["failures"][0]["layer"]
                if evaluation["failures"] else "scorer"
            ),
            "failures": evaluation["failures"],
            "report_path": str(run_root / "reconstructed_report.json"),
            "evaluation_path": str(run_root / "evaluation.json"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_json(run_root / "reconstructed_report.json", report)
        _write_json(run_root / "evaluation.json", evaluation)
        _write_json(run_root / "run_result.json", result)
        return result
    except LivePilotFailure as exc:
        return _classified_failure_result(
            run_root=run_root,
            run_id=run_id_text,
            failure=exc,
        )


class LiveAutonomyPilotRunner:
    """Run the two-cycle live pilot through the audited harness."""

    def __init__(
        self,
        *,
        paths: RehearsalPaths,
        run_id: UUID,
        action_client: Any,
    ) -> None:
        self.paths = paths
        self.run_id = run_id
        self.action_client = action_client
        self.budget = token_cycle_budget()
        self.total_tokens = 0

    def run(self) -> JsonDict:
        memory, ledger, event_store, frontier_store, load = self._load()
        if load.frontier is None:
            frontier_store.ensure_run_manifest(
                ledger=ledger,
                run_id=str(self.run_id),
                manifest={
                    "pilot_id": PILOT_ID,
                    "model": DEFAULT_MODEL,
                    "provider": DEFAULT_PROVIDER,
                    "live_model_calls": True,
                },
                sandbox=sandbox_manifest(live_model_calls=True),
            )
            frontier_store.commit_frontier(
                run_id=str(self.run_id),
                cycle_id=0,
                result_record_id=None,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                notes={"boundary": "initial_live_pilot"},
            )
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        if load.frontier.next_cycle_id <= 1:
            self._run_seed_cycle(memory, ledger, event_store, frontier_store)
            memory, ledger, event_store, frontier_store, load = self._load()

        assert load.frontier is not None
        if load.frontier.next_cycle_id <= 2:
            self._run_wake_cycle(memory, ledger, event_store, frontier_store)

        return reconstruct_rehearsal_report(self.paths, run_id=str(self.run_id))

    def _run_seed_cycle(
        self,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
    ) -> None:
        result_record_id = _live_cycle_record_id(self.run_id, 1)
        provider = self._call_model(
            cycle_id=1,
            ledger=ledger,
            messages=_seed_messages(result_record_id=result_record_id),
        )
        trace = parse_autonomous_action(provider.action_object).to_dict()
        _require_trace_actions(trace, {"open_item", "schedule_request"})
        applier = self._applier(memory=memory, ledger=ledger, event_store=event_store)
        result = applier.apply_trace(
            trace,
            run_id=str(self.run_id),
            cycle_id=1,
            result_record_id=result_record_id,
        )
        if result.status != "applied":
            raise LivePilotFailure(
                layer="harness",
                code="hidden_inference_refused",
                message="seed action did not apply cleanly",
                evidence=result.to_dict(),
            )
        frontier_store.commit_frontier(
            run_id=str(self.run_id),
            cycle_id=1,
            result_record_id=result.result_record_id,
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            notes={"boundary": "after_live_seed_cycle"},
        )

    def _run_wake_cycle(
        self,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
        frontier_store: RestartFrontierStore,
    ) -> None:
        claimed = event_store.claim_next_pending(run_id=self.run_id)
        if claimed is None:
            raise LivePilotFailure(
                layer="model",
                code="model_action_missing",
                message="seed cycle did not produce a runnable scheduled wake",
            )
        event, running = claimed
        if running.get("status") != "running":
            raise LivePilotFailure(
                layer="substrate",
                code="memory_or_event_substrate_error",
                message="event claim did not produce a running event",
                evidence={"running": running},
            )
        open_items = memory.open_items(reason="live pilot wake target selection")
        if not open_items.ok:
            event_store.append_failed(event=event, run_id=str(self.run_id), exc=RuntimeError("open_items failed"))
            raise LivePilotFailure(
                layer="substrate",
                code="memory_or_event_substrate_error",
                message="open_items failed during wake cycle",
                evidence=open_items.to_dict(),
            )
        items = open_items.data.get("items", [])
        if len(items) != 1:
            event_store.append_failed(event=event, run_id=str(self.run_id), exc=RuntimeError("unexpected open item count"))
            raise LivePilotFailure(
                layer="model",
                code="model_policy_incoherent",
                message="wake cycle expected exactly one open item",
                evidence={"open_items": items},
            )
        result_record_id = _live_cycle_record_id(self.run_id, 2)
        provider = self._call_model(
            cycle_id=2,
            ledger=ledger,
            messages=_wake_messages(event=event, open_item=items[0]),
        )
        trace = parse_autonomous_action(provider.action_object).to_dict()
        _require_trace_actions(trace, {"closure", "policy_action"})
        applier = self._applier(memory=memory, ledger=ledger, event_store=event_store)
        result = applier.apply_trace(
            trace,
            run_id=str(self.run_id),
            cycle_id=2,
            result_record_id=result_record_id,
            event=event,
        )
        if result.status != "applied":
            event_store.append_failed(event=event, run_id=str(self.run_id), exc=RuntimeError("wake action did not apply cleanly"))
            raise LivePilotFailure(
                layer="harness",
                code="hidden_inference_refused",
                message="wake action did not apply cleanly",
                evidence=result.to_dict(),
            )
        completed = event_store.append_completed(
            event=event,
            run_id=str(self.run_id),
            wake_cycle=2,
            result_record_id=UUID(str(result.result_record_id)),
            response_text=str(provider.action_object.get("response", "")),
            context_results=[{"source": "open_items", "items": items}],
        )
        ledger.append_operation(
            run_id=str(self.run_id),
            cycle_id=2,
            operation_id="cycle-2:complete-live-pilot-event",
            operation_type="complete_live_pilot_event",
            actor="scheduler",
            raw_parameters={"event": event},
            validated_parameters={"completed_event_id": event["event_id"]},
            reason="live pilot scheduled wake completed",
            precondition_checks=[
                {"name": "event_claimed_running", "ok": True},
            ],
            result_status="applied",
            result={"completed": completed},
            created_records=[
                {
                    "record_type": "event_status",
                    "event_id": completed["event_id"],
                    "status": "completed",
                }
            ],
        )
        frontier_store.commit_frontier(
            run_id=str(self.run_id),
            cycle_id=2,
            result_record_id=result.result_record_id,
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            notes={"boundary": "after_live_wake_cycle"},
        )

    def _call_model(
        self,
        *,
        cycle_id: int,
        ledger: ActionLedger,
        messages: list[JsonDict],
    ) -> ProviderActionResponse:
        try:
            response = self.action_client.generate_action(
                messages=messages,
                max_output_tokens=int(self.budget["max_output_tokens_per_cycle"]),
            )
        except LivePilotFailure as exc:
            ledger.append_operation(
                run_id=str(self.run_id),
                cycle_id=cycle_id,
                operation_id=f"cycle-{cycle_id}:live-model-call",
                operation_type="live_model_call",
                actor="provider",
                raw_parameters={"messages": messages},
                validated_parameters={"model": DEFAULT_MODEL},
                reason="live pilot model action request",
                precondition_checks=[
                    {"name": "live_model_calls_enabled", "ok": True},
                ],
                result_status="failed",
                result={"applied": False},
                error={
                    "layer": exc.layer,
                    "code": exc.code,
                    "message": exc.message,
                },
            )
            raise
        self.total_tokens += int(response.usage.get("total_tokens", 0) or 0)
        _write_json(
            self.paths.root / f"cycle_{cycle_id:02d}_provider_request.json",
            response.request_payload,
        )
        _write_json(
            self.paths.root / f"cycle_{cycle_id:02d}_provider_response.json",
            response.response_payload,
        )
        ledger.append_operation(
            run_id=str(self.run_id),
            cycle_id=cycle_id,
            operation_id=f"cycle-{cycle_id}:live-model-call",
            operation_type="live_model_call",
            actor="provider",
            raw_parameters={"request_path": f"cycle_{cycle_id:02d}_provider_request.json"},
            validated_parameters={
                "model": DEFAULT_MODEL,
                "max_output_tokens": self.budget["max_output_tokens_per_cycle"],
            },
            reason="live pilot model action request",
            precondition_checks=[
                {"name": "live_model_calls_enabled", "ok": True},
                {
                    "name": "total_token_budget_not_exceeded",
                    "ok": self.total_tokens <= int(self.budget["max_total_tokens"]),
                },
            ],
            result_status="applied",
            result={
                "response_path": f"cycle_{cycle_id:02d}_provider_response.json",
                "elapsed_seconds": response.elapsed_seconds,
                "usage": response.usage,
                "total_tokens_so_far": self.total_tokens,
            },
        )
        if self.total_tokens > int(self.budget["max_total_tokens"]):
            raise LivePilotFailure(
                layer="provider",
                code="provider_budget_or_timeout",
                message="live pilot exceeded total token budget",
                evidence={"total_tokens": self.total_tokens},
            )
        return response

    def _load(
        self,
    ) -> tuple[
        LocalMemorySubstrate,
        ActionLedger,
        EventStore,
        RestartFrontierStore,
        Any,
    ]:
        memory = LocalMemorySubstrate()
        ledger = ActionLedger(self.paths.ledger_path)
        event_store = EventStore(self.paths.event_path)
        frontier_store = RestartFrontierStore(
            frontier_path=self.paths.frontier_path,
            memory_snapshot_path=self.paths.memory_snapshot_path,
        )
        load = frontier_store.load_latest(
            run_id=str(self.run_id),
            memory=memory,
            ledger=ledger,
            event_store=event_store,
        )
        return memory, ledger, event_store, frontier_store, load

    @staticmethod
    def _applier(
        *,
        memory: LocalMemorySubstrate,
        ledger: ActionLedger,
        event_store: EventStore,
    ) -> AutonomousActionApplier:
        return AutonomousActionApplier(
            memory=memory,
            ledger=ledger,
            event_store=event_store,
            instance_id="live-autonomy-pilot",
        )


def _run_clean_case(root: Path) -> PilotGateResult:
    result = run_fake_autonomy_rehearsal(output_dir=root)
    report = result.to_dict()
    report_path = root / "reconstructed_report.json"
    _write_json(report_path, report)
    evaluation = evaluate_pilot_report(report, case_id="clean_reconstruction")
    _write_json(root / "evaluation.json", evaluation)
    return PilotGateResult(
        case_id="clean_reconstruction",
        passed=bool(evaluation["passed"]),
        report_path=report_path,
        report=report,
        failures=deepcopy(evaluation["failures"]),
    )


def _run_resume_case(root: Path) -> PilotGateResult:
    paths = RehearsalPaths.from_root(root)
    runner = RestartableAutonomyRehearsal(paths=paths)
    try:
        runner.run(interrupt_after="after_event_claim")
    except RehearsalInterrupted:
        pass
    report = RestartableAutonomyRehearsal(paths=paths).run().to_dict()
    report_path = root / "reconstructed_report.json"
    _write_json(report_path, report)
    evaluation = evaluate_pilot_report(report, case_id="resume_after_event_claim")
    if not _has_running_to_pending_recovery(report):
        evaluation["passed"] = False
        evaluation["failures"].append(
            {
                "layer": "restart_boundary",
                "code": "resume_recovery_failed",
                "evidence": {
                    "recovered_event_count": report.get(
                        "recovered_event_count"
                    ),
                    "event_statuses": report.get("event_statuses", []),
                },
            }
        )
    _write_json(root / "evaluation.json", evaluation)
    return PilotGateResult(
        case_id="resume_after_event_claim",
        passed=bool(evaluation["passed"]),
        report_path=report_path,
        report=report,
        failures=deepcopy(evaluation["failures"]),
    )


def _extract_openai_content(response_payload: JsonDict) -> str:
    try:
        message = response_payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LivePilotFailure(
            layer="provider",
            code="provider_api_error",
            message="provider response did not contain choices[0].message",
            evidence={"response": response_payload},
        ) from exc
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
        ]
        joined = "".join(parts).strip()
        if joined:
            return joined
    raise LivePilotFailure(
        layer="provider",
        code="provider_api_error",
        message="provider response did not contain text content",
        evidence={"message": message},
    )


def _assert_dry_run_gate_passed() -> None:
    gate_path = Path("experiments/live_autonomy_pilot_20260609/dry_run/dry_run_gate_report.json")
    try:
        gate = json.loads(gate_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise LivePilotFailure(
            layer="scorer",
            code="report_unscoreable",
            message="dry-run gate report could not be read",
            evidence={"path": str(gate_path)},
        ) from exc
    if gate.get("passed") is not True or gate.get("live_model_calls") is not False:
        raise LivePilotFailure(
            layer="scorer",
            code="report_unscoreable",
            message="dry-run gate has not passed; live pilot is not eligible",
            evidence={"path": str(gate_path), "gate": gate},
        )


def _classified_failure_result(
    *,
    run_root: Path,
    run_id: str,
    failure: LivePilotFailure,
) -> JsonDict:
    run_root.mkdir(parents=True, exist_ok=True)
    _write_json(run_root / "sandbox_manifest.json", sandbox_manifest(live_model_calls=True))
    _write_json(run_root / "token_cycle_budget.json", token_cycle_budget())
    _write_json(run_root / "failure_taxonomy.json", failure_taxonomy())
    evaluation = {
        "schema_version": "hamutay.autonomy_pilot_evaluation.v1",
        "pilot_id": PILOT_ID,
        "case_id": "live_pilot",
        "passed": False,
        "failures": [failure.to_failure()],
        "taxonomy_layers_available": sorted(_taxonomy_layers()),
        "required_layers_available": (
            _taxonomy_layers() >= REQUIRED_FAILURE_LAYERS
        ),
    }
    result = {
        "schema_version": "hamutay.live_autonomy_pilot_result.v1",
        "pilot_id": PILOT_ID,
        "run_id": run_id,
        "passed": False,
        "outcome_layer": failure.layer,
        "failures": [failure.to_failure()],
        "evaluation_path": str(run_root / "evaluation.json"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(run_root / "evaluation.json", evaluation)
    _write_json(run_root / "run_result.json", result)
    return result


def _live_cycle_record_id(run_id: UUID, cycle_id: int) -> UUID:
    return uuid5(NAMESPACE_URL, f"hamutay:{PILOT_ID}:{run_id}:cycle:{cycle_id}")


def _require_trace_actions(trace: JsonDict, required: set[str]) -> None:
    if trace.get("validation_status") == "rejected":
        raise LivePilotFailure(
            layer="protocol",
            code="invalid_action_schema",
            message="model action object was rejected by parser",
            evidence={"trace": trace},
        )
    accepted_types = {
        action.get("action_type")
        for action in trace.get("accepted_actions", [])
    }
    missing = sorted(required - accepted_types)
    if missing:
        raise LivePilotFailure(
            layer="model",
            code="model_action_missing",
            message="model action object omitted required actions",
            evidence={"missing_action_types": missing, "trace": trace},
        )


def _seed_messages(*, result_record_id: UUID) -> list[JsonDict]:
    return [
        {
            "role": "system",
            "content": _action_object_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "Seed wake for the first tiny live autonomy pilot.\n"
                "Task: identify exactly one bounded follow-up item, preserve it "
                "as an open item, and schedule exactly one wake to resolve it.\n"
                "Use this recall target in the scheduled wake requested_context: "
                f"{result_record_id}.\n"
                "Return one JSON object with response, open_items, and "
                "schedule_requests. Do not include policy_action on this cycle."
            ),
        },
    ]


def _wake_messages(*, event: JsonDict, open_item: JsonDict) -> list[JsonDict]:
    return [
        {
            "role": "system",
            "content": _action_object_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "Scheduled wake for the first tiny live autonomy pilot.\n"
                "The harness resolved the pending event and found exactly one "
                "open item. If the item is resolved by acknowledging this "
                "bounded pilot wake, close the exact target_handle and emit "
                "policy_action \"stop_complete\".\n"
                f"Source event:\n{json.dumps(event, sort_keys=True)}\n"
                f"Open item:\n{json.dumps(open_item, sort_keys=True)}\n"
                "Return one JSON object with response, closures, and "
                "policy_action."
            ),
        },
    ]


def _action_object_system_prompt() -> str:
    return (
        "You produce a single JSON object for the Hamutay audited autonomy "
        "harness. Return only JSON, with no markdown or prose outside the "
        "object. The object must always include a non-empty string response. "
        "Allowed fields are response, open_items, closures, schedule_requests, "
        "policy_action, declared_losses, uncertainty, abandonment_reason, and "
        "defer_reason. Open items are JSON objects. Closure objects must use "
        "the exact target_handle supplied by the harness and include status "
        "and basis. Schedule requests must include purpose and requested_context; "
        "requested_context entries may use {\"tool\":\"recall\",\"record_id\":"
        "\"...\"}. Policy action vocabulary is stop_complete, continue_after, "
        "ask_external_evidence, abandon, or defer."
    )


def _has_running_to_pending_recovery(report: JsonDict) -> bool:
    statuses_by_event: dict[str, list[str]] = {}
    for item in report.get("event_statuses", []):
        if item.get("record_type") != "event_status":
            continue
        event_id = item.get("event_id")
        status = item.get("status")
        if event_id is None or status is None:
            continue
        statuses_by_event.setdefault(str(event_id), []).append(str(status))
    return any(
        current == "running" and next_status == "pending"
        for statuses in statuses_by_event.values()
        for current, next_status in zip(statuses, statuses[1:])
    )


def _taxonomy_layers() -> set[str]:
    return {
        str(entry["layer"])
        for entry in failure_taxonomy()["entries"]
    }


def _write_json(path: Path, payload: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the no-token gate for the first live autonomy pilot."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for dry-run artifacts.",
    )
    parser.add_argument(
        "--run-live",
        action="store_true",
        help="Execute the preregistered live pilot instead of the dry-run gate.",
    )
    parser.add_argument(
        "--runs-root",
        default=str(DEFAULT_RUN_ROOT),
        help="Directory under which live run artifacts are written.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional UUID run id for live execution.",
    )
    args = parser.parse_args()
    if args.run_live:
        print(
            json.dumps(
                execute_live_pilot(
                    runs_root=args.runs_root,
                    run_id=args.run_id,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(
        json.dumps(
            run_no_token_dry_run_gate(args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
