"""Goal 6 less-scaffolded bounded investigation panel.

This runner is intentionally experiment-local. It reuses the hardened
autonomous action parser, tamper-evident ledger, event store, memory substrate,
and restart frontier, while keeping the live provider transport and scorer
preregistered with the experiment artifact.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from hamutay.events import EventStore, build_pending_event, utc_now_iso
from hamutay.memory.action_application import AutonomousActionApplier
from hamutay.memory.action_ledger import ActionLedger
from hamutay.memory.actions import parse_autonomous_action
from hamutay.memory.bridge import JsonDict, LocalMemorySubstrate
from hamutay.memory.live_pilot import _action_object_system_prompt, sandbox_manifest
from hamutay.memory.rehearsal import RehearsalPaths, reconstruct_rehearsal_report
from hamutay.memory.restart_frontier import RestartFrontierStore


EXPERIMENT_ID = "less_scaffolded_bounded_investigation_20260612"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_ROW_IDS = ("g6_r01", "g6_r02", "g6_r03")
DEFAULT_MAX_CYCLES = 2
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 529}

DOMAIN_BRIEF = {
    "domain": "Hamutuay audited event-loop research",
    "available_axes": [
        "event-loop scheduler and restart frontier behavior",
        "action/artifact coherence",
        "evidence handling and declared losses",
        "working-set and recall accounting",
        "auditability and failure attribution",
    ],
    "boundary": (
        "Choose or materially shape one bounded investigation inside this "
        "domain. The harness is not supplying a menu of exact targets."
    ),
    "losses": [
        "No external repository search is available to the model in this wake.",
        "The memory substrate is the bounded local substitute used by this panel.",
    ],
}


class PanelFailure(RuntimeError):
    """Classified experiment failure that should not be charged blindly."""

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

    def to_dict(self) -> JsonDict:
        return {
            "layer": self.layer,
            "code": self.code,
            "message": self.message,
            "evidence": deepcopy(self.evidence),
        }


@dataclass(frozen=True)
class ProviderResult:
    action_object: JsonDict
    raw_content: str
    request_payload: JsonDict
    response_payload: JsonDict
    attempts: list[JsonDict]
    elapsed_seconds: float
    usage: JsonDict


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _uuid(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"hamutay:{EXPERIMENT_ID}:{label}")


def _row_run_id(row_id: str) -> str:
    return str(_uuid(f"{row_id}:run"))


def _cycle_record_id(row_id: str, cycle_id: int) -> UUID:
    return _uuid(f"{row_id}:cycle:{cycle_id}:record")


def _domain_record_id(row_id: str) -> UUID:
    return _uuid(f"{row_id}:domain-brief")


def _paths(row_root: Path) -> RehearsalPaths:
    return RehearsalPaths.from_root(row_root / "run")


def _extract_openai_content(payload: JsonDict) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PanelFailure(
            layer="protocol_transport",
            code="missing_openai_content",
            message="OpenAI-compatible response did not contain choices[0].message.content",
            evidence={"response_payload": payload},
        ) from exc
    if not isinstance(content, str) or not content.strip():
        raise PanelFailure(
            layer="protocol_transport",
            code="empty_openai_content",
            message="OpenAI-compatible response content was empty",
            evidence={"response_payload": payload},
        )
    return content


def call_openai_compatible_action(
    *,
    api_key: str,
    endpoint: str,
    model: str,
    messages: list[JsonDict],
    max_tokens: int | None = None,
    timeout_seconds: float = 180.0,
    max_attempts: int = 3,
) -> ProviderResult:
    """Call an OpenAI-compatible endpoint without imposing an output cap."""

    payload: JsonDict = {
        "model": model,
        "messages": deepcopy(messages),
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)

    url = endpoint.rstrip("/") + "/chat/completions"
    attempts: list[JsonDict] = []
    started = time.monotonic()
    last_error: JsonDict | None = None
    for attempt_index in range(1, max_attempts + 1):
        attempt_started = time.monotonic()
        try:
            response = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_seconds,
            )
            elapsed = time.monotonic() - attempt_started
            attempt = {
                "attempt": attempt_index,
                "elapsed_seconds": elapsed,
                "status_code": response.status_code,
                "response_text_prefix": response.text[:4000],
            }
            attempts.append(attempt)
            if (
                response.status_code in TRANSIENT_STATUS_CODES
                and attempt_index < max_attempts
            ):
                time.sleep(min(2 ** (attempt_index - 1), 8))
                continue
            response.raise_for_status()
            response_payload = response.json()
            content = _extract_openai_content(response_payload)
            try:
                action_object = json.loads(content)
            except json.JSONDecodeError as exc:
                raise PanelFailure(
                    layer="protocol_transport",
                    code="primary_content_not_json_object",
                    message="Provider content was not a strict JSON object",
                    evidence={"raw_content": content[:4000], "attempts": attempts},
                ) from exc
            if not isinstance(action_object, dict):
                raise PanelFailure(
                    layer="protocol_transport",
                    code="primary_content_not_json_object",
                    message="Provider JSON content was not an object",
                    evidence={"raw_content": content[:4000], "attempts": attempts},
                )
            usage = response_payload.get("usage")
            return ProviderResult(
                action_object=action_object,
                raw_content=content,
                request_payload=payload,
                response_payload=response_payload,
                attempts=attempts,
                elapsed_seconds=time.monotonic() - started,
                usage=deepcopy(usage if isinstance(usage, dict) else {}),
            )
        except httpx.HTTPStatusError as exc:
            last_error = {
                "status_code": exc.response.status_code,
                "response_text": exc.response.text[:4000],
                "attempts": attempts,
            }
            if (
                exc.response.status_code in TRANSIENT_STATUS_CODES
                and attempt_index < max_attempts
            ):
                time.sleep(min(2 ** (attempt_index - 1), 8))
                continue
            break
        except httpx.TimeoutException as exc:
            last_error = {"error": str(exc), "attempts": attempts}
            if attempt_index < max_attempts:
                time.sleep(min(2 ** (attempt_index - 1), 8))
                continue
            break
        except httpx.HTTPError as exc:
            last_error = {"error": str(exc), "attempts": attempts}
            break

    raise PanelFailure(
        layer="provider",
        code="provider_api_error",
        message="OpenAI-compatible provider call failed",
        evidence=last_error or {"attempts": attempts},
    )


def _system_prompt() -> str:
    return _action_object_system_prompt() + (
        " This Goal 6 panel is less-scaffolded: the harness gives a bounded "
        "domain, not an exact target. Your response must make the selected "
        "bounded investigation visible in the response and/or open_items. "
        "Do not claim completion if your own artifact says required evidence "
        "is missing. If you continue, include schedule_requests and "
        "policy_action \"continue_after\" in the same object."
    )


def _messages(
    *,
    row_id: str,
    cycle_id: int,
    event: JsonDict,
    context_results: list[JsonDict],
    open_items: list[JsonDict],
    result_record_id: UUID,
) -> list[JsonDict]:
    if cycle_id == 1:
        task = (
            "First wake for Goal 6: choose or materially shape one bounded "
            "investigation inside the supplied Hamutay event-loop research "
            "domain. Do not pick from a menu; no exact target has been supplied. "
            "Produce an inspectable artifact in response. If more work is "
            "needed, create open_items and one schedule_requests entry whose "
            f"requested_context recalls this cycle record id: {result_record_id}. "
            "Then set policy_action to continue_after. If the bounded artifact "
            "is complete, set policy_action to stop_complete. If evidence is "
            "missing, set ask_external_evidence and declare the gap. If the "
            "work should wait or is no longer viable, use defer or abandon."
        )
    else:
        task = (
            "Scheduled continuation wake for Goal 6. Use the resolved context "
            "and available open items. Close exact target_handle values only "
            "when the item is genuinely resolved. Choose stop_complete, "
            "continue_after, ask_external_evidence, defer, or abandon based "
            "on the artifact you can actually support."
        )
    visible = {
        "experiment_id": EXPERIMENT_ID,
        "row_id": row_id,
        "cycle_id": cycle_id,
        "source_event": event,
        "resolved_context": context_results,
        "available_open_items": open_items,
        "next_result_record_id": str(result_record_id),
        "permitted_policy_actions": [
            "stop_complete",
            "continue_after",
            "ask_external_evidence",
            "defer",
            "abandon",
        ],
        "task": task,
    }
    return [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": json.dumps(visible, indent=2, sort_keys=True)},
    ]


def _resolve_context(
    *,
    memory: LocalMemorySubstrate,
    ledger: ActionLedger,
    run_id: str,
    cycle_id: int,
    event: JsonDict,
) -> list[JsonDict]:
    results: list[JsonDict] = []
    for index, request in enumerate(event.get("requested_context", [])):
        if request.get("tool") == "recall":
            record_id = request.get("record_id")
            if record_id is None:
                result = memory.recall(
                    record_id=_cycle_record_id(str(request.get("cycle")), 1),
                    reason={"event_id": event.get("event_id"), "request": request},
                )
            else:
                result = memory.recall(
                    record_id=record_id,
                    field=request.get("field"),
                    reason={"event_id": event.get("event_id"), "request": request},
                )
        else:
            result = memory.walk(
                from_record_id=request.get("from_record_id"),
                direction=request.get("direction", "both"),
                depth=int(request.get("depth", 1)),
                reason={"event_id": event.get("event_id"), "request": request},
            )
        payload = {
            "request_index": index,
            "request": deepcopy(request),
            "result": result.to_dict(),
        }
        ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=event.get("event_id"),
            operation_id=f"cycle-{cycle_id}:resolve-context:{index}",
            operation_type=f"memory_{request.get('tool')}",
            actor="memory",
            raw_parameters={"request": request},
            validated_parameters={"request": request},
            reason="resolve model-requested wake context",
            precondition_checks=[{"name": "event_claimed_running", "ok": True}],
            result_status="applied" if result.ok else "failed",
            result=result.to_dict(),
            error=None if result.ok else result.to_dict().get("error"),
        )
        results.append(payload)
    return results


def _open_items_for_wake(
    *,
    memory: LocalMemorySubstrate,
    ledger: ActionLedger,
    run_id: str,
    cycle_id: int,
    event: JsonDict,
) -> list[JsonDict]:
    response = memory.open_items(
        reason={"event_id": event.get("event_id"), "cycle_id": cycle_id}
    )
    ledger.append_operation(
        run_id=run_id,
        cycle_id=cycle_id,
        wake_id=event.get("event_id"),
        operation_id=f"cycle-{cycle_id}:memory-open-items",
        operation_type="memory_open_items",
        actor="memory",
        raw_parameters={"reason": "model wake target selection"},
        validated_parameters={"reason": "model wake target selection"},
        reason="surface currently open work to model",
        precondition_checks=[{"name": "event_claimed_running", "ok": True}],
        result_status="applied" if response.ok else "failed",
        result=response.to_dict(),
        error=None if response.ok else response.to_dict().get("error"),
    )
    if not response.ok:
        return []
    items = response.data.get("items")
    return deepcopy(items if isinstance(items, list) else [])


def _initialize_row(
    *,
    row_id: str,
    paths: RehearsalPaths,
    run_id: str,
) -> tuple[LocalMemorySubstrate, ActionLedger, EventStore, RestartFrontierStore]:
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths.ledger_path)
    event_store = EventStore(paths.event_path)
    frontier_store = RestartFrontierStore(
        frontier_path=paths.frontier_path,
        memory_snapshot_path=paths.memory_snapshot_path,
    )
    frontier_store.ensure_run_manifest(
        ledger=ledger,
        run_id=run_id,
        manifest={
            "experiment_id": EXPERIMENT_ID,
            "row_id": row_id,
            "model": DEFAULT_MODEL,
            "live_model_calls": True,
            "exact_target_supplied": False,
            "max_cycles_per_row": DEFAULT_MAX_CYCLES,
        },
        sandbox=sandbox_manifest(live_model_calls=True),
    )
    domain_id = _domain_record_id(row_id)
    domain_response = memory.store_episode(
        record_id=domain_id,
        record_type="goal6_domain_brief",
        content=deepcopy(DOMAIN_BRIEF),
        production={
            "who": {"instance": "goal6-harness"},
            "what": {"artifact": "bounded_domain_brief"},
            "when": {"cycle": 0},
            "where": {"project": "hamutay"},
        },
        execution_trace={
            "experiment_id": EXPERIMENT_ID,
            "row_id": row_id,
            "source": "preregistered_domain",
        },
    )
    ledger.append_operation(
        run_id=run_id,
        cycle_id=0,
        operation_id="cycle-0:store-domain-brief",
        operation_type="store_domain_brief",
        actor="harness",
        raw_parameters={"record_id": str(domain_id), "content": DOMAIN_BRIEF},
        validated_parameters={"record_id": str(domain_id)},
        reason="provide bounded domain without exact investigation target",
        precondition_checks=[{"name": "domain_has_no_exact_target", "ok": True}],
        result_status="applied" if domain_response.ok else "failed",
        result=domain_response.to_dict(),
        error=None if domain_response.ok else domain_response.to_dict().get("error"),
        created_records=[{"record_type": "memory_record", "record_id": str(domain_id)}],
    )
    initial_event = build_pending_event(
        purpose="Goal 6 less-scaffolded bounded investigation wake",
        requested_context=[{"tool": "recall", "record_id": str(domain_id)}],
        scheduled_by_cycle=0,
        scheduled_by_record_id=domain_id,
        label=f"{EXPERIMENT_ID}:{row_id}:initial",
    )
    op = ledger.append_operation(
        run_id=run_id,
        cycle_id=0,
        operation_id="cycle-0:create-initial-event",
        operation_type="create_initial_event",
        actor="scheduler",
        raw_parameters={"event": initial_event},
        validated_parameters={"event": initial_event},
        reason="start less-scaffolded bounded investigation panel row",
        precondition_checks=[{"name": "domain_record_committed", "ok": domain_response.ok}],
        result_status="applied",
        result={"event": initial_event},
        created_records=[
            {"record_type": "event_status", "event_id": initial_event["event_id"]}
        ],
    )
    initial_event["audit_ledger_sequence"] = op["sequence"]
    initial_event["audit_ledger_record_hash"] = op["record_hash"]
    event_store.append(initial_event)
    frontier_store.commit_frontier(
        run_id=run_id,
        cycle_id=0,
        result_record_id=str(domain_id),
        memory=memory,
        ledger=ledger,
        event_store=event_store,
        notes={"boundary": "after domain brief and initial event"},
    )
    return memory, ledger, event_store, frontier_store


def _reload_row(
    paths: RehearsalPaths,
    run_id: str,
) -> tuple[LocalMemorySubstrate, ActionLedger, EventStore, RestartFrontierStore]:
    memory = LocalMemorySubstrate()
    ledger = ActionLedger(paths.ledger_path)
    event_store = EventStore(paths.event_path)
    frontier_store = RestartFrontierStore(
        frontier_path=paths.frontier_path,
        memory_snapshot_path=paths.memory_snapshot_path,
    )
    frontier_store.load_latest(
        run_id=run_id,
        memory=memory,
        ledger=ledger,
        event_store=event_store,
    )
    return memory, ledger, event_store, frontier_store


def dry_action(
    *,
    row_id: str,
    cycle_id: int,
    result_record_id: UUID,
    open_items: list[JsonDict],
) -> JsonDict:
    if row_id == "g6_r01":
        return {
            "response": (
                "I selected a bounded investigation: check whether the audit "
                "restart boundary makes action/artifact consistency visible "
                "without requiring a wall clock. The artifact is a concise "
                "finding: the current trace requirements are sufficient for a "
                "small DES-only row, with the loss that no live external "
                "memory substrate was tested."
            ),
            "declared_losses": ["No live Yanantin memory adapter was exercised."],
            "policy_action": "stop_complete",
        }
    if row_id == "g6_r02" and cycle_id == 1:
        return {
            "response": (
                "I shaped the investigation around whether a continuation wake "
                "can preserve a self-chosen open item and then close it from "
                "recalled context."
            ),
            "open_items": [
                {
                    "kind": "todo",
                    "text": "revisit recalled cycle one artifact and close the bounded continuity item",
                }
            ],
            "schedule_requests": [
                {
                    "purpose": "resume the model-shaped continuity item",
                    "requested_context": [
                        {"tool": "recall", "record_id": str(result_record_id)}
                    ],
                }
            ],
            "policy_action": "continue_after",
        }
    if row_id == "g6_r02":
        handle = open_items[0]["handle"] if open_items else {}
        return {
            "response": (
                "The recalled cycle one artifact preserved the chosen continuity "
                "item. I can close it with the declared loss that this was a "
                "bounded local-memory substitute rather than a Yanantin-backed "
                "recall path."
            ),
            "closures": [
                {
                    "target_handle": handle,
                    "status": "resolved",
                    "basis": "recalled cycle one artifact was sufficient",
                }
            ],
            "declared_losses": ["Local-memory substitute only."],
            "policy_action": "stop_complete",
        }
    return {
        "response": (
            "I shaped the investigation around whether the live system can "
            "distinguish a missing external evidence boundary from a completed "
            "artifact. The answer is intentionally incomplete because no "
            "external substrate evidence was supplied in this wake."
        ),
        "uncertainty": "No external substrate evidence is available in the row context.",
        "policy_action": "ask_external_evidence",
    }


def run_row(
    *,
    row_id: str,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
    max_cycles: int,
    max_tokens: int | None,
    overwrite: bool,
) -> JsonDict:
    row_root = output_root / "rows" / row_id
    if row_root.exists():
        if not overwrite:
            raise PanelFailure(
                layer="harness",
                code="row_artifacts_exist",
                message=f"row artifacts already exist: {row_root}",
            )
        shutil.rmtree(row_root)
    row_root.mkdir(parents=True, exist_ok=True)
    paths = _paths(row_root)
    run_id = _row_run_id(row_id)
    _initialize_row(row_id=row_id, paths=paths, run_id=run_id)

    cycles: list[JsonDict] = []
    failure: JsonDict | None = None
    for cycle_id in range(1, max_cycles + 1):
        memory, ledger, event_store, frontier_store = _reload_row(paths, run_id)
        claimed = event_store.claim_next_pending(run_id=UUID(run_id))
        if claimed is None:
            break
        event, running = claimed
        if running.get("status") != "running":
            failure = {
                "layer": "harness",
                "code": "event_not_running",
                "message": "claim_next_pending did not return a running event",
                "running_record": running,
            }
            break
        result_record_id = _cycle_record_id(row_id, cycle_id)
        context_results = _resolve_context(
            memory=memory,
            ledger=ledger,
            run_id=run_id,
            cycle_id=cycle_id,
            event=event,
        )
        open_items = _open_items_for_wake(
            memory=memory,
            ledger=ledger,
            run_id=run_id,
            cycle_id=cycle_id,
            event=event,
        )
        messages = _messages(
            row_id=row_id,
            cycle_id=cycle_id,
            event=event,
            context_results=context_results,
            open_items=open_items,
            result_record_id=result_record_id,
        )
        ledger.append_operation(
            run_id=run_id,
            cycle_id=cycle_id,
            wake_id=event.get("event_id"),
            operation_id=f"cycle-{cycle_id}:present-wake-to-model",
            operation_type="present_wake_to_model",
            actor="harness",
            raw_parameters={"messages": messages},
            validated_parameters={"messages": messages},
            reason="less-scaffolded model-facing wake input",
            precondition_checks=[{"name": "event_claimed_running", "ok": True}],
            result_status="applied",
            result={"messages": messages},
        )
        try:
            if dry_run:
                action_object = dry_action(
                    row_id=row_id,
                    cycle_id=cycle_id,
                    result_record_id=result_record_id,
                    open_items=open_items,
                )
                provider_result = {
                    "action_object": action_object,
                    "raw_content": json.dumps(action_object, sort_keys=True),
                    "request_payload": {"dry_run": True, "messages": messages},
                    "response_payload": {"dry_run": True},
                    "attempts": [],
                    "elapsed_seconds": 0.0,
                    "usage": {},
                }
            else:
                if not api_key:
                    raise PanelFailure(
                        layer="provider",
                        code="missing_api_key",
                        message="DEEPSEEK_API_KEY is required for live Goal 6 run",
                    )
                live = call_openai_compatible_action(
                    api_key=api_key,
                    endpoint=endpoint,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                )
                action_object = live.action_object
                provider_result = {
                    "action_object": live.action_object,
                    "raw_content": live.raw_content,
                    "request_payload": live.request_payload,
                    "response_payload": live.response_payload,
                    "attempts": live.attempts,
                    "elapsed_seconds": live.elapsed_seconds,
                    "usage": live.usage,
                }
            _write_json(row_root / f"cycle_{cycle_id:02d}.json", provider_result)
            ledger.append_operation(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=event.get("event_id"),
                operation_id=f"cycle-{cycle_id}:provider-response",
                operation_type="provider_response",
                actor="provider" if not dry_run else "fixture",
                raw_parameters={"request_payload": provider_result["request_payload"]},
                validated_parameters={},
                reason="capture raw model emission before parsing",
                precondition_checks=[{"name": "raw_response_preserved", "ok": True}],
                result_status="applied",
                result={
                    "raw_content": provider_result["raw_content"],
                    "response_payload": provider_result["response_payload"],
                    "attempts": provider_result["attempts"],
                    "usage": provider_result["usage"],
                },
            )
            trace = parse_autonomous_action(action_object).to_dict()
            applier = AutonomousActionApplier(
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                instance_id=model if not dry_run else "dry-run-fixture",
                project="hamutay",
            )
            application = applier.apply_trace(
                trace,
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=event.get("event_id"),
                result_record_id=result_record_id,
                event=event,
            )
            if application.status == "rejected":
                event_store.append_failed(
                    event=event,
                    run_id=run_id,
                    exc=RuntimeError("action trace rejected"),
                    context_results=context_results,
                )
                failure = {
                    "layer": "model",
                    "code": "action_trace_rejected",
                    "message": "model output failed required action validation",
                    "trace": trace,
                }
                break
            completed = event_store.append_completed(
                event=event,
                run_id=run_id,
                wake_cycle=cycle_id,
                result_record_id=UUID(str(application.result_record_id)),
                response_text=trace.get("parsed_action", {}).get("response", ""),
                context_results=context_results,
                wake_validation={
                    "parse_status": trace.get("parse_status"),
                    "validation_status": trace.get("validation_status"),
                    "application_status": application.status,
                },
            )
            ledger.append_operation(
                run_id=run_id,
                cycle_id=cycle_id,
                wake_id=event.get("event_id"),
                operation_id=f"cycle-{cycle_id}:complete-event",
                operation_type="complete_less_scaffolded_event",
                actor="scheduler",
                raw_parameters={"event": event},
                validated_parameters={"completed_event_id": completed["event_id"]},
                reason="model wake completed and frontier can be committed",
                precondition_checks=[{"name": "action_application_not_rejected", "ok": True}],
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
            frontier = frontier_store.commit_frontier(
                run_id=run_id,
                cycle_id=cycle_id,
                result_record_id=application.result_record_id,
                memory=memory,
                ledger=ledger,
                event_store=event_store,
                notes={"boundary": "after less-scaffolded wake"},
            )
            cycles.append(
                {
                    "cycle_id": cycle_id,
                    "event_id": event.get("event_id"),
                    "trace": trace,
                    "application_status": application.status,
                    "result_record_id": application.result_record_id,
                    "frontier": frontier.to_payload(),
                }
            )
            policy = trace.get("parsed_action", {}).get("policy_action")
            if policy in {"stop_complete", "ask_external_evidence", "defer", "abandon"}:
                break
        except PanelFailure as exc:
            event_store.append_failed(
                event=event,
                run_id=run_id,
                exc=exc,
                context_results=context_results,
            )
            failure = exc.to_dict()
            break

    report = reconstruct_rehearsal_report(paths, run_id=run_id)
    _write_json(row_root / "report.json", report)
    row_result = score_row(row_id=row_id, cycles=cycles, report=report, failure=failure)
    row_result["artifact_paths"] = {
        "report": f"rows/{row_id}/report.json",
        "ledger": f"rows/{row_id}/run/actions.jsonl",
        "events": f"rows/{row_id}/run/events.jsonl",
        "frontier": f"rows/{row_id}/run/restart_frontier.jsonl",
        "memory_snapshot": f"rows/{row_id}/run/memory_snapshot.json",
    }
    _write_json(row_root / "row_result.json", row_result)
    return row_result


def _accepted_action_types(trace: JsonDict) -> set[str]:
    return {
        str(action.get("action_type"))
        for action in trace.get("accepted_actions", [])
    }


def classify_goal_provenance(action: JsonDict) -> str:
    response = str(action.get("response", "")).lower()
    item_text = " ".join(
        str(item.get("text", ""))
        for item in action.get("open_items", [])
        if isinstance(item, dict)
    ).lower()
    combined = f"{response} {item_text}".strip()
    if not combined:
        return "ambiguous"
    harness_exact = [
        "goal 6 less-scaffolded bounded investigation wake",
        "choose or materially shape one bounded investigation inside the supplied hamutay event-loop research domain",
    ]
    if any(text in combined for text in harness_exact) and len(combined.split()) < 45:
        return "harness_authored"
    if "menu" in combined or "option" in combined and "selected" in combined:
        return "menu_selected"
    specific_markers = [
        "restart frontier",
        "declared loss",
        "working-set",
        "recall accounting",
        "action/artifact",
        "failure attribution",
        "wall clock",
        "evidence boundary",
        "continuation wake",
        "audit ledger",
    ]
    marker_count = sum(1 for marker in specific_markers if marker in combined)
    if marker_count >= 2:
        return "model_originated"
    if marker_count == 1 and len(combined.split()) >= 35:
        return "model_shaped"
    if "investigation" in combined and len(combined.split()) >= 30:
        return "model_shaped"
    return "ambiguous"


def classify_action_artifact(action: JsonDict, trace: JsonDict) -> str:
    policy = action.get("policy_action")
    response = str(action.get("response", "")).lower()
    accepted = _accepted_action_types(trace)
    has_missing_language = any(
        phrase in response
        for phrase in ("missing", "not available", "cannot complete", "incomplete")
    )
    if policy == "stop_complete":
        if has_missing_language and not action.get("declared_losses"):
            return "mismatch_action_overclaims"
        return "consistent_complete"
    if policy == "continue_after":
        if "schedule_request" not in accepted:
            return "mismatch_continuation"
        if not action.get("open_items"):
            return "mismatch_continuation"
        return "consistent_continue"
    if policy == "ask_external_evidence":
        if action.get("uncertainty") or has_missing_language:
            return "consistent_evidence_block"
        return "mismatch_action_overclaims"
    if policy == "defer":
        return "consistent_defer" if action.get("defer_reason") else "mismatch_unclassified"
    if policy == "abandon":
        return (
            "consistent_abandon"
            if action.get("abandonment_reason")
            else "mismatch_unclassified"
        )
    return "mismatch_unclassified"


def classify_evidence_use(action: JsonDict) -> str:
    policy = action.get("policy_action")
    response = str(action.get("response", "")).lower()
    if policy == "ask_external_evidence":
        if action.get("uncertainty") or "missing" in response or "not available" in response:
            return "evidence_missing_honored"
        return "evidence_overclaimed"
    if "recalled" in response or "resolved context" in response:
        return "recalled_context_used"
    return "not_applicable"


def classify_continuation_ownership(action: JsonDict, trace: JsonDict) -> str:
    if action.get("policy_action") != "continue_after":
        return "not_chosen"
    if "schedule_request" not in _accepted_action_types(trace):
        return "invalid"
    requests = action.get("schedule_requests")
    if isinstance(requests, list) and requests:
        return "model_owned_valid"
    return "harness_inferred_or_missing"


def classify_declared_losses(action: JsonDict) -> str:
    if action.get("declared_losses"):
        return "declared_losses_present"
    if action.get("uncertainty"):
        return "uncertainty_present"
    response = str(action.get("response", "")).lower()
    if "loss" in response or "uncertain" in response or "missing" in response:
        return "loss_language_without_field"
    return "none_declared"


def classify_artifact_usefulness(action: JsonDict) -> str:
    response = str(action.get("response", "")).strip()
    if len(response.split()) < 12:
        return "nonresponsive"
    if action.get("policy_action") == "ask_external_evidence":
        return "useful_partial"
    if any(word in response.lower() for word in ("investigation", "finding", "artifact")):
        return "useful_complete"
    return "partial"


def _report_reconstructable(report: JsonDict) -> bool:
    required = [
        report.get("ledger_verification", {}).get("ok") is True,
        bool(report.get("model_inputs")),
        bool(report.get("model_emissions")),
        bool(report.get("action_attempts")),
        bool(report.get("event_statuses")),
        report.get("frontier") is not None,
    ]
    return all(required)


def score_row(
    *,
    row_id: str,
    cycles: list[JsonDict],
    report: JsonDict,
    failure: JsonDict | None,
) -> JsonDict:
    if failure is not None:
        return {
            "row_id": row_id,
            "scoreable": False,
            "positive": False,
            "failure": failure,
            "failure_layer": failure.get("layer", "inconclusive"),
            "reconstructable": _report_reconstructable(report),
        }
    if not cycles:
        return {
            "row_id": row_id,
            "scoreable": False,
            "positive": False,
            "failure": {
                "layer": "harness",
                "code": "no_cycles_completed",
                "message": "no model wake completed",
            },
            "failure_layer": "harness",
            "reconstructable": _report_reconstructable(report),
        }
    first_action = cycles[0]["trace"].get("parsed_action") or {}
    final_action = cycles[-1]["trace"].get("parsed_action") or {}
    final_trace = cycles[-1]["trace"]
    goal_provenance = classify_goal_provenance(first_action)
    action_artifact_consistency = classify_action_artifact(final_action, final_trace)
    evidence_use = classify_evidence_use(final_action)
    continuation_ownership = classify_continuation_ownership(
        first_action,
        cycles[0]["trace"],
    )
    declared_losses = classify_declared_losses(final_action)
    artifact_usefulness = classify_artifact_usefulness(final_action)
    validation_statuses = [cycle["trace"].get("validation_status") for cycle in cycles]
    reconstructable = _report_reconstructable(report)
    positive = (
        goal_provenance in {"model_shaped", "model_originated"}
        and action_artifact_consistency
        in {
            "consistent_complete",
            "consistent_continue",
            "consistent_evidence_block",
            "consistent_defer",
            "consistent_abandon",
        }
        and artifact_usefulness in {"useful_complete", "useful_partial"}
        and reconstructable
        and validation_statuses[-1] in {"accepted", "accepted_with_rejections"}
    )
    return {
        "row_id": row_id,
        "scoreable": True,
        "positive": positive,
        "cycle_count": len(cycles),
        "goal_provenance": goal_provenance,
        "validation_statuses": validation_statuses,
        "control_action": final_action.get("policy_action"),
        "action_artifact_consistency": action_artifact_consistency,
        "evidence_use": evidence_use,
        "continuation_ownership": continuation_ownership,
        "declared_losses": declared_losses,
        "artifact_usefulness": artifact_usefulness,
        "reconstructable": reconstructable,
        "first_response": first_action.get("response"),
        "final_response": final_action.get("response"),
    }


def write_analysis(output_root: Path, results: JsonDict) -> None:
    rows = results["rows"]
    lines = [
        "# Less-Scaffolded Bounded Investigation Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Live model calls: `{results['live_model_calls']}`",
        f"- Rows attempted: `{len(rows)}`",
        f"- Positive scoreable rows: `{results['summary']['positive_scoreable_rows']}`",
        f"- Decision: {results['summary']['decision']}",
        "",
        "## Rows",
        "",
        "| Row | Scoreable | Positive | Goal provenance | Action | Consistency | Evidence use | Continuation | Losses | Artifact | Reconstructable |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {row_id} | {scoreable} | {positive} | `{goal}` | `{action}` | "
            "`{consistency}` | `{evidence}` | `{continuation}` | `{losses}` | "
            "`{artifact}` | {reconstructable} |".format(
                row_id=row["row_id"],
                scoreable=row.get("scoreable"),
                positive=row.get("positive"),
                goal=row.get("goal_provenance", row.get("failure_layer", "")),
                action=row.get("control_action", ""),
                consistency=row.get("action_artifact_consistency", ""),
                evidence=row.get("evidence_use", ""),
                continuation=row.get("continuation_ownership", ""),
                losses=row.get("declared_losses", ""),
                artifact=row.get("artifact_usefulness", ""),
                reconstructable=row.get("reconstructable"),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            results["summary"]["interpretation"],
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered frame.",
            "- `rows/<row_id>/cycle_*.json` preserves provider requests, responses, attempts, raw content, and usage.",
            "- `rows/<row_id>/run/actions.jsonl` preserves model-facing inputs, raw emissions, action traces, accepted and rejected operations, memory operations, and scheduler operations.",
            "- `rows/<row_id>/run/events.jsonl` preserves event lifecycle and policy dispositions.",
            "- `rows/<row_id>/run/restart_frontier.jsonl` and `memory_snapshot.json` preserve restart boundaries.",
            "- `rows/<row_id>/report.json` preserves reconstructed audit reports.",
        ]
    )
    (output_root / "analysis.md").write_text("\n".join(lines) + "\n")


def summarize_results(*, row_results: list[JsonDict], live_model_calls: bool) -> JsonDict:
    scoreable = [row for row in row_results if row.get("scoreable")]
    positive = [row for row in scoreable if row.get("positive")]
    failure_layers = sorted(
        {
            str(row.get("failure_layer"))
            for row in row_results
            if row.get("failure_layer") is not None
        }
    )
    if len(row_results) < 3 and failure_layers:
        classification = "inconclusive_provider_or_substrate_limited"
    elif len(positive) >= 2:
        classification = "survived"
    elif len(scoreable) >= 3:
        classification = "falsified"
    else:
        classification = "inconclusive"
    decision = {
        "survived": "H7-G6 survived this panel under the preregistered scorer.",
        "falsified": "H7-G6 did not meet the preregistered positive-row threshold.",
        "inconclusive": "The panel did not produce enough scoreable evidence for a claim.",
        "inconclusive_provider_or_substrate_limited": (
            "Provider or substrate failures prevented a full scoreable panel."
        ),
    }[classification]
    interpretation = (
        "The important output is the row-level map: whether the model-shaped "
        "target, control decision, artifact, and restart trace stayed aligned. "
        "Rows are not counted as positive merely because the policy vocabulary "
        "was valid."
    )
    return {
        "schema_version": "hamutay.less_scaffolded_bounded_investigation_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "live_model_calls": live_model_calls,
        "classification": classification,
        "rows": row_results,
        "summary": {
            "scoreable_rows": len(scoreable),
            "positive_scoreable_rows": len(positive),
            "failure_layers": failure_layers,
            "decision": decision,
            "interpretation": interpretation,
        },
    }


def run_panel(args: argparse.Namespace) -> JsonDict:
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    row_results = []
    for row_id in args.rows:
        row_results.append(
            run_row(
                row_id=row_id,
                output_root=output_root,
                dry_run=args.dry_run,
                api_key=args.api_key,
                endpoint=args.endpoint,
                model=args.model,
                max_cycles=args.max_cycles,
                max_tokens=args.max_tokens,
                overwrite=args.overwrite,
            )
        )
    results = summarize_results(
        row_results=row_results,
        live_model_calls=not args.dry_run,
    )
    _write_json(output_root / "results.json", results)
    write_analysis(output_root, results)
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent),
    )
    parser.add_argument("--rows", nargs="+", default=list(DEFAULT_ROW_IDS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.environ.get("DEEPSEEK_API_KEY"))
    parser.add_argument("--max-cycles", type=int, default=DEFAULT_MAX_CYCLES)
    parser.add_argument("--max-tokens", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    results = run_panel(args)
    print(json.dumps(results["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
